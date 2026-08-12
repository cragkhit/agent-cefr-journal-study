# Experiment Notes

A running log of major decisions made while working with this repo. Newest entries at the
bottom. Keep this updated any time a non-obvious choice is made about how to explore, document,
run, or modify this codebase.

## 2026-08-08

- **Cloned the repo as-is, unmodified.** Source: `https://github.com/swindlemek/codeProficiencyExtraction`,
  cloned into `/home/chaiyong.rag/pycefr/codeProficiencyExtraction`. No code changes made yet —
  this phase was read-only exploration.

- **Documented architecture understanding directly in `README.md` rather than a separate
  design doc.** Rationale: the existing README was already the user-facing usage doc; folding
  architecture notes into it keeps one canonical reference instead of splitting
  usage-vs-internals across files. Sections added: Architecture, Known limitations/rough
  edges, Open questions. Kept the original Installation/Usage/Output Format sections intact.

- **Flagged (but did not fix) several rough edges found during reading**, to avoid changing
  behavior before the user asks for it:
  - `pdfminer.six` is a listed dependency but unused by `extractCodeFromDir.py`.
  - The "page" abstraction (`{1: content}` in `extract_text_from_py`) looks vestigial from an
    earlier PDF-based version of the tool.
  - Construct regexes overlap (not mutually exclusive), so per-line double-counting across
    construct types is possible and appears to be the current (undocumented) behavior rather
    than a bug that's been fixed.
  - `ubersequenceLevel.csv` has `Node`/`Final Group`/`Percentage` columns that
    `load_construct_level_mapping` does not read.
  - `process_directory` scans `input_dir` non-recursively.

- **Created this file (`exp_notes.md`) as a decision log**, separate from `README.md`.
  Rationale: `README.md` should stay a description of *what the tool is and how to use it*;
  this file tracks *why* choices were made along the way (exploration decisions, judgment
  calls, things deliberately left alone) — a different audience/purpose than the README.

- **Moved `README.md` and `exp_notes.md` from `codeProficiencyExtraction/` up to the
  `pycefr/` root**, per explicit user request, so they live alongside (not inside) the cloned
  repo. Left the repo's original tracked `README.md` deleted rather than restoring the
  upstream version — this shows as `D README.md` in `git status` inside
  `codeProficiencyExtraction/`. Flagged to the user; not yet resolved one way or the other.

- **Restored the original upstream `README.md` inside `codeProficiencyExtraction/`** via
  `git checkout -- README.md`, per user request. The repo now has both its unmodified
  original README and, one level up at `pycefr/README.md`, the expanded version with
  architecture notes — these are two distinct files going forward, not one being duplicated;
  changes to one won't propagate to the other.

- **Read the motivating paper (ACM DOI 10.1145/3769864, pasted by the user) and added a
  "Motivation & Related Research" section to `README.md`, plus tightened the "Unused CSV
  columns" limitation entry.** Decision: fold this into the existing README rather than a new
  file, since it's context for the same architecture, not a separate concern.
  Key finding worth calling out here: this repo's tool is a descendant of **pycefr**, whose
  A1–C2 assignments were manually/subjectively defined (author opinion + informal surveys) —
  the exact gap the paper closes empirically via 22 introductory-textbook mining
  (`Übersequence`, RQ1) and Louvain graph clustering (RQ2, 6 stable clusters of sizes
  27/28/15/26/8/19). Strong circumstantial evidence that `ubersequenceLevel.csv`'s `Index`
  column *is* the paper's Übersequence (118 of 138 constructs appear in textbooks — matches
  the CSV's Index range exactly) and `Final Group`/`Percentage` are the paper's clustering
  result — columns the script currently ignores in favor of cruder equal-width `Index`
  binning. Not yet confirmed with the user whether this is intentional or a bug to fix.
  Also noted: `pdfminer.six` and the vestigial "page" dict shape are explained now — the
  paper's own construct-extraction pipeline ran PDFMiner over textbook PDFs page-by-page; this
  script looks like a repointed/adapted copy of that pipeline aimed at `.py` files instead.

- **Verified the tool actually runs**, using a hand-written sample file in the session
  scratchpad (not committed anywhere) rather than modifying the repo. Confirmed:
  `python3 extractCodeFromDir.py <input_dir> <output_dir>` works out of the box with
  pandas/numpy already installed (pandas 2.3.3, numpy 2.2.6, Python 3.10.6) —
  `pdfminer.six` was not needed, consistent with it being unused. Confirmed the CWD
  requirement is real: the script must be invoked with `codeProficiencyExtraction/` as the
  working directory, since `REGEX_FILE`/`MAPPING_CSV` are relative paths. The sample run's
  output also confirmed the previously-logged overlapping-construct behavior in practice —
  e.g. one `try/except/finally` block was counted under `tryexcept`, `tryfinally`, and
  `tryexceptfinally` simultaneously, and `range(10)` appearing twice on one line was counted
  twice under `rangefunc`.

