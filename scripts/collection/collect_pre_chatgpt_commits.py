#!/usr/bin/env python3
"""
Build a pre-ChatGPT human commit corpus in the SAME shape as aidev_all_commits.parquet,
so that make_file_versions.py can consume it unchanged.

Why this exists
---------------
AIDev only spans Dec 2024 - Jul 2025, so it contains no pre-ChatGPT pull requests.
This script rebuilds the equivalent commit/file table straight from the GitHub API for
PRs merged before the ChatGPT release (2022-11-30), across the repositories that later
received AI agent PRs.

Sampling (decided with the user)
--------------------------------
Take the MOST RECENT merged PRs before the cutoff, up to --per-repo per repository,
keeping only PRs that touch .py files. Most-recent-first matters: the oldest repos here
date to 2010-2015 and their early PRs are Python 2, which pycefr (a Python 3 tool) either
fails to parse or scores on constructs that do not mean the same thing.

Pipeline position
-----------------
  1. THIS SCRIPT           -> data_csv/pre_chatgpt_data.csv
  2. make_file_versions.py -> pre_chatgpt_results/ + pre_chatgpt_fetch_summary.csv
       python make_file_versions.py \
           --input-csv data_csv/pre_chatgpt_data.csv \
           --results-dir pre_chatgpt_results \
           --summary-csv data_csv/pre_chatgpt_fetch_summary.csv \
           --log-path "log files/pre_chatgpt_make_versions.log"
  3. run_pycefr_parallel.py (professor's step)

Outputs
-------
  data_csv/pre_chatgpt_data.csv          one row per (commit, .py file) - the corpus
  analysis_csv/pre_chatgpt_pr_index.csv  one row per PR examined, incl. whether it had
                                         .py files (answers "how many PRs have py files")
  log files/pre_chatgpt_collect_*.log

Resumable at repository granularity: repos already present in the PR index are skipped.

Usage:
    python collect_pre_chatgpt_commits.py --limit-repos 2 --per-repo 2   # smoke test
    python collect_pre_chatgpt_commits.py                               # full run
"""

import argparse
import csv
import os
import sys
import time
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

GITHUB_API = "https://api.github.com"
CUTOFF_DEFAULT = "2022-11-30"

REPOS_CSV = "data/td2_td3_pre_chatgpt_prs.csv"
OUT_CSV = "data_csv/pre_chatgpt_data.csv"
INDEX_CSV = "analysis_csv/pre_chatgpt_pr_index.csv"
LOG_DIR = "log files"

# Column order copied from data_csv/new_data.csv so make_file_versions.py sees an
# identical schema. Do not reorder or rename.
DATA_FIELDS = [
    "sha", "pr_id", "author", "committer", "message",
    "commit_stats_total", "commit_stats_additions", "commit_stats_deletions",
    "filename", "status", "additions", "deletions", "changes", "patch",
    "id", "repo_id", "agent", "repo_url", "html_url",
]

INDEX_FIELDS = [
    "full_name", "pr_id", "number", "merged_at", "n_files", "n_py_files",
    "has_py", "kept", "n_commits", "n_rows_emitted", "note",
]


