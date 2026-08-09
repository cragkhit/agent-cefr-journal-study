#!/usr/bin/env python3

"""
CreateFile step for the Pipeline Architecture implementation of the file editor agent.
This step is responsible for creating a new file with specified content.
"""

import os
from typing import Dict, Any, Optional

import sys
import os

# Add the parent directory to the Python path to enable absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.utilities import console, FileOperationResult, normalize_path
from steps.file_operations.base_file_operation import BaseFileOperation

class CreateFile(BaseFileOperation):
    """
    CreateFile step for the file editor pipeline.
    Responsible for creating a new file with specified content.
    """
    
    def _execute_operation(self, request: Any) -> FileOperationResult:
        """
        Create a new file with specified content.

        Args:
            request: The request containing the path and file_text

        Returns:
            FileOperationResult with result or error message
        """
        try:
            path = request.path
            file_text = request.kwargs.get("file_text")
            
            console.log(f"[CreateFile] Creating file: {path}")
            
            # Check if the path is empty or invalid
            if not path or not path.strip():
                error_msg = "Invalid file path provided: path is empty."
                console.log(f"[CreateFile] Error: {error_msg}")
                return FileOperationResult(False, error_msg)

            # Normalize the path
            path = normalize_path(path)

            # Check if the directory exists
            directory = os.path.dirname(path)
            if directory and not os.path.exists(directory):
                console.log(f"[CreateFile] Creating directory: {directory}")
                os.makedirs(directory)

            with open(path, "w") as f:
                f.write(file_text or "")

            console.print(f"[green]Successfully created file {path}[/green]")
            console.log(f"[CreateFile] Successfully created file {path}")
            return FileOperationResult(True, f"Successfully created file {path}")
        except Exception as e:
            error_msg = f"Error creating file: {str(e)}"
            console.log(f"[CreateFile] Error: {error_msg}")
            return FileOperationResult(False, error_msg)
