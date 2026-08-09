#!/usr/bin/env python3

"""
CommandRouter step for the Pipeline Architecture implementation of the file editor agent.
This step is responsible for routing requests to the appropriate file operation step.
"""

import traceback
from typing import Dict, Any, Optional

import sys
import os

# Add the parent directory to the Python path to enable absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.utilities import console, FileOperationResult
from steps.file_operations import ViewFile, StrReplace, CreateFile, InsertText, UndoEdit

class CommandRouter:
    """
    CommandRouter step for the file editor pipeline.
    Responsible for routing requests to the appropriate file operation step.
    """
    
    def __init__(self):
        """
        Initialize the command router with file operation steps.
        """
        self.file_operations = {
            "view": ViewFile(),
            "str_replace": StrReplace(),
            "create": CreateFile(),
            "insert": InsertText(),
            "undo_edit": UndoEdit()
        }
        
        console.log(f"[CommandRouter] Initialized with file operations: {list(self.file_operations.keys())}")
    
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the input data by routing to the appropriate file operation step.
        
        Args:
            data: The input data containing the request
            
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
                console.log(f"[CommandRouter] Error: {error_msg}")
                return {"error": error_msg, "stage": "command_router"}
                
            command = request.command
            console.log(f"[CommandRouter] Routing command: {command}")
            
            # Get the appropriate file operation step
            file_operation = self.file_operations.get(command)
            if not file_operation:
                error_msg = f"Unknown command: {command}"
                console.log(f"[CommandRouter] Error: {error_msg}")
                return {"error": error_msg, "stage": "command_router"}
            
            # Process the request with the file operation step
            console.log(f"[CommandRouter] Routing to {file_operation.__class__.__name__}")
            return file_operation.process(data)
                
        except Exception as e:
            error_msg = f"Error in command router: {str(e)}"
            console.print(f"[red]{error_msg}[/red]")
            console.log(f"[CommandRouter] Error: {str(e)}")
            console.log(traceback.format_exc())
            return {"error": error_msg, "stage": "command_router"}
