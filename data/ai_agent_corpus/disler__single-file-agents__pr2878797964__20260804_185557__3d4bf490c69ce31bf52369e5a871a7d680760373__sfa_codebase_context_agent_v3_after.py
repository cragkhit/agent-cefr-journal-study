#!/usr/bin/env -S uv run --script

# /// script
# dependencies = [
#   "anthropic>=0.47.1",
#   "rich>=13.7.0",
#   "pydantic>=2.0.0",
# ]
# ///

"""
Usage:
    uv run sfa_codebase_context_agent_v3.py --prompt "What do i have to do to build a new v4 openai agent?" --directory "." --globs "*.py" --extensions py md --limit 10 --file-line-limit 1000
"""

import os
import sys
import json
import argparse
import subprocess
import time
import fnmatch
import concurrent.futures
from typing import List, Dict, Any
from rich.console import Console
from anthropic import Anthropic

# Initialize rich console
console = Console()

# Constants
THINKING_BUDGET_TOKENS_PER_FILE = 2000
BATCH_SIZE = 10
MAX_RETRIES = 3
RETRY_WAIT = 1

# Global variables
USER_PROMPT = ""
RELEVANT_FILES = []

def git_list_files(reasoning: str, directory: str = os.getcwd(), globs: List[str] = [], extensions: List[str] = []) -> List[str]:
    """Returns a list of files in the repository, respecting gitignore.

    Args:
        reasoning: Explanation of why we're listing files
        directory: Directory to search in (defaults to current working directory)
        globs: List of glob patterns to filter files (optional)
        extensions: List of file extensions to filter files (optional)

    Returns:
        List of file paths as strings
    """
    try:
        console.log(f"[blue]Git List Files Tool[/blue] - Reasoning: {reasoning}")
        console.log(f"[dim]Directory: {directory}, Globs: {globs}, Extensions: {extensions}[/dim]")
        
        # Change to the specified directory
        original_dir = os.getcwd()
        os.chdir(directory)
        
        # Get all files tracked by git
        result = subprocess.run(
            "git ls-files",
            shell=True,
            text=True,
            capture_output=True,
        )
        
        files = result.stdout.strip().split("\n")
        
        # Filter by globs if provided
        if globs:
            filtered_files = []
            for pattern in globs:
                for file in files:
                    if fnmatch.fnmatch(file, pattern):
                        filtered_files.append(file)
            files = filtered_files
        
        # Filter by extensions if provided
        if extensions:
            files = [file for file in files if any(file.endswith(f".{ext}") for ext in extensions)]
        
        # Change back to the original directory
        os.chdir(original_dir)
        
        # Convert to absolute paths
        files = [os.path.join(directory, file) for file in files]
        
        console.log(f"[dim]Found {len(files)} files[/dim]")
        return files
    except Exception as e:
        console.log(f"[red]Error listing files: {str(e)}[/red]")
        return []

def check_file_paths_line_length(reasoning: str, file_paths: List[str], file_line_limit: int = 500) -> Dict[str, int]:
    """Checks the line length of each file and returns a dictionary of file paths and their line counts.
    
    Args:
        reasoning: Explanation of why we're checking line lengths
        file_paths: List of file paths to check
        file_line_limit: Maximum number of lines per file
        
    Returns:
        Dictionary mapping file paths to their total line counts
    """
    try:
        console.log(f"[blue]Check File Paths Line Length Tool[/blue] - Reasoning: {reasoning}")
        console.log(f"[dim]Checking {len(file_paths)} files with line limit {file_line_limit}[/dim]")
        
        result = {}
        for file_path in file_paths:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    line_count = len(lines)
                    if line_count <= file_line_limit:
                        result[file_path] = line_count
                    else:
                        console.log(f"[yellow]Skipping {file_path}: {line_count} lines exceed limit of {file_line_limit}[/yellow]")
            except Exception as e:
                console.log(f"[red]Error reading file {file_path}: {str(e)}[/red]")
        
        console.log(f"[dim]Found {len(result)} files within line limit[/dim]")
        return result
    except Exception as e:
        console.log(f"[red]Error checking file paths: {str(e)}[/red]")
        return {}

