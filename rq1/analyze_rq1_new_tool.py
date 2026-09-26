#!/usr/bin/env python3
"""
RQ1 re-analysis using the new proficiency tool (codeProficiencyExtraction) instead of pycefr.

Input
-----
Per-repo result CSVs from cragkhit/agent-cefr-journal-study (data/output_by_repo/), one row
per analysed file:

    filename, code_snippet, code_type, count_A1 .. count_C2

`code_type` is a stringified list of every construct occurrence in that file; the count_*
columns are that file's per-level totals. Levels come from the tool's own rule in
load_construct_level_mapping(): the Index column of ubersequenceLevel.csv bucketed
1-20 A1, 21-40 A2, 41-60 B1, 61-80 B2, 81-100 C1, 101-118 C2.

Method
------
Replicates the MSR paper so the new numbers are comparable with the published ones:

  * Sec 4.2 differential - for a file with both before and after snapshots, count only
    constructs newly introduced: delta = max(after - before, 0) per construct, negatives
    clipped to zero. Files that are new in the PR are counted in full.
  * Constructs are mapped to levels AFTER differencing, matching pycefr's per
    (Level, Class) delta rather than differencing level totals (which would cancel out a
    construct swapped for another at the same level).
  * Agent identity is not present in the tool's output; it is joined by pr_id from
    aidev_all_commits.parquet. This closes the "Known gap" noted in the professor's README.
  * Sec 4.1 - only Copilot, Cursor and Devin are analysed.
  * Files are paired by full repository path and merge commits are excluded -- see
    cpet_artifacts.py for why (both corrected 2026-09-22).

Outputs
-------
  data/rq1_new_tool_by_agent.csv    Table 4 replacement
  data/rq1_new_tool_by_level.csv    overall distribution
  data/rq1_new_tool_per_pr.csv      per-PR level counts (input to the rank tests)
  log files/rq1_new_tool_<ts>.log

Usage:
    python analyze_rq1_new_tool.py --output-dir <path to data/output_by_repo>
"""

import argparse
import collections
import glob
import os
import sys
from datetime import datetime

import pandas as pd
from scipy.stats import chi2_contingency, kruskal

# The merge-exclusion and path-pairing helpers are shared with RQ2 and live in lib/.
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib'))
from cpet_artifacts import build_groups, difference  # noqa: E402

LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
COUNT_COLS = ['count_' + L for L in LEVELS]
AGENTS = ['Copilot', 'Cursor', 'Devin']


