#!/usr/bin/env -S uv run --script

# /// script
# dependencies = [
#   "openai-agents>=0.0.2",
#   "pytest>=7.4.0",
#   "rich>=13.7.0",
#   "markdown>=3.5.2",
# ]
# ///

"""
Research and Blog Agent System

This example demonstrates a complete system where research agents and blog agents work together
to create markdown blogs. It showcases the integration of multiple agent capabilities.

Run with:
    uv run 13_research_blog_system.py --topic "Artificial Intelligence Ethics" --output blog_post.md

Test with:
    uv run pytest 13_research_blog_system.py
"""

import os
import sys
import argparse
import json
import asyncio
import markdown
from datetime import datetime
from typing import Optional, List, Dict, Any, Union, Tuple
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from openai import OpenAI
from agents import Agent, Runner, handoff, Context, function_tool

# Initialize console for rich output
console = Console()

# Define function tools for the research agent
@function_tool
def search_for_information(query: str, depth: int = 3) -> str:
    """
    Simulated search for information on a topic.
    
    Args:
        query: The search query
        depth: The depth of the search (1-5, with 5 being most comprehensive)
        
    Returns:
        A string containing the search results
    """
    # This is a mock implementation - in a real application, you would call a search API
    search_results = {
        "artificial intelligence ethics": """
            Artificial Intelligence Ethics is a field focused on ensuring AI systems are developed and used responsibly.
            
            Key principles include:
            1. Transparency - AI systems should be explainable and understandable
            2. Fairness - AI should not perpetuate or amplify biases
            3. Privacy - AI systems should respect user privacy and data rights
            4. Accountability - Clear responsibility for AI decisions and impacts
            5. Safety - AI systems should be reliable and minimize harm
            
            Current challenges include:
            - Algorithmic bias in facial recognition and criminal justice systems
            - Privacy concerns with data collection and surveillance
            - Autonomous weapons and military applications
            - Job displacement due to automation
            - Concentration of AI power among few tech companies
            
            Organizations like the IEEE, EU Commission, and various academic institutions have developed ethical frameworks for AI development.
        """,
        
        "climate change solutions": """
            Climate Change Solutions encompass various approaches to mitigate and adapt to global warming.
            
            Key mitigation strategies include:
            1. Renewable energy transition (solar, wind, hydro, geothermal)
            2. Energy efficiency improvements in buildings and industry
            3. Sustainable transportation (electric vehicles, public transit)
            4. Carbon capture and storage technologies
            5. Reforestation and ecosystem restoration
            
            Adaptation strategies include:
            - Climate-resilient infrastructure
            - Water conservation and management
            - Sustainable agriculture practices
            - Early warning systems for extreme weather
            - Planned relocation of vulnerable communities
            
            Policy approaches include carbon pricing, regulations, subsidies for clean technology, and international agreements like the Paris Climate Accord.
            
            Emerging technologies such as green hydrogen, advanced batteries, and direct air capture show promise for addressing climate challenges.
        """,
        
        "quantum computing": """
            Quantum Computing leverages quantum mechanics principles to process information in fundamentally new ways.
            
            Key concepts:
            1. Qubits - Unlike classical bits (0 or 1), qubits can exist in superposition of states
            2. Entanglement - Quantum particles become correlated, enabling complex computations
            3. Quantum gates - Operations that manipulate qubits to perform calculations
            
            Potential applications:
            - Cryptography and security (both breaking existing systems and creating new ones)
            - Drug discovery and materials science through molecular simulation
            - Optimization problems in logistics, finance, and energy
            - Machine learning and AI acceleration
            - Climate modeling and complex system simulation
            
            Current state: Quantum computers remain in early development with 50-100+ qubit systems from IBM, Google, and others. Quantum advantage (surpassing classical computers) has been demonstrated for specific problems.
            
            Challenges include error correction, qubit stability (decoherence), and scaling systems to practical sizes.
            
            Major players include IBM, Google, Microsoft, IonQ, Rigetti, and various academic research groups.
        """
    }
    
    # Find the most relevant result based on the query
    for key, value in search_results.items():
        if any(word in query.lower() for word in key.split()):
            # Adjust the depth of information
            lines = value.strip().split('\n')
            result_depth = max(5, min(len(lines), depth * 5))
            return '\n'.join(lines[:result_depth])
    
    # Default response if no match found
    return "No specific information found on this topic. Please try a more general query."