def determine_if_file_is_relevant(prompt: str, file_path: str, client: Anthropic) -> Dict[str, Any]:  # type: ignore
    """Determines if a single file is relevant to the prompt.
    
    Args:
        prompt: The user prompt
        file_path: Path to the file to check
        client: Anthropic client
        
    Returns:
        Dictionary with reasoning and is_relevant flag
    """
    result = {
        "reasoning": "Error: Could not process file",
        "file_path": file_path,
        "is_relevant": False
    }
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        # Truncate file content if it's too long
        if len(file_content) > 10000:
            file_content = file_content[:10000] + "... [content truncated]"
        
        file_prompt = f"""
        <purpose>
        You are a codebase context builder. Your task is to determine if a file is relevant to a user query.
        </purpose>
        
        <instructions>
        <instruction>Analyze the file content and determine if it's relevant to the user query.</instruction>
        <instruction>Provide clear reasoning for your decision.</instruction>
        <instruction>Return a structured output with your reasoning and a boolean indicating relevance.</instruction>
        </instructions>
        
        <user-query>
        {prompt}
        </user-query>
        
        <file-path>
        {file_path}
        </file-path>
        
        <file-content>
        {file_content}
        </file-content>
        """
        
        for attempt in range(MAX_RETRIES):
            try:
                response = client.messages.create(
                    model="claude-3-7-sonnet-20250219",
                    max_tokens=3000,  # Increased to be greater than thinking.budget_tokens
                    thinking={
                        "type": "enabled",
                        "budget_tokens": THINKING_BUDGET_TOKENS_PER_FILE
                    },
                    messages=[{"role": "user", "content": file_prompt}],
                    system="Determine if the file is relevant to the user query. Return a JSON object with 'reasoning' and 'is_relevant' fields."
                )
                
                # Parse the response
                response_text = response.content[0].text
                result = json.loads(response_text)
                
                return {
                    "reasoning": result.get("reasoning", "No reasoning provided"),
                    "file_path": file_path,
                    "is_relevant": result.get("is_relevant", False)
                }
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    console.log(f"[yellow]Retry {attempt + 1}/{MAX_RETRIES} for {file_path}: {str(e)}[/yellow]")
                    time.sleep(RETRY_WAIT)
                else:
                    console.log(f"[red]Failed to determine relevance for {file_path}: {str(e)}[/red]")
                    return {
                        "reasoning": f"Error: {str(e)}",
                        "file_path": file_path,
                        "is_relevant": False
                    }
    except Exception as e:
        console.log(f"[red]Error processing file {file_path}: {str(e)}[/red]")
        return {
            "reasoning": f"Error: {str(e)}",
            "file_path": file_path,
            "is_relevant": False
        }

def determine_if_files_are_relevant(reasoning: str, file_paths: List[str]) -> Dict[str, Any]:
    """Determines if files are relevant to the prompt using parallelism.
    
    Args:
        reasoning: Explanation of why we're determining relevance
        file_paths: List of file paths to check
        
    Returns:
        Dictionary with results for each file
    """
    try:
        console.log(f"[blue]Determine If Files Are Relevant Tool[/blue] - Reasoning: {reasoning}")
        console.log(f"[dim]Checking {len(file_paths)} files in batches of {BATCH_SIZE}[/dim]")
        
        # Initialize Anthropic client
        client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        
        results = {}
        
        # Process files in batches
        for i in range(0, len(file_paths), BATCH_SIZE):
            batch = file_paths[i:i+BATCH_SIZE]
            console.log(f"[dim]Processing batch {i//BATCH_SIZE + 1}/{(len(file_paths) + BATCH_SIZE - 1)//BATCH_SIZE}[/dim]")
            
            # Process batch in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=BATCH_SIZE) as executor:
                future_to_file = {
                    executor.submit(determine_if_file_is_relevant, USER_PROMPT, file_path, client): file_path
                    for file_path in batch
                }
                
                for future in concurrent.futures.as_completed(future_to_file):
                    file_path = future_to_file[future]
                    try:
                        result = future.result()
                        results[file_path] = result
                        relevance = "Relevant" if result["is_relevant"] else "Not relevant"
                        console.log(f"[dim]{file_path}: {relevance}[/dim]")
                    except Exception as e:
                        console.log(f"[red]Error processing {file_path}: {str(e)}[/red]")
        
        return results
    except Exception as e:
        console.log(f"[red]Error determining file relevance: {str(e)}[/red]")
        return {}

