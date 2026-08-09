#!/usr/bin/env python3

"""
Shared utilities for the Vertical Slice Architecture implementation of the file editor agent.
"""

import os
import traceback
from typing import Dict, Any, Optional, List, Union
from rich.console import Console
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
    Display file content with syntax highlighting.

    Args:
        path: The path to the file
        content: The content to display
    """
    # Get file extension for syntax highlighting
    extension = os.path.splitext(path)[1][1:] if os.path.splitext(path)[1] else ""
    
    # Default to Python if no extension
    if not extension:
        extension = "python"
        
    # Display the content with syntax highlighting
    syntax = Syntax(content, extension, theme="monokai", line_numbers=True)
    console.print(syntax)

def display_token_usage(input_tokens: int, output_tokens: int) -> None:
    """
    Display token usage in a table.

    Args:
        input_tokens: Number of input tokens used
        output_tokens: Number of output tokens used
    """
    table = Table(title="Token Usage")
    table.add_column("Type", style="cyan")
    table.add_column("Count", style="green")
    
    table.add_row("Input Tokens", str(input_tokens))
    table.add_row("Output Tokens", str(output_tokens))
    table.add_row("Total Tokens", str(input_tokens + output_tokens))
    
    console.print(table)
