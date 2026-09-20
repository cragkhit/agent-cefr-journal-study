#!/usr/bin/env python
"""
make_full_versions_human.py

Reads `data_csv/human_pr_commits.csv` and, for each row:
- uses `status` column:
    - if status in {"added", "new"}:
        -> only fetch AFTER (current commit) and save *_new.ext
    - if status in {"modified", "changed", "renamed", "copied"} or missing:
        -> fetch BEFORE (parent commit) + AFTER
    - if status == "removed":
        -> only BEFORE (file existed in parent, not in current commit)

- fetches FULL file content at:
    - parent commit  -> "before"
    - current commit -> "after"

- saves them into `results_human/` as:
    results_human/<owner>__<repo>__pr<pr_number>__<timestamp>__<sha>__<root>_before.ext
    results_human/<owner>__<repo>__pr<pr_number>__<timestamp>__<sha>__<root>_after.ext
    results_human/<owner>__<repo>__pr<pr_number>__<timestamp>__<sha>__<root>_new.ext
    results_human/<owner>__<repo>__pr<pr_number>__<timestamp>__<sha>__<root>_deleted.ext

- writes/APPENDS a summary CSV:
    data_csv/fetch_summary_human.csv

You can control:
    --start-row : 0-based index in human_pr_commits.csv to start from
    --max-rows  : max number of rows to process in this run
"""

import os
import base64
import datetime
from pathlib import Path
from typing import Optional, Dict, Tuple, Any, List

import argparse
import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

INPUT_CSV_DEFAULT = "data_csv/human_pr_commits.csv"
RESULTS_DIR_DEFAULT = Path("results_human")
SUMMARY_CSV_DEFAULT = Path("data_csv/fetch_summary_human.csv")

GITHUB_API = "https://api.github.com"


def get_github_token() -> str:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise RuntimeError(
            "GITHUB_TOKEN environment variable not set.\n"
            "Create a personal access token and put it in your .env as:\n"
            "  GITHUB_TOKEN=ghp_...\n"
        )
    return token


def compute_add_del_from_patch(patch: str):
    """Count additions and deletions from a unified diff patch string."""
    if not isinstance(patch, str):
        return 0, 0

    adds = 0
    dels = 0
    for line in patch.splitlines():
        if line.startswith("+++ ") or line.startswith("--- "):
            continue
        if line.startswith("+"):
            adds += 1
        elif line.startswith("-"):
            dels += 1
    return adds, dels


def github_request(path: str, token: str, params=None) -> Optional[Dict[str, Any]]:
    """Small helper around requests.get with auth and basic error handling."""
    headers = {"Authorization": f"token {token}"}
    resp = requests.get(GITHUB_API + path, headers=headers, params=params)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


def get_parent_sha(
    owner: str,
    repo: str,
    sha: str,
    token: str,
    cache: Dict[Tuple[str, str, str], Optional[str]],
) -> Optional[str]:
    """Get the first parent SHA of a commit, with caching."""
    key = (owner, repo, sha)
    if key in cache:
        return cache[key]

    data = github_request(f"/repos/{owner}/{repo}/commits/{sha}", token)
    if data is None:
        cache[key] = None
        return None

    parents = data.get("parents", [])
    if not parents:
        cache[key] = None
        return None

    parent_sha = parents[0].get("sha")
    cache[key] = parent_sha
    return parent_sha


def get_file_content(
    owner: str,
    repo: str,
    path: str,
    sha: str,
    token: str,
    cache: Dict[Tuple[str, str, str, str], Optional[str]],
) -> Optional[str]:
    """Get file content at a specific commit SHA, with caching."""
    key = (owner, repo, path, sha)
    if key in cache:
        return cache[key]

    data = github_request(
        f"/repos/{owner}/{repo}/contents/{path}",
        token,
        params={"ref": sha},
    )
    if data is None:
        cache[key] = None
        return None

    if data.get("encoding") == "base64":
        content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
    else:
        content = data.get("content", "")

    cache[key] = content
    return content


