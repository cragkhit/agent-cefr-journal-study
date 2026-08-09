#!/usr/bin/env python3

"""
InsertText step for the Pipeline Architecture implementation of the file editor agent.
This step is responsible for inserting text at a specific location in a file.
"""

import os
from typing import Dict, Any, Optional

import sys
import os

# Add the parent directory to the Python path to enable absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.utilities import console, FileOperationResult, normalize_path
from steps.file_operations.base_file_operation import BaseFileOperation

class InsertText(BaseFileOperation):
    """
    InsertText step for the file editor pipeline.
    Responsible for inserting text at a specific location in a file.
    """
    
    def _execute_operation(self, request: Any) -> FileOperationResult:
        """
        Insert text at a specific location in a file.

        Args:
            request: The request containing the path, insert_line, and new_str

        Returns:
            FileOperationResult with result or error message
        """
        try:
            path = request.path
            insert_line = request.kwargs.get("insert_line")
            new_str = request.kwargs.get("new_str")
            
            console.log(f"[InsertText] Inserting text at line {insert_line} in file: {path}")
            
            if not path or not path.strip():
                error_msg = "Invalid file path provided: path is empty."
                console.log(f"[InsertText] Error: {error_msg}")
                return FileOperationResult(False, error_msg)

            # Normalize the path
            path = normalize_path(path)

            if not os.path.exists(path):
                error_msg = f"File {path} does not exist"
                console.log(f"[InsertText] Error: {error_msg}")
                return FileOperationResult(False, error_msg)

            if insert_line is None:
                error_msg = "No line number specified: insert_line is missing."
                console.log(f"[InsertText] Error: {error_msg}")
                return FileOperationResult(False, error_msg)

            with open(path, "r") as f:
                lines = f.readlines()

            # Line is 0-indexed for this function, but Claude provides 1-indexed
            insert_line = min(max(0, insert_line - 1), len(lines))

            # Check that the index is within acceptable bounds
            if insert_line < 0 or insert_line > len(lines):
                error_msg = (
                    f"Insert line number {insert_line} out of range (0-{len(lines)})."
                )
                console.log(f"[InsertText] Error: {error_msg}")
                return FileOperationResult(False, error_msg)

            # Ensure new_str ends with newline
            if new_str and not new_str.endswith("\n"):
                new_str += "\n"

            lines.insert(insert_line, new_str)

            with open(path, "w") as f:
                f.writelines(lines)

            console.print(
                f"[green]Successfully inserted text at line {insert_line + 1} in {path}[/green]"
            )
            console.log(
                f"[InsertText] Successfully inserted text at line {insert_line + 1} in {path}"
            )
            return FileOperationResult(
                True, f"Successfully inserted text at line {insert_line + 1} in {path}"
            )
        except Exception as e:
            error_msg = f"Error inserting text: {str(e)}"
            console.log(f"[InsertText] Error: {error_msg}")
            return FileOperationResult(False, error_msg)
