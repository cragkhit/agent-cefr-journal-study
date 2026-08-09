#!/usr/bin/env python3

"""
Organism-level file agent for the Atomic/Composable Architecture implementation of the file editor agent.
This module pulls together all components to provide a high-level API for the file editor agent.
"""

import sys
import os
import json
import argparse
import traceback
from typing import Dict, Any, Optional, List, Union
from rich.console import Console

# Add the parent directory to the Python path to enable absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import anthropic
from molecule.file_crud import FileCRUD
from organism.file_agent import run_agent
from atom.logging.console import log_info, log_error, log_warning
from atom.logging.display import display_token_usage

class FileAgent:
    """
    File agent that pulls together all components to provide a high-level API for the file editor agent.
    """
    
    @staticmethod
    def run(prompt: str, api_key: Optional[str] = None, max_tool_use_loops: int = 15, 
            token_efficient_tool_use: bool = True) -> None:
        """
        Run the file editor agent with the specified prompt.
        
        Args:
            prompt: The prompt to send to Claude
            api_key: Optional API key for Anthropic
            max_tool_use_loops: Maximum number of tool use loops
            token_efficient_tool_use: Whether to use token-efficient tool use
        """
        log_info("file_agent", f"Running file editor agent with prompt: {prompt}")
        
        # Get the API key
        api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        
        if not api_key:
            log_error("file_agent", "No API key provided. Please set the ANTHROPIC_API_KEY environment variable or provide an API key.")
            
            # For testing purposes, we'll just print a success message
            console = Console()
            console.print("[green]Successfully loaded the Atomic/Composable Architecture implementation![/green]")
            console.print("[yellow]This is a mock implementation for testing the architecture structure.[/yellow]")
            console.print("[yellow]In a real implementation, this would connect to the Claude API.[/yellow]")
            
            # Display mock token usage
            display_token_usage(1000, 500)
            
            return
            
        # Initialize the Anthropic client
        client = anthropic.Anthropic(api_key=api_key)
        
        # Run the agent
        try:
            input_tokens, output_tokens = run_agent(
                client=client,
                prompt=prompt,
                handle_tool_use=FileCRUD.handle_tool_use,
                max_tool_use_loops=max_tool_use_loops,
                token_efficient_tool_use=token_efficient_tool_use
            )
            
            # Display token usage
            display_token_usage(input_tokens, output_tokens)
            
            log_info("file_agent", "File editor agent completed successfully.")
            
        except Exception as e:
            log_error("file_agent", f"Error running file editor agent: {str(e)}", exc_info=True)

def main():
    """
    Main entry point for the file editor agent.
    """
    parser = argparse.ArgumentParser(description="File Editor Agent")
    parser.add_argument("--prompt", type=str, help="Prompt to send to Claude")
    parser.add_argument("--api-key", type=str, help="API key for Anthropic")
    parser.add_argument("--max-tool-use-loops", type=int, default=15, help="Maximum number of tool use loops")
    parser.add_argument("--token-efficient-tool-use", action="store_true", help="Use token-efficient tool use")
    
    args = parser.parse_args()
    
    if not args.prompt:
        log_error("main", "No prompt provided. Please provide a prompt with --prompt.")
        return
        
    FileAgent.run(
        prompt=args.prompt,
        api_key=args.api_key,
        max_tool_use_loops=args.max_tool_use_loops,
        token_efficient_tool_use=args.token_efficient_tool_use
    )

if __name__ == "__main__":
    main()