def add_relevant_files(reasoning: str, file_paths: List[str]) -> str:
    """Adds files to the list of relevant files.
    
    Args:
        reasoning: Explanation of why we're adding these files
        file_paths: List of file paths to add
        
    Returns:
        String indicating success
    """
    try:
        console.log(f"[blue]Add Relevant Files Tool[/blue] - Reasoning: {reasoning}")
        console.log(f"[dim]Adding {len(file_paths)} files to relevant files list[/dim]")
        
        global RELEVANT_FILES
        for file_path in file_paths:
            if file_path not in RELEVANT_FILES:
                RELEVANT_FILES.append(file_path)
        
        console.log(f"[green]Added {len(file_paths)} files. Total relevant files: {len(RELEVANT_FILES)}[/green]")
        return "Files Added"
    except Exception as e:
        console.log(f"[red]Error adding relevant files: {str(e)}[/red]")
        return f"Error: {str(e)}"

# Define tool schemas for Anthropic
TOOLS = [
    {
        "name": "git_list_files",
        "description": "Returns list of files in the repository, respecting gitignore",
        "input_schema": {
            "type": "object",
            "properties": {
                "reasoning": {
                    "type": "string",
                    "description": "Why we need to list files relative to user request",
                },
                "directory": {
                    "type": "string",
                    "description": "Directory to search in (defaults to current working directory)",
                },
                "globs": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "List of glob patterns to filter files (optional)",
                },
                "extensions": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "List of file extensions to filter files (optional)",
                },
            },
            "required": ["reasoning"],
        },
    },
    {
        "name": "check_file_paths_line_length",
        "description": "Checks the line length of each file and returns a dictionary of file paths and their line counts",
        "input_schema": {
            "type": "object",
            "properties": {
                "reasoning": {
                    "type": "string",
                    "description": "Why we need to check line lengths",
                },
                "file_paths": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "List of file paths to check",
                },
            },
            "required": ["reasoning", "file_paths"],
        },
    },
    {
        "name": "determine_if_files_are_relevant",
        "description": "Determines if files are relevant to the prompt using parallelism",
        "input_schema": {
            "type": "object",
            "properties": {
                "reasoning": {
                    "type": "string",
                    "description": "Why we need to determine relevance",
                },
                "file_paths": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "List of file paths to check",
                },
            },
            "required": ["reasoning", "file_paths"],
        },
    },
    {
        "name": "add_relevant_files",
        "description": "Adds files to the list of relevant files",
        "input_schema": {
            "type": "object",
            "properties": {
                "reasoning": {
                    "type": "string",
                    "description": "Why we need to add these files",
                },
                "file_paths": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "List of file paths to add",
                },
            },
            "required": ["reasoning", "file_paths"],
        },
    },
]

