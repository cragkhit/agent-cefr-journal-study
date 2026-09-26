#!/usr/bin/env python3
"""
fetch_pre_chatgpt_titles.py

Fetch PR titles for the 477 pre-ChatGPT PRs in the RQ3 comparison sample.

Why this is needed: data/pre_chatgpt_pr_index.csv records full_name + number for every
pre-ChatGPT PR but never stored the title, and AIDev's pr_task_type.parquet covers agent
PRs only. Chaiyong needs the titles to label task types via ChatGPT for RQ3.

Reads GITHUB_TOKEN from .env (never printed). Checkpoints after every PR, so a re-run
resumes instead of refetching. Handles rate limits proactively (X-RateLimit-Remaining)
and reactively (Retry-After on 403/429).

Output
------
  data/rq3_pre_chatgpt_prs_titles.csv        same column layout as the other two groups
  data/rq3_pre_chatgpt_prs_for_labelling.csv bare pr_id,title
  log files/pre_chatgpt_titles_checkpoint.csv
  log files/pre_chatgpt_titles_<ts>.log
"""

import os
import sys
import time
import csv
from datetime import datetime
from pathlib import Path

import requests
import pandas as pd

LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
COLS = ['group', 'pr_id', 'repo', 'html_url', 'title', 'body',
        'type', 'confidence', 'reason'] + LEVELS + ['total']

# Bumped when the checkpoint schema changed (body added) so an old checkpoint
# is not resumed against the new columns.
CHECKPOINT = Path('log files/pre_chatgpt_title_body_checkpoint.csv')
API = 'https://api.github.com/repos/{full_name}/pulls/{number}'
TIMEOUT = 30
MAX_RETRIES = 5