- **Read the MSR'26 paper (arXiv:2604.00299) the user is extending into a journal paper**,
  using `codeProficiencyExtraction` in place of pycefr. Extracted its PDF text via pdfminer
  (installed `pdfminer.six` for python3.10 with `python3 -m pip install --user`, since the
  system `pip` resolved to a mismatched python3.9 install — WebFetch's own PDF text extraction
  was unreliable/partly fabricated for this file and flagged itself as such, so went straight
  to the source PDF instead of trusting that summary). Confirmed the user (cragkhit@gmail.com)
  is Chaiyong Ragkhitwetsagul, a co-author of this paper and of pycefr itself — upgraded from
  a tentative hint to a confirmed identity in memory.
  Added a "paper this tool is meant to power" subsection to `README.md`'s Motivation section,
  identifying two concrete gaps to close before the pycefr→codeProficiencyExtraction swap is
  methodologically faithful: (1) no before/after differential construct counting exists in
  this repo (the MSR paper's core technique for isolating PR-added code — reconstructs
  before/after file versions from GitHub diffs, takes `max(after−before, 0)` per construct);
  (2) the already-logged `Final Group`-vs-naive-binning gap, which matters more now since the
  whole point of the swap is presumably to use the more rigorous levels. Did not implement
  either fix — just identified and documented them, pending direction from the user on how
  they want to proceed with the extension.

- **Downloaded the AI-agent-PR code corpus from the user's Google Drive link and placed it at
  `/home/chaiyong.rag/pycefr/data/`** (`ai_agent_corpus.zip`, extracted to `ai_agent_corpus/`
  + `ai_fetch_summary.csv`). The Drive MCP connector (`mcp__claude_ai_Google_Drive__*`)
  rejected every call with "insufficient authentication scopes," including on this
  single-file share link, so downloaded via a plain `curl` against Google's public
  `drive.usercontent.google.com/download` confirm-flow instead (the file is >32MB, past
  Google's virus-scan size limit, so it required parsing the "Download anyway" HTML form's
  hidden `id`/`export`/`confirm`/`uuid` fields and resubmitting them as a GET). Chose to keep
  this data outside the `codeProficiencyExtraction` git repo (it's not source code, and the
  repo's `.gitignore` isn't guaranteed to cover a `data/` dir) — placed as a sibling directory
  under `pycefr/` instead, alongside `README.md`/`exp_notes.md`.
  Verified contents: 8,592 `.py` files (3,721 before/after pairs + 1,150 new-file singles),
  591 PRs / 145 repos — matches the MSR paper's Table 2 "Collected merged PRs" counts almost
  exactly. `ai_fetch_summary.csv` gives per-file fetch metadata (owner/repo/pr_id/sha/path,
  before_path/after_or_new_path, status) but has **no AI-agent-identity or PR-task-type
  column** — that'll have to come from elsewhere (the broader AIDev dataset) to reproduce
  RQ1/RQ3. Did not yet write any code to process this corpus.

- **Grouped `ai_agent_corpus/`'s 8,592 files into per-repo subfolders** at
  `/home/chaiyong.rag/pycefr/data/ai_agent_corpus_by_repo/{owner}__{repo}/`, per user request.
  Repo key = the first two `__`-separated fields of each filename (confirmed via
  `ai_fetch_summary.csv`'s `owner`/`repo` columns matching those fields exactly on the sample
  checked) — 142 repo folders, matching the earlier-logged unique-repo count. Used `os.link`
  (hardlinks) rather than copying, since both directories are on the same filesystem — this
  avoids doubling the 158MB footprint, but means the two directory trees share inode data:
  editing a file in one location edits it in the other too. Left the original
  `ai_agent_corpus/` flat directory in place rather than replacing it, since some future step
  (e.g. running the tool once over everything, or joining against `ai_fetch_summary.csv` by
  basename) may prefer the flat layout — the two are just different views of the same files.

