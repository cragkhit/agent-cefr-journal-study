#!/usr/bin/env -S uv run --script

# /// script
# dependencies = [
#   "openai-agents>=0.0.2",
#   "pytest>=7.4.0",
#   "rich>=13.7.0",
#   "pydantic>=2.0.0",
# ]
# ///

"""
Agent with Guardrails Example

This example demonstrates how to use guardrails with agents to filter and validate inputs.
It shows how to create an agent with input validation to prevent prompt injection and ensure
proper input format.

Run with:
    uv run 10_agent_with_guardrails.py --prompt "Summarize this article about renewable energy"

Test with:
    uv run pytest 10_agent_with_guardrails.py
"""

import os
import sys
import argparse
import json
import asyncio
import re
from typing import Optional, List, Dict, Any, Union
from rich.console import Console
from rich.panel import Panel
from pydantic import BaseModel, Field

from openai import OpenAI
from agents import Agent, Runner, InputGuardrail

# Initialize console for rich output
console = Console()

# Define a custom input guardrail for content moderation
class ContentModerationGuardrail(InputGuardrail):
    """
    A guardrail that filters out potentially harmful or inappropriate content.
    """
    
    def __init__(self):
        """Initialize the content moderation guardrail."""
        # List of terms to filter out (simplified for example purposes)
        self.filtered_terms = [
            "hack", "exploit", "bypass", "illegal", "steal", "attack",
            "malware", "virus", "phishing", "scam", "fraud"
        ]
    
    def filter(self, input_str: str) -> Optional[str]:
        """
        Filter the input string for potentially harmful content.
        
        Args:
            input_str: The input string to filter
            
        Returns:
            The filtered string if it passes, or None if it should be rejected
        """
        # Convert to lowercase for case-insensitive matching
        lower_input = input_str.lower()
        
        # Check for filtered terms
        for term in self.filtered_terms:
            if term in lower_input:
                return None  # Reject the input
        
        return input_str  # Accept the input
    
    def get_rejection_message(self, input_str: str) -> str:
        """
        Get a message explaining why the input was rejected.
        
        Args:
            input_str: The rejected input string
            
        Returns:
            A message explaining the rejection
        """
        return "Your input contains terms that may be related to harmful or inappropriate content. Please rephrase your request."

# Define a custom input guardrail for input format validation
class FormatValidationGuardrail(InputGuardrail):
    """
    A guardrail that ensures inputs follow a specific format.
    """
    
    def __init__(self, min_length: int = 5, max_length: int = 500):
        """
        Initialize the format validation guardrail.
        
        Args:
            min_length: Minimum allowed input length
            max_length: Maximum allowed input length
        """
        self.min_length = min_length
        self.max_length = max_length
    
    def filter(self, input_str: str) -> Optional[str]:
        """
        Filter the input string based on format requirements.
        
        Args:
            input_str: The input string to filter
            
        Returns:
            The input string if it passes, or None if it should be rejected
        """
        # Check length constraints
        if len(input_str) < self.min_length:
            return None  # Too short
        
        if len(input_str) > self.max_length:
            return None  # Too long
        
        return input_str  # Accept the input
    
    def get_rejection_message(self, input_str: str) -> str:
        """
        Get a message explaining why the input was rejected.
        
        Args:
            input_str: The rejected input string
            
        Returns:
            A message explaining the rejection
        """
        if len(input_str) < self.min_length:
            return f"Your input is too short. Please provide at least {self.min_length} characters."
        
        if len(input_str) > self.max_length:
            return f"Your input is too long. Please limit your request to {self.max_length} characters."
        
        return "Your input does not meet the format requirements."

def create_protected_agent() -> Agent:
    """
    Create an agent with input guardrails for protection.
    
    Returns:
        An Agent instance with input guardrails.
    """
    instructions = """
    You are a helpful assistant that provides information and assistance on various topics.
    You prioritize user safety and ethical responses.
    Provide accurate, helpful information while avoiding potentially harmful content.
    Be concise but thorough in your responses.
    """
    
    # Create guardrails
    content_guardrail = ContentModerationGuardrail()
    format_guardrail = FormatValidationGuardrail(min_length=5, max_length=500)
    
    # Create the agent with guardrails
    return Agent(
        name="ProtectedAssistant",
        instructions=instructions,
        model="gpt-4o-mini",
        input_guardrails=[content_guardrail, format_guardrail]
    )

