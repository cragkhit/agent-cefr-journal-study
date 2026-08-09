# /// script
# dependencies = [
#   "openai>=1.63.0",
#   "rich>=13.7.0",
#   "pydantic>=2.0.0",
#   "polars>=1.22.0",
# ]
# ///

import os
import sys
import json
import argparse
import tempfile
import subprocess
from typing import List, Optional
from rich.console import Console
from rich.panel import Panel
import openai
import polars as pl
from pydantic import BaseModel, Field, ValidationError
from openai import pydantic_function_tool

# Initialize rich console
console = Console()

# Create our list of function tools from our pydantic models
class ListColumnsArgs(BaseModel):
    reasoning: str = Field(
        ..., description="Explanation for listing columns relative to the user request"
    )
    csv_path: str = Field(..., description="Path to the CSV file")

class SampleCSVArgs(BaseModel):
    reasoning: str = Field(..., description="Explanation for sampling the CSV data")
    csv_path: str = Field(..., description="Path to the CSV file")
    row_count: int = Field(
        ..., description="Number of rows to sample (aim for 3-5 rows)"
    )

class RunTestPolarsCodeArgs(BaseModel):
    reasoning: str = Field(..., description="Reason for testing this Polars code")
    polars_python_code: str = Field(..., description="The Polars Python code to test")
    csv_path: str = Field(..., description="Path to the CSV file")

class RunFinalPolarsCodeArgs(BaseModel):
    reasoning: str = Field(
        ...,
        description="Final explanation of how this code satisfies the user request",
    )
    csv_path: str = Field(..., description="Path to the CSV file")
    polars_python_code: str = Field(..., description="The validated Polars Python code to run")
    output_file: Optional[str] = Field(None, description="Optional path to save results to")

# Create tools list
tools = [
    pydantic_function_tool(ListColumnsArgs),
    pydantic_function_tool(SampleCSVArgs),
    pydantic_function_tool(RunTestPolarsCodeArgs),
    pydantic_function_tool(RunFinalPolarsCodeArgs),
]

AGENT_PROMPT = """<purpose>
    You are a world-class expert at crafting precise Polars data transformations in Python.
    Your goal is to generate accurate code that exactly matches the user's data analysis needs.
</purpose>

<instructions>
    <instruction>Use the provided tools to explore the CSV data and construct the perfect Polars transformation.</instruction>
    <instruction>Start by listing columns to understand what's available in the CSV.</instruction>
    <instruction>Sample the CSV to see actual data patterns.</instruction>
    <instruction>Test Polars code before finalizing it.</instruction>
    <instruction>Only call run_final_polars_code when you're confident the code is perfect.</instruction>
    <instruction>Be thorough but efficient with tool usage.</instruction>
    <instruction>If you find your run_test_polars_code tool call returns an error or won't satisfy the user request, try to fix the code or try a different approach.</instruction>
    <instruction>Think step by step about what information you need.</instruction>
    <instruction>Be sure to specify every parameter for each tool call.</instruction>
    <instruction>Every tool call should have a reasoning parameter which gives you a place to explain why you are calling the tool.</instruction>
    <instruction>When writing Polars code, always use proper error handling and data validation.</instruction>
</instructions>

<tools>
    <tool>
        <name>list_columns</name>
        <description>Returns list of available columns in the CSV file</description>
        <parameters>
            <parameter>
                <name>reasoning</name>
                <type>string</type>
                <description>Why we need to list columns relative to user request</description>
                <required>true</required>
            </parameter>
            <parameter>
                <name>csv_path</name>
                <type>string</type>
                <description>Path to the CSV file</description>
                <required>true</required>
            </parameter>
        </parameters>
    </tool>
    
    <tool>
        <name>sample_csv</name>
        <description>Returns sample rows from the CSV file</description>
        <parameters>
            <parameter>
                <name>reasoning</name>
                <type>string</type>
                <description>Why we need to sample this data</description>
                <required>true</required>
            </parameter>
            <parameter>
                <name>csv_path</name>
                <type>string</type>
                <description>Path to the CSV file</description>
                <required>true</required>
            </parameter>
            <parameter>
                <name>row_count</name>
                <type>integer</type>
                <description>Number of rows to sample aim for 3-5 rows</description>
                <required>true</required>
            </parameter>
        </parameters>
    </tool>
    
    <tool>
        <name>run_test_polars_code</name>
        <description>Tests Polars Python code and returns results (only visible to agent)</description>
        <parameters>
            <parameter>
                <name>reasoning</name>
                <type>string</type>
                <description>Why we're testing this specific code</description>
                <required>true</required>
            </parameter>
            <parameter>
                <name>polars_python_code</name>
                <type>string</type>
                <description>The Polars Python code to test</description>
                <required>true</required>
            </parameter>
            <parameter>
                <name>csv_path</name>
                <type>string</type>
                <description>Path to the CSV file</description>
                <required>true</required>
            </parameter>
        </parameters>
    </tool>
    
    <tool>
        <name>run_final_polars_code</name>
        <description>Runs the final validated Polars code and shows results to user</description>
        <parameters>
            <parameter>
                <name>reasoning</name>
                <type>string</type>
                <description>Final explanation of how code satisfies user request</description>
                <required>true</required>
            </parameter>
            <parameter>
                <name>csv_path</name>
                <type>string</type>
                <description>Path to the CSV file</description>
                <required>true</required>
            </parameter>
            <parameter>
                <name>polars_python_code</name>
                <type>string</type>
                <description>The validated Polars Python code to run</description>
                <required>true</required>
            </parameter>
            <parameter>
                <name>output_file</name>
                <type>string</type>
                <description>Optional path to save results to</description>
                <required>false</required>
            </parameter>
        </parameters>
    </tool>
</tools>

<user-request>
    {{user_request}}
</user-request>

<csv-file-path>
    {{csv_file_path}}
</csv-file-path>
"""

