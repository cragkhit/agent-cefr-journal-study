#!/usr/bin/env python3
"""Label the pre-ChatGPT PRs by task type with GPT-4.1-mini via OpenRouter.

Follows Li et al., "The Rise of AI Teammates in SE 3.0" (arXiv:2507.15003), Sec. 4.1:
each PR (title and body) is classified into one of 11 task categories defined by the
Conventional Commits specification, using GPT-4.1-mini.

One API call per PR, so the pr_id never round-trips through the model and cannot be
rounded or reformatted. Results are cached to JSONL, so the run is resumable: re-running
only labels PRs that are still missing.

Usage:
    export OPENROUTER_API_KEY=sk-or-...
    python label_pre_chatgpt_prs.py --limit 10      # smoke test
    python label_pre_chatgpt_prs.py                 # full run
    python label_pre_chatgpt_prs.py --merge-only    # rebuild the CSV from the cache
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import pathlib
import random
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = pathlib.Path(__file__).resolve().parent
SRC = HERE / "rq3_pre_chatgpt_prs_titles.csv"
CACHE = HERE / "rq3_pre_chatgpt_labels.jsonl"
OUT = HERE / "rq3_pre_chatgpt_prs_with_task_type.csv"

API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openai/gpt-4.1-mini"

# The 11 categories of Table 4 / FLOW_ORDER in the authors' own productivity.py.
# `revert` is deliberately excluded -- see rq3_labelling_prompt.md.
TYPES = [
    "build", "chore", "ci", "docs", "feat", "fix",
    "other", "perf", "refactor", "style", "test",
]

SYSTEM_PROMPT = f"""\
You are labelling GitHub pull requests by task type, following the Conventional Commits \
specification.

Assign exactly one label to the pull request. `type` must be exactly one of: \
{", ".join(TYPES)}.

Judge from the PR title and body together. Some PRs have an empty body -- judge from the \
title alone in that case. If the PR is ambiguous, pick the most likely label and lower the \
confidence rather than falling back to `other`. Reserve `other` for PRs that genuinely fit \
no category; label a revert as `other`.

`confidence` is an integer from 3 to 10: 10 means the PR states its task type \
unambiguously, 3 means it is too vague to be sure.

