#!/usr/bin/env python3

"""
Shared utilities for the Pipeline Architecture implementation of the file editor agent.
"""

import os
import json
import traceback
from typing import Dict, Any, Optional, List, Union
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

# Initialize rich console
console = Console()

def normalize_path(path: str) -> str:
    """
    Normalize file paths to handle various formats (absolute, relative, Windows paths, etc.)

    Args:
        path: The path to normalize

    Returns:
        The normalized path
    """
    if not path:
        return path

    # Handle Windows backslash paths if provided
    path = path.replace("\\", os.sep)

    is_windows_path = False
    if os.name == "nt" and len(path) > 1 and path[1] == ":":
        is_windows_path = True

    # Handle /repo/ paths from Claude (tool use convention)
    if path.startswith("/repo/"):
        path = os.path.join(os.getcwd(), path[6:])
        return path

    if path.startswith("/"):
        # Handle case when Claude provides paths with leading slash
        if path == "/" or path == "/.":
            # Special case for root directory
            path = os.getcwd()
        else:
            # Replace leading slash with current working directory
            path = os.path.join(os.getcwd(), path[1:])
    elif path.startswith("./"):
        # Handle relative paths starting with ./
        path = os.path.join(os.getcwd(), path[2:])
    elif not os.path.isabs(path) and not is_windows_path:
        # For non-absolute paths that aren't Windows paths either
        path = os.path.join(os.getcwd(), path)

    return path

def display_file_content(path: str, content: str) -> None:
    """
    Display file content with syntax highlighting

    Args:
        path: Path to the file
        content: Content of the file
    """
    file_extension = os.path.splitext(path)[1][1:]  # Get extension without the dot
    syntax = Syntax(content, file_extension or "text", line_numbers=True)
    console.print(Panel(syntax, title=f"File: {path}"))

def display_token_usage(input_tokens: int, output_tokens: int) -> None:
    """
    Display token usage information in a rich formatted table

    Args:
        input_tokens: Number of input tokens used
        output_tokens: Number of output tokens used
    """
    total_tokens = input_tokens + output_tokens
    token_ratio = output_tokens / input_tokens if input_tokens > 0 else 0

    # Create a table for token usage
    table = Table(title="Token Usage Statistics", expand=True)

    # Add columns with proper styling
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Count", style="magenta", justify="right")
    table.add_column("Percentage", justify="right")

    # Add rows with data
    table.add_row(
        "Input Tokens", f"{input_tokens:,}", f"{input_tokens/total_tokens:.1%}"
    )
    table.add_row(
        "Output Tokens", f"{output_tokens:,}", f"{output_tokens/total_tokens:.1%}"
    )
    table.add_row("Total Tokens", f"{total_tokens:,}", "100.0%")
    table.add_row("Output/Input Ratio", f"{token_ratio:.2f}", "")

    console.print()
    console.print(table)

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