def log_factory(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'w', encoding='utf-8').write(f'=== rq1_new_tool {datetime.now().isoformat()} ===\n')

    def log(m):
        line = f'[{datetime.now().strftime("%H:%M:%S")}] {m}'
        print(line, flush=True)
        with open(path, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    return log


def load_mapping(path, log):
    d = pd.read_csv(path)
    m = {}
    for _, r in d.iterrows():
        i = r['Index']
        lvl = (0 if 1 <= i <= 20 else 1 if 21 <= i <= 40 else 2 if 41 <= i <= 60 else
               3 if 61 <= i <= 80 else 4 if 81 <= i <= 100 else 5 if 101 <= i <= 118 else 0)
        m[r['Construct']] = LEVELS[lvl]
    log(f'construct->level mapping: {len(m)} constructs')
    log('  per level: ' + str(collections.Counter(m.values())))
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output-dir', required=True)
    ap.add_argument('--mapping', required=True)
    ap.add_argument('--commits', default='aidev_all_commits.parquet')
    ap.add_argument('--fetch-summary', default=None,
                    help='default: ai_fetch_summary.csv next to --output-dir')
    ap.add_argument('--parents', default='data/commit_parents.csv')
    ap.add_argument('--keep-merges', action='store_true',
                    help='reproduce the pre-2026-09-22 numbers (merge commits included)')
    args = ap.parse_args()

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    log = log_factory(os.path.join('log files', f'rq1_new_tool_{ts}.log'))

    mapping = load_mapping(args.mapping, log)

    files = sorted(glob.glob(os.path.join(args.output_dir, '*.csv')) + glob.glob(os.path.join(args.output_dir, '*.csv.gz')))
    files = [f for f in files if 'run_log' not in os.path.basename(f)]
    log(f'repo result CSVs: {len(files)}')
    summary = args.fetch_summary or os.path.join(os.path.dirname(os.path.normpath(args.output_dir)),
                                                 'ai_fetch_summary.csv')
    groups = build_groups(files, summary, args.parents, log, keep_merges=args.keep_merges)
    log(f'(pr, commit, file) groups: {len(groups)}')

    # ---- Sec 4.2 differential, per construct -----------------------------------
    per_pr, _ = difference(groups, mapping, log)

    df = pd.DataFrame([{'pr_id': p, **{L: c.get(L, 0) for L in LEVELS}}
                       for p, c in per_pr.items()])
    log(f'PRs with constructs: {len(df)}')

    # ---- join agent identity (the gap in the professor's data) ------------------
    cm = pd.read_parquet(args.commits, columns=['pr_id', 'agent'])
    cm['pr_id'] = cm['pr_id'].astype(str)
    amap = dict(cm.drop_duplicates('pr_id').values)
    df['agent'] = df.pr_id.map(amap).fillna('Unknown')
    log('agent join: ' + str(df.agent.value_counts().to_dict()))

    df.to_csv('data/rq1_new_tool_per_pr.csv', index=False)

    sub = df[df.agent.isin(AGENTS)].copy()
    log(f'PRs from the three analysed agents: {len(sub)}')

    # ---- Table 4 ---------------------------------------------------------------
    def pct_row(counts):
        t = sum(counts)
        return [f'{c:,} ({c / t * 100:.2f}%)' if t else '0 (0.00%)' for c in counts]

    overall = [int(sub[L].sum()) for L in LEVELS]
    rows = [{'Agent': 'All agents', **dict(zip(LEVELS, pct_row(overall))),
             'Total': f'{sum(overall):,}'}]
    raw = [{'agent': 'All agents', **{L: int(sub[L].sum()) for L in LEVELS},
            'total': int(sum(overall))}]
    for a in AGENTS:
        s = sub[sub.agent == a]
        c = [int(s[L].sum()) for L in LEVELS]
        rows.append({'Agent': a, **dict(zip(LEVELS, pct_row(c))), 'Total': f'{sum(c):,}'})
        raw.append({'agent': a, **{L: v for L, v in zip(LEVELS, c)}, 'total': int(sum(c))})

    t4 = pd.DataFrame(rows)
    pd.DataFrame(raw).to_csv('data/rq1_new_tool_by_agent.csv', index=False)
    pd.DataFrame([{'Level': L, 'count': v, 'percentage': round(v / sum(overall) * 100, 2)}
                  for L, v in zip(LEVELS, overall)]).to_csv('data/rq1_new_tool_by_level.csv', index=False)

    log('')
    log('=' * 74)
    log('TABLE 4 (new tool) - distribution of AI agents\' Python constructs by level')
    log('=' * 74)
    for line in t4.to_string(index=False).split('\n'):
        log(line)

    # ---- RQ1 statistics --------------------------------------------------------
    obs = [[int(sub[sub.agent == a][L].sum()) for L in LEVELS] for a in AGENTS]
    chi2, p, dof, _ = chi2_contingency(obs)
    n = sum(map(sum, obs))
    v = (chi2 / (n * (min(len(obs), len(LEVELS)) - 1))) ** .5
    log('')
    log(f'chi-square across agents : chi2={chi2:,.2f}  df={dof}  p={p:.3g}  Cramer V={v:.3f}')

    scores = {a: [] for a in AGENTS}
    for _, r in sub.iterrows():
        tot = sum(r[L] for L in LEVELS)
        if tot:
            scores[r['agent']].append(sum(i * r[L] for i, L in enumerate(LEVELS)) / tot)
    hs = [s for s in scores.values() if s]
    if len(hs) > 1:
        H, pk = kruskal(*hs)
        log(f'Kruskal-Wallis (ordinal) : H={H:,.2f}  p={pk:.3g}')
        for a in AGENTS:
            if scores[a]:
                log(f'   {a:8s} n={len(scores[a]):4d}  mean ordinal={sum(scores[a])/len(scores[a]):.3f}')

    log('')
    log('saved: data/rq1_new_tool_by_agent.csv, _by_level.csv, _per_pr.csv')


if __name__ == '__main__':
    main()