class Logger:
    def __init__(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.path = path
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"=== collect_pre_chatgpt_commits started {datetime.now().isoformat()} ===\n")

    def __call__(self, msg, *, also_print=True):
        line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
        if also_print:
            print(line, flush=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(line + "\n")


class GitHub:
    """Shared retry / rate-limit behaviour, matching make_file_versions.py's contract
    (403 -> back off -> retry the same request) but driven by the reset headers."""

    def __init__(self, token, log, max_retries=5):
        self.log = log
        self.max_retries = max_retries
        self.s = requests.Session()
        self.s.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        self.n_requests = 0
        self.n_sleeps = 0
        self.slept = 0.0

    def _sleep(self, secs, why):
        secs = max(0.0, secs)
        if secs <= 0:
            return
        self.n_sleeps += 1
        self.slept += secs
        self.log(f"      sleeping {secs:.0f}s ({why})")
        time.sleep(secs)

    def get(self, path, params=None, *, full_url=None):
        url = full_url or (GITHUB_API + path)
        for attempt in range(1, self.max_retries + 1):
            try:
                r = self.s.get(url, params=params, timeout=60)
            except requests.RequestException as e:
                self.log(f"      network {e.__class__.__name__}; retry {attempt}/{self.max_retries}")
                self._sleep(min(30 * attempt, 300), "network backoff")
                continue

            self.n_requests += 1

            if r.status_code == 404:
                return None, 404, {}
            if r.status_code in (403, 429):
                ra = r.headers.get("Retry-After")
                if ra:
                    wait, why = float(ra) + 1, f"Retry-After {ra}s"
                else:
                    try:
                        reset = int(r.headers.get("X-RateLimit-Reset", "0"))
                    except ValueError:
                        reset = 0
                    wait, why = max(reset - time.time() + 2, 60), "rate limit"
                self.log(f"      HTTP {r.status_code} ({attempt}/{self.max_retries}) - {why}")
                self._sleep(wait, why)
                continue
            if r.status_code >= 500:
                self.log(f"      HTTP {r.status_code} server error; retry {attempt}/{self.max_retries}")
                self._sleep(min(30 * attempt, 300), "server backoff")
                continue
            if r.status_code != 200:
                return {"_error": r.text[:200]}, r.status_code, {}

            # stay ahead of the search quota (30/min) rather than getting blocked
            try:
                remaining = int(r.headers.get("X-RateLimit-Remaining", "-1"))
                reset = int(r.headers.get("X-RateLimit-Reset", "0"))
                if 0 <= remaining <= 1:
                    self._sleep(reset - time.time() + 2, "quota exhausted")
            except ValueError:
                pass

            return r.json(), 200, r.links or {}
        raise RuntimeError(f"retries exhausted for {url}")

    def paged(self, path, params=None, cap_pages=40):
        """Yield items across Link-paginated endpoints."""
        params = dict(params or {})
        params.setdefault("per_page", 100)
        url, pages = GITHUB_API + path, 0
        while url and pages < cap_pages:
            body, code, links = self.get(None, params=params if pages == 0 else None, full_url=url)
            if code != 200 or not isinstance(body, list):
                return
            for item in body:
                yield item
            nxt = links.get("next", {}).get("url")
            url, pages = nxt, pages + 1


def is_py(name):
    return isinstance(name, str) and name.endswith(".py")


def collect_repo(gh, log, full_name, cutoff, per_repo, max_candidates):
    """Returns (index_rows, data_rows) for one repository."""
    owner, repo = full_name.split("/", 1)
    idx_rows, data_rows = [], []

    # --- candidates: merged before cutoff, most recently created first -------------
    q = f"repo:{full_name} is:pr is:merged merged:<{cutoff}"
    body, code, _ = gh.get("/search/issues",
                           params={"q": q, "sort": "created", "order": "desc", "per_page": 100})
    if code != 200 or not body or "items" not in body:
        log(f"    search failed (HTTP {code}) - skipping repo")
        return idx_rows, data_rows

    candidates = body["items"][:max_candidates]
    log(f"    {body.get('total_count', 0)} merged pre-cutoff PRs; examining up to {len(candidates)}")

    kept = 0
    for pr in candidates:
        if kept >= per_repo:
            break
        number = pr.get("number")
        pr_id = pr.get("id")

        files = list(gh.paged(f"/repos/{owner}/{repo}/pulls/{number}/files", cap_pages=30))
        py_files = [f for f in files if is_py(f.get("filename"))]
        row = {
            "full_name": full_name, "pr_id": pr_id, "number": number,
            "merged_at": pr.get("closed_at", ""), "n_files": len(files),
            "n_py_files": len(py_files), "has_py": bool(py_files),
            "kept": False, "n_commits": "", "n_rows_emitted": 0, "note": "",
        }
        if not py_files:
            idx_rows.append(row)
            continue

        # --- keeper: pull commit-level file changes (this is what the pipeline needs)
        commits = list(gh.paged(f"/repos/{owner}/{repo}/pulls/{number}/commits", cap_pages=5))
        row["n_commits"] = len(commits)
        emitted = 0
        for c in commits:
            sha = c.get("sha")
            if not sha:
                continue
            detail, code, _ = gh.get(f"/repos/{owner}/{repo}/commits/{sha}")
            if code != 200 or not isinstance(detail, dict):
                row["note"] = (row["note"] + "; " if row["note"] else "") + f"commit {sha[:7]} HTTP {code}"
                continue
            stats = detail.get("stats") or {}
            cm = detail.get("commit") or {}
            for f in (detail.get("files") or []):
                if not is_py(f.get("filename")):
                    continue
                patch = f.get("patch")
                if not patch:
                    continue          # binary/too-large: make_file_versions requires a patch
                data_rows.append({
                    "sha": sha,
                    "pr_id": pr_id,
                    "author": ((detail.get("author") or {}).get("login")
                               or (cm.get("author") or {}).get("name") or ""),
                    "committer": ((detail.get("committer") or {}).get("login")
                                  or (cm.get("committer") or {}).get("name") or ""),
                    "message": (cm.get("message") or "").replace("\r", " "),
                    "commit_stats_total": stats.get("total", ""),
                    "commit_stats_additions": stats.get("additions", ""),
                    "commit_stats_deletions": stats.get("deletions", ""),
                    "filename": f.get("filename"),
                    "status": f.get("status"),
                    "additions": f.get("additions", ""),
                    "deletions": f.get("deletions", ""),
                    "changes": f.get("changes", ""),
                    "patch": patch,
                    "id": pr_id,
                    "repo_id": "",   # unused downstream; kept for schema parity
                    "agent": "Human",
                    "repo_url": f"{GITHUB_API}/repos/{full_name}",
                    "html_url": f"https://github.com/{full_name}/pull/{number}",
                })
                emitted += 1
        row["n_rows_emitted"] = emitted
        if emitted:
            row["kept"] = True
            kept += 1
        idx_rows.append(row)
        log(f"      PR #{number}: {len(py_files)} py file(s), {len(commits)} commit(s) -> {emitted} rows"
            f"{'  [kept %d/%d]' % (kept, per_repo) if emitted else '  (no usable patch)'}")

    return idx_rows, data_rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cutoff", default=CUTOFF_DEFAULT)
    ap.add_argument("--per-repo", type=int, default=15, help="PRs with .py files to keep per repo")
    ap.add_argument("--max-candidates", type=int, default=45, help="PRs to examine per repo")
    ap.add_argument("--limit-repos", type=int, default=0, help="only N repos (smoke test)")
    ap.add_argument("--restart", action="store_true")
    args = ap.parse_args()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log = Logger(os.path.join(LOG_DIR, f"pre_chatgpt_collect_{ts}.log"))

    load_dotenv()
    token = (os.getenv("GITHUB_TOKEN") or "").strip()
    if not token:
        log("FATAL: GITHUB_TOKEN missing from .env")
        sys.exit(2)

    gh = GitHub(token, log)
    who, code, _ = gh.get("/user")
    if code != 200:
        log(f"FATAL: token rejected (HTTP {code})")
        sys.exit(2)
    log(f"authenticated as {who.get('login','?')}")

    # repos that actually have pre-cutoff history
    with open(REPOS_CSV, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    repos = []
    for r in rows:
        n = r.get("pre_cutoff_merged_prs", "")
        try:
            if int(float(n)) > 0:
                repos.append(r.get("resolved_full_name") or r["full_name"])
        except (ValueError, TypeError):
            pass
    log(f"{len(repos)} repos with pre-cutoff history (from {REPOS_CSV})")

    for p in (OUT_CSV, INDEX_CSV):
        os.makedirs(os.path.dirname(p), exist_ok=True)
        if args.restart and os.path.exists(p):
            os.remove(p)
    if args.restart:
        log("--restart: cleared previous output")

    done = set()
    if os.path.exists(INDEX_CSV):
        with open(INDEX_CSV, encoding="utf-8", newline="") as f:
            done = {r["full_name"] for r in csv.DictReader(f) if r.get("full_name")}
        if done:
            log(f"resuming: {len(done)} repos already done")

    todo = [r for r in repos if r not in done]
    if args.limit_repos:
        todo = todo[:args.limit_repos]
    log(f"to process: {len(todo)} repos | cutoff {args.cutoff} | keep {args.per_repo}/repo "
        f"| examine <= {args.max_candidates}/repo")

    new_data = not os.path.exists(OUT_CSV)
    new_idx = not os.path.exists(INDEX_CSV)
    fd = open(OUT_CSV, "a", encoding="utf-8", newline="")
    fi = open(INDEX_CSV, "a", encoding="utf-8", newline="")
    wd = csv.DictWriter(fd, fieldnames=DATA_FIELDS)
    wi = csv.DictWriter(fi, fieldnames=INDEX_FIELDS)
    if new_data:
        wd.writeheader(); fd.flush()
    if new_idx:
        wi.writeheader(); fi.flush()

    t0, tot_rows, tot_kept = time.time(), 0, 0
    try:
        for i, full_name in enumerate(todo, start=1):
            log(f"[{i}/{len(todo)}] {full_name}")
            try:
                idx_rows, data_rows = collect_repo(
                    gh, log, full_name, args.cutoff, args.per_repo, args.max_candidates)
            except Exception as e:
                log(f"    ERROR {e.__class__.__name__}: {e}")
                continue
            for r in idx_rows:
                wi.writerow(r)
            for r in data_rows:
                wd.writerow(r)
            fd.flush(); fi.flush()          # checkpoint per repo
            k = sum(1 for r in idx_rows if r["kept"])
            tot_rows += len(data_rows); tot_kept += k
            log(f"    -> kept {k} PRs, {len(data_rows)} file rows "
                f"(running: {tot_kept} PRs, {tot_rows} rows)")
    except KeyboardInterrupt:
        log("interrupted - partial results saved")
    finally:
        fd.close(); fi.close()
        dt = time.time() - t0
        log("=" * 60)
        log(f"done in {dt/60:.1f} min | {gh.n_requests} requests | "
            f"{gh.n_sleeps} sleeps ({gh.slept/60:.1f} min) | {tot_kept} PRs kept | {tot_rows} rows")
        log(f"corpus: {OUT_CSV}")
        log(f"index : {INDEX_CSV}")
        log(f"log   : {log.path}")


if __name__ == "__main__":
    main()