def log_factory(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write('=== pre_chatgpt_titles ' + datetime.now().isoformat() + ' ===\n')

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


def respect_rate_limit(resp, log):
    """Proactive: sleep before we run out, not after we get blocked."""
    remaining = resp.headers.get('X-RateLimit-Remaining')
    reset = resp.headers.get('X-RateLimit-Reset')
    if remaining is None or reset is None:
        return
    if int(remaining) <= 5:
        wait = max(0, int(reset) - int(time.time())) + 5
        log('rate limit nearly exhausted (remaining=' + remaining + '); sleeping ' + str(wait) + 's')
        time.sleep(wait)


def fetch_one(session, full_name, number, log):
    url = API.format(full_name=full_name, number=number)
    tag = full_name + '#' + str(number)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = session.get(url, timeout=TIMEOUT)
        except requests.RequestException as e:
            wait = min(60, 2 ** attempt)
            log('  network error ' + type(e).__name__ + ' on ' + tag + ', retry in ' + str(wait) + 's')
            time.sleep(wait)
            continue

        if r.status_code == 200:
            respect_rate_limit(r, log)
            d = r.json()
            return {'title': d.get('title') or '', 'body': d.get('body') or '',
                    'html_url': d.get('html_url') or '', 'status': 'ok'}

        if r.status_code in (403, 429):
            ra = r.headers.get('Retry-After')
            if ra:
                wait = int(ra) + 1
            else:
                reset = r.headers.get('X-RateLimit-Reset')
                if reset:
                    wait = max(0, int(reset) - int(time.time())) + 5
                else:
                    wait = min(120, 2 ** attempt)
            log('  ' + str(r.status_code) + ' on ' + tag + '; waiting ' + str(wait) + 's (attempt ' + str(attempt) + ')')
            time.sleep(wait)
            continue

        if r.status_code == 404:
            log('  404 ' + tag + ' - repo or PR no longer public')
            return {'title': '', 'body': '', 'html_url': '', 'status': '404'}

        wait = min(60, 2 ** attempt)
        log('  HTTP ' + str(r.status_code) + ' on ' + tag + ', retry in ' + str(wait) + 's')
        time.sleep(wait)

    return {'title': '', 'body': '', 'html_url': '', 'status': 'failed'}


def main():
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    log = log_factory(Path('log files') / ('pre_chatgpt_titles_' + ts + '.log'))

    per = pd.read_csv('data/rq2_three_groups_per_pr.csv', dtype={'pr_id': str})
    pre = per[per.group == 'Human (pre-ChatGPT)'].copy()
    idx = pd.read_csv('data/pre_chatgpt_pr_index.csv', dtype={'pr_id': str})
    tgt = pre.merge(idx[['pr_id', 'full_name', 'number']], on='pr_id', how='left')

    if tgt['full_name'].isna().any():
        sys.exit(str(tgt.full_name.isna().sum()) + ' PRs missing full_name in the index - stopping')
    log(str(len(tgt)) + ' pre-ChatGPT PRs across ' + str(tgt.full_name.nunique()) + ' repos')

    # ---------------- resume ----------------
    done = {}
    if CHECKPOINT.exists():
        prev = pd.read_csv(CHECKPOINT, dtype={'pr_id': str}).fillna('')
        for r in prev.itertuples():
            done[r.pr_id] = {'title': r.title, 'body': r.body,
                             'html_url': r.html_url, 'status': r.status}
        log('resuming: ' + str(len(done)) + ' already fetched')
    else:
        CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
        with open(CHECKPOINT, 'w', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow(['pr_id', 'title', 'body', 'html_url', 'status'])

    session = requests.Session()
    session.headers.update({
        'Authorization': 'Bearer ' + load_token(),
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
        'User-Agent': 'aidev-cefr-journal-study',
    })

    todo = [r for r in tgt.itertuples() if r.pr_id not in done]
    log(str(len(todo)) + ' to fetch, ' + str(len(done)) + ' cached')
    t0 = time.time()

    for i, r in enumerate(todo, 1):
        res = fetch_one(session, r.full_name, int(r.number), log)
        done[r.pr_id] = res
        with open(CHECKPOINT, 'a', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow([r.pr_id, res['title'], res['body'],
                                    res['html_url'], res['status']])
        if i % 25 == 0 or i == len(todo):
            rate = i / max(1e-9, time.time() - t0)
            log('  ' + str(i) + '/' + str(len(todo)) + ' (' + format(rate, '.1f') + '/s)')
        time.sleep(0.1)  # stay well under the secondary rate limit

    # ---------------- assemble ----------------
    tgt['title'] = tgt.pr_id.map(lambda p: done.get(p, {}).get('title', ''))
    tgt['body'] = tgt.pr_id.map(lambda p: done.get(p, {}).get('body', ''))
    tgt['html_url'] = tgt.pr_id.map(lambda p: done.get(p, {}).get('html_url', ''))
    tgt['status'] = tgt.pr_id.map(lambda p: done.get(p, {}).get('status', 'missing'))

    out = tgt.copy()
    for c in COLS:
        if c not in out.columns:
            out[c] = ''
    out['total'] = out[LEVELS].sum(axis=1)
    out = out[COLS].sort_values('pr_id').reset_index(drop=True)
    out.to_csv('data/rq3_pre_chatgpt_prs_titles.csv', index=False)
    out[['pr_id', 'title', 'body']].to_csv('data/rq3_pre_chatgpt_prs_for_labelling.csv', index=False)

    # ---------------- run summary + sanity ----------------
    log('')
    log('=== run summary ===')
    log('elapsed: ' + format(time.time() - t0, '.0f') + 's')
    for k, v in tgt.status.value_counts().items():
        log('  status ' + str(k) + ': ' + str(v))

    ok = True
    if len(out) != 477:
        log('  FAIL: expected 477 rows, got ' + str(len(out)))
        ok = False
    blank = int(out.title.astype(str).str.strip().eq('').sum())
    if blank:
        log('  WARN: ' + str(blank) + ' PRs have no title (see the status column)')
        ok = False
    if out.pr_id.duplicated().any():
        log('  FAIL: duplicate pr_id')
        ok = False
    empty_body = int(out.body.astype(str).str.strip().eq('').sum())
    log('  PRs with an empty body: ' + str(empty_body) + ' (legitimate - not all PRs have a description)')
    log('  body chars: total ' + str(int(out.body.astype(str).str.len().sum())) +
        ', max ' + str(int(out.body.astype(str).str.len().max())))
    if int(out.total.sum()) != int(tgt[LEVELS].sum().sum()):
        log('  FAIL: CEFR counts did not survive the join')
        ok = False
    log('  all checks passed' if ok else '  SEE ISSUES ABOVE')


if __name__ == '__main__':
    main()
