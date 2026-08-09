#!/usr/bin/env python3

"""
Atomic display utilities for the Atomic/Composable Architecture.
These are the most basic building blocks for displaying content.
"""

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
import sys
import os

# Add the parent directory to the Python path to enable absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from atom.path_utils.extension import get_file_extension

# Initialize rich console
console = Console()

def display_file_content(path: str, content: str) -> None:
    """
    Display file content with syntax highlighting.

    Args:
        path: Path to the file
        content: Content of the file
    """
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
