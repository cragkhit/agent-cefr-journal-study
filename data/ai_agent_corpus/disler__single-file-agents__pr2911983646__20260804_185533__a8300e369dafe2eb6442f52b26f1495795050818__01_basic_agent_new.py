#!/usr/bin/env -S uv run --script

# /// script
# dependencies = [
#   "openai-agents>=0.0.2",
#   "pytest>=7.4.0",
#   "rich>=13.7.0",
# ]
# ///

"""
Basic Agent Example

This example demonstrates how to create a simple agent using the OpenAI Agents SDK.
The agent can respond to user queries with helpful information.

Run with:
    uv run 01_basic_agent.py --prompt "Tell me about climate change"

Test with:
    uv run pytest 01_basic_agent.py
"""

import os
import sys
import argparse
import json
from typing import Optional, List, Dict, Any, Union
from rich.console import Console
from rich.panel import Panel

from openai import OpenAI
from openai.types.chat import ChatCompletion
from agents import Agent, Runner

# Initialize console for rich output
console = Console()

def create_basic_agent(instructions: str = None) -> Agent:
    """
    Create a basic agent with the given instructions.
    
    Args:
        instructions: Custom instructions for the agent. If None, default instructions are used.
        
    Returns:
        An Agent instance configured with the provided instructions.
    """
    default_instructions = """
    You are a helpful assistant that provides accurate and concise information.
    Always be respectful and provide factual responses based on the latest available information.
    If you don't know something, admit it rather than making up information.
    """
    
    # Create and return a basic agent
    return Agent(
        name="BasicAssistant",
        instructions=instructions or default_instructions,
        model="gpt-4o-mini",  # Using GPT-4o-mini as specified in requirements
    )

async def run_basic_agent(prompt: str, agent: Optional[Agent] = None) -> str:
    """
    Run the basic agent with the given prompt.
    
    Args:
        prompt: The user's query or prompt
        agent: Optional pre-configured agent. If None, a default agent is created.
        
    Returns:
        The agent's response as a string
    """
    # Create agent if not provided
    if agent is None:
        agent = create_basic_agent()
    
    # Run the agent with the prompt
    result = await Runner.run(agent, prompt)
    
    # Extract and return the text response
    return result.final_output

def main():
    """Main function to parse arguments and run the agent."""
    parser = argparse.ArgumentParser(description="Basic Agent Example")
    parser.add_argument("--prompt", "-p", type=str, required=True, 
                        help="The prompt to send to the agent")
    
    args = parser.parse_args()
    
    # Ensure API key is available
    if not os.environ.get("OPENAI_API_KEY"):
        console.print(Panel("[bold red]Error: OPENAI_API_KEY environment variable not set[/bold red]"))
        sys.exit(1)
    
    try:
        # Run the agent and get response
        import asyncio
        response = asyncio.run(run_basic_agent(args.prompt))
        
        # Display the response
        console.print(Panel(response, title="Agent Response", border_style="green"))
    
    except Exception as e:
        console.print(Panel(f"[bold red]Error: {str(e)}[/bold red]"))
        sys.exit(1)

# Test functions
def test_create_basic_agent():
    """Test that the agent is created with the correct configuration."""
    agent = create_basic_agent("Test instructions")
    assert agent.name == "BasicAssistant"
    assert agent.instructions == "Test instructions"
    assert agent.model == "gpt-4o-mini"

def test_run_basic_agent():
    """Test that the agent can run and produce a response."""
    import pytest
    
    # Skip this test if no API key is available
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")
    
    # Run a simple test query
    import asyncio
    response = asyncio.run(run_basic_agent("What is 2+2?"))
    
    # Verify we got a non-empty response
    assert response
    assert len(response) > 0
    # The response should contain "4" somewhere
    assert "4" in response

if __name__ == "__main__":
    main()
