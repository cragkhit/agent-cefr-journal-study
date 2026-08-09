#!/usr/bin/env python3

"""
Task model definition.
"""

from shared.utils import generate_id, get_timestamp

class Task:
    """Task model representing a to-do item."""
    
    def __init__(self, title, description=None, user_id=None, status="pending", id=None):
        self.id = id or generate_id()
        self.title = title
        self.description = description
        self.user_id = user_id
        self.status = status
        self.created_at = get_timestamp()
        self.updated_at = self.created_at
        
    def to_dict(self):
        """Convert task to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "user_id": self.user_id,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
        
    @classmethod
    def from_dict(cls, data):
        """Create a task from dictionary."""
        task = cls(
            title=data["title"],
            description=data.get("description"),
            user_id=data.get("user_id"),
            status=data.get("status", "pending"),
            id=data.get("id")
        )
        task.created_at = data.get("created_at", task.created_at)
        task.updated_at = data.get("updated_at", task.updated_at)
        return task
