#!/usr/bin/env python3
"""
Figure: repository-paired mean ordinal CEFR score for the three comparison groups.

One row per repository present in all three groups; three markers per row. Rows are
sorted by the AI-agent score, so the AI series forms a monotone reference and the two
human series can be seen scattering around it with no consistent ordering - which is the
visual statement of the non-significant paired tests.

Markers differ by shape as well as colour so the figure survives greyscale printing.

Reads data/rq2_three_groups_per_pr.csv and writes figures/repo_paired_cefr.{pdf,png}.
"""

import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
GROUPS = [
    ('AI agents',           '#0069B4', 'o'),
    ('Human',               '#B4690E', 's'),
    ('Human (pre-ChatGPT)', '#1B7F5A', '^'),
]
OUT = 'figures'


def main():
    per = pd.read_csv('data/rq2_three_groups_per_pr.csv')
    sets = [set(per[per.group == g].repo) for g, _, _ in GROUPS]
    common = sorted(set.intersection(*sets))

    rows = []
    for repo in common:
        e = {'repo': repo}
        ok = True
        for g, _, _ in GROUPS:
            s = per[(per.group == g) & (per.repo == repo)]
            tot = sum(s[l].sum() for l in LEVELS)
            if not tot:
                ok = False
                break
            e[g] = sum(i * s[l].sum() for i, l in enumerate(LEVELS)) / tot
        if ok:
            rows.append(e)
    df = pd.DataFrame(rows).sort_values('AI agents').reset_index(drop=True)
    print(f'{len(df)} repositories present in all three groups')

    plt.rcParams.update({
        'font.family': 'serif',
        'font.serif': ['DejaVu Serif', 'Times New Roman', 'Liberation Serif'],
        'font.size': 9,
        'axes.linewidth': 0.6,
        'xtick.major.width': 0.6,
        'ytick.major.width': 0.0,
        'pdf.fonttype': 42,      # embed TrueType, not Type 3 - ACM requires this
        'ps.fonttype': 42,
    })

    fig, ax = plt.subplots(figsize=(6.4, 3.5))
    y = range(len(df))

    # connector per repository, so the three markers read as one observation
    for i, r in df.iterrows():
        vals = [r[g] for g, _, _ in GROUPS]
        ax.plot([min(vals), max(vals)], [i, i], color='0.75', lw=0.8, zorder=1)

    for g, colour, marker in GROUPS:
        ax.scatter(df[g], y, s=34, marker=marker, color=colour, label=g,
                   zorder=3, edgecolors='white', linewidths=0.6)

    ax.set_yticks(list(y))
    ax.set_yticklabels(df.repo, fontsize=8)
    ax.set_xlabel('Mean ordinal CEFR score  (A1 = 0 … C2 = 5)')
    ax.set_xlim(0.35, 1.40)
    ax.grid(axis='x', color='0.9', lw=0.5, zorder=0)
    ax.set_axisbelow(True)
    for side in ('top', 'right', 'left'):
        ax.spines[side].set_visible(False)
    ax.tick_params(axis='y', length=0)
    ax.invert_yaxis()

    ax.legend(loc='lower center', bbox_to_anchor=(0.5, 1.01), ncol=3,
              frameon=False, fontsize=8, handletextpad=0.3, columnspacing=1.6)

    fig.tight_layout()
    os.makedirs(OUT, exist_ok=True)
    for ext in ('pdf', 'png'):
        p = os.path.join(OUT, f'repo_paired_cefr.{ext}')
        fig.savefig(p, dpi=300, bbox_inches='tight')
        print('wrote', p, f'({os.path.getsize(p)/1024:.0f} KB)')


if __name__ == '__main__':
    main()
