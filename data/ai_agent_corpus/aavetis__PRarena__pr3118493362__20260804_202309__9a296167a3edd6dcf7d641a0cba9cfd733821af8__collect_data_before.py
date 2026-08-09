#!/usr/bin/env python3
# PR‑tracker: counts Copilot / Codex PRs and saves data to CSV.
# Tracks merged PRs (not just approved ones)
# deps: requests

import csv
import datetime as dt
from pathlib import Path
import requests

# Basic headers for GitHub public API
HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "PR-Watcher"
}

# Search queries - tracking merged PRs
Q = {
    "is:pr+head:copilot/":              "copilot_total",
    "is:pr+head:copilot/+is:merged":    "copilot_merged",
    "is:pr+head:codex/":                "codex_total",
    "is:pr+head:codex/+is:merged":      "codex_merged",
    "author:devin-ai-integration[bot]": "devin_total",
    "author:devin-ai-integration[bot]+is:merged": "devin_merged",
}

def collect_data():
    # Get data from GitHub API
    cnt = {}
    for query, key in Q.items():
        r = requests.get(f"https://api.github.com/search/issues?q={query}",
                        headers=HEADERS, timeout=30)
        r.raise_for_status()
        cnt[key] = r.json()["total_count"]

    # Save data to CSV
    timestamp = dt.datetime.now(dt.UTC).strftime("%Y‑%m‑%d %H:%M:%S")
    row = [timestamp, cnt["copilot_total"], cnt["copilot_merged"],
           cnt["codex_total"], cnt["codex_merged"], cnt["devin_total"], cnt["devin_merged"]]

    csv_file = Path("data.csv")
    is_new_file = not csv_file.exists()
    with csv_file.open("a", newline="") as f:
        writer = csv.writer(f)
        if is_new_file:
            writer.writerow(["timestamp", "copilot_total", "copilot_merged",
                            "codex_total", "codex_merged", "devin_total", "devin_merged"])
        writer.writerow(row)

    return csv_file

if __name__ == "__main__":
    collect_data()
    print("Data collection complete. To generate chart, run generate_chart.py")
