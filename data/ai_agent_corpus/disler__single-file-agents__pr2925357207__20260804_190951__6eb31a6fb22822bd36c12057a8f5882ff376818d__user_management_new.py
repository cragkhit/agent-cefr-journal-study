#!/usr/bin/env python3

"""
User management capability for the Atomic/Composable Architecture.
This capability combines auth and validation modules.
"""

from typing import Dict, List, Optional, Tuple

from atom.auth import (
    register_user, authenticate, create_token, validate_token,
    revoke_token, get_user_by_id
)
from atom.validation import (
    validate_required_fields, validate_email, validate_username,
    validate_password_strength, validate_string_length
)

def register_new_user(username: str, password: str, email: str) -> Tuple[bool, Dict]:
    """
    Register a new user with validation.
    
    Args:
        username: The username for the new user
        password: The password for the new user
        email: The email for the new user
        
    Returns:
        Tuple of (success, result) where result is either user data or error messages
    """
    # Validate required fields
    missing_fields = validate_required_fields(
        {"username": username, "password": password, "email": email},
        ["username", "password", "email"]
    )
    
    if missing_fields:
        return False, {"error": f"Missing required fields: {', '.join(missing_fields)}"}
    
    # Validate username
    if not validate_username(username):
        return False, {"error": "Username must be 3-20 characters, alphanumeric with underscores"}
    
    # Validate email
    if not validate_email(email):
        return False, {"error": "Invalid email format"}
    
    # Validate password strength
    password_validation = validate_password_strength(password)
    if not password_validation["is_valid"]:
        errors = []
        if not password_validation["length"]:
            errors.append("Password must be at least 8 characters")
        if not password_validation["uppercase"]:
            errors.append("Password must contain at least one uppercase letter")
        if not password_validation["lowercase"]:
            errors.append("Password must contain at least one lowercase letter")
        if not password_validation["digit"]:
            errors.append("Password must contain at least one digit")
        if not password_validation["special_char"]:
            errors.append("Password must contain at least one special character")
        
        return False, {"error": errors}
    
    try:
        # Register the user
        user_data = register_user(username, password, email)
        return True, {"user": user_data}
    except ValueError as e:
        return False, {"error": str(e)}

def login_user(username: str, password: str) -> Tuple[bool, Dict]:
    """
    Login a user and create an authentication token.
    
    Args:
        username: The username to authenticate
        password: The password to authenticate
        
    Returns:
        Tuple of (success, result) where result contains user data and token or error message
    """
    # Validate required fields
    missing_fields = validate_required_fields(
        {"username": username, "password": password},
        ["username", "password"]
    )
    
    if missing_fields:
        return False, {"error": f"Missing required fields: {', '.join(missing_fields)}"}
    
    # Authenticate the user
    user_data = authenticate(username, password)
    if not user_data:
        return False, {"error": "Invalid username or password"}
    
    # Create an authentication token
    token = create_token(user_data["id"])
    
    return True, {
        "user": user_data,
        "token": token
    }

def validate_user_token(token: str) -> Tuple[bool, Optional[Dict]]:
    """
    Validate a user token and return user data.
    
    Args:
        token: The token to validate
        
    Returns:
        Tuple of (success, user_data) where user_data is None if validation fails
    """
    if not token:
        return False, None
    
    user_id = validate_token(token)
    if not user_id:
        return False, None
    
    user_data = get_user_by_id(user_id)
    if not user_data:
        return False, None
    
    return True, user_data

def logout_user(token: str) -> bool:
    """
    Logout a user by revoking their token.
    
    Args:
        token: The token to revoke
        
    Returns:
        True if the token was revoked, False otherwise
    """
    return revoke_token(token)

def update_user_profile(user_id: str, profile_data: Dict) -> Tuple[bool, Dict]:
    """
    Update a user's profile data.
    
    Args:
        user_id: The ID of the user to update
        profile_data: The profile data to update
        
    Returns:
        Tuple of (success, result) where result is either updated user data or error messages
    """
    # Get the current user data
    user_data = get_user_by_id(user_id)
    if not user_data:
        return False, {"error": "User not found"}
    
    # Validate email if provided
    if "email" in profile_data:
        if not validate_email(profile_data["email"]):
            return False, {"error": "Invalid email format"}
    
    # In a real application, this would update the user in the database
    # For this mock, we'll just print the update
    print(f"[UPDATE] User {user_id} profile updated:")
    for key, value in profile_data.items():
        print(f"  {key}: {value}")
    
    # Return success with mock updated data
    updated_user = {**user_data, **profile_data}
    return True, {"user": updated_user}

def change_password(user_id: str, current_password: str, new_password: str) -> Tuple[bool, Dict]:
    """
    Change a user's password.
    
    Args:
        user_id: The ID of the user
        current_password: The current password
        new_password: The new password
        
    Returns:
        Tuple of (success, result) where result contains a success message or error message
    """
    # Validate required fields
    missing_fields = validate_required_fields(
        {"current_password": current_password, "new_password": new_password},
        ["current_password", "new_password"]
    )
    
    if missing_fields:
        return False, {"error": f"Missing required fields: {', '.join(missing_fields)}"}
    
    # Validate new password strength
    password_validation = validate_password_strength(new_password)
    if not password_validation["is_valid"]:
        errors = []
        if not password_validation["length"]:
            errors.append("Password must be at least 8 characters")
        if not password_validation["uppercase"]:
            errors.append("Password must contain at least one uppercase letter")
        if not password_validation["lowercase"]:
            errors.append("Password must contain at least one lowercase letter")
        if not password_validation["digit"]:
            errors.append("Password must contain at least one digit")
        if not password_validation["special_char"]:
            errors.append("Password must contain at least one special character")
        
        return False, {"error": errors}
    
    # In a real application, this would verify the current password and update it
    # For this mock, we'll just print the change
    print(f"[PASSWORD] User {user_id} password changed")
    
    return True, {"message": "Password changed successfully"}
