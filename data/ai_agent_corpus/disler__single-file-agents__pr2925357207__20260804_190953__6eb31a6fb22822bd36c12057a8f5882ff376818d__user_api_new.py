#!/usr/bin/env python3

"""
User API endpoints for the Atomic/Composable Architecture.
This module combines user_management capability with HTTP endpoints.
"""

from typing import Dict, Optional

from molecule.user_management import (
    register_new_user, login_user, validate_user_token,
    logout_user, update_user_profile, change_password
)

class UserAPI:
    """API endpoints for user management."""
    
    @staticmethod
    def register(username: str, password: str, email: str) -> Dict:
        """
        Register a new user.
        
        Args:
            username: The username for the new user
            password: The password for the new user
            email: The email for the new user
            
        Returns:
            Response with success status and user data or error message
        """
        success, result = register_new_user(username, password, email)
        
        if success:
            return {
                "status": "success",
                "message": "User registered successfully",
                "data": result
            }
        else:
            return {
                "status": "error",
                "message": result.get("error", "Registration failed"),
                "data": None
            }
    
    @staticmethod
    def login(username: str, password: str) -> Dict:
        """
        Login a user.
        
        Args:
            username: The username to authenticate
            password: The password to authenticate
            
        Returns:
            Response with success status and user data with token or error message
        """
        success, result = login_user(username, password)
        
        if success:
            return {
                "status": "success",
                "message": "Login successful",
                "data": result
            }
        else:
            return {
                "status": "error",
                "message": result.get("error", "Login failed"),
                "data": None
            }
    
    @staticmethod
    def get_profile(token: str) -> Dict:
        """
        Get a user's profile.
        
        Args:
            token: Authentication token
            
        Returns:
            Response with success status and user data or error message
        """
        success, user_data = validate_user_token(token)
        
        if success:
            return {
                "status": "success",
                "message": "Profile retrieved successfully",
                "data": {"user": user_data}
            }
        else:
            return {
                "status": "error",
                "message": "Invalid or expired token",
                "data": None
            }
    
    @staticmethod
    def logout(token: str) -> Dict:
        """
        Logout a user.
        
        Args:
            token: Authentication token
            
        Returns:
            Response with success status
        """
        success = logout_user(token)
        
        if success:
            return {
                "status": "success",
                "message": "Logout successful",
                "data": None
            }
        else:
            return {
                "status": "error",
                "message": "Invalid token",
                "data": None
            }
    
    @staticmethod
    def update_profile(token: str, profile_data: Dict) -> Dict:
        """
        Update a user's profile.
        
        Args:
            token: Authentication token
            profile_data: The profile data to update
            
        Returns:
            Response with success status and updated user data or error message
        """
        # Validate token
        success, user_data = validate_user_token(token)
        if not success:
            return {
                "status": "error",
                "message": "Invalid or expired token",
                "data": None
            }
        
        # Update profile
        success, result = update_user_profile(user_data["id"], profile_data)
        
        if success:
            return {
                "status": "success",
                "message": "Profile updated successfully",
                "data": result
            }
        else:
            return {
                "status": "error",
                "message": result.get("error", "Profile update failed"),
                "data": None
            }
    
    @staticmethod
    def change_password(token: str, current_password: str, new_password: str) -> Dict:
        """
        Change a user's password.
        
        Args:
            token: Authentication token
            current_password: The current password
            new_password: The new password
            
        Returns:
            Response with success status or error message
        """
        # Validate token
        success, user_data = validate_user_token(token)
        if not success:
            return {
                "status": "error",
                "message": "Invalid or expired token",
                "data": None
            }
        
        # Change password
        success, result = change_password(user_data["id"], current_password, new_password)
        
        if success:
            return {
                "status": "success",
                "message": "Password changed successfully",
                "data": None
            }
        else:
            return {
                "status": "error",
                "message": result.get("error", "Password change failed"),
                "data": None
            }
