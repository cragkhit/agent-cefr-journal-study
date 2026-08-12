# agent-cefr-journal-study

Replication package for a journal extension of *"When is Generated Code Difficult to
Comprehend? Assessing AI Agent Python Code Proficiency in the Wild"* (MSR '26,
[arXiv:2604.00299](https://arxiv.org/abs/2604.00299)). The MSR paper used **pycefr** to
compare Python code proficiency between AI coding agents and human developers on the
[AIDev](https://arxiv.org/abs/2507.15003) dataset. This extension swaps pycefr for a more
empirically-grounded proficiency-leveling tool (see [Tool](#tool) below) and reruns the
analysis over a refreshed corpus of AI-agent-authored pull requests.

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

**Known gap**: `ai_fetch_summary.csv` has no AI-agent-identity (Copilot/Cursor/Devin) or
PR-task-type (feat/fix/refactor/...) column, both of which the MSR paper's RQ1/RQ3 depend on.
That metadata isn't in this corpus yet.

- **`data/human_corpus/`** — 36,757 Python files from 785 merged human-authored PRs across 160
  repos (matches the MSR paper's 785-PR human comparison set), same filename pattern as above.
- **`data/human_fetch_summary.csv`** — per-file fetch manifest, same shape as `ai_fetch_summary.csv`.
- **`data/output_by_repo_human/`** — one result CSV per repo, same naming convention. Two
  files (`Azure__azure-sdk-for-python`, `crewAIInc__crewAI`) exceeded GitHub's 100MB
  per-file limit uncompressed (300MB and 113MB) and are stored gzipped
  (`.csv.gz`, 26MB/16MB) — read with `pd.read_csv(path, compression="gzip")` or `gunzip` first.
- **`data/human_corpus_by_repo/`** — not stored, same reasoning as above. Regenerate with
  `python3 scripts/group_by_repo.py human_corpus`.

## Running the analysis

```bash
python3 scripts/group_by_repo.py                  # regenerate data/ai_agent_corpus_by_repo/
python3 scripts/group_by_repo.py human_corpus      # regenerate data/human_corpus_by_repo/
TOOL_DIR=/path/to/codeProficiencyExtraction ./run_extraction_by_repo.sh
TOOL_DIR=/path/to/codeProficiencyExtraction INPUT_ROOT=data/human_corpus_by_repo OUTPUT_DIR=data/output_by_repo_human ./run_extraction_by_repo.sh
```

Safe to re-run — repos with an existing output CSV are skipped. Took ~3h17m for the AI-agent
corpus (142 repos) and ~12h (interrupted partway by the second ReDoS bug above, then quick
after the fix) for the human-PR corpus (160 repos).

**Current status / known gaps before results are directly comparable to the MSR paper**:
1. The tool currently derives A1-C2 levels via naive equal-width binning of
   `ubersequenceLevel.csv`'s `Index` column, not its empirically-derived `Final Group` column
   — see `docs/tool-notes.md`.
2. No before/after differential construct counting yet (the MSR paper's method for isolating
   PR-*added* code from pre-existing file content) — `data/output_by_repo/` currently holds
   whole-file counts for every snapshot independently.

## Process log

[`exp_notes.md`](exp_notes.md) is a running decision log covering how this study's tooling was
built, debugged, and validated (including the ReDoS diagnosis/fix and its regression tests).
