#!/usr/bin/env bash
# Runs extractCodeFromDir.py (from the codeProficiencyExtraction tool -- see
# README.md for which fork/commit this study used) once per repo folder under
# data/ai_agent_corpus_by_repo/, writing each repo's result CSV into a single
# shared output folder (data/output_by_repo/). The tool names each file
# code_constructs_{repo_name}_{timestamp}.csv, so results stay distinguishable
# by name without needing separate subfolders.
#
# The tool itself is NOT vendored in this repo -- clone it separately (see
# README.md for the fork URL/branch used for this study) and point TOOL_DIR
# at it.
#
# Usage:
#   TOOL_DIR=/path/to/codeProficiencyExtraction ./run_extraction_by_repo.sh
#
# If data/ai_agent_corpus_by_repo/ doesn't exist yet, regenerate it first with:
#   python3 extraction/group_by_repo.py
#
# Safe to re-run: repos that already have an output CSV are skipped.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOL_DIR="${TOOL_DIR:-}"
INPUT_ROOT="$SCRIPT_DIR/data/ai_agent_corpus_by_repo"
OUTPUT_DIR="$SCRIPT_DIR/data/output_by_repo"
LOG_FILE="$OUTPUT_DIR/run_log.txt"

if [ -z "$TOOL_DIR" ] || [ ! -f "$TOOL_DIR/extractCodeFromDir.py" ]; then
    echo "Error: TOOL_DIR must point at a checkout of codeProficiencyExtraction" >&2
    echo "  (extractCodeFromDir.py not found in: ${TOOL_DIR:-<unset>})" >&2
    echo "  Usage: TOOL_DIR=/path/to/codeProficiencyExtraction $0" >&2
    exit 1
fi

if [ ! -d "$INPUT_ROOT" ]; then
    echo "Error: $INPUT_ROOT does not exist." >&2
    echo "  Regenerate it first with: python3 extraction/group_by_repo.py" >&2
    exit 1
fi

mkdir -p "$OUTPUT_DIR"
: > "$LOG_FILE"

pushd "$TOOL_DIR" > /dev/null || { echo "Cannot cd into $TOOL_DIR"; exit 1; }

mapfile -t repo_dirs < <(find "$INPUT_ROOT" -mindepth 1 -maxdepth 1 -type d | sort)
total=${#repo_dirs[@]}
count=0
skipped=0
failed=()

start_time=$(date +%s)

for repo_dir in "${repo_dirs[@]}"; do
    repo_name=$(basename "$repo_dir")
    count=$((count + 1))

    if compgen -G "$OUTPUT_DIR/code_constructs_${repo_name}_*.csv" > /dev/null; then
        echo "[$count/$total] Skipping $repo_name (already processed)"
        skipped=$((skipped + 1))
        continue
    fi

    echo "[$count/$total] Processing $repo_name..."
    {
        echo "===== $repo_name ====="
        python3 -u extractCodeFromDir.py "$repo_dir" "$OUTPUT_DIR"
        echo
    } >> "$LOG_FILE" 2>&1
    run_status=$?

    if [ $run_status -ne 0 ]; then
        echo "  !! Failed: $repo_name (see $LOG_FILE)"
        failed+=("$repo_name")
    fi
done

popd > /dev/null

end_time=$(date +%s)
elapsed=$((end_time - start_time))

echo "================================================================"
echo "Done in ${elapsed}s. $count repos total, $skipped skipped (already done)."
echo "All result CSVs are in: $OUTPUT_DIR/"
if [ ${#failed[@]} -gt 0 ]; then
    echo "Failed repos (${#failed[@]}):"
    printf '  - %s\n' "${failed[@]}"
    exit 1
fi
