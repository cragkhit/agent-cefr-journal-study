#!/usr/bin/env -S uv run --script

# /// script
# dependencies = [
#   "openai-agents>=0.0.2",
#   "pytest>=7.4.0",
#   "rich>=13.7.0",
#   "requests>=2.31.0",
# ]
# ///

"""
Agent with Function Tools Example

This example demonstrates how to create an agent with function tools using the @function_tool decorator.
The agent can use these tools to perform actions like fetching weather data or calculating distances.

Run with:
    uv run 05_agent_with_function_tools.py --prompt "What's the weather in New York?"

Test with:
    uv run pytest 05_agent_with_function_tools.py
"""

import os
import sys
import argparse
import json
import asyncio
import requests
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from rich.console import Console
from rich.panel import Panel

from openai import OpenAI
from agents import Agent, Runner, function_tool

# Initialize console for rich output
console = Console()

# Define function tools using the decorator
@function_tool
def get_current_weather(location: str, unit: str) -> str:
    """
    Get the current weather in a given location.
    
    Args:
        location: The city and state, e.g. San Francisco, CA or country e.g., London, UK
        unit: The temperature unit to use. Either "celsius" or "fahrenheit".
        
    Returns:
        A string containing the weather information.
    """
    # This is a mock implementation - in a real application, you would call a weather API
    weather_data = {
        "New York": {"temperature": 22, "condition": "Sunny"},
        "London": {"temperature": 15, "condition": "Cloudy"},
        "Tokyo": {"temperature": 28, "condition": "Rainy"},
        "Sydney": {"temperature": 31, "condition": "Hot and sunny"},
    }
    
    # Default weather if location not found
    default_weather = {"temperature": 20, "condition": "Clear"}
    
    # Get weather for the location (case insensitive)
    location_key = next((k for k in weather_data.keys() if k.lower() == location.lower()), None)
    weather = weather_data.get(location_key, default_weather)
    
    # Convert temperature if needed
    temp = weather["temperature"]
    if unit.lower() == "fahrenheit":
        temp = (temp * 9/5) + 32
    
    return f"The current weather in {location} is {weather['condition']} with a temperature of {temp}°{'F' if unit.lower() == 'fahrenheit' else 'C'}."

@function_tool
def calculate_distance(origin: str, destination: str, unit: str) -> str:
    """
    Calculate the distance between two locations.
    
    Args:
        origin: The starting location (city name)
        destination: The ending location (city name)
        unit: The unit of distance. Either "kilometers" or "miles".
        
    Returns:
        A string containing the distance information.
    """
    # This is a mock implementation - in a real application, you would call a mapping API
    distances = {
        ("New York", "London"): 5567,
        ("New York", "Tokyo"): 10838,
        ("London", "Tokyo"): 9562,
        ("London", "Sydney"): 16983,
        ("Tokyo", "Sydney"): 7921,
    }
    
    # Try to find the distance in both directions
    distance_km = distances.get((origin, destination)) or distances.get((destination, origin))
    
    # If not found, provide an estimate
    if distance_km is None:
        distance_km = 1000  # Default distance
    
    # Convert to miles if needed
    if unit.lower() == "miles":
        distance = distance_km * 0.621371
        unit_symbol = "miles"
    else:
        distance = distance_km
        unit_symbol = "km"
    
    return f"The distance between {origin} and {destination} is approximately {distance:.1f} {unit_symbol}."

@function_tool
def get_current_time(location: str) -> str:
    """
    Get the current time in a given location.
    
    Args:
        location: The location to get the time for. Currently only supports "UTC".
        
    Returns:
        A string containing the current time information.
    """
    # In a real implementation, you would use a timezone library
    current_time = datetime.utcnow()
    formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
    
    return f"The current time in {location} is {formatted_time}."

def create_travel_assistant() -> Agent:
    """
    Create a travel assistant agent with function tools.
    
    Returns:
        An Agent instance with function tools for travel assistance.
    """
    instructions = """
    You are a helpful travel assistant that can provide information about weather, 
    distances between locations, and current time.
    Use the tools available to you to provide accurate information when asked.
    If you don't have a tool for the specific request, acknowledge the limitations
    and provide the best information you can.
    """
    
    # Create the agent with function tools
    return Agent(
        name="TravelAssistant",
        instructions=instructions,
        model="gpt-4o-mini",
        tools=[get_current_weather, calculate_distance, get_current_time]
    )

async def run_function_tool_agent(prompt: str) -> str:
    """
    Run the travel assistant agent with the given prompt.
    
    Args:
        prompt: The user's query or prompt
        
    Returns:
        The agent's response as a string
    """
    # Create the agent with function tools
    agent = create_travel_assistant()
    
    # Run the agent with the prompt
    result = await Runner.run(agent, prompt)
    
    # Return the response
    return result.final_output

def main():
    """Main function to parse arguments and run the agent with function tools."""
    parser = argparse.ArgumentParser(description="Agent with Function Tools Example")
    parser.add_argument("--prompt", "-p", type=str, required=True, 
                        help="The prompt to send to the agent")
    
    args = parser.parse_args()
    
    # Ensure API key is available
    if not os.environ.get("OPENAI_API_KEY"):
        console.print(Panel("[bold red]Error: OPENAI_API_KEY environment variable not set[/bold red]"))
        sys.exit(1)
    
    try:
        # Run the agent and get response
        response = asyncio.run(run_function_tool_agent(args.prompt))
        
        # Display the response
        console.print(Panel(response, title="Travel Assistant Response", border_style="green"))
    
    except Exception as e:
        console.print(Panel(f"[bold red]Error: {str(e)}[/bold red]"))
        sys.exit(1)

# Test functions
def test_function_tools():
    """Test that the function tools work correctly."""
    # Test weather function
    weather_result = get_current_weather("New York", "celsius")
    assert "New York" in weather_result
    assert "°C" in weather_result
    
    # Test distance function
    distance_result = calculate_distance("New York", "London", "kilometers")
    assert "New York" in distance_result
    assert "London" in distance_result
    assert "km" in distance_result
    
    # Test time function
    time_result = get_current_time()
    assert "UTC" in time_result
    assert ":" in time_result  # Time should contain colons

def test_create_travel_assistant():
    """Test that the travel assistant agent is created with the correct configuration."""
    agent = create_travel_assistant()
    assert agent.name == "TravelAssistant"
    assert "travel assistant" in agent.instructions.lower()
    assert len(agent.tools) == 3

def test_run_function_tool_agent():
    """Test that the agent can use function tools and produce a response."""
    import pytest
    
    # Skip this test if no API key is available
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")
    
    # Run a test query that should use the weather tool
    response = asyncio.run(run_function_tool_agent("What's the weather in London?"))
    
    # Verify we got a non-empty response that mentions London
    assert response
    assert len(response) > 0
    assert "London" in response

if __name__ == "__main__":
    main()
