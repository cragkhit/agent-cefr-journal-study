#!/usr/bin/env python3

"""
Molecular file writer for the Atomic/Composable Architecture implementation of the file editor agent.
This module combines atomic components to provide file writing capabilities.
"""

import sys
import os

# Add the parent directory to the Python path to enable absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from atom.file_operations import write_file, replace_in_file, insert_in_file, FileOperationResult
from atom.logging.console import log_info, log_error

class FileWriter:
    """
    File writer that combines atomic components to provide file writing capabilities.
    """
    
    @staticmethod
    def write(path: str, content: str) -> FileOperationResult:
        """
        Write content to a file.
        
        Args:
            path: The path to the file to write
            content: The content to write to the file
            
        Returns:
            FileOperationResult with result or error message
        """
        log_info("file_writer", f"Writing to file {path}")
        
        # Use the atomic write_file function
        result = write_file(path, content)
        
        if result.success:
            log_info("file_writer", f"Successfully wrote to file {path}")
        else:
            log_error("file_writer", f"Failed to write to file {path}: {result.message}")
            
        return result
    
    @staticmethod
    def replace(path: str, old_str: str, new_str: str) -> FileOperationResult:
        """
        Replace a string in a file.
        
        Args:
            path: The path to the file to modify
            old_str: The string to replace
            new_str: The string to replace with
            
        Returns:
            FileOperationResult with result or error message
        """
        log_info("file_writer", f"Replacing text in file {path}")
        
        # Use the atomic replace_in_file function
        result = replace_in_file(path, old_str, new_str)
        
        if result.success:
            log_info("file_writer", f"Successfully replaced text in file {path}")
        else:
            log_error("file_writer", f"Failed to replace text in file {path}: {result.message}")
            
        return result
    
    @staticmethod
    def insert(path: str, insert_line: int, new_str: str) -> FileOperationResult:
        """
        Insert text at a specific line in a file.
        
        Args:
            path: The path to the file to modify
            insert_line: The line number after which to insert the text (1-indexed)
            new_str: The text to insert
            
        Returns:
            FileOperationResult with result or error message
        """
        log_info("file_writer", f"Inserting text at line {insert_line} in file {path}")
        
        # Use the atomic insert_in_file function
        result = insert_in_file(path, insert_line, new_str)
        
        if result.success:
            log_info("file_writer", f"Successfully inserted text at line {insert_line} in file {path}")
        else:
            log_error("file_writer", f"Failed to insert text at line {insert_line} in file {path}: {result.message}")
            
        return result
    
    @staticmethod
    def create(path: str, content: str) -> FileOperationResult:
        """
        Create a new file with the specified content.
        
        Args:
            path: The path to the file to create
            content: The content to write to the file
            
        Returns:
            FileOperationResult with result or error message
        """
        log_info("file_writer", f"Creating file {path}")
        
        # Use the atomic write_file function
        return FileWriter.write(path, content)
