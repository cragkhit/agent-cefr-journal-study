#!/usr/bin/env python3

"""
Shared utilities for the application.
"""

import uuid
from datetime import datetime

def generate_id():
    """Generate a unique ID."""
    return str(uuid.uuid4())

def get_timestamp():
    """Get the current timestamp."""
    return datetime.now().isoformat()

def validate_required_fields(data, required_fields):
    """Validate that all required fields are present in the data."""
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
    return True
