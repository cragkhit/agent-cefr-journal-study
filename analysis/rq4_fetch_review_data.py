#!/usr/bin/env python3
"""
fetch_rq4_review_data.py

Collect the review-effort data RQ4 needs, for all three comparison groups.

Why the GitHub API and not AIDev
--------------------------------
AIDev's pr_reviews / pr_comments / pr_timeline tables cover AGENT PRs only. Checked at
the pinned v3 revision: of our 513 human PRs and 477 pre-ChatGPT PRs, exactly ZERO appear
in any of them. RQ4's whole point is comparing review effort on agent vs human code, so
that comparison is impossible from AIDev alone.

Fetching all three groups from the API with one script also keeps the measurement
consistent -- mixing an AIDev snapshot for agents with a live API pull for humans would
confound group with snapshot date.

Two requests per PR:
  GET /repos/{full}/pulls/{number}           -> size controls + comment counts
  GET /repos/{full}/pulls/{number}/reviews   -> review rounds, states, reviewers
then one request per distinct reviewer for the seniority proxy:
  GET /users/{login}                         -> followers, public_repos, account age

Reads GITHUB_TOKEN from .env (never printed). Checkpoints after every PR so a re-run
resumes. Proactive rate limiting on X-RateLimit-Remaining plus Retry-After on 403/429.

Outputs
-------
  rq4_pr_review_metrics.csv    one row per PR, ready to join as new columns
  rq4_reviews_long.csv         one row per review submission
  rq4_reviewers.csv            one row per distinct reviewer
  log files/rq4_review_checkpoint.jsonl
  log files/rq4_review_<ts>.log
"""

import os
import sys
import time
import json
from datetime import datetime
from pathlib import Path

import requests
import pandas as pd

REF = 'rq4_pr_reference.csv'
CHECKPOINT = Path('log files/rq4_review_checkpoint.jsonl')
REVIEWER_CP = Path('log files/rq4_reviewer_checkpoint.jsonl')
TIMEOUT = 30
MAX_RETRIES = 5
PAUSE = 0.1


