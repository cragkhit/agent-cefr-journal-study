# /// script
# dependencies = [
#   "anthropic>=0.47.1",
#   "rich>=13.7.0",
#   "pydantic>=2.0.0",
#   "polars>=1.22.0",
# ]
# ///

"""
    Example Usage:
        uv run sfa_polars_csv_agent_anthropic_v3.py -i "data/analytics.csv" -p "What is the average age of the users?"
"""

import io
import os
import sys
import json
import argparse
import tempfile
import subprocess
import time
from typing import List, Optional, Dict, Any
from rich.console import Console
from rich.panel import Panel
import anthropic
from anthropic import Anthropic
import polars as pl
from pydantic import BaseModel, Field, ValidationError

# Initialize rich console
console = Console()

# Tool functions
def list_columns(reasoning: str, csv_path: str) -> List[str]:
    """Returns a list of columns in the CSV file.

    The agent uses this to discover available columns and make informed decisions.
    This is typically the first tool called to understand the data structure.

    Args:
        reasoning: Explanation of why we're listing columns relative to user request
        csv_path: Path to the CSV file

    Returns:
        List of column names as strings

    Example:
        columns = list_columns("Need to find age-related columns", "data.csv")
        # Returns: ['user_id', 'age', 'name', ...]
    """
    try:
        df = pl.scan_csv(csv_path).collect()
        columns = df.columns
        console.log(f"[blue]List Columns Tool[/blue] - Reasoning: {reasoning}")
        console.log(f"[dim]Columns: {columns}[/dim]")
        return columns
    except Exception as e:
        console.log(f"[red]Error listing columns: {str(e)}[/red]")
        return []


def sample_csv(reasoning: str, csv_path: str, row_count: int) -> str:
    """Returns a sample of rows from the CSV file.

    The agent uses this to understand actual data content and patterns.
    This helps validate data types and identify any potential data quality issues.

    Args:
        reasoning: Explanation of why we're sampling this data
        csv_path: Path to the CSV file
        row_count: Number of rows to sample (aim for 3-5 rows)

    Returns:
        String containing sample rows in readable format

    Example:
        sample = sample_csv("Check age values and formats", "data.csv", 3)
        # Returns formatted string with 3 rows of data
    """
    try:
        df = pl.scan_csv(csv_path).limit(row_count).collect()
        # Convert to string representation
        output = df.select(pl.all()).write_csv(None)
        console.log(
            f"[blue]Sample CSV Tool[/blue] - Rows: {row_count} - Reasoning: {reasoning}"
        )
        console.log(f"[dim]Sample:\n{output}[/dim]")
        return output
    except Exception as e:
        console.log(f"[red]Error sampling CSV: {str(e)}[/red]")
        return ""


def run_test_polars_code(reasoning: str, polars_python_code: str, csv_path: str) -> str:
    """Executes test Polars Python code and returns results.

    The agent uses this to validate code before finalizing it.
    Results are only shown to the agent, not the user.
    The code should use Polars' lazy evaluation (LazyFrame) for better performance.

    Args:
        reasoning: Explanation of why we're running this test code
        polars_python_code: The Polars Python code to test. Should use pl.scan_csv() for lazy evaluation.
        csv_path: Path to the CSV file

    Returns:
        Code execution results as a string
    """
    try:
        # Create a unique filename based on timestamp
        timestamp = int(time.time())
        filename = f"test_polars_{timestamp}.py"

        # Write code to a real file
        with open(filename, "w") as f:
            f.write(polars_python_code)

        # Execute the code
        result = subprocess.run(
            ["uv", "run", "--with", "polars", filename],
            text=True,
            capture_output=True,
        )
        output = result.stdout + result.stderr

        # Clean up the file
        os.remove(filename)

        console.log(f"[blue]Test Code Tool[/blue] - Reasoning: {reasoning}")
        console.log(f"[dim]Code:\n{polars_python_code}[/dim]")
        return output
    except Exception as e:
        console.log(f"[red]Error running test code: {str(e)}[/red]")
        return str(e)


def run_final_polars_code(
    reasoning: str,
    polars_python_code: str,
    csv_path: str,
    output_file: Optional[str] = None,
) -> str:
    """Executes the final Polars code and returns results to user.

    This is the last tool call the agent should make after validating the code.
    The code should be fully tested and ready for production use.
    Results will be displayed to the user and optionally saved to a file.

    Args:
        reasoning: Final explanation of how this code satisfies user request
        polars_python_code: The validated Polars Python code to run. Should use pl.scan_csv() for lazy evaluation.
        csv_path: Path to the CSV file
        output_file: Optional path to save results to

    Returns:
        Code execution results as a string
    """
    try:
        # Create a unique filename based on timestamp
        timestamp = int(time.time())
        filename = f"polars_code_{timestamp}.py"

        # Write code to a real file
        with open(filename, "w") as f:
            f.write(polars_python_code)

        # Execute the code
        result = subprocess.run(
            ["uv", "run", "--with", "polars", filename],
            text=True,
            capture_output=True,
        )
        output = result.stdout + result.stderr

        # Clean up the file
        os.remove(filename)

        console.log(Panel(f"[green]Final Code Tool[/green]\nReasoning: {reasoning}\n"))
        console.log(f"[dim]Code:\n{polars_python_code}[/dim]")
        return output
    except Exception as e:
        console.log(f"[red]Error running final code: {str(e)}[/red]")
        return str(e)


