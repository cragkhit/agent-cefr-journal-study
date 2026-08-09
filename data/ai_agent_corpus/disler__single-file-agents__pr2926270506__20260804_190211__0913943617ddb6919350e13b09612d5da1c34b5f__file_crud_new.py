#!/usr/bin/env python3

"""
Molecular file CRUD operations for the Atomic/Composable Architecture implementation of the file editor agent.
This module combines atomic components to provide file CRUD capabilities.
"""

import sys
import os

# Add the parent directory to the Python path to enable absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from atom.file_operations import read_file, write_file, replace_in_file, insert_in_file, undo_edit, FileOperationResult
from atom.logging.console import log_info, log_error

class FileCRUD:
    """
    File CRUD operations that combine atomic components to provide file manipulation capabilities.
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
        log_info("file_crud", f"Reading file {path} with range {start_line}-{end_line}")
        
        result = read_file(path, start_line, end_line)
        
        if result.success:
            log_info("file_crud", f"Successfully read file {path}")
        else:
            log_error("file_crud", f"Failed to read file {path}: {result.message}")
            
        return result
    
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
        log_info("file_crud", f"Writing to file {path}")
        
        result = write_file(path, content)
        
        if result.success:
            log_info("file_crud", f"Successfully wrote to file {path}")
        else:
            log_error("file_crud", f"Failed to write to file {path}: {result.message}")
            
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
        log_info("file_crud", f"Replacing text in file {path}")
        
        result = replace_in_file(path, old_str, new_str)
        
        if result.success:
            log_info("file_crud", f"Successfully replaced text in file {path}")
        else:
            log_error("file_crud", f"Failed to replace text in file {path}: {result.message}")
            
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
        log_info("file_crud", f"Inserting text at line {insert_line} in file {path}")
        
        result = insert_in_file(path, insert_line, new_str)
        
        if result.success:
            log_info("file_crud", f"Successfully inserted text at line {insert_line} in file {path}")
        else:
            log_error("file_crud", f"Failed to insert text at line {insert_line} in file {path}: {result.message}")
            
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
        log_info("file_crud", f"Creating file {path}")
        
        return FileCRUD.write(path, content)
    
    @staticmethod
    def undo(path: str) -> FileOperationResult:
        """
        Undo the last edit to a file.
        
        Args:
            path: The path to the file whose last edit should be undone
            
        Returns:
            FileOperationResult with message about undo functionality
        """
        log_info("file_crud", f"Undoing last edit to file {path}")
        
        result = undo_edit(path)
        
        if result.success:
            log_info("file_crud", f"Successfully undid last edit to file {path}")
        else:
            log_error("file_crud", f"Failed to undo last edit to file {path}: {result.message}")
            
        return result
    
    @staticmethod
    def handle_tool_use(tool_use: dict) -> dict:
        """
        Handle a tool use request from Claude.
        
        Args:
            tool_use: The tool use request from Claude
            
        Returns:
            Dictionary with result or error to send back to Claude
        """
        command = tool_use.get("command")
        path = tool_use.get("path")
        
        log_info("file_crud", f"Handling tool use request: {command} on {path}")
        
        if not command:
            error_msg = "No command specified in tool use request"
            log_error("file_crud", error_msg)
            return {"error": error_msg}
            
        if not path and command != "undo_edit":
            error_msg = "No path specified in tool use request"
            log_error("file_crud", error_msg)
            return {"error": error_msg}
            
        result = None
        
        try:
            if command == "view":
                view_range = tool_use.get("view_range")
                start_line = None
                end_line = None
                
                if view_range:
                    start_line, end_line = view_range
                    
                result = FileCRUD.read(path, start_line, end_line)
                
            elif command == "str_replace":
                old_str = tool_use.get("old_str")
                new_str = tool_use.get("new_str")
                
                if old_str is None:
                    return {"error": "Missing 'old_str' parameter for str_replace command"}
                    
                if new_str is None:
                    return {"error": "Missing 'new_str' parameter for str_replace command"}
                    
                result = FileCRUD.replace(path, old_str, new_str)
                
            elif command == "create":
                file_text = tool_use.get("file_text", "")
                result = FileCRUD.create(path, file_text)
                
            elif command == "insert":
                insert_line = tool_use.get("insert_line")
                new_str = tool_use.get("new_str")
                
                if insert_line is None:
                    return {"error": "Missing 'insert_line' parameter for insert command"}
                    
                if new_str is None:
                    return {"error": "Missing 'new_str' parameter for insert command"}
                    
                result = FileCRUD.insert(path, insert_line, new_str)
                
            elif command == "undo_edit":
                result = FileCRUD.undo(path)
                
            else:
                error_msg = f"Unknown command: {command}"
                log_error("file_crud", error_msg)
                return {"error": error_msg}
                
            # Convert the result to a response for Claude
            if result.success:
                return {"result": result.data if result.data is not None else result.message}
            else:
                return {"error": result.message}
                
        except Exception as e:
            error_msg = f"Error handling tool use: {str(e)}"
            log_error("file_crud", error_msg, exc_info=True)
            return {"error": error_msg}
