#!/usr/bin/env python3

"""
Atomic file operation result model for the Atomic/Composable Architecture.
This is the most basic building block for representing file operation results.
"""

from typing import Any, Dict

class FileOperationResult:
    """
    Model representing the result of a file operation.
    """
    
    def __init__(self, success: bool, message: str, data: Any = None):
        """
        Initialize a file operation result.
        
        Args:
            success: Whether the operation was successful
            message: A message describing the result
            data: Optional data returned by the operation
        """
        self.success = success
        self.message = message
        self.data = data
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the result to a dictionary.
        
        Returns:
            Dictionary representation of the result
        """
        return {
            "success": self.success,
            "message": self.message,
            "data": self.data
        }
    
    def to_response(self) -> Dict[str, Any]:
        """
        Convert the result to a response for Claude.
        
        Returns:
            Dictionary with result or error to send back to Claude
        """
        if self.success:
            return {"result": self.data if self.data is not None else self.message}
        else:
            return {"error": self.message}
