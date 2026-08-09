#!/usr/bin/env python3

"""
Input stage for the pipeline architecture.
This stage is responsible for loading and validating input data.
"""

import os
import json
from shared.utilities import load_json_file, load_csv_file, validate_required_fields

class InputStage:
    """Input stage for data processing pipeline."""
    
    def __init__(self):
        """Initialize the input stage."""
        self.data = None
        self.metadata = {
            "stage": "input",
            "status": "initialized",
            "errors": []
        }
    
    def load_data(self, source, source_type="json"):
        """
        Load data from the specified source.
        
        Args:
            source: Path to the data file or raw data
            source_type: Type of data source (json, csv, raw)
        
        Returns:
            dict: Stage result with data and metadata
        """
        try:
            self.metadata["source"] = source
            self.metadata["source_type"] = source_type
            
            # Load data based on source type
            if source_type == "json":
                if isinstance(source, str) and os.path.exists(source):
                    self.data = load_json_file(source)
                elif isinstance(source, str):
                    self.data = json.loads(source)
                else:
                    self.data = source
            elif source_type == "csv":
                self.data = load_csv_file(source)
            elif source_type == "raw":
                self.data = source
            else:
                raise ValueError(f"Unsupported source type: {source_type}")
            
            self.metadata["status"] = "data_loaded"
            self.metadata["record_count"] = len(self.data) if isinstance(self.data, list) else 1
            
            return self._create_result()
        except Exception as e:
            self.metadata["status"] = "error"
            self.metadata["errors"].append(str(e))
            return self._create_result()
    
    def validate_data(self, schema=None, required_fields=None):
        """
        Validate the loaded data against a schema or required fields.
        
        Args:
            schema: Schema definition for validation
            required_fields: List of required field names
        
        Returns:
            dict: Stage result with data and metadata
        """
        if self.data is None:
            self.metadata["status"] = "error"
            self.metadata["errors"].append("No data loaded to validate")
            return self._create_result()
        
        try:
            validation_errors = []
            
            # Validate required fields if specified
            if required_fields:
                if isinstance(self.data, list):
                    for i, item in enumerate(self.data):
                        try:
                            validate_required_fields(item, required_fields)
                        except ValueError as e:
                            validation_errors.append(f"Record {i}: {str(e)}")
                else:
                    try:
                        validate_required_fields(self.data, required_fields)
                    except ValueError as e:
                        validation_errors.append(str(e))
            
            # Update metadata based on validation results
            if validation_errors:
                self.metadata["status"] = "validation_failed"
                self.metadata["errors"].extend(validation_errors)
            else:
                self.metadata["status"] = "validated"
            
            return self._create_result()
        except Exception as e:
            self.metadata["status"] = "error"
            self.metadata["errors"].append(f"Validation error: {str(e)}")
            return self._create_result()
    
    def transform_data(self, transform_func):
        """
        Apply a transformation function to the data.
        
        Args:
            transform_func: Function to transform the data
        
        Returns:
            dict: Stage result with data and metadata
        """
        if self.data is None:
            self.metadata["status"] = "error"
            self.metadata["errors"].append("No data loaded to transform")
            return self._create_result()
        
        try:
            self.data = transform_func(self.data)
            self.metadata["status"] = "transformed"
            return self._create_result()
        except Exception as e:
            self.metadata["status"] = "error"
            self.metadata["errors"].append(f"Transformation error: {str(e)}")
            return self._create_result()
    
    def _create_result(self):
        """Create a result dictionary with data and metadata."""
        return {
            "data": self.data,
            "metadata": self.metadata
        }
