#!/usr/bin/env python3

"""
Atomic file insert operation for the Atomic/Composable Architecture.
This is the most basic building block for inserting content in files.
"""

import sys
import os

# Add the parent directory to the Python path to enable absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from atom.path_utils.normalize import normalize_path
from atom.path_utils.validation import is_valid_path, file_exists
from atom.logging.console import log_info, log_error
from atom.file_operations.result import FileOperationResult

def insert_in_file(path: str, insert_line: int, new_str: str) -> FileOperationResult:
    """
    Insert text at a specific line in a file.

    Args:
        path: The path to the file to modify
        insert_line: The line number after which to insert the text (1-indexed)
        new_str: The text to insert

    Returns:
        FileOperationResult with result or error message
    """
    try:
        # Validate path
        if not is_valid_path(path):
            error_msg = "Invalid file path provided: path is empty."
            log_error("insert_in_file", error_msg)
            return FileOperationResult(False, error_msg)

        # Normalize the path
        path = normalize_path(path)

        # Check if the file exists
        if not file_exists(path):
            error_msg = f"File {path} does not exist"
            log_error("insert_in_file", error_msg)
            return FileOperationResult(False, error_msg)

        # Validate insert_line
        if insert_line is None:
            error_msg = "No line number specified: insert_line is missing."
            log_error("insert_in_file", error_msg)
            return FileOperationResult(False, error_msg)

        # Read the file
        with open(path, "r") as f:
            lines = f.readlines()

        # Line is 0-indexed for this function, but Claude provides 1-indexed
        insert_line = min(max(0, insert_line - 1), len(lines))

        # Check that the index is within acceptable bounds
        if insert_line < 0 or insert_line > len(lines):
            error_msg = (
                f"Insert line number {insert_line} out of range (0-{len(lines)})."
            )
            log_error("insert_in_file", error_msg)
            return FileOperationResult(False, error_msg)

        # Ensure new_str ends with newline
        if new_str and not new_str.endswith("\n"):
            new_str += "\n"

        # Insert the text
        lines.insert(insert_line, new_str)

        # Write the file
        with open(path, "w") as f:
            f.writelines(lines)

        log_info("insert_in_file", f"Successfully inserted text at line {insert_line + 1} in {path}")
        return FileOperationResult(
            True, f"Successfully inserted text at line {insert_line + 1} in {path}"
        )
    except Exception as e:
        error_msg = f"Error inserting text: {str(e)}"
        log_error("insert_in_file", error_msg, exc_info=True)
        return FileOperationResult(False, error_msg)
