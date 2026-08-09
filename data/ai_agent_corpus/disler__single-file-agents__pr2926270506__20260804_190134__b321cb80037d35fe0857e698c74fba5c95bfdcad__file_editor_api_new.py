#!/usr/bin/env python3

"""
API layer for the Layered Architecture implementation of the file editor agent.
"""

import traceback
from typing import Dict, Any

import sys
import os

# Add the parent directory to the Python path to enable absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.file_service import FileService
from models.tool_models import ToolUseRequest
from utils.logger import Logger, app_logger

class FileEditorAPI:
    """
    API for file editor operations.
    """
    
    @staticmethod
    def handle_tool_use(tool_use: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle text editor tool use from Claude.

        Args:
            tool_use: The tool use request from Claude

        Returns:
            Dictionary with result or error to send back to Claude
        """
        try:
            # Convert the tool use dictionary to a ToolUseRequest object
            request = ToolUseRequest.from_dict(tool_use)
            
            Logger.info(app_logger, f"Received command: {request.command}, path: {request.path}")

            if not request.command:
                error_msg = "No command specified in tool use request"
                Logger.error(app_logger, error_msg)
                return {"error": error_msg}

            if not request.path and request.command != "undo_edit":  # undo_edit might not need a path
                error_msg = "No path specified in tool use request"
                Logger.error(app_logger, error_msg)
                return {"error": error_msg}

            result = None
            
            if request.command == "view":
                view_range = request.kwargs.get("view_range")
                Logger.info(app_logger, f"Calling view_file with view_range: {view_range}")
                result = FileService.view_file(request.path, view_range)

            elif request.command == "str_replace":
                old_str = request.kwargs.get("old_str")
                new_str = request.kwargs.get("new_str")
                Logger.info(app_logger, "Calling str_replace")
                result = FileService.str_replace(request.path, old_str, new_str)

            elif request.command == "create":
                file_text = request.kwargs.get("file_text")
                Logger.info(app_logger, "Calling create_file")
                result = FileService.create_file(request.path, file_text)

            elif request.command == "insert":
                insert_line = request.kwargs.get("insert_line")
                new_str = request.kwargs.get("new_str")
                Logger.info(app_logger, f"Calling insert_text at line: {insert_line}")
                result = FileService.insert_text(request.path, insert_line, new_str)

            elif request.command == "undo_edit":
                Logger.info(app_logger, "Calling undo_edit")
                result = FileService.undo_edit(request.path)

            else:
                error_msg = f"Unknown command: {request.command}"
                Logger.error(app_logger, error_msg)
                return {"error": error_msg}
            
            # Convert the result to a response for Claude
            return result.to_response()
                
        except Exception as e:
            error_msg = f"Error handling tool use: {str(e)}"
            Logger.error(app_logger, error_msg, exc_info=True)
            return {"error": error_msg}
