#!/usr/bin/env python3
"""
make_fig_task_type_agent.py

Regenerate Figures 3 and 4 (CEFR distribution per PR task type x agent) from CPET data.

The versions in the paper were drawn from the pycefr-era notebook
(notebooks/2026-MSR-AIDevCEFR-Journal_Faceted_Barcharts.ipynb) and still show A2
dominating -- e.g. feat|Copilot A1 31.8 / A2 58.6. CPET inverts that: A1 65.4 / A2 13.4.

Paths are resolved relative to the repository root (the parent of this script's folder),
so the script can be run from anywhere.

Input   analysis/rq3_agent_prs_with_task_type.csv   (agent, type, A1..C2 per PR)
Output  cefr_top5_task_types.{pdf,png}        Fig 3: feat, fix, refactor, build, chore
        cefr_remaining_task_types.{pdf,png}   Fig 4: test, docs, ci, perf, other
        (written to the repository root, where paper.tex includes them by filename)

Percentages are construct shares within each (task type, agent) facet, so every facet
sums to 100. Layout, grayscale palette, hatches and value labels follow the notebook.
"""

import os
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'analysis', 'rq3_agent_prs_with_task_type.csv')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
HATCH = dict(zip(LEVELS, ['/', '\\', '|', '-', '+', 'x']))
# Light grayscale ramp: dark enough at A1 to read as a gradient, light enough that the
# black hatches and value labels stay legible on every bar.
GRAYS = dict(zip(LEVELS, ['#7a7a7a', '#939393', '#adadad', '#c6c6c6', '#dedede', '#f4f4f4']))
AGENTS = ['Copilot', 'Devin', 'Cursor']          # column order used in the paper

FIGS = {
    'cefr_top5_task_types':      ['feat', 'fix', 'refactor', 'build', 'chore'],
    'cefr_remaining_task_types': ['test', 'docs', 'ci', 'perf', 'other'],
}


def facet_table(df):
    """Construct counts and percentages per (type, agent)."""
    g = df.groupby(['type', 'agent'])[LEVELS].sum()
    pct = g.div(g.sum(axis=1), axis=0) * 100
    n_prs = df.groupby(['type', 'agent']).size()
    return g, pct, n_prs


def draw(pct, n_prs, types, out_stem):
    nrow, ncol = len(types), len(AGENTS)
    fig, axes = plt.subplots(nrow, ncol, figsize=(3.0 * ncol, 2.5 * nrow),
                             sharex=True, sharey=True, squeeze=False)
    x = range(len(LEVELS))

    # Shared y-axis, so the ceiling must clear the tallest bar in THIS figure plus its
    # label. A fixed 75 clipped docs|Cursor (1 PR, 2 constructs -> B1 100%) in Fig 4.
    present = [(t, a) for t in types for a in AGENTS if (t, a) in pct.index]
    ymax = max(pct.loc[k, LEVELS].max() for k in present) if present else 100
    ytop = min(112, ymax + 12)

    for r, t in enumerate(types):
        for c, a in enumerate(AGENTS):
            ax = axes[r][c]
            ax.set_title(f'{t} | {a}', fontsize=14)
            ax.set_ylim(0, ytop)
            ax.set_xticks(list(x))
            ax.set_xticklabels(LEVELS, rotation=45, fontsize=12)
            ax.tick_params(axis='y', labelsize=12)
            if c == 0:
                ax.set_ylabel('Percentage', fontsize=12)
            if r == nrow - 1:
                ax.set_xlabel('CEFR Level', fontsize=12)

            if (t, a) not in pct.index:
                continue                      # facet with no PRs stays empty, as before
            vals = pct.loc[(t, a), LEVELS].values
            bars = ax.bar(list(x), vals, width=0.8, edgecolor='black', linewidth=0.6)
            for lvl, bar, v in zip(LEVELS, bars, vals):
                bar.set_facecolor(GRAYS[lvl])
                bar.set_hatch(HATCH[lvl])
                if v > 0:
                    ax.text(bar.get_x() + bar.get_width() / 2, v + 0.8, f'{v:.1f}',
                            ha='center', va='bottom', fontsize=10)

    handles = [mpatches.Patch(facecolor=GRAYS[l], edgecolor='black', hatch=HATCH[l], label=l)
               for l in LEVELS]
    # Lay out the panels first, then hang the legend from the top edge of the figure
    # (its *lower* edge at y=1.0) so it sits entirely above the first row of titles.
    # bbox_inches='tight' in savefig grows the saved canvas to include it.
    fig.tight_layout()
    fig.legend(handles=handles, title='CEFR Level', loc='lower center',
               bbox_to_anchor=(0.5, 1.0), ncol=len(LEVELS), fontsize=12, title_fontsize=14)

    for ext in ('pdf', 'png'):
        fig.savefig(os.path.join(ROOT, f'{out_stem}.{ext}'), bbox_inches='tight',
                    dpi=200 if ext == 'png' else None)
    plt.close(fig)


def main():
    df = pd.read_csv(DATA, dtype={'pr_id': str})
    print(f'{len(df)} agent PRs | agents {df.agent.value_counts().to_dict()}')
    counts, pct, n_prs = facet_table(df)

    for stem, types in FIGS.items():
        draw(pct, n_prs, types, stem)
        print(f'\n{stem}: wrote {stem}.pdf and .png to {ROOT}')
        for t in types:
            for a in AGENTS:
                if (t, a) in pct.index:
                    p = pct.loc[(t, a), LEVELS]
                    print(f'  {t:9s}| {a:8s} PRs={int(n_prs[(t, a)]):3d} '
                          f'constructs={int(counts.loc[(t, a)].sum()):6d}  '
                          + '  '.join(f'{l} {p[l]:4.1f}' for l in LEVELS)
                          + f'   sum={p.sum():.1f}')
                else:
                    print(f'  {t:9s}| {a:8s} (no PRs -> empty facet)')


if __name__ == '__main__':
    main()