- **Diagnosed and fixed a catastrophic-backtracking (ReDoS) bug in
  `regularExpressionList.json`** that was hanging the batch run on `514-labs__moose`.
  Root cause, found by timing each of the ~140 regexes individually against the offending
  file with a `signal.alarm` guard: (1) several `try*`/`metaclass3` patterns had a `.*`
  immediately adjacent to an unbounded `[\s\S]*` — ambiguous overlap (`.` is a subset of
  `[\s\S]`) forces exhaustive backtracking over every split; (2) some of those same patterns
  chain 2–3 unbounded wildcards (try→except→else→finally), which multiplies into polynomial
  blowup on real code with multiple except/else/finally occurrences — confirmed empirically
  (unbounded: hangs indefinitely; bounded to `{0,5000}`: still 1.9–5+s; bounded to `{0,300}`:
  ~0.04s). Fix applied in two passes: removed the redundant adjacent `.*` (9 places), then
  bounded all 14 multi-line `[\s\S]*`/`[\s\S]*?` wildcards to `[\s\S]{0,300}?` (~5–8 lines of
  slack, generous for a real try/except block, small enough to cap worst-case backtracking).
  Verified against the original moose file and the 5 largest files in the whole 8,592-file
  corpus (up to 405KB) — no more timeouts anywhere; large files just take proportionally
  longer (12–17s for ~400KB), which is legitimate linear-time cost, not backtracking blowup.
  Re-ran the earlier `calc.py` regression sample — identical construct counts to pre-fix,
  confirming no behavior change on normal-sized files.
  This modifies the vendored `regularExpressionList.json` inside the git-tracked
  `codeProficiencyExtraction/` repo (shows as `M regularExpressionList.json` in `git status`,
  not committed) — a deliberate, explicitly user-requested divergence from upstream, done
  in-place rather than as a separate patch file since the whole point was to unblock the
  batch-run script that reads this file directly.

- **Opened a PR upstream for the regex fix**: https://github.com/swindlemek/codeProficiencyExtraction/pull/1
  (branch `fix/redos-try-except-patterns`, from fork `cragkhit/codeProficiencyExtraction`).
  Needed to install `gh` CLI first — not present on this machine and no sudo available, so
  installed the release binary directly to `~/.local/bin/gh` (already on `PATH`) rather than
  via apt. The user authenticated it themselves (`gh auth login`, device-code flow) since that
  has to be their own GitHub identity, not something done on their behalf. `origin` on the
  local clone still points at upstream (`swindlemek/...`); added a second remote named `fork`
  pointing at the user's fork rather than repointing `origin`, so the existing setup
  (`REGEX_FILE`/`MAPPING_CSV` relative-path assumptions, run scripts, etc.) stays unaffected.
  Also had to run `gh auth setup-git` — plain `git push` over HTTPS failed
  ("could not read Username") until git was told to use gh's stored credentials.

- **Added a 31-test regression suite for the ReDoS fix and pushed it as a follow-up commit to
  the same PR** (`tests/test_redos_fix.py` + `tests/fixtures/redos_trigger_sample.py`, the
  latter being a real copy of the `514-labs__moose` file that originally hung the tool).
  Rejected my first draft of the synthetic adversarial generator once I discovered it didn't
  reproduce the bug at all (a shape that eventually *matches* lets the regex engine exit early
  regardless of distance — only a shape with **no valid match anywhere** forces the exhaustive
  worst case; only `tryexceptelsefinally`/`tryexceptfinally` were ever confirmed to actually
  hang). Verified the final suite discriminates correctly by temporarily restoring the pre-fix
  `regularExpressionList.json` from backup and re-running: 9/31 tests correctly fail/timeout
  (all and only the ones tied to the real bug), the other 22 independent correctness/
  specificity checks pass unchanged on both versions — confirms the suite isn't just trivially
  green. Committed and pushed to the `fork` remote's `fix/redos-try-except-patterns` branch,
  which auto-updated PR #1; also left a summary comment on the PR.

- **Ran the full batch extraction over all 142 repos** (`run_extraction_by_repo.sh`, in the
  background) now that the ReDoS fix is in place. Completed cleanly: 142/142 repos, 0
  failures, ~3h17m (11,774s) total, 8,592 files accounted for (matches the corpus exactly),
  164MB of output CSVs in `data/output_by_repo/`. No hangs anywhere across the full real-world
  corpus — the strongest validation yet that the fix holds at scale, not just on the
  hand-picked test cases. Aggregate level distribution across all files: A1 69.6%, A2 12.1%,
  B1 7.9%, B2 7.4%, C1 2.5%, C2 0.4% — heavily Basic-skewed, qualitatively similar in shape to
  the MSR paper's pycefr-based finding, though **not yet directly comparable**: this still
  uses the naive equal-width `Index` binning (not `Final Group`) and whole-file counts (not
  the before/after differential the MSR methodology needs). Both gaps remain open (see the
  "Motivation & Related Research" section of `README.md`).

