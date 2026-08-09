#!/usr/bin/env python3
"""
Groups data/ai_agent_corpus/*.py (flat, one file per before/after/new commit
snapshot) into data/ai_agent_corpus_by_repo/{owner}__{repo}/ subfolders, by
the first two `__`-separated fields of each filename.

Not stored in this repo to avoid duplicating ~160MB of identical file
content under two directory layouts -- regenerate it with:
    python3 scripts/group_by_repo.py
"""
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "data", "ai_agent_corpus")
DST = os.path.join(HERE, "..", "data", "ai_agent_corpus_by_repo")


def main():
    if not os.path.isdir(SRC):
        raise SystemExit(f"Error: {SRC} not found. Extract ai_agent_corpus.zip first.")

    os.makedirs(DST, exist_ok=True)

    repo_counts = {}
    linked = 0
    copied = 0

    for fname in os.listdir(SRC):
        if not fname.endswith(".py"):
            continue
        parts = fname.split("__")
        repo_key = "__".join(parts[:2])
        repo_dir = os.path.join(DST, repo_key)
        os.makedirs(repo_dir, exist_ok=True)

        src_path = os.path.join(SRC, fname)
        dst_path = os.path.join(repo_dir, fname)

        if not os.path.exists(dst_path):
            try:
                os.link(src_path, dst_path)
                linked += 1
            except OSError:
                shutil.copy2(src_path, dst_path)
                copied += 1

        repo_counts[repo_key] = repo_counts.get(repo_key, 0) + 1

    print(f"Total repos: {len(repo_counts)}")
    print(f"Files hardlinked: {linked}, copied (fallback): {copied}")
    print(f"Total files placed: {sum(repo_counts.values())}")


if __name__ == "__main__":
    main()
