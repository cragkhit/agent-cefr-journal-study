# agent-cefr-journal-study

Replication package for a journal extension of *"When is Generated Code Difficult to
Comprehend? Assessing AI Agent Python Code Proficiency in the Wild"* (MSR '26,
[arXiv:2604.00299](https://arxiv.org/abs/2604.00299)). The MSR paper used **pycefr** to
compare Python code proficiency between AI coding agents and human developers on the
[AIDev](https://arxiv.org/abs/2507.15003) dataset. This extension swaps pycefr for a more
empirically-grounded proficiency-leveling tool (see [Tool](#tool) below) and reruns the
analysis over three comparison corpora: AI-agent-authored PRs, current-era human PRs, and a
pre-ChatGPT (pre-LLM-assistance) human PR baseline — see [Data](#data) below.

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

- **`data/ai_agent_corpus/`** — 8,592 Python files (before/after/new snapshots) from 591 merged
  AI-agent PRs across 145 repos, fetched 2026-08-04. Filename pattern:
  `{owner}__{repo}__pr{prNumber}__{timestamp}__{commitSHA}__{originalFilename}_{before|after|new}.py`.
- **`data/ai_fetch_summary.csv`** — per-file fetch manifest (owner/repo/pr_id/sha/path,
  before_path/after_or_new_path, fetch status).
- **`data/output_by_repo/`** — one result CSV per repo (`code_constructs_{repo}_{timestamp}.csv`)
  from running the tool over `data/ai_agent_corpus_by_repo/` (see below), plus `run_log.txt`.
- **`data/ai_agent_corpus_by_repo/`** — *not stored here* (would duplicate ~160MB of identical
  file content under a second directory layout). Regenerate it with:
  ```bash
  python3 scripts/group_by_repo.py
  ```

**Agent identity and PR task type** are not columns of `ai_fetch_summary.csv` or of the
tool's output. Both are joined back by `pr_id`: agents from `data/aidev_pr_agent.parquet`
(7,104 AIDev agent PRs → agent; no PR mixes agents at commit level), task types from AIDev's
`pr_task_type` / `human_pr_task_type` tables. See [Code](#code) below.

- **`data/human_corpus/`** — 36,757 Python files from 785 merged human-authored PRs across 160
  repos (matches the MSR paper's 785-PR human comparison set), same filename pattern as above.
- **`data/human_fetch_summary.csv`** — per-file fetch manifest, same shape as `ai_fetch_summary.csv`.
- **`data/output_by_repo_human/`** — one result CSV per repo, same naming convention. Two
  files (`Azure__azure-sdk-for-python`, `crewAIInc__crewAI`) exceeded GitHub's 100MB
  per-file limit uncompressed (300MB and 113MB) and are stored gzipped
  (`.csv.gz`, 26MB/16MB) — read with `pd.read_csv(path, compression="gzip")` or `gunzip` first.
- **`data/human_corpus_by_repo/`** — not stored, same reasoning as above. Regenerate with
  `python3 scripts/group_by_repo.py human_corpus`.

- **`data/pre_chatgpt_results/`** — 13,092 Python files from 604 merged human-authored PRs
  across 50 repos, all merged **before 2022-11-30** (ChatGPT's public release) — a pre-LLM-
  assistance temporal baseline, the third comparison group alongside the AI-agent and
  current-era human corpora above. Same filename pattern.
- **`data/pre_chatgpt_pr_index.csv`** — PR-level (not file-level) metadata:
  `full_name, pr_id, number, merged_at, n_files, n_py_files, has_py, kept, n_commits,
  n_rows_emitted, note`. 606 of 1,764 candidate PRs were `kept`.
- **`data/pre_chatgpt_fetch_summary.csv`** — per-file fetch manifest, same shape as the other
  two `*_fetch_summary.csv` files.
- **`data/output_by_repo_pre_chatgpt/`** — one result CSV per repo, same naming convention.
  All files under GitHub's 100MB limit uncompressed (largest: `spcl__dace`, 92.5MB).
- **`data/pre_chatgpt_results_by_repo/`** — not stored, same reasoning as above. Regenerate
  with `python3 scripts/group_by_repo.py pre_chatgpt_results`.

## Running the analysis

```bash
python3 scripts/group_by_repo.py                        # regenerate data/ai_agent_corpus_by_repo/
python3 scripts/group_by_repo.py human_corpus            # regenerate data/human_corpus_by_repo/
python3 scripts/group_by_repo.py pre_chatgpt_results      # regenerate data/pre_chatgpt_results_by_repo/
TOOL_DIR=/path/to/codeProficiencyExtraction ./run_extraction_by_repo.sh
TOOL_DIR=/path/to/codeProficiencyExtraction INPUT_ROOT=data/human_corpus_by_repo OUTPUT_DIR=data/output_by_repo_human ./run_extraction_by_repo.sh
TOOL_DIR=/path/to/codeProficiencyExtraction INPUT_ROOT=data/pre_chatgpt_results_by_repo OUTPUT_DIR=data/output_by_repo_pre_chatgpt ./run_extraction_by_repo.sh
```

Safe to re-run — repos with an existing output CSV are skipped. Took ~3h17m for the AI-agent
corpus (142 repos), ~12h (interrupted partway by the second ReDoS bug above, then quick after
the fix) for the human-PR corpus (160 repos), and ~44min for the pre-ChatGPT corpus (50
repos, run after both ReDoS fixes landed — no issues).

**Notes on the tool's output**:
1. The tool derives A1-C2 levels by binning `ubersequenceLevel.csv`'s `Index` column twenty
   constructs per level (the paper's Übersequence ordering), not its `Final Group` column
   — see `docs/tool-notes.md`. A copy of the mapping is at `data/ubersequenceLevel.csv`.
2. `data/output_by_repo*/` holds **whole-file** counts for every snapshot independently. The
   before/after differencing that isolates PR-*added* code is done downstream by the
   analysis scripts: per construct, `delta = max(after − before, 0)`, applied **before**
   mapping constructs to levels; files new in a PR are counted in full.

## Code

Everything from the AIDev pull to the numbers in the paper. Run all commands **from the
repository root**. `pip install -r requirements.txt`; scripts that call the GitHub API read
`GITHUB_TOKEN` from a `.env` file (gitignored — never commit it).

> **AIDev is pinned.** On 2026-08-21 AIDev's maintainers promoted v4 (AIDev-2.7M) to `main`
> on Hugging Face, which deleted `pr_task_type`, `human_pr_task_type` and
> `human_pull_request` and replaced `pull_request`. Every number in the paper comes from v3,
> so every script here reads revision `68ed5f4b80` (the last v3 revision).
> `data/human_pull_request.parquet` is a local copy of the deleted human PR table.

### Stage 1 — building the corpora (`scripts/collection/`)

| Group | Scripts, in order |
|---|---|
| AI agents | `collect_commits.py` (joins AIDev `pull_request` + `pr_commit_details`) → `convert_to_csv.py` → `make_file_versions.py` (fetches each file's before/after version from the GitHub API) |
| Human | `collect_human_prs.py` (AIDev `human_pull_request`) → `collect_human_commits.py` (file-level commit details from the GitHub API) → `filter_human_commits.py` (keep `.py` files and merged PRs: 27,029 rows, 795 PRs) → `make_file_versions_human.py --input-csv data_csv/human_commit_data_py.csv`. `human_prs_to_csv.py` and `collect_human_pr_commits.py` are an earlier commit-level exporter; its output covers only 46% of the final corpus and was not what the corpus was built from. |
| Human, pre-ChatGPT | `collect_pre_chatgpt_prs.py` + `analyze_pre_chatgpt_prs.py` (which repositories have pre-2022-11-30 history → `data/td1_*.csv`, `data/td2_td3_*.csv`) → `collect_pre_chatgpt_commits.py` → `make_file_versions.py`; `fetch_pre_chatgpt_titles.py` adds PR titles/bodies for task-type labelling |
| all | `package_paper_corpora.py` drops failed fetches and non-merged PRs and zips the corpora stored under `data/` |
| all | `fetch_commit_parents.py --study-data data` records every corpus commit's parent count → `data/commit_parents.csv` (947 of 7,462 commits are merges) |

### Stage 2 — proficiency extraction

`scripts/group_by_repo.py` and `run_extraction_by_repo.sh`, see
[Running the analysis](#running-the-analysis) above.

### Stage 3 — results

> **Merge commits are excluded, and files are paired by full path.** The corpora contain
> every commit listed on each PR, including merge commits such as "Merge branch 'main'
> into feature", whose diff is upstream code rather than the PR author's; they are 64% of
> the human file snapshots, 32% of the pre-ChatGPT ones and 14% of the agent ones. The
> analysis skips any commit with more than one parent (`data/commit_parents.csv`). The
> tool's output names each file by basename only, so every output row is also mapped
> back to its fetch-summary row to recover the full repository path — otherwise two files
> with the same name in one commit would be differenced against each other. Both are
> implemented once, in `scripts/analysis/cpet_artifacts.py`, and shared by the RQ1 and
> RQ2 scripts; pass `--keep-merges` to reproduce the earlier merge-inclusive numbers.

| Paper artifact | Command | Output |
|---|---|---|
| Table 4, RQ1 statistics | `python scripts/analysis/analyze_rq1_new_tool.py --output-dir data/output_by_repo --mapping data/ubersequenceLevel.csv --commits data/aidev_pr_agent.parquet` | `data/rq1_new_tool_*.csv` |
| Tables 5–6 (RQ1 by task type) | `python scripts/analysis/analyze_rq3_new_tool.py` | `data/rq1_new_tool_by_pr_type.csv`, `data/rq1_new_tool_residuals.csv`, `data/rq3_new_tool_*.csv` |
| Figures 3–4 (task type × agent) | `python analysis/rq1_make_fig_task_type_agent.py` | `cefr_*_task_types.pdf` at the repository root (copies in `figures/`) |
| Table 7, RQ2 statistics | `python scripts/analysis/analyze_rq2_three_groups.py --repo-root .` then `python scripts/analysis/rq2_pairwise_stats.py` | `data/rq2_three_groups_*.csv`; pairwise tests printed |
| Figure 5 (repository-paired) | `python scripts/analysis/make_fig_repo_paired.py` | `figures/repo_paired_cefr.pdf` |
| Pre-ChatGPT per-PR table | `python scripts/analysis/make_rq3_pre_chatgpt_table.py --labelled analysis/rq3_pre_chatgpt_prs_with_task_type.csv` | re-bases the GPT-4.1-mini-labelled table on the current counts, labels untouched |
| RQ3 tables and figures | `analysis/rq3_task_type_proficiency.ipynb` | `analysis/rq3_tables/`, `figures/rq3_outlier_tasks_*.pdf` |
| RQ4 tables and figures | `analysis/rq4_review_effort.ipynb` | `analysis/rq4_tables/`, `figures/rq4_predicted_effort_*.pdf` |

The `data/*.tex` files are the LaTeX tables as pasted into the paper, typeset by hand from the
CSVs above — no script writes them.

The two human CPET outputs stored as `.csv.gz` are read transparently — the scripts glob both
`*.csv` and `*.csv.gz`.

`analysis/` is self-contained (its scripts and notebooks use paths relative to that folder):
the per-PR tables for the three groups with task types and review-effort columns, the
pre-ChatGPT task-type labelling (prompt, batches, GPT-4.1-mini labels), and the RQ4
review-effort data pulled from the GitHub API. `analysis/rq4-review-effort-data.md` is the
column reference. The notebooks write figures one level up (the paper includes them from its
root); copies of every generated figure in the paper are in `figures/`.

## Process log

[`exp_notes.md`](exp_notes.md) is a running decision log covering how this study's tooling was
built, debugged, and validated (including the ReDoS diagnosis/fix and its regression tests).
