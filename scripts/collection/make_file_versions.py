"""
make_full_versions.py

Reads INPUT_CSV and, for each row:
- uses `status` column when available:
    - if status == "new"    -> only fetch AFTER (current commit) and save *_new.ext
    - if status == "modified" or others -> fetch BEFORE (parent commit) + AFTER

- fetches the FULL file content at:
    - parent commit  -> "before"
    - current commit -> "after"
- saves them into RESULTS_DIR as:
    <owner>__<repo>__pr<pr_id>__<timestamp>__<sha>__<root>_before.ext
    <owner>__<repo>__pr<pr_id>__<timestamp>__<sha>__<root>_after.ext

If it's a completely new file:
- save only:
    ..._new.ext

Also produces (APPEND MODE):
- SUMMARY_CSV : one row per processed row in this run, appended (not overwritten)

CLI examples:
  python make_full_versions.py --start-row 500 --max-rows 200
  python make_full_versions.py --input-csv data_csv/new_data.csv --results-dir new_results
"""

import os
import sys
import base64
import argparse
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional, Dict, Tuple, Any, List
import datetime
import traceback

import pandas as pd
import requests
from dotenv import load_dotenv

import time

load_dotenv()

GITHUB_API = "https://api.github.com"


# -------------------------
# Logging helpers
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
# Custom error for 403
# -------------------------
class ForbiddenError(Exception):
    pass


def get_github_token() -> str:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise RuntimeError(
            "GITHUB_TOKEN environment variable not set. "
            "Create a personal access token and put it in your .env as GITHUB_TOKEN=..."
        )
    return token


def pick_first_existing(df: pd.DataFrame, candidates, required=True):
    """Pick the first column name that exists in df from candidates."""
    for c in candidates:
        if c in df.columns:
            return c
    if required:
        raise KeyError(f"None of the candidate columns {candidates} exist in DataFrame.")
    return None


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


def extract_owner_repo(repo_url: Optional[str], html_url: Optional[str]):
    """
    Parse owner/repo from repo_url or html_url.
    Works with:
      - https://github.com/<owner>/<repo>
      - https://api.github.com/repos/<owner>/<repo>
      - https://github.mycompany.com/api/v3/repos/<owner>/<repo>
    """
    url = repo_url or html_url
    if not isinstance(url, str) or not url:
        raise ValueError("No repo_url or html_url available.")

    parsed = urlparse(url)
    parts = [p for p in parsed.path.split("/") if p]

    if "repos" in parts:
        i = parts.index("repos")
        if len(parts) >= i + 3:
            owner, repo = parts[i + 1], parts[i + 2]
        else:
            raise ValueError(f"Cannot parse owner/repo from URL: {url}")
    else:
        if len(parts) < 2:
            raise ValueError(f"Cannot parse owner/repo from URL: {url}")
        owner, repo = parts[0], parts[1]

    if repo.endswith(".git"):
        repo = repo[:-4]

    return owner, repo


def build_commit_url(
    repo_url: Optional[str],
    html_url: Optional[str],
    owner: str,
    repo: str,
    sha: str,
    pr_id: Any,
) -> str:
    base = None

    if isinstance(html_url, str) and html_url:
        parsed = urlparse(html_url)
        base = f"{parsed.scheme}://{parsed.netloc}"
    elif isinstance(repo_url, str) and repo_url:
        parsed = urlparse(repo_url)
        if parsed.netloc == "api.github.com":
            base = "https://github.com"
        else:
            base = f"{parsed.scheme}://{parsed.netloc}"

    if not base:
        return ""

    return f"{base}/{owner}/{repo}/commit/{sha}"


def github_request(path: str, token: str, params=None, *, max_retries=3) -> Optional[Dict[str, Any]]:
    """
    requests.get with auth + retry-on-403 logic.
    On 403:
      - sleep 5 minutes
      - retry the SAME request
    """
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }

    for attempt in range(1, max_retries + 1):
        resp = requests.get(
            GITHUB_API + path,
            headers=headers,
            params=params,
            timeout=60,
        )

        # ---------- 404 ----------
        if resp.status_code == 404:
            return None

        # ---------- 403 (rate limit / secondary limit) ----------
        if resp.status_code == 403:
            print(
                f"[403] Forbidden for {resp.url} "
                f"(attempt {attempt}/{max_retries}). "
                f"Sleeping 5 minutes before retry..."
            )
            time.sleep(60 * 5)
            continue  # retry SAME request

        # ---------- other errors ----------
        resp.raise_for_status()
        return resp.json()

    # If we reach here, retries exhausted
    raise ForbiddenError(
        f"403 Client Error: Forbidden for url: {GITHUB_API + path} "
        f"after {max_retries} retries"
    )



