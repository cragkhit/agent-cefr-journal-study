#!/usr/bin/env python3
"""
Rebuild the AI-agent and human corpora exactly as used in the paper, and zip each
separately for hand-off.

Nothing is re-fetched. The files are already on disk from the original collection runs;
this script identifies which of them the paper actually used and packages those.

Provenance
----------
The authoritative record of what went into the paper is the fetch summary produced by
make_file_versions.py, filtered the same way report.ipynb cell 13 / cell 15 filter it:

  AI     data_csv/fetch_summary.csv        drop status=='fail', keep merged PRs
         -> Table 3 row 1: 591 PRs, 145 repos, 1,830 commits, 5,027 files
  Human  data_csv/human_fetch_summary.csv  drop status=='fail', keep merged PRs
         -> 785 PRs, 160 repos, 3,548 commits, 20,063 files

Each summary row carries before_path / after_or_new_path pointing at the real file on
disk, so the corpus is reconstructed by resolving those paths rather than by guessing
which results directory holds what.

Outputs
-------
  ai_agent_corpus.zip
  human_corpus.zip
  analysis_csv/paper_corpora_manifest.csv    per-file record incl. anything missing

Usage:
    python package_paper_corpora.py --dry-run     # report counts, write nothing
    python package_paper_corpora.py
"""

import argparse
import csv
import os
import sys
import time
import zipfile
from datetime import datetime

import pandas as pd

LOG_DIR = "log files"
MANIFEST = "analysis_csv/paper_corpora_manifest.csv"

# search roots for resolving a bare/relative path back to a real file
SEARCH_DIRS = [
    "results", "new_results", "results_human", "new_human_results",
    "human_results_2025-12-15", "human_results_31331",
    "ai_agents_results_merged", "ai_agents_results_64340",
]


def log_factory(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"=== package_paper_corpora {datetime.now().isoformat()} ===\n")

    def log(msg):
        line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
        print(line, flush=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    return log


def build_basename_index(log):
    """basename -> full path, for resolving paths whose directory has moved."""
    idx = {}
    for d in SEARCH_DIRS:
        if not os.path.isdir(d):
            continue
        n = 0
        for root, _dirs, files in os.walk(d):
            for fn in files:
                if fn.endswith(".py"):
                    idx.setdefault(fn, os.path.join(root, fn))
                    n += 1
        log(f"  indexed {n:>7,} .py under {d}/")
    log(f"  {len(idx):,} unique basenames indexed")
    return idx


def resolve(p, idx):
    if not isinstance(p, str) or not p.strip():
        return None
    p = p.strip().replace("\\", os.sep).replace("/", os.sep)
    if os.path.isfile(p):
        return p
    return idx.get(os.path.basename(p))


def select(summary_csv, merged_ids, log, label):
    """Apply the paper's filters and return the surviving summary rows."""
    s = pd.read_csv(summary_csv, low_memory=False)
    log(f"{label}: {len(s):,} summary rows")
    s = s[s["status"] != "fail"].copy()
    log(f"  after dropping status=='fail': {len(s):,}")
    if merged_ids is not None:
        s = s[s["pr_id"].astype(str).isin(merged_ids)].copy()
        log(f"  after keeping merged PRs   : {len(s):,}")
    log(f"  PRs={s.pr_id.nunique():,}  commits={s.sha.nunique():,}")
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log = log_factory(os.path.join(LOG_DIR, f"package_corpora_{ts}.log"))

    B = "hf://datasets/hao-li/AIDev@68ed5f4b80/"   # pinned to AIDev v3, see collect_commits.py
    log("loading merged-PR ids from AIDev ...")
    try:
        pr = pd.read_parquet(B + "pull_request.parquet", columns=["id", "merged_at"])
        hpr = pd.read_parquet(B + "human_pull_request.parquet", columns=["id", "merged_at"])
        ai_merged = set(pr[pr.merged_at.notna()].id.astype(str))
        hu_merged = set(hpr[hpr.merged_at.notna()].id.astype(str))
        log(f"  AI merged PRs={len(ai_merged):,}  human merged PRs={len(hu_merged):,}")
    except Exception as e:
        log(f"  WARNING: could not load AIDev ({e.__class__.__name__}); skipping merged filter")
        ai_merged = hu_merged = None

    log("indexing files on disk (this takes a minute) ...")
    idx = build_basename_index(log)

    jobs = [
        ("ai_agent", "data_csv/fetch_summary.csv", ai_merged, "ai_agent_corpus.zip"),
        ("human", "data_csv/human_fetch_summary.csv", hu_merged, "human_corpus.zip"),
    ]

    manifest = []
    for label, summary_csv, merged, zip_name in jobs:
        log("=" * 62)
        if not os.path.exists(summary_csv):
            log(f"{label}: MISSING {summary_csv} - skipping")
            continue
        s = select(summary_csv, merged, log, label)

        wanted, missing = {}, 0
        for _, r in s.iterrows():
            for col in ("before_path", "after_or_new_path"):
                real = resolve(r.get(col), idx)
                if real:
                    wanted[os.path.basename(real)] = real
                elif isinstance(r.get(col), str) and r.get(col).strip():
                    missing += 1
                    manifest.append({"corpus": label, "pr_id": r.get("pr_id"),
                                     "column": col, "recorded_path": r.get(col),
                                     "resolved": "", "status": "MISSING"})
        for bn, full in wanted.items():
            manifest.append({"corpus": label, "pr_id": "", "column": "",
                             "recorded_path": "", "resolved": full, "status": "OK"})

        log(f"  resolved {len(wanted):,} unique files   (unresolved refs: {missing:,})")
        if args.dry_run:
            log("  --dry-run: not writing zip")
            continue

        t0 = time.time()
        with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for i, (bn, full) in enumerate(sorted(wanted.items()), 1):
                z.write(full, os.path.join(label + "_corpus", bn))
                if i % 5000 == 0:
                    log(f"    zipped {i:,}/{len(wanted):,}")
            if os.path.exists(summary_csv):
                z.write(summary_csv, os.path.basename(summary_csv))
        mb = os.path.getsize(zip_name) / 1e6
        log(f"  -> {zip_name}  {len(wanted):,} files, {mb:.1f} MB, {time.time()-t0:.0f}s")

    os.makedirs(os.path.dirname(MANIFEST), exist_ok=True)
    pd.DataFrame(manifest).to_csv(MANIFEST, index=False)
    log(f"manifest: {MANIFEST}  ({len(manifest):,} rows)")
    log("done")


if __name__ == "__main__":
    main()
