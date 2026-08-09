#!/usr/bin/env python3
"""
Python MCP Real-time Progress Streaming Example
Demonstrates the execute_sequence tool with real-time progress notifications
"""

import asyncio
import json
import sys
from datetime import datetime
from typing import Dict, Any
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class ProgressTracker:
    """Tracks progress of sequence execution"""
    def __init__(self):
        self.total_steps = 0
        self.completed_steps = 0
        self.current_step = None
        self.start_time = None
        
    def update_from_notification(self, data: Dict[str, Any]):
        """Update progress from notification data"""
        notification_type = data.get("type")
        
        if notification_type == "execution_plan":
            self.total_steps = data.get("total_steps", 0)
            
        elif notification_type == "sequence_start":
            self.start_time = data.get("started_at")
            
        elif notification_type == "step_complete":
            self.completed_steps += 1


def format_progress_bar(current: int, total: int, width: int = 30) -> str:
    """Create a text progress bar"""
    if total == 0:
        return "[" + " " * width + "]"
    
    filled = int((current / total) * width)
    bar = "█" * filled + "░" * (width - filled)
    percentage = (current / total) * 100
    return f"[{bar}] {percentage:.0f}%"


def print_notification(data: Dict[str, Any], tracker: ProgressTracker):
    """Print formatted notification based on type"""
    notification_type = data.get("type", "unknown")
    
    if notification_type == "execution_plan":
        print("\n📋 EXECUTION PLAN")
        print("=" * 60)
        print(f"Total steps: {data.get('total_steps', 0)}")
        for step in data.get('steps', []):
            print(f"  {step['step']}. {step['description']}")
        print("=" * 60)
        
    elif notification_type == "sequence_start":
        print(f"\n🚀 Starting sequence execution at {data.get('started_at', 'unknown')}")
        print("-" * 60)
        
    elif notification_type == "step_start":
        step_num = data.get('step', 0)
        total = data.get('total_steps', 0)
        tool_name = data.get('tool_name', 'unknown')
        description = data.get('description', '')
        
        print(f"\n⏳ Step {step_num}/{total}: {tool_name}")
        print(f"   {description}")
        
    elif notification_type == "step_complete":
        step_num = data.get('step', 0)
        total = data.get('total_steps', 0)
        status = data.get('status', 'unknown')
        duration = data.get('duration_ms', 0)
        
        status_icon = "✅" if status == "success" else "❌"
        progress_bar = format_progress_bar(step_num, total)
        
        print(f"{status_icon} Step {step_num}/{total} completed in {duration}ms")
        print(f"   {progress_bar}")
        
        # Print result summary if available
        result_summary = data.get('result_summary', {})
        if isinstance(result_summary, dict) and result_summary.get('status') != 'success':
            error = result_summary.get('error', 'Unknown error')
            print(f"   ⚠️  Error: {error}")
            
    elif notification_type == "group_start":
        group_name = data.get('group_name', 'unknown')
        print(f"\n📁 Starting group: {group_name}")
        
    elif notification_type == "group_complete":
        group_name = data.get('group_name', 'unknown')
        had_errors = data.get('had_errors', False)
        status = "✅ completed" if not had_errors else "⚠️  completed with errors"
        print(f"📁 Group '{group_name}' {status}")
        
    elif notification_type == "sequence_complete":
        print("\n" + "=" * 60)
        print("🏁 SEQUENCE COMPLETE")
        print("=" * 60)
        
        summary = data.get('execution_summary', {})
        print(f"Status: {data.get('status', 'unknown').upper()}")
        print(f"Total steps: {summary.get('total_steps', 0)}")
        print(f"Executed: {summary.get('executed_steps', 0)}")
        print(f"Successful: {summary.get('successful_steps', 0)}")
        print(f"Failed: {summary.get('failed_steps', 0)}")
        print(f"Duration: {summary.get('total_duration_ms', 0)}ms")


async def run_streaming_demo():
    """Run a demo showing real-time progress streaming"""
    
    # Define a sequence that demonstrates various features
    sequence = [
        {
            "tool_name": "get_applications",
            "arguments": {}
        },
        {
            "tool_name": "delay",
            "arguments": {"delay_ms": 500}
        },
        {
            "tool_name": "open_application",
            "arguments": {"app_name": "notepad"}
        },
        {
            "tool_name": "delay",
            "arguments": {"delay_ms": 1500}
        },
        {
            "tool_name": "type_into_element",
            "arguments": {
                "selector": "role:document",
                "text_to_type": "Real-time progress streaming with MCP!"
            }
        },
        {
            "tool_name": "delay",
            "arguments": {"delay_ms": 1000}
        },
        {
            "tool_name": "type_into_element",
            "arguments": {
                "selector": "role:document", 
                "text_to_type": "\n\nThis text appears with live progress updates.",
                "clear_before_typing": False
            }
        }
    ]
    
    # Convert to execute_sequence format
    items = []
    for tool in sequence:
        items.append({
            "tool_name": tool["tool_name"],
            "arguments": tool.get("arguments", {}),
            "continue_on_error": False,
            "delay_ms": 0
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
            
            print("🔌 Connected to terminator-mcp-agent")
            print("\n" + "🎬 REAL-TIME PROGRESS STREAMING DEMO " + "🎬")
            
            # Set up progress tracker
            tracker = ProgressTracker()
            
            # Set up notification handler for logging messages
            def handle_logging(level: str, data: Any):
                """Handle logging notifications"""
                # The progress data is sent as the log data
                if isinstance(data, dict):
                    tracker.update_from_notification(data)
                    print_notification(data, tracker)
            
            # Register the notification handler
            session.set_logging_handler(handle_logging)
            
            # Execute the sequence
            print("\n📡 Executing sequence with real-time progress...")
            
            try:
                result = await session.call_tool(
                    "execute_sequence",
                    arguments={
                        "items": items,
                        "stop_on_error": True,
                        "include_detailed_results": True
                    }
                )
                
                # The final result is still available if needed
                if result.content and len(result.content) > 0:
                    final_data = json.loads(result.content[0].text)
                    
                    # Show final status
                    print(f"\n✨ Final status: {final_data.get('status', 'unknown').upper()}")
                    
            except Exception as e:
                print(f"\n❌ Error executing sequence: {e}")


async def main():
    """Main entry point"""
    try:
        await run_streaming_demo()
    except KeyboardInterrupt:
        print("\n\n🛑 Demo interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("🚀 Starting MCP Real-time Progress Streaming Demo")
    print("This demo shows how execute_sequence sends progress notifications in real-time")
    print("-" * 70)
    asyncio.run(main())