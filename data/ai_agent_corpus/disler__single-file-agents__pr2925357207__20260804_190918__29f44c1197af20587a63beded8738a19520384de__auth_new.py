#!/usr/bin/env python3

"""
Authentication module for the Atomic/Composable Architecture.
This module provides atomic authentication utilities.
"""

import hashlib
import os
import time
import uuid
from typing import Dict, Optional, Tuple

# In-memory user store for demonstration purposes
# In a real application, this would be a database
USER_STORE: Dict[str, Dict] = {}

# In-memory token store for demonstration purposes
TOKEN_STORE: Dict[str, Dict] = {}

def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """
    Hash a password with a salt for secure storage.
    
    Args:
        password: The password to hash
        salt: Optional salt, generated if not provided
        
    Returns:
        Tuple of (hashed_password, salt)
    """
    if salt is None:
        salt = os.urandom(16).hex()
    
    # In a real application, use a more secure hashing algorithm like bcrypt
    hashed = hashlib.sha256((password + salt).encode()).hexdigest()
    return hashed, salt

def verify_password(password: str, hashed_password: str, salt: str) -> bool:
    """
    Verify a password against a stored hash.
    
    Args:
        password: The password to verify
        hashed_password: The stored hashed password
        salt: The salt used for hashing
        
    Returns:
        True if the password matches, False otherwise
    """
    calculated_hash, _ = hash_password(password, salt)
    return calculated_hash == hashed_password

def register_user(username: str, password: str, email: str) -> Dict:
    """
    Register a new user.
    
    Args:
        username: The username for the new user
        password: The password for the new user
        email: The email for the new user
        
    Returns:
        User data dictionary
    
    Raises:
        ValueError: If the username already exists
    """
    if username in USER_STORE:
        raise ValueError(f"Username '{username}' already exists")
    
    hashed_password, salt = hash_password(password)
    user_id = str(uuid.uuid4())
    
    user_data = {
        "id": user_id,
        "username": username,
        "email": email,
        "hashed_password": hashed_password,
        "salt": salt,
        "created_at": time.time()
    }
    
    USER_STORE[username] = user_data
    return {k: v for k, v in user_data.items() if k not in ["hashed_password", "salt"]}

def authenticate(username: str, password: str) -> Optional[Dict]:
    """
    Authenticate a user with username and password.
    
    Args:
        username: The username to authenticate
        password: The password to authenticate
        
    Returns:
        User data dictionary if authentication succeeds, None otherwise
    """
    if username not in USER_STORE:
        return None
    
    user_data = USER_STORE[username]
    if verify_password(password, user_data["hashed_password"], user_data["salt"]):
        return {k: v for k, v in user_data.items() if k not in ["hashed_password", "salt"]}
    
    return None

def create_token(user_id: str, expires_in: int = 3600) -> str:
    """
    Create an authentication token for a user.
    
    Args:
        user_id: The user ID to create a token for
        expires_in: Token expiration time in seconds
        
    Returns:
        Authentication token
    """
    token = str(uuid.uuid4())
    expiration = time.time() + expires_in
    
    TOKEN_STORE[token] = {
        "user_id": user_id,
        "expires_at": expiration
    }
    
    return token

def validate_token(token: str) -> Optional[str]:
    """
    Validate an authentication token.
    
    Args:
        token: The token to validate
        
    Returns:
        User ID if the token is valid, None otherwise
    """
    if token not in TOKEN_STORE:
        return None
    
    token_data = TOKEN_STORE[token]
    if token_data["expires_at"] < time.time():
        # Token expired, remove it
        del TOKEN_STORE[token]
        return None
    
    return token_data["user_id"]

def revoke_token(token: str) -> bool:
    """
    Revoke an authentication token.
    
    Args:
        token: The token to revoke
        
    Returns:
        True if the token was revoked, False if it didn't exist
    """
    if token in TOKEN_STORE:
        del TOKEN_STORE[token]
        return True
    return False

def get_user_by_id(user_id: str) -> Optional[Dict]:
    """
    Get a user by ID.
    
    Args:
        user_id: The user ID to look up
        
    Returns:
        User data dictionary if found, None otherwise
    """
    for user_data in USER_STORE.values():
        if user_data["id"] == user_id:
            return {k: v for k, v in user_data.items() if k not in ["hashed_password", "salt"]}
    return None
