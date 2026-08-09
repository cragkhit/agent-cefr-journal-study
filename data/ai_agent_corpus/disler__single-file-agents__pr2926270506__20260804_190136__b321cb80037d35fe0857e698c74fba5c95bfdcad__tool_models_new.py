#!/usr/bin/env python3

"""
Models for the Layered Architecture implementation of the file editor agent.
"""

from typing import Dict, Any, Optional, List, Union

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
