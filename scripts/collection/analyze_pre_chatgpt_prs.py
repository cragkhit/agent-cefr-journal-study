#!/usr/bin/env python3
"""
Answer TD2 / TD3 from the output of collect_pre_chatgpt_prs.py, and sanity-check it.

TD2: how many of the TD1 repositories have >= 1 PR merged before the ChatGPT
     release (2022-11-30)?
TD3: min / max / mean / median number of such PRs per repository.

Kept separate from the collector so the statistics can be recomputed from the
saved CSV without re-hitting the GitHub API.

Usage:
    python analyze_pre_chatgpt_prs.py
"""

import argparse
import os

import pandas as pd

IN_CSV_DEFAULT = "analysis_csv/td2_td3_pre_chatgpt_prs.csv"
SUMMARY_CSV = "analysis_csv/td2_td3_summary.csv"
SHARE_CSV = "data/td2_td3_pre_chatgpt_prs.csv"
CUTOFF = "2022-11-30"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-csv", default=IN_CSV_DEFAULT)
    ap.add_argument("--expected", type=int, default=139)
    args = ap.parse_args()

    if not os.path.exists(args.in_csv):
        raise SystemExit(f"missing {args.in_csv} - run collect_pre_chatgpt_prs.py first")

    df = pd.read_csv(args.in_csv)
    n = len(df)

    print("=" * 66)
    print("SANITY CHECKS")
    print("=" * 66)
    print(f"rows                     : {n} (expected {args.expected})")
    if n != args.expected:
        print(f"  !! row count differs from expected {args.expected}")
    dupes = df.full_name.duplicated().sum()
    print(f"duplicate repos          : {dupes}" + ("   !! investigate" if dupes else ""))

    print("\nstatus breakdown:")
    print(df.status.value_counts().to_string())

    bad = df[df.status != "OK"]
    if len(bad):
        print(f"\nnon-OK repos ({len(bad)}):")
        print(bad[["full_name", "status", "note"]].to_string(index=False))

    nulls = df.pre_cutoff_merged_prs.isna().sum()
    print(f"\nnull pre_cutoff_merged_prs : {nulls}")
    if nulls:
        miss = df[df.pre_cutoff_merged_prs.isna()]
        print("  -- repos with no count:")
        print(miss[["full_name", "status", "note"]].to_string(index=False))
        gone = (miss.status == "NOT_FOUND").sum()
        if gone:
            print(f"  {gone} are NOT_FOUND: the repo no longer exists on GitHub. This is permanent -")
            print("  re-running will not help. Exclude them and report the reduced denominator.")
        transient = len(miss) - gone
        if transient:
            print(f"  {transient} failed for other reasons - delete those rows from the output CSV and")
            print("  re-run collect_pre_chatgpt_prs.py; resume will retry only the missing ones.")

    usable = df[df.pre_cutoff_merged_prs.notna()].copy()
    usable["pre_cutoff_merged_prs"] = usable.pre_cutoff_merged_prs.astype(int)

    # cross-validation: a repo created AFTER the cutoff cannot have PRs merged before it
    if "created_before_cutoff" in usable.columns:
        cb = usable.created_before_cutoff.astype(str).str.lower()
        viol = usable[(cb == "false") & (usable.pre_cutoff_merged_prs > 0)]
        print(f"\ncross-check (repo created after {CUTOFF} but has pre-cutoff merged PRs): {len(viol)}")
        if len(viol):
            print("  !! logically impossible - indicates a query or rename bug:")
            print(viol[["full_name", "repo_created_at", "pre_cutoff_merged_prs"]].to_string(index=False))
        else:
            print("  OK - no contradictions")
        n_old_repo = (cb == "true").sum()
        print(f"repos created before {CUTOFF}: {n_old_repo} / {len(usable)}")

    # ---------------- TD2 ----------------
    has_pre = usable[usable.pre_cutoff_merged_prs > 0]
    print("\n" + "=" * 66)
    print("TD2 - repos with >=1 PR merged before " + CUTOFF)
    print("=" * 66)
    print(f"{len(has_pre)} of {len(usable)} repos "
          f"({len(has_pre)/len(usable)*100:.1f}%)")
    print(f"repos with zero          : {len(usable) - len(has_pre)}")

    # ---------------- TD3 ----------------
    print("\n" + "=" * 66)
    print("TD3 - PRs merged before " + CUTOFF + ", per repo")
    print("=" * 66)

    def stats(s, label):
        if not len(s):
            print(f"{label}: (no repos)")
            return {}
        d = {
            "scope": label, "repos": len(s), "total_prs": int(s.sum()),
            "min": int(s.min()), "max": int(s.max()),
            "mean": round(float(s.mean()), 2), "median": float(s.median()),
        }
        print(f"{label}:")
        print(f"   repos={d['repos']}  total={d['total_prs']:,}  "
              f"min={d['min']}  max={d['max']}  mean={d['mean']}  median={d['median']}")
        return d

    rows = []
    rows.append(stats(usable.pre_cutoff_merged_prs, "all repos (zeros included)"))
    rows.append(stats(has_pre.pre_cutoff_merged_prs, "repos with >=1 only"))

    print("\ndistribution:")
    bins = [(0, 0), (1, 9), (10, 49), (50, 199), (200, 999), (1000, 10**9)]
    for lo, hi in bins:
        c = ((usable.pre_cutoff_merged_prs >= lo) & (usable.pre_cutoff_merged_prs <= hi)).sum()
        label = f"{lo}" if lo == hi else (f"{lo}-{hi}" if hi < 10**9 else f"{lo}+")
        print(f"   {label:>9} PRs : {c:3d} repos  {'#' * min(c, 50)}")

    print("\ntop 15 repos by pre-cutoff merged PRs:")
    print(has_pre.nlargest(15, "pre_cutoff_merged_prs")[
        ["full_name", "pre_cutoff_merged_prs", "repo_created_at", "stars", "n_agent_prs"]
    ].to_string(index=False))

    os.makedirs("analysis_csv", exist_ok=True)
    pd.DataFrame([r for r in rows if r]).to_csv(SUMMARY_CSV, index=False)
    os.makedirs("data", exist_ok=True)
    df.to_csv(SHARE_CSV, index=False)
    print(f"\nsaved: {SUMMARY_CSV}")
    print(f"saved: {SHARE_CSV}  (small, shareable with the professor)")


if __name__ == "__main__":
    main()
