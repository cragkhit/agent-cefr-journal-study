#!/usr/bin/env -S uv run --script

# /// script
# dependencies = [
#   "openai-agents>=0.0.2",
#   "pytest>=7.4.0",
#   "rich>=13.7.0",
#   "opentelemetry-api>=1.20.0",
#   "opentelemetry-sdk>=1.20.0",
# ]
# ///

"""
Agent with Tracing Example

This example demonstrates how to use tracing with agents to monitor and debug their execution.
It shows how to set up OpenTelemetry tracing and capture spans for agent operations.

Run with:
    uv run 04_agent_with_tracing.py --prompt "What is the capital of France?"

Test with:
    uv run pytest 04_agent_with_tracing.py
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

# Import OpenTelemetry components
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

# Initialize console for rich output
console = Console()

# Set up OpenTelemetry tracing
def setup_tracing():
    """Set up OpenTelemetry tracing with console exporter."""
    # Create a tracer provider
    provider = TracerProvider()
    
    # Add a console exporter to see spans in the console
    console_exporter = ConsoleSpanExporter()
    processor = SimpleSpanProcessor(console_exporter)
    provider.add_span_processor(processor)
    
    # Set the global tracer provider
    trace.set_tracer_provider(provider)
    
    # Get a tracer
    return trace.get_tracer("agent_tracer")

def create_geography_agent() -> Agent:
    """
    Create a geography specialist agent.
    
    Returns:
        An Agent instance specialized in geography topics.
    """
    instructions = """
    You are a geography specialist with knowledge about countries, capitals, landmarks, and geographical features.
    Provide accurate, concise information about geographical topics.
    Include interesting facts when relevant but prioritize accuracy.
    """
    
    return Agent(
        name="GeographySpecialist",
        instructions=instructions,
        model="gpt-4o-mini",
    )

async def run_traced_agent(prompt: str, tracer) -> str:
    """
    Run an agent with tracing for the given prompt.
    
    Args:
        prompt: The user's query or prompt
        tracer: The OpenTelemetry tracer to use
        
    Returns:
        The agent's response as a string
    """
    # Create a span for the entire agent execution
    with tracer.start_as_current_span("agent_execution") as span:
        # Add attributes to the span
        span.set_attribute("prompt", prompt)
        
        # Create the agent
        with tracer.start_as_current_span("create_agent"):
            agent = create_geography_agent()
            span.set_attribute("agent_name", agent.name)
        
        # Run the agent with the prompt
        with tracer.start_as_current_span("Runner.run"):
            result = await Runner.run(agent, prompt)
            # Note: In the current version, RunResult doesn't have usage attribute
            # We'll just record the response length as a basic metric
            span.set_attribute("response_length", len(result.final_output))
            span.set_attribute("response_first_chars", result.final_output[:30])
        
        # Return the response
        return result.final_output

def main():
    """Main function to parse arguments and run the agent with tracing."""
    parser = argparse.ArgumentParser(description="Agent with Tracing Example")
    parser.add_argument("--prompt", "-p", type=str, required=True, 
                        help="The prompt to send to the agent")
    
    args = parser.parse_args()
    
    # Ensure API key is available
    if not os.environ.get("OPENAI_API_KEY"):
        console.print(Panel("[bold red]Error: OPENAI_API_KEY environment variable not set[/bold red]"))
        sys.exit(1)
    
    try:
        # Set up tracing
        tracer = setup_tracing()
        
        # Run the agent with tracing and get response
        response = asyncio.run(run_traced_agent(args.prompt, tracer))
        
        # Display the response
        console.print(Panel(response, title="Agent Response with Tracing", border_style="green"))
    
    except Exception as e:
        console.print(Panel(f"[bold red]Error: {str(e)}[/bold red]"))
        sys.exit(1)

# Test functions
def test_create_geography_agent():
    """Test that the geography agent is created with the correct configuration."""
    agent = create_geography_agent()
    assert agent.name == "GeographySpecialist"
    assert "geography specialist" in agent.instructions.lower()
    assert agent.model == "gpt-4o-mini"

def test_run_traced_agent():
    """Test that the agent can run with tracing and produce a response."""
    import pytest
    
    # Skip this test if no API key is available
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")
    
    # Set up tracing
    tracer = setup_tracing()
    
    # Run a simple test query
    response = asyncio.run(run_traced_agent("What is the capital of Japan?", tracer))
    
    # Verify we got a non-empty response
    assert response
    assert len(response) > 0
    # The response should contain "Tokyo"
    assert "Tokyo" in response

if __name__ == "__main__":
    main()
