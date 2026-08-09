#!/usr/bin/env python3

"""
User service containing business logic for user management.
"""

from shared.db import db
from shared.utils import validate_required_fields, get_timestamp
from .model import User

class UserService:
    """Service for managing users."""
    
    @staticmethod
    def create_user(user_data):
        """Create a new user."""
        validate_required_fields(user_data, ["username", "email"])
        
        # Check if username already exists
        all_users = db.get_all("users")
        if any(user["username"] == user_data["username"] for user in all_users):
            raise ValueError(f"Username '{user_data['username']}' already exists")
        
        user = User(**user_data)
        db.insert("users", user.id, user.to_dict())
        return user.to_dict()
    
    @staticmethod
    def get_user(user_id):
        """Get a user by ID."""
        user_data = db.get("users", user_id)
        if not user_data:
            return None
        return user_data
    
    @staticmethod
    def get_by_username(username):
        """Get a user by username."""
        all_users = db.get_all("users")
        for user in all_users:
            if user["username"] == username:
                return user
        return None
    
    @staticmethod
    def get_all_users():
        """Get all users."""
        return db.get_all("users")
    
    @staticmethod
    def update_user(user_id, user_data):
        """Update a user."""
        existing_user = db.get("users", user_id)
        if not existing_user:
            return None
        
        # Check if username is being changed and already exists
        if "username" in user_data and user_data["username"] != existing_user["username"]:
            all_users = db.get_all("users")
            if any(user["username"] == user_data["username"] for user in all_users if user["id"] != user_id):
                raise ValueError(f"Username '{user_data['username']}' already exists")
        
        # Update fields
        for key, value in user_data.items():
            if key not in ["id", "created_at"]:
                existing_user[key] = value
        
        # Update timestamp
        existing_user["updated_at"] = get_timestamp()
        
        # Save to database
        db.update("users", user_id, existing_user)
        return existing_user
    
    @staticmethod
    def delete_user(user_id):
        """Delete a user."""
        return db.delete("users", user_id)
