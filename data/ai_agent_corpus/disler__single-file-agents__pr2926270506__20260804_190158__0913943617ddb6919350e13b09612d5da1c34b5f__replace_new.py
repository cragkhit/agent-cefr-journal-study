#!/usr/bin/env python3

"""
Atomic file replace operation for the Atomic/Composable Architecture.
This is the most basic building block for replacing content in files.
"""

import sys
import os

# Add the parent directory to the Python path to enable absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from atom.path_utils.normalize import normalize_path
from atom.path_utils.validation import is_valid_path, file_exists
from atom.logging.console import log_info, log_error
from atom.file_operations.result import FileOperationResult

def replace_in_file(path: str, old_str: str, new_str: str) -> FileOperationResult:
    """
    Replace a string in a file.

    Args:
        path: The path to the file to modify
        old_str: The string to replace
        new_str: The string to replace with

    Returns:
        FileOperationResult with result or error message
    """
    try:
        # Validate path
        if not is_valid_path(path):
            error_msg = "Invalid file path provided: path is empty."
            log_error("replace_in_file", error_msg)
            return FileOperationResult(False, error_msg)

        # Normalize the path
        path = normalize_path(path)

        # Check if the file exists
        if not file_exists(path):
            error_msg = f"File {path} does not exist"
            log_error("replace_in_file", error_msg)
            return FileOperationResult(False, error_msg)

        # Read the file
        with open(path, "r") as f:
            content = f.read()

        # Check if the string exists
        if old_str not in content:
            error_msg = f"The specified string was not found in the file {path}"
            log_error("replace_in_file", error_msg)
            return FileOperationResult(False, error_msg)

        # Replace the string
        new_content = content.replace(old_str, new_str, 1)

        # Write the file
        with open(path, "w") as f:
            f.write(new_content)

        log_info("replace_in_file", f"Successfully replaced text in {path}")
        return FileOperationResult(True, f"Successfully replaced text in {path}")
    except Exception as e:
        error_msg = f"Error replacing text: {str(e)}"
        log_error("replace_in_file", error_msg, exc_info=True)
        return FileOperationResult(False, error_msg)
