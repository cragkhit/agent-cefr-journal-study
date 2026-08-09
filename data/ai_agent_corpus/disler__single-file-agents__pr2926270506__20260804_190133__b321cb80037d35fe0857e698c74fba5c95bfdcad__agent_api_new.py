#!/usr/bin/env python3

"""
Organism-level agent API for the Atomic/Composable Architecture implementation of the file editor agent.
This module combines molecular components to provide a high-level API for the file editor agent.
"""

import os
import sys
import argparse
from typing import Dict, Any, Optional, List, Union, Tuple
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from anthropic import Anthropic

import sys
import os

# Add the parent directory to the Python path to enable absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from molecule.file_editor import FileEditor
from molecule.tool_handler import ToolHandler
from atom.logging import log_info, log_error, display_token_usage

# Initialize rich console
console = Console()

class AgentAPI:
    """
    High-level API for the file editor agent.
    Combines molecular components to provide a user-facing interface.
    """
    
    @staticmethod
    def run(prompt: str, max_loops: int = 15, thinking_tokens: int = 3000, use_efficiency: bool = False) -> None:
        """
        Run the file editor agent with the given prompt.

        Args:
            prompt: The user's prompt
            max_loops: Maximum number of tool use loops
            thinking_tokens: Maximum tokens for thinking
            use_efficiency: Whether to use token-efficient tool use beta feature
        """
        # Get API key
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            console.print(
                "[red]Error: ANTHROPIC_API_KEY environment variable is not set[/red]"
            )
            console.print(
                "Please set it with: export ANTHROPIC_API_KEY='your-api-key-here'"
            )
            log_error("agent_api", "ANTHROPIC_API_KEY environment variable is not set")
            sys.exit(1)

        # Initialize Anthropic client
        client = Anthropic(api_key=api_key)

        console.print(Panel.fit("Claude 3.7 File Editor Agent (Atomic/Composable Architecture)"))

        console.print(f"\n[bold]Prompt:[/bold] {prompt}\n")
        console.print(f"[dim]Thinking tokens: {thinking_tokens}[/dim]")
        console.print(f"[dim]Max loops: {max_loops}[/dim]")
        if use_efficiency:
            console.print(f"[dim]Token-efficient tools: Enabled[/dim]\n")
        else:
            console.print(f"[dim]Token-efficient tools: Disabled[/dim]\n")

        try:
            # Run the agent
            response, input_tokens, output_tokens = FileEditor.run_agent(
                client, 
                prompt, 
                ToolHandler.handle_tool_use,
                thinking_tokens, 
                max_loops, 
                use_efficiency
            )

            # Print the final response
            console.print(Panel(Markdown(response), title="Claude's Response"))

            # Display token usage with rich table
            display_token_usage(input_tokens, output_tokens)

        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")
            log_error("agent_api", f"Error: {str(e)}", exc_info=True)
            sys.exit(1)
    
    @staticmethod
    def parse_args() -> argparse.Namespace:
        """
        Parse command-line arguments.

        Returns:
            Parsed arguments
        """
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
            default=3000,
            help="Maximum thinking tokens (default: 3000)",
        )
        parser.add_argument(
            "--efficiency",
            "-e",
            action="store_true",
            help="Enable token-efficient tool use (beta feature)",
        )
        return parser.parse_args()
