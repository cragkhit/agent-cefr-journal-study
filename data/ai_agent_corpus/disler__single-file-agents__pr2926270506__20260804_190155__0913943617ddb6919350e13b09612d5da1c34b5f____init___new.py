"""
Atomic file operations for the Atomic/Composable Architecture implementation of the file editor agent.
These are the most basic building blocks for file manipulation.
"""

from .result import FileOperationResult
from .read import read_file
from .write import write_file
from .replace import replace_in_file
from .insert import insert_in_file
from .undo import undo_edit

__all__ = [
    'FileOperationResult',
    'read_file',
    'write_file',
    'replace_in_file',
    'insert_in_file',
    'undo_edit'
]
