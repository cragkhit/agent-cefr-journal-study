#!/usr/bin/env python3
"""
fetch_commit_parents.py

Record the parent count of every commit in the three corpora, so merge commits can be
excluded from the proficiency analysis.

Why: the commit-collection step took every commit listed on a PR, including merge commits
such as "Merge branch 'main' into feature". A merge commit's diff is the upstream code being
pulled into the branch -- not code the PR author wrote -- and counting it inflates a PR's
constructs. A commit is a merge iff it has more than one parent.

Uses GraphQL, batching up to 50 commits per request (one alias per commit), so ~7,400
commits take about 150 requests instead of 7,400 REST calls.

Reads GITHUB_TOKEN from .env (never printed). Checkpoints per batch; a re-run resumes.

Output: data/commit_parents.csv   columns owner, repo, sha, parents  (-1 = not found)
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

STUDY_DEFAULT = '../agent-cefr-journal-study/data'   # where the *_fetch_summary.csv files live
SUMMARIES = ['ai_fetch_summary.csv', 'human_fetch_summary.csv', 'pre_chatgpt_fetch_summary.csv']
OUT = Path('data/commit_parents.csv')
CHECKPOINT = Path('log files/commit_parents_checkpoint.jsonl')
BATCH = 50


def log_factory(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    def log(m):
        line = '[' + datetime.now().strftime('%H:%M:%S') + '] ' + str(m)
        print(line, flush=True)
        with open(path, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    return log


def load_token():
    tok = os.environ.get('GITHUB_TOKEN')
    if not tok and Path('.env').exists():
        for line in Path('.env').read_text(encoding='utf-8-sig').splitlines():
            if line.strip().startswith('GITHUB_TOKEN='):
                tok = line.split('=', 1)[1].strip().strip('"').strip("'")
    if not tok:
        sys.exit('GITHUB_TOKEN not found in .env or environment.')
    return tok


def query(session, owner, repo, shas, log):
    fields = '\n'.join(f'c{i}: object(oid: "{s}") {{ ... on Commit {{ parents {{ totalCount }} }} }}'
                       for i, s in enumerate(shas))
    q = f'query {{ repository(owner: "{owner}", name: "{repo}") {{ {fields} }} rateLimit {{ remaining resetAt }} }}'
    for attempt in range(1, 6):
        try:
            r = session.post('https://api.github.com/graphql', json={'query': q}, timeout=60)
        except requests.RequestException as e:
            log(f'  network {type(e).__name__} on {owner}/{repo}; retrying')
            time.sleep(min(60, 2 ** attempt)); continue
        if r.status_code in (403, 429, 502, 503):
            wait = int(r.headers.get('Retry-After', min(120, 2 ** attempt * 5)))
            log(f'  {r.status_code} on {owner}/{repo}; waiting {wait}s'); time.sleep(wait); continue
        body = r.json()
        rl = (body.get('data') or {}).get('rateLimit')
        if rl and rl['remaining'] < 50:
            reset = datetime.fromisoformat(rl['resetAt'].replace('Z', '+00:00')).timestamp()
            wait = max(0, reset - time.time()) + 5
            log(f'  GraphQL budget low ({rl["remaining"]}); sleeping {wait:.0f}s'); time.sleep(wait)
        repo_obj = (body.get('data') or {}).get('repository')
        if repo_obj is None:
            return {s: -1 for s in shas}          # repository gone or renamed
        return {s: ((repo_obj.get(f'c{i}') or {}).get('parents') or {}).get('totalCount', -1)
                for i, s in enumerate(shas)}
    return {s: -1 for s in shas}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--study-data', default=STUDY_DEFAULT,
                    help='folder holding the fetch summaries ("data" inside the replication package)')
    args = ap.parse_args()
    STUDY = Path(args.study_data)

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    log = log_factory(Path('log files') / f'commit_parents_{ts}.log')

    parts = [pd.read_csv(STUDY / f, usecols=['owner', 'repo', 'sha'], dtype=str) for f in SUMMARIES]
    commits = pd.concat(parts).dropna().drop_duplicates().sort_values(['owner', 'repo', 'sha'])
    log(f'{len(commits)} distinct commits across {commits.groupby(["owner", "repo"]).ngroups} repos')

    done = {}
    if CHECKPOINT.exists():
        for line in CHECKPOINT.read_text(encoding='utf-8').splitlines():
            if line.strip():
                done.update(json.loads(line))
    log(f'resuming: {len(done)} cached')

    s = requests.Session()
    s.headers.update({'Authorization': 'Bearer ' + load_token(), 'User-Agent': 'aidev-cefr-journal-study'})

    todo = commits[~commits.sha.isin(done)]
    batches = [(o, r, g.sha.tolist()[i:i + BATCH])
               for (o, r), g in todo.groupby(['owner', 'repo'])
               for i in range(0, len(g), BATCH)]
    log(f'{len(todo)} to fetch in {len(batches)} batches')
    for i, (o, r, shas) in enumerate(batches, 1):
        res = query(s, o, r, shas, log)
        done.update(res)
        with open(CHECKPOINT, 'a', encoding='utf-8') as f:
            f.write(json.dumps(res) + '\n')
        if i % 20 == 0 or i == len(batches):
            log(f'  {i}/{len(batches)} batches')
        time.sleep(0.2)

    commits['parents'] = commits.sha.map(done).fillna(-1).astype(int)
    commits.to_csv(OUT, index=False)

    log('=== run summary ===')
    log(f'parents distribution: {commits.parents.value_counts().sort_index().to_dict()}')
    miss = int((commits.parents < 0).sum())
    log(f'not found: {miss} ({miss / len(commits) * 100:.2f}%)')
    log('all checks passed' if len(commits) == commits.sha.nunique() else 'WARN: duplicate sha across repos')


if __name__ == '__main__':
    main()
