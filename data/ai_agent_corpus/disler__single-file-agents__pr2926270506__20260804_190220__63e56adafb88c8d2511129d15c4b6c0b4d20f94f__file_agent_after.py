#!/usr/bin/env python3

"""
Molecular file editor for the Atomic/Composable Architecture implementation of the file editor agent.
This module combines atomic components to provide file editing capabilities.
"""

import time
from typing import Tuple, Dict, Any, List, Optional, Callable
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from anthropic import Anthropic

import sys
import os

# Add the parent directory to the Python path to enable absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from atom.logging import log_info, log_error, display_token_usage

# Initialize rich console
console = Console()

# Define constants
MODEL = "claude-3-7-sonnet-20250219"
DEFAULT_THINKING_TOKENS = 3000

class FileEditor:
    """
    File editor that combines atomic components to provide file editing capabilities.
    """
    
    @staticmethod
    def run_agent(
        client: Anthropic,
        prompt: str,
        handle_tool_use_func,
        max_thinking_tokens: int = DEFAULT_THINKING_TOKENS,
        max_loops: int = 10,
        use_token_efficiency: bool = False,
    ) -> Tuple[str, int, int]:
        """
        Run the Claude agent with file editing capabilities.

        Args:
            client: The Anthropic client
            prompt: The user's prompt
            handle_tool_use_func: Function to handle tool use requests
            max_thinking_tokens: Maximum tokens for thinking
            max_loops: Maximum number of tool use loops
            use_token_efficiency: Whether to use token-efficient tool use beta feature

        Returns:
            Tuple containing:
            - Final response from Claude (str)
            - Total input tokens used (int)
            - Total output tokens used (int)
        """
        # Track token usage
        input_tokens_total = 0
        output_tokens_total = 0
        system_prompt = """You are a helpful AI assistant with text editing capabilities.
You have access to a text editor tool that can view, edit, and create files.
Always think step by step about what you need to do before taking any action.
Be careful when making edits to files, as they can permanently change the user's files.
Follow these steps when handling file operations:
1. First, view files to understand their content before making changes
2. For edits, ensure you have the correct context and are making the right changes
3. When creating files, make sure they're in the right location with proper formatting
"""

        # Define text editor tool
        text_editor_tool = {"name": "str_replace_editor", "type": "text_editor_20250124"}

        messages = [
            {
                "role": "user",
                "content": f"""I need help with editing files. Here's what I want to do:

{prompt}

Please use the text editor tool to help me with this. First, think through what you need to do, then use the appropriate tool.
""",
            }
        ]

        loop_count = 0
        tool_use_count = 0
        thinking_start_time = time.time()

        while loop_count < max_loops:
            loop_count += 1

            console.rule(f"[yellow]Agent Loop {loop_count}/{max_loops}[/yellow]")
            log_info("file_editor", f"Starting agent loop {loop_count}/{max_loops}")

            # Create message with text editor tool
            message_args = {
                "model": MODEL,
                "max_tokens": 4096,
                "tools": [text_editor_tool],
                "messages": messages,
                "system": system_prompt,
                "thinking": {"type": "enabled", "budget_tokens": max_thinking_tokens},
            }

            # Use the beta.messages with betas parameter if token efficiency is enabled
            if use_token_efficiency:
                # Using token-efficient tools beta feature
                message_args["betas"] = ["token-efficient-tools-2025-02-19"]
                response = client.beta.messages.create(**message_args)
            else:
                # Standard approach
                response = client.messages.create(**message_args)

            # Track token usage
            if hasattr(response, "usage"):
                input_tokens = getattr(response.usage, "input_tokens", 0)
                output_tokens = getattr(response.usage, "output_tokens", 0)

                input_tokens_total += input_tokens
                output_tokens_total += output_tokens

                console.print(
                    f"[dim]Loop {loop_count} tokens: Input={input_tokens}, Output={output_tokens}[/dim]"
                )
                log_info(
                    "file_editor", 
                    f"Loop {loop_count} tokens: Input={input_tokens}, Output={output_tokens}"
                )

            # Process response content
            thinking_block = None
            tool_use_block = None
            text_block = None

            for content_block in response.content:
                if content_block.type == "thinking":
                    thinking_block = content_block
                    # Access the thinking attribute which contains the actual thinking text
                    if hasattr(thinking_block, "thinking"):
                        console.print(
                            Panel(
                                thinking_block.thinking,
                                title=f"Claude's Thinking (Loop {loop_count})",
                                border_style="blue",
                            )
                        )
                    else:
                        console.print(
                            Panel(
                                "Claude is thinking...",
                                title=f"Claude's Thinking (Loop {loop_count})",
                                border_style="blue",
                            )
                        )
                elif content_block.type == "tool_use":
                    tool_use_block = content_block
                    tool_use_count += 1
                elif content_block.type == "text":
                    text_block = content_block

            # If we got a final text response with no tool use, we're done
            if text_block and not tool_use_block:
                thinking_end_time = time.time()
                thinking_duration = thinking_end_time - thinking_start_time

                console.print(
                    f"\n[bold green]Completed in {thinking_duration:.2f} seconds after {loop_count} loops and {tool_use_count} tool uses[/bold green]"
                )
                log_info(
                    "file_editor",
                    f"Completed in {thinking_duration:.2f} seconds after {loop_count} loops and {tool_use_count} tool uses"
                )

                # Add the response to messages
                messages.append(
                    {
                        "role": "assistant",
                        "content": [
                            *([thinking_block] if thinking_block else []),
                            {"type": "text", "text": text_block.text},
                        ],
                    }
                )

                return text_block.text, input_tokens_total, output_tokens_total

            # Handle tool use
            if tool_use_block:
                # Add the assistant's response to messages before handling tool calls
                messages.append({"role": "assistant", "content": response.content})

                console.print(
                    f"\n[bold blue]Tool Call:[/bold blue] {tool_use_block.name}"
                )
                log_info("file_editor", f"Tool Call: {tool_use_block.name}")

                # Handle the tool use
                tool_result = handle_tool_use_func(tool_use_block.input)

                # Format tool result for Claude
                tool_result_message = {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use_block.id,
                            "content": tool_result.get("error") or tool_result.get("result", ""),
                        }
                    ],
                }
                messages.append(tool_result_message)

        # If we reach here, we hit the max loops
        console.print(
            f"\n[bold red]Warning: Reached maximum loops ({max_loops}) without completing the task[/bold red]"
        )
        log_error(
            "file_editor",
            f"Reached maximum loops ({max_loops}) without completing the task"
        )
        return (
            "I wasn't able to complete the task within the allowed number of thinking steps. Please try a more specific prompt or increase the loop limit.",
            input_tokens_total,
            output_tokens_total,
        )

# Expose the run_agent function at the module level
def run_agent(
    client: Anthropic,
    prompt: str,
    handle_tool_use: Callable[[Dict[str, Any]], Dict[str, Any]],
    max_tool_use_loops: int = 15,
    token_efficient_tool_use: bool = True,
) -> Tuple[int, int]:
    """
    Run the file editor agent with the specified prompt.
    
    Args:
        client: The Anthropic client
        prompt: The prompt to send to Claude
        handle_tool_use: Function to handle tool use requests
        max_tool_use_loops: Maximum number of tool use loops
        token_efficient_tool_use: Whether to use token-efficient tool use
        
    Returns:
        Tuple containing input and output token counts
    """
    log_info("file_editor", f"Running agent with prompt: {prompt}")
    
    _, input_tokens, output_tokens = FileEditor.run_agent(
        client=client,
        prompt=prompt,
        handle_tool_use_func=handle_tool_use,
        max_loops=max_tool_use_loops,
        use_token_efficiency=token_efficient_tool_use,
        max_thinking_tokens=DEFAULT_THINKING_TOKENS
    )
    
    return input_tokens, output_tokens