AGENT_PROMPT = """
<purpose>
You are a codebase context builder. Use the available tools to search, filter and determine which files in the codebase are relevant to the prompt (user query).
</purpose>

<instructions>
<instruction>Start by listing files in the codebase using git_list_files, filtering by globs and extensions if provided.</instruction>
<instruction>Check file line lengths to ensure they are within the specified limit using check_file_paths_line_length.</instruction>
<instruction>Determine which files are relevant to the user query using determine_if_files_are_relevant.</instruction>
<instruction>Add relevant files to the final list using add_relevant_files.</instruction>
<instruction>Be thorough but efficient with tool usage.</instruction>
<instruction>Think step by step about what information you need.</instruction>
<instruction>Be sure to specify every parameter for each tool call.</instruction>
<instruction>Every tool call should have a reasoning parameter which gives you a place to explain why you are calling the tool.</instruction>
<instruction>The determine_if_files_are_relevant tool will process files in batches of 10 for efficiency.</instruction>
<instruction>Focus on finding the most relevant files that will help answer the user query.</instruction>
<instruction>Stop once you've reached the file limit or have exhausted all potential relevant files.</instruction>
</instructions>

<user-request>
{{user_request}}
</user-request>

<dynamic-variables>
Directory: {{directory}}
Globs: {{globs}}
Extensions: {{extensions}}
File Line Limit: {{file_line_limit}}
File Limit: {{limit}}
</dynamic-variables>
"""

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Codebase Context Agent using Claude 3.7")
    parser.add_argument("-p", "--prompt", required=True, help="The user's request")
    parser.add_argument("-d", "--directory", default=os.getcwd(), help="Directory to search in (defaults to current working directory)")
    parser.add_argument("-g", "--globs", nargs="*", default=[], help="List of glob patterns to filter files (optional)")
    parser.add_argument("-e", "--extensions", nargs="*", default=[], help="List of file extensions to filter files (optional)")
    parser.add_argument("-q", "--quiet", action="store_true", help="Quiet mode (don't show logging)")
    parser.add_argument("-l", "--limit", type=int, default=100, help="Maximum number of files to return")
    parser.add_argument("-f", "--file-line-limit", type=int, default=500, help="Maximum number of lines per file")
    parser.add_argument("-c", "--compute", type=int, default=10, help="Maximum number of agent loops (default: 10)")
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

    # Set global USER_PROMPT
    global USER_PROMPT
    USER_PROMPT = args.prompt

    # Configure quiet mode
    if args.quiet:
        console.quiet = True

    # Create a single combined prompt based on the full template
    completed_prompt = (
        AGENT_PROMPT.replace("{{user_request}}", args.prompt)
        .replace("{{directory}}", args.directory)
        .replace("{{globs}}", str(args.globs))
        .replace("{{extensions}}", str(args.extensions))
        .replace("{{file_line_limit}}", str(args.file_line_limit))
        .replace("{{limit}}", str(args.limit))
    )
    
    # Initialize messages with proper typing for Anthropic chat
    messages = [{"role": "user", "content": completed_prompt}]

    compute_iterations = 0
    break_loop = False
    # Main agent loop
    while True:
        if break_loop or compute_iterations >= args.compute or len(RELEVANT_FILES) >= args.limit:
            break

        console.rule(
            f"[yellow]Agent Loop {compute_iterations+1}/{args.compute}[/yellow]"
        )
        compute_iterations += 1

        try:
            # Generate content with tool support
            response = client.messages.create(
                model="claude-3-7-sonnet-20250219",
                system="You are a codebase context builder. Use the available tools to search, filter and determine which files in the codebase are relevant to the prompt (user query).",
                messages=messages,
                tools=TOOLS,
                max_tokens=4000,
                thinking={
                    "type": "enabled",
                    "budget_tokens": 2000
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
                    messages.append({  # type: ignore
                        "role": "assistant", 
                        "content": [
                            *([thinking_block] if thinking_block else []), 
                            {"type": "text", "text": text_block.text}
                        ]
                    })
                    break_loop = True
                    continue
                
                # We need a tool use block to proceed
                if tool_use_block:
                    console.print(
                        f"[blue]Tool Call:[/blue] {tool_name}({json.dumps(tool_input, indent=2)})"
                    )

                    try:
                        # Execute the appropriate tool based on name
                        if tool_name == "git_list_files":
                            directory = tool_input.get("directory", args.directory)
                            globs = tool_input.get("globs", args.globs)
                            extensions = tool_input.get("extensions", args.extensions)
                            result = git_list_files(
                                reasoning=tool_input["reasoning"],
                                directory=directory,
                                globs=globs,
                                extensions=extensions,
                            )
                        elif tool_name == "check_file_paths_line_length":
                            result = check_file_paths_line_length(
                                reasoning=tool_input["reasoning"],
                                file_paths=tool_input["file_paths"],
                                file_line_limit=args.file_line_limit,
                            )
                        elif tool_name == "determine_if_files_are_relevant":
                            result = determine_if_files_are_relevant(
                                reasoning=tool_input["reasoning"],
                                file_paths=tool_input["file_paths"],
                            )
                        elif tool_name == "add_relevant_files":
                            result = add_relevant_files(
                                reasoning=tool_input["reasoning"],
                                file_paths=tool_input["file_paths"],
                            )
                            # Check if we've reached the limit
                            if len(RELEVANT_FILES) >= args.limit:
                                console.print(f"[green]Reached file limit of {args.limit}. Stopping.[/green]")
                                break_loop = True
                        else:
                            raise Exception(f"Unknown tool call: {tool_name}")

                        console.print(
                            f"[blue]Tool Call Result:[/blue] {tool_name}(...)"
                        )

                        # Append the tool result to messages
                        messages.append(
                            {  # type: ignore
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
                            {  # type: ignore
                                "role": "user",
                                "content": [
                                    {
                                        "type": "tool_result",
                                        "tool_use_id": tool_id,
                                        "content": json.dumps(result)
                                    }
                                ]
                            }
                        )

                    except Exception as e:
                        error_msg = f"Error executing {tool_name}: {e}"
                        console.print(f"[red]{error_msg}[/red]")

                        # Append the error to messages
                        messages.append(
                            {  # type: ignore
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
                            {  # type: ignore
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

    # Print the final list of relevant files
    console.rule("[green]Relevant Files[/green]")
    for i, file_path in enumerate(RELEVANT_FILES, 1):
        console.print(f"{i}. {file_path}")


if __name__ == "__main__":
    main()
