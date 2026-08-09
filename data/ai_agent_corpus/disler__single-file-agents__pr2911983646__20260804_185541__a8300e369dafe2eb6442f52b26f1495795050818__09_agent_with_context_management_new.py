#!/usr/bin/env -S uv run --script

# /// script
# dependencies = [
#   "openai-agents>=0.0.2",
#   "pytest>=7.4.0",
#   "rich>=13.7.0",
# ]
# ///

"""
Agent with Context Management Example

This example demonstrates how to use context management with agents to maintain state
across multiple interactions. It shows how to create a conversation agent that remembers
previous interactions.

Run with:
    uv run 09_agent_with_context_management.py --prompt "Tell me about Mars"

Test with:
    uv run pytest 09_agent_with_context_management.py
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
from agents import Agent, Runner, Context

# Initialize console for rich output
console = Console()

def create_conversation_agent() -> Agent:
    """
    Create a conversation agent that can maintain context.
    
    Returns:
        An Agent instance that maintains conversation context.
    """
    instructions = """
    You are a helpful conversational assistant that maintains context across interactions.
    Remember details from previous parts of the conversation and refer back to them when relevant.
    Be friendly, informative, and engaging in your responses.
    If the user asks about something you discussed earlier, acknowledge that and build upon it.
    """
    
    return Agent(
        name="ConversationAssistant",
        instructions=instructions,
        model="gpt-4o-mini",
    )

async def run_conversation_with_context(prompt: str, context: Optional[Context] = None) -> tuple[str, Context]:
    """
    Run a conversation agent with context management.
    
    Args:
        prompt: The user's query or prompt
        context: Optional existing context from previous interactions
        
    Returns:
        A tuple containing the agent's response and the updated context
    """
    # Create the conversation agent
    agent = create_conversation_agent()
    
    # Create a new context if none is provided
    if context is None:
        context = Context()
    
    # Run the agent with the prompt and context
    result = await Runner.run(agent, prompt, context=context)
    
    # Return the response and updated context
    return result.final_output, result.context

def simulate_conversation(initial_prompt: str, follow_up_prompts: List[str]) -> List[str]:
    """
    Simulate a multi-turn conversation with context management.
    
    Args:
        initial_prompt: The first user prompt
        follow_up_prompts: List of follow-up prompts
        
    Returns:
        List of agent responses
    """
    responses = []
    context = None
    
    # Run the initial prompt
    response, context = asyncio.run(run_conversation_with_context(initial_prompt, context))
    responses.append(result.final_output)
    
    # Run each follow-up prompt with the updated context
    for prompt in follow_up_prompts:
        response, context = asyncio.run(run_conversation_with_context(prompt, context))
        responses.append(result.final_output)
    
    return responses

def main():
    """Main function to parse arguments and run the conversation agent."""
    parser = argparse.ArgumentParser(description="Agent with Context Management Example")
    parser.add_argument("--prompt", "-p", type=str, required=True, 
                        help="The prompt to send to the agent")
    parser.add_argument("--follow-up", "-f", type=str, nargs="*", default=[],
                        help="Optional follow-up prompts to simulate a conversation")
    
    args = parser.parse_args()
    
    # Ensure API key is available
    if not os.environ.get("OPENAI_API_KEY"):
        console.print(Panel("[bold red]Error: OPENAI_API_KEY environment variable not set[/bold red]"))
        sys.exit(1)
    
    try:
        # Simulate a conversation with the provided prompts
        responses = simulate_conversation(args.prompt, args.follow_up)
        
        # Display the initial response
        console.print(Panel(responses[0], title=f"Response to: {args.prompt}", border_style="green"))
        
        # Display follow-up responses if any
        for i, response in enumerate(responses[1:]):
            console.print(Panel(response, title=f"Response to: {args.follow_up[i]}", border_style="blue"))
    
    except Exception as e:
        console.print(Panel(f"[bold red]Error: {str(e)}[/bold red]"))
        sys.exit(1)

# Test functions
def test_create_conversation_agent():
    """Test that the conversation agent is created with the correct configuration."""
    agent = create_conversation_agent()
    assert agent.name == "ConversationAssistant"
    assert "conversational assistant" in agent.instructions.lower()
    assert agent.model == "gpt-4o-mini"

def test_run_conversation_with_context():
    """Test that the agent can maintain context across interactions."""
    import pytest
    
    # Skip this test if no API key is available
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")
    
    # Run an initial query
    initial_prompt = "Tell me about Mars"
    response, context = asyncio.run(run_conversation_with_context(initial_prompt))
    
    # Verify we got a non-empty response
    assert response
    assert len(response) > 0
    assert context is not None
    
    # Run a follow-up query that references the previous conversation
    follow_up_prompt = "How long would it take to travel there?"
    follow_up_response, _ = asyncio.run(run_conversation_with_context(follow_up_prompt, context))
    
    # Verify the follow-up response acknowledges the previous context
    assert follow_up_response
    assert len(follow_up_response) > 0
    # The response should contain terms related to Mars travel
    assert any(term in follow_up_response.lower() for term in ["mars", "travel", "journey", "months"])

if __name__ == "__main__":
    main()
