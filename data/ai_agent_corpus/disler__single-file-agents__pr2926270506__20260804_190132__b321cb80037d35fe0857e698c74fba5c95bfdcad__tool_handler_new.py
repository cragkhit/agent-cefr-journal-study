#!/usr/bin/env python3

"""
Molecular tool handler for the Atomic/Composable Architecture implementation of the file editor agent.
This module combines atomic components to handle tool use requests from Claude.
"""

import traceback
from typing import Dict, Any, Optional, List, Union

import sys
import os

# Add the parent directory to the Python path to enable absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from atom.logging import log_info, log_error
from atom.file_operations import FileOperationResult, read_file, write_file, replace_in_file, insert_in_file

class ToolUseRequest:
    """
    Model representing a tool use request from Claude.
    """
    
    def __init__(self, command: str, path: str = None, **kwargs):
        """
        Initialize a tool use request.
        
        Args:
            command: The command to execute
            path: The path to operate on
            **kwargs: Additional arguments for the command
        """
        self.command = command
        self.path = path
        self.kwargs = kwargs
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ToolUseRequest':
        """
        Create a tool use request from a dictionary.
        
        Args:
            data: Dictionary containing the tool use request
            
        Returns:
            A ToolUseRequest instance
        """
        command = data.get("command")
        path = data.get("path")
        
        # Extract all other keys as kwargs
        kwargs = {k: v for k, v in data.items() if k not in ["command", "path"]}
        
        return cls(command, path, **kwargs)

class ToolHandler:
    """
    Handler for tool use requests from Claude.
    Combines atomic file operations to handle complex tool use requests.
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
            
            log_info("tool_handler", f"Received command: {request.command}, path: {request.path}")

            # Validate the request
            validation_result = ToolHandler._validate_request(request)
            if not validation_result.success:
                log_error("tool_handler", f"Validation error: {validation_result.message}")
                return {"error": validation_result.message}
            
            # Execute the appropriate file operation based on the command
            result = None
            
            if request.command == "view":
                view_range = request.kwargs.get("view_range")
                log_info("tool_handler", f"Calling view_file with view_range: {view_range}")
                
                start_line = None
                end_line = None
                if view_range:
                    start_line, end_line = view_range
                    
                result = read_file(request.path, start_line, end_line)

            elif request.command == "str_replace":
                old_str = request.kwargs.get("old_str")
                new_str = request.kwargs.get("new_str")
                log_info("tool_handler", "Calling str_replace")
                result = replace_in_file(request.path, old_str, new_str)

            elif request.command == "create":
                file_text = request.kwargs.get("file_text")
                log_info("tool_handler", "Calling create_file")
                result = write_file(request.path, file_text)

            elif request.command == "insert":
                insert_line = request.kwargs.get("insert_line")
                new_str = request.kwargs.get("new_str")
                log_info("tool_handler", f"Calling insert_text at line: {insert_line}")
                result = insert_in_file(request.path, insert_line, new_str)

            elif request.command == "undo_edit":
                log_info("tool_handler", "Calling undo_edit")
                result = FileOperationResult(True, "Undo functionality is not implemented in this version.")

            else:
                error_msg = f"Unknown command: {request.command}"
                log_error("tool_handler", error_msg)
                return {"error": error_msg}
            
            # Convert the result to a response for Claude
            return result.to_response()
                
        except Exception as e:
            error_msg = f"Error handling tool use: {str(e)}"
            log_error("tool_handler", error_msg, exc_info=True)
            return {"error": error_msg}
    
    @staticmethod
    def _validate_request(request: ToolUseRequest) -> FileOperationResult:
        """
        Validate the tool use request.
        
        Args:
            request: The tool use request to validate
            
        Returns:
            FileOperationResult with validation result
        """
        if not request.command:
            return FileOperationResult(False, "No command specified in tool use request")

        if not request.path and request.command != "undo_edit":  # undo_edit might not need a path
            return FileOperationResult(False, "No path specified in tool use request")
            
        # Validate command-specific parameters
        if request.command == "view":
            # View command is valid with just a path
            pass
            
        elif request.command == "str_replace":
            # Validate str_replace parameters
            old_str = request.kwargs.get("old_str")
            new_str = request.kwargs.get("new_str")
            
            if old_str is None:
                return FileOperationResult(False, "Missing 'old_str' parameter for str_replace command")
                
            if new_str is None:
                return FileOperationResult(False, "Missing 'new_str' parameter for str_replace command")
                
        elif request.command == "create":
            # Validate create parameters
            file_text = request.kwargs.get("file_text")
            # file_text can be None or empty, so no validation needed
            
        elif request.command == "insert":
            # Validate insert parameters
            insert_line = request.kwargs.get("insert_line")
            new_str = request.kwargs.get("new_str")
            
            if insert_line is None:
                return FileOperationResult(False, "Missing 'insert_line' parameter for insert command")
                
            if new_str is None:
                return FileOperationResult(False, "Missing 'new_str' parameter for insert command")
                
        elif request.command == "undo_edit":
            # undo_edit is valid with just a path
            pass
            
        else:
            return FileOperationResult(False, f"Unknown command: {request.command}")
            
        return FileOperationResult(True, "Request validation successful")
