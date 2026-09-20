#!/usr/bin/env python3
"""
make_rq3_task_type_export.py

Export the three RQ3 comparison groups with PR task types attached, for Chaiyong's
RQ3 plots.

Background
----------
AIDev publishes PR task-type labels in TWO tables, one per population:
  pr_task_type.parquet        agent PRs       (33,596 rows, confidence 3-10)
  human_pr_task_type.parquet  human PRs       (6,618 rows, confidence all NULL)
Both use the same Conventional-Commit taxonomy, auto-classified by LLM.

So the agent and human groups both get their labels straight from AIDev. Only the
pre-ChatGPT group has no upstream labels -- those PRs predate the AIDev sample entirely
-- so it ships with titles only and gets labelled via data/rq3_labelling_prompt.md.

Note: AIDev never populated `confidence` for the human table, so that column is empty
for the human group. `type` and `reason` are both present.

Outputs (all keyed on pr_id, same column layout so they can be concatenated)
---------------------------------------------------------------------------
  data/rq3_agent_prs_with_task_type.csv      491 rows, type/confidence/reason filled
  data/rq3_human_prs_with_task_type.csv      513 rows, type/reason filled
  (pre-ChatGPT titles come from fetch_pre_chatgpt_titles.py, which needs the API)
"""

import os
import pandas as pd

LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
COLS = ['group', 'pr_id', 'repo', 'agent', 'html_url', 'title', 'body',
        'type', 'confidence', 'reason'] + LEVELS + ['total']

# Agent identity is not in CPET's output; it is joined by pr_id from the RQ1 stage.
# Every AIDev PR has exactly one agent (0 of 7,104 PRs mix agents at commit level),
# so PR-level and commit-level classification are the same thing.
AGENT_BY_PR = 'data/rq1_new_tool_per_pr.csv'

# AIDev's maintainers promoted "v4 (AIDev-2.7M, cutoff Nov 2025)" to main on
# 2026-08-21, which DROPPED pr_task_type.parquet, human_pr_task_type.parquet and
# human_pull_request.parquet and replaced pull_request.parquet with a much larger
# table. Every RQ1-RQ3 number in the paper comes from the previous revision, so the
# paths below are pinned to it. Do not unpin without re-deriving the whole paper.
AIDEV_REV = '68ed5f4b80'   # last v3 revision, 2026-05-10
BASE = f'hf://datasets/hao-li/AIDev@{AIDEV_REV}/'

TASK_TYPE = BASE + 'pr_task_type.parquet'
AGENT_PRS = BASE + 'pull_request.parquet'
HUMAN_TASK_TYPE = BASE + 'human_pr_task_type.parquet'


def shape(df):
    """Force the shared column layout, filling anything missing with blanks."""
    for c in COLS:
        if c not in df.columns:
            df[c] = ''
    df['total'] = df[LEVELS].sum(axis=1)
    return df[COLS].sort_values('pr_id').reset_index(drop=True)


def main():
    per = pd.read_csv('data/rq2_three_groups_per_pr.csv', dtype={'pr_id': str})
    print(f'RQ2 per-PR rows: {len(per)}')
    print(per.groupby('group').size().to_string())

    # ---------------- AI agents: task types already exist ----------------
    ai = per[per.group == 'AI agents'].copy()
    tt = pd.read_parquet(TASK_TYPE, columns=['id', 'title', 'type', 'confidence', 'reason'])
    tt['id'] = tt['id'].astype(str)
    ai = ai.merge(tt, left_on='pr_id', right_on='id', how='left').drop(columns=['id'])

    urls = pd.read_parquet(AGENT_PRS, columns=['id', 'html_url', 'body'])
    urls['id'] = urls['id'].astype(str)
    ai = ai.merge(urls, left_on='pr_id', right_on='id', how='left').drop(columns=['id'])

    ag = pd.read_csv(AGENT_BY_PR, dtype={'pr_id': str})[['pr_id', 'agent']]
    ai = ai.merge(ag, on='pr_id', how='left')

    missing = ai['type'].isna().sum()
    print(f'\nAI agents: {len(ai)} rows, {missing} without a task type, '
          f'{ai["agent"].isna().sum()} without an agent')
    ai = shape(ai)
    ai.to_csv('data/rq3_agent_prs_with_task_type.csv', index=False)

    # ---------------- Human: labels come from AIDev's human table ----------------
    hu = per[per.group == 'Human'].copy()
    ht = pd.read_parquet(HUMAN_TASK_TYPE, columns=['id', 'title', 'type', 'confidence', 'reason'])
    ht['id'] = ht['id'].astype(str)
    hu = hu.merge(ht, left_on='pr_id', right_on='id', how='left').drop(columns=['id'])

    urls_h = pd.read_parquet('human_pull_request.parquet', columns=['id', 'html_url', 'body'])
    urls_h['id'] = urls_h['id'].astype(str)
    hu = hu.merge(urls_h, left_on='pr_id', right_on='id', how='left').drop(columns=['id'])

    print(f'Human: {len(hu)} rows, {hu["type"].isna().sum()} without a task type')
    hu = shape(hu)
    hu.to_csv('data/rq3_human_prs_with_task_type.csv', index=False)

    # ---------------- Sanity checks ----------------
    print('\n=== sanity ===')
    ok = True
    for name, df, n in [('agent', ai, 491), ('human', hu, 513)]:
        if len(df) != n:
            print(f'  FAIL {name}: expected {n} rows, got {len(df)}'); ok = False
        if df['title'].astype(str).str.strip().eq('').any() or df['title'].isna().any():
            print(f'  FAIL {name}: blank titles present'); ok = False
        if df['pr_id'].duplicated().any():
            print(f'  FAIL {name}: duplicate pr_id'); ok = False
    for name, df in [('agent', ai), ('human', hu)]:
        if df['type'].astype(str).str.strip().eq('').any():
            print(f'  FAIL {name}: unlabelled task types'); ok = False
    print('  all checks passed' if ok else '  SEE FAILURES ABOVE')

    for name, df in [('Agent', ai), ('Human', hu)]:
        print(f'\n{name} task-type distribution:')
        print(df['type'].value_counts().to_string())

    # Empty bodies are legitimate - plenty of PRs ship with no description.
    print('')
    print('PR body coverage:')
    for name, df in [('Agent', ai), ('Human', hu)]:
        b = df['body'].fillna('').astype(str)
        empty = int(b.str.strip().eq('').sum())
        print(f'  {name}: {empty} empty of {len(b)}, '
              f'median {int(b.str.len().median())} chars, max {int(b.str.len().max())}')


if __name__ == '__main__':
    main()
