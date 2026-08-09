#!/usr/bin/env python3

"""
Output stage for the Pipeline Architecture implementation of the file editor agent.
This stage is responsible for formatting the results for Claude.
"""

import traceback
from typing import Dict, Any, Optional, List, Union

import sys
import os

# Add the parent directory to the Python path to enable absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.utilities import console, FileOperationResult

class OutputStage:
    """
    Output stage for the file editor pipeline.
    Responsible for formatting the results for Claude.
    """
    
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the data from the previous stage by formatting the results for Claude.
        
        Args:
            data: The data from the previous stage containing the operation result
            
        Returns:
            Dictionary with the formatted result for Claude
        """
        try:
            # Check if there was an error in the previous stages
            if "error" in data:
                console.log(f"[output_stage] Error from previous stage: {data['error']}")
                return {"error": data["error"], "stage": "output"}
                
            result = data.get("result")
            if not result:
                error_msg = "No result found in data from previous stage"
                console.log(f"[output_stage] Error: {error_msg}")
                return {"error": error_msg, "stage": "output"}
                
            console.log(f"[output_stage] Formatting result for Claude")
            
            # Format the result for Claude
            if isinstance(result, FileOperationResult):
                formatted_result = result.to_response()
            else:
                # If the result is not a FileOperationResult, return it as is
                formatted_result = result
                
            console.log(f"[output_stage] Formatted result: {formatted_result}")
            
            return formatted_result
                
        except Exception as e:
            error_msg = f"Error in output stage: {str(e)}"
            console.print(f"[red]{error_msg}[/red]")
            console.log(f"[output_stage] Error: {str(e)}")
            console.log(traceback.format_exc())
            return {"error": error_msg, "stage": "output"}
