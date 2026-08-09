# Code Construct Extraction Tool — background notes

> These are architecture/motivation notes about the **codeProficiencyExtraction** tool used by
> this study (see the top-level [README.md](../README.md) for which fork/branch). The tool's
> code is not vendored in this repo; these notes are preserved here as background reading for
> reproducing the study, written while developing and fixing the tool ahead of this run.

# Code Construct Extraction Tool

This tool extracts Python code constructs from source files and categorizes them by CEFR-like proficiency levels (A1-C2), borrowing the framework used to grade language-learner proficiency and applying it to Python code style/complexity.

## Overview

The tool analyzes Python code files to identify various programming constructs (e.g., loops, functions, classes, comprehensions) and counts them according to predefined complexity levels:

- **A1/A2**: Basic constructs (simple loops, conditionals, basic functions)
- **B1/B2**: Intermediate constructs (list comprehensions, decorators, exception handling)
- **C1/C2**: Advanced constructs (metaclasses, generators, context managers)

## Motivation & Related Research

This tool's approach — regex-based construct detection mapped to CEFR-style A1–C2 levels — is
not novel to this repo; it traces back to **pycefr**, cited in the literature as reference
[36] and described as "the most direct and relevant prior work aimed at establishing a
proficiency framework for Python code constructs." pycefr assigns each Python construct a
CEFR level based on **the tool author's opinion and informal developer surveys** — i.e., a
manually/subjectively defined baseline, with no systematic, evidence-based methodology behind
the level assignments. The pycefr authors themselves flagged this as needing a more scientific
evaluation.

