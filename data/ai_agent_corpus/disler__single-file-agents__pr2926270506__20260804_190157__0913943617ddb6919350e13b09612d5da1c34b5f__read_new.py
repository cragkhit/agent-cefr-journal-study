#!/usr/bin/env python3

"""
Atomic file read operation for the Atomic/Composable Architecture.
This is the most basic building block for reading files.
"""

import sys
import os

# Add the parent directory to the Python path to enable absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from atom.path_utils.normalize import normalize_path
from atom.path_utils.validation import is_valid_path, file_exists
from atom.logging.console import log_error
from atom.logging.display import display_file_content
from atom.file_operations.result import FileOperationResult

def read_file(path: str, start_line: int = None, end_line: int = None) -> FileOperationResult:
    """
    Read the contents of a file.

    Args:
        path: The path to the file to read
        start_line: Optional start line (1-indexed)
        end_line: Optional end line (1-indexed, -1 for end of file)

    Returns:
        FileOperationResult with content or error message
    """
    try:
        # Validate path
        if not is_valid_path(path):
            error_msg = "Invalid file path provided: path is empty."
            log_error("read_file", error_msg)
            return FileOperationResult(False, error_msg)

        # Normalize the path
        path = normalize_path(path)

        # Check if the file exists
        if not file_exists(path):
            error_msg = f"File {path} does not exist"
            log_error("read_file", error_msg)
            return FileOperationResult(False, error_msg)

        # Read the file
        with open(path, "r") as f:
            lines = f.readlines()

        # Apply line range if specified
        if start_line is not None or end_line is not None:
            # Convert to 0-indexed for Python
            start = max(0, (start_line or 1) - 1)
            if end_line == -1 or end_line is None:
                end = len(lines)
            else:
                end = min(len(lines), end_line)
            lines = lines[start:end]

        content = "".join(lines)
        
        # Display the file content (only for console, not returned to Claude)
        display_file_content(path, content)

        return FileOperationResult(True, f"Successfully read file {path}", content)
    except Exception as e:
        error_msg = f"Error reading file: {str(e)}"
        log_error("read_file", error_msg, exc_info=True)
        return FileOperationResult(False, error_msg)
