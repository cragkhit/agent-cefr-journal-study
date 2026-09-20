#!/usr/bin/env python3
"""
collect_human_pr_commits.py

Read human_pull_request.csv, and for each PR (human-written):
- parse owner/repo from repo_url or html_url
- use PR number to call GitHub API:
    /repos/{owner}/{repo}/pulls/{number}/commits
    /repos/{owner}/{repo}/commits/{sha}
- collect commit-file-level info (filename, additions, deletions, patch)
  filtered to .py and .js files.

Features:
1. --max-prs    : limit number of PRs processed this run
2. --start-row  : start from a given row index in the CSV (0-based)
3. Append results to an existing CSV safely (no header duplication).

Output:
  data_csv/human_pr_commits.csv (append-only)
"""

import os
import base64
from urllib.parse import urlparse
from pathlib import Path
from typing import Optional, Dict, Any, List

import argparse
import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

INPUT_CSV_DEFAULT = "data_csv/human_pull_request.csv"
OUTPUT_CSV_DEFAULT = "data_csv/human_pr_commits.csv"

GITHUB_API = "https://api.github.com"


def get_token() -> str:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise RuntimeError(
            "GITHUB_TOKEN environment variable not set.\n"
            "Create a GitHub personal access token and put it in your .env as:\n"
            "  GITHUB_TOKEN=ghp_your_token_here"
        )
    return token


def extract_owner_repo(repo_url: Optional[str], html_url: Optional[str]):
    """
    Parse owner/repo from repo_url or html_url.
    Works with:
      - https://github.com/owner/repo/pull/123
      - https://api.github.com/repos/owner/repo
    """
    url = repo_url or html_url
    if not url:
        raise ValueError("No repo_url or html_url available")

    parsed = urlparse(url)
    parts = [p for p in parsed.path.split("/") if p]

    if "repos" in parts:
        # /repos/owner/repo
        i = parts.index("repos")
        if len(parts) < i + 3:
            raise ValueError(f"Cannot parse owner/repo from URL: {url}")
        owner, repo = parts[i + 1], parts[i + 2]
    else:
        # /owner/repo/pull/123
        if len(parts) < 2:
            raise ValueError(f"Cannot parse owner/repo from URL: {url}")
        owner, repo = parts[0], parts[1]

    if repo.endswith(".git"):
        repo = repo[:-4]

    return owner, repo


def gh_get(path: str, token: str, params=None) -> requests.Response:
    headers = {"Authorization": f"token {token}"}
    resp = requests.get(GITHUB_API + path, headers=headers, params=params)
    # 404 / 410 etc. can happen; raise and catch outside
    resp.raise_for_status()
    return resp


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-csv",
        default=INPUT_CSV_DEFAULT,
        help="Path to human_pull_request.csv (default: data_csv/human_pull_request.csv)",
    )
    parser.add_argument(
        "--out-csv",
        default=OUTPUT_CSV_DEFAULT,
        help="Output CSV file for commit-level data (default: data_csv/human_pr_commits.csv)",
    )
    parser.add_argument(
        "--start-row",
        type=int,
        default=0,
        help="0-based row index in the input CSV to start from (for resuming).",
    )
    parser.add_argument(
        "--max-prs",
        type=int,
        default=None,
        help="Max number of PRs to process this run (from start-row).",
    )
    args = parser.parse_args()

    token = get_token()

    input_path = Path(args.input_csv)
    out_path = Path(args.out_csv)

    # Ensure output directory exists
    out_path.parent.mkdir(exist_ok=True, parents=True)

    if not input_path.exists():
        raise SystemExit(f"Input CSV not found: {input_path}")

    print(f"Reading PR list from: {input_path}")
    full_df = pd.read_csv(input_path)

    required_cols = ["number", "repo_url", "html_url"]
    for col in required_cols:
        if col not in full_df.columns:
            raise KeyError(f"Column '{col}' not found in {input_path}")

    total_rows = len(full_df)
    if args.start_row >= total_rows:
        raise SystemExit(
            f"start-row={args.start_row} >= total rows={total_rows}. Nothing to process."
        )

    # Slice the DataFrame based on start-row and max-prs
    if args.max_prs is None:
        df = full_df.iloc[args.start_row :]
    else:
        df = full_df.iloc[args.start_row : args.start_row + args.max_prs]

    num_prs_to_process = len(df)
    print(
        f"Total PR rows in CSV: {total_rows}. "
        f"Starting at row {args.start_row}. "
        f"Will process {num_prs_to_process} PR(s) this run."
    )

    rows: List[Dict[str, Any]] = []

    for i, (orig_idx, row) in enumerate(df.iterrows(), start=1):
        pr_number = int(row["number"])
        repo_url = row.get("repo_url")
        html_url = row.get("html_url")

        # For resume tracking, keep original row index from human_pull_request.csv
        pr_row_index = int(orig_idx)

        # Progress counter: i / num_prs_to_process
        print(f"[PR {i}/{num_prs_to_process}] row_index={pr_row_index}", end=" ")

        try:
            owner, repo = extract_owner_repo(repo_url, html_url)
        except Exception as e:
            print(f"→ skip (cannot parse owner/repo: {e})")
            continue

        print(f"→ {owner}/{repo} #{pr_number}")

        # 1) list commits in this PR
        try:
            resp = gh_get(f"/repos/{owner}/{repo}/pulls/{pr_number}/commits", token)
        except requests.HTTPError as e:
            print(f"    commits API failed: {e}")
            continue
        except Exception as e:
            print(f"    commits API unexpected error: {e}")
            continue

        commits = resp.json()
        if not isinstance(commits, list):
            print("    commits API returned non-list JSON, skipping.")
            continue

        for c in commits:
            sha = c.get("sha")
            if not sha:
                continue

            # 2) for each commit, get changed files
            try:
                resp2 = gh_get(f"/repos/{owner}/{repo}/commits/{sha}", token)
            except requests.HTTPError as e:
                print(f"    commit {sha} failed: {e}")
                continue
            except Exception as e:
                print(f"    commit {sha} unexpected error: {e}")
                continue

            data = resp2.json()
            files = data.get("files", [])
            if not isinstance(files, list):
                continue

            for f in files:
                filename = f.get("filename")
                if not isinstance(filename, str):
                    continue

                # Optional: filter to .py / .js files
                if not (filename.endswith(".py") or filename.endswith(".js")):
                    continue

                rows.append(
                    {
                        "pr_row_index": pr_row_index,  # row index in human_pull_request.csv
                        "owner": owner,
                        "repo": repo,
                        "pr_number": pr_number,
                        "sha": sha,
                        "filename": filename,
                        "status": f.get("status"),
                        "additions": f.get("additions"),
                        "deletions": f.get("deletions"),
                        "changes": f.get("changes"),
                        "patch": f.get("patch"),
                    }
                )

    if not rows:
        print("No commit-file rows collected in this run.")
        return

    out_df = pd.DataFrame(rows)

    # Append safely to CSV
    if out_path.exists():
        print(f"Appending {len(out_df)} rows to existing {out_path}")
        header = False
        mode = "a"
    else:
        print(f"Creating new commit CSV at {out_path}")
        header = True
        mode = "w"

    out_df.to_csv(out_path, index=False, mode=mode, header=header)
    print(f"Done. Now {len(out_df)} new rows written to {out_path}")
    print("Tip: you can inspect 'pr_row_index' to see which PR rows have been processed.")
    

if __name__ == "__main__":
    main()
