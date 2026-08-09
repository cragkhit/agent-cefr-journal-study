#!/usr/bin/env python3

"""
ViewFile step for the Pipeline Architecture implementation of the file editor agent.
This step is responsible for viewing the contents of a file.
"""

import os
from typing import Dict, Any, Optional

import sys
import os

# Add the parent directory to the Python path to enable absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.utilities import console, FileOperationResult, normalize_path, display_file_content
from steps.file_operations.base_file_operation import BaseFileOperation

class ViewFile(BaseFileOperation):
    """
    ViewFile step for the file editor pipeline.
    Responsible for viewing the contents of a file.
    """
    
    def _execute_operation(self, request: Any) -> FileOperationResult:
        """
        View the contents of a file.

        Args:
            request: The request containing the path and view_range

        Returns:
            FileOperationResult with content or error message
        """
        try:
            path = request.path
            view_range = request.kwargs.get("view_range")
            
            console.log(f"[ViewFile] Viewing file: {path}, view_range: {view_range}")
            
            # Normalize the path
            path = normalize_path(path)

            if not os.path.exists(path):
                error_msg = f"File {path} does not exist"
                console.log(f"[ViewFile] Error: {error_msg}")
                return FileOperationResult(False, error_msg)

            with open(path, "r") as f:
                lines = f.readlines()

            if view_range:
                start, end = view_range
                # Convert to 0-indexed for Python
                start = max(0, start - 1)
                if end == -1:
                    end = len(lines)
                else:
                    end = min(len(lines), end)
                lines = lines[start:end]

            content = "".join(lines)

            # Display the file content (only for console, not returned to Claude)
            display_file_content(path, content)

            return FileOperationResult(True, f"Successfully viewed file {path}", content)
        except Exception as e:
            error_msg = f"Error viewing file: {str(e)}"
            console.log(f"[ViewFile] Error: {error_msg}")
            return FileOperationResult(False, error_msg)