def list_columns(reasoning: str, csv_path: str) -> List[str]:
    """Returns a list of columns in the CSV file.

    The agent uses this to discover available columns and make informed decisions.

    Args:
        reasoning: Explanation of why we're listing columns relative to user request
        csv_path: Path to the CSV file

    Returns:
        List of column names as strings
    """
    try:
        df = pl.scan_csv(csv_path).collect()
        columns = df.columns
        console.log(f"[blue]List Columns Tool[/blue] - Reasoning: {reasoning}")
        return columns
    except Exception as e:
        console.log(f"[red]Error listing columns: {str(e)}[/red]")
        return []

def sample_csv(reasoning: str, csv_path: str, row_count: int) -> str:
    """Returns a sample of rows from the CSV file.

    The agent uses this to understand actual data content and patterns.

    Args:
        reasoning: Explanation of why we're sampling this data
        csv_path: Path to the CSV file
        row_count: Number of rows to sample (aim for 3-5 rows)

    Returns:
        String containing sample rows in readable format
    """
    try:
        df = pl.scan_csv(csv_path).limit(row_count).collect()
        output = df.to_string()
        console.log(
            f"[blue]Sample CSV Tool[/blue] - Rows: {row_count} - Reasoning: {reasoning}"
        )
        return output
    except Exception as e:
        console.log(f"[red]Error sampling CSV: {str(e)}[/red]")
        return ""

