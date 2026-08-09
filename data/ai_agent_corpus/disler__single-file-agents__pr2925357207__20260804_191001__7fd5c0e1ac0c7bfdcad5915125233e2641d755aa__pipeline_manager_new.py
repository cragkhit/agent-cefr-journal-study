#!/usr/bin/env python3

"""
Pipeline manager for the pipeline architecture.
This module coordinates the execution of the pipeline stages.
"""

from datetime import datetime

class PipelineManager:
    """Manager for coordinating pipeline stages."""
    
    def __init__(self, name="Data Processing Pipeline"):
        """Initialize the pipeline manager."""
        self.name = name
        self.stages = []
        self.results = {}
        self.metadata = {
            "pipeline_name": name,
            "status": "initialized",
            "started_at": None,
            "completed_at": None,
            "errors": []
        }
    
    def add_stage(self, stage_name, stage_instance):
        """
        Add a stage to the pipeline.
        
        Args:
            stage_name: Name of the stage
            stage_instance: Instance of the stage class
        """
        self.stages.append({
            "name": stage_name,
            "instance": stage_instance,
            "status": "pending"
        })
    
    def run(self):
        """
        Run the pipeline by executing all stages in sequence.
        
        Returns:
            dict: Pipeline results including data and metadata
        """
        self.metadata["started_at"] = datetime.now().isoformat()
        self.metadata["status"] = "running"
        
        print(f"\n=== Starting Pipeline: {self.name} ===")
        
        # Execute each stage
        for i, stage in enumerate(self.stages):
            stage_name = stage["name"]
            stage_instance = stage["instance"]
            
            print(f"\n--- Stage {i+1}: {stage_name} ---")
            
            try:
                # Execute the stage
                if i == 0:
                    # First stage doesn't take input from previous stage
                    result = self._execute_first_stage(stage_instance)
                else:
                    # Pass result from previous stage
                    previous_result = self.results[self.stages[i-1]["name"]]
                    result = self._execute_stage(stage_instance, previous_result)
                
                # Store the result
                self.results[stage_name] = result
                
                # Update stage status
                stage["status"] = result["metadata"]["status"]
                
                # Check for errors
                if result["metadata"]["status"] in ["error", "skipped"]:
                    print(f"Stage {stage_name} {result['metadata']['status']}")
                    for error in result["metadata"].get("errors", []):
                        print(f"  Error: {error}")
                    
                    # Add errors to pipeline metadata
                    self.metadata["errors"].append({
                        "stage": stage_name,
                        "errors": result["metadata"].get("errors", [])
                    })
                else:
                    print(f"Stage {stage_name} completed successfully")
            
            except Exception as e:
                # Handle unexpected errors
                error_message = f"Unexpected error in stage {stage_name}: {str(e)}"
                print(f"  Error: {error_message}")
                
                # Update stage status
                stage["status"] = "error"
                
                # Add error to pipeline metadata
                self.metadata["errors"].append({
                    "stage": stage_name,
                    "errors": [error_message]
                })
        
        # Update pipeline status
        self.metadata["completed_at"] = datetime.now().isoformat()
        if self.metadata["errors"]:
            self.metadata["status"] = "completed_with_errors"
        else:
            self.metadata["status"] = "completed"
        
        # Calculate total execution time
        start_time = datetime.fromisoformat(self.metadata["started_at"])
        end_time = datetime.fromisoformat(self.metadata["completed_at"])
        execution_time = (end_time - start_time).total_seconds()
        self.metadata["execution_time_seconds"] = execution_time
        
        print(f"\n=== Pipeline {self.name} {self.metadata['status']} ===")
        print(f"Total execution time: {execution_time:.2f} seconds")
        
        return self._create_pipeline_result()
    
    def _execute_first_stage(self, stage_instance):
        """Execute the first stage of the pipeline."""
        # This method should be overridden in subclasses to provide
        # specific implementation for the first stage
        raise NotImplementedError("Subclasses must implement _execute_first_stage")
    
    def _execute_stage(self, stage_instance, previous_result):
        """Execute a stage with the result from the previous stage."""
        # This method should be overridden in subclasses to provide
        # specific implementation for subsequent stages
        raise NotImplementedError("Subclasses must implement _execute_stage")
    
    def get_final_result(self):
        """
        Get the result from the final stage of the pipeline.
        
        Returns:
            dict: Result from the final stage
        """
        if not self.stages:
            return None
        
        final_stage_name = self.stages[-1]["name"]
        if final_stage_name in self.results:
            return self.results[final_stage_name]
        
        return None
    
    def _create_pipeline_result(self):
        """Create a result dictionary for the entire pipeline."""
        # Get the final result
        final_result = self.get_final_result()
        
        # Create pipeline result
        pipeline_result = {
            "metadata": self.metadata,
            "stages": [{
                "name": stage["name"],
                "status": stage["status"]
            } for stage in self.stages]
        }
        
        # Add data from final stage if available
        if final_result and "data" in final_result:
            pipeline_result["data"] = final_result["data"]
        
        # Add analysis from final stage if available
        if final_result and "analysis" in final_result:
            pipeline_result["analysis"] = final_result["analysis"]
        
        return pipeline_result
