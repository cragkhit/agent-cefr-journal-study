#!/usr/bin/env -S uv run --script

# /// script
# dependencies = [
#   "openai-agents>=0.0.2",
#   "pytest>=7.4.0",
#   "rich>=13.7.0",
# ]
# ///

"""
Multi-Agent Example

This example demonstrates how to create and use multiple agents that work together.
It includes a coordinator agent that delegates tasks to specialist agents.

Run with:
    uv run 02_multi_agent.py --prompt "Explain quantum computing and its applications"

Test with:
    uv run pytest 02_multi_agent.py
"""

import os
import sys
import argparse
import json
import asyncio
from typing import Optional, List, Dict, Any, Union, Tuple
from rich.console import Console
from rich.panel import Panel

from openai import OpenAI
from agents import Agent, Runner, handoff

# Initialize console for rich output
console = Console()

def create_science_agent() -> Agent:
    """
    Create a science specialist agent.
    
    Returns:
        An Agent instance specialized in scientific topics.
    """
    instructions = """
    You are a science specialist with deep knowledge of physics, chemistry, biology, and related fields.
    Provide accurate, detailed scientific explanations while making complex concepts accessible.
    Use analogies and examples when helpful to illustrate scientific principles.
    Always clarify when something is theoretical or not yet proven.
    """
    
    return Agent(
        name="ScienceSpecialist",
        instructions=instructions,
        model="gpt-4o-mini",
        handoff_description="Use this agent for questions about scientific topics, theories, and concepts."
    )

def create_tech_agent() -> Agent:
    """
    Create a technology specialist agent.
    
    Returns:
        An Agent instance specialized in technology topics.
    """
    instructions = """
    You are a technology specialist with expertise in computer science, programming, AI, and digital technologies.
    Provide clear, accurate explanations of technical concepts and their practical applications.
    When discussing programming, focus on concepts rather than writing extensive code.
    Explain how technologies work and their real-world impact.
    """
    
    return Agent(
        name="TechSpecialist",
        instructions=instructions,
        model="gpt-4o-mini",
        handoff_description="Use this agent for questions about technology, computing, programming, and digital systems."
    )

def create_coordinator_agent(specialists: List[Agent]) -> Agent:
    """
    Create a coordinator agent that can delegate to specialists.
    
    Args:
        specialists: List of specialist agents to which tasks can be delegated
        
    Returns:
        An Agent instance that coordinates between specialists
    """
    instructions = """
    You are a coordinator who determines which specialist should handle a user's question.
    Analyze the user's query and decide which specialist would be best suited to respond.
    For questions that span multiple domains, choose the specialist most relevant to the core of the question.
    """
    
    # Create handoffs to specialist agents
    handoffs = [handoff(agent) for agent in specialists]
    
    return Agent(
        name="Coordinator",
        instructions=instructions,
        model="gpt-4o-mini",
        handoffs=handoffs
    )

async def run_multi_agent_system(prompt: str) -> str:
    """
    Run the multi-agent system with the given prompt.
    
    Args:
        prompt: The user's query or prompt
        
    Returns:
        The final response from the appropriate specialist agent
    """
    # Create specialist agents
    science_agent = create_science_agent()
    tech_agent = create_tech_agent()
    
    # Create coordinator agent with specialists
    coordinator = create_coordinator_agent([science_agent, tech_agent])
    
    # Run the coordinator agent with the prompt
    result = await Runner.run(coordinator, prompt)
    
    # Return the final response
    return result.final_output

def main():
    """Main function to parse arguments and run the multi-agent system."""
    parser = argparse.ArgumentParser(description="Multi-Agent Example")
    parser.add_argument("--prompt", "-p", type=str, required=True, 
                        help="The prompt to send to the multi-agent system")
    
    args = parser.parse_args()
    
    # Ensure API key is available
    if not os.environ.get("OPENAI_API_KEY"):
        console.print(Panel("[bold red]Error: OPENAI_API_KEY environment variable not set[/bold red]"))
        sys.exit(1)
    
    try:
        # Run the multi-agent system and get response
        response = asyncio.run(run_multi_agent_system(args.prompt))
        
        # Display the response
        console.print(Panel(response, title="Multi-Agent Response", border_style="green"))
    
    except Exception as e:
        console.print(Panel(f"[bold red]Error: {str(e)}[/bold red]"))
        sys.exit(1)

# Test functions
def test_create_specialist_agents():
    """Test that specialist agents are created with the correct configuration."""
    science_agent = create_science_agent()
    tech_agent = create_tech_agent()
    
    assert science_agent.name == "ScienceSpecialist"
    assert tech_agent.name == "TechSpecialist"
    assert "science specialist" in science_agent.instructions.lower()
    assert "technology specialist" in tech_agent.instructions.lower()

def test_create_coordinator_agent():
    """Test that the coordinator agent is created with the correct configuration."""
    science_agent = create_science_agent()
    tech_agent = create_tech_agent()
    
    coordinator = create_coordinator_agent([science_agent, tech_agent])
    
    assert coordinator.name == "Coordinator"
    assert "coordinator" in coordinator.instructions.lower()
    assert len(coordinator.handoffs) == 2

def test_run_multi_agent_system():
    """Test that the multi-agent system can run and produce a response."""
    import pytest
    
    # Skip this test if no API key is available
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")
    
    # Run a simple test query that should go to the tech specialist
    response = asyncio.run(run_multi_agent_system("What is machine learning?"))
    
    # Verify we got a non-empty response
    assert response
    assert len(response) > 0

if __name__ == "__main__":
    main()
