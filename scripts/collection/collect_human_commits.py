"""
export_human_pr_commit_files.py

Input: PR-level CSV with columns like:
id, number, title, user, ..., repo_url, html_url, ..., agent

Notes:
- id == pr_id
- agent is always "Human" (forced, not fetched)
- Uses GitHub API to:
    1) list commits in PR
    2) fetch commit details (stats + files + patch)
- Output: one row per file per commit, with columns:
sha pr_id author committer message commit_stats_total commit_stats_additions commit_stats_deletions
filename status additions deletions changes patch repo_id agent repo_url html_url

CLI:
  python export_human_pr_commit_files.py --input-csv pr_list.csv --out-csv out.csv --start-row 0 --max-rows 200
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Optional, Dict, Any, List
import datetime
import traceback
import time

import pandas as pd
import requests
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()

GITHUB_API = "https://api.github.com"


# -------------------------
# Logging helpers (SAME STYLE)
# -------------------------
def setup_logger(log_path: str):
    Path(os.path.dirname(log_path) or ".").mkdir(parents=True, exist_ok=True)

    def log(msg: str, *, also_print: bool = True):
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] {msg}"
        if also_print:
            print(line)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def log_exception(context: str, exc: Exception):
        log(f"ERROR: {context}: {exc}", also_print=True)
        tb = traceback.format_exc()
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(tb + "\n")

    return log, log_exception


# -------------------------
# Custom error for 403 (SAME IDEA)
# -------------------------
class ForbiddenError(Exception):
    pass


def get_github_token() -> str:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise RuntimeError(
            "GITHUB_TOKEN environment variable not set. "
            "Put it in your .env as GITHUB_TOKEN=..."
        )
    return token


def pick_first_existing(df: pd.DataFrame, candidates, required=True):
    for c in candidates:
        if c in df.columns:
            return c
    if required:
        raise KeyError(f"None of the candidate columns {candidates} exist in DataFrame.")
    return None


def extract_owner_repo_from_repo_url(repo_url: str) -> (str, str):
    """
    repo_url example: https://api.github.com/repos/getsentry/sentry
    """
    if not isinstance(repo_url, str) or not repo_url:
        raise ValueError("repo_url is missing/invalid")

    parsed = urlparse(repo_url)
    parts = [p for p in parsed.path.split("/") if p]  # e.g. ["repos","getsentry","sentry"]
    if "repos" in parts:
        i = parts.index("repos")
        if len(parts) >= i + 3:
            return parts[i + 1], parts[i + 2]
    raise ValueError(f"Cannot parse owner/repo from repo_url: {repo_url}")


def github_request(path_or_url: str, token: str, params=None, *, max_retries=3) -> Optional[Any]:
    """
    requests.get with auth + retry-on-403 logic (SAME BEHAVIOR AS YOUR FILE).
    If `path_or_url` starts with http, call it directly; else treat as API path under https://api.github.com
    """
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }

    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        url = path_or_url
    else:
        url = GITHUB_API + path_or_url

    for attempt in range(1, max_retries + 1):
        resp = requests.get(url, headers=headers, params=params, timeout=60)

        if resp.status_code == 404:
            return None

        if resp.status_code == 403:
            print(
                f"[403] Forbidden for {resp.url} "
                f"(attempt {attempt}/{max_retries}). "
                f"Sleeping 5 minutes before retry..."
            )
            time.sleep(60 * 5)
            continue

        resp.raise_for_status()
        return resp.json()

    raise ForbiddenError(f"403 Client Error: Forbidden for url: {url} after {max_retries} retries")


def list_pr_commits(repo_url: str, pr_number: str, token: str) -> List[Dict[str, Any]]:
    """
    GET /repos/{owner}/{repo}/pulls/{pull_number}/commits (paginated)
    """
    commits: List[Dict[str, Any]] = []
    per_page = 100
    page = 1

    while True:
        # Use repo_url directly to stay consistent with enterprise domains too.
        url = f"{repo_url}/pulls/{pr_number}/commits"
        data = github_request(url, token, params={"per_page": per_page, "page": page})
        if data is None:
            break
        if not isinstance(data, list):
            break

        commits.extend(data)
        if len(data) < per_page:
            break
        page += 1

    return commits


def get_commit_details(repo_url: str, sha: str, token: str) -> Optional[Dict[str, Any]]:
    """
    GET /repos/{owner}/{repo}/commits/{sha}
    """
    url = f"{repo_url}/commits/{sha}"
    data = github_request(url, token)
    if data is None:
        return None
    if isinstance(data, dict):
        return data
    return None


def get_repo_id(repo_url: str, token: str) -> Optional[int]:
    """
    GET repo_url (which is API URL) to get repo id
    """
    data = github_request(repo_url, token)
    if isinstance(data, dict):
        rid = data.get("id")
        return rid
    return None


def pick_name(commit_person_obj: Any, github_user_obj: Any) -> str:
    """
    Prefer commit['author']['name'] (git author) or commit['committer']['name'].
    Fall back to GitHub user login if available.
    """
    if isinstance(commit_person_obj, dict):
        if commit_person_obj.get("name"):
            return commit_person_obj["name"]
        if commit_person_obj.get("email"):
            return commit_person_obj["email"]

    if isinstance(github_user_obj, dict):
        if github_user_obj.get("login"):
            return github_user_obj["login"]

    return ""


def parse_args():
    p = argparse.ArgumentParser(description="Export human PR commit file rows using GitHub API.")
    p.add_argument("--input-csv", type=str, default="input_prs.csv", help="Input PR CSV path.")
    p.add_argument("--out-csv", type=str, default="human_commit_files.csv", help="Output CSV path.")
    p.add_argument("--log-path", type=str, default="export_human_pr_commit_files.log", help="Log file path.")
    p.add_argument("--start-row", type=int, default=0, help="0-based start row index for input CSV.")
    p.add_argument("--max-rows", type=int, default=None, help="Max rows to process from start-row.")
    return p.parse_args()


def main():
    args = parse_args()
    log, log_exception = setup_logger(args.log_path)

    token = get_github_token()

    log(f"Loading hf://datasets/hao-li/AIDev@68ed5f4b80/human_pull_request.parquet ...")
    # df = pd.read_csv(args.input_csv)
    df = pd.read_parquet("hf://datasets/hao-li/AIDev@68ed5f4b80/human_pull_request.parquet")

    pr_id_col = pick_first_existing(df, ["id", "pr_id"], required=True)  # your input uses id
    pr_number_col = pick_first_existing(df, ["number"], required=True)
    repo_url_col = pick_first_existing(df, ["repo_url"], required=True)
    # input has html_url for PR, but output wants commit html_url; still we keep repo_url column from input
    # html_url_col = pick_first_existing(df, ["html_url"], required=False)

    total_rows = len(df)
    start_row = args.start_row
    if start_row < 0 or start_row >= total_rows:
        raise ValueError(f"--start-row {start_row} out of range (0..{total_rows-1})")

    end_row = total_rows if args.max_rows is None else min(total_rows, start_row + int(args.max_rows))
    run_df = df.iloc[start_row:end_row].copy()
    run_total = len(run_df)

    log(f"Running rows [{start_row}:{end_row}] -> {run_total} rows")
    log(f"Output CSV: {Path(args.out_csv).resolve()}")
    log(f"Log file  : {Path(args.log_path).resolve()}")

    out_dir = os.path.dirname(args.out_csv)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    out_columns = [
        "sha",
        "pr_id",
        "author",
        "committer",
        "message",
        "commit_stats_total",
        "commit_stats_additions",
        "commit_stats_deletions",
        "filename",
        "status",
        "additions",
        "deletions",
        "changes",
        "patch",
        "repo_id",
        "agent",
        "repo_url",
        "html_url",
    ]

    # overwrite output
    pd.DataFrame(columns=out_columns).to_csv(args.out_csv, index=False, encoding="utf-8")

    repo_id_cache: Dict[str, Optional[int]] = {}

    written_rows = 0
    forbidden_triggered = False

    all_out_rows: List[Dict[str, Any]] = []

    for n, (idx, row) in enumerate(run_df.iterrows(), start=1):
        prefix = f"[{n}/{run_total}] [row={idx}]"
        try:
            pr_id = str(row.get(pr_id_col))
            pr_number = str(row.get(pr_number_col))
            repo_url = str(row.get(repo_url_col))

            agent = "Human"  # forced

            log(f"{prefix} PR id={pr_id} number={pr_number} repo_url={repo_url}")

            if repo_url not in repo_id_cache:
                repo_id_cache[repo_url] = get_repo_id(repo_url, token)
                log(f"{prefix} repo_id => {repo_id_cache[repo_url]}")
            repo_id = repo_id_cache[repo_url]

            pr_commits = list_pr_commits(repo_url, pr_number, token)
            log(f"{prefix} Found {len(pr_commits)} commits")

            for c in pr_commits:
                sha = c.get("sha", "")
                if not sha:
                    continue

                details = get_commit_details(repo_url, sha, token)
                if details is None:
                    # write a minimal row
                    all_out_rows.append({
                        "sha": sha,
                        "pr_id": pr_id,
                        "author": "",
                        "committer": "",
                        "message": "",
                        "commit_stats_total": "",
                        "commit_stats_additions": "",
                        "commit_stats_deletions": "",
                        "filename": "",
                        "status": "",
                        "additions": "",
                        "deletions": "",
                        "changes": "",
                        "patch": "",
                        "repo_id": repo_id if repo_id is not None else "",
                        "agent": agent,
                        "repo_url": repo_url,
                        "html_url": "",
                    })
                    written_rows += 1
                    continue

                commit_obj = details.get("commit", {}) or {}
                message = (commit_obj.get("message") or "").replace("\r\n", "\n")

                author_name = pick_name(commit_obj.get("author") or {}, details.get("author") or {})
                committer_name = pick_name(commit_obj.get("committer") or {}, details.get("committer") or {})

                stats = details.get("stats") or {}
                commit_stats_total = stats.get("total", "")
                commit_stats_additions = stats.get("additions", "")
                commit_stats_deletions = stats.get("deletions", "")

                commit_html_url = details.get("html_url", "")

                files = details.get("files") or []
                if not files:
                    all_out_rows.append({
                        "sha": sha,
                        "pr_id": pr_id,
                        "author": author_name,
                        "committer": committer_name,
                        "message": message,
                        "commit_stats_total": commit_stats_total,
                        "commit_stats_additions": commit_stats_additions,
                        "commit_stats_deletions": commit_stats_deletions,
                        "filename": "",
                        "status": "",
                        "additions": "",
                        "deletions": "",
                        "changes": "",
                        "patch": "",
                        "repo_id": repo_id if repo_id is not None else "",
                        "agent": agent,
                        "repo_url": repo_url,
                        "html_url": commit_html_url,
                    })
                    written_rows += 1
                    continue

                for fobj in files:
                    all_out_rows.append({
                        "sha": sha,
                        "pr_id": pr_id,
                        "author": author_name,
                        "committer": committer_name,
                        "message": message,
                        "commit_stats_total": commit_stats_total,
                        "commit_stats_additions": commit_stats_additions,
                        "commit_stats_deletions": commit_stats_deletions,
                        "filename": fobj.get("filename", ""),
                        "status": fobj.get("status", ""),
                        "additions": fobj.get("additions", ""),
                        "deletions": fobj.get("deletions", ""),
                        "changes": fobj.get("changes", ""),
                        "patch": fobj.get("patch", ""),
                        "repo_id": repo_id if repo_id is not None else "",
                        "agent": agent,
                        "repo_url": repo_url,
                        "html_url": commit_html_url,
                    })
                    written_rows += 1

            log(f"{prefix} Done PR #{pr_number}. Rows written so far: {written_rows}")

            # flush periodically so you can see progress in the output file
            if len(all_out_rows) >= 2000:
                pd.DataFrame(all_out_rows, columns=out_columns).to_csv(
                    args.out_csv, mode="a", header=False, index=False, encoding="utf-8"
                )
                all_out_rows.clear()
                log(f"{prefix} Flushed 2000 rows to disk (append).")

        except ForbiddenError as fe:
            forbidden_triggered = True
            log(f"{prefix} 🚫 {fe}")
            log(f"{prefix} Terminating early due to 403. Will flush what we have first.")
            break
        except Exception as e:
            log_exception(f"{prefix} error", e)
            continue

    # final flush
    if all_out_rows:
        pd.DataFrame(all_out_rows, columns=out_columns).to_csv(
            args.out_csv, mode="a", header=False, index=False, encoding="utf-8"
        )
        log(f"Final flush: appended {len(all_out_rows)} rows.")

    log("=== SUMMARY ===")
    log(f"Input rows intended : {run_total}")
    log(f"Rows written (file-per-commit rows): {written_rows}")
    log(f"Output CSV: {Path(args.out_csv).resolve()}")

    if forbidden_triggered:
        raise SystemExit("Stopped due to GitHub 403 (Forbidden). Output was flushed.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        sys.exit(130)
