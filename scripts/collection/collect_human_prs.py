#!/usr/bin/env python3
"""
collect_human_prs.py

Download the human_pull_request table from the AIDev dataset
and save it as a local Parquet file.
"""

from pathlib import Path
import pandas as pd

# Pinned to the last AIDev v3 revision (2026-05-10). On 2026-08-21 upstream promoted v4
# to main, which deleted pr_task_type / human_pr_task_type / human_pull_request and
# replaced pull_request with a much larger table. Every number in the paper is v3.
BASE = "hf://datasets/hao-li/AIDev@68ed5f4b80/"
REMOTE_TABLE = BASE + "human_pull_request.parquet"
LOCAL_PARQUET = Path("human_pull_request.parquet")


def main():
    print(f"Reading remote table: {REMOTE_TABLE}")
    df = pd.read_parquet(REMOTE_TABLE)
    print(f"Loaded {len(df):,} rows with {len(df.columns)} columns.")

    df.to_parquet(LOCAL_PARQUET, index=False)
    print(f"Saved local parquet -> {LOCAL_PARQUET.resolve()}")


if __name__ == "__main__":
    main()
