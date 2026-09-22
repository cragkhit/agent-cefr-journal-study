#!/usr/bin/env python3
"""
cpet_artifacts.py

Shared by analyze_rq1_new_tool.py and analyze_rq2_three_groups.py: turns CPET's per-file
output rows into (PR, commit, file) groups ready for the Sec 4.2 before/after differencing.

Two corrections over parsing the artifact filename alone (applied 2026-09-22):

1. Files are identified by their full repository path, not their basename.
   An artifact filename carries only the basename (owner__repo__pr<ID>__<ts>__<sha>__
   <basename>_<variant>), so two different files with the same basename in one commit --
   e.g. two `_client.py` in a monorepo -- used to collide: one silently overwrote the other,
   and the `after` of one file could be differenced against the `before` of another. The
   full path is recovered from the fetch summary, which lists both artifact names of every
   fetched file next to its `path`. Every CPET artifact maps to exactly one fetch-summary
   row. A few artifact names (8 agent, 124 human, 6 pre-ChatGPT) stand for two different
   paths -- same basename, fetched in the same second, so one file overwrote the other on
   disk; which file CPET saw cannot be told, so both are excluded.

2. Merge commits are excluded.
   Commit collection took every commit listed on a PR, including merge commits such as
   "Merge branch 'main' into feature". A merge commit's diff is upstream code pulled into
   the branch, not code the PR author wrote. A commit is a merge iff it has more than one
   parent; parent counts come from data/commit_parents.csv (fetch_commit_parents.py).

A (PR, commit, file) group that ends up with only one of before/after is dropped rather
than counted whole: counting a modified file's whole snapshot is exactly the error the
differencing exists to avoid.
"""

import ast
import collections
import os
import re

import pandas as pd

VARIANTS = ('before', 'after', 'new')


def _stem(p):
    b = re.split(r'[\\/]', str(p))[-1]
    return b[:-3] if b.endswith('.py') else b


def _variant(stem):
    low = stem.lower()
    for v in VARIANTS:
        if low.endswith('_' + v):
            return v
    return 'new'


def load_index(summary_csv):
    """artifact name -> (owner, repo, pr_id, sha, path, variant); plus the ambiguous names."""
    fs = pd.read_csv(summary_csv, dtype=str)
    fs = fs[fs.status != 'fail']
    art = pd.concat([
        fs[['owner', 'repo', 'pr_id', 'sha', 'path', 'before_path']].rename(columns={'before_path': 'a'}),
        fs[['owner', 'repo', 'pr_id', 'sha', 'path', 'after_or_new_path']].rename(columns={'after_or_new_path': 'a'}),
    ]).dropna(subset=['a'])
    art['stem'] = art['a'].map(_stem)
    art = art.drop_duplicates(['stem', 'pr_id', 'sha', 'path'])
    n_paths = art.groupby('stem').path.nunique()
    ambiguous = set(n_paths[n_paths > 1].index)
    art = art[~art.stem.isin(ambiguous)]
    index = {r.stem: (r.owner, r.repo, r.pr_id, r.sha, r.path, _variant(r.stem))
             for r in art.itertuples()}
    return index, ambiguous


def load_merges(parents_csv):
    p = pd.read_csv(parents_csv, dtype={'sha': str})
    return set(p.loc[p['parents'].astype(int) > 1, 'sha'])


def build_groups(result_files, summary_csv, parents_csv, log, keep_merges=False):
    """Read CPET result CSVs -> {(owner, repo, pr_id, sha, path): {variant: Counter}}."""
    index, ambiguous = load_index(summary_csv)
    merges = set() if keep_merges else load_merges(parents_csv)
    groups = collections.defaultdict(dict)
    stats = collections.Counter()
    for f in result_files:
        try:
            d = pd.read_csv(f, usecols=['filename', 'code_type'])
        except Exception as e:
            log(f'  skip {os.path.basename(f)}: {e.__class__.__name__}')
            continue
        for name, ct in zip(d['filename'].astype(str), d['code_type']):
            stats['rows'] += 1
            if name in ambiguous:
                stats['ambiguous'] += 1
                continue
            k = index.get(name)
            if k is None:
                stats['unmapped'] += 1
                continue
            owner, repo, pr, sha, path, variant = k
            if sha in merges:
                stats['merge'] += 1
                continue
            try:
                lst = ast.literal_eval(ct) if isinstance(ct, str) else []
            except Exception:
                stats['bad_code_type'] += 1
                lst = []
            groups[(owner, repo, pr, sha, path)][variant] = collections.Counter(lst)
            stats['used'] += 1
    log(f'  artifact rows={stats["rows"]}  used={stats["used"]}  merge-commit={stats["merge"]}  '
        f'ambiguous-name={stats["ambiguous"]}  unmapped={stats["unmapped"]}  '
        f'unreadable code_type={stats["bad_code_type"]}')
    return groups


def difference(groups, mapping, log):
    """Sec 4.2: per-construct delta = max(after - before, 0), mapped to levels afterwards.
    Returns ({pr_id: Counter(level)}, {pr_id: 'owner/repo'})."""
    per_pr = collections.defaultdict(collections.Counter)
    pr_repo = {}
    n = collections.Counter()
    for (owner, repo, pr, sha, path), v in groups.items():
        if 'new' in v:
            delta = v['new']
            n['new'] += 1
        elif 'before' in v and 'after' in v:
            b, a = v['before'], v['after']
            delta = collections.Counter({k: a[k] - b.get(k, 0) for k in a if a[k] > b.get(k, 0)})
            n['pair'] += 1
        else:
            n['one_sided_dropped'] += 1
            continue
        pr_repo[pr] = f'{owner}/{repo}'
        for c, cnt in delta.items():
            lv = mapping.get(c)
            if lv:
                per_pr[pr][lv] += cnt
    log(f'  new files={n["new"]}  before/after pairs={n["pair"]}  '
        f'one-sided dropped={n["one_sided_dropped"]}  PRs with constructs={len(per_pr)}')
    return per_pr, pr_repo
