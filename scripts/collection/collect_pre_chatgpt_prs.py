#!/usr/bin/env python3
"""
TD2 / TD3 - Pre-ChatGPT human activity in repositories that have AI agent PRs.

For every repository in the TD1 list, count how many pull requests were MERGED
before the ChatGPT release date (2022-11-30). The goal is to find repositories
whose history contains work that is guaranteed to predate AI coding assistants.

Definitions locked with the user:
  * repo set  : the 139 repositories in the RQ1 analysed population (TD1)
  * PR state  : merged only
  * timestamp : merged_at (strictly before the cutoff)
  * scope     : all merged PRs, no Python-file filter

Per repository we issue two requests:
  1. GET /repos/{full_name}          (core API, 5000/hr)
     -> repo metadata. Gives created_at, stars, language, archived, and tells us
        whether the repo still exists or was renamed/deleted. Without this a
        deleted repo would return search total_count=0 and be silently
        misread as "exists but has no old PRs".
  2. GET /search/issues?q=repo:X is:pr is:merged merged:<CUTOFF
     -> total_count = TD2/TD3 number. (search API, 30/min - the binding limit)

Rate limiting is handled both proactively (sleep against X-RateLimit-Remaining /
X-RateLimit-Reset before we get blocked) and reactively (403/429 -> Retry-After
or reset-time backoff, then retry the same request).

The run is resumable: results are appended to the output CSV after every repo,
so an interrupted run can be restarted and will skip repositories already done.

Usage:
    python collect_pre_chatgpt_prs.py
    python collect_pre_chatgpt_prs.py --cutoff 2022-11-30 --limit 10
"""

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

GITHUB_API = "https://api.github.com"
CUTOFF_DEFAULT = "2022-11-30"          # ChatGPT public release

IN_CSV_DEFAULT = "data/td1_repos_with_agent_prs.csv"
OUT_CSV_DEFAULT = "analysis_csv/td2_td3_pre_chatgpt_prs.csv"
LOG_DIR = "log files"

FIELDNAMES = [
    "full_name",
    "n_agent_prs",
    "agents",
    "repo_exists",
    "resolved_full_name",   # set when the repo was renamed
    "repo_created_at",
    "created_before_cutoff",
    "stars",
    "language",
    "archived",
    "pre_cutoff_merged_prs",
    "status",               # OK | RENAMED | NOT_FOUND | ERROR
    "note",
    "fetched_at",
]


