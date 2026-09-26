# agent-cefr-journal-study

Replication package for *"Simple Code, More Scrutiny: Python Proficiency and Review Effort in
AI Agent and Human Pull Requests"*, a journal extension of *"When is Generated Code Difficult to
Comprehend? Assessing AI Agent Python Code Proficiency in the Wild"* (MSR '26,
[arXiv:2604.00299](https://arxiv.org/abs/2604.00299)). The MSR paper used **pycefr** to
compare Python code proficiency between AI coding agents and human developers on the
[AIDev](https://arxiv.org/abs/2507.15003) dataset. This extension swaps pycefr for a more
empirically-grounded proficiency-leveling tool (see [Tool](#tool) below), adds a review-effort
analysis (RQ4), and reruns everything over three comparison corpora: AI-agent-authored PRs,
current-era human PRs, and a pre-ChatGPT (pre-LLM-assistance) human PR baseline — see
[Data](#data) below.

## Layout

Shared inputs live in `data/`. Everything that produces a number or a figure for a given
research question lives in that question's folder.

```
data/          corpora, CPET output, and every shared table (see Data below)
collection/    stage 1 -- building the three corpora from AIDev + the GitHub API
extraction/    stage 2 -- running the proficiency tool over the corpora
lib/           shared analysis helpers (merge exclusion, full-path file pairing)
rq1/           RQ1  proficiency levels of agent code, by agent and by task type
rq2/           RQ2  agents vs. humans vs. pre-ChatGPT humans
rq3/           RQ3  which task types contain the most proficient code
rq4/           RQ4  proficiency vs. the review effort a PR receives
paper/         supplementary.tex and the supporting-figure document it builds
docs/          notes on the proficiency tool itself
exp_notes.md   running decision log for the whole study
```

Each `rq*/` folder holds its scripts or notebook, its `tables/` (LaTeX fragments) and its
`figures/` (PDF + PNG). **Run every command from the repository root**; the scripts and
notebooks resolve their own paths, so running them from inside an `rq*/` folder also works.

> Earlier revisions of this package kept RQ3 and RQ4 in a single self-contained `analysis/`
> folder. That folder no longer exists: its notebooks, scripts and tables moved into `rq3/` and
> `rq4/`, its shared CSVs moved into `data/`, and the pre-ChatGPT labelling material moved into
> `rq3/labelling/`.

## Tool

This repo does **not** vendor the analysis tool itself. It was run against:

- **Fork**: [cragkhit/codeProficiencyExtraction](https://github.com/cragkhit/codeProficiencyExtraction),
  branch `fix/redos-try-except-patterns`
- **Upstream**: [swindlemek/codeProficiencyExtraction](https://github.com/swindlemek/codeProficiencyExtraction),
  [PR #1](https://github.com/swindlemek/codeProficiencyExtraction/pull/1) — fixes two waves of
  catastrophic-regex-backtracking (ReDoS) bugs in the construct-detection patterns that
  otherwise hang the tool on real-world-sized Python files (the first wave — multi-line
  `try`/`except`/`finally` patterns — surfaced running the AI-agent corpus below; the second
  — same-line wildcards, e.g. `generatorExpression`, plus an unrelated `nestedTuple` bracket
  bug — surfaced running the human-PR corpus, and hung for 19+ hours in production before
  being caught and fixed).

Background on the tool's own architecture, its relationship to pycefr/PyGress/the MSR paper,
and known limitations (e.g. `ubersequenceLevel.csv`'s `Final Group`/`Percentage` columns not
yet being used for level assignment) is preserved in
[`docs/tool-notes.md`](docs/tool-notes.md).

To reproduce:
```bash
git clone --branch fix/redos-try-except-patterns https://github.com/cragkhit/codeProficiencyExtraction
```

## Data

### Corpora

- **`data/ai_agent_corpus/`** — 8,592 Python files (before/after/new snapshots) from 591 merged
  AI-agent PRs across 145 repos, fetched 2026-08-04. Filename pattern:
  `{owner}__{repo}__pr{prNumber}__{timestamp}__{commitSHA}__{originalFilename}_{before|after|new}.py`.
- **`data/human_corpus/`** — 36,757 Python files from 785 merged human-authored PRs across 160
  repos, same filename pattern.
- **`data/pre_chatgpt_results/`** — 13,092 Python files from 604 merged human-authored PRs
  across 50 repos, all merged **before 2022-11-30** (ChatGPT's public release) — a pre-LLM-
  assistance temporal baseline. Same filename pattern.
- **`data/{ai,human,pre_chatgpt}_fetch_summary.csv`** — per-file fetch manifests
  (owner/repo/pr_id/sha/path, before_path/after_or_new_path, fetch status).
- **`data/pre_chatgpt_pr_index.csv`** — PR-level metadata; 606 of 1,764 candidate PRs were `kept`.

**Agent identity and PR task type** are not columns of the fetch summaries or of the tool's
output. Both are joined back by `pr_id`: agents from `data/aidev_pr_agent.parquet` (7,104 AIDev
agent PRs → agent; no PR mixes agents at commit level), task types from AIDev's `pr_task_type` /
`human_pr_task_type` tables.

### CPET output

- **`data/output_by_repo/`**, **`data/output_by_repo_human/`**,
  **`data/output_by_repo_pre_chatgpt/`** — one result CSV per repo
  (`code_constructs_{repo}_{timestamp}.csv`), plus `run_log.txt`. Two human files
  (`Azure__azure-sdk-for-python`, `crewAIInc__crewAI`) exceeded GitHub's 100MB per-file limit
  uncompressed (300MB and 113MB) and are stored gzipped (`.csv.gz`, 26MB/16MB); the scripts glob
  both `*.csv` and `*.csv.gz` and read them transparently.
- **`data/*_by_repo/` input layouts are not stored** (they would duplicate ~160MB of identical
  file content). Regenerate with
  `python3 extraction/group_by_repo.py [human_corpus|pre_chatgpt_results]`.

**Notes on the tool's output**:
1. The tool derives A1–C2 levels by binning `ubersequenceLevel.csv`'s `Index` column twenty
   constructs per level (the paper's Übersequence ordering), not its `Final Group` column
   — see `docs/tool-notes.md`. A copy of the mapping is at `data/ubersequenceLevel.csv`.
2. `data/output_by_repo*/` holds **whole-file** counts for every snapshot independently. The
   before/after differencing that isolates PR-*added* code is done downstream, in
   `lib/cpet_artifacts.py`: per construct, `delta = max(after − before, 0)`, applied **before**
   mapping constructs to levels; files new in a PR are counted in full.

### Per-PR analysis tables

These are the inputs the RQ3 and RQ4 analyses read. One row per PR, identical column layout so
they can be concatenated.

| File | Rows | Contents |
|---|---|---|
| `data/rq3_agent_prs_with_task_type.csv` | 481 | agent PRs: CEFR counts, task type, PR size, review metrics |
| `data/rq3_human_prs_with_task_type.csv` | 537 | current-era human PRs, same columns |
| `data/rq3_pre_chatgpt_prs_with_task_type.csv` | 465 | pre-ChatGPT human PRs, same columns |
| `data/rq3_pre_chatgpt_prs_titles.csv` | 477 | titles/bodies fed to the task-type labeller |
| `data/rq4_pr_reference.csv` | 1,483 | the PR list RQ4 fetches against |
| `data/rq4_pr_review_metrics.csv` | 1,483 | per-PR review counts, human/bot split |
| `data/rq4_pr_comment_authors.csv` | 1,468 | comments split into human / bot / PR author |
| `data/rq4_reviews_long.csv` | 4,180 | one row per review submission |
| `data/rq4_reviewers.csv` | 536 | reviewer account metadata |
| `data/rq3_outlier_prs.csv` | 191 | IQR outliers on C1+C2, written by the RQ3 notebook |

> **Privacy.** The `body` column of the four `rq3_*` tables and the labelling batches under
> `rq3/labelling/labelling_batches/` are scraped PR descriptions. 154 occurrences of 56 distinct
> personal email addresses have been replaced with `<email redacted>`. GitHub's pseudonymous
> `@users.noreply.github.com` addresses are kept, as are reviewer logins in the RQ4 tables,
> which are the unit of analysis there. No other field was altered; every numeric column is
> unchanged.

## Code

`pip install -r requirements.txt`. Python 3.14.5 was used for the reported results.
**Run all commands from the repository root.** Scripts that call the GitHub API read
`GITHUB_TOKEN` from the environment or a `.env` file (gitignored — never commit it):

```bash
export GITHUB_TOKEN=$(gh auth token)      # or put GITHUB_TOKEN=... in .env
```

`rq3/labelling/label_pre_chatgpt_prs.py` additionally reads `OPENROUTER_API_KEY`.

> **AIDev is pinned.** On 2026-08-21 AIDev's maintainers promoted v4 (AIDev-2.7M) to `main`
> on Hugging Face, which deleted `pr_task_type`, `human_pr_task_type` and
> `human_pull_request` and replaced `pull_request`. Every number in the paper comes from v3,
> so every script here reads revision `68ed5f4b80` (the last v3 revision).
> `data/human_pull_request.parquet` is a local copy of the deleted human PR table.

### Stage 1 — building the corpora (`collection/`)

| Group | Scripts, in order |
|---|---|
| AI agents | `collect_commits.py` (joins AIDev `pull_request` + `pr_commit_details`) → `convert_to_csv.py` → `make_file_versions.py` (fetches each file's before/after version from the GitHub API) |
| Human | `collect_human_prs.py` (AIDev `human_pull_request`) → `collect_human_commits.py` → `filter_human_commits.py` (keep `.py` files and merged PRs: 27,029 rows, 795 PRs) → `make_file_versions_human.py --input-csv data_csv/human_commit_data_py.csv`. `human_prs_to_csv.py` and `collect_human_pr_commits.py` are an earlier commit-level exporter; its output covers only 46% of the final corpus and was not what the corpus was built from. |
| Human, pre-ChatGPT | `collect_pre_chatgpt_prs.py` + `analyze_pre_chatgpt_prs.py` (which repositories have pre-2022-11-30 history → `data/td1_*.csv`, `data/td2_td3_*.csv`) → `collect_pre_chatgpt_commits.py` → `make_file_versions.py`; `fetch_pre_chatgpt_titles.py` adds PR titles/bodies for task-type labelling |
| all | `package_paper_corpora.py` drops failed fetches and non-merged PRs and zips the corpora |
| all | `fetch_commit_parents.py --study-data data` records every corpus commit's parent count → `data/commit_parents.csv` (947 of 7,462 commits are merges) |

### Stage 2 — proficiency extraction (`extraction/`)

```bash
python3 extraction/group_by_repo.py                     # data/ai_agent_corpus_by_repo/
python3 extraction/group_by_repo.py human_corpus        # data/human_corpus_by_repo/
python3 extraction/group_by_repo.py pre_chatgpt_results # data/pre_chatgpt_results_by_repo/

TOOL_DIR=/path/to/codeProficiencyExtraction ./extraction/run_extraction_by_repo.sh
TOOL_DIR=/path/to/codeProficiencyExtraction INPUT_ROOT=data/human_corpus_by_repo        OUTPUT_DIR=data/output_by_repo_human        ./extraction/run_extraction_by_repo.sh
TOOL_DIR=/path/to/codeProficiencyExtraction INPUT_ROOT=data/pre_chatgpt_results_by_repo OUTPUT_DIR=data/output_by_repo_pre_chatgpt ./extraction/run_extraction_by_repo.sh
```

Safe to re-run — repos with an existing output CSV are skipped. Took ~3h17m for the AI-agent
corpus (142 repos), ~12h for the human-PR corpus (160 repos, interrupted partway by the second
ReDoS bug above, then quick after the fix), and ~44min for the pre-ChatGPT corpus (50 repos).

### Stage 3 — results, by research question

> **Merge commits are excluded, and files are paired by full path.** The corpora contain
> every commit listed on each PR, including merge commits such as "Merge branch 'main'
> into feature", whose diff is upstream code rather than the PR author's; they are 64% of
> the human file snapshots, 32% of the pre-ChatGPT ones and 14% of the agent ones. The
> analysis skips any commit with more than one parent (`data/commit_parents.csv`). The
> tool's output names each file by basename only, so every output row is also mapped
> back to its fetch-summary row to recover the full repository path — otherwise two files
> with the same name in one commit would be differenced against each other. Both are
> implemented once, in `lib/cpet_artifacts.py`, and shared by the RQ1 and RQ2 scripts;
> pass `--keep-merges` to reproduce the earlier merge-inclusive numbers.

#### RQ1 — What are the Python proficiency levels of AI agents' code?

| Paper artifact | Command | Output |
|---|---|---|
| Table 4, RQ1 statistics | `python rq1/analyze_rq1_new_tool.py --output-dir data/output_by_repo --mapping data/ubersequenceLevel.csv --commits data/aidev_pr_agent.parquet` | `data/rq1_new_tool_*.csv` |
| Tables 5–6 (by task type) | `python rq1/analyze_rq3_new_tool.py` | `data/rq1_new_tool_by_pr_type.csv`, `data/rq1_new_tool_residuals.csv`, `data/rq3_new_tool_*.csv` |
| Figures 3–4 (task type × agent) | `python rq1/rq1_make_fig_task_type_agent.py` | `rq1/figures/cefr_*_task_types.{pdf,png}` |

`analyze_rq3_new_tool.py` keeps its historical name: it dates from a three-RQ draft in which
the by-task-type breakdown was RQ3. It produces RQ1's Tables 5–6, which is why it lives in `rq1/`.

#### RQ2 — How does agent code compare with human code?

| Paper artifact | Command | Output |
|---|---|---|
| Table 7, RQ2 statistics | `python rq2/analyze_rq2_three_groups.py --repo-root .` then `python rq2/rq2_pairwise_stats.py` | `data/rq2_three_groups_*.csv`; pairwise tests printed |
| Figure 5 (repository-paired) | `python rq2/make_fig_repo_paired.py` | `rq2/figures/repo_paired_cefr.pdf` |

#### RQ3 — Which kinds of PRs contain the most proficient code?

| Paper artifact | Command | Output |
|---|---|---|
| RQ3 tables and figures | run `rq3/rq3_task_type_proficiency.ipynb` | `rq3/tables/*.tex`, `rq3/figures/*`, `data/rq3_outlier_prs.csv` |
| Pre-ChatGPT per-PR table | `python rq3/make_rq3_pre_chatgpt_table.py` | re-bases the labelled table on the current counts, labels untouched |
| Provenance of the per-PR tables | `rq3/rq3_task_type_export.py` | documentation only — see below |

`rq3/rq3_task_type_export.py` records how the three per-PR tables in `data/` were built. It is
**not a runnable step**: it reads AIDev at the pinned v3 revision, which Hugging Face no longer
serves from `main`. The tables it would produce are shipped directly in `data/`.

**Pre-ChatGPT task-type labelling** (`rq3/labelling/`). The pre-ChatGPT PRs predate the AIDev
sample and carry no upstream labels, so they were labelled with GPT-4.1-mini following Li et al.
§4.1. The folder holds the prompt (`rq3_labelling_prompt.md`), the methodology note
(`pre-chatgpt-pr-labelling.md`), the raw label cache (`rq3_pre_chatgpt_labels.jsonl`), the API
labeller (`label_pre_chatgpt_prs.py`), and the 20 paste-ready batches with the script that
builds them. The batches are an earlier manual route, superseded by the API labeller that
produced the shipped labels; both are included for completeness.

#### RQ4 — Does proficiency predict the review effort a PR receives?

| Paper artifact | Command | Output |
|---|---|---|
| RQ4 tables and figures | run `rq4/rq4_review_effort.ipynb` | `rq4/tables/*.tex`, `rq4/figures/*` |
| Rebuild the PR list | `python rq4/rq4_make_pr_reference.py` | `data/rq4_pr_reference.csv` |
| Re-fetch review data | `python rq4/rq4_fetch_review_data.py` | `data/rq4_pr_review_metrics.csv`, `rq4_reviews_long.csv`, `rq4_reviewers.csv` |
| Re-fetch comment authors | `python rq4/rq4_fetch_comment_authors.py` | `data/rq4_pr_comment_authors.csv` |
| Join review data onto the PR tables | `python rq4/rq4_make_tables.py` | rewrites the three `data/rq3_*_with_task_type.csv` in place |

The three fetch/join steps only need re-running to rebuild the review data from GitHub; the
shipped CSVs already contain their output. They require `GITHUB_TOKEN`, checkpoint after every
PR into `rq4/log files/` (gitignored) and resume from there, so an interrupted run is safe to
restart. `rq4/rq4-review-effort-data.md` is the column reference and explains why AIDev cannot
answer RQ4 (none of the human PRs appear in its `pr_reviews`/`pr_comments`/`pr_timeline` tables).

All review-effort outcomes count **human** activity only: bots write 41.7% of the reviews and
51.4% of the comments on agent PRs, and the PR author's own replies are excluded as well.

### LaTeX tables

The `.tex` files under `rq*/tables/` and `data/*.tex` are LaTeX fragments (a bare `tabular`, no
caption or label). They are pasted into the paper by hand — the paper contains no `\input{}` —
so nothing automatically checks that the paper and these files agree.

## Supporting figures

`paper/supplementary.tex` collects the figures referenced from the article but not printed in
it: the per-agent task-type breakdowns (RQ1) and the per-repository CEFR means (RQ2). Build with:

```bash
cd paper && latexmk -pdf supplementary.tex
```

## Process log

[`exp_notes.md`](exp_notes.md) is a running decision log covering how this study's tooling was
built, debugged, and validated (including the ReDoS diagnosis/fix and its regression tests).
