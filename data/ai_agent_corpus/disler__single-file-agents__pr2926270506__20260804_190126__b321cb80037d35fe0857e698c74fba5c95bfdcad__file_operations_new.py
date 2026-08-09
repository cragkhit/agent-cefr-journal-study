#!/usr/bin/env python3

"""
Atomic file operations for the Atomic/Composable Architecture implementation of the file editor agent.
These are the most basic building blocks for file manipulation.
"""

import os
from typing import Any, Dict, List, Optional, Tuple, Union

from .path_utils import normalize_path, ensure_directory_exists, is_valid_path, file_exists
from .logging import log_info, log_error, display_file_content

class FileOperationResult:
    """
    Model representing the result of a file operation.
    """
    
    def __init__(self, success: bool, message: str, data: Any = None):
        """
        Initialize a file operation result.
        
        Args:
            success: Whether the operation was successful
            message: A message describing the result
            data: Optional data returned by the operation
        """
        self.success = success
        self.message = message
        self.data = data
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the result to a dictionary.
        
        Returns:
            Dictionary representation of the result
        """
        return {
            "success": self.success,
            "message": self.message,
            "data": self.data
        }
    
    def to_response(self) -> Dict[str, Any]:
        """
        Convert the result to a response for Claude.
        
        Returns:
            Dictionary with result or error to send back to Claude
        """
        if self.success:
            return {"result": self.data if self.data is not None else self.message}
        else:
            return {"error": self.message}

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