- **Published this study as its own repo**: https://github.com/cragkhit/agent-cefr-journal-study
  (the target repo already existed, empty/placeholder). Per explicit user choices: included
  the full raw corpus (not just derived CSVs), and referenced the tool by URL/PR link rather
  than vendoring its code. Built it in a fresh clone of the target repo (not a `git init` in
  `pycefr/`), to inherit its existing placeholder commit cleanly rather than dealing with
  unrelated-history merge issues.
  Two judgment calls made without a further round of questions, both explained in the new
  repo's README: (1) dropped `ai_agent_corpus.zip` and `ai_agent_corpus_by_repo/` from the
  push — both are byte-identical duplicates of `ai_agent_corpus/` under a different
  packaging/layout, so including them would only add ~190MB for zero new information;
  `ai_agent_corpus_by_repo/` regenerates in seconds via a new `scripts/group_by_repo.py`.
  (2) Wrote a new top-level `README.md` specific to the study repo (what it replicates, links
  to the tool fork/PR, data layout, reproduction steps) rather than reusing the
  tool-architecture README verbatim — moved that content to `docs/tool-notes.md` with a
  preamble clarifying it describes the separate (unvendored) tool repo.
  Also made `run_extraction_by_repo.sh` portable: it previously hardcoded this machine's
  absolute paths (`/home/chaiyong.rag/pycefr/...`); now it takes `TOOL_DIR` as an env var and
  resolves its own data paths relative to the script's location, so it works for anyone who
  clones the study repo. Total push: 324MB, 8,742 files, well under GitHub's per-file/repo
  limits (largest single file ~21MB), no Git LFS needed.

- **Downloaded a second corpus ("human PRs") and ran the same pipeline** — 140MB
  `human_corpus.zip` from a Google Drive link (same curl-against-`drive.usercontent.google.com`
  workaround as before), extracted to 36,757 files / 785 PRs / 160 repos (matches the MSR
  paper's 785-human-PR figure), grouped by repo via the same `group_by_repo.py` logic, and
  parameterized `run_extraction_by_repo.sh` with `INPUT_ROOT`/`OUTPUT_DIR` env vars (default
  unchanged) instead of writing a second near-duplicate script.

- **Found and fixed a second wave of ReDoS bugs while running the human-PR batch** — this one
  much more severe in impact (the batch run appeared to hang for 19+ hours on
  `tinygrad__tinygrad` before being caught). Root cause was the same overlap-ambiguity anti-
  pattern as the original fix, but manifesting in same-line wildcards (`.*`/`.+`) rather than
  the multi-line `[\s\S]*` already addressed. Two-stage fix, both verified necessary via direct
  experiment (not assumed):
  1. Bounded all 103 patterns with bare `.*`→`.{0,200}` / `.+`→`.{1,200}`, and fixed a
     pre-existing `nestedTuple` bug (ended in `\])` instead of `\))`, meaning it could never
     legitimately match a real tuple — an "always fails" pattern is the worst case for
     backtracking, since every tuple-shaped line forced a full futile search.
  2. That bounding alone was NOT sufficient — confirmed empirically that `\w+` immediately
     followed by a bounded wildcard still hangs on real lines up to ~4,200 characters long
     (a real length found in the crewAI/tinygrad corpus files), because cost scales as
     `line_length × bound^k` regardless of how small the bound is once the pattern chains
     multiple wildcards and the line never matches. Fixed by merging the adjacent overlapping
     quantifiers into one (`\w+.{0,200}` → `\w.{0,200}`), which is the actual fix — bounding
     alone was a dead end for this shape of bug. Verified: the worst synthetic case (4,200-char
     line) now runs all 136 patterns in ~2.8s (previously indefinite hang); the real tinygrad
     file that hung 19+ hours in production now completes in ~4.5s.
  Added 18 more regression tests (`tests/test_bare_wildcard_fix.py`) plus a second real
  trigger-file fixture, verified (as before) to discriminate correctly against both
  intermediate pre-fix states, not just trivially pass. Pushed both fixes as additional
  commits on the same open PR (#1) rather than a new one, since it's clearly the same class of
  bug in the same file, just a different manifestation the first fix's test corpus (AI-agent
  PRs) never happened to trigger.

- **Completed the full human-PR batch run**: all 160 repos, 0 failures, 36,757 files
  accounted for exactly (matches corpus size), 746MB of output CSVs in
  `data/output_by_repo_human/`. Did not yet push this to the study repo — pending the user's
  answer on whether to commit now or wait (asked once, got interrupted by the "is it stuck"
  investigation above; re-asked after this completion).
