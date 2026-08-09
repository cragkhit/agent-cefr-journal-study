#!/usr/bin/env python3

"""
Atomic logging utilities for the Atomic/Composable Architecture implementation of the file editor agent.
These are the most basic building blocks for logging and console output.
"""

import traceback
from typing import Any, Dict, Optional
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

# Initialize rich console
console = Console()

def log_info(component: str, message: str) -> None:
    """
    Log an informational message.

    Args:
        component: The component that is logging the message
        message: The message to log
    """
    console.log(f"[{component}] {message}")

def log_warning(component: str, message: str) -> None:
    """
    Log a warning message.

    Args:
        component: The component that is logging the message
        message: The message to log
    """
    console.log(f"[{component}] [warning] {message}")
    console.print(f"[yellow]{message}[/yellow]")

def log_error(component: str, message: str, exc_info: bool = False) -> None:
    """
    Log an error message.

    Args:
        component: The component that is logging the message
        message: The message to log
        exc_info: Whether to include exception info
    """
    console.log(f"[{component}] [error] {message}")
    console.print(f"[red]{message}[/red]")
    
    if exc_info:
        console.log(traceback.format_exc())

def display_file_content(path: str, content: str) -> None:
    """
    Display file content with syntax highlighting.

    Args:
        path: Path to the file
        content: Content of the file
    """
    from .path_utils import get_file_extension
    
    file_extension = get_file_extension(path)
    syntax = Syntax(content, file_extension or "text", line_numbers=True)
    console.print(Panel(syntax, title=f"File: {path}"))

def display_token_usage(input_tokens: int, output_tokens: int) -> None:
    """
    Display token usage information in a rich formatted table.

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