def run_test_polars_code(reasoning: str, polars_python_code: str, csv_path: str) -> str:
    """Executes test Polars Python code and returns results.

    The agent uses this to validate code before finalizing it.
    Results are only shown to the agent, not the user.

    Args:
        reasoning: Explanation of why we're running this test code
        polars_python_code: The Polars Python code to test
        csv_path: Path to the CSV file

    Returns:
        Code execution results as a string
    """
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(f"""
import polars as pl
import sys
import json

try:
    # Read the CSV file
    df = pl.scan_csv("{csv_path}")
    
    # Execute the user's code
    {polars_python_code}
    
    # If the code doesn't explicitly print or assign results, try to collect and display
    if 'result' not in locals():
        if any(var for var in locals().values() if isinstance(var, (pl.LazyFrame, pl.DataFrame))):
            # Find the last DataFrame/LazyFrame in locals
            result = next(var for var in reversed(list(locals().values())) 
                        if isinstance(var, (pl.LazyFrame, pl.DataFrame)))
            if isinstance(result, pl.LazyFrame):
                result = result.collect()
        else:
            result = df.collect()
    
    # Convert result to string if it's a DataFrame
    if isinstance(result, pl.DataFrame):
        output = result.to_string()
    else:
        output = str(result)
        
    print(output)
    
except Exception as e:
    print(json.dumps({{"error": str(e)}}), file=sys.stderr)
    sys.exit(1)
""")
            temp_file = f.name

        result = subprocess.run(['uv', 'run', '--with', 'polars', temp_file], 
                              capture_output=True, text=True)
        os.unlink(temp_file)

        if result.returncode != 0:
            return f"Error: {result.stderr}"

        console.log(f"[blue]Test Code Tool[/blue] - Reasoning: {reasoning}")
        console.log(f"[dim]Code:\n{polars_python_code}[/dim]")
        return result.stdout
    except Exception as e:
        console.log(f"[red]Error running test code: {str(e)}[/red]")
        return str(e)