A follow-up empirical study (ACM DOI [10.1145/3769864](https://doi.org/10.1145/3769864))
addresses exactly that gap, and its methodology explains most of this repo's file layout and
naming:

- It compiled **138 Python code constructs** from the official Python AST grammar (vs.
  pycefr's 98) — this matches the ~138 entries in `regularExpressionList.json` almost exactly.
- It mined **22 introductory Python textbooks** (converted PDF → text via **PDFMiner** —
  explaining this repo's otherwise-unused `pdfminer.six` dependency, and the vestigial
  "page"-keyed dict shape in `extract_text_from_py`, both almost certainly inherited from the
  paper's own textbook-processing pipeline before being repointed at plain `.py` files) to
  extract, per textbook, the **first-occurrence order** of each construct.
- **RQ1 — the "Übersequence"**: for each construct, the paper normalizes its position across
  textbooks, discards outliers (>1 std-dev from the mean), and sorts by median position to
  produce one consensus ordering. Only **118 of the 138 constructs** actually appear across
  the 22 textbooks (20 are excluded as either conceptually redundant with an already-covered
  construct, or too new/rare to appear in the corpus) — which is exactly why this repo's
  `ubersequenceLevel.csv` has `Index` values 1–118, not 1–138. **This CSV file *is* (or is
  directly derived from) the paper's Übersequence output.**
- **RQ2 — clustering**: the paper builds a weighted co-occurrence graph of constructs
  (edge weight from normalized page-distance, doubled if same chapter) and runs the Louvain
  community-detection algorithm 100 times, finding 6 stable clusters (sizes 27, 28, 15, 26, 8,
  19) that it then maps to A1–C2. This strongly suggests the CSV's `Final Group` column holds
  each construct's resulting cluster/level, and `Percentage` holds its cluster-membership
  probability across the 100 Louvain runs (the paper gives a worked example: the `read`
  function was assigned to its predominant group in 80% of runs).
- The paper explicitly cross-checked its empirically-derived levels against pycefr's original
  manual ones and found weak agreement — 56% at A1, dropping to **0% agreement at C1** —
  concluding pycefr's subjective assignments diverge substantially from an evidence-based
  ordering.

### The paper this tool is meant to power: an MSR'26 → journal extension

A second, related paper — "When is Generated Code Difficult to Comprehend? Assessing AI Agent
Python Code Proficiency in the Wild" (MSR '26, arXiv:2604.00299) — used the *original* pycefr
(as a black box) to compare Python code proficiency between three AI coding agents (Copilot,
Cursor, Devin) and human developers, on the AIDev dataset (591 agent PRs / 5,027 files vs. 785
human PRs / 20,063 files). Findings: AI agents overwhelmingly generate Basic-level code
(>90% A1/A2, <0.5% C2); AI vs. human proficiency profiles are broadly similar; agents' rare
high-proficiency code clusters in `feat`/`fix` PRs.

This repo (`codeProficiencyExtraction`) is the tool intended to **replace pycefr** in a journal
extension of that MSR paper — swapping pycefr's manually-assigned levels for the more
rigorously derived Übersequence/clustering-based ones described above. Two gaps to close before
that swap is faithful to the original study:

1. **No differential (before/after) counting.** The MSR paper only counts constructs *newly
   introduced* by a PR: for modified files, it reconstructs before/after versions from GitHub
   diffs, runs the analysis on both, and takes `max(after − before, 0)` per construct. This
   repo's `process_directory`/`process_file` only ever analyze one snapshot of a directory —
   there is no before/after diffing step. This would need to be added as a wrapper around
   `extractCodeFromDir.py` (not baked into it), so the tool stays usable for non-PR-diff cases.
2. **The `Final Group`/`Percentage`-vs-naive-binning gap** described just above. Since the
   entire point of using this tool instead of pycefr is presumably to use the more rigorous
   levels, this should likely be resolved before rerunning the MSR paper's RQ1–3 with it.

**This matters for how `extractCodeFromDir.py` should be read**: the script currently
**ignores** the paper's actual empirical `Final Group`/`Percentage` columns and instead
re-derives levels with a crude, hardcoded equal-width binning of `Index` (buckets of 20:
1–20→A1, 21–40→A2, …) — see [Architecture](#architecture) and
[Known limitations](#known-limitations--rough-edges). That binning is *not* the paper's
Louvain-derived grouping (whose 6 clusters are unevenly sized: 27/28/15/26/8/19, not ~20/20/
20/20/20/18), so this script's current level assignment is closer in spirit to pycefr's
original placeholder-style bucketing than to the more rigorously derived clusters sitting
unused in the same CSV file.

## Installation

### Prerequisites

- Python 3.7 or higher
- pip (Python package installer)

### Setup

1. **Clone or download the repository**

2. **Install required packages**

```bash
pip install pandas pdfminer.six numpy
```

> Note: `pdfminer.six` is listed in `requirements.txt` but is not actually used by
> `extractCodeFromDir.py` — see [Architecture](#architecture) below. It appears to be a
> holdover from an earlier version of the tool that read source out of PDFs.

## Required Files

Ensure the following files are present in the working directory (the script hardcodes these as relative paths, so it must be run from this directory):

1. **extractCodeFromDir.py** - Main extraction script
2. **regularExpressionList.json** - Contains regex patterns for code constructs
3. **ubersequenceLevel.csv** - Maps constructs to CEFR levels

## Usage

### Basic Usage

Process all Python files in a directory:

```bash
python extractCodeFromDir.py <input_directory>
```

**Example:**

```bash
python extractCodeFromDir.py /path/to/student/code
```

### Custom Output Directory

Specify a custom output location:

```bash
python extractCodeFromDir.py <input_directory> <output_directory>
```

**Example:**

```bash
python extractCodeFromDir.py /path/to/student/code /path/to/output
```

## Output Format

### CSV File

The tool generates a timestamped CSV file with the following naming convention:

```
code_constructs_{directory_name}_{timestamp}.csv
```

**Example:** `code_constructs_student_submissions_20260123_143022.csv`

### CSV Columns

| Column | Description |
|--------|-------------|
| `filename` | Name of the processed Python file |
| `code_snippet` | List of extracted code snippets |
| `code_type` | List of construct types found |
| `count_A1` | Number of A1-level constructs |
| `count_A2` | Number of A2-level constructs |
| `count_B1` | Number of B1-level constructs |
| `count_B2` | Number of B2-level constructs |
| `count_C1` | Number of C1-level constructs |
| `count_C2` | Number of C2-level constructs |

### Example Output

```csv
filename,code_snippet,code_type,count_A1,count_A2,count_B1,count_B2,count_C1,count_C2
calc.py,"['def add(a, b):', 'for i in range(10):']","['simplefunc', 'forloop']",15,8,3,0,0,0
```

## Architecture

The tool is regex-based, not AST-based: it never parses Python into a syntax tree, it just
pattern-matches the raw source text of each `.py` file against ~140 named regexes.

### Files

- **`extractCodeFromDir.py`** — the entire implementation (~390 lines), CLI entry point is `main()`.
- **`regularExpressionList.json`** — a single top-level key `"All"` mapping ~138 construct
  names (e.g. `forsimple`, `tryexcept`, `metaclass2`, `descriptorGet`, `dictComptwithIfelse`)
  to regex patterns. This is the primary construct catalogue.
- **`ubersequenceLevel.csv`** — maps each construct name to an `Index` (1–118). The script
  buckets indices into 6 CEFR levels:
  - 1–20 → A1 (level 0)
  - 21–40 → A2 (level 1)
  - 41–60 → B1 (level 2)
  - 61–80 → B2 (level 3)
  - 81–100 → C1 (level 4)
  - 101–118 → C2 (level 5)

  The CSV also has `Node`, `Final Group`, and `Percentage` columns that are **not** currently
  used by the script (only `Construct` and `Index` are read in `load_construct_level_mapping`).

  **Patched (2026-08-09):** several `try*`/`metaclass3` patterns in this file originally
  caused catastrophic regex backtracking (effectively an infinite hang) on real-world-sized
  Python files — see [Known limitations](#known-limitations--rough-edges) for details and the
  fix applied. This is a deliberate divergence from the upstream repo, not an upstream change.

### Pipeline (`process_directory` → `process_file`)

1. `process_directory` validates the input directory, loads the construct→level mapping from
   the CSV, and lists all `.py` files (non-recursive — subdirectories are not walked).
2. For each file, `process_file` runs three separate extraction passes over the same raw text:
   - `extract_code_from_text` — iterates all constructs in `regularExpressionList.json` and
     runs `re.findall` for each against the whole file, counting every match.
   - `extract_code_custom` (recursive functions) — one hand-written regex, not in the JSON:
     `def foo(...): ... return ... foo` — looks for a function that calls itself by name in
     its own body.
   - `extract_code_custom` (inheritance chains) — another hand-written regex, not in the JSON:
     looks for a `class X(Y):` followed later by another `class Z(Y):` (shared-base-class
     detection, not a true inheritance-chain detector).
   - `merge_result` combines all three passes into one per-file result (keyed by "page" — see
     below — with construct counts, snippets, and type labels).
3. `convert_result_to_row` aggregates snippets/types across all "pages" and rolls per-construct
   counts up into `count_A1` ... `count_C2` using the CSV-derived mapping.
4. All rows become a pandas `DataFrame`, written to
   `code_constructs_{dirname}_{timestamp}.csv`, and summary statistics (total/average per
   level) are printed to stdout.

### The "page" abstraction

`extract_text_from_py` reads a whole `.py` file and wraps it as `{1: content}` — a dict keyed
by page number, even though there is always exactly one "page" per file. This, plus the
`pdfminer.six` dependency, strongly suggests the tool was originally built (or adapted from a
sibling tool) to extract text from PDF submissions page-by-page, and was later repointed at
`.py` files directly without removing the now-vestigial page machinery.

## Known limitations / rough edges

- **~~Catastrophic regex backtracking on real-world files~~ — fixed 2026-08-09**: several
  `try*` constructs (`tryexceptelsefinally`, `tryexceptfinally`, `trytry`, `tryexceptelse`,
  `tryexcept`, `tryStar`) plus `metaclass3` originally combined a `.*` immediately adjacent to
  an unbounded `[\s\S]*` (ambiguous overlap — `.` is a subset of `[\s\S]`), and several chained
  2–3 such unbounded wildcards in sequence (try→except→else→finally). On short samples like
  `calc.py` this never showed up, but it caused the tool to hang indefinitely on real ~30KB+
  files (first observed processing `514-labs__moose`, which has an ~31KB file with a dozen-ish
  try/except/else blocks — enough occurrences of each keyword to blow up combinatorially).
  Fixed by removing the redundant `.*` and bounding every multi-line wildcard to
  `[\s\S]{0,300}?` (~5–8 lines of slack — generous for a real try/except block, small enough to
  cap worst-case backtracking to a constant). Verified against the original hanging file and
  the 5 largest files in the corpus (up to 405KB): no more timeouts, and construct counts on a
  small regression sample are unchanged. **This means `regularExpressionList.json` in this
  repo now differs from the upstream `swindlemek/codeProficiencyExtraction` version** — if you
  re-clone or diff against upstream, expect this file to show as modified.
- **Textual, not syntactic**: since detection is pure regex over source text (not an AST), it
  is sensitive to formatting and can misfire on unusual style, multi-line statements, or code
  inside comments/strings.
- **Overlapping/non-exclusive patterns**: many regexes are broad (e.g. `simpleAssign` is
  essentially `\w+.*=\w+.*`) and overlap with more specific ones (e.g. `simpleif` vs `ifelse`),
  so a single line can be counted under multiple construct types simultaneously — construct
  counts are not mutually exclusive tallies of distinct code lines.
- **Hardcoded relative paths**: `REGEX_FILE` (`./regularExpressionList.json`) and
  `MAPPING_CSV` (`./ubersequenceLevel.csv`) are relative to the current working directory, not
  the script location — the tool must be invoked from this directory.
- **Non-recursive directory scan**: `process_directory` only looks at the top level of
  `input_dir`; `.py` files in subdirectories are skipped.
- **Unused dependency**: `pdfminer.six` is required by `requirements.txt` but never imported
  or used by `extractCodeFromDir.py`.
- **Unused CSV columns, likely discarding the actual research result**: `Node`, `Final Group`,
  and `Percentage` in `ubersequenceLevel.csv` are not read by the current script. Per
  [Motivation & Related Research](#motivation--related-research), `Final Group`/`Percentage`
  appear to be the empirically-derived (Louvain clustering) proficiency levels from the source
  paper — the actual evidence-based result the CSV was built to carry. The script instead
  recomputes levels via naive equal-width binning of `Index` in
  `load_construct_level_mapping`, which does not match the paper's uneven cluster sizes. If the
  goal is to reproduce the paper's findings, mapping directly from `Final Group` instead of
  rebinning `Index` looks like the fix.

## Open questions (worth revisiting as the code evolves)

- Is the "shared base class" regex (`inheritclass`) intended to detect actual inheritance
  chains (`class B(A): ... class C(B):`) or just siblings inheriting the same parent — the
  current pattern only proves the latter.
- Should overlapping constructs be de-duplicated per line, or is double-counting intentional
  (e.g. because a compound construct like a decorated static method *should* count toward both
  `staticmethod` and `decaratorfunc`)?
- Should the directory scan become recursive to support nested student-submission layouts?
