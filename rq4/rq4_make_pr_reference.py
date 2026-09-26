#!/usr/bin/env python3
"""
rq4_make_pr_reference.py

Build rq4_pr_reference.csv -- the list of PRs that rq4_fetch_review_data.py pulls review
data for -- from the three per-group PR tables, so the RQ4 sample always follows the
RQ2/RQ3 sample. Run it whenever the rq3_*_prs_with_task_type.csv tables change, then
rq4_fetch_review_data.py (it resumes from its checkpoint, so only new PRs are fetched)
and rq4_make_tables.py.

The GitHub coordinates (full_name, number) are parsed from each PR's html_url, which is
the only place they live: pr_id is AIDev's own id, not the GitHub PR number.

Shared inputs and outputs live in data/ at the repository root.

Output: data/rq4_pr_reference.csv   columns group, pr_id, full_name, number
"""

import os
import re
import sys

import pandas as pd

# Resolved from this file's location so the script runs correctly from anywhere.
DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')

FILES = {
    'AI agents':           os.path.join(DATA, 'rq3_agent_prs_with_task_type.csv'),
    'Human':               os.path.join(DATA, 'rq3_human_prs_with_task_type.csv'),
    'Human (pre-ChatGPT)': os.path.join(DATA, 'rq3_pre_chatgpt_prs_with_task_type.csv'),
}
OUT = os.path.join(DATA, 'rq4_pr_reference.csv')
URL = re.compile(r'github\.com/([^/]+/[^/]+)/pull/(\d+)')


def main():
    parts = []
    for group, path in FILES.items():
        d = pd.read_csv(path, dtype={'pr_id': str})
        m = d['html_url'].astype(str).str.extract(URL)
        bad = int(m[0].isna().sum())
        if bad:
            sys.exit(f'{group}: {bad} rows with no parsable html_url in {path}')
        parts.append(pd.DataFrame({'group': group, 'pr_id': d['pr_id'],
                                   'full_name': m[0], 'number': m[1].astype(int)}))
        print(f'{group:22s} {len(d):4d} PRs across {m[0].nunique():3d} repos')

    ref = pd.concat(parts, ignore_index=True)
    if ref['pr_id'].duplicated().any():
        sys.exit('duplicate pr_id across groups')
    ref.to_csv(OUT, index=False)
    print(f'wrote {OUT}: {len(ref)} PRs across {ref.full_name.nunique()} repos')


if __name__ == '__main__':
    main()