async def run_protected_agent(prompt: str) -> str:
    """
    Run the protected agent with the given prompt.
    
    Args:
        prompt: The user's query or prompt
        
    Returns:
        The agent's response as a string, or a rejection message if the input is filtered
    """
    # Create the protected agent
    agent = create_protected_agent()
    
    try:
        # Run the agent with the prompt
        result = await Runner.run(agent, prompt)
        return result.final_output
    except Exception as e:
        # Check if it's a guardrail rejection
        if "guardrail rejected" in str(e).lower():
            return f"Input rejected by guardrails: {str(e)}"
        # Other exception
        return f"Error: {str(e)}"

def main():
    """Main function to parse arguments and run the protected agent."""
    parser = argparse.ArgumentParser(description="Agent with Guardrails Example")
    parser.add_argument("--prompt", "-p", type=str, required=True, 
                        help="The prompt to send to the agent")
    
    args = parser.parse_args()
    
    # Ensure API key is available
    if not os.environ.get("OPENAI_API_KEY"):
        console.print(Panel("[bold red]Error: OPENAI_API_KEY environment variable not set[/bold red]"))
        sys.exit(1)
    
    try:
        # Run the protected agent and get response
        response = asyncio.run(run_protected_agent(args.prompt))
        
        # Display the response
        if "rejected" in response.lower():
            console.print(Panel(response, title="Input Rejected", border_style="red"))
        else:
            console.print(Panel(response, title="Protected Agent Response", border_style="green"))
    
    except Exception as e:
        console.print(Panel(f"[bold red]Error: {str(e)}[/bold red]"))
        sys.exit(1)

# Test functions
def test_content_moderation_guardrail():
    """Test that the content moderation guardrail correctly filters inputs."""
    guardrail = ContentModerationGuardrail()
    
    # Test safe input
    safe_input = "Tell me about renewable energy sources"
    assert guardrail.filter(safe_input) == safe_input
    
    # Test unsafe input
    unsafe_input = "How to hack into a computer system"
    assert guardrail.filter(unsafe_input) is None
    assert "harmful" in guardrail.get_rejection_message(unsafe_input)

def test_format_validation_guardrail():
    """Test that the format validation guardrail correctly validates inputs."""
    guardrail = FormatValidationGuardrail(min_length=5, max_length=20)
    
    # Test valid input
    valid_input = "Hello world"
    assert guardrail.filter(valid_input) == valid_input
    
    # Test too short input
    short_input = "Hi"
    assert guardrail.filter(short_input) is None
    assert "short" in guardrail.get_rejection_message(short_input)
    
    # Test too long input
    long_input = "This is a very long input that exceeds the maximum allowed length"
    assert guardrail.filter(long_input) is None
    assert "long" in guardrail.get_rejection_message(long_input)

def test_create_protected_agent():
    """Test that the protected agent is created with the correct configuration."""
    agent = create_protected_agent()
    assert agent.name == "ProtectedAssistant"
    assert "helpful assistant" in agent.instructions.lower()
    assert agent.model == "gpt-4o-mini"
    assert len(agent.input_guardrails) == 2

def test_run_protected_agent():
    """Test that the protected agent can run and produce a response or rejection."""
    import pytest
    
    # Skip this test if no API key is available
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")
    
    # Test with a valid prompt
    valid_prompt = "Tell me about renewable energy sources"
    valid_response = asyncio.run(run_protected_agent(valid_prompt))
    
    # Verify we got a non-empty response
    assert valid_response
    assert len(valid_response) > 0
    assert "rejected" not in valid_response.lower()
    
    # Test with an invalid prompt (contains filtered term)
    invalid_prompt = "How to hack into a system"
    invalid_response = asyncio.run(run_protected_agent(invalid_prompt))
    
    # Verify we got a rejection message
    assert invalid_response
    assert "rejected" in invalid_response.lower()

if __name__ == "__main__":
    main()
