#!/usr/bin/env python3
"""
make_rq3_pre_chatgpt_table.py

Rebuild the pre-ChatGPT per-PR table on the current construct counts while keeping
Chaiyong's task-type labels untouched.

Unlike the agent and human groups, the pre-ChatGPT task types are not in AIDev: Chaiyong
labelled the 477 PRs with GPT-4.1-mini (see analysis/rq4_label_pre_chatgpt_prs.py in the
paper repository). make_rq3_task_type_export.py cannot regenerate those labels, so this
script takes the labelled table as the source of titles, bodies and labels, and replaces
only the A1-C2 counts with those in data/rq2_three_groups_per_pr.csv. PRs that no longer
contribute any construct -- e.g. those whose only commits were merges -- drop out.

  --labelled   the labelled table (default: the copy in data/)
  output       data/rq3_pre_chatgpt_prs_with_task_type.csv  (base columns only;
               make_rq4_tables.py adds the RQ4 columns)
"""

import argparse

import pandas as pd

LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
BASE_COLS = ['group', 'pr_id', 'repo', 'agent', 'html_url', 'title', 'body',
             'type', 'confidence', 'reason'] + LEVELS + ['total']
GROUP = 'Human (pre-ChatGPT)'
OUT = 'data/rq3_pre_chatgpt_prs_with_task_type.csv'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--labelled', default=OUT)
    args = ap.parse_args()

    lab = pd.read_csv(args.labelled, dtype={'pr_id': str})
    keep = [c for c in BASE_COLS if c not in LEVELS + ['total']]
    lab = lab[keep]
    per = pd.read_csv('data/rq2_three_groups_per_pr.csv', dtype={'pr_id': str})
    per = per[per.group == GROUP][['pr_id'] + LEVELS]

    out = per.merge(lab, on='pr_id', how='left')
    unlabelled = int(out['type'].isna().sum())
    out['group'] = GROUP
    out['total'] = out[LEVELS].sum(axis=1)
    out = out[BASE_COLS].sort_values('pr_id').reset_index(drop=True)

    dropped = sorted(set(lab.pr_id) - set(out.pr_id))
    print(f'labelled PRs {len(lab)} -> with constructs now {len(out)} '
          f'(dropped {len(dropped)}, unlabelled {unlabelled})')
    if unlabelled:
        raise SystemExit('some pre-ChatGPT PRs have no label -- the labelled table is stale')
    if out.pr_id.duplicated().any():
        raise SystemExit('duplicate pr_id')
    out.to_csv(OUT, index=False)
    print(f'wrote {OUT}')


if __name__ == '__main__':
    main()