def run_final_polars_code(reasoning: str, csv_path: str, polars_python_code: str, output_file: Optional[str] = None) -> str:
    """Executes the final Polars code and returns results to user.

    This is the last tool call the agent should make after validating the code.

    Args:
        reasoning: Final explanation of how this code satisfies user request
        csv_path: Path to the CSV file
        polars_python_code: The validated Polars Python code to run
        output_file: Optional path to save results to

    Returns:
        Code execution results as a string
    """
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(f"""
import polars as pl
import sys
import json

try:
    # Read the CSV file
    df = pl.scan_csv("{csv_path}")
    
    # Execute the user's code
    {polars_python_code}
    
    # If the code doesn't explicitly print or assign results, try to collect and display
    if 'result' not in locals():
        if any(var for var in locals().values() if isinstance(var, (pl.LazyFrame, pl.DataFrame))):
            # Find the last DataFrame/LazyFrame in locals
            result = next(var for var in reversed(list(locals().values())) 
                        if isinstance(var, (pl.LazyFrame, pl.DataFrame)))
            if isinstance(result, pl.LazyFrame):
                result = result.collect()
        else:
            result = df.collect()
    
    # Handle output file if specified
    output_file = {repr(output_file) if output_file else 'None'}
    if output_file:
        if isinstance(result, pl.DataFrame):
            if output_file.endswith('.csv'):
                result.write_csv(output_file)
            elif output_file.endswith('.json'):
                result.write_json(output_file)
            else:
                result.write_csv(output_file + '.csv')  # Default to CSV
        else:
            # For non-DataFrame results, create a single column DataFrame
            pl.DataFrame({{'result': [str(result)]}).write_csv(output_file)
        print(f"Results written to {{output_file}}")
    
    # Convert result to string for display
    if isinstance(result, pl.DataFrame):
        output = result.to_string()
    else:
        output = str(result)
        
    print(output)
    
except Exception as e:
    print(json.dumps({{"error": str(e)}}), file=sys.stderr)
    sys.exit(1)
""")
            temp_file = f.name

        result = subprocess.run(['uv', 'run', '--with', 'polars', temp_file],
                              capture_output=True, text=True)
        os.unlink(temp_file)

        if result.returncode != 0:
            return f"Error: {result.stderr}"

        console.log(
            Panel(
                f"[green]Final Code Tool[/green]\nReasoning: {reasoning}\nCode:\n{polars_python_code}"
            )
        )
        return result.stdout
    except Exception as e:
        console.log(f"[red]Error running final code: {str(e)}[/red]")
        return str(e)

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Polars CSV Agent using OpenAI API")
    parser.add_argument(
        "-i", "--input", required=True, help="Path to input CSV file"
    )
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
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        console.print(
            "[red]Error: OPENAI_API_KEY environment variable is not set[/red]"
        )
        console.print(
            "Please get your API key from https://platform.openai.com/api-keys"
        )
        console.print("Then set it with: export OPENAI_API_KEY='your-api-key-here'")
        sys.exit(1)

    openai.api_key = OPENAI_API_KEY

    # Create a single combined prompt based on the full template
    completed_prompt = AGENT_PROMPT.replace("{{user_request}}", args.prompt).replace("{{csv_file_path}}", args.input)
    # Initialize messages with proper typing for OpenAI chat
    messages: List[dict] = [{"role": "user", "content": completed_prompt}]

    compute_iterations = 0

    # Main agent loop
    while True:
        console.rule(
            f"[yellow]Agent Loop {compute_iterations+1}/{args.compute}[/yellow]"
        )
        compute_iterations += 1

        if compute_iterations >= args.compute:
            console.print(
                "[yellow]Warning: Reached maximum compute loops without final code[/yellow]"
            )
            raise Exception(
                f"Maximum compute loops reached: {compute_iterations}/{args.compute}"
            )

        try:
            # Generate content with tool support
            response = openai.chat.completions.create(
                model="o3-mini",
                messages=messages,
                tools=tools,
                tool_choice="required",
            )

            if response.choices:
                assert len(response.choices) == 1
                message = response.choices[0].message

                if message.function_call:
                    func_call = message.function_call
                elif message.tool_calls and len(message.tool_calls) > 0:
                    tool_call = message.tool_calls[0]
                    func_call = tool_call.function
                else:
                    func_call = None

                if func_call:
                    func_name = func_call.name
                    func_args_str = func_call.arguments

                    messages.append(
                        {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": tool_call.id,
                                    "type": "function",
                                    "function": func_call,
                                }
                            ],
                        }
                    )

                    console.print(
                        f"[blue]Function Call:[/blue] {func_name}({func_args_str})"
                    )
                    try:
                        # Validate and parse arguments using the corresponding pydantic model
                        if func_name == "ListColumnsArgs":
                            args_parsed = ListColumnsArgs.model_validate_json(
                                func_args_str
                            )
                            result = list_columns(
                                reasoning=args_parsed.reasoning,
                                csv_path=args_parsed.csv_path
                            )
                        elif func_name == "SampleCSVArgs":
                            args_parsed = SampleCSVArgs.model_validate_json(
                                func_args_str
                            )
                            result = sample_csv(
                                reasoning=args_parsed.reasoning,
                                csv_path=args_parsed.csv_path,
                                row_count=args_parsed.row_count,
                            )
                        elif func_name == "RunTestPolarsCodeArgs":
                            args_parsed = RunTestPolarsCodeArgs.model_validate_json(
                                func_args_str
                            )
                            result = run_test_polars_code(
                                reasoning=args_parsed.reasoning,
                                polars_python_code=args_parsed.polars_python_code,
                                csv_path=args_parsed.csv_path,
                            )
                        elif func_name == "RunFinalPolarsCodeArgs":
                            args_parsed = RunFinalPolarsCodeArgs.model_validate_json(
                                func_args_str
                            )
                            result = run_final_polars_code(
                                reasoning=args_parsed.reasoning,
                                csv_path=args_parsed.csv_path,
                                polars_python_code=args_parsed.polars_python_code,
                                output_file=args_parsed.output_file,
                            )
                            console.print("\n[green]Final Results:[/green]")
                            console.print(result)
                            return
                        else:
                            raise Exception(f"Unknown tool call: {func_name}")

                        console.print(
                            f"[blue]Function Call Result:[/blue] {func_name}(...) ->\n{result}"
                        )

                        # Append the function call result into our messages as a tool response
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": json.dumps({"result": str(result)}),
                            }
                        )

                    except Exception as e:
                        error_msg = f"Argument validation failed for {func_name}: {e}"
                        console.print(f"[red]{error_msg}[/red]")
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": json.dumps({"error": error_msg}),
                            }
                        )
                        continue
                else:
                    raise Exception(
                        "No function call in this response - should never happen"
                    )

        except Exception as e:
            console.print(f"[red]Error in agent loop: {str(e)}[/red]")
            raise e

if __name__ == "__main__":
    main()
