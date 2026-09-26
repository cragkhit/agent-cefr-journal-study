#!/usr/bin/env python3
"""
rq4_fetch_comment_authors.py

Split the per-PR comment counts into human-authored and bot-authored.

Why this is needed
------------------
rq4_fetch_review_data.py stored GitHub's own counters `comments` and `review_comments`
(written out as n_issue_comments / n_review_comments). Those counters include comments
written by bots, and on agent PRs bots write about 70% of all comments. The RQ4
methodology counts only human review effort, so the counters have to be broken down by
author. The review *submissions* were already split human/bot by the first script; only
the comments were not.

We also record how many of the human comments were written by the PR author, so that
author replies can be excluded as a robustness check -- they are the author answering the
reviewer, not reviewer effort.

Requests per PR (REST):
  GET /repos/{full}/pulls/{n}/comments    -> inline review comments, with authors
  GET /repos/{full}/issues/{n}/comments   -> conversation comments, with authors

The PR author login is fetched separately in batches over GraphQL (about 30 requests for
the whole corpus) rather than one REST call per PR, which keeps the run inside a single
primary rate-limit window.

Reads GITHUB_TOKEN from .env or the environment; `gh auth token` also works:
  GITHUB_TOKEN=$(gh auth token) ./rq4_fetch_comment_authors.py

Checkpoints after every PR so a re-run resumes.

Outputs
-------
  rq4_pr_comment_authors.csv   one row per PR, the human/bot/author split
  log files/rq4_comments_checkpoint.jsonl
  log files/rq4_authors_checkpoint.jsonl
  log files/rq4_comments_<ts>.log
"""

import os
import sys
import time
import json
from datetime import datetime
from pathlib import Path

import requests
import pandas as pd

# Shared data lives in data/ at the repository root; checkpoints and run logs stay
# beside this script. Both are resolved from this file so it runs from anywhere.
HERE = Path(__file__).resolve().parent
DATA = HERE.parent / 'data'
LOGS = HERE / 'log files'

REF = DATA / 'rq4_pr_reference.csv'
METRICS = DATA / 'rq4_pr_review_metrics.csv'
OUT = DATA / 'rq4_pr_comment_authors.csv'
CHECKPOINT = LOGS / 'rq4_comments_checkpoint.jsonl'
AUTHOR_CP = LOGS / 'rq4_authors_checkpoint.jsonl'
TIMEOUT = 30
MAX_RETRIES = 5
PAUSE = 0.05
GQL_BATCH = 50