def log_factory(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write('=== rq4_review ' + datetime.now().isoformat() + ' ===\n')

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
        sys.exit('GITHUB_TOKEN not found in .env or environment. Add it and re-run.')
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
    if not user:
        return False
    if str(user.get('type', '')) == 'Bot':
        return True
    return str(user.get('login', '')).endswith('[bot]')


def hours(a, b):
    if not a or not b:
        return None
    ta = pd.to_datetime(a, utc=True, errors='coerce')
    tb = pd.to_datetime(b, utc=True, errors='coerce')
    if pd.isna(ta) or pd.isna(tb):
        return None
    return (tb - ta).total_seconds() / 3600.0


def fetch_pr(session, full_name, number, log):
    base = f'https://api.github.com/repos/{full_name}/pulls/{number}'
    pr, st = get(session, base, log)
    if st != 'ok':
        return {'status': st}

    reviews, page = [], 1
    while True:
        chunk, st2 = get(session, base + '/reviews', log,
                         params={'per_page': 100, 'page': page})
        if st2 != 'ok' or not chunk:
            break
        reviews.extend(chunk)
        if len(chunk) < 100:
            break
        page += 1
        time.sleep(PAUSE)

    created = pr.get('created_at')
    rows = []
    for rv in reviews:
        u = rv.get('user') or {}
        rows.append({
            'login': u.get('login'),
            'bot': is_bot(u),
            'state': rv.get('state'),
            'submitted_at': rv.get('submitted_at'),
            'body_len': len(rv.get('body') or ''),
        })

    human = [r for r in rows if not r['bot']]
    subs = sorted([r['submitted_at'] for r in human if r['submitted_at']])
    subs_all = sorted([r['submitted_at'] for r in rows if r['submitted_at']])

    def count(states, only_human=True):
        src = human if only_human else rows
        return sum(1 for r in src if r['state'] in states)

    return {
        'status': 'ok',
        # --- size controls ---
        'additions': pr.get('additions'),
        'deletions': pr.get('deletions'),
        'changed_files': pr.get('changed_files'),
        'n_commits': pr.get('commits'),
        # --- comment volume (GitHub's own counters) ---
        'n_issue_comments': pr.get('comments'),
        'n_review_comments': pr.get('review_comments'),
        # --- review activity ---
        'n_reviews_total': len(rows),
        'n_reviews_human': len(human),
        'n_reviews_bot': len(rows) - len(human),
        'n_reviewers_human': len({r['login'] for r in human if r['login']}),
        'n_reviewers_bot': len({r['login'] for r in rows if r['bot'] and r['login']}),
        'n_approved': count(['APPROVED']),
        'n_changes_requested': count(['CHANGES_REQUESTED']),
        'n_commented': count(['COMMENTED']),
        'any_changes_requested': int(count(['CHANGES_REQUESTED']) > 0),
        # --- latency ---
        'first_review_latency_h': hours(created, subs[0]) if subs else None,
        'first_review_latency_any_h': hours(created, subs_all[0]) if subs_all else None,
        'time_to_merge_h': hours(created, pr.get('merged_at')),
        # --- context ---
        'pr_state': pr.get('state'),
        'merged': int(bool(pr.get('merged_at'))),
        'draft': int(bool(pr.get('draft'))),
        'author_association': pr.get('author_association'),
        'pr_created_at': created,
        'pr_merged_at': pr.get('merged_at'),
        '_reviews': rows,
    }


def load_jsonl(path):
    seen = {}
    if path.exists():
        with open(path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                seen[d['pr_id']] = d
    return seen


def main():
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    log = log_factory(Path('log files') / ('rq4_review_' + ts + '.log'))

    ref = pd.read_csv(REF, dtype={'pr_id': str})
    log(str(len(ref)) + ' PRs across ' + str(ref.full_name.nunique()) + ' repos')

    done = load_jsonl(CHECKPOINT)
    log('resuming: ' + str(len(done)) + ' already fetched')
    CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update({
        'Authorization': 'Bearer ' + load_token(),
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
        'User-Agent': 'aidev-cefr-journal-study',
    })

    todo = [r for r in ref.itertuples() if r.pr_id not in done]
    log(str(len(todo)) + ' to fetch')
    t0 = time.time()

    for i, r in enumerate(todo, 1):
        rec = fetch_pr(session, r.full_name, int(r.number), log)
        rec['pr_id'] = r.pr_id
        rec['group'] = r.group
        rec['full_name'] = r.full_name
        rec['number'] = int(r.number)
        done[r.pr_id] = rec
        with open(CHECKPOINT, 'a', encoding='utf-8') as f:
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')
        if i % 25 == 0 or i == len(todo):
            rate = i / max(1e-9, time.time() - t0)
            eta = (len(todo) - i) / max(1e-9, rate) / 60
            log('  ' + str(i) + '/' + str(len(todo)) + ' (' + format(rate, '.1f') +
                '/s, ETA ' + format(eta, '.0f') + 'm)')
        time.sleep(PAUSE)

    # ---------------- reviewer seniority ----------------
    logins = set()
    for d in done.values():
        for rv in d.get('_reviews', []) or []:
            if rv.get('login') and not rv.get('bot'):
                logins.add(rv['login'])
    log('distinct human reviewers: ' + str(len(logins)))

    rdone = {}
    if REVIEWER_CP.exists():
        with open(REVIEWER_CP, encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    d = json.loads(line)
                    rdone[d['login']] = d
    log('reviewers cached: ' + str(len(rdone)))

    for i, lg in enumerate(sorted(logins - set(rdone)), 1):
        u, st = get(session, 'https://api.github.com/users/' + lg, log)
        rec = {'login': lg, 'status': st}
        if st == 'ok':
            rec.update({'followers': u.get('followers'), 'following': u.get('following'),
                        'public_repos': u.get('public_repos'),
                        'account_created_at': u.get('created_at'), 'user_type': u.get('type')})
        rdone[lg] = rec
        with open(REVIEWER_CP, 'a', encoding='utf-8') as f:
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')
        if i % 50 == 0:
            log('  reviewers ' + str(i) + '/' + str(len(logins - set(rdone)) + i))
        time.sleep(PAUSE)

    # ---------------- write outputs ----------------
    per, long = [], []
    for pid, d in done.items():
        row = {k: v for k, v in d.items() if k != '_reviews'}
        per.append(row)
        for rv in d.get('_reviews', []) or []:
            long.append({'pr_id': pid, 'group': d.get('group'),
                         'full_name': d.get('full_name'), **rv})

    per = pd.DataFrame(per).sort_values(['group', 'pr_id'])
    per.to_csv('rq4_pr_review_metrics.csv', index=False)
    pd.DataFrame(long).to_csv('rq4_reviews_long.csv', index=False)
    pd.DataFrame(list(rdone.values())).to_csv('rq4_reviewers.csv', index=False)

    # ---------------- run summary + sanity ----------------
    log('')
    log('=== run summary ===')
    log('elapsed: ' + format(time.time() - t0, '.0f') + 's')
    log('status: ' + str(per.status.value_counts().to_dict()))
    ok = True
    if len(per) != len(ref):
        log('  FAIL: expected ' + str(len(ref)) + ' rows, got ' + str(len(per)))
        ok = False
    if per.pr_id.duplicated().any():
        log('  FAIL: duplicate pr_id')
        ok = False
    good = per[per.status == 'ok']
    log('  fetched ok: ' + str(len(good)) + ' of ' + str(len(per)))
    for g, s in good.groupby('group'):
        z_rev = int((s.n_reviews_human.fillna(0) == 0).sum())
        z_com = int((s.n_review_comments.fillna(0) + s.n_issue_comments.fillna(0) == 0).sum())
        log(f'  {g:22s} n={len(s):4d}  zero human reviews={z_rev:4d} ({z_rev/len(s)*100:5.1f}%)'
            f'  zero comments={z_com:4d} ({z_com/len(s)*100:5.1f}%)'
            f'  median additions={s.additions.median()}')
    log('  all checks passed' if ok else '  SEE ISSUES ABOVE')


if __name__ == '__main__':
    main()
