#!/usr/bin/env python3
# PR‑tracker: generates a combo chart from the collected PR data.
# deps: pandas, matplotlib, numpy

from pathlib import Path
import pandas as pd
import matplotlib

matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt
import numpy as np
import datetime as dt
import re


def generate_chart(csv_file=None):
    # Default to data.csv if no file specified
    if csv_file is None:
        csv_file = Path("data.csv")

    # Ensure file exists
    if not csv_file.exists():
        print(f"Error: {csv_file} not found.")
        print("Run collect_data.py first to collect data.")
        return False

    # Create chart
    df = pd.read_csv(csv_file)
    # Fix timestamp format - replace special dash characters with regular hyphens
    df["timestamp"] = df["timestamp"].str.replace("‑", "-")
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Check if data exists
    if len(df) == 0:
        print("Error: No data found in CSV file.")
        return False
        
    # Limit to the last 8 data points to avoid chart getting too busy
    total_points = len(df)
    if total_points > 8:
        df = df.tail(8)
        print(f"Limited chart to the last 8 data points (out of {total_points}).")

    # Calculate percentages with safety checks
    df["copilot_percentage"] = df.apply(
        lambda row: (
            (row["copilot_merged"] / row["copilot_total"] * 100)
            if row["copilot_total"] > 0
            else 0
        ),
        axis=1,
    )
    df["codex_percentage"] = df.apply(
        lambda row: (
            (row["codex_merged"] / row["codex_total"] * 100)
            if row["codex_total"] > 0
            else 0
        ),
        axis=1,
    )

    # Adjust chart size based on data points
    num_points = len(df)
    if num_points <= 3:
        fig_width = max(10, num_points * 4)
        fig_height = 6
    else:
        fig_width = 14
        fig_height = 8

    # Create the combination chart
    fig, ax1 = plt.subplots(figsize=(fig_width, fig_height))
    ax2 = ax1.twinx()

    # Prepare data
    x = np.arange(len(df))
    # Adjust bar width based on number of data points
    width = min(0.35, 0.8 / max(1, num_points * 0.5))

    # Bar charts for totals and merged
    bars_copilot_total = ax1.bar(
        x - width / 2,
        df["copilot_total"],
        width,
        label="Copilot Total",
        alpha=0.7,
        color="#87CEEB",
    )
    bars_copilot_merged = ax1.bar(
        x - width / 2,
        df["copilot_merged"],
        width,
        label="Copilot Merged",
        alpha=1.0,
        color="#4682B4",
    )

    bars_codex_total = ax1.bar(
        x + width / 2,
        df["codex_total"],
        width,
        label="Codex Total",
        alpha=0.7,
        color="#FFA07A",
    )
    bars_codex_merged = ax1.bar(
        x + width / 2,
        df["codex_merged"],
        width,
        label="Codex Merged",
        alpha=1.0,
        color="#CD5C5C",
    )

    # Line charts for percentages (on secondary y-axis)
    line_copilot = ax2.plot(
        x,
        df["copilot_percentage"],
        "o-",
        color="#000080",
        linewidth=3,
        markersize=10,
        label="Copilot Success %",
        markerfacecolor="white",
        markeredgewidth=2,
        markeredgecolor="#000080",
    )

    line_codex = ax2.plot(
        x,
        df["codex_percentage"],
        "s-",
        color="#8B0000",
        linewidth=3,
        markersize=10,
        label="Codex Success %",
        markerfacecolor="white",
        markeredgewidth=2,
        markeredgecolor="#8B0000",
    )

    # Customize the chart
    ax1.set_xlabel("Data Points", fontsize=12, fontweight="bold")
    ax1.set_ylabel(
        "PR Counts (Total & Merged)", fontsize=12, fontweight="bold", color="black"
    )
    ax2.set_ylabel(
        "Merge Success Rate (%)", fontsize=12, fontweight="bold", color="black"
    )

    title = "PR Analytics: Volume vs Success Rate Comparison"
    ax1.set_title(title, fontsize=16, fontweight="bold", pad=20)

    # Set x-axis labels with timestamps
    timestamps = df["timestamp"].dt.strftime("%m-%d %H:%M")
    ax1.set_xticks(x)
    ax1.set_xticklabels(timestamps, rotation=45)

    # Add legends
    legend1 = ax1.legend(loc="upper left", bbox_to_anchor=(0, 0.95))
    legend2 = ax2.legend(loc="upper right", bbox_to_anchor=(1, 0.95))

    # Add grid
    ax1.grid(True, alpha=0.3, linestyle="--")

    # Set percentage axis range
    ax2.set_ylim(0, 100)

    # Add value labels on bars (with safety checks)
    def add_value_labels(ax, bars, format_str="{:.0f}"):
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                # Ensure the label fits within reasonable bounds
                label_text = format_str.format(height)
                if len(label_text) > 10:  # Truncate very long numbers
                    if height >= 1000:
                        label_text = f"{height/1000:.1f}k"
                    elif height >= 1000000:
                        label_text = f"{height/1000000:.1f}M"

                ax.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    height,
                    label_text,
                    ha="center",
                    va="bottom",
                    fontsize=9,
                    fontweight="bold",
                )

    add_value_labels(ax1, bars_copilot_total)
    add_value_labels(ax1, bars_copilot_merged)
    add_value_labels(ax1, bars_codex_total)
    add_value_labels(ax1, bars_codex_merged)

    # Add percentage labels on line points (with validation)
    for i, (cop_pct, cod_pct) in enumerate(
        zip(df["copilot_percentage"], df["codex_percentage"])
    ):
        # Only add labels if percentages are valid numbers
        if pd.notna(cop_pct) and pd.notna(cod_pct):
            ax2.annotate(
                f"{cop_pct:.1f}%",
                (i, cop_pct),
                textcoords="offset points",
                xytext=(0, 15),
                ha="center",
                fontsize=10,
                fontweight="bold",
                color="#000080",
            )
            ax2.annotate(
                f"{cod_pct:.1f}%",
                (i, cod_pct),
                textcoords="offset points",
                xytext=(0, -20),
                ha="center",
                fontsize=10,
                fontweight="bold",
                color="#8B0000",
            )

    plt.tight_layout()

    # Save chart with appropriate DPI for CI environments
    chart_file = Path("chart.png")
    dpi = 150 if num_points <= 5 else 300
    fig.savefig(chart_file, dpi=dpi, bbox_inches="tight", facecolor="white")
    print(f"Chart generated: {chart_file}")
    
    # Also save chart to docs directory for GitHub Pages
    docs_dir = Path("docs")
    if docs_dir.exists():
        docs_chart_file = docs_dir / "chart.png"
        fig.savefig(docs_chart_file, dpi=dpi, bbox_inches="tight", facecolor="white")
        print(f"Chart copied to GitHub Pages: {docs_chart_file}")

    # Update the README with latest statistics
    update_readme(df)
    
    # Update the GitHub Pages with latest statistics
    update_github_pages(df)

    return True


