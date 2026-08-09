#!/usr/bin/env python3

"""
Atomic path validation utilities for the Atomic/Composable Architecture.
These are the most basic building blocks for validating paths.
"""

import os

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
