#!/usr/bin/env -S uv run --script

# /// script
# dependencies = [
# ]
# ///

"""
Main application entry point for the Pipeline Architecture example.
"""

import os
import json
from steps.input_stage import InputStage
from steps.processing_stage import ProcessingStage
from steps.output_stage import OutputStage
from pipeline_manager.data_pipeline import DataProcessingPipeline
from shared.utilities import format_currency, format_percentage

def create_sample_data():
    """Create sample sales data for the pipeline example."""
    # Create output directory if it doesn't exist
    os.makedirs("./data", exist_ok=True)
    
    # Sample sales data
    sales_data = [
        {
            "id": "S001",
            "product": "Laptop",
            "category": "Electronics",
            "price": 1299.99,
            "quantity": 5,
            "date": "2025-01-15",
            "customer": "ABC Corp",
            "discount": 0.1
        },
        {
            "id": "S002",
            "product": "Smartphone",
            "category": "Electronics",
            "price": 899.99,
            "quantity": 10,
            "date": "2025-01-20",
            "customer": "XYZ Ltd",
            "discount": 0.05
        },
        {
            "id": "S003",
            "product": "Office Chair",
            "category": "Furniture",
            "price": 249.99,
            "quantity": 8,
            "date": "2025-01-22",
            "customer": "123 Industries",
            "discount": 0.0
        },
        {
            "id": "S004",
            "product": "Desk",
            "category": "Furniture",
            "price": 349.99,
            "quantity": 4,
            "date": "2025-01-25",
            "customer": "ABC Corp",
            "discount": 0.15
        },
        {
            "id": "S005",
            "product": "Monitor",
            "category": "Electronics",
            "price": 499.99,
            "quantity": 12,
            "date": "2025-01-30",
            "customer": "XYZ Ltd",
            "discount": 0.1
        },
        {
            "id": "S006",
            "product": "Printer",
            "category": "Electronics",
            "price": 299.99,
            "quantity": 3,
            "date": "2025-02-05",
            "customer": "123 Industries",
            "discount": 0.0
        },
        {
            "id": "S007",
            "product": "Bookshelf",
            "category": "Furniture",
            "price": 199.99,
            "quantity": 6,
            "date": "2025-02-10",
            "customer": "ABC Corp",
            "discount": 0.05
        }
    ]
    
    # Save to file
    with open("./data/sales_data.json", "w") as file:
        json.dump(sales_data, file, indent=2)
    
    print(f"Created sample data file: ./data/sales_data.json")
    return "./data/sales_data.json"

def main():
    """Run the pipeline architecture example."""
    print("\n===== Pipeline Architecture Example =====")
    
    # Create sample data
    data_file = create_sample_data()
    
    # Create pipeline stages
    input_stage = InputStage()
    processing_stage = ProcessingStage()
    output_stage = OutputStage()
    
    # Create and configure pipeline
    pipeline = DataProcessingPipeline("Sales Data Analysis Pipeline")
    
    # Add stages
    pipeline.add_stage("input", input_stage)
    pipeline.add_stage("processing", processing_stage)
    pipeline.add_stage("output", output_stage)
    
    # Configure input
    pipeline.configure_input(
        source=data_file,
        source_type="json",
        required_fields=["id", "product", "price", "quantity"]
    )
    
    # Configure processing
    pipeline.configure_processing({
        "calculate_statistics": True,
        "numeric_fields": ["price", "quantity", "discount"],
        "filters": [
            {
                "filter_func": lambda item: item["price"] * item["quantity"] > 1000,
                "description": "High-value sales (>$1000)"
            }
        ],
        "transformations": {
            "price": lambda price: format_currency(price),
            "discount": lambda discount: format_percentage(discount)
        },
        "transformation_description": "Format price as currency and discount as percentage"
    })
    
    # Configure output
    pipeline.configure_output({
        "format_summary": True,
        "format_detailed": True,
        "print_results": True,
        "print_output_type": "summary",
        "save_to_file": [
            {
                "format": "json",
                "dir": "./output",
                "filename": "sales_analysis.json"
            }
        ]
    })
    
    # Run the pipeline
    result = pipeline.run()
    
    print("\n===== Pipeline Execution Complete =====")
    print(f"Pipeline status: {result['metadata']['status']}")
    print(f"Execution time: {result['metadata']['execution_time_seconds']:.2f} seconds")
    
    # Show output file location if saved
    if "stages" in result and len(result["stages"]) > 0:
        output_stage_name = result["stages"][-1]["name"]
        if output_stage_name in pipeline.results:
            output_result = pipeline.results[output_stage_name]
            if "metadata" in output_result and "output_files" in output_result["metadata"]:
                print("\nOutput files:")
                for output_file in output_result["metadata"]["output_files"]:
                    print(f"- {output_file['path']} ({output_file['format']})")

if __name__ == "__main__":
    main()
