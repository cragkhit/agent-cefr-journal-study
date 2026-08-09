#!/usr/bin/env python3

"""
Atomic file write operation for the Atomic/Composable Architecture.
This is the most basic building block for writing files.
"""

import sys
import os

# Add the parent directory to the Python path to enable absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from atom.path_utils.normalize import normalize_path
from atom.path_utils.validation import is_valid_path
from atom.path_utils.directory import ensure_directory_exists
from atom.logging.console import log_info, log_error
from atom.file_operations.result import FileOperationResult

def write_file(path: str, content: str) -> FileOperationResult:
    """
    Write content to a file.

    Args:
        path: The path to the file to write
        content: The content to write to the file

    Returns:
        FileOperationResult with result or error message
    """
    try:
        # Validate path
        if not is_valid_path(path):
            error_msg = "Invalid file path provided: path is empty."
            log_error("write_file", error_msg)
            return FileOperationResult(False, error_msg)

        # Normalize the path
        path = normalize_path(path)

        # Ensure the directory exists
        ensure_directory_exists(path)

        # Write the file
        with open(path, "w") as f:
            f.write(content or "")

        log_info("write_file", f"Successfully wrote to file {path}")
        return FileOperationResult(True, f"Successfully wrote to file {path}")
    except Exception as e:
        error_msg = f"Error writing file: {str(e)}"
        log_error("write_file", error_msg, exc_info=True)
        return FileOperationResult(False, error_msg)
