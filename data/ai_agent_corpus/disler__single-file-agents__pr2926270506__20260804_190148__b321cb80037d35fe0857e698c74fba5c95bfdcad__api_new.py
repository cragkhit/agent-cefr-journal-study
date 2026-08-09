#!/usr/bin/env python3

"""
API layer for file operations in the Vertical Slice Architecture.
"""

import os
import sys
import traceback
from typing import Dict, Any, Optional, List, Union

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from shared.utils import console
from features.file_operations.service import FileOperationService
from features.file_operations.model import ToolUseRequest, FileOperationResult

class FileOperationsAPI:
    """
    API for file operations.
    """
    
    @staticmethod
    def handle_tool_use(tool_use: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle text editor tool use from Claude.

        Args:
            tool_use: The tool use request from Claude

        Returns:
            Dictionary with result or error to send back to Claude
        """
        try:
            # Convert the tool use dictionary to a ToolUseRequest object
            request = ToolUseRequest.from_dict(tool_use)
            
            console.log(f"[handle_tool_use] Received command: {request.command}, path: {request.path}")

            if not request.command:
                error_msg = "No command specified in tool use request"
                console.log(f"[handle_tool_use] Error: {error_msg}")
                return {"error": error_msg}

            if not request.path and request.command != "undo_edit":  # undo_edit might not need a path
                error_msg = "No path specified in tool use request"
                console.log(f"[handle_tool_use] Error: {error_msg}")
                return {"error": error_msg}

            # The path normalization is now handled in each file operation function
            console.print(f"[blue]Executing {request.command} command on {request.path}[/blue]")

            result = None
            
            if request.command == "view":
                view_range = request.kwargs.get("view_range")
                console.log(
                    f"[handle_tool_use] Calling view_file with view_range: {view_range}"
                )
                result = FileOperationService.view_file(request.path, view_range)

            elif request.command == "str_replace":
                old_str = request.kwargs.get("old_str")
                new_str = request.kwargs.get("new_str")
                console.log(f"[handle_tool_use] Calling str_replace")
                result = FileOperationService.str_replace(request.path, old_str, new_str)

            elif request.command == "create":
                file_text = request.kwargs.get("file_text")
                console.log(f"[handle_tool_use] Calling create_file")
                result = FileOperationService.create_file(request.path, file_text)

            elif request.command == "insert":
                insert_line = request.kwargs.get("insert_line")
                new_str = request.kwargs.get("new_str")
                console.log(f"[handle_tool_use] Calling insert_text at line: {insert_line}")
                result = FileOperationService.insert_text(request.path, insert_line, new_str)

            elif request.command == "undo_edit":
                console.log(f"[handle_tool_use] Calling undo_edit")
                result = FileOperationService.undo_edit(request.path)

            else:
                error_msg = f"Unknown command: {request.command}"
                console.print(f"[red]{error_msg}[/red]")
                console.log(f"[handle_tool_use] Error: {error_msg}")
                return {"error": error_msg}
            
            # Convert the result to a dictionary
            if result.success:
                return {"result": result.data if result.data is not None else result.message}
            else:
                return {"error": result.message}
                
        except Exception as e:
            error_msg = f"Error handling tool use: {str(e)}"
            console.print(f"[red]{error_msg}[/red]")
            console.log(f"[handle_tool_use] Error: {str(e)}")
            console.log(traceback.format_exc())
            return {"error": error_msg}
