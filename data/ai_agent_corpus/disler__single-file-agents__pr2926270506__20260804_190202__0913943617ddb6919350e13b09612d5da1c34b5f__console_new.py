#!/usr/bin/env python3

"""
Atomic console logging utilities for the Atomic/Composable Architecture.
These are the most basic building blocks for console logging.
"""

import traceback
from rich.console import Console

# Initialize rich console
console = Console()

def log_info(component: str, message: str) -> None:
    """
    Log an informational message.

    Args:
        component: The component that is logging the message
        message: The message to log
    """
    console.log(f"[{component}] {message}")

def log_warning(component: str, message: str) -> None:
    """
    Log a warning message.

    Args:
        component: The component that is logging the message
        message: The message to log
    """
    console.log(f"[{component}] [warning] {message}")
    console.print(f"[yellow]{message}[/yellow]")

def log_error(component: str, message: str, exc_info: bool = False) -> None:
    """
    Log an error message.

    Args:
        component: The component that is logging the message
        message: The message to log
        exc_info: Whether to include exception info
    """
    console.log(f"[{component}] [error] {message}")
    console.print(f"[red]{message}[/red]")
    
    if exc_info:
        console.log(traceback.format_exc())
