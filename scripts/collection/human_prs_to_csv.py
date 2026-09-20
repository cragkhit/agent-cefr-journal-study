#!/usr/bin/env python3
"""
human_prs_parquet_to_csv.py

Read the local human_pull_request.parquet file
and convert it to a CSV file inside data_csv/ directory.
"""

from pathlib import Path
import argparse
import pandas as pd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--in-parquet",
        default="human_pull_request.parquet",
        help="Input parquet filename",
    )
    parser.add_argument(
        "--out-csv",
        default="human_pull_request.csv",
        help="Output CSV filename (inside data_csv/)",
    )
    args = parser.parse_args()

    in_path = Path(args.in_parquet)
    if not in_path.exists():
        raise SystemExit(f"Input parquet not found: {in_path}")

    # Ensure output folder exists
    out_dir = Path("data_csv")
    out_dir.mkdir(exist_ok=True)

    out_path = out_dir / args.out_csv

    print(f"Reading parquet: {in_path}")
    df = pd.read_parquet(in_path)
    print(f"Loaded {len(df):,} rows, {len(df.columns)} columns.")

    df.to_csv(out_path, index=False)
    print(f"Saved CSV → {out_path.resolve()}")


if __name__ == "__main__":
    main()
