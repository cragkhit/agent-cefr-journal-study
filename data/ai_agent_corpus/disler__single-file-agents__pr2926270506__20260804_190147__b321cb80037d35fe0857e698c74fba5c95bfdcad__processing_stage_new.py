#!/usr/bin/env python3

"""
Processing stage for the Pipeline Architecture implementation of the file editor agent.
This stage is responsible for executing file operations based on the validated request.
"""

import os
import traceback
from typing import Dict, Any, Optional, List, Union

import sys
import os

# Add the parent directory to the Python path to enable absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.utilities import console, normalize_path, display_file_content, FileOperationResult, ToolUseRequest

class ProcessingStage:
    """
    Processing stage for the file editor pipeline.
    Responsible for executing file operations based on the validated request.
    """
    
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the validated request by executing the appropriate file operation.
        
        Args:
            data: The data from the previous stage containing the validated request
            
        Returns:
            Dictionary with the operation result or error
        """
        try:
            # Check if there was an error in the previous stage
            if "error" in data:
                return data
                
            request = data.get("request")
            if not request:
                error_msg = "No request found in data from previous stage"
                console.log(f"[processing_stage] Error: {error_msg}")
                return {"error": error_msg, "stage": "processing"}
                
            console.log(f"[processing_stage] Processing command: {request.command}")
            
            # Execute the appropriate file operation based on the command
            result = None
            
            if request.command == "view":
                view_range = request.kwargs.get("view_range")
                console.log(
                    f"[processing_stage] Calling view_file with view_range: {view_range}"
                )
                result = self._view_file(request.path, view_range)

            elif request.command == "str_replace":
                old_str = request.kwargs.get("old_str")
                new_str = request.kwargs.get("new_str")
                console.log(f"[processing_stage] Calling str_replace")
                result = self._str_replace(request.path, old_str, new_str)

            elif request.command == "create":
                file_text = request.kwargs.get("file_text")
                console.log(f"[processing_stage] Calling create_file")
                result = self._create_file(request.path, file_text)

            elif request.command == "insert":
                insert_line = request.kwargs.get("insert_line")
                new_str = request.kwargs.get("new_str")
                console.log(f"[processing_stage] Calling insert_text at line: {insert_line}")
                result = self._insert_text(request.path, insert_line, new_str)

            elif request.command == "undo_edit":
                console.log(f"[processing_stage] Calling undo_edit")
                result = self._undo_edit(request.path)

            else:
                error_msg = f"Unknown command: {request.command}"
                console.print(f"[red]{error_msg}[/red]")
                console.log(f"[processing_stage] Error: {error_msg}")
                return {"error": error_msg, "stage": "processing"}
                
            # Pass the result to the next stage
            return {
                "result": result,
                "request": request,
                "stage": "processing",
                "status": "success"
            }
                
        except Exception as e:
            error_msg = f"Error in processing stage: {str(e)}"
            console.print(f"[red]{error_msg}[/red]")
            console.log(f"[processing_stage] Error: {str(e)}")
            console.log(traceback.format_exc())
            return {"error": error_msg, "stage": "processing"}
    
    def _view_file(self, path: str, view_range=None) -> FileOperationResult:
        """
        View the contents of a file.

        Args:
            path: The path to the file to view
            view_range: Optional start and end lines to view [start, end]

        Returns:
            FileOperationResult with content or error message
        """
        try:
            # Normalize the path
            path = normalize_path(path)

            if not os.path.exists(path):
                error_msg = f"File {path} does not exist"
                console.log(f"[view_file] Error: {error_msg}")
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
            console.print(f"[red]{error_msg}[/red]")
            console.log(f"[view_file] Error: {str(e)}")
            console.log(traceback.format_exc())
            return FileOperationResult(False, error_msg)

    def _str_replace(self, path: str, old_str: str, new_str: str) -> FileOperationResult:
        """
        Replace a specific string in a file.

        Args:
            path: The path to the file to modify
            old_str: The text to replace
            new_str: The new text to insert

        Returns:
            FileOperationResult with result or error message
        """
        try:
            # Normalize the path
            path = normalize_path(path)

            if not os.path.exists(path):
                error_msg = f"File {path} does not exist"
                console.log(f"[str_replace] Error: {error_msg}")
                return FileOperationResult(False, error_msg)

            with open(path, "r") as f:
                content = f.read()

            if old_str not in content:
                error_msg = f"The specified string was not found in the file {path}"
                console.log(f"[str_replace] Error: {error_msg}")
                return FileOperationResult(False, error_msg)

            new_content = content.replace(old_str, new_str, 1)

            with open(path, "w") as f:
                f.write(new_content)

            console.print(f"[green]Successfully replaced text in {path}[/green]")
            console.log(f"[str_replace] Successfully replaced text in {path}")
            return FileOperationResult(True, f"Successfully replaced text in {path}")
        except Exception as e:
            error_msg = f"Error replacing text: {str(e)}"
            console.print(f"[red]{error_msg}[/red]")
            console.log(f"[str_replace] Error: {str(e)}")
            console.log(traceback.format_exc())
            return FileOperationResult(False, error_msg)

    def _create_file(self, path: str, file_text: str) -> FileOperationResult:
        """
        Create a new file with specified content.

        Args:
            path: The path where the new file should be created
            file_text: The content to write to the new file

        Returns:
            FileOperationResult with result or error message
        """
        try:
            # Check if the path is empty or invalid
            if not path or not path.strip():
                error_msg = "Invalid file path provided: path is empty."
                console.log(f"[create_file] Error: {error_msg}")
                return FileOperationResult(False, error_msg)

            # Normalize the path
            path = normalize_path(path)

            # Check if the directory exists
            directory = os.path.dirname(path)
            if directory and not os.path.exists(directory):
                console.log(f"[create_file] Creating directory: {directory}")
                os.makedirs(directory)

            with open(path, "w") as f:
                f.write(file_text or "")

            console.print(f"[green]Successfully created file {path}[/green]")
            console.log(f"[create_file] Successfully created file {path}")
            return FileOperationResult(True, f"Successfully created file {path}")
        except Exception as e:
            error_msg = f"Error creating file: {str(e)}"
            console.print(f"[red]{error_msg}[/red]")
            console.log(f"[create_file] Error: {str(e)}")
            console.log(traceback.format_exc())
            return FileOperationResult(False, error_msg)

    def _insert_text(self, path: str, insert_line: int, new_str: str) -> FileOperationResult:
        """
        Insert text at a specific location in a file.

        Args:
            path: The path to the file to modify
            insert_line: The line number after which to insert the text
            new_str: The text to insert

        Returns:
            FileOperationResult with result or error message
        """
        try:
            if not path or not path.strip():
                error_msg = "Invalid file path provided: path is empty."
                console.log(f"[insert_text] Error: {error_msg}")
                return FileOperationResult(False, error_msg)

            # Normalize the path
            path = normalize_path(path)

            if not os.path.exists(path):
                error_msg = f"File {path} does not exist"
                console.log(f"[insert_text] Error: {error_msg}")
                return FileOperationResult(False, error_msg)

            if insert_line is None:
                error_msg = "No line number specified: insert_line is missing."
                console.log(f"[insert_text] Error: {error_msg}")
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
                console.log(f"[insert_text] Error: {error_msg}")
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
                f"[insert_text] Successfully inserted text at line {insert_line + 1} in {path}"
            )
            return FileOperationResult(
                True, f"Successfully inserted text at line {insert_line + 1} in {path}"
            )
        except Exception as e:
            error_msg = f"Error inserting text: {str(e)}"
            console.print(f"[red]{error_msg}[/red]")
            console.log(f"[insert_text] Error: {str(e)}")
            console.log(traceback.format_exc())
            return FileOperationResult(False, error_msg)

    def _undo_edit(self, path: str) -> FileOperationResult:
        """
        Placeholder for undo_edit functionality.
        In a real implementation, you would need to track edit history.

        Args:
            path: The path to the file whose last edit should be undone

        Returns:
            FileOperationResult with message about undo functionality
        """
        try:
            if not path or not path.strip():
                error_msg = "Invalid file path provided: path is empty."
                console.log(f"[undo_edit] Error: {error_msg}")
                return FileOperationResult(False, error_msg)

            # Normalize the path
            path = normalize_path(path)

            message = "Undo functionality is not implemented in this version."
            console.print(f"[yellow]{message}[/yellow]")
            console.log(f"[undo_edit] {message}")
            return FileOperationResult(True, message)
        except Exception as e:
            error_msg = f"Error in undo_edit: {str(e)}"
            console.print(f"[red]{error_msg}[/red]")
            console.log(f"[undo_edit] Error: {str(e)}")
            console.log(traceback.format_exc())
            return FileOperationResult(False, error_msg)