# Define tool schemas for Anthropic
TOOLS = [
    {
        "name": "list_columns",
        "description": "Returns list of available columns in the CSV file",
        "input_schema": {
            "type": "object",
            "properties": {
                "reasoning": {
                    "type": "string",
                    "description": "Why we need to list columns relative to user request",
                },
                "csv_path": {
                    "type": "string",
                    "description": "Path to the CSV file",
                },
            },
            "required": ["reasoning", "csv_path"],
        },
    },
    {
        "name": "sample_csv",
        "description": "Returns sample rows from the CSV file",
        "input_schema": {
            "type": "object",
            "properties": {
                "reasoning": {
                    "type": "string",
                    "description": "Why we need to sample this data",
                },
                "csv_path": {
                    "type": "string",
                    "description": "Path to the CSV file",
                },
                "row_count": {
                    "type": "integer",
                    "description": "Number of rows to sample aim for 3-5 rows",
                },
            },
            "required": ["reasoning", "csv_path", "row_count"],
        },
    },
    {
        "name": "run_test_polars_code",
        "description": "Tests Polars Python code and returns results (only visible to agent)",
        "input_schema": {
            "type": "object",
            "properties": {
                "reasoning": {
                    "type": "string",
                    "description": "Why we're testing this specific code",
                },
                "polars_python_code": {
                    "type": "string",
                    "description": "The Complete Polars Python code to test",
                },
                "csv_path": {
                    "type": "string",
                    "description": "Path to the CSV file",
                },
            },
            "required": ["reasoning", "polars_python_code", "csv_path"],
        },
    },
    {
        "name": "run_final_polars_code",
        "description": "Runs the final validated Polars code and shows results to user",
        "input_schema": {
            "type": "object",
            "properties": {
                "reasoning": {
                    "type": "string",
                    "description": "Final explanation of how code satisfies user request",
                },
                "polars_python_code": {
                    "type": "string",
                    "description": "The complete validated Polars Python code to run",
                },
                "csv_path": {
                    "type": "string",
                    "description": "Path to the CSV file",
                },
                "output_file": {
                    "type": "string",
                    "description": "Optional path to save results to",
                },
            },
            "required": ["reasoning", "polars_python_code", "csv_path"],
        },
    },
]

AGENT_PROMPT = """
You are a world-class expert at crafting precise Polars data transformations in Python.
Your goal is to generate accurate code that exactly matches the user's data analysis needs.

Use the provided tools to explore the CSV data and construct the perfect Polars transformation:
1. Start by listing columns to understand what's available in the CSV.
2. Sample the CSV to see actual data patterns.
3. Test Polars code with run_test_polars_code before finalizing it. Run the run_test_polars_code tool as many times as needed to get the code working.
4. Only call run_final_polars_code when you're confident the code is perfect.

If you find your run_test_polars_code tool call returns an error or won't satisfy the user request, try to fix the code or try a different approach.
Think step by step about what information you need.

Be sure to specify every parameter for each tool call, and every tool call should have a reasoning parameter which gives you a place to explain why you are calling the tool.

When using run_test_polars_code, make sure to test edge cases and validate data types.
If saving results to a file, add file writing code to the end of your polars_python_code variable (df.write_csv(output_file)).

Your code should use DataFrame to immediately operate on the data.
Your polars_python_code variable should be a complete python script that can be run with uv run --with polars. Read the code in the csv_file_path, operate on the data as requested, and print the results.

User request: {{user_request}}
CSV file path: {{csv_file_path}}
"""


