#!/usr/bin/env python3

"""
Molecular file reader for the Atomic/Composable Architecture implementation of the file editor agent.
This module combines atomic components to provide file reading capabilities.
"""

import sys
import os

# Add the parent directory to the Python path to enable absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from atom.file_operations import read_file, FileOperationResult
from atom.logging.console import log_info, log_error

class FileReader:
    """
    File reader that combines atomic components to provide file reading capabilities.
    """
    
    @staticmethod
    def read(path: str, start_line: int = None, end_line: int = None) -> FileOperationResult:
        """
        Read the contents of a file.

        Args:
            path: The path to the file to read
            start_line: Optional start line (1-indexed)
            end_line: Optional end line (1-indexed, -1 for end of file)

        Returns:
            FileOperationResult with content or error message
        """
        log_info("file_reader", f"Reading file {path} with range {start_line}-{end_line}")
        
        # Use the atomic read_file function
        result = read_file(path, start_line, end_line)
        
        if result.success:
            log_info("file_reader", f"Successfully read file {path}")
        else:
            log_error("file_reader", f"Failed to read file {path}: {result.message}")
            
        return result
    
    @staticmethod
    def view_file(path: str, view_range=None) -> FileOperationResult:
        """
        View the contents of a file with optional range.

        Args:
            path: The path to the file to view
            view_range: Optional tuple of (start_line, end_line)

        Returns:
            FileOperationResult with content or error message
        """
        start_line = None
        end_line = None
        
        if view_range:
            start_line, end_line = view_range
            
        log_info("file_reader", f"Viewing file {path} with range {start_line}-{end_line}")
        
        return FileReader.read(path, start_line, end_line)
