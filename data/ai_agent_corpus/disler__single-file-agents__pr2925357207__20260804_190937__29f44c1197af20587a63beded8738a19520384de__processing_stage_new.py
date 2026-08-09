#!/usr/bin/env python3

"""
Processing stage for the pipeline architecture.
This stage is responsible for transforming and analyzing the data.
"""

import statistics
from datetime import datetime

class ProcessingStage:
    """Processing stage for data transformation and analysis."""
    
    def __init__(self):
        """Initialize the processing stage."""
        self.data = None
        self.metadata = {
            "stage": "processing",
            "status": "initialized",
            "errors": [],
            "processing_steps": []
        }
    
    def process(self, input_result):
        """
        Process the data from the input stage.
        
        Args:
            input_result: Result from the input stage
        
        Returns:
            dict: Stage result with processed data and metadata
        """
        # Check if input stage had errors
        if input_result["metadata"]["status"] in ["error", "validation_failed"]:
            self.metadata["status"] = "skipped"
            self.metadata["errors"].append("Input stage had errors, processing skipped")
            return self._create_result()
        
        # Get data from input stage
        self.data = input_result["data"]
        self.metadata["input_metadata"] = input_result["metadata"]
        
        # Initialize processing
        self.metadata["status"] = "processing"
        self.metadata["started_at"] = datetime.now().isoformat()
        
        return self._create_result()
    
    def calculate_statistics(self, numeric_fields=None):
        """
        Calculate statistics for numeric fields in the data.
        
        Args:
            numeric_fields: List of field names to calculate statistics for
        
        Returns:
            dict: Stage result with data and metadata
        """
        if self.data is None:
            self.metadata["status"] = "error"
            self.metadata["errors"].append("No data to process")
            return self._create_result()
        
        try:
            # Determine fields to analyze
            if numeric_fields is None:
                # Try to automatically detect numeric fields
                if isinstance(self.data, list) and len(self.data) > 0:
                    sample = self.data[0]
                    numeric_fields = [
                        field for field, value in sample.items()
                        if isinstance(value, (int, float)) or (
                            isinstance(value, str) and value.replace('.', '', 1).isdigit()
                        )
                    ]
            
            # Calculate statistics
            stats = {}
            if isinstance(self.data, list) and numeric_fields:
                for field in numeric_fields:
                    try:
                        # Extract numeric values
                        values = []
                        for item in self.data:
                            if field in item:
                                value = item[field]
                                if isinstance(value, (int, float)):
                                    values.append(value)
                                elif isinstance(value, str) and value.replace('.', '', 1).isdigit():
                                    values.append(float(value))
                        
                        # Calculate statistics if we have values
                        if values:
                            field_stats = {
                                "count": len(values),
                                "min": min(values),
                                "max": max(values),
                                "sum": sum(values),
                                "mean": statistics.mean(values),
                                "median": statistics.median(values)
                            }
                            
                            # Add standard deviation if we have enough values
                            if len(values) > 1:
                                field_stats["std_dev"] = statistics.stdev(values)
                            
                            stats[field] = field_stats
                    except Exception as e:
                        self.metadata["errors"].append(f"Error calculating statistics for field '{field}': {str(e)}")
            
            # Add statistics to data
            if not hasattr(self, "analysis"):
                self.analysis = {}
            self.analysis["statistics"] = stats
            
            # Update metadata
            self.metadata["processing_steps"].append("calculate_statistics")
            self.metadata["statistics_fields"] = list(stats.keys())
            
            return self._create_result()
        except Exception as e:
            self.metadata["status"] = "error"
            self.metadata["errors"].append(f"Statistics calculation error: {str(e)}")
            return self._create_result()
    
    def filter_data(self, filter_func, description=None):
        """
        Filter the data using the provided filter function.
        
        Args:
            filter_func: Function that takes a data item and returns True to keep it
            description: Description of the filter for metadata
        
        Returns:
            dict: Stage result with data and metadata
        """
        if self.data is None:
            self.metadata["status"] = "error"
            self.metadata["errors"].append("No data to filter")
            return self._create_result()
        
        try:
            original_count = len(self.data) if isinstance(self.data, list) else 1
            
            # Apply filter
            if isinstance(self.data, list):
                self.data = [item for item in self.data if filter_func(item)]
            else:
                self.data = self.data if filter_func(self.data) else None
            
            # Update metadata
            filtered_count = len(self.data) if isinstance(self.data, list) else (1 if self.data else 0)
            filter_info = {
                "description": description or "Custom filter",
                "original_count": original_count,
                "filtered_count": filtered_count,
                "removed_count": original_count - filtered_count
            }
            
            if not hasattr(self, "filters_applied"):
                self.filters_applied = []
            self.filters_applied.append(filter_info)
            
            self.metadata["processing_steps"].append("filter_data")
            self.metadata["filters_applied"] = self.filters_applied
            
            return self._create_result()
        except Exception as e:
            self.metadata["status"] = "error"
            self.metadata["errors"].append(f"Filter error: {str(e)}")
            return self._create_result()
    
    def transform_fields(self, transformations, description=None):
        """
        Apply transformations to specific fields in the data.
        
        Args:
            transformations: Dict mapping field names to transformation functions
            description: Description of the transformations for metadata
        
        Returns:
            dict: Stage result with data and metadata
        """
        if self.data is None:
            self.metadata["status"] = "error"
            self.metadata["errors"].append("No data to transform")
            return self._create_result()
        
        try:
            # Apply transformations
            if isinstance(self.data, list):
                for item in self.data:
                    for field, transform_func in transformations.items():
                        if field in item:
                            item[field] = transform_func(item[field])
            else:
                for field, transform_func in transformations.items():
                    if field in self.data:
                        self.data[field] = transform_func(self.data[field])
            
            # Update metadata
            transform_info = {
                "description": description or "Field transformations",
                "fields_transformed": list(transformations.keys())
            }
            
            if not hasattr(self, "transformations_applied"):
                self.transformations_applied = []
            self.transformations_applied.append(transform_info)
            
            self.metadata["processing_steps"].append("transform_fields")
            self.metadata["transformations_applied"] = self.transformations_applied
            
            return self._create_result()
        except Exception as e:
            self.metadata["status"] = "error"
            self.metadata["errors"].append(f"Transformation error: {str(e)}")
            return self._create_result()
    
    def finalize(self):
        """
        Finalize the processing stage.
        
        Returns:
            dict: Stage result with data and metadata
        """
        if self.metadata["status"] not in ["error", "skipped"]:
            self.metadata["status"] = "completed"
            self.metadata["completed_at"] = datetime.now().isoformat()
            
            # Calculate processing time if we have start time
            if "started_at" in self.metadata:
                start_time = datetime.fromisoformat(self.metadata["started_at"])
                end_time = datetime.fromisoformat(self.metadata["completed_at"])
                processing_time = (end_time - start_time).total_seconds()
                self.metadata["processing_time_seconds"] = processing_time
        
        return self._create_result()
    
    def _create_result(self):
        """Create a result dictionary with data and metadata."""
        result = {
            "data": self.data,
            "metadata": self.metadata
        }
        
        # Add analysis if available
        if hasattr(self, "analysis"):
            result["analysis"] = self.analysis
        
        return result
