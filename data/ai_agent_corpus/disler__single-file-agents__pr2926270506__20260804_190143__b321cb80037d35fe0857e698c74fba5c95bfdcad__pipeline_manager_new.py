#!/usr/bin/env python3

"""
Pipeline manager for the Pipeline Architecture implementation of the file editor agent.
This module provides the base pipeline infrastructure.
"""

from typing import Dict, Any, List, Callable, Optional
from rich.console import Console

# Initialize rich console
console = Console()

class PipelineStage:
    """
    Interface for pipeline stages.
    All stages must implement the process method.
    """
    
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the input data and return the result.
        
        Args:
            data: The input data to process
            
        Returns:
            The processed data
        """
        raise NotImplementedError("Pipeline stages must implement the process method")

class Pipeline:
    """
    Base pipeline class that manages the flow of data through stages.
    """
    
    def __init__(self, name: str):
        """
        Initialize a pipeline.
        
        Args:
            name: The name of the pipeline
        """
        self.name = name
        self.stages: Dict[str, PipelineStage] = {}
        self.stage_order: List[str] = []
        console.log(f"[pipeline] Initialized pipeline: {name}")
    
    def add_stage(self, name: str, stage: PipelineStage) -> None:
        """
        Add a stage to the pipeline.
        
        Args:
            name: The name of the stage
            stage: The stage to add
        """
        self.stages[name] = stage
        self.stage_order.append(name)
        console.log(f"[pipeline] Added stage: {name}")
    
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process data through the pipeline.
        
        Args:
            data: The input data to process
            
        Returns:
            The processed data after passing through all stages
        """
        console.log(f"[pipeline] Starting pipeline: {self.name}")
        
        current_data = data
        
        for stage_name in self.stage_order:
            stage = self.stages[stage_name]
            console.log(f"[pipeline] Processing stage: {stage_name}")
            
            try:
                current_data = stage.process(current_data)
                
                # Check if there was an error in the stage
                if "error" in current_data:
                    console.log(f"[pipeline] Error in stage {stage_name}: {current_data['error']}")
                    # Continue to the next stage, which may handle the error
                
            except Exception as e:
                console.log(f"[pipeline] Exception in stage {stage_name}: {str(e)}")
                current_data = {"error": f"Exception in stage {stage_name}: {str(e)}"}
        
        console.log(f"[pipeline] Completed pipeline: {self.name}")
        return current_data