def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Polars CSV Agent using Claude 3.7")
    parser.add_argument("-i", "--input", required=True, help="Path to input CSV file")
    parser.add_argument("-p", "--prompt", required=True, help="The user's request")
    parser.add_argument(
        "-c",
        "--compute",
        type=int,
        default=10,
        help="Maximum number of agent loops (default: 10)",
    )
    args = parser.parse_args()

    # Configure the API key
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    if not ANTHROPIC_API_KEY:
        console.print(
            "[red]Error: ANTHROPIC_API_KEY environment variable is not set[/red]"
        )
        console.print(
            "Please get your API key from https://console.anthropic.com/settings/keys"
        )
        console.print("Then set it with: export ANTHROPIC_API_KEY='your-api-key-here'")
        sys.exit(1)

    client = Anthropic(api_key=ANTHROPIC_API_KEY)

    # Create a single combined prompt based on the full template
    completed_prompt = AGENT_PROMPT.replace("{{user_request}}", args.prompt).replace(
        "{{csv_file_path}}", args.input
    )
    
    # Initialize messages with proper typing for Anthropic chat
    messages = [{"role": "user", "content": completed_prompt}]

    compute_iterations = 0
    break_loop = False
    previous_thinking = None

    # Main agent loop
    while True:
        if break_loop:
            break

        console.rule(
            f"[yellow]Agent Loop {compute_iterations+1}/{args.compute}[/yellow]"
        )
        compute_iterations += 1

        if compute_iterations >= args.compute:
            console.print(
                "[yellow]Warning: Reached maximum compute loops without final code[/yellow]"
            )
            console.print(
                "[yellow]Please try adjusting your prompt or increasing the compute limit.[/yellow]"
            )
            raise Exception(
                f"Maximum compute loops reached: {compute_iterations}/{args.compute}"
            )

        try:
            # Generate content with tool support
            response = client.messages.create(
                model="claude-3-7-sonnet-20250219",
                system="You are a world-class expert at crafting precise Polars data transformations in Python.",
                messages=messages,
                tools=TOOLS,
                max_tokens=8096,
                thinking={
                    "type": "enabled",
                    "budget_tokens": 4096
                },
            )

            # Extract thinking block and other content
            thinking_block = None
            tool_use_block = None
            text_block = None
            
            if response.content:
                # Get the message content
                for content_block in response.content:
                    if content_block.type == "thinking":
                        thinking_block = content_block
                        previous_thinking = thinking_block
                    elif content_block.type == "tool_use":
                        tool_use_block = content_block
                        # Access the proper attributes directly
                        tool_name = content_block.name
                        tool_input = content_block.input
                        tool_id = content_block.id
                    elif content_block.type == "text":
                        text_block = content_block
                        console.print(f"[cyan]Model response:[/cyan] {content_block.text}")
                
                # Handle text responses if there was no tool use
                if not tool_use_block and text_block:
                    messages.append({
                        "role": "assistant", 
                        "content": [
                            *([thinking_block] if thinking_block else []), 
                            {"type": "text", "text": text_block.text}
                        ]
                    })
                    continue
                
                # We need a tool use block to proceed
                if tool_use_block:
                    console.print(
                        f"[blue]Tool Call:[/blue] {tool_name}({json.dumps(tool_input, indent=2)})"
                    )

                    try:
                        # Execute the appropriate tool based on name
                        if tool_name == "list_columns":
                            result = list_columns(
                                reasoning=tool_input["reasoning"],
                                csv_path=tool_input["csv_path"],
                            )
                        elif tool_name == "sample_csv":
                            result = sample_csv(
                                reasoning=tool_input["reasoning"],
                                csv_path=tool_input["csv_path"],
                                row_count=tool_input["row_count"],
                            )
                        elif tool_name == "run_test_polars_code":
                            result = run_test_polars_code(
                                reasoning=tool_input["reasoning"],
                                polars_python_code=tool_input["polars_python_code"],
                                csv_path=tool_input["csv_path"],
                            )
                        elif tool_name == "run_final_polars_code":
                            output_file = tool_input.get("output_file")
                            result = run_final_polars_code(
                                reasoning=tool_input["reasoning"],
                                polars_python_code=tool_input["polars_python_code"],
                                csv_path=tool_input["csv_path"],
                                output_file=output_file,
                            )
                            break_loop = True
                        else:
                            raise Exception(f"Unknown tool call: {tool_name}")

                        console.print(
                            f"[blue]Tool Call Result:[/blue] {tool_name}(...) ->\n{result}"
                        )

                        # Append the tool result to messages
                        messages.append(
                            {
                                "role": "assistant",
                                "content": [
                                    *([thinking_block] if thinking_block else []),
                                    {
                                        "type": "tool_use",
                                        "id": tool_id,
                                        "name": tool_name,
                                        "input": tool_input
                                    }
                                ]
                            }
                        )

                        messages.append(
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "tool_result",
                                        "tool_use_id": tool_id,
                                        "content": str(result)
                                    }
                                ]
                            }
                        )

                    except Exception as e:
                        error_msg = f"Error executing {tool_name}: {e}"
                        console.print(f"[red]{error_msg}[/red]")

                        # Append the error to messages
                        messages.append(
                            {
                                "role": "assistant",
                                "content": [
                                    *([thinking_block] if thinking_block else []),
                                    {
                                        "type": "tool_use",
                                        "id": tool_id,
                                        "name": tool_name,
                                        "input": tool_input
                                    }
                                ]
                            }
                        )

                        messages.append(
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "tool_result",
                                        "tool_use_id": tool_id,
                                        "content": str(error_msg)
                                    }
                                ]
                            }
                        )

        except Exception as e:
            console.print(f"[red]Error in agent loop: {str(e)}[/red]")
            raise e


if __name__ == "__main__":
    main()