`reason` is one sentence explaining the choice.\
"""

SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "pr_task_type",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": TYPES},
                "confidence": {"type": "integer", "minimum": 3, "maximum": 10},
                "reason": {"type": "string"},
            },
            "required": ["type", "confidence", "reason"],
            "additionalProperties": False,
        },
    },
}

_print_lock = threading.Lock()
_cache_lock = threading.Lock()


def log(msg: str) -> None:
    with _print_lock:
        print(msg, file=sys.stderr, flush=True)


def build_user_prompt(row: dict, max_body: int) -> str:
    body = (row.get("body") or "").replace("\r\n", "\n").strip()
    if max_body and len(body) > max_body:
        body = body[:max_body] + "\n[... truncated ...]"
    return f"title: {row['title']}\n\nbody:\n{body if body else '(empty)'}"


def call_api(api_key: str, model: str, user_prompt: str, use_schema: bool,
             retries: int, timeout: int) -> dict:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0,
        "seed": 42,
        "max_tokens": 300,
    }
    if use_schema:
        payload["response_format"] = SCHEMA

    data = json.dumps(payload).encode()
    last_err: Exception | None = None

    for attempt in range(retries):
        req = urllib.request.Request(
            API_URL,
            data=data,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                # Optional OpenRouter attribution headers.
                "HTTP-Referer": "https://github.com/",
                "X-Title": "AIDev CEFR RQ3 PR task-type labelling",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = json.loads(resp.read().decode())
            content = body["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            if parsed.get("type") not in TYPES:
                raise ValueError(f"type not in vocabulary: {parsed.get('type')!r}")
            conf = int(parsed["confidence"])
            if not 3 <= conf <= 10:
                raise ValueError(f"confidence out of range: {conf}")
            return {
                "type": parsed["type"],
                "confidence": conf,
                "reason": str(parsed["reason"]).strip(),
            }
        except urllib.error.HTTPError as e:
            detail = e.read().decode()[:300]
            last_err = RuntimeError(f"HTTP {e.code}: {detail}")
            if e.code not in (408, 409, 429, 500, 502, 503, 504):
                break
        except Exception as e:  # noqa: BLE001 - retry transport and parse failures alike
            last_err = e

        time.sleep(min(2 ** attempt + random.random(), 30))

    raise RuntimeError(f"failed after {retries} attempts: {last_err}")


def load_cache() -> dict[str, dict]:
    out: dict[str, dict] = {}
    if CACHE.exists():
        for line in CACHE.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("type") in TYPES:
                out[str(rec["pr_id"])] = rec
    return out


def append_cache(rec: dict) -> None:
    with _cache_lock, CACHE.open("a") as fh:
        fh.write(json.dumps(rec) + "\n")


def merge(rows: list[dict], cache: dict[str, dict], fieldnames: list[str]) -> int:
    filled = 0
    for r in rows:
        rec = cache.get(str(r["pr_id"]))
        if rec:
            r["type"] = rec["type"]
            r["confidence"] = rec["confidence"]
            r["reason"] = rec["reason"]
            filled += 1
    with OUT.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    return filled


def validate(rows: list[dict]) -> list[str]:
    problems = []
    ids = [str(r["pr_id"]) for r in rows]
    if len(ids) != len(set(ids)):
        problems.append("duplicate pr_id values in the source file")
    missing = [r["pr_id"] for r in rows if not str(r.get("type") or "").strip()]
    if missing:
        problems.append(f"{len(missing)} PRs still unlabelled (e.g. {missing[:5]})")
    bad = sorted({r["type"] for r in rows if r.get("type") and r["type"] not in TYPES})
    if bad:
        problems.append(f"labels outside the 11-value vocabulary: {bad}")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default=MODEL, help=f"OpenRouter model id (default {MODEL})")
    ap.add_argument("--limit", type=int, default=0, help="label at most N PRs (smoke test)")
    ap.add_argument("--workers", type=int, default=8, help="parallel requests (default 8)")
    ap.add_argument("--retries", type=int, default=5)
    ap.add_argument("--timeout", type=int, default=90)
    ap.add_argument("--max-body", type=int, default=0,
                    help="truncate bodies to N chars (0 = no truncation, the default)")
    ap.add_argument("--no-schema", action="store_true",
                    help="do not send response_format json_schema")
    ap.add_argument("--merge-only", action="store_true",
                    help="skip the API entirely; rebuild the output CSV from the cache")
    args = ap.parse_args()

    if not SRC.exists():
        log(f"missing input: {SRC}")
        return 1

    with SRC.open() as fh:
        reader = csv.DictReader(fh)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    for col in ("pr_id", "title", "body", "type", "confidence", "reason"):
        if col not in fieldnames:
            log(f"input is missing the {col!r} column")
            return 1

    cache = load_cache()
    log(f"{len(rows)} PRs in {SRC.name}; {len(cache)} already labelled in {CACHE.name}")

    if not args.merge_only:
        todo = [r for r in rows if str(r["pr_id"]) not in cache]
        if args.limit:
            todo = todo[:args.limit]
        if todo:
            api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
            if not api_key:
                log("OPENROUTER_API_KEY is not set")
                return 1

            log(f"labelling {len(todo)} PRs with {args.model} "
                f"({args.workers} workers)...")
            done = failed = 0
            with ThreadPoolExecutor(max_workers=args.workers) as pool:
                futures = {
                    pool.submit(
                        call_api, api_key, args.model,
                        build_user_prompt(r, args.max_body),
                        not args.no_schema, args.retries, args.timeout,
                    ): r
                    for r in todo
                }
                for fut in as_completed(futures):
                    r = futures[fut]
                    try:
                        rec = fut.result()
                    except Exception as e:  # noqa: BLE001
                        failed += 1
                        log(f"  FAILED {r['pr_id']}: {e}")
                        continue
                    rec["pr_id"] = str(r["pr_id"])
                    rec["model"] = args.model
                    append_cache(rec)
                    cache[rec["pr_id"]] = rec
                    done += 1
                    if done % 25 == 0:
                        log(f"  {done}/{len(todo)} done")
            log(f"labelled {done}, failed {failed}")
            if failed:
                log("re-run the same command to retry only the failures")
        else:
            log("nothing to label; every PR is already in the cache")

    filled = merge(rows, cache, fieldnames)
    log(f"wrote {OUT.name}: {filled}/{len(rows)} rows carry a label")

    problems = validate(rows)
    if problems:
        log("VALIDATION:")
        for p in problems:
            log(f"  - {p}")
    else:
        log("VALIDATION: ok -- all rows labelled, all labels in the 11-value vocabulary")

    counts: dict[str, int] = {}
    for r in rows:
        t = r.get("type") or ""
        if t:
            counts[t] = counts.get(t, 0) + 1
    total = sum(counts.values()) or 1
    log("distribution:")
    for t in TYPES:
        if counts.get(t):
            log(f"  {t:9s} {counts[t]:4d}  {100 * counts[t] / total:5.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
