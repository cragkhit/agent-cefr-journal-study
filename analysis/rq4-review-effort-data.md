# RQ4 data — review effort as a function of proficiency

Data for the recommended RQ4 in `RQs_proposals.md`. Collected 2026-09-01.

## ⚠️ Read this first: AIDev cannot answer RQ4

`RQs_proposals.md` lists AIDev's `pr_reviews`, `pr_comments` and `pr_timeline` as the
sources. **Those tables cover agent PRs only.** Checked against AIDev's pinned v3
revision `68ed5f4b80`:

| Table | Our agent PRs | Our human PRs |
|---|---|---|
| `pr_reviews` | 357 / 491 | **0 / 513** |
| `pr_comments` | 429 / 491 | **0 / 513** |
| `pr_timeline` | 491 / 491 | **0 / 513** |

RQ4's payoff is the agent-vs-human comparison, so it is not answerable from AIDev.
Everything here was therefore pulled from the **GitHub API**, for all three groups with
one script at one point in time. That also avoids confounding group with snapshot date,
which mixing an AIDev snapshot for agents with a live pull for humans would have done.

A second reason to prefer the API: AIDev's `user` table has no `public_repos`, so it is a
weaker seniority proxy than `GET /users/{login}`.

## Files

| File | Rows | What |
|---|---|---|
| `rq3_agent_prs_with_task_type.csv` | 491 | per-PR table, **now with RQ4 columns added** |
| `rq3_human_prs_with_task_type.csv` | 513 | same |
| `rq3_pre_chatgpt_prs_with_task_type.csv` | 477 | same, keeping your GPT-4.1-mini labels |
| `rq4_pr_review_metrics.csv` | 1,481 | the review metrics on their own |
| `rq4_reviews_long.csv` | 4,206 | one row per review submission (reviewer, state, timestamp) |
| `rq4_reviewers.csv` | 601 | one row per distinct human reviewer — seniority proxy |
| `rq4_pr_reference.csv` | 1,481 | `pr_id → full_name, number` |
| `rq4_pr_comment_authors.csv` | 1,466 | comments split into human / bot / PR author |

Regenerate with `rq4_fetch_review_data.py`, then `rq4_make_tables.py`, then
`rq4_fetch_comment_authors.py` (all here). Every fetch checkpoints per PR and resumes;
they need `GITHUB_TOKEN` in `.env` or the environment (`GITHUB_TOKEN=$(gh auth token)`
works). All paths are relative to this `analysis/` directory.

## Columns added to the three per-group tables

**Independent variables** (from the CEFR counts already in the table)

| Column | Meaning |
|---|---|
| `constructs_total` | total constructs in the PR |
| `c1c2` | C1 + C2 count |
| `c1c2_pct` | C1 + C2 as a % of the PR's constructs |
| `cefr_mean` | ordinal CEFR mean, A1=1 … C2=6 — same measure as RQ2's repository-paired Wilcoxon |

**Dependent variables**

| Column | Meaning |
|---|---|
| `n_issue_comments` | PR conversation comments -- GitHub's counter, **includes bots** |
| `n_review_comments` | inline code-review comments -- GitHub's counter, **includes bots** |
| `n_*_comments_human` / `_bot` / `_author` | the same comments split by author, from `rq4_pr_comment_authors.csv` |
| `n_reviews_human` / `n_reviews_bot` / `n_reviews_total` | review submissions |
| `n_reviewers_human` / `n_reviewers_bot` | distinct reviewers |
| `n_approved`, `n_changes_requested`, `n_commented` | human review states |
| `any_changes_requested` | 0/1 |
| `first_review_latency_h` | PR created → first **human** review |
| `first_review_latency_any_h` | … → first review of any kind |

**Controls** — `additions`, `deletions`, `changed_files`, `n_commits`.
`RQs_proposals.md` is right that PR size is the confound that decides whether reviewers
believe this: on human PRs, raw `additions` correlates with comment volume at ρ = +0.301,
stronger than any proficiency measure. These must be a regression, not a raw correlation.

