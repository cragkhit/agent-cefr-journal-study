#!/usr/bin/env python3

"""
User model definition.
"""

from shared.utils import generate_id, get_timestamp

class User:
    """User model representing an application user."""
    
    def __init__(self, username, email, name=None, id=None):
        self.id = id or generate_id()
        self.username = username
        self.email = email
        self.name = name
        self.created_at = get_timestamp()
        self.updated_at = self.created_at
        
    def to_dict(self):
        """Convert user to dictionary."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "name": self.name,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
        
    @classmethod
    def from_dict(cls, data):
        """Create a user from dictionary."""
        user = cls(
            username=data["username"],
            email=data["email"],
            name=data.get("name"),
            id=data.get("id")
        )
        user.created_at = data.get("created_at", user.created_at)
        user.updated_at = data.get("updated_at", user.updated_at)
        return user
