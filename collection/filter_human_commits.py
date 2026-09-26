#!/usr/bin/env python3
"""
filter_human_commits.py

Step between collect_human_commits.py and make_file_versions_human.py for the human group:
keep only Python files, and only PRs that were merged.

  data_csv/human_commit_data.csv  ->  data_csv/human_commit_data_py.csv

This filter was originally run as a one-off notebook cell; it is a script here so the human
pipeline can be followed end to end. The output is what make_file_versions_human.py was run
on (27,029 rows, 795 PRs):

  python make_file_versions_human.py --input-csv data_csv/human_commit_data_py.csv
"""

import argparse
import pandas as pd

# Pinned to the last AIDev v3 revision -- upstream's v4 deleted human_pull_request.
HUMAN_PRS = 'hf://datasets/hao-li/AIDev@68ed5f4b80/human_pull_request.parquet'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in-csv', default='data_csv/human_commit_data.csv')
    ap.add_argument('--out-csv', default='data_csv/human_commit_data_py.csv')
    ap.add_argument('--human-prs', default=HUMAN_PRS,
                    help='human_pull_request table (a local parquet copy also works)')
    args = ap.parse_args()

    df = pd.read_csv(args.in_csv)
    print(f'{len(df):,} file-level rows, {df.pr_id.nunique():,} PRs')

    df = df[df['filename'].str.endswith('.py', na=False)].reset_index(drop=True)
    print(f'{len(df):,} rows after keeping .py files')

    prs = pd.read_parquet(args.human_prs, columns=['id', 'merged_at'])
    df = df.merge(prs, left_on='pr_id', right_on='id', how='left').drop(columns='id')
    df = df[~df['merged_at'].isna()].reset_index(drop=True)
    print(f'{len(df):,} rows, {df.pr_id.nunique():,} PRs after keeping merged PRs')

    df.to_csv(args.out_csv, index=False)
    print(f'wrote {args.out_csv}')


if __name__ == '__main__':
    main()
