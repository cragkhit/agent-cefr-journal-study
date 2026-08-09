#!/usr/bin/env python3

"""
Atomic path utilities for the Atomic/Composable Architecture implementation of the file editor agent.
These are the most basic building blocks for path manipulation.
"""

import os
from typing import Optional

def normalize_path(path: str) -> str:
    """
    Normalize file paths to handle various formats (absolute, relative, Windows paths, etc.)

    Args:
        path: The path to normalize

    Returns:
        The normalized path
    """
    if not path:
        return path

    # Handle Windows backslash paths if provided
    path = path.replace("\\", os.sep)

    is_windows_path = False
    if os.name == "nt" and len(path) > 1 and path[1] == ":":
        is_windows_path = True

    # Handle /repo/ paths from Claude (tool use convention)
    if path.startswith("/repo/"):
        path = os.path.join(os.getcwd(), path[6:])
        return path

    if path.startswith("/"):
        # Handle case when Claude provides paths with leading slash
        if path == "/" or path == "/.":
            # Special case for root directory
            path = os.getcwd()
        else:
            # Replace leading slash with current working directory
            path = os.path.join(os.getcwd(), path[1:])
    elif path.startswith("./"):
        # Handle relative paths starting with ./
        path = os.path.join(os.getcwd(), path[2:])
    elif not os.path.isabs(path) and not is_windows_path:
        # For non-absolute paths that aren't Windows paths either
        path = os.path.join(os.getcwd(), path)

    return path

def get_file_extension(path: str) -> str:
    """
    Get the file extension from a path.

    Args:
        path: The path to get the extension from

    Returns:
        The file extension without the dot
    """
    return os.path.splitext(path)[1][1:]

def ensure_directory_exists(path: str) -> None:
    """
    Ensure that the directory for a file path exists.
    Creates the directory if it doesn't exist.

    Args:
        path: The path to check
    """
    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)

def is_valid_path(path: str) -> bool:
    """
    Check if a path is valid.

    Args:
        path: The path to check

    Returns:
        True if the path is valid, False otherwise
    """
    return path is not None and path.strip() != ""

def file_exists(path: str) -> bool:
    """
    Check if a file exists.

    Args:
        path: The path to check

    Returns:
        True if the file exists, False otherwise
    """
    return os.path.exists(path) and os.path.isfile(path)