@function_tool
def analyze_topic(topic: str) -> str:
    """
    Analyze a topic to identify key aspects for research.
    
    Args:
        topic: The topic to analyze
        
    Returns:
        A string containing analysis of the topic with key aspects to research
    """
    # This is a mock implementation - in a real application, this would be more sophisticated
    topic_analyses = {
        "artificial intelligence ethics": """
            Topic Analysis: Artificial Intelligence Ethics
            
            Key aspects to research:
            1. Ethical frameworks and principles for AI development
            2. Bias and fairness in AI systems
            3. Privacy implications of AI technologies
            4. Accountability and transparency in AI decision-making
            5. Regulatory approaches and governance models
            6. Economic and social impacts of AI deployment
            7. Case studies of ethical failures and successes
            8. Future challenges and emerging ethical concerns
        """,
        
        "climate change solutions": """
            Topic Analysis: Climate Change Solutions
            
            Key aspects to research:
            1. Renewable energy technologies and implementation
            2. Carbon capture and sequestration approaches
            3. Policy mechanisms (carbon pricing, regulations, incentives)
            4. Adaptation strategies for vulnerable communities
            5. Agricultural and land use changes
            6. Behavioral and lifestyle modifications
            7. Economic considerations and just transition
            8. International cooperation frameworks
        """,
        
        "quantum computing": """
            Topic Analysis: Quantum Computing
            
            Key aspects to research:
            1. Fundamental quantum mechanics principles relevant to computing
            2. Quantum computing architectures and hardware approaches
            3. Quantum algorithms and computational advantages
            4. Potential applications across industries
            5. Current state of development and key players
            6. Challenges and limitations of quantum systems
            7. Quantum programming languages and software tools
            8. Timeline and roadmap for practical quantum computing
        """
    }
    
    # Find the most relevant analysis
    for key, value in topic_analyses.items():
        if any(word in topic.lower() for word in key.split()):
            return value.strip()
    
    # Default analysis if no match found
    return f"""
        Topic Analysis: {topic}
        
        Key aspects to research:
        1. Historical context and development
        2. Current state and major concepts
        3. Key stakeholders and perspectives
        4. Challenges and controversies
        5. Future trends and developments
        6. Practical applications and implications
        7. Related fields and intersections
        8. Resources for further learning
    """.strip()

# Define function tools for the blog agent
@function_tool
def generate_blog_outline(topic: str, research: str) -> str:
    """
    Generate an outline for a blog post based on research.
    
    Args:
        topic: The blog topic
        research: The research information to incorporate
        
    Returns:
        A string containing a structured blog outline
    """
    # This is a simplified implementation - in a real application, this would use more sophisticated logic
    # Extract key points from research
    research_lines = research.strip().split('\n')
    key_points = [line.strip() for line in research_lines if line.strip() and not line.strip().startswith('#')]
    
    # Create a basic outline structure
    outline = f"""
        # Blog Outline: {topic}
        
        ## Introduction
        - Hook: Engaging opening to capture reader interest
        - Context: Brief background on {topic}
        - Thesis: Main point or argument of the blog post
        
        ## Main Section 1: Overview and Background
        - Historical context
        - Current relevance
        - Key concepts and definitions
        
        ## Main Section 2: Key Aspects and Analysis
    """
    
    # Add research points to the outline
    for i, point in enumerate(key_points[:5]):
        if len(point) > 100:  # Only use shorter points
            continue
        outline += f"\n        - Point {i+1}: {point}"
    
    # Complete the outline
    outline += f"""
        
        ## Main Section 3: Implications and Applications
        - Practical applications
        - Future developments
        - Challenges and opportunities
        
        ## Conclusion
        - Summary of key points
        - Final thoughts
        - Call to action or next steps
    """
    
    return outline.strip()

