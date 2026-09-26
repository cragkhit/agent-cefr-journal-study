import itertools
import pandas as pd
from scipy.stats import chi2_contingency, mannwhitneyu, kruskal

D = 'data/'   # run from the repository root
L = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
GROUPS = ['AI agents', 'Human', 'Human (pre-ChatGPT)']

per = pd.read_csv(D + 'rq2_three_groups_per_pr.csv')
per['pr_id'] = per.pr_id.astype(str)

agg = pd.read_csv(D + 'rq2_three_groups_all.csv')
print('=== group sizes (all repos) ===')
for _, r in agg.iterrows():
    print(f"  {r['group']:22s} PRs={int(r['prs']):4d}  repos={int(r['repos']):4d}  "
          f"constructs={int(r['total']):,}")

print()
print('=== pairwise chi-square (2 x 6) ===')
for a, b in itertools.combinations(GROUPS, 2):
    ra = agg[agg.group == a].iloc[0]
    rb = agg[agg.group == b].iloc[0]
    obs = [[int(ra[l]) for l in L], [int(rb[l]) for l in L]]
    chi2, p, dof, _ = chi2_contingency(obs)
    n = sum(map(sum, obs))
    V = (chi2 / (n * 1)) ** .5
    print(f'  {a:22s} vs {b:22s} chi2={chi2:9,.2f}  df={dof}  p={p:.3g}  V={V:.3f}')

print()
print('=== per-PR ordinal score: Mann-Whitney pairwise ===')


def scores(g):
    s = per[per.group == g]
    out = []
    for _, r in s.iterrows():
        tot = sum(r[l] for l in L)
        if tot:
            out.append(sum(i * r[l] for i, l in enumerate(L)) / tot)
    return out


sc = {g: scores(g) for g in GROUPS}
for g in GROUPS:
    v = sc[g]
    print(f'  {g:22s} n={len(v):4d}  mean={sum(v)/len(v):.3f}  '
          f'median={pd.Series(v).median():.3f}')
print()
for a, b in itertools.combinations(GROUPS, 2):
    U, p = mannwhitneyu(sc[a], sc[b], alternative='two-sided')
    n1, n2 = len(sc[a]), len(sc[b])
    r = 1 - (2 * U) / (n1 * n2)          # rank-biserial
    print(f'  {a:22s} vs {b:22s} U={U:>10,.0f}  p={p:.3f}  rank-biserial r={r:+.3f}')

H, p = kruskal(*[sc[g] for g in GROUPS])
print()
print(f'  Kruskal-Wallis across all three: H={H:.2f}, p={p:.3f}')

print()
print('=== repository-paired comparison (repos common to all three) ===')
sets = [set(per[per.group == g].repo) for g in GROUPS]
common = set.intersection(*sets)
print(f'  common repos: {len(common)}')
rows = []
for repo in sorted(common):
    e = {'repo': repo}
    for g in GROUPS:
        s = per[(per.group == g) & (per.repo == repo)]
        tot = sum(s[l].sum() for l in L)
        e[g] = (sum(i * s[l].sum() for i, l in enumerate(L)) / tot) if tot else None
    rows.append(e)
pr = pd.DataFrame(rows).dropna()
print(f'  repos with data in all three: {len(pr)}')
print()
print(pr.round(3).to_string(index=False))
from scipy.stats import wilcoxon
print()
for a, b in itertools.combinations(GROUPS, 2):
    try:
        W, p = wilcoxon(pr[a], pr[b])
        med = (pr[a] - pr[b]).median()
        print(f'  {a:22s} vs {b:22s} W={W:6.1f}  p={p:.3f}  median diff={med:+.3f}')
    except Exception as e:
        print(f'  {a} vs {b}: {e}')
