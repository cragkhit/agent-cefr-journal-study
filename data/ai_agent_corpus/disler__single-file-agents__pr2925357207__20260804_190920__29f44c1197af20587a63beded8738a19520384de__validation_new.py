#!/usr/bin/env python3

"""
Validation module for the Atomic/Composable Architecture.
This module provides atomic validation utilities.
"""

import re
from typing import Any, Dict, List, Optional, Union

def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> List[str]:
    """
    Validate that all required fields are present in the data.
    
    Args:
        data: The data to validate
        required_fields: List of required field names
        
    Returns:
        List of missing field names, empty if all required fields are present
    """
    return [field for field in required_fields if field not in data or data[field] is None]

def validate_email(email: str) -> bool:
    """
    Validate an email address format.
    
    Args:
        email: The email address to validate
        
    Returns:
        True if the email is valid, False otherwise
    """
    # Simple regex for email validation
    # In a real application, consider using a more comprehensive validation
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_string_length(value: str, min_length: int = 0, max_length: Optional[int] = None) -> bool:
    """
    Validate that a string's length is within the specified range.
    
    Args:
        value: The string to validate
        min_length: Minimum allowed length
        max_length: Maximum allowed length, or None for no maximum
        
    Returns:
        True if the string length is valid, False otherwise
    """
    if not isinstance(value, str):
        return False
    
    if len(value) < min_length:
        return False
    
    if max_length is not None and len(value) > max_length:
        return False
    
    return True

def validate_numeric_range(value: Union[int, float], min_value: Optional[Union[int, float]] = None, 
                          max_value: Optional[Union[int, float]] = None) -> bool:
    """
    Validate that a numeric value is within the specified range.
    
    Args:
        value: The numeric value to validate
        min_value: Minimum allowed value, or None for no minimum
        max_value: Maximum allowed value, or None for no maximum
        
    Returns:
        True if the value is within range, False otherwise
    """
    if not isinstance(value, (int, float)):
        return False
    
    if min_value is not None and value < min_value:
        return False
    
    if max_value is not None and value > max_value:
        return False
    
    return True

def validate_pattern(value: str, pattern: str) -> bool:
    """
    Validate that a string matches a regular expression pattern.
    
    Args:
        value: The string to validate
        pattern: Regular expression pattern to match
        
    Returns:
        True if the string matches the pattern, False otherwise
    """
    return bool(re.match(pattern, value))

def validate_username(username: str) -> bool:
    """
    Validate a username format.
    
    Args:
        username: The username to validate
        
    Returns:
        True if the username is valid, False otherwise
    """
    # Username must be 3-20 characters, alphanumeric with underscores
    pattern = r'^[a-zA-Z0-9_]{3,20}$'
    return bool(re.match(pattern, username))

def validate_password_strength(password: str) -> Dict[str, bool]:
    """
    Validate password strength against multiple criteria.
    
    Args:
        password: The password to validate
        
    Returns:
        Dictionary with validation results for each criterion
    """
    results = {
        "length": len(password) >= 8,
        "uppercase": bool(re.search(r'[A-Z]', password)),
        "lowercase": bool(re.search(r'[a-z]', password)),
        "digit": bool(re.search(r'\d', password)),
        "special_char": bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))
    }
    
    results["is_valid"] = all(results.values())
    return results

def validate_data(data: Dict[str, Any], schema: Dict[str, Dict[str, Any]]) -> Dict[str, List[str]]:
    """
    Validate data against a schema.
    
    Args:
        data: The data to validate
        schema: Validation schema defining field types and constraints
        
    Returns:
        Dictionary mapping field names to lists of validation error messages
    """
    errors: Dict[str, List[str]] = {}
    
    for field_name, field_schema in schema.items():
        field_type = field_schema.get("type")
        required = field_schema.get("required", False)
        
        # Check if required field is missing
        if required and (field_name not in data or data[field_name] is None):
            errors.setdefault(field_name, []).append("Field is required")
            continue
        
        # Skip validation for optional fields that are not present
        if field_name not in data or data[field_name] is None:
            continue
        
        value = data[field_name]
        
        # Type validation
        if field_type == "string" and not isinstance(value, str):
            errors.setdefault(field_name, []).append("Must be a string")
        elif field_type == "number" and not isinstance(value, (int, float)):
            errors.setdefault(field_name, []).append("Must be a number")
        elif field_type == "integer" and not isinstance(value, int):
            errors.setdefault(field_name, []).append("Must be an integer")
        elif field_type == "boolean" and not isinstance(value, bool):
            errors.setdefault(field_name, []).append("Must be a boolean")
        elif field_type == "array" and not isinstance(value, list):
            errors.setdefault(field_name, []).append("Must be an array")
        elif field_type == "object" and not isinstance(value, dict):
            errors.setdefault(field_name, []).append("Must be an object")
        
        # String-specific validations
        if field_type == "string" and isinstance(value, str):
            min_length = field_schema.get("min_length")
            max_length = field_schema.get("max_length")
            pattern = field_schema.get("pattern")
            
            if min_length is not None and len(value) < min_length:
                errors.setdefault(field_name, []).append(f"Must be at least {min_length} characters")
            
            if max_length is not None and len(value) > max_length:
                errors.setdefault(field_name, []).append(f"Must be at most {max_length} characters")
            
            if pattern is not None and not re.match(pattern, value):
                errors.setdefault(field_name, []).append("Does not match required pattern")
        
        # Number-specific validations
        if field_type in ["number", "integer"] and isinstance(value, (int, float)):
            minimum = field_schema.get("minimum")
            maximum = field_schema.get("maximum")
            
            if minimum is not None and value < minimum:
                errors.setdefault(field_name, []).append(f"Must be at least {minimum}")
            
            if maximum is not None and value > maximum:
                errors.setdefault(field_name, []).append(f"Must be at most {maximum}")
    
    return errors
