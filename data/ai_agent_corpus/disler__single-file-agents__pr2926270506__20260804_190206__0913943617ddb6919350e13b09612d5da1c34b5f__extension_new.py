#!/usr/bin/env python3

"""
Atomic file extension utility for the Atomic/Composable Architecture.
This is the most basic building block for getting file extensions.
"""

import os

def get_file_extension(path: str) -> str:
    """
    Get the file extension from a path.

    Args:
        path: The path to get the extension from

    Returns:
        The file extension without the dot
    """
    return os.path.splitext(path)[1][1:]
