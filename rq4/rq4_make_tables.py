#!/usr/bin/env python3
"""
make_rq4_tables.py

Add the RQ4 review-effort columns to the three per-group PR tables, and compute the
independent variables the RQ4 proposal names.

Run fetch_rq4_review_data.py first -- this consumes rq4_pr_review_metrics.csv.

The three rq3_*.csv tables are extended in place, so each group stays one table:
  rq3_agent_prs_with_task_type.csv
  rq3_human_prs_with_task_type.csv
  rq3_pre_chatgpt_prs_with_task_type.csv   (Chaiyong's GPT-4.1-mini labels)

Independent variables (RQs_proposals.md, "Method"):
  c1c2            C1 + C2 construct count
  c1c2_pct        C1 + C2 as a share of the PR's constructs
  cefr_mean       ordinal CEFR mean, A1=1 .. C2=6 -- the same measure used for the
                  repository-paired Wilcoxon test in RQ2

Dependent variables and controls come from the fetch. Every count is split human/bot:
bots produce 41% of reviews and 70% of comments on agent PRs, so unfiltered counts
would drown the signal.
"""

import os

import pandas as pd

LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
WEIGHT = {'A1': 1, 'A2': 2, 'B1': 3, 'B2': 4, 'C1': 5, 'C2': 6}

# Resolved from this file's location so the script runs correctly from anywhere.
DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')

FILES = {
    'AI agents':           os.path.join(DATA, 'rq3_agent_prs_with_task_type.csv'),
    'Human':               os.path.join(DATA, 'rq3_human_prs_with_task_type.csv'),
    'Human (pre-ChatGPT)': os.path.join(DATA, 'rq3_pre_chatgpt_prs_with_task_type.csv'),
}

REVIEW_COLS = [
    # size controls -- the confound the proposal says decides whether reviewers believe it
    'additions', 'deletions', 'changed_files', 'n_commits',
    # dependent variables
    'n_issue_comments', 'n_review_comments',
    'n_reviews_total', 'n_reviews_human', 'n_reviews_bot',
    'n_reviewers_human', 'n_reviewers_bot',
    'n_approved', 'n_changes_requested', 'n_commented', 'any_changes_requested',
    'first_review_latency_h', 'first_review_latency_any_h',
    # secondary outcome -- the original RQ4; kept because it is free from the same response
    'time_to_merge_h',
    # context
    'pr_state', 'merged', 'draft', 'author_association',
    'pr_created_at', 'pr_merged_at', 'full_name', 'number', 'status',
]


def add_ivs(d):
    total = d[LEVELS].sum(axis=1)
    d['constructs_total'] = total
    d['c1c2'] = d['C1'] + d['C2']
    d['c1c2_pct'] = (d['c1c2'] / total.replace(0, pd.NA) * 100).round(4)
    weighted = sum(d[l] * WEIGHT[l] for l in LEVELS)
    d['cefr_mean'] = (weighted / total.replace(0, pd.NA)).round(4)
    return d


def main():
    rv = pd.read_csv(os.path.join(DATA, 'rq4_pr_review_metrics.csv'), dtype={'pr_id': str})
    rv = rv[['pr_id'] + [c for c in REVIEW_COLS if c in rv.columns]]
    print(f'review metrics: {len(rv)} PRs')

    summary = []
    for group, path in FILES.items():
        d = pd.read_csv(path, dtype={'pr_id': str})
        before = list(d.columns)

        # drop any previously added columns so a re-run is idempotent
        d = d[[c for c in d.columns if c not in rv.columns or c == 'pr_id']]
        d = d.drop(columns=[c for c in ['constructs_total', 'c1c2', 'c1c2_pct', 'cefr_mean']
                            if c in d.columns])

        d = add_ivs(d)
        d = d.merge(rv, on='pr_id', how='left')

        missing = int(d['status'].isna().sum()) if 'status' in d else len(d)
        failed = int((d['status'] != 'ok').sum()) if 'status' in d else len(d)
        d.to_csv(path, index=False)
        print(f'{group:22s} {len(d):4d} rows, {len(before)} -> {len(d.columns)} cols, '
              f'{missing} unmatched, {failed} not fetched ok')
        summary.append((group, d))

    print('\n=== RQ4 headline distributions (fetched ok only) ===')
    for group, d in summary:
        g = d[d.status == 'ok'] if 'status' in d else d
        if not len(g):
            print(f'{group}: nothing fetched')
            continue
        hr = g.n_reviews_human.fillna(0)
        hc = g.n_review_comments.fillna(0) + g.n_issue_comments.fillna(0)
        print(f'\n{group}  n={len(g)}')
        print(f'   human reviews   zero={int((hr==0).sum()):4d} ({(hr==0).mean()*100:5.1f}%)  '
              f'median={hr.median():4.1f}  mean={hr.mean():5.2f}  max={int(hr.max())}')
        print(f'   comments        zero={int((hc==0).sum()):4d} ({(hc==0).mean()*100:5.1f}%)  '
              f'median={hc.median():4.1f}  mean={hc.mean():5.2f}  max={int(hc.max())}')
        print(f'   changes req.    {int(g.any_changes_requested.fillna(0).sum())} PRs '
              f'({g.any_changes_requested.fillna(0).mean()*100:.1f}%)')
        print(f'   additions       median={g.additions.median():.0f}  '
              f'cefr_mean median={g.cefr_mean.median():.3f}  c1c2 median={g.c1c2.median():.0f}')

    # the raw correlation, before any size control -- reported so the confound is visible
    print('\n=== raw Spearman vs review effort (NOT size-controlled) ===')
    try:
        from scipy.stats import spearmanr
        for group, d in summary:
            g = d[(d.status == 'ok')].dropna(subset=['cefr_mean', 'additions'])
            if len(g) < 20:
                continue
            hc = g.n_review_comments.fillna(0) + g.n_issue_comments.fillna(0)
            print(f'\n{group}  n={len(g)}')
            for nm, x in [('cefr_mean', g.cefr_mean), ('c1c2', g.c1c2),
                          ('additions', g.additions)]:
                r1, p1 = spearmanr(x, hc)
                r2, p2 = spearmanr(x, g.n_reviews_human.fillna(0))
                print(f'   {nm:10s} vs comments rho={r1:+.3f} p={p1:.4f}   '
                      f'vs human reviews rho={r2:+.3f} p={p2:.4f}')
    except ImportError:
        print('  scipy not available, skipped')


if __name__ == '__main__':
    main()
