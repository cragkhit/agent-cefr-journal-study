#!/usr/bin/env python3
"""
Table 7 (RQ2) with the new proficiency tool, for three comparison groups:

    AI agents             data/output_by_repo
    Human                 data/output_by_repo_human            (2025 PRs, AIDev)
    Human (pre-ChatGPT)   data/output_by_repo_pre_chatgpt      (PRs merged before 2022-11-30)

Method is identical to analyze_rq1_new_tool.py so the three rows are comparable:
per-construct Sec 4.2 differencing (delta = max(after - before, 0)) applied BEFORE
mapping constructs to levels, using the tool's own Index-bucket rule.

Two scopes are reported:
  * all repos in each group
  * repos common to all three groups, which is the like-for-like comparison and the
    analogue of the paper's "same projects" restriction for RQ2

Outputs
-------
  data/rq2_three_groups_all.csv
  data/rq2_three_groups_common.csv
  data/rq2_three_groups_per_pr.csv
  log files/rq2_three_groups_<ts>.log
"""

import argparse
import ast
import collections
import glob
import os
import re
from datetime import datetime

import pandas as pd
from scipy.stats import chi2_contingency, kruskal

LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
COUNT_COLS = ['count_' + L for L in LEVELS]

FN = re.compile(r'^(?P<owner>.+?)__(?P<repo>.+?)__pr(?P<pr>\d+)__(?P<ts>\d{8}_\d{6})__'
                r'(?P<sha>[0-9a-f]{7,40})__(?P<rest>.+)$')

GROUPS = [
    ('AI agents',           'output_by_repo'),
    ('Human',               'output_by_repo_human'),
    ('Human (pre-ChatGPT)', 'output_by_repo_pre_chatgpt'),
]