@function_tool
def format_blog_as_markdown(title: str, content: str) -> str:
    """
    Format a blog post as markdown.
    
    Args:
        title: The blog post title
        content: The blog post content
        
    Returns:
        A string containing the formatted markdown
    """
    # Ensure the content has proper markdown formatting
    if not content.startswith('#'):
        content = f"# {title}\n\n{content}"
    
    # Add metadata
    markdown = f"""---
title: "{title}"
date: "{datetime.now().strftime('%Y-%m-%d')}"
author: "AI Research & Blog System"
tags: ["ai", "research", "blog"]
---

{content}
"""
    
    return markdown

def create_research_agent() -> Agent:
    """
    Create a research agent that gathers and analyzes information.
    
    Returns:
        An Agent instance specialized in research.
    """
    instructions = """
    You are a research specialist who excels at gathering and analyzing information on various topics.
    Your task is to:
    1. Understand the research request
    2. Use the search_for_information tool to gather relevant information
    3. Use the analyze_topic tool to identify key aspects for research
    4. Synthesize the information into a comprehensive, well-organized research report
    5. Include relevant facts, statistics, and context
    6. Ensure the research is accurate, balanced, and thorough
    
    Your research should be detailed enough to serve as the foundation for content creation.
    """
    
    # Create the research agent with function tools
    return Agent(
        name="ResearchSpecialist",
        instructions=instructions,
        model="gpt-4o-mini",
        tools=[search_for_information, analyze_topic],
        handoff_description="Use this agent to conduct thorough research on a topic."
    )

def create_blog_agent() -> Agent:
    """
    Create a blog agent that writes engaging blog posts.
    
    Returns:
        An Agent instance specialized in blog writing.
    """
    instructions = """
    You are a blog writing specialist who excels at creating engaging, informative blog posts.
    Your task is to:
    1. Understand the blog request and research provided
    2. Use the generate_blog_outline tool to create a structured outline
    3. Write a comprehensive blog post based on the outline and research
    4. Use the format_blog_as_markdown tool to format the post properly
    5. Ensure the blog is engaging, informative, and well-structured
    
    Your blog posts should be conversational yet informative, with a clear introduction,
    well-developed body sections, and a compelling conclusion.
    """
    
    # Create the blog agent with function tools
    return Agent(
        name="BlogSpecialist",
        instructions=instructions,
        model="gpt-4o-mini",
        tools=[generate_blog_outline, format_blog_as_markdown],
        handoff_description="Use this agent to write engaging blog posts based on research."
    )

def create_coordinator_agent(specialists: List[Agent]) -> Agent:
    """
    Create a coordinator agent that manages the research and blog writing process.
    
    Args:
        specialists: List of specialist agents to coordinate
        
    Returns:
        An Agent instance that coordinates the content creation process
    """
    instructions = """
    You are a content coordinator who manages the process of creating research-based blog posts.
    Your task is to:
    1. Understand the blog topic request
    2. Delegate research to the Research Specialist
    3. Provide the research to the Blog Specialist to create a blog post
    4. Ensure the final blog post is comprehensive, engaging, and based on solid research
    5. Deliver the final markdown blog post
    
    Manage the workflow efficiently and ensure each specialist has the information they need.
    """
    
    # Create handoffs to specialist agents
    handoffs = [handoff(agent) for agent in specialists]
    
    return Agent(
        name="ContentCoordinator",
        instructions=instructions,
        model="gpt-4o-mini",
        handoffs=handoffs
    )

