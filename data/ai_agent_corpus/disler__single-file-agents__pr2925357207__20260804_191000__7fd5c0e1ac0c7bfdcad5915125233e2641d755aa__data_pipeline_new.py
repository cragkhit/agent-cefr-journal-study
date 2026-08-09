#!/usr/bin/env python3

"""
Data processing pipeline implementation for the pipeline architecture.
This module provides a specific implementation of the pipeline manager for data processing.
"""

from pipeline_manager.pipeline_manager import PipelineManager

class DataProcessingPipeline(PipelineManager):
    """Specific implementation of a data processing pipeline."""
    
    def __init__(self, name="Data Processing Pipeline"):
        """Initialize the data processing pipeline."""
        super().__init__(name)
    
    def _execute_first_stage(self, input_stage):
        """Execute the input stage of the pipeline."""
        # This implementation assumes the input stage has load_data and validate_data methods
        result = input_stage.load_data(self.input_source, self.input_source_type)
        
        if result["metadata"]["status"] != "error":
            if hasattr(self, "required_fields"):
                result = input_stage.validate_data(required_fields=self.required_fields)
        
        return result
    
    def _execute_stage(self, stage_instance, previous_result):
        """Execute a stage with the result from the previous stage."""
        # Determine which stage we're executing based on the instance type
        if hasattr(stage_instance, "process"):
            # Processing stage
            result = stage_instance.process(previous_result)
            
            # Execute additional processing methods if configured
            if hasattr(self, "processing_config"):
                config = self.processing_config
                
                # Calculate statistics if configured
                if config.get("calculate_statistics"):
                    result = stage_instance.calculate_statistics(
                        numeric_fields=config.get("numeric_fields")
                    )
                
                # Apply filters if configured
                if "filters" in config:
                    for filter_config in config["filters"]:
                        result = stage_instance.filter_data(
                            filter_config["filter_func"],
                            filter_config.get("description")
                        )
                
                # Apply transformations if configured
                if "transformations" in config:
                    result = stage_instance.transform_fields(
                        config["transformations"],
                        config.get("transformation_description")
                    )
            
            # Finalize the processing stage
            result = stage_instance.finalize()
            
        elif hasattr(stage_instance, "prepare"):
            # Output stage
            result = stage_instance.prepare(previous_result)
            
            # Execute additional output methods if configured
            if hasattr(self, "output_config"):
                config = self.output_config
                
                # Format as summary if configured
                if config.get("format_summary", False):
                    result = stage_instance.format_as_summary()
                
                # Format as detailed report if configured
                if config.get("format_detailed", False):
                    result = stage_instance.format_as_detailed_report()
                
                # Save to file if configured
                if "save_to_file" in config:
                    for save_config in config["save_to_file"]:
                        result = stage_instance.save_to_file(
                            output_format=save_config.get("format", "json"),
                            output_dir=save_config.get("dir", "./output"),
                            filename=save_config.get("filename")
                        )
                
                # Print results if configured
                if config.get("print_results"):
                    result = stage_instance.print_results(
                        output_type=config.get("print_output_type", "summary")
                    )
            
            # Finalize the output stage
            result = stage_instance.finalize()
            
        else:
            # Unknown stage type
            raise ValueError(f"Unknown stage type: {type(stage_instance).__name__}")
        
        return result
    
    def configure_input(self, source, source_type="json", required_fields=None):
        """
        Configure the input stage.
        
        Args:
            source: Path to the data file or raw data
            source_type: Type of data source (json, csv, raw)
            required_fields: List of required field names for validation
        """
        self.input_source = source
        self.input_source_type = source_type
        if required_fields:
            self.required_fields = required_fields
    
    def configure_processing(self, config):
        """
        Configure the processing stage.
        
        Args:
            config: Dictionary with processing configuration
        """
        self.processing_config = config
    
    def configure_output(self, config):
        """
        Configure the output stage.
        
        Args:
            config: Dictionary with output configuration
        """
        self.output_config = config
