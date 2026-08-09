#!/usr/bin/env python3

"""
Output stage for the pipeline architecture.
This stage is responsible for formatting and delivering the final results.
"""

import os
import json
from datetime import datetime
from shared.utilities import save_json_file, save_csv_file, generate_report_filename

class OutputStage:
    """Output stage for formatting and delivering results."""
    
    def __init__(self):
        """Initialize the output stage."""
        self.data = None
        self.analysis = None
        self.metadata = {
            "stage": "output",
            "status": "initialized",
            "errors": [],
            "output_formats": []
        }
    
    def prepare(self, processing_result):
        """
        Prepare the output stage with data from the processing stage.
        
        Args:
            processing_result: Result from the processing stage
        
        Returns:
            dict: Stage result with data and metadata
        """
        # Check if processing stage had errors
        if processing_result["metadata"]["status"] in ["error", "skipped"]:
            self.metadata["status"] = "skipped"
            self.metadata["errors"].append("Processing stage had errors, output skipped")
            return self._create_result()
        
        # Get data and metadata from processing stage
        self.data = processing_result["data"]
        self.metadata["input_metadata"] = processing_result["metadata"]["input_metadata"]
        self.metadata["processing_metadata"] = processing_result["metadata"]
        
        # Get analysis if available
        if "analysis" in processing_result:
            self.analysis = processing_result["analysis"]
        
        # Initialize output
        self.metadata["status"] = "preparing"
        self.metadata["started_at"] = datetime.now().isoformat()
        
        return self._create_result()
    
    def format_as_summary(self):
        """
        Format the data as a summary report.
        
        Returns:
            dict: Stage result with data and metadata
        """
        if self.data is None:
            self.metadata["status"] = "error"
            self.metadata["errors"].append("No data to format")
            return self._create_result()
        
        try:
            # Create summary
            summary = {
                "report_type": "summary",
                "generated_at": datetime.now().isoformat(),
                "data_source": self.metadata.get("input_metadata", {}).get("source", "unknown"),
                "record_count": len(self.data) if isinstance(self.data, list) else 1
            }
            
            # Add statistics if available
            if self.analysis and "statistics" in self.analysis:
                summary["statistics"] = self.analysis["statistics"]
            
            # Add processing information
            if "processing_metadata" in self.metadata:
                processing_meta = self.metadata["processing_metadata"]
                if "processing_steps" in processing_meta:
                    summary["processing_steps"] = processing_meta["processing_steps"]
                if "processing_time_seconds" in processing_meta:
                    summary["processing_time_seconds"] = processing_meta["processing_time_seconds"]
            
            # Store the summary
            self.summary = summary
            
            # Update metadata
            self.metadata["output_formats"].append("summary")
            
            return self._create_result()
        except Exception as e:
            self.metadata["status"] = "error"
            self.metadata["errors"].append(f"Summary formatting error: {str(e)}")
            return self._create_result()
    
    def format_as_detailed_report(self):
        """
        Format the data as a detailed report.
        
        Returns:
            dict: Stage result with data and metadata
        """
        if self.data is None:
            self.metadata["status"] = "error"
            self.metadata["errors"].append("No data to format")
            return self._create_result()
        
        try:
            # Create detailed report
            report = {
                "report_type": "detailed",
                "generated_at": datetime.now().isoformat(),
                "data_source": self.metadata.get("input_metadata", {}).get("source", "unknown"),
                "record_count": len(self.data) if isinstance(self.data, list) else 1,
                "data": self.data
            }
            
            # Add analysis if available
            if self.analysis:
                report["analysis"] = self.analysis
            
            # Add processing information
            if "processing_metadata" in self.metadata:
                report["processing_info"] = {
                    "steps": self.metadata["processing_metadata"].get("processing_steps", []),
                    "filters": self.metadata["processing_metadata"].get("filters_applied", []),
                    "transformations": self.metadata["processing_metadata"].get("transformations_applied", []),
                    "processing_time_seconds": self.metadata["processing_metadata"].get("processing_time_seconds")
                }
            
            # Store the detailed report
            self.detailed_report = report
            
            # Update metadata
            self.metadata["output_formats"].append("detailed_report")
            
            return self._create_result()
        except Exception as e:
            self.metadata["status"] = "error"
            self.metadata["errors"].append(f"Detailed report formatting error: {str(e)}")
            return self._create_result()
    
    def save_to_file(self, output_format="json", output_dir="./output", filename=None):
        """
        Save the formatted output to a file.
        
        Args:
            output_format: Format to save (json, csv)
            output_dir: Directory to save the file
            filename: Optional filename (generated if not provided)
        
        Returns:
            dict: Stage result with data and metadata
        """
        try:
            # Create output directory if it doesn't exist
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # Determine what to save
            if output_format == "json":
                if hasattr(self, "detailed_report"):
                    data_to_save = self.detailed_report
                    file_prefix = "detailed_report"
                elif hasattr(self, "summary"):
                    data_to_save = self.summary
                    file_prefix = "summary_report"
                else:
                    data_to_save = {
                        "data": self.data,
                        "generated_at": datetime.now().isoformat()
                    }
                    file_prefix = "data_export"
                
                # Generate filename if not provided
                if not filename:
                    filename = generate_report_filename(file_prefix, "json")
                
                # Save to file
                file_path = os.path.join(output_dir, filename)
                save_json_file(data_to_save, file_path)
                
            elif output_format == "csv":
                # CSV format only works for list data
                if not isinstance(self.data, list):
                    raise ValueError("CSV output format requires list data")
                
                # Generate filename if not provided
                if not filename:
                    filename = generate_report_filename("data_export", "csv")
                
                # Save to file
                file_path = os.path.join(output_dir, filename)
                save_csv_file(self.data, file_path)
            
            else:
                raise ValueError(f"Unsupported output format: {output_format}")
            
            # Update metadata
            self.metadata["output_files"] = self.metadata.get("output_files", [])
            self.metadata["output_files"].append({
                "format": output_format,
                "path": file_path,
                "filename": filename
            })
            
            return self._create_result()
        except Exception as e:
            self.metadata["status"] = "error"
            self.metadata["errors"].append(f"File save error: {str(e)}")
            return self._create_result()
    
    def print_results(self, output_type="summary"):
        """
        Print the results to the console.
        
        Args:
            output_type: Type of output to print (summary, detailed)
        
        Returns:
            dict: Stage result with data and metadata
        """
        try:
            if output_type == "summary" and hasattr(self, "summary"):
                print("\n===== SUMMARY REPORT =====")
                print(f"Generated at: {self.summary['generated_at']}")
                print(f"Data source: {self.summary['data_source']}")
                print(f"Record count: {self.summary['record_count']}")
                
                if "statistics" in self.summary:
                    print("\n----- Statistics -----")
                    for field, stats in self.summary["statistics"].items():
                        print(f"\n{field}:")
                        for stat_name, stat_value in stats.items():
                            print(f"  {stat_name}: {stat_value}")
                
                if "processing_steps" in self.summary:
                    print("\n----- Processing Steps -----")
                    for step in self.summary["processing_steps"]:
                        print(f"- {step}")
                
            elif output_type == "detailed" and hasattr(self, "detailed_report"):
                print("\n===== DETAILED REPORT =====")
                print(f"Generated at: {self.detailed_report['generated_at']}")
                print(f"Data source: {self.detailed_report['data_source']}")
                print(f"Record count: {self.detailed_report['record_count']}")
                
                if "analysis" in self.detailed_report:
                    print("\n----- Analysis -----")
                    for analysis_type, analysis_data in self.detailed_report["analysis"].items():
                        print(f"\n{analysis_type}:")
                        print(json.dumps(analysis_data, indent=2))
                
                print("\n----- Data Sample -----")
                if isinstance(self.data, list):
                    sample_size = min(3, len(self.data))
                    for i in range(sample_size):
                        print(f"\nRecord {i+1}:")
                        print(json.dumps(self.data[i], indent=2))
                else:
                    print(json.dumps(self.data, indent=2))
            
            else:
                print("\n===== DATA OUTPUT =====")
                if isinstance(self.data, list):
                    print(f"Record count: {len(self.data)}")
                    sample_size = min(3, len(self.data))
                    print(f"\nShowing {sample_size} sample records:")
                    for i in range(sample_size):
                        print(f"\nRecord {i+1}:")
                        print(json.dumps(self.data[i], indent=2))
                else:
                    print(json.dumps(self.data, indent=2))
            
            # Update metadata
            self.metadata["output_formats"].append("console")
            
            return self._create_result()
        except Exception as e:
            self.metadata["status"] = "error"
            self.metadata["errors"].append(f"Print error: {str(e)}")
            return self._create_result()
    
    def finalize(self):
        """
        Finalize the output stage.
        
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
        if self.analysis:
            result["analysis"] = self.analysis
        
        # Add formatted outputs if available
        if hasattr(self, "summary"):
            result["summary"] = self.summary
        
        if hasattr(self, "detailed_report"):
            result["detailed_report"] = self.detailed_report
        
        return result
