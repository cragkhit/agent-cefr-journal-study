#!/usr/bin/env python3

"""
Atomic directory utility for the Atomic/Composable Architecture.
This is the most basic building block for directory operations.
"""

import os

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
