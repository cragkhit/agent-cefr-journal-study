#!/usr/bin/env python3

"""
StrReplace step for the Pipeline Architecture implementation of the file editor agent.
This step is responsible for replacing text in a file.
"""

import os
from typing import Dict, Any, Optional

import sys
import os

# Add the parent directory to the Python path to enable absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.utilities import console, FileOperationResult, normalize_path
from steps.file_operations.base_file_operation import BaseFileOperation

class StrReplace(BaseFileOperation):
    """
    StrReplace step for the file editor pipeline.
    Responsible for replacing text in a file.
    """
    
    def _execute_operation(self, request: Any) -> FileOperationResult:
        """
        Replace a specific string in a file.

        Args:
            request: The request containing the path, old_str, and new_str

        Returns:
            FileOperationResult with result or error message
        """
        try:
            path = request.path
            old_str = request.kwargs.get("old_str")
            new_str = request.kwargs.get("new_str")
            
            console.log(f"[StrReplace] Replacing text in file: {path}")
            
            # Normalize the path
            path = normalize_path(path)

            if not os.path.exists(path):
                error_msg = f"File {path} does not exist"
                console.log(f"[StrReplace] Error: {error_msg}")
                return FileOperationResult(False, error_msg)

            with open(path, "r") as f:
                content = f.read()

            if old_str not in content:
                error_msg = f"The specified string was not found in the file {path}"
                console.log(f"[StrReplace] Error: {error_msg}")
                return FileOperationResult(False, error_msg)

            new_content = content.replace(old_str, new_str, 1)

            with open(path, "w") as f:
                f.write(new_content)

            console.print(f"[green]Successfully replaced text in {path}[/green]")
            console.log(f"[StrReplace] Successfully replaced text in {path}")
            return FileOperationResult(True, f"Successfully replaced text in {path}")
        except Exception as e:
            error_msg = f"Error replacing text: {str(e)}"
            console.log(f"[StrReplace] Error: {error_msg}")
            return FileOperationResult(False, error_msg)