def log_factory(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write('=== rq4_comment_authors ' + datetime.now().isoformat() + ' ===\n')

    def log(m):
        line = '[' + datetime.now().strftime('%H:%M:%S') + '] ' + str(m)
        print(line, flush=True)
        with open(path, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    return log


def load_token():
    """Read GITHUB_TOKEN from .env or the environment. The value is never logged."""
    tok = os.environ.get('GITHUB_TOKEN')
    if not tok:
        env = Path('.env')
        if env.exists():
            for line in env.read_text(encoding='utf-8').splitlines():
                line = line.strip()
                if line.startswith('GITHUB_TOKEN='):
                    tok = line.split('=', 1)[1].strip().strip('"').strip("'")
                    break
    if not tok:
        sys.exit('GITHUB_TOKEN not found in .env or environment. '
                 'Try: GITHUB_TOKEN=$(gh auth token) ./rq4_fetch_comment_authors.py')
    return tok


def respect(resp, log):
    remaining = resp.headers.get('X-RateLimit-Remaining')
    reset = resp.headers.get('X-RateLimit-Reset')
    if remaining is None or reset is None:
        return
    if int(remaining) <= 10:
        wait = max(0, int(reset) - int(time.time())) + 5
        log('rate limit low (remaining=' + remaining + '); sleeping ' + str(wait) + 's')
        time.sleep(wait)


def get(session, url, log, params=None):
    """Return (json, status). status is 'ok', '404' or 'failed'."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = session.get(url, timeout=TIMEOUT, params=params)
        except requests.RequestException as e:
            wait = min(60, 2 ** attempt)
            log('  network ' + type(e).__name__ + ' on ' + url + ', retry in ' + str(wait) + 's')
            time.sleep(wait)
            continue

        if r.status_code == 200:
            respect(r, log)
            return r.json(), 'ok'
        if r.status_code in (403, 429):
            ra = r.headers.get('Retry-After')
            if ra:
                wait = int(ra) + 1
            else:
                reset = r.headers.get('X-RateLimit-Reset')
                wait = max(0, int(reset) - int(time.time())) + 5 if reset else min(120, 2 ** attempt)
            log('  ' + str(r.status_code) + ' on ' + url + '; waiting ' + str(wait) + 's')
            time.sleep(wait)
            continue
        if r.status_code in (404, 451):
            return None, str(r.status_code)
        wait = min(60, 2 ** attempt)
        log('  HTTP ' + str(r.status_code) + ' on ' + url + ', retry in ' + str(wait) + 's')
        time.sleep(wait)
    return None, 'failed'


def is_bot(user):
    """Same rule as rq4_fetch_review_data.py, so the two splits stay consistent."""
    if not user:
        return False
    if str(user.get('type', '')) == 'Bot':
        return True
    return str(user.get('login', '')).endswith('[bot]')


def paged(session, url, log):
    """All items from a paginated list endpoint. Returns (items, status)."""
    items, page = [], 1
    while True:
        chunk, st = get(session, url, log, params={'per_page': 100, 'page': page})
        if st != 'ok':
            return items, st
        if not chunk:
            break
        items.extend(chunk)
        if len(chunk) < 100:
            break
        page += 1
        time.sleep(PAUSE)
    return items, 'ok'


def split_comments(items, author_login):
    """Count comments by human / bot / the PR author."""
    human = bot = by_author = 0
    for c in items:
        u = c.get('user') or {}
        if is_bot(u):
            bot += 1
        else:
            human += 1
            if author_login and u.get('login') == author_login:
                by_author += 1
    return human, bot, by_author


# ---------------- PR authors, batched over GraphQL ----------------

GQL = 'https://api.github.com/graphql'


def fetch_authors(session, rows, log):
    """{pr_id: login or None} for every PR, fetched GQL_BATCH at a time."""
    done = {}
    if AUTHOR_CP.exists():
        with open(AUTHOR_CP, encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    d = json.loads(line)
                    done[d['pr_id']] = d
    log('PR authors cached: ' + str(len(done)))

    todo = [r for r in rows if r.pr_id not in done]
    AUTHOR_CP.parent.mkdir(parents=True, exist_ok=True)

    for start in range(0, len(todo), GQL_BATCH):
        batch = todo[start:start + GQL_BATCH]
        parts = []
        for i, r in enumerate(batch):
            owner, name = r.full_name.split('/', 1)
            parts.append(
                f'a{i}: repository(owner: "{owner}", name: "{name}") '
                f'{{ pullRequest(number: {int(r.number)}) '
                f'{{ author {{ login __typename }} }} }}'
            )
        query = 'query {' + ' '.join(parts) + '}'

        data = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = session.post(GQL, json={'query': query}, timeout=TIMEOUT)
            except requests.RequestException as e:
                log('  gql network ' + type(e).__name__ + ', retry')
                time.sleep(min(60, 2 ** attempt))
                continue
            if resp.status_code == 200:
                data = resp.json().get('data') or {}
                break
            if resp.status_code in (403, 429):
                ra = resp.headers.get('Retry-After')
                wait = int(ra) + 1 if ra else min(120, 2 ** attempt)
                log('  gql ' + str(resp.status_code) + '; waiting ' + str(wait) + 's')
                time.sleep(wait)
                continue
            log('  gql HTTP ' + str(resp.status_code) + ', retry')
            time.sleep(min(60, 2 ** attempt))
        if data is None:
            data = {}

        with open(AUTHOR_CP, 'a', encoding='utf-8') as f:
            for i, r in enumerate(batch):
                node = (data.get('a' + str(i)) or {}).get('pullRequest') or {}
                au = node.get('author') or {}
                login, tname = au.get('login'), au.get('__typename')
                # GraphQL reports a bot as "devin-ai-integration"; REST comment authors
                # carry the "[bot]" suffix. Normalise so the two can be compared.
                if login and tname == 'Bot' and not login.endswith('[bot]'):
                    login = login + '[bot]'
                rec = {'pr_id': r.pr_id,
                       'author_login': login,
                       'author_typename': tname}
                done[r.pr_id] = rec
                f.write(json.dumps(rec, ensure_ascii=False) + '\n')

        log('  authors ' + str(min(start + GQL_BATCH, len(todo))) + '/' + str(len(todo)))
        time.sleep(PAUSE)

    return done


def main():
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    log = log_factory(LOGS / ('rq4_comments_' + ts + '.log'))

    ref = pd.read_csv(REF, dtype={'pr_id': str})

    # only PRs the first fetch actually reached; the 15 deleted ones stay out
    met = pd.read_csv(METRICS, dtype={'pr_id': str})
    ok_ids = set(met.loc[met.status == 'ok', 'pr_id'])
    ref = ref[ref.pr_id.isin(ok_ids)].reset_index(drop=True)
    log(str(len(ref)) + ' PRs with status ok across ' + str(ref.full_name.nunique()) + ' repos')

    session = requests.Session()
    session.headers.update({
        'Authorization': 'Bearer ' + load_token(),
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
        'User-Agent': 'aidev-cefr-journal-study',
    })

    rows = list(ref.itertuples())
    authors = fetch_authors(session, rows, log)

    done = {}
    if CHECKPOINT.exists():
        with open(CHECKPOINT, encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    d = json.loads(line)
                    done[d['pr_id']] = d
    log('comments cached: ' + str(len(done)))
    CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)

    todo = [r for r in rows if r.pr_id not in done]
    log(str(len(todo)) + ' PRs to fetch comments for')
    t0 = time.time()

    for i, r in enumerate(todo, 1):
        author_login = (authors.get(r.pr_id) or {}).get('author_login')
        base = f'https://api.github.com/repos/{r.full_name}'

        rc, st1 = paged(session, f'{base}/pulls/{int(r.number)}/comments', log)
        ic, st2 = paged(session, f'{base}/issues/{int(r.number)}/comments', log)

        rc_h, rc_b, rc_a = split_comments(rc, author_login)
        ic_h, ic_b, ic_a = split_comments(ic, author_login)

        rec = {
            'pr_id': r.pr_id,
            'group': r.group,
            'full_name': r.full_name,
            'number': int(r.number),
            'author_login': author_login,
            'comment_status': 'ok' if st1 == 'ok' and st2 == 'ok' else f'{st1}/{st2}',
            'n_review_comments_human': rc_h,
            'n_review_comments_bot': rc_b,
            'n_review_comments_author': rc_a,
            'n_issue_comments_human': ic_h,
            'n_issue_comments_bot': ic_b,
            'n_issue_comments_author': ic_a,
            'n_review_comments_fetched': len(rc),
            'n_issue_comments_fetched': len(ic),
        }
        done[r.pr_id] = rec
        with open(CHECKPOINT, 'a', encoding='utf-8') as f:
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')

        if i % 25 == 0 or i == len(todo):
            rate = i / max(1e-9, time.time() - t0)
            eta = (len(todo) - i) / max(1e-9, rate) / 60
            log('  ' + str(i) + '/' + str(len(todo)) + ' (' + format(rate, '.1f') +
                '/s, ETA ' + format(eta, '.0f') + 'm)')
        time.sleep(PAUSE)

    out = pd.DataFrame(list(done.values())).sort_values(['group', 'pr_id'])
    out.to_csv(OUT, index=False)

    # ---------------- run summary + reconciliation ----------------
    log('')
    log('=== run summary ===')
    log('elapsed: ' + format(time.time() - t0, '.0f') + 's')
    log('comment_status: ' + str(out.comment_status.value_counts().to_dict()))

    chk = out.merge(met[['pr_id', 'n_review_comments', 'n_issue_comments']],
                    on='pr_id', how='left')
    for kind in ['review', 'issue']:
        tot = chk[f'n_{kind}_comments_human'] + chk[f'n_{kind}_comments_bot']
        counter = chk[f'n_{kind}_comments'].fillna(0)
        mism = int((tot != counter).sum())
        log(f'  {kind:6s} comments: {len(chk) - mism}/{len(chk)} reconcile with the '
            f'stored counter ({(len(chk) - mism) / len(chk) * 100:.1f}%)')
        if mism:
            d = (tot - counter)
            log(f'          {mism} differ; median drift {d[d != 0].median():+.1f} '
                f'(comments deleted or added since the first fetch)')

    log('')
    for g, s in out.groupby('group'):
        tot_h = (s.n_review_comments_human + s.n_issue_comments_human)
        tot_b = (s.n_review_comments_bot + s.n_issue_comments_bot)
        tot_a = (s.n_review_comments_author + s.n_issue_comments_author)
        allc = tot_h.sum() + tot_b.sum()
        log(f'  {g:22s} n={len(s):4d}  comments: human={int(tot_h.sum()):6d} '
            f'bot={int(tot_b.sum()):6d} ({tot_b.sum() / max(1, allc) * 100:4.1f}% bot)  '
            f'of human, {int(tot_a.sum()):5d} by the PR author '
            f'({tot_a.sum() / max(1, tot_h.sum()) * 100:4.1f}%)')
        log(f'  {"":22s}  zero human comments: '
            f'{int((tot_h == 0).sum()):4d} ({(tot_h == 0).mean() * 100:5.1f}%)')


if __name__ == '__main__':
    main()
