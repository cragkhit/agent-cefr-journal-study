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
Agent with Custom Tools Example

This example demonstrates how to create an agent with custom tools without using the @function_tool decorator.
It shows how to define custom tool schemas and implement tool handlers manually.

Run with:
    uv run 06_agent_with_custom_tools.py --prompt "Convert 100 USD to EUR"

Test with:
    uv run pytest 06_agent_with_custom_tools.py
"""

import os
import sys
import argparse
import json
import asyncio
from typing import Optional, List, Dict, Any, Union, Callable
from rich.console import Console
from rich.panel import Panel
from pydantic import BaseModel, Field

from openai import OpenAI
from agents import Agent, Runner, Tool

# Initialize console for rich output
console = Console()

# Define custom tool input models
class CurrencyConversionInput(BaseModel):
    """Input for currency conversion tool."""
    amount: float = Field(..., description="The amount to convert")
    from_currency: str = Field(..., description="The currency to convert from (e.g., USD, EUR, JPY)")
    to_currency: str = Field(..., description="The currency to convert to (e.g., USD, EUR, JPY)")

class StockPriceInput(BaseModel):
    """Input for stock price tool."""
    symbol: str = Field(..., description="The stock symbol (e.g., AAPL, MSFT, GOOGL)")

# Define custom tool handlers
def convert_currency(params: CurrencyConversionInput) -> str:
    """
    Convert an amount from one currency to another.
    
    Args:
        params: The currency conversion parameters
        
    Returns:
        A string containing the conversion result
    """
    # This is a mock implementation - in a real application, you would call a currency API
    exchange_rates = {
        "USD": {"EUR": 0.92, "GBP": 0.79, "JPY": 149.50},
        "EUR": {"USD": 1.09, "GBP": 0.86, "JPY": 162.50},
        "GBP": {"USD": 1.27, "EUR": 1.16, "JPY": 189.20},
        "JPY": {"USD": 0.0067, "EUR": 0.0062, "GBP": 0.0053},
    }
    
    from_curr = params.from_currency.upper()
    to_curr = params.to_currency.upper()
    
    # Check if currencies are supported
    if from_curr not in exchange_rates:
        return f"Sorry, {from_curr} is not a supported currency."
    
    if to_curr not in exchange_rates[from_curr] and from_curr != to_curr:
        return f"Sorry, conversion from {from_curr} to {to_curr} is not supported."
    
    # If same currency, return the amount
    if from_curr == to_curr:
        return f"{params.amount} {from_curr} is equal to {params.amount} {to_curr}."
    
    # Calculate converted amount
    converted_amount = params.amount * exchange_rates[from_curr][to_curr]
    
    return f"{params.amount} {from_curr} is equal to {converted_amount:.2f} {to_curr}."

def get_stock_price(params: StockPriceInput) -> str:
    """
    Get the current price of a stock.
    
    Args:
        params: The stock price parameters
        
    Returns:
        A string containing the stock price information
    """
    # This is a mock implementation - in a real application, you would call a stock API
    stock_prices = {
        "AAPL": 175.34,
        "MSFT": 410.34,
        "GOOGL": 147.68,
        "AMZN": 178.75,
        "META": 474.99,
    }
    
    symbol = params.symbol.upper()
    
    # Check if stock is supported
    if symbol not in stock_prices:
        return f"Sorry, stock information for {symbol} is not available."
    
    price = stock_prices[symbol]
    
    return f"The current price of {symbol} is ${price:.2f}."

def create_financial_assistant() -> Agent:
    """
    Create a financial assistant agent with custom tools.
    
    Returns:
        An Agent instance with custom tools for financial assistance
    """
    instructions = """
    You are a helpful financial assistant that can provide information about 
    currency conversions and stock prices.
    Use the tools available to you to provide accurate financial information when asked.
    If you don't have a tool for the specific request, acknowledge the limitations
    and provide the best information you can.
    """
    
    # Create custom tools
    currency_tool = Tool(
        name="convert_currency",
        description="Convert an amount from one currency to another",
        input_type=CurrencyConversionInput,
        function=convert_currency
    )
    
    stock_tool = Tool(
        name="get_stock_price",
        description="Get the current price of a stock",
        input_type=StockPriceInput,
        function=get_stock_price
    )
    
    # Create the agent with custom tools
    return Agent(
        name="FinancialAssistant",
        instructions=instructions,
        model="gpt-4o-mini",
        tools=[currency_tool, stock_tool]
    )

async def run_custom_tool_agent(prompt: str) -> str:
    """
    Run the financial assistant agent with the given prompt.
    
    Args:
        prompt: The user's query or prompt
        
    Returns:
        The agent's response as a string
    """
    # Create the agent with custom tools
    agent = create_financial_assistant()
    
    # Run the agent with the prompt
    result = await Runner.run(agent, prompt)
    
    # Return the response
    return result.final_output

def main():
    """Main function to parse arguments and run the agent with custom tools."""
    parser = argparse.ArgumentParser(description="Agent with Custom Tools Example")
    parser.add_argument("--prompt", "-p", type=str, required=True, 
                        help="The prompt to send to the agent")
    
    args = parser.parse_args()
    
    # Ensure API key is available
    if not os.environ.get("OPENAI_API_KEY"):
        console.print(Panel("[bold red]Error: OPENAI_API_KEY environment variable not set[/bold red]"))
        sys.exit(1)
    
    try:
        # Run the agent and get response
        response = asyncio.run(run_custom_tool_agent(args.prompt))
        
        # Display the response
        console.print(Panel(response, title="Financial Assistant Response", border_style="green"))
    
    except Exception as e:
        console.print(Panel(f"[bold red]Error: {str(e)}[/bold red]"))
        sys.exit(1)

# Test functions
def test_custom_tools():
    """Test that the custom tools work correctly."""
    # Test currency conversion
    currency_result = convert_currency(CurrencyConversionInput(
        amount=100,
        from_currency="USD",
        to_currency="EUR"
    ))
    assert "USD" in currency_result
    assert "EUR" in currency_result
    
    # Test stock price
    stock_result = get_stock_price(StockPriceInput(symbol="AAPL"))
    assert "AAPL" in stock_result
    assert "$" in stock_result

def test_create_financial_assistant():
    """Test that the financial assistant agent is created with the correct configuration."""
    agent = create_financial_assistant()
    assert agent.name == "FinancialAssistant"
    assert "financial assistant" in agent.instructions.lower()
    assert len(agent.tools) == 2
    assert any(tool.name == "convert_currency" for tool in agent.tools)
    assert any(tool.name == "get_stock_price" for tool in agent.tools)

def test_run_custom_tool_agent():
    """Test that the agent can use custom tools and produce a response."""
    import pytest
    
    # Skip this test if no API key is available
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")
    
    # Run a test query that should use the currency conversion tool
    response = asyncio.run(run_custom_tool_agent("Convert 50 USD to EUR"))
    
    # Verify we got a non-empty response that mentions the currencies
    assert response
    assert len(response) > 0
    assert "USD" in response
    assert "EUR" in response

if __name__ == "__main__":
    main()
