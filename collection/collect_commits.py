# collect_commits.py
#
# Collect all commit records from the AIDev dataset and
# attach PR-level metadata (agent, repo info, etc.),
# then filter only commits that modify .py or .js files.

import pandas as pd

# Pinned to the last AIDev v3 revision (2026-05-10). On 2026-08-21 upstream promoted v4
# to main, which deleted pr_task_type / human_pr_task_type / human_pull_request and
# replaced pull_request with a much larger table. Every number in the paper is v3.
BASE = "hf://datasets/hao-li/AIDev@68ed5f4b80/"

def load_tables():
    """
    Load the core tables needed to collect commits.

    - pull_request.parquet      : PR-level metadata
    - pr_commit_details.parquet : commit/file-level info + patch text
    """
    # Include repo_id + repo_url + html_url for repo context
    pr_df = pd.read_parquet(
        BASE + "pull_request.parquet",
        columns=[
            "id",
            "repo_id",
            "agent",
            "repo_url",
            "html_url",
        ],
    )

    pr_commit_details_df = pd.read_parquet(BASE + "pr_commit_details.parquet")

    return pr_df, pr_commit_details_df


def collect_all_commits():
    """
    Return a DataFrame where each row is a commit-file entry,
    joined with PR-level metadata (including repo info),
    and filtered to only include files ending with .py or .js.
    """
    pr_df, pr_commit_details_df = load_tables()

    # Join commit details with PR metadata
    commits_with_meta = pr_commit_details_df.merge(
        pr_df,
        left_on="pr_id",
        right_on="id",
        how="left",
        suffixes=("", "_pr"),
    )

    # Identify filename column (some schemas use "filename" or "file_path")
    file_col = None
    for c in ["filename", "file_path", "path"]:
        if c in commits_with_meta.columns:
            file_col = c
            break
    if not file_col:
        raise KeyError("Could not find filename column in commit details table.")

    # Filter for Python (.py) or JavaScript (.js) files
    filtered_commits = commits_with_meta[
        commits_with_meta[file_col].str.endswith((".py", ".js"), na=False)
    ].copy()

    print(f"Filtered commits: {len(filtered_commits)} / {len(commits_with_meta)} rows kept")

    return filtered_commits


def main():
    print("Loading and collecting all commits from AIDev (with repo info from pull_request)…")
    commits_df = collect_all_commits()
    print(f"Total filtered rows (only .py or .js): {len(commits_df)}")

    commits_df.to_parquet("aidev_all_commits.parquet", index=False)
    print("Saved filtered commits to aidev_all_commits.parquet")

    # Optional: preview sample
    # commits_df.head(100).to_csv("data_csv/sample_commits.csv", index=False)
    # print("Saved preview to sample_commits.csv")


if __name__ == "__main__":
    main()
