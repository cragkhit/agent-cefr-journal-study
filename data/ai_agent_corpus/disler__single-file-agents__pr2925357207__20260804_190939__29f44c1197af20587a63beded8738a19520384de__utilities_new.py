#!/usr/bin/env python3

"""
Shared utilities for the pipeline architecture.
"""

import json
import csv
import os
from datetime import datetime

def load_json_file(file_path):
    """Load data from a JSON file."""
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        raise ValueError(f"File not found: {file_path}")
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON format in file: {file_path}")

def save_json_file(data, file_path):
    """Save data to a JSON file."""
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
    
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=2)

def load_csv_file(file_path):
    """Load data from a CSV file."""
    try:
        with open(file_path, 'r', newline='') as file:
            reader = csv.DictReader(file)
            return list(reader)
    except FileNotFoundError:
        raise ValueError(f"File not found: {file_path}")
    except Exception as e:
        raise ValueError(f"Error reading CSV file {file_path}: {str(e)}")

def save_csv_file(data, file_path, fieldnames=None):
    """Save data to a CSV file."""
    if not data:
        raise ValueError("No data to save")
    
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
    
    if fieldnames is None:
        fieldnames = data[0].keys()
    
    with open(file_path, 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

def get_timestamp():
    """Get the current timestamp."""
    return datetime.now().isoformat()

def validate_required_fields(data, required_fields):
    """Validate that all required fields are present in the data."""
    if not isinstance(data, dict):
        raise ValueError("Data must be a dictionary")
    
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
    
    return True

def format_currency(amount):
    """Format a number as currency."""
    try:
        return f"${float(amount):.2f}"
    except (ValueError, TypeError):
        return "N/A"

def format_percentage(value):
    """Format a number as percentage."""
    try:
        return f"{float(value) * 100:.1f}%"
    except (ValueError, TypeError):
        return "N/A"

def generate_report_filename(prefix="report", extension="json"):
    """Generate a filename for a report with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.{extension}"
