#!/usr/bin/env python3
"""Generate paste-ready ChatGPT batches for labelling the pre-ChatGPT PRs (RQ3).

Input : rq3_pre_chatgpt_prs_titles.csv  (needs pr_id, title, body)
Output: labelling_batches/batch_NN.txt  (each file = one ChatGPT message)

Follows Li et al. (arXiv:2507.15003) Section 4.1: each PR (title and body) is
classified into one of 11 Conventional Commits task categories.
"""
import csv, pathlib, sys

SRC = pathlib.Path("rq3_pre_chatgpt_prs_titles.csv")
OUT = pathlib.Path("labelling_batches")
BATCH = 25

TYPES = "build, chore, ci, docs, feat, fix, other, perf, refactor, style, test"

HEADER = """You are labelling GitHub pull requests by task type, following the Conventional
Commits specification.

For each PR below, output `pr_id`, `type`, `confidence`, `reason`.

- `type` must be exactly one of: {types}
- `confidence` is an integer from 3 to 10 (10 = the PR states its task type
  unambiguously; 3 = too vague to be sure)
- `reason` is one sentence explaining the choice

Judge from the PR title and body together. Some PRs have an empty body — judge from
the title alone in that case. If a PR is ambiguous, pick the most likely label and
lower the confidence rather than falling back to `other`. Reserve `other` for PRs
that genuinely fit no category; label a revert as `other`.

Assign exactly one label per PR.

Return CSV with the header `pr_id,type,confidence,reason`, one row per input PR and
nothing else — no commentary, no code fence. Quote the `reason` field. Preserve each
`pr_id` exactly as given: they are 10-digit integers, do not round, reformat, or
truncate them. Return exactly {n} rows, in the order given.

Input ({n} PRs):
"""


def main() -> int:
    if not SRC.exists():
        print(f"missing {SRC}", file=sys.stderr)
        return 1
    rows = list(csv.DictReader(SRC.open()))
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob("batch_*.txt"):
        old.unlink()

    batches = [rows[i:i + BATCH] for i in range(0, len(rows), BATCH)]
    for n, batch in enumerate(batches, 1):
        parts = [HEADER.format(types=TYPES, n=len(batch))]
        for r in batch:
            body = (r.get("body") or "").replace("\r\n", "\n").strip()
            parts.append(
                f"----- PR -----\n"
                f"pr_id: {r['pr_id']}\n"
                f"title: {r['title']}\n"
                f"body:\n{body if body else '(empty)'}\n"
            )
        (OUT / f"batch_{n:02d}.txt").write_text("\n".join(parts))

    print(f"{len(rows)} PRs -> {len(batches)} batches of <= {BATCH} in {OUT}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
