#!/usr/bin/env python3

"""
Base file operation step for the Pipeline Architecture implementation of the file editor agent.
This module provides a base class for all file operation steps.
"""

import traceback
from typing import Dict, Any, Optional

import sys
import os

# Add the parent directory to the Python path to enable absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.utilities import console, FileOperationResult, normalize_path

class BaseFileOperation:
    """
    Base class for all file operation steps.
    """
    
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the input data by executing the file operation.
        
        Args:
            data: The input data containing the request and previous stage results
            
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
                console.log(f"[{self.__class__.__name__}] Error: {error_msg}")
                return {"error": error_msg, "stage": self.__class__.__name__}
            
            # Execute the file operation
            result = self._execute_operation(request)
            
            # Pass the result to the next stage
            return {
                "result": result,
                "request": request,
                "stage": self.__class__.__name__,
                "status": "success"
            }
                
        except Exception as e:
            error_msg = f"Error in {self.__class__.__name__}: {str(e)}"
            console.print(f"[red]{error_msg}[/red]")
            console.log(f"[{self.__class__.__name__}] Error: {str(e)}")
            console.log(traceback.format_exc())
            return {"error": error_msg, "stage": self.__class__.__name__}
    
    def _execute_operation(self, request: Any) -> FileOperationResult:
        """
        Execute the file operation.
        
        Args:
            request: The request containing the operation parameters
            
        Returns:
            FileOperationResult with the operation result
        """
        raise NotImplementedError("File operation steps must implement the _execute_operation method")
