#!/usr/bin/env python3

"""
Models for the file operations feature in the Vertical Slice Architecture.
"""

import os
import sys
from typing import Dict, Any, Optional, List, Union

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

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
