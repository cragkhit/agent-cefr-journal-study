#!/usr/bin/env -S uv run --script

# /// script
# dependencies = [
#   "openai-agents>=0.0.2",
#   "pytest>=7.4.0",
#   "rich>=13.7.0",
# ]
# ///

"""
Synchronous Agent Example

This example demonstrates how to run an agent synchronously instead of asynchronously.
It shows how to use the Runner.run_sync function for simpler code in non-async environments.

Run with:
    uv run 03_sync_agent.py --prompt "What are the benefits of exercise?"

Test with:
    uv run pytest 03_sync_agent.py
"""

import os
import sys
import argparse
import json
from typing import Optional, List, Dict, Any, Union
from rich.console import Console
from rich.panel import Panel

from openai import OpenAI
from agents import Agent, Runner

# Initialize console for rich output
console = Console()

def create_health_agent() -> Agent:
    """
    Create a health advisor agent.
    
    Returns:
        An Agent instance specialized in health topics.
    """
    instructions = """
    You are a health advisor with expertise in fitness, nutrition, and general wellness.
    Provide evidence-based information about health topics, focusing on practical advice.
    Always emphasize that you're not a medical professional and serious concerns should be 
    discussed with a healthcare provider.
    Keep responses concise and actionable.
    """
    
    return Agent(
        name="HealthAdvisor",
        instructions=instructions,
        model="gpt-4o-mini",
    )

def run_sync_agent(prompt: str, agent: Optional[Agent] = None) -> str:
    """
    Run an agent synchronously with the given prompt.
    
    Args:
        prompt: The user's query or prompt
        agent: Optional pre-configured agent. If None, a health advisor agent is created.
        
    Returns:
        The agent's response as a string
    """
    # Create agent if not provided
    if agent is None:
        agent = create_health_agent()
    
    # Run the agent synchronously with the prompt
    result = Runner.run_sync(agent, prompt)
    
    # Return the response
    return result.final_output

def main():
    """Main function to parse arguments and run the agent synchronously."""
    parser = argparse.ArgumentParser(description="Synchronous Agent Example")
    parser.add_argument("--prompt", "-p", type=str, required=True, 
                        help="The prompt to send to the agent")
    
    args = parser.parse_args()
    
    # Ensure API key is available
    if not os.environ.get("OPENAI_API_KEY"):
        console.print(Panel("[bold red]Error: OPENAI_API_KEY environment variable not set[/bold red]"))
        sys.exit(1)
    
    try:
        # Run the agent synchronously and get response
        response = run_sync_agent(args.prompt)
        
        # Display the response
        console.print(Panel(response, title="Synchronous Agent Response", border_style="green"))
    
    except Exception as e:
        console.print(Panel(f"[bold red]Error: {str(e)}[/bold red]"))
        sys.exit(1)

# Test functions
def test_create_health_agent():
    """Test that the health agent is created with the correct configuration."""
    agent = create_health_agent()
    assert agent.name == "HealthAdvisor"
    assert "health advisor" in agent.instructions.lower()
    assert agent.model == "gpt-4o-mini"

def test_run_sync_agent():
    """Test that the agent can run synchronously and produce a response."""
    import pytest
    
    # Skip this test if no API key is available
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")
    
    # Run a simple test query
    response = run_sync_agent("What are some quick exercises I can do at my desk?")
    
    # Verify we got a non-empty response
    assert response
    assert len(response) > 0
    # The response should contain relevant terms
    assert any(term in response.lower() for term in ["exercise", "stretch", "desk", "movement"])

if __name__ == "__main__":
    main()
