#!/usr/bin/env python3

"""
File editor pipeline for the Pipeline Architecture implementation of the file editor agent.
This module configures the pipeline for file editing operations.
"""

from typing import Dict, Any
from rich.console import Console

import sys
import os

# Add the parent directory to the Python path to enable absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline_manager.pipeline_manager import Pipeline
from steps.input_stage import InputStage
from steps.command_router import CommandRouter
from steps.output_stage import OutputStage

# Initialize rich console
console = Console()

class FileEditorPipeline:
    """
    File editor pipeline that configures and manages the pipeline for file editing operations.
    """
    
    def __init__(self):
        """
        Initialize the file editor pipeline.
        """
        # Create pipeline stages
        self.input_stage = InputStage()
        self.command_router = CommandRouter()
        self.output_stage = OutputStage()
        
        # Create and configure pipeline
        self.pipeline = Pipeline("File Editor Pipeline")
        
        # Add stages
        self.pipeline.add_stage("input", self.input_stage)
        self.pipeline.add_stage("command_router", self.command_router)
        self.pipeline.add_stage("output", self.output_stage)
        
        console.log("[file_editor_pipeline] Initialized file editor pipeline")
    
    def handle_tool_use(self, tool_use: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle text editor tool use from Claude.

        Args:
            tool_use: The tool use request from Claude

        Returns:
            Dictionary with result or error to send back to Claude
        """
        console.log(f"[file_editor_pipeline] Handling tool use: {tool_use.get('command', 'unknown')}")
        
        # Process the tool use through the pipeline
        result = self.pipeline.process(tool_use)
        
        console.log(f"[file_editor_pipeline] Tool use result: {result}")
        return result
