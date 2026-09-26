#!/usr/bin/env python3
"""
Groups data/{corpus}/*.py (flat, one file per before/after/new commit
snapshot) into data/{corpus}_by_repo/{owner}__{repo}/ subfolders, by the
first two `__`-separated fields of each filename.

Not stored in this repo to avoid duplicating the corpus's file content
under two directory layouts -- regenerate it with:
    python3 extraction/group_by_repo.py                  # ai_agent_corpus (default)
    python3 extraction/group_by_repo.py human_corpus      # human_corpus
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    corpus = sys.argv[1] if len(sys.argv) > 1 else "ai_agent_corpus"
    src = os.path.join(HERE, "..", "data", corpus)
    dst = os.path.join(HERE, "..", "data", f"{corpus}_by_repo")

    if not os.path.isdir(src):
        raise SystemExit(f"Error: {src} not found. Extract the corresponding .zip first.")

    os.makedirs(dst, exist_ok=True)

    repo_counts = {}
    linked = 0
    copied = 0

    for fname in os.listdir(src):
        if not fname.endswith(".py"):
            continue
        parts = fname.split("__")
        repo_key = "__".join(parts[:2])
        repo_dir = os.path.join(dst, repo_key)
        os.makedirs(repo_dir, exist_ok=True)

        src_path = os.path.join(src, fname)
        dst_path = os.path.join(repo_dir, fname)

        if not os.path.exists(dst_path):
            try:
                os.link(src_path, dst_path)
                linked += 1
            except OSError:
                shutil.copy2(src_path, dst_path)
                copied += 1

        repo_counts[repo_key] = repo_counts.get(repo_key, 0) + 1

    print(f"Corpus: {corpus}")
    print(f"Total repos: {len(repo_counts)}")
    print(f"Files hardlinked: {linked}, copied (fallback): {copied}")
    print(f"Total files placed: {sum(repo_counts.values())}")


if __name__ == "__main__":
    main()
