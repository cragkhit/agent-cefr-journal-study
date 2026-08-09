#!/usr/bin/env -S uv run --script

# /// script
# dependencies = [
#   "openai-agents>=0.0.2",
#   "pytest>=7.4.0",
#   "rich>=13.7.0",
# ]
# ///

"""
Agent Orchestration Example

This example demonstrates how to orchestrate multiple agents to work together on complex tasks.
It shows how to create a system where specialized agents collaborate under the coordination
of a manager agent.

Run with:
    uv run 11_agent_orchestration.py --prompt "Create a blog post about climate change solutions"

Test with:
    uv run pytest 11_agent_orchestration.py
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
from agents import Agent, Runner, handoff, Context

# Initialize console for rich output
console = Console()

def create_research_agent() -> Agent:
    """
    Create a research agent that gathers information.
    
    Returns:
        An Agent instance specialized in research.
    """
    instructions = """
    You are a research specialist who excels at gathering accurate information on various topics.
    Your task is to collect relevant facts, statistics, and context on the assigned topic.
    Focus on providing comprehensive, well-organized information that covers different aspects of the topic.
    Include both general information and specific details that would be useful for content creation.
    Always prioritize accuracy and cite sources when providing specific facts.
    """
    
    return Agent(
        name="ResearchSpecialist",
        instructions=instructions,
        model="gpt-4o-mini",
        handoff_description="Use this agent to gather comprehensive information on a topic."
    )

def create_outline_agent() -> Agent:
    """
    Create an outline agent that structures content.
    
    Returns:
        An Agent instance specialized in creating outlines.
    """
    instructions = """
    You are an outline specialist who excels at organizing information into clear, logical structures.
    Your task is to create well-structured outlines for content based on research provided.
    Include main sections, subsections, and key points to cover in each section.
    Ensure the outline has a logical flow and covers the topic comprehensively.
    Focus on creating a structure that will engage readers while effectively communicating information.
    """
    
    return Agent(
        name="OutlineSpecialist",
        instructions=instructions,
        model="gpt-4o-mini",
        handoff_description="Use this agent to create a structured outline based on research."
    )

def create_content_agent() -> Agent:
    """
    Create a content agent that writes engaging content.
    
    Returns:
        An Agent instance specialized in content writing.
    """
    instructions = """
    You are a content writing specialist who excels at creating engaging, informative content.
    Your task is to write high-quality content based on the provided outline and research.
    Use a conversational, engaging tone while maintaining accuracy and clarity.
    Include an attention-grabbing introduction, well-developed body paragraphs, and a compelling conclusion.
    Incorporate the research seamlessly into the content while maintaining a consistent voice.
    """
    
    return Agent(
        name="ContentSpecialist",
        instructions=instructions,
        model="gpt-4o-mini",
        handoff_description="Use this agent to write engaging content based on an outline and research."
    )

def create_editor_agent() -> Agent:
    """
    Create an editor agent that refines and polishes content.
    
    Returns:
        An Agent instance specialized in editing.
    """
    instructions = """
    You are an editing specialist who excels at refining and polishing content.
    Your task is to review content for clarity, coherence, grammar, and style.
    Improve sentence structure, word choice, and flow while maintaining the original voice.
    Ensure the content is well-organized, engaging, and free of errors.
    Focus on making the content more impactful and reader-friendly.
    """
    
    return Agent(
        name="EditingSpecialist",
        instructions=instructions,
        model="gpt-4o-mini",
        handoff_description="Use this agent to refine and polish content."
    )

def create_manager_agent(specialists: List[Agent]) -> Agent:
    """
    Create a manager agent that coordinates the work of specialist agents.
    
    Args:
        specialists: List of specialist agents to coordinate
        
    Returns:
        An Agent instance that manages the content creation process
    """
    instructions = """
    You are a content manager who coordinates the work of specialist agents to create high-quality content.
    Your task is to:
    1. Understand the content request
    2. Delegate research to the Research Specialist
    3. Have the Outline Specialist create a structure based on the research
    4. Have the Content Specialist write content based on the outline and research
    5. Have the Editing Specialist refine and polish the content
    6. Deliver the final polished content
    
    Manage the workflow efficiently and ensure each specialist has the information they need.
    """
    
    # Create handoffs to specialist agents
    handoffs = [handoff(agent) for agent in specialists]
    
    return Agent(
        name="ContentManager",
        instructions=instructions,
        model="gpt-4o-mini",
        handoffs=handoffs
    )

async def orchestrate_content_creation(prompt: str) -> str:
    """
    Orchestrate the content creation process with multiple specialized agents.
    
    Args:
        prompt: The content request
        
    Returns:
        The final polished content
    """
    # Create specialist agents
    research_agent = create_research_agent()
    outline_agent = create_outline_agent()
    content_agent = create_content_agent()
    editor_agent = create_editor_agent()
    
    # Create manager agent with specialists
    manager = create_manager_agent([research_agent, outline_agent, content_agent, editor_agent])
    
    # Create a context to track the workflow
    context = Context()
    
    # Run the manager agent with the prompt and context
    result = await Runner.run(manager, prompt, context=context)
    
    # Return the final content
    return result.final_output

def main():
    """Main function to parse arguments and run the content creation system."""
    parser = argparse.ArgumentParser(description="Agent Orchestration Example")
    parser.add_argument("--prompt", "-p", type=str, required=True, 
                        help="The content request to process")
    
    args = parser.parse_args()
    
    # Ensure API key is available
    if not os.environ.get("OPENAI_API_KEY"):
        console.print(Panel("[bold red]Error: OPENAI_API_KEY environment variable not set[/bold red]"))
        sys.exit(1)
    
    try:
        # Run the content creation system and get the final content
        console.print(Panel("Starting content creation process...", title="Status", border_style="blue"))
        content = asyncio.run(orchestrate_content_creation(args.prompt))
        
        # Display the final content
        console.print(Panel(content, title="Final Content", border_style="green"))
    
    except Exception as e:
        console.print(Panel(f"[bold red]Error: {str(e)}[/bold red]"))
        sys.exit(1)

# Test functions
def test_create_specialist_agents():
    """Test that specialist agents are created with the correct configuration."""
    research_agent = create_research_agent()
    outline_agent = create_outline_agent()
    content_agent = create_content_agent()
    editor_agent = create_editor_agent()
    
    assert research_agent.name == "ResearchSpecialist"
    assert outline_agent.name == "OutlineSpecialist"
    assert content_agent.name == "ContentSpecialist"
    assert editor_agent.name == "EditingSpecialist"
    
    assert "research specialist" in research_agent.instructions.lower()
    assert "outline specialist" in outline_agent.instructions.lower()
    assert "content writing specialist" in content_agent.instructions.lower()
    assert "editing specialist" in editor_agent.instructions.lower()

def test_create_manager_agent():
    """Test that the manager agent is created with the correct configuration."""
    research_agent = create_research_agent()
    outline_agent = create_outline_agent()
    content_agent = create_content_agent()
    editor_agent = create_editor_agent()
    
    manager = create_manager_agent([research_agent, outline_agent, content_agent, editor_agent])
    
    assert manager.name == "ContentManager"
    assert "content manager" in manager.instructions.lower()
    assert len(manager.handoffs) == 4

def test_orchestrate_content_creation():
    """Test that the content creation system can run and produce content."""
    import pytest
    
    # Skip this test if no API key is available
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")
    
    # Run a test with a simple content request
    # Use a shorter timeout for testing
    content = asyncio.run(orchestrate_content_creation("Write a short paragraph about renewable energy"))
    
    # Verify we got non-empty content
    assert content
    assert len(content) > 0
    # The content should contain relevant terms
    assert any(term in content.lower() for term in ["renewable", "energy", "sustainable"])

if __name__ == "__main__":
    main()
