#!/usr/bin/env python3
"""
Tables 5 and 6 (RQ1 by PR task type) and RQ3 (outlier PRs), using the new proficiency
tool's results instead of pycefr.

Input is data/rq1_new_tool_per_pr.csv, written by analyze_rq1_new_tool.py: one row per PR
with A1..C2 counts already differenced per Sec 4.2 and the agent joined on.

PR task types are not present in the tool's output (the same gap as agent identity), so
they are joined from AIDev's pr_task_type.parquet by pr_id - the same source the published
tables used.

Outputs
-------
  data/rq1_new_tool_by_pr_type.csv    Table 5 replacement
  data/rq1_new_tool_residuals.csv     Table 6 replacement
  data/rq3_new_tool_outliers.csv      outlier PRs with task type
  data/rq3_new_tool_task_summary.csv  RQ3 task breakdown
  log files/rq3_new_tool_<ts>.log
"""

import os
from datetime import datetime

import pandas as pd
from scipy.stats import chi2_contingency

LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
# Pinned to the last AIDev v3 revision (2026-05-10). On 2026-08-21 upstream promoted v4
# to main, which deleted pr_task_type / human_pr_task_type / human_pull_request and
# replaced pull_request with a much larger table. Every number in the paper is v3.
PARQUET = 'hf://datasets/hao-li/AIDev@68ed5f4b80/pr_task_type.parquet'


def log_factory(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'w', encoding='utf-8').write(f'=== rq3_new_tool {datetime.now().isoformat()} ===\n')

    def log(m):
        line = f'[{datetime.now().strftime("%H:%M:%S")}] {m}'
        print(line, flush=True)
        with open(path, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    return log


def main():
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    log = log_factory(os.path.join('log files', f'rq3_new_tool_{ts}.log'))

    df = pd.read_csv('data/rq1_new_tool_per_pr.csv')
    df['pr_id'] = df.pr_id.astype(str)
    log(f'PRs from RQ1 stage: {len(df)}')

    tt = pd.read_parquet(PARQUET)
    idcol = 'id' if 'id' in tt.columns else tt.columns[0]
    tt[idcol] = tt[idcol].astype(str)
    df = df.merge(tt[[idcol, 'type']], left_on='pr_id', right_on=idcol, how='left').drop(columns=[idcol])
    unl = df.type.isna().sum()
    df['type'] = df.type.fillna('unlabelled')
    log(f'task types joined; {unl} PRs without a label')

    # ---------------- Table 5 ----------------
    by = df.groupby('type')[LEVELS].sum()
    by['total'] = by.sum(axis=1)
    by = by[by.total > 0].sort_values('total', ascending=False)
    rows = []
    for t, r in by.iterrows():
        rows.append({'type': t, **{L: int(r[L]) for L in LEVELS}, 'total': int(r['total']),
                     **{L + '_pct': round(r[L] / r['total'] * 100, 2) for L in LEVELS}})
    t5 = pd.DataFrame(rows)
    t5.to_csv('data/rq1_new_tool_by_pr_type.csv', index=False)

    log('')
    log('=' * 78)
    log('TABLE 5 (new tool) - constructs by PR task type')
    log('=' * 78)
    log(f'{"type":<10}' + ''.join(f'{L:>16}' for L in LEVELS) + f'{"total":>10}')
    for _, r in t5.iterrows():
        log(f'{r["type"]:<10}' +
            ''.join(f'{r[L]:>9,} ({r[L + "_pct"]:>4.1f}%)' for L in LEVELS) +
            f'{r["total"]:>10,}')

    # ---------------- Table 6 : standardized residuals ----------------
    obs = by[LEVELS].values
    chi2, p, dof, exp = chi2_contingency(obs)
    n = obs.sum()
    k = min(obs.shape) - 1
    V = (chi2 / (n * k)) ** .5
    resid = (obs - exp) / (exp ** .5)
    rdf = pd.DataFrame(resid, index=by.index, columns=LEVELS).round(2)
    rdf.to_csv('data/rq1_new_tool_residuals.csv')

    log('')
    log(f'chi-square task type x level: chi2={chi2:,.2f}  df={dof}  p={p:.3g}  Cramer V={V:.3f}')
    log('')
    log('TABLE 6 (new tool) - standardized Pearson residuals  (|r| >= 2 is meaningful)')
    log(f'{"type":<10}' + ''.join(f'{L:>9}' for L in LEVELS))
    for t, r in rdf.iterrows():
        log(f'{t:<10}' + ''.join(f'{r[L]:>9.2f}' for L in LEVELS))

    # ---------------- RQ3 : outliers ----------------
    df['C1+C2'] = df.C1 + df.C2
    q1, q3 = df['C1+C2'].quantile(.25), df['C1+C2'].quantile(.75)
    iqr = q3 - q1
    ub = q3 + 1.5 * iqr
    out = df[df['C1+C2'] > ub].copy().sort_values('C1+C2', ascending=False)
    log('')
    log('=' * 78)
    log('RQ3 (new tool) - PRs with unusually many proficient constructs')
    log('=' * 78)
    log(f'Q1={q1}  Q3={q3}  IQR={iqr}  upper bound = Q3 + 1.5*IQR = {ub}')
    log(f'outlier PRs: {len(out)} of {len(df)}')
    if len(out):
        s = out['C1+C2']
        log(f'C1+C2 range {int(s.min())}-{int(s.max())}, median {s.median():.0f}, mean {s.mean():.2f}')
    out.to_csv('data/rq3_new_tool_outliers.csv', index=False)

    g = (out.groupby('type')['C1+C2']
         .agg(prs='size', constructs='sum', avg='mean')
         .sort_values('constructs', ascending=False))
    g['avg'] = g['avg'].round(2)
    g.to_csv('data/rq3_new_tool_task_summary.csv')
    log('')
    log('RQ3 task breakdown of the outliers:')
    log(f'{"type":<12}{"PRs":>6}{"C1+C2":>10}{"avg/PR":>10}')
    for t, r in g.iterrows():
        log(f'{t:<12}{int(r.prs):>6}{int(r.constructs):>10,}{r.avg:>10.2f}')
    log(f'covered {int(g.prs.sum())} of {len(out)} outlier PRs')

    log('')
    log('saved: data/rq1_new_tool_by_pr_type.csv, _residuals.csv,')
    log('       data/rq3_new_tool_outliers.csv, _task_summary.csv')


if __name__ == '__main__':
    main()
