#!/usr/bin/env -S uv run --script

# /// script
# dependencies = [
#   "openai-agents>=0.0.2",
#   "pytest>=7.4.0",
#   "rich>=13.7.0",
# ]
# ///

"""
Agent with Agent as Tool Example

This example demonstrates how to use an agent as a tool for another agent.
It shows how to create a research agent that can be used as a tool by a blog writer agent.

Run with:
    uv run 08_agent_with_agent_as_tool.py --prompt "Write a blog post about quantum computing"

Test with:
    uv run pytest 08_agent_with_agent_as_tool.py
"""

import os
import sys
import argparse
import json
import asyncio
from typing import Optional, List, Dict, Any, Union
from rich.console import Console
from rich.panel import Panel

from openai import OpenAI
from agents import Agent, Runner

# Initialize console for rich output
console = Console()

def create_research_agent() -> Agent:
    """
    Create a research agent that can gather information on topics.
    
    Returns:
        An Agent instance specialized in research.
    """
    instructions = """
    You are a research specialist who excels at gathering accurate information on various topics.
    Your responses should be factual, well-organized, and comprehensive.
    Include relevant details, statistics, and context when available.
    Always cite your sources if you're providing specific facts or quotes.
    Focus on providing high-quality, reliable information that would be useful for content creation.
    """
    
    return Agent(
        name="ResearchSpecialist",
        instructions=instructions,
        model="gpt-4o-mini",
    )

def create_blog_writer_agent(research_agent: Agent) -> Agent:
    """
    Create a blog writer agent that can use a research agent as a tool.
    
    Args:
        research_agent: The research agent to use as a tool
        
    Returns:
        An Agent instance specialized in blog writing with research capabilities
    """
    instructions = """
    You are a professional blog writer who creates engaging, informative content.
    Your writing should be clear, conversational, and tailored to a general audience.
    Structure your blog posts with an introduction, body paragraphs, and conclusion.
    Use the research tool available to you to gather accurate information on topics.
    Incorporate the research seamlessly into your writing while maintaining your voice.
    """
    
    # Convert the research agent into a tool
    research_tool = research_agent.as_tool(
        tool_name="research_topic",
        tool_description="Research a specific topic to gather accurate information. Provide a clear, specific topic or question to research."
    )
    
    return Agent(
        name="BlogWriter",
        instructions=instructions,
        model="gpt-4o-mini",
        tools=[research_tool]
    )

async def run_blog_writer_system(prompt: str) -> str:
    """
    Run the blog writer system with the given prompt.
    
    Args:
        prompt: The topic or request for a blog post
        
    Returns:
        The blog post content
    """
    # Create the research agent
    research_agent = create_research_agent()
    
    # Create the blog writer agent with the research agent as a tool
    blog_writer = create_blog_writer_agent(research_agent)
    
    # Run the blog writer agent with the prompt
    result = await Runner.run(blog_writer, prompt)
    
    # Return the blog post
    return result.final_output

def main():
    """Main function to parse arguments and run the blog writer system."""
    parser = argparse.ArgumentParser(description="Agent with Agent as Tool Example")
    parser.add_argument("--prompt", "-p", type=str, required=True, 
                        help="The topic or request for a blog post")
    
    args = parser.parse_args()
    
    # Ensure API key is available
    if not os.environ.get("OPENAI_API_KEY"):
        console.print(Panel("[bold red]Error: OPENAI_API_KEY environment variable not set[/bold red]"))
        sys.exit(1)
    
    try:
        # Run the blog writer system and get the blog post
        blog_post = asyncio.run(run_blog_writer_system(args.prompt))
        
        # Display the blog post
        console.print(Panel(blog_post, title="Blog Post", border_style="green"))
    
    except Exception as e:
        console.print(Panel(f"[bold red]Error: {str(e)}[/bold red]"))
        sys.exit(1)

# Test functions
def test_create_research_agent():
    """Test that the research agent is created with the correct configuration."""
    agent = create_research_agent()
    assert agent.name == "ResearchSpecialist"
    assert "research specialist" in agent.instructions.lower()
    assert agent.model == "gpt-4o-mini"

def test_create_blog_writer_agent():
    """Test that the blog writer agent is created with the correct configuration."""
    research_agent = create_research_agent()
    blog_writer = create_blog_writer_agent(research_agent)
    
    assert blog_writer.name == "BlogWriter"
    assert "blog writer" in blog_writer.instructions.lower()
    assert len(blog_writer.tools) == 1
    assert blog_writer.tools[0].name == "research_topic"

def test_run_blog_writer_system():
    """Test that the blog writer system can run and produce a blog post."""
    import pytest
    
    # Skip this test if no API key is available
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")
    
    # Run a test query for a simple blog post
    blog_post = asyncio.run(run_blog_writer_system("Write a short blog post about artificial intelligence"))
    
    # Verify we got a non-empty blog post
    assert blog_post
    assert len(blog_post) > 0
    # The blog post should contain relevant terms
    assert any(term in blog_post.lower() for term in ["ai", "artificial intelligence", "technology"])

if __name__ == "__main__":
    main()
