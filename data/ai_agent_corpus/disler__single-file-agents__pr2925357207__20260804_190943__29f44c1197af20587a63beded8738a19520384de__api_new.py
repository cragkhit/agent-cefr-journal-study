#!/usr/bin/env python3

"""
User API endpoints.
"""

from .service import UserService

class UserAPI:
    """API endpoints for user management."""
    
    @staticmethod
    def create_user(username, email, name=None):
        """Create a new user."""
        try:
            user_data = {
                "username": username,
                "email": email,
                "name": name
            }
            return UserService.create_user(user_data)
        except ValueError as e:
            return {"error": str(e)}
    
    @staticmethod
    def get_user(user_id):
        """Get a user by ID."""
        user = UserService.get_user(user_id)
        if not user:
            return {"error": f"User with ID {user_id} not found"}
        return user
    
    @staticmethod
    def get_by_username(username):
        """Get a user by username."""
        user = UserService.get_by_username(username)
        if not user:
            return {"error": f"User with username '{username}' not found"}
        return user
    
    @staticmethod
    def get_all_users():
        """Get all users."""
        return UserService.get_all_users()
    
    @staticmethod
    def update_user(user_id, user_data):
        """Update a user."""
        try:
            user = UserService.update_user(user_id, user_data)
            if not user:
                return {"error": f"User with ID {user_id} not found"}
            return user
        except ValueError as e:
            return {"error": str(e)}
    
    @staticmethod
    def delete_user(user_id):
        """Delete a user."""
        success = UserService.delete_user(user_id)
        if not success:
            return {"error": f"User with ID {user_id} not found"}
        return {"message": f"User with ID {user_id} deleted successfully"}