def update_readme(df):
    """Update the README.md with the latest statistics"""
    readme_path = Path("README.md")

    # Skip if README doesn't exist
    if not readme_path.exists():
        print(f"Warning: {readme_path} not found, skipping README update.")
        return False

    # Get the latest data
    latest = df.iloc[-1]

    # Calculate merge rates
    copilot_rate = latest.copilot_merged / latest.copilot_total * 100
    codex_rate = latest.codex_merged / latest.codex_total * 100

    # Format numbers with commas
    copilot_total = f"{latest.copilot_total:,}"
    copilot_merged = f"{latest.copilot_merged:,}"
    codex_total = f"{latest.codex_total:,}"
    codex_merged = f"{latest.codex_merged:,}"

    # Create the new table content
    table_content = f"""## Current Statistics

| Project | Total PRs | Merged PRs | Merge Rate |
| ------- | --------- | ---------- | ---------- |
| Copilot | {copilot_total} | {copilot_merged} | {copilot_rate:.2f}% |
| Codex   | {codex_total} | {codex_merged} | {codex_rate:.2f}% |"""

    # Read the current README content
    readme_content = readme_path.read_text()

    # Split content at the statistics header (if it exists)
    if "## Current Statistics" in readme_content:
        base_content = readme_content.split("## Current Statistics")[0].rstrip()
        new_content = f"{base_content}\n\n{table_content}"
    else:
        new_content = f"{readme_content}\n\n{table_content}"

    # Write the updated content back
    readme_path.write_text(new_content)
    print(f"README.md updated with latest statistics.")
    return True


def update_github_pages(df):
    """Update the GitHub Pages website with the latest statistics"""
    index_path = Path("docs/index.html")
    
    # Skip if index.html doesn't exist
    if not index_path.exists():
        print(f"Warning: {index_path} not found, skipping GitHub Pages update.")
        return False
    
    # Get the latest data
    latest = df.iloc[-1]
    
    # Calculate merge rates
    copilot_rate = latest.copilot_merged / latest.copilot_total * 100
    codex_rate = latest.codex_merged / latest.codex_total * 100
    
    # Format numbers with commas
    copilot_total = f"{latest.copilot_total:,}"
    copilot_merged = f"{latest.copilot_merged:,}"
    codex_total = f"{latest.codex_total:,}"
    codex_merged = f"{latest.codex_merged:,}"
    
    # Current timestamp for last updated
    timestamp = dt.datetime.now().strftime("%B %d, %Y %H:%M UTC")
    
    # Read the current index.html content
    index_content = index_path.read_text()
    
    # Update the table data
    index_content = re.sub(
        r'<td>Copilot</td>\s*<td>[^<]*</td>\s*<td>[^<]*</td>\s*<td>[^<]*</td>',
        f'<td>Copilot</td>\n                        <td>{copilot_total}</td>\n                        <td>{copilot_merged}</td>\n                        <td>{copilot_rate:.2f}%</td>',
        index_content
    )
    
    index_content = re.sub(
        r'<td>Codex</td>\s*<td>[^<]*</td>\s*<td>[^<]*</td>\s*<td>[^<]*</td>',
        f'<td>Codex</td>\n                        <td>{codex_total}</td>\n                        <td>{codex_merged}</td>\n                        <td>{codex_rate:.2f}%</td>',
        index_content
    )
    
    # Update the last updated timestamp
    index_content = re.sub(
        r'<span id="last-updated">[^<]*</span>',
        f'<span id="last-updated">{timestamp}</span>',
        index_content
    )
    
    # Write the updated content back
    index_path.write_text(index_content)
    print(f"GitHub Pages updated with latest statistics.")
    return True


if __name__ == "__main__":
    generate_chart()
