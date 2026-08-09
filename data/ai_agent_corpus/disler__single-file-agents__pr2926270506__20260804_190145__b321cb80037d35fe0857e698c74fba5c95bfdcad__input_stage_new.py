#!/usr/bin/env python3

"""
Input stage for the Pipeline Architecture implementation of the file editor agent.
This stage is responsible for parsing and validating tool use requests.
"""

import traceback
from typing import Dict, Any, Optional, List, Union

import sys
import os

# Add the parent directory to the Python path to enable absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.utilities import console, ToolUseRequest, FileOperationResult

class InputStage:
    """
    Input stage for the file editor pipeline.
    Responsible for parsing and validating tool use requests.
    """
    
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the input data by parsing and validating the tool use request.
        
        Args:
            data: The input data containing the tool use request
            
        Returns:
            Dictionary with the parsed request or error
        """
        try:
            console.log(f"[input_stage] Processing tool use request")
            
            # Convert the tool use dictionary to a ToolUseRequest object
            request = ToolUseRequest.from_dict(data)
            
            console.log(f"[input_stage] Received command: {request.command}, path: {request.path}")

            # Validate the request
            validation_result = self._validate_request(request)
            if not validation_result.success:
                console.log(f"[input_stage] Validation error: {validation_result.message}")
                return {"error": validation_result.message, "stage": "input"}
            
            # Pass the validated request to the next stage
            return {
                "request": request,
                "stage": "input",
                "status": "success"
            }
                
        except Exception as e:
            error_msg = f"Error in input stage: {str(e)}"
            console.print(f"[red]{error_msg}[/red]")
            console.log(f"[input_stage] Error: {str(e)}")
            console.log(traceback.format_exc())
            return {"error": error_msg, "stage": "input"}
    
    def _validate_request(self, request: ToolUseRequest) -> FileOperationResult:
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
