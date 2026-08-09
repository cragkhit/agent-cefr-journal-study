#!/usr/bin/env python3

"""
Logger utility for the Layered Architecture implementation of the file editor agent.
"""

from rich.console import Console

# Initialize rich console
console = Console()

# Create a logger instance for the application
app_logger = "file_editor_app"

class Logger:
    """
    Logger utility class for the application.
    """
    
    @staticmethod
    def info(logger_name: str, message: str) -> None:
        """
        Log an info message.
        
        Args:
            logger_name: Name of the logger
            message: Message to log
        """
        console.log(f"[{logger_name}] [info] {message}")
    
    @staticmethod
    def warning(logger_name: str, message: str) -> None:
        """
        Log a warning message.
        
        Args:
            logger_name: Name of the logger
            message: Message to log
        """
        console.log(f"[{logger_name}] [warning] {message}")
    
    @staticmethod
    def error(logger_name: str, message: str, exc_info: bool = False) -> None:
        """
        Log an error message.
        
        Args:
            logger_name: Name of the logger
            message: Message to log
            exc_info: Whether to include exception info
        """
        console.log(f"[{logger_name}] [error] {message}")
        
        if exc_info:
            import traceback
            console.log(traceback.format_exc())