def build_commit_url(owner: str, repo: str, sha: str) -> str:
    """Build a clickable GitHub.com commit URL."""
    return f"https://github.com/{owner}/{repo}/commit/{sha}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-csv",
        default=INPUT_CSV_DEFAULT,
        help="Input commit-level CSV (default: data_csv/human_pr_commits.csv)",
    )
    parser.add_argument(
        "--results-dir",
        default=str(RESULTS_DIR_DEFAULT),
        help="Directory to store before/after/new files (default: results_human)",
    )
    parser.add_argument(
        "--summary-csv",
        default=str(SUMMARY_CSV_DEFAULT),
        help="Summary CSV path (default: data_csv/fetch_summary_human.csv)",
    )
    parser.add_argument(
        "--start-row",
        type=int,
        default=0,
        help="0-based row index in input CSV to start from (for resuming).",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=None,
        help="Max number of rows to process this run (from start-row).",
    )
    args = parser.parse_args()

    input_csv = Path(args.input_csv)
    results_dir = Path(args.results_dir)
    summary_csv = Path(args.summary_csv)

    if not input_csv.exists():
        raise SystemExit(f"Input CSV not found: {input_csv}")

    results_dir.mkdir(exist_ok=True, parents=True)
    summary_csv.parent.mkdir(exist_ok=True, parents=True)

    token = get_github_token()

    print(f"Loading {input_csv} ...")
    full_df = pd.read_csv(input_csv)

    total_rows = len(full_df)
    if args.start_row >= total_rows:
        raise SystemExit(
            f"start-row={args.start_row} >= total rows={total_rows}. Nothing to process."
        )

    if args.max_rows is None:
        df = full_df.iloc[args.start_row :]
    else:
        df = full_df.iloc[args.start_row : args.start_row + args.max_rows]

    num_rows = len(df)
    print(
        f"Total rows in CSV: {total_rows}. "
        f"Starting at row {args.start_row}. "
        f"Will process {num_rows} row(s) this run."
    )

    # Ensure additions/deletions exist
    if "additions" not in df.columns or "deletions" not in df.columns:
        print("No 'additions'/'deletions' in CSV; computing from patch...")
        adds, dels = [], []
        for p in df.get("patch", []):
            a, d = compute_add_del_from_patch(p)
            adds.append(a)
            dels.append(d)
        df["additions"] = adds
        df["deletions"] = dels

    parent_cache: Dict[Tuple[str, str, str], Optional[str]] = {}
    content_cache: Dict[Tuple[str, str, str, str], Optional[str]] = {}

    summary_rows: List[Dict[str, Any]] = []
    success_count = 0      # before+after
    new_file_count = 0     # new file only
    deleted_file_count = 0 # deleted only
    fail_count = 0

    # For progress display
    for i, (orig_idx, row) in enumerate(df.iterrows(), start=1):
        # indexes
        pr_row_index = row.get("pr_row_index", None)

        owner = str(row.get("owner"))
        repo = str(row.get("repo"))
        pr_number = row.get("pr_number")
        sha = str(row.get("sha"))
        path = str(row.get("filename"))
        file_status_raw = row.get("status")
        file_status = str(file_status_raw).lower() if isinstance(file_status_raw, str) else None

        print(f"[{i}/{num_rows}] idx={orig_idx}, pr_row_index={pr_row_index}, "
              f"{owner}/{repo} #{pr_number} {sha} {path}")

        row_summary = {
            "input_index": int(orig_idx),
            "pr_row_index": pr_row_index,
            "status": "fail",
            "reason": "",
            "owner": owner,
            "repo": repo,
            "pr_number": pr_number,
            "sha": sha,
            "path": path,
            "file_status": file_status,
            "commit_url": build_commit_url(owner, repo, sha),
            "before_path": "",
            "after_or_new_path": "",
        }

        try:
            patch = row.get("patch")
            if not isinstance(patch, str) or patch.strip() == "":
                row_summary["reason"] = "no patch"
                fail_count += 1
                summary_rows.append(row_summary)
                print("    Skipping: no patch")
                continue

            # Work out extension and safe filename
            base_name = os.path.basename(path)
            root, ext = os.path.splitext(base_name)
            if not ext:
                ext = ".txt"

            safe_root = root.replace("/", "_").replace("\\", "_")
            safe_owner = owner.replace("/", "_")
            safe_repo = repo.replace("/", "_")
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

            base = f"{safe_owner}__{safe_repo}__pr{pr_number}__{timestamp}__{sha}__{safe_root}"
            before_path = results_dir / f"{base}_before{ext}"
            after_path = results_dir / f"{base}_after{ext}"
            new_path = results_dir / f"{base}_new{ext}"
            deleted_path = results_dir / f"{base}_deleted{ext}"

            # ==== STATUS BRANCHES ===========================================
            # interpret GitHub statuses
            is_new_like = file_status in {"added", "new"}
            is_removed_like = file_status == "removed"
            # modified/changed/renamed/copied or unknown fall to "normal" path

            # ----- REMOVED: only BEFORE exists at parent commit -------------
            if is_removed_like:
                parent_sha = get_parent_sha(owner, repo, sha, token, parent_cache)
                if parent_sha is None:
                    row_summary["reason"] = "removed file but no parent commit"
                    fail_count += 1
                    summary_rows.append(row_summary)
                    print("    Removed file but no parent commit → fail")
                    continue

                before_content = get_file_content(
                    owner, repo, path, parent_sha, token, content_cache
                )
                if before_content is None:
                    row_summary["reason"] = "removed file, but file missing in parent"
                    fail_count += 1
                    summary_rows.append(row_summary)
                    print("    Removed file, file missing in parent → fail")
                    continue

                with open(deleted_path, "w", encoding="utf-8") as f:
                    f.write(before_content)

                row_summary["status"] = "deleted_file"
                row_summary["reason"] = "file removed in this commit"
                row_summary["before_path"] = str(deleted_path)
                row_summary["after_or_new_path"] = ""
                deleted_file_count += 1
                summary_rows.append(row_summary)
                print(f"    🗑️  Deleted file. Wrote {deleted_path.name}")
                continue

            # ----- NEW-LIKE: only AFTER exists at this commit ---------------
            if is_new_like:
                after_content = get_file_content(
                    owner, repo, path, sha, token, content_cache
                )
                if after_content is None:
                    row_summary["reason"] = "new file but after content not found"
                    fail_count += 1
                    summary_rows.append(row_summary)
                    print("    New file but after content not found → fail")
                    continue

                with open(new_path, "w", encoding="utf-8") as f:
                    f.write(after_content)

                row_summary["status"] = "new_file"
                row_summary["reason"] = "file added in this commit"
                row_summary["after_or_new_path"] = str(new_path)
                new_file_count += 1
                summary_rows.append(row_summary)
                print(f"    🆕 New file. Wrote {new_path.name}")
                continue

            # ----- MODIFIED / OTHER: BEFORE + AFTER -------------------------
            after_content = get_file_content(
                owner, repo, path, sha, token, content_cache
            )
            if after_content is None:
                row_summary["reason"] = "after content not found"
                fail_count += 1
                summary_rows.append(row_summary)
                print("    After content not found → fail")
                continue

            parent_sha = get_parent_sha(owner, repo, sha, token, parent_cache)
            if parent_sha is None:
                # no parent -> treat as new file
                with open(new_path, "w", encoding="utf-8") as f:
                    f.write(after_content)
                row_summary["status"] = "new_file"
                row_summary["reason"] = "no parent commit; treated as new"
                row_summary["after_or_new_path"] = str(new_path)
                new_file_count += 1
                summary_rows.append(row_summary)
                print("    No parent commit → treated as new file")
                continue

            before_content = get_file_content(
                owner, repo, path, parent_sha, token, content_cache
            )
            if before_content is None:
                # parent exists but file missing -> treat as new file
                with open(new_path, "w", encoding="utf-8") as f:
                    f.write(after_content)
                row_summary["status"] = "new_file"
                row_summary["reason"] = "file not present in parent; treated as new"
                row_summary["after_or_new_path"] = str(new_path)
                new_file_count += 1
                summary_rows.append(row_summary)
                print("    File missing in parent → treated as new file")
                continue

            with open(before_path, "w", encoding="utf-8") as f:
                f.write(before_content)
            with open(after_path, "w", encoding="utf-8") as f:
                f.write(after_content)

            row_summary["status"] = "success"
            row_summary["reason"] = ""
            row_summary["before_path"] = str(before_path)
            row_summary["after_or_new_path"] = str(after_path)
            success_count += 1
            summary_rows.append(row_summary)
            print(f"    ✅ Wrote {before_path.name} and {after_path.name}")

        except Exception as e:
            msg = f"error: {e}"
            print(f"    {msg}")
            row_summary["reason"] = msg
            fail_count += 1
            summary_rows.append(row_summary)
            continue

    # ---- Save / append summary CSV ----------------------------------------
    summary_df = pd.DataFrame(summary_rows)

    if summary_csv.exists():
        mode = "a"
        header = False
        print(f"\nAppending summary to {summary_csv}")
    else:
        mode = "w"
        header = True
        print(f"\nCreating summary at {summary_csv}")

    summary_df.to_csv(summary_csv, index=False, mode=mode, header=header)

    print("\n=== SUMMARY ===")
    print(f"Rows processed this run : {len(summary_rows)}")
    print(f"Success (before+after) : {success_count}")
    print(f"New file only          : {new_file_count}")
    print(f"Deleted file only      : {deleted_file_count}")
    print(f"Fail                   : {fail_count}")
    print(f"Summary CSV            : {summary_csv.resolve()}")
    print(f"Code files directory   : {results_dir.resolve()}")


if __name__ == "__main__":
    main()