# --------------------------------------------------------------------------
# logging
# --------------------------------------------------------------------------
class Logger:
    def __init__(self, path):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"=== collect_pre_chatgpt_prs run started {datetime.now().isoformat()} ===\n")

    def __call__(self, msg, *, also_print=True):
        line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
        if also_print:
            print(line, flush=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(line + "\n")


# --------------------------------------------------------------------------
# HTTP with rate-limit handling
# --------------------------------------------------------------------------
class GitHub:
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
        self.slept_seconds = 0.0

    def _sleep(self, seconds, why):
        seconds = max(0.0, seconds)
        if seconds <= 0:
            return
        self.n_sleeps += 1
        self.slept_seconds += seconds
        self.log(f"    sleeping {seconds:.0f}s ({why})")
        time.sleep(seconds)

    def _preemptive_wait(self, resp):
        """Stay ahead of the limit instead of waiting to be blocked."""
        try:
            remaining = int(resp.headers.get("X-RateLimit-Remaining", "-1"))
            reset = int(resp.headers.get("X-RateLimit-Reset", "0"))
        except ValueError:
            return
        if remaining < 0:
            return
        # Search API is 30/min. Leave a small buffer.
        if remaining <= 1:
            wait = reset - time.time() + 2
            self._sleep(wait, f"quota exhausted, reset in {wait:.0f}s")

    def get(self, path, params=None):
        """Returns (json_or_None, status_code). None body on 404."""
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self.s.get(GITHUB_API + path, params=params, timeout=60)
            except requests.RequestException as e:
                back = min(60 * attempt, 300)
                self.log(f"    network error ({e.__class__.__name__}); retry {attempt}/{self.max_retries}")
                self._sleep(back, "network backoff")
                continue

            self.n_requests += 1

            if resp.status_code == 404:
                return None, 404

            if resp.status_code in (403, 429):
                retry_after = resp.headers.get("Retry-After")
                if retry_after:
                    wait = float(retry_after) + 1
                    why = f"Retry-After {retry_after}s"
                else:
                    try:
                        reset = int(resp.headers.get("X-RateLimit-Reset", "0"))
                    except ValueError:
                        reset = 0
                    wait = max(reset - time.time() + 2, 60)
                    why = "rate limit / secondary limit"
                self.log(f"    HTTP {resp.status_code} (attempt {attempt}/{self.max_retries}) - {why}")
                self._sleep(wait, why)
                continue

            if resp.status_code >= 500:
                self.log(f"    HTTP {resp.status_code} server error; retry {attempt}/{self.max_retries}")
                self._sleep(min(30 * attempt, 300), "server error backoff")
                continue

            if resp.status_code == 422:
                return {"_error": resp.text[:300]}, 422

            if resp.status_code != 200:
                return {"_error": resp.text[:300]}, resp.status_code

            self._preemptive_wait(resp)
            return resp.json(), 200

        raise RuntimeError(f"exhausted {self.max_retries} retries for {path}")


# --------------------------------------------------------------------------
# per-repo work
# --------------------------------------------------------------------------
def process_repo(gh, full_name, cutoff):
    row = {k: "" for k in FIELDNAMES}
    row["full_name"] = full_name
    row["fetched_at"] = datetime.now(timezone.utc).isoformat()

    meta, code = gh.get(f"/repos/{full_name}")
    if code == 404 or meta is None:
        row.update(repo_exists=False, status="NOT_FOUND",
                   note="repo deleted, renamed without redirect, or made private")
        return row
    if code != 200 or "_error" in meta:
        row.update(repo_exists="", status="ERROR",
                   note=f"metadata HTTP {code}: {meta.get('_error','') if meta else ''}")
        return row

    resolved = meta.get("full_name", full_name)
    row["repo_exists"] = True
    row["repo_created_at"] = meta.get("created_at", "")
    row["stars"] = meta.get("stargazers_count", "")
    row["language"] = meta.get("language") or ""
    row["archived"] = meta.get("archived", "")
    if resolved.lower() != full_name.lower():
        row["resolved_full_name"] = resolved
        row["status"] = "RENAMED"
        row["note"] = f"redirected to {resolved}"
    else:
        row["status"] = "OK"

    if row["repo_created_at"]:
        row["created_before_cutoff"] = row["repo_created_at"][:10] < cutoff

    # search against the resolved name so renames do not silently return 0
    q = f"repo:{resolved} is:pr is:merged merged:<{cutoff}"
    data, code = gh.get("/search/issues", params={"q": q, "per_page": 1})
    if code == 200 and data is not None and "total_count" in data:
        row["pre_cutoff_merged_prs"] = data["total_count"]
    else:
        row["status"] = "ERROR"
        row["note"] = (row["note"] + " | " if row["note"] else "") + \
                      f"search HTTP {code}: {(data or {}).get('_error','')}"
    return row


def load_done(path):
    if not os.path.exists(path):
        return {}
    done = {}
    with open(path, "r", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r.get("full_name"):
                done[r["full_name"]] = r
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cutoff", default=CUTOFF_DEFAULT)
    ap.add_argument("--in-csv", default=IN_CSV_DEFAULT)
    ap.add_argument("--out-csv", default=OUT_CSV_DEFAULT)
    ap.add_argument("--limit", type=int, default=0, help="process only N repos (smoke test)")
    ap.add_argument("--restart", action="store_true", help="ignore existing output and start over")
    args = ap.parse_args()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log = Logger(os.path.join(LOG_DIR, f"td2_td3_{ts}.log"))

    load_dotenv()
    token = (os.getenv("GITHUB_TOKEN") or "").strip()
    if not token:
        log("FATAL: GITHUB_TOKEN not set in .env")
        sys.exit(2)

    gh = GitHub(token, log)
    who, code = gh.get("/user")
    if code != 200:
        log(f"FATAL: token rejected (HTTP {code}). Regenerate GITHUB_TOKEN in .env.")
        sys.exit(2)
    log(f"authenticated as {who.get('login','?')}")

    with open(args.in_csv, "r", encoding="utf-8", newline="") as f:
        repos = list(csv.DictReader(f))
    log(f"loaded {len(repos)} repos from {args.in_csv}")

    os.makedirs(os.path.dirname(args.out_csv), exist_ok=True)
    if args.restart and os.path.exists(args.out_csv):
        os.remove(args.out_csv)
        log("--restart: removed previous output")

    done = load_done(args.out_csv)
    if done:
        log(f"resuming: {len(done)} repos already done, will skip them")

    todo = [r for r in repos if r["full_name"] not in done]
    if args.limit:
        todo = todo[:args.limit]
    log(f"to process: {len(todo)} repos | cutoff = merged before {args.cutoff}")
    log(f"estimated wall clock: ~{len(todo) * 2.2 / 60:.1f} min (search API is 30 req/min)")

    new_file = not os.path.exists(args.out_csv)
    out = open(args.out_csv, "a", encoding="utf-8", newline="")
    writer = csv.DictWriter(out, fieldnames=FIELDNAMES)
    if new_file:
        writer.writeheader()
        out.flush()

    t0 = time.time()
    errors = 0
    try:
        for i, r in enumerate(todo, start=1):
            name = r["full_name"]
            log(f"[{i}/{len(todo)}] {name}")
            try:
                row = process_repo(gh, name, args.cutoff)
            except Exception as e:
                errors += 1
                row = {k: "" for k in FIELDNAMES}
                row.update(full_name=name, status="ERROR", note=f"{e.__class__.__name__}: {e}",
                           fetched_at=datetime.now(timezone.utc).isoformat())
                log(f"    ERROR {e.__class__.__name__}: {e}")
            row["n_agent_prs"] = r.get("n_agent_prs", "")
            row["agents"] = r.get("agents", "")
            if row["status"] == "ERROR":
                errors += 0 if row["note"].startswith(("Exception",)) else 1
            writer.writerow(row)
            out.flush()            # checkpoint every repo so a crash loses nothing
            log(f"    status={row['status']} pre_cutoff_merged_prs={row['pre_cutoff_merged_prs']}")
            # keep comfortably under 30 search requests/min
            time.sleep(2.1)
    except KeyboardInterrupt:
        log("interrupted by user - partial results are saved")
    finally:
        out.close()
        dt = time.time() - t0
        log("=" * 60)
        log(f"finished in {dt/60:.1f} min | {gh.n_requests} requests | "
            f"{gh.n_sleeps} rate-limit sleeps totalling {gh.slept_seconds/60:.1f} min | {errors} errors")
        log(f"output: {args.out_csv}")
        log(f"log:    {log.path}")


if __name__ == "__main__":
    main()
