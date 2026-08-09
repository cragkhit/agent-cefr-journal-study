#!/usr/bin/env python3
"""
Python MCP Chunk Streaming Example
Demonstrates the enhanced execute_sequence tool with detailed step tracking
"""

import asyncio
import json
import sys
import time
from datetime import datetime
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def format_timestamp(iso_timestamp):
    """Convert ISO timestamp to readable format"""
    dt = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))
    return dt.strftime("%H:%M:%S.%f")[:-3]


def print_step_info(step):
    """Print formatted step information"""
    status_symbol = "✓" if step["status"] == "success" else "✗"
    print(f"\n[{step['progress']}] {status_symbol} Step {step['step']}: {step['tool_name']}")
    print(f"  Started:  {format_timestamp(step['started_at'])}")
    print(f"  Completed: {format_timestamp(step['completed_at'])}")
    print(f"  Duration: {step['duration_ms']}ms")
    
    if step["status"] != "success" and "result" in step and "error" in step["result"]:
        print(f"  Error: {step['result']['error']}")


async def run_sequence_demo():
    """Run a demo sequence showing chunk-like streaming"""
    
    # Define our automation sequence
    sequence = [
        {
            "tool_name": "get_applications",
            "arguments": {}
        },
        {
            "tool_name": "delay",
            "arguments": {"delay_ms": 1000}
        },
        {
            "tool_name": "capture_screen",
            "arguments": {}
        },
        {
            "tool_name": "get_clipboard",
            "arguments": {}
        },
        {
            "tool_name": "open_application",
            "arguments": {"app_name": "notepad"}
        },
        {
            "tool_name": "delay", 
            "arguments": {"delay_ms": 2000}
        },
        {
            "tool_name": "type_into_element",
            "arguments": {
                "selector": "role:document",
                "text_to_type": "Hello from chunk streaming demo!"
            }
        }
    ]
    
    # Convert sequence to the format expected by execute_sequence
    items = []
    for tool in sequence:
        items.append({
            "tool_name": tool["tool_name"],
            "arguments": tool.get("arguments", {}),
            "continue_on_error": tool.get("continue_on_error", False),
            "delay_ms": tool.get("delay_ms", 0)
        })
    
    # Connect to MCP server
    server_params = StdioServerParameters(
        command="terminator-mcp-agent",
        args=[],
        env=None
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            print("Connected to terminator-mcp-agent")
            print("\n" + "="*60)
            print("ENHANCED SEQUENCE EXECUTION WITH DETAILED TRACKING")
            print("="*60)
            
            # Execute the sequence
            print("\nExecuting sequence...")
            result = await session.call_tool(
                "execute_sequence",
                arguments={
                    "items": items,
                    "stop_on_error": True,
                    "include_detailed_results": True
                }
            )
            
            # Parse the result
            if result.content and len(result.content) > 0:
                data = json.loads(result.content[0].text)
                
                # Display execution plan
                print("\n📋 EXECUTION PLAN:")
                print("-" * 50)
                plan = data.get("execution_plan", {})
                print(f"Total steps to execute: {plan.get('total_steps', 0)}")
                for step in plan.get("steps", []):
                    print(f"  Step {step['step']}: {step['tool_name']} - {step['description']}")
                
                # Display step results as they would appear in a stream
                print("\n🚀 EXECUTING STEPS:")
                print("-" * 50)
                
                step_results = data.get("step_results", [])
                for step_result in step_results:
                    print_step_info(step_result)
                    
                    # Show a sample of the result content if available
                    if "result" in step_result and "result" in step_result["result"]:
                        result_data = step_result["result"]["result"]
                        if isinstance(result_data, dict) and "content" in result_data:
                            content = result_data["content"]
                            if isinstance(content, list) and len(content) > 0:
                                # Show truncated content for readability
                                content_str = str(content[0])
                                if len(content_str) > 100:
                                    content_str = content_str[:100] + "..."
                                print(f"  Result: {content_str}")
                
                # Display execution summary
                print("\n📊 EXECUTION SUMMARY:")
                print("-" * 50)
                summary = data.get("execution_summary", {})
                print(f"Total steps planned:    {summary.get('total_steps', 0)}")
                print(f"Steps executed:         {summary.get('executed_steps', 0)}")
                print(f"Successful steps:       {summary.get('successful_steps', 0)}")
                print(f"Failed steps:           {summary.get('failed_steps', 0)}")
                print(f"Total duration:         {summary.get('total_duration_ms', 0)}ms")
                print(f"Started at:             {format_timestamp(summary.get('started_at', ''))}")
                print(f"Completed at:           {format_timestamp(summary.get('completed_at', ''))}")
                
                # Final status
                print(f"\n🏁 FINAL STATUS: {data.get('status', 'unknown').upper()}")
                
            else:
                print("No result received from execute_sequence")


async def main():
    """Main entry point"""
    try:
        await run_sequence_demo()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())