**Context** — `pr_state`, `merged`, `draft`, `author_association`, `pr_created_at`,
`pr_merged_at`, `full_name`, `number`, `status`.

### `time_to_merge_h` — please decide

`RQs_proposals.md` says the original time-to-merge RQ4 "has been removed". It is included
anyway because it is free from the same API response and works as a secondary outcome.
**It is not used by the recommended RQ4** — drop the column if you would rather it stay
out.

### `status`

`ok` for 1,466 PRs. **15 PRs returned 404** — 2 agent, 13 human, 0 pre-ChatGPT. The
repositories still exist; the individual PRs have been deleted. Filter on
`status == 'ok'`. This is 1.0% and matches the loss the paper already describes in §4.2.

## The zero-inflation check the proposal asked for

> *"Check the review-count distribution before committing. If most agent PRs have zero
> review comments, the review RQ becomes a descriptive finding rather than a modelling
> one."*

Zero-inflated but **not degenerate — modelling is viable.**

| Group | n | Zero human reviews | Zero comments | Median comments | Changes requested |
|---|---|---|---|---|---|
| AI agents | 489 | 31.7% | 10.0% | 3.0 | **10.4%** |
| Human | 500 | 33.4% | 27.0% | 2.0 | 4.0% |
| Human (pre-ChatGPT) | 477 | 36.9% | 40.0% | 1.0 | 5.0% |

Negative binomial with zero inflation, as proposed, is the right model.

**Bots must be filtered.** On agent PRs bots produce 41% of reviews and 70% of comments.
Every count above is split human/bot for that reason. Since AIDev has no human PRs, its
reviewer-identity classification could not be reused; bots are flagged by
`user.type == 'Bot'` or a `[bot]` login suffix.

## What the analysis found

Run `rq4_review_effort.ipynb`; it writes its tables to `rq4_tables/` and its figures to the
repository root. The headline numbers, all size-controlled:

| | agents | human | pre-ChatGPT |
|---|---|---|---|
| C1+C2 -> review rounds (IRR per 1 SD) | 1.11 n.s. | **1.22*** | **1.40*** |
| C1+C2 -> reviewer comments | 1.20 n.s. | 1.14 n.s. | **1.39*** |
| C1+C2 -> changes requested (OR) | 1.30 n.s. | **2.14*** | 1.53 n.s. |
| ordinal CEFR mean -> anything | n.s. | n.s. | n.s. |

Proficiency predicts review effort on human PRs and not on agent PRs. The agents' PRs are
not under-reviewed in absolute terms -- they draw more reviewer comments (mean 3.31 vs 1.81
and 1.69) and twice the change requests (10.4% vs 4.0% and 5.0%) -- so what is missing is
the *calibration* of effort to how demanding the code is. The between-group interaction
terms point the same way but do not survive Holm correction, so that contrast is reported
as a tendency, not a demonstrated difference.

Three method points the data forced:

1. **Bots must be excluded, and they are a bigger share than expected.** On agent PRs bots
   submit 41.6% of reviews and write 51.4% of comments, against 4.3% and 17.7% on
   pre-ChatGPT human PRs.
2. **The PR author's own comments must be excluded too.** They are 36.4% and 41.5% of the
   human comments on the two human groups but only 3.3% on agent PRs, where the author is a
   bot and is already filtered out. Leaving them in would inflate the human groups.
   The primary comment outcome therefore excludes them; including them is a robustness check
   and does not change the conclusion.
3. **Repository is handled with clustered standard errors, not a random effect.** statsmodels
   has no negative binomial mixed model, and clustering is the standard alternative.

Zero-inflated negative binomial was tried and is *not* needed: its AIC is higher than plain
NB in all six group-by-outcome comparisons, so the dispersion parameter alone absorbs the
zeros.
