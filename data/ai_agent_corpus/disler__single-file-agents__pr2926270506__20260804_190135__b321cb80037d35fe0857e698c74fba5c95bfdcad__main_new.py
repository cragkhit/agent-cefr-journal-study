#!/usr/bin/env -S uv run --script

# /// script
# dependencies = [
#   "anthropic>=0.49.0",
#   "rich>=13.7.0",
# ]
# ///

"""
Main application entry point for the Layered Architecture implementation
of the Claude 3.7 File Editor Agent.

Example Usage:

# View a file
uv run main.py --prompt "Show me the content of README.md"

# Edit a file
uv run main.py --prompt "Fix the syntax error in sfa_poc.py"

# Create a new file
uv run main.py --prompt "Create a new file called hello.py with a function that prints Hello World"

# Run with higher thinking tokens
uv run main.py --prompt "Refactor README.md to make it more concise" --thinking 5000

# Increase max loops for complex tasks
uv run main.py --prompt "Create a Python class that implements a binary search tree" --max-loops 20
"""

import os
import sys
import argparse
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Add the current directory to the Python path to enable absolute imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Initialize rich console
console = Console()

# Define constants
DEFAULT_THINKING_TOKENS = 3000

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

def main():
    """Main entry point for the application."""
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Claude 3.7 File Editor Agent")
    parser.add_argument(
        "--prompt",
        "-p",
        required=True,
        help="The prompt for what file operations to perform",
    )
    parser.add_argument(
        "--max-loops",
        "-l",
        type=int,
        default=15,
        help="Maximum number of tool use loops (default: 15)",
    )
    parser.add_argument(
        "--thinking",
        "-t",
        type=int,
        default=DEFAULT_THINKING_TOKENS,
        help=f"Maximum thinking tokens (default: {DEFAULT_THINKING_TOKENS})",
    )
    parser.add_argument(
        "--efficiency",
        "-e",
        action="store_true",
        help="Enable token-efficient tool use (beta feature)",
    )
    args = parser.parse_args()

    console.print(Panel.fit("Claude 3.7 File Editor Agent (Layered Architecture)"))
    console.print(f"\n[bold]Prompt:[/bold] {args.prompt}\n")
    console.print(f"[dim]Thinking tokens: {args.thinking}[/dim]")
    console.print(f"[dim]Max loops: {args.max_loops}[/dim]")
    
    if args.efficiency:
        console.print(f"[dim]Token-efficient tools: Enabled[/dim]\n")
    else:
        console.print(f"[dim]Token-efficient tools: Disabled[/dim]\n")

    # For testing purposes, we'll just print a success message
    console.print("[green]Successfully loaded the Layered Architecture implementation![/green]")
    console.print("[yellow]This is a mock implementation for testing the architecture structure.[/yellow]")
    console.print("[yellow]In a real implementation, this would connect to the Claude API.[/yellow]")

    # Display mock token usage
    display_token_usage(1000, 500)

if __name__ == "__main__":
    main()