async def create_research_blog(topic: str) -> str:
    """
    Create a research-based blog post on the given topic.
    
    Args:
        topic: The blog topic
        
    Returns:
        A string containing the markdown blog post
    """
    # Create specialist agents
    research_agent = create_research_agent()
    blog_agent = create_blog_agent()
    
    # Create coordinator agent with specialists
    coordinator = create_coordinator_agent([research_agent, blog_agent])
    
    # Create a context to track the workflow
    context = Context()
    
    # Run the coordinator agent with the topic and context
    result = await Runner.run(coordinator, f"Create a blog post about {topic}", context=context)
    
    # Return the final blog post
    return result.final_output

def main():
    """Main function to parse arguments and run the research blog system."""
    parser = argparse.ArgumentParser(description="Research and Blog Agent System")
    parser.add_argument("--topic", "-t", type=str, required=True, 
                        help="The topic for the blog post")
    parser.add_argument("--output", "-o", type=str, default=None,
                        help="Optional file path to save the markdown blog post")
    
    args = parser.parse_args()
    
    # Ensure API key is available
    if not os.environ.get("OPENAI_API_KEY"):
        console.print(Panel("[bold red]Error: OPENAI_API_KEY environment variable not set[/bold red]"))
        sys.exit(1)
    
    try:
        # Create the blog post
        console.print(Panel(f"Creating a blog post about '{args.topic}'...", title="Status", border_style="blue"))
        blog_post = asyncio.run(create_research_blog(args.topic))
        
        # Display the blog post
        console.print(Panel(Markdown(blog_post), title="Blog Post", border_style="green"))
        
        # Save to file if output path is provided
        if args.output:
            with open(args.output, "w") as f:
                f.write(blog_post)
            console.print(f"[green]Blog post saved to {args.output}[/green]")
    
    except Exception as e:
        console.print(Panel(f"[bold red]Error: {str(e)}[/bold red]"))
        sys.exit(1)

# Test functions
def test_research_tools():
    """Test that the research tools work correctly."""
    # Test search tool
    search_result = search_for_information("artificial intelligence ethics")
    assert "ethics" in search_result.lower()
    assert "principles" in search_result.lower()
    
    # Test analysis tool
    analysis_result = analyze_topic("artificial intelligence ethics")
    assert "analysis" in analysis_result.lower()
    assert "key aspects" in analysis_result.lower()

def test_blog_tools():
    """Test that the blog tools work correctly."""
    # Test outline tool
    outline = generate_blog_outline(
        "AI Ethics",
        "AI Ethics involves principles like transparency, fairness, and accountability."
    )
    assert "introduction" in outline.lower()
    assert "conclusion" in outline.lower()
    
    # Test markdown formatting tool
    markdown = format_blog_as_markdown(
        "AI Ethics",
        "# AI Ethics\n\nThis is a blog post about AI ethics."
    )
    assert "title" in markdown.lower()
    assert "date" in markdown.lower()
    assert "ai ethics" in markdown.lower()

def test_create_agents():
    """Test that the agents are created with the correct configuration."""
    research_agent = create_research_agent()
    blog_agent = create_blog_agent()
    coordinator = create_coordinator_agent([research_agent, blog_agent])
    
    assert research_agent.name == "ResearchSpecialist"
    assert blog_agent.name == "BlogSpecialist"
    assert coordinator.name == "ContentCoordinator"
    
    assert len(research_agent.tools) == 2
    assert len(blog_agent.tools) == 2
    assert len(coordinator.handoffs) == 2

def test_create_research_blog():
    """Test that the research blog system can run and produce a blog post."""
    import pytest
    
    # Skip this test if no API key is available
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")
    
    # Run a test with a simple topic
    # Use a shorter timeout for testing
    blog_post = asyncio.run(create_research_blog("AI Ethics"))
    
    # Verify we got a non-empty blog post
    assert blog_post
    assert len(blog_post) > 0
    # The blog post should contain relevant terms
    assert any(term in blog_post.lower() for term in ["ai", "ethics", "principles"])

if __name__ == "__main__":
    main()
