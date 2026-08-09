#!/usr/bin/env -S uv run --script

# /// script
# dependencies = [
#   "openai-agents>=0.0.2",
#   "pytest>=7.4.0",
#   "rich>=13.7.0",
# ]
# ///

"""
Agent with Handoffs Example

This example demonstrates how to create agents that can hand off tasks to other specialized agents.
It shows how to implement a customer support system with a triage agent and specialist agents.

Run with:
    uv run 07_agent_with_handoffs.py --prompt "I need help with my billing"

Test with:
    uv run pytest 07_agent_with_handoffs.py
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
from agents import Agent, Runner, handoff

# Initialize console for rich output
console = Console()

def create_billing_agent() -> Agent:
    """
    Create a billing specialist agent.
    
    Returns:
        An Agent instance specialized in billing issues.
    """
    instructions = """
    You are a billing specialist who can help customers with billing-related issues.
    You can assist with questions about invoices, payment methods, refunds, and subscription plans.
    Be helpful, clear, and concise in your responses.
    Always verify the customer's information before providing specific account details.
    """
    
    return Agent(
        name="BillingSpecialist",
        instructions=instructions,
        model="gpt-4o-mini",
        handoff_description="Use this agent for questions about billing, payments, invoices, or subscription issues."
    )

def create_technical_agent() -> Agent:
    """
    Create a technical support agent.
    
    Returns:
        An Agent instance specialized in technical support.
    """
    instructions = """
    You are a technical support specialist who can help customers with technical issues.
    You can assist with questions about software functionality, bugs, error messages, and how-to guides.
    Provide clear step-by-step instructions when explaining technical procedures.
    Ask clarifying questions if the customer's issue is not clear.
    """
    
    return Agent(
        name="TechnicalSupport",
        instructions=instructions,
        model="gpt-4o-mini",
        handoff_description="Use this agent for technical issues, bugs, error messages, or how-to questions."
    )

def create_account_agent() -> Agent:
    """
    Create an account management agent.
    
    Returns:
        An Agent instance specialized in account management.
    """
    instructions = """
    You are an account management specialist who can help customers with account-related issues.
    You can assist with questions about account creation, profile updates, security settings, and account recovery.
    Always prioritize account security and verify the customer's identity before making changes.
    Provide clear guidance on how customers can manage their account settings.
    """
    
    return Agent(
        name="AccountManager",
        instructions=instructions,
        model="gpt-4o-mini",
        handoff_description="Use this agent for account management, profile updates, or security questions."
    )

def create_triage_agent(specialists: List[Agent]) -> Agent:
    """
    Create a triage agent that can delegate to specialist agents.
    
    Args:
        specialists: List of specialist agents to which tasks can be delegated
        
    Returns:
        An Agent instance that triages customer inquiries
    """
    instructions = """
    You are a customer support triage agent. Your job is to:
    1. Understand the customer's issue
    2. Determine which specialist would be best suited to help
    3. Hand off the conversation to that specialist
    
    Be polite and professional. If you're unsure which specialist to choose, ask clarifying questions.
    """
    
    # Create handoffs to specialist agents
    handoffs = [handoff(agent) for agent in specialists]
    
    return Agent(
        name="TriageAgent",
        instructions=instructions,
        model="gpt-4o-mini",
        handoffs=handoffs
    )

async def run_customer_support_system(prompt: str) -> str:
    """
    Run the customer support system with the given prompt.
    
    Args:
        prompt: The customer's inquiry
        
    Returns:
        The final response from the appropriate specialist agent
    """
    # Create specialist agents
    billing_agent = create_billing_agent()
    technical_agent = create_technical_agent()
    account_agent = create_account_agent()
    
    # Create triage agent with specialists
    triage_agent = create_triage_agent([billing_agent, technical_agent, account_agent])
    
    # Run the triage agent with the prompt
    result = await Runner.run(triage_agent, prompt)
    
    # Return the final response
    return result.final_output

def main():
    """Main function to parse arguments and run the customer support system."""
    parser = argparse.ArgumentParser(description="Agent with Handoffs Example")
    parser.add_argument("--prompt", "-p", type=str, required=True, 
                        help="The customer inquiry to send to the support system")
    
    args = parser.parse_args()
    
    # Ensure API key is available
    if not os.environ.get("OPENAI_API_KEY"):
        console.print(Panel("[bold red]Error: OPENAI_API_KEY environment variable not set[/bold red]"))
        sys.exit(1)
    
    try:
        # Run the customer support system and get response
        response = asyncio.run(run_customer_support_system(args.prompt))
        
        # Display the response
        console.print(Panel(response, title="Customer Support Response", border_style="green"))
    
    except Exception as e:
        console.print(Panel(f"[bold red]Error: {str(e)}[/bold red]"))
        sys.exit(1)

# Test functions
def test_create_specialist_agents():
    """Test that specialist agents are created with the correct configuration."""
    billing_agent = create_billing_agent()
    technical_agent = create_technical_agent()
    account_agent = create_account_agent()
    
    assert billing_agent.name == "BillingSpecialist"
    assert technical_agent.name == "TechnicalSupport"
    assert account_agent.name == "AccountManager"
    
    assert "billing specialist" in billing_agent.instructions.lower()
    assert "technical support" in technical_agent.instructions.lower()
    assert "account management" in account_agent.instructions.lower()

def test_create_triage_agent():
    """Test that the triage agent is created with the correct configuration."""
    billing_agent = create_billing_agent()
    technical_agent = create_technical_agent()
    account_agent = create_account_agent()
    
    triage_agent = create_triage_agent([billing_agent, technical_agent, account_agent])
    
    assert triage_agent.name == "TriageAgent"
    assert "triage agent" in triage_agent.instructions.lower()
    assert len(triage_agent.handoffs) == 3

def test_run_customer_support_system():
    """Test that the customer support system can run and produce a response."""
    import pytest
    
    # Skip this test if no API key is available
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")
    
    # Run a test query that should go to the billing specialist
    response = asyncio.run(run_customer_support_system("I have a question about my recent invoice"))
    
    # Verify we got a non-empty response
    assert response
    assert len(response) > 0

if __name__ == "__main__":
    main()