def log_factory(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'w', encoding='utf-8').write(f'=== rq2_three_groups {datetime.now().isoformat()} ===\n')

    def log(m):
        line = f'[{datetime.now().strftime("%H:%M:%S")}] {m}'
        print(line, flush=True)
        with open(path, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    return log


def load_mapping(path):
    d = pd.read_csv(path)
    m = {}
    for _, r in d.iterrows():
        i = r['Index']
        lvl = (0 if 1 <= i <= 20 else 1 if 21 <= i <= 40 else 2 if 41 <= i <= 60 else
               3 if 61 <= i <= 80 else 4 if 81 <= i <= 100 else 5 if 101 <= i <= 118 else 0)
        m[r['Construct']] = LEVELS[lvl]
    return m


def parse_fn(name):
    m = FN.match(name)
    if not m:
        return None
    rest = m.group('rest')
    low = rest.lower()
    if low.endswith('_before'):
        variant, base = 'before', rest[:-7]
    elif low.endswith('_after'):
        variant, base = 'after', rest[:-6]
    elif low.endswith('_new'):
        variant, base = 'new', rest[:-4]
    else:
        variant, base = 'new', rest
    return (m.group('owner'), m.group('repo'), m.group('pr'), m.group('sha'), base, variant)


def process(dirpath, mapping, log, label):
    files = [f for f in sorted(glob.glob(os.path.join(dirpath, '*.csv')) + glob.glob(os.path.join(dirpath, '*.csv.gz')))
             if 'run_log' not in os.path.basename(f)]
    groups, unparsed, nrows = collections.defaultdict(dict), 0, 0
    for f in files:
        try:
            d = pd.read_csv(f, usecols=['filename', 'code_type'] + COUNT_COLS)
        except Exception:
            continue
        for _, r in d.iterrows():
            nrows += 1
            info = parse_fn(str(r['filename']))
            if not info:
                unparsed += 1
                continue
            owner, repo, pr, sha, base, variant = info
            try:
                lst = ast.literal_eval(r['code_type']) if isinstance(r['code_type'], str) else []
            except Exception:
                lst = []
            groups[(owner, repo, pr, sha, base)][variant] = collections.Counter(lst)

    rows, n_new, n_pair, n_one = [], 0, 0, 0
    per_pr = collections.defaultdict(lambda: collections.Counter())
    pr_repo = {}
    for (owner, repo, pr, sha, base), v in groups.items():
        if 'new' in v:
            delta, n_new = v['new'], n_new + 1
        elif 'before' in v and 'after' in v:
            b, a = v['before'], v['after']
            delta = collections.Counter()
            for k in set(a) | set(b):
                dd = a.get(k, 0) - b.get(k, 0)
                if dd > 0:
                    delta[k] = dd
            n_pair += 1
        else:
            delta, n_one = next(iter(v.values())), n_one + 1
        pr_repo[pr] = f'{owner}/{repo}'
        for c, n in delta.items():
            lv = mapping.get(c)
            if lv:
                per_pr[pr][lv] += n

    for pr, c in per_pr.items():
        rows.append({'group': label, 'pr_id': pr, 'repo': pr_repo[pr],
                     **{L: c.get(L, 0) for L in LEVELS}})
    df = pd.DataFrame(rows)
    log(f'{label:22s} repos={len(files):3d}  file rows={nrows:6d}  groups={len(groups):5d}  '
        f'new={n_new} pairs={n_pair} single={n_one}  PRs with constructs={len(df)}')
    if unparsed:
        log(f'{"":22s} unparsed filenames: {unparsed}')
    return df


def table(df_all, log, title):
    log('')
    log('=' * 78)
    log(title)
    log('=' * 78)
    log(f'{"":22s}' + ''.join(f'{L:>10}' for L in LEVELS) + f'{"total":>12}{"PRs":>7}{"repos":>7}')
    out = []
    for label, _ in GROUPS:
        s = df_all[df_all.group == label]
        if not len(s):
            continue
        c = [int(s[L].sum()) for L in LEVELS]
        t = sum(c)
        if not t:
            continue
        log(f'{label:22s}' + ''.join(f'{v / t * 100:9.2f}%' for v in c) +
            f'{t:>12,}{s.pr_id.nunique():>7}{s.repo.nunique():>7}')
        out.append({'group': label, **{L: v for L, v in zip(LEVELS, c)},
                    **{L + '_pct': round(v / t * 100, 2) for L, v in zip(LEVELS, c)},
                    'total': t, 'prs': int(s.pr_id.nunique()), 'repos': int(s.repo.nunique())})
    res = pd.DataFrame(out)

    obs = [[int(r[L]) for L in LEVELS] for _, r in res.iterrows()]
    if len(obs) > 1:
        chi2, p, dof, _ = chi2_contingency(obs)
        n = sum(map(sum, obs))
        V = (chi2 / (n * (min(len(obs), 6) - 1))) ** .5
        log('')
        log(f'chi-square across groups : chi2={chi2:,.2f}  df={dof}  p={p:.3g}  Cramer V={V:.3f}')

        scores = []
        for label, _ in GROUPS:
            s = df_all[df_all.group == label]
            vals = []
            for _, r in s.iterrows():
                tot = sum(r[L] for L in LEVELS)
                if tot:
                    vals.append(sum(i * r[L] for i, L in enumerate(LEVELS)) / tot)
            if vals:
                scores.append((label, vals))
        if len(scores) > 1:
            H, pk = kruskal(*[v for _, v in scores])
            log(f'Kruskal-Wallis (per-PR)  : H={H:,.2f}  p={pk:.3g}')
            for label, vals in scores:
                log(f'   {label:22s} n={len(vals):4d}  mean ordinal={sum(vals)/len(vals):.3f}')
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo-root', required=True, help='path to agent-cefr-journal-study')
    ap.add_argument('--mapping', default='data/ubersequenceLevel.csv')
    args = ap.parse_args()

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    log = log_factory(os.path.join('log files', f'rq2_three_groups_{ts}.log'))
    mapping = load_mapping(args.mapping)
    log(f'construct->level mapping: {len(mapping)} constructs')
    log('')

    frames = []
    for label, sub in GROUPS:
        d = os.path.join(args.repo_root, 'data', sub)
        if not os.path.isdir(d):
            log(f'MISSING {d}')
            continue
        frames.append(process(d, mapping, log, label))
    df = pd.concat(frames, ignore_index=True)
    df.to_csv('data/rq2_three_groups_per_pr.csv', index=False)

    res_all = table(df, log, 'TABLE 7 (new tool) - all repositories in each group')
    res_all.to_csv('data/rq2_three_groups_all.csv', index=False)

    sets = [set(df[df.group == g].repo) for g, _ in GROUPS if len(df[df.group == g])]
    common = set.intersection(*sets) if sets else set()
    log('')
    log(f'repositories common to all three groups: {len(common)}')
    if common:
        res_c = table(df[df.repo.isin(common)], log,
                      'TABLE 7 (new tool) - repositories common to all three groups')
        res_c.to_csv('data/rq2_three_groups_common.csv', index=False)

    log('')
    log('saved: data/rq2_three_groups_all.csv, _common.csv, _per_pr.csv')


if __name__ == '__main__':
    main()