def get_parent_sha(
    owner: str,
    repo: str,
    sha: str,
    token: str,
    cache: Dict[Tuple[str, str, str], Optional[str]],
) -> Optional[str]:
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


def append_summary_csv(summary_df: pd.DataFrame, summary_csv_path: str):
    """Append summary rows to SUMMARY_CSV without overwriting."""
    out_dir = os.path.dirname(summary_csv_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    file_exists = os.path.exists(summary_csv_path)

    summary_df.to_csv(
        summary_csv_path,
        mode="a",
        header=not file_exists,
        index=False,
        encoding="utf-8",
    )


def parse_args():
    parser = argparse.ArgumentParser(description="Fetch before/after full file versions from GitHub.")
    parser.add_argument(
        "--input-csv",
        type=str,
        default="data_csv/new_data.csv",
        help="Path to input CSV.",
    )
    parser.add_argument(
        "--results-dir",
        type=str,
        default="new_results",
        help="Directory to write fetched files.",
    )
    parser.add_argument(
        "--summary-csv",
        type=str,
        default="data_csv/new_fetch_summary.csv",
        help="Path to summary CSV (appended, not overwritten).",
    )
    parser.add_argument(
        "--log-path",
        type=str,
        default="make_full_versions_log.txt",
        help="Path to log file.",
    )
    parser.add_argument(
        "--start-row",
        type=int,
        default=0,
        help="0-based row index in the input CSV to start from (for resuming).",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=None,
        help="Max number of rows to process this run (from start-row).",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    log, log_exception = setup_logger(args.log_path)

    input_csv = args.input_csv
    results_dir = Path(args.results_dir)
    summary_csv = args.summary_csv

    results_dir.mkdir(parents=True, exist_ok=True)

    token = get_github_token()

    log(f"Loading {input_csv} ...")
    df = pd.read_csv(input_csv)

    # Detect columns
    repo_url_col = pick_first_existing(df, ["repo_url"], required=False)
    html_url_col = pick_first_existing(df, ["html_url"], required=False)
    pr_col = pick_first_existing(df, ["pr_id", "pull_request_id", "id"], required=True)
    commit_col = pick_first_existing(df, ["sha", "commit_sha", "commit_id"], required=True)
    filename_col = pick_first_existing(df, ["filename", "file_path", "path"], required=True)
    patch_col = pick_first_existing(df, ["patch"], required=True)
    status_col = pick_first_existing(df, ["status"], required=False)

    # Ensure we have additions/deletions
    if "additions" not in df.columns or "deletions" not in df.columns:
        log("No 'additions' or 'deletions' columns found; computing from patch...")
        adds, dels = [], []
        for p in df[patch_col]:
            a, d = compute_add_del_from_patch(p)
            adds.append(a)
            dels.append(d)
        df["additions"] = adds
        df["deletions"] = dels

    total_rows = len(df)
    start_row = args.start_row
    if start_row < 0 or start_row >= total_rows:
        raise ValueError(f"--start-row {start_row} out of range (0..{total_rows-1})")

    end_row = total_rows if args.max_rows is None else min(total_rows, start_row + int(args.max_rows))
    run_df = df.iloc[start_row:end_row].copy()
    run_total = len(run_df)

    log(f"Running rows [{start_row}:{end_row}] -> {run_total} rows")
    log(f"Results dir: {results_dir.resolve()}")
    log(f"Summary CSV (append): {summary_csv}")
    log(f"Log file: {Path(args.log_path).resolve()}")

    parent_cache: Dict[Tuple[str, str, str], Optional[str]] = {}
    content_cache: Dict[Tuple[str, str, str, str], Optional[str]] = {}

    summary_rows: List[Dict[str, Any]] = []
    success_count = 0
    new_file_count = 0
    fail_count = 0

    forbidden_triggered = False

    for n, (idx, row) in enumerate(run_df.iterrows(), start=1):
        prefix = f"[{n}/{run_total}] [row={idx}]"

        row_pr_id = row.get(pr_col)
        row_sha = str(row.get(commit_col))
        row_path = str(row.get(filename_col))
        file_status = (
            str(row.get(status_col)).lower()
            if status_col is not None and not pd.isna(row.get(status_col))
            else None
        )

        row_summary = {
            "index": idx,
            "status": "fail",
            "reason": "",
            "owner": "",
            "repo": "",
            "pr_id": row_pr_id,
            "sha": row_sha,
            "path": row_path,
            "file_status": file_status,
            "commit_url": "",
            "before_path": "",
            "after_or_new_path": "",
            "run_start_row": start_row,
            "run_end_row": end_row,
        }

        try:
            patch = row.get(patch_col)
            if not isinstance(patch, str) or patch.strip() == "":
                row_summary["reason"] = "no patch"
                fail_count += 1
                summary_rows.append(row_summary)
                log(f"{prefix} Skipping: no patch")
                continue

            repo_url = row[repo_url_col] if repo_url_col else None
            html_url = row[html_url_col] if html_url_col else None

            owner, repo = extract_owner_repo(repo_url, html_url)
            row_summary["owner"] = owner
            row_summary["repo"] = repo

            sha = row_sha
            path = row_path
            commit_url = build_commit_url(repo_url, html_url, owner, repo, sha, row_pr_id)
            row_summary["commit_url"] = commit_url

            base_name = os.path.basename(path)
            root, ext = os.path.splitext(base_name)
            if not ext:
                ext = ".txt"

            safe_root = root.replace("/", "_").replace("\\", "_")
            safe_owner = owner.replace("/", "_")
            safe_repo = repo.replace("/", "_")
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

            base = f"{safe_owner}__{safe_repo}__pr{row_pr_id}__{timestamp}__{sha}__{safe_root}"
            before_path = results_dir / f"{base}_before{ext}"
            after_path = results_dir / f"{base}_after{ext}"
            new_path = results_dir / f"{base}_new{ext}"

            # AFTER content
            after_content = get_file_content(owner, repo, path, sha, token, content_cache)
            if after_content is None:
                msg = "after content not found (404 or similar)"
                row_summary["reason"] = msg
                fail_count += 1
                summary_rows.append(row_summary)
                log(f"{prefix} {msg} for {owner}/{repo}:{sha} {path}")
                continue

            # status == new
            if file_status == "new":
                with open(new_path, "w", encoding="utf-8") as f:
                    f.write(after_content)

                row_summary["status"] = "new_file"
                row_summary["reason"] = "new file (status=new from dataset)"
                row_summary["after_or_new_path"] = str(new_path)

                new_file_count += 1
                summary_rows.append(row_summary)
                log(f"{prefix} 🆕 New file (status=new). Wrote {new_path.name}")
                continue

            # parent sha
            parent_sha = get_parent_sha(owner, repo, sha, token, parent_cache)
            if parent_sha is None:
                with open(new_path, "w", encoding="utf-8") as f:
                    f.write(after_content)

                row_summary["status"] = "new_file"
                row_summary["reason"] = "new file (no parent commit)"
                row_summary["after_or_new_path"] = str(new_path)

                new_file_count += 1
                summary_rows.append(row_summary)
                log(f"{prefix} 🆕 New file (no parent). Wrote {new_path.name}")
                continue

            before_content = get_file_content(owner, repo, path, parent_sha, token, content_cache)
            if before_content is None:
                with open(new_path, "w", encoding="utf-8") as f:
                    f.write(after_content)

                row_summary["status"] = "new_file"
                row_summary["reason"] = "new file (no file in parent commit)"
                row_summary["after_or_new_path"] = str(new_path)

                new_file_count += 1
                summary_rows.append(row_summary)
                log(f"{prefix} 🆕 New file (no file in parent). Wrote {new_path.name}")
                continue

            # normal case
            with open(before_path, "w", encoding="utf-8") as f:
                f.write(before_content)
            with open(after_path, "w", encoding="utf-8") as f:
                f.write(after_content)

            row_summary["status"] = "success"
            row_summary["before_path"] = str(before_path)
            row_summary["after_or_new_path"] = str(after_path)

            success_count += 1
            summary_rows.append(row_summary)

            log(f"{prefix} ✅ Wrote {before_path.name} and {after_path.name}")

        except ForbiddenError as fe:
            # STOP THE RUN on 403, but save what we have first
            row_summary["reason"] = str(fe)
            fail_count += 1
            summary_rows.append(row_summary)

            forbidden_triggered = True
            log(f"{prefix} 🚫 {fe}")
            log(f"{prefix} Terminating early due to 403. Will save summary before exit.")
            break

        except Exception as e:
            msg = f"error: {e}"
            row_summary["reason"] = msg
            fail_count += 1
            summary_rows.append(row_summary)
            log_exception(f"{prefix} {msg}", e)
            continue

    # Save (APPEND) summary for this run
    summary_df = pd.DataFrame(summary_rows)
    if len(summary_df) > 0:
        append_summary_csv(summary_df, summary_csv)
        log(f"Appended {len(summary_df)} rows to {summary_csv}")
    else:
        log("No summary rows to save (nothing processed).")

    log("=== SUMMARY ===")
    log(f"Rows intended this run : {run_total}")
    log(f"Rows actually processed: {len(summary_rows)}")
    log(f"Success (before+after) : {success_count}")
    log(f"New file only          : {new_file_count}")
    log(f"Fail                   : {fail_count}")
    log(f"Full before/after/new files in: {results_dir.resolve()}")

    if forbidden_triggered:
        raise SystemExit("Stopped due to GitHub 403 (Forbidden). Summary was saved.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        sys.exit(130)
