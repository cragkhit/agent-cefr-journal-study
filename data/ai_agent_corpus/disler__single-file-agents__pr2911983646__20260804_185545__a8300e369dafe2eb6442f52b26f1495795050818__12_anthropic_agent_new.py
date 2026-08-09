#!/usr/bin/env -S uv run --script

# /// script
# dependencies = [
#   "openai-agents>=0.0.2",
#   "anthropic>=0.45.2",
#   "pytest>=7.4.0",
#   "rich>=13.7.0",
# ]
# ///

"""
Anthropic Agent Example

This example demonstrates how to use the OpenAI Agents SDK with Anthropic's Claude model.
It shows how to create a custom model provider that works with Anthropic's API.

Run with:
    uv run 12_anthropic_agent.py --prompt "Explain the concept of quantum entanglement"

Test with:
    uv run pytest 12_anthropic_agent.py
"""

import os
import sys
import argparse
import json
import asyncio
from typing import Optional, List, Dict, Any, Union, Callable
from rich.console import Console
from rich.panel import Panel

import anthropic
from openai import OpenAI
from agents import Agent, Runner
from openai_agents.providers import ModelProvider, ModelResponse
from openai.types.chat import ChatCompletion, ChatCompletionMessage

# Initialize console for rich output
console = Console()

class AnthropicModelProvider(ModelProvider):
    """
    Custom model provider for Anthropic's Claude model.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Anthropic model provider.
        
        Args:
            api_key: Anthropic API key. If None, will use the ANTHROPIC_API_KEY environment variable.
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key is required")
        
        self.client = anthropic.Anthropic(api_key=self.api_key)
    
    async def generate(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs
    ) -> ModelResponse:
        """
        Generate a response using Anthropic's Claude model.
        
        Args:
            messages: List of messages in the conversation
            model: Model name (will be mapped to Anthropic model)
            temperature: Sampling temperature
            max_tokens: Maximum number of tokens to generate
            **kwargs: Additional arguments to pass to the model
            
        Returns:
            A ModelResponse containing the model's response
        """
        # Map OpenAI model names to Anthropic model names
        model_mapping = {
            "gpt-4o-mini": "claude-3-haiku-20240307",
            "gpt-4o": "claude-3-opus-20240229",
            "gpt-3.5-turbo": "claude-3-sonnet-20240229",
        }
        
        # Use the mapped model or default to claude-3-haiku
        anthropic_model = model_mapping.get(model, "claude-3-haiku-20240307")
        
        # Convert OpenAI message format to Anthropic message format
        anthropic_messages = []
        for message in messages:
            role = message["role"]
            # Map OpenAI roles to Anthropic roles
            if role == "system":
                # System messages are handled differently in Anthropic
                system_content = message.get("content", "")
                continue
            elif role == "user":
                anthropic_role = "user"
            elif role == "assistant":
                anthropic_role = "assistant"
            else:
                # Skip unsupported roles
                continue
            
            # Add the message
            anthropic_messages.append({
                "role": anthropic_role,
                "content": message.get("content", "")
            })
        
        # Create the message with system prompt if available
        try:
            response = await self.client.messages.create(
                model=anthropic_model,
                messages=anthropic_messages,
                system=system_content if 'system_content' in locals() else "",
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            # Convert Anthropic response to OpenAI format
            output_message = {
                "role": "assistant",
                "content": response.content[0].text
            }
            
            # Create a ModelResponse
            return ModelResponse(
                output=[output_message],
                usage={
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                },
                referenceable_id=None
            )
        
        except Exception as e:
            raise Exception(f"Error generating response from Anthropic: {str(e)}")

def create_anthropic_agent() -> Agent:
    """
    Create an agent that uses Anthropic's Claude model.
    
    Returns:
        An Agent instance that uses Anthropic's Claude model.
    """
    instructions = """
    You are a helpful assistant powered by Anthropic's Claude model.
    You provide accurate, thoughtful responses to user queries.
    You excel at explaining complex concepts in clear, accessible language.
    When appropriate, you break down information into easy-to-understand parts.
    You acknowledge when you don't know something rather than making up information.
    """
    
    # Create the Anthropic model provider
    provider = AnthropicModelProvider()
    
    # Create the agent with the Anthropic provider
    return Agent(
        name="ClaudeAssistant",
        instructions=instructions,
        model="gpt-4o-mini",  # This will be mapped to claude-3-haiku
        model_provider=provider
    )

async def run_anthropic_agent(prompt: str) -> str:
    """
    Run the Anthropic agent with the given prompt.
    
    Args:
        prompt: The user's query or prompt
        
    Returns:
        The agent's response as a string
    """
    # Create the Anthropic agent
    agent = create_anthropic_agent()
    
    # Run the agent with the prompt
    result = await Runner.run(agent, prompt)
    
    # Return the response
    return result.final_output

def main():
    """Main function to parse arguments and run the Anthropic agent."""
    parser = argparse.ArgumentParser(description="Anthropic Agent Example")
    parser.add_argument("--prompt", "-p", type=str, required=True, 
                        help="The prompt to send to the agent")
    
    args = parser.parse_args()
    
    # Ensure API key is available
    if not os.environ.get("ANTHROPIC_API_KEY"):
        console.print(Panel("[bold red]Error: ANTHROPIC_API_KEY environment variable not set[/bold red]"))
        sys.exit(1)
    
    try:
        # Run the Anthropic agent and get response
        response = asyncio.run(run_anthropic_agent(args.prompt))
        
        # Display the response
        console.print(Panel(response, title="Claude Response", border_style="green"))
    
    except Exception as e:
        console.print(Panel(f"[bold red]Error: {str(e)}[/bold red]"))
        sys.exit(1)

# Test functions
def test_create_anthropic_agent():
    """Test that the Anthropic agent is created with the correct configuration."""
    import pytest
    
    # Skip this test if no API key is available
    if not os.environ.get("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")
    
    agent = create_anthropic_agent()
    assert agent.name == "ClaudeAssistant"
    assert "claude" in agent.instructions.lower()
    assert isinstance(agent.model_provider, AnthropicModelProvider)

def test_run_anthropic_agent():
    """Test that the Anthropic agent can run and produce a response."""
    import pytest
    
    # Skip this test if no API key is available
    if not os.environ.get("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")
    
    # Run a simple test query
    response = asyncio.run(run_anthropic_agent("What is 2+2?"))
    
    # Verify we got a non-empty response
    assert response
    assert len(response) > 0
    # The response should contain "4" somewhere
    assert "4" in response

if __name__ == "__main__":
    main()
