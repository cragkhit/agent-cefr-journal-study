#!/usr/bin/env python3

"""
Project model definition.
"""

from shared.utils import generate_id, get_timestamp

class Project:
    """Project model representing a collection of tasks."""
    
    def __init__(self, name, description=None, user_id=None, id=None):
        self.id = id or generate_id()
        self.name = name
        self.description = description
        self.user_id = user_id  # Owner of the project
        self.task_ids = []  # List of task IDs associated with this project
        self.created_at = get_timestamp()
        self.updated_at = self.created_at
        
    def to_dict(self):
        """Convert project to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "user_id": self.user_id,
            "task_ids": self.task_ids,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
        
    @classmethod
    def from_dict(cls, data):
        """Create a project from dictionary."""
        project = cls(
            name=data["name"],
            description=data.get("description"),
            user_id=data.get("user_id"),
            id=data.get("id")
        )
        project.task_ids = data.get("task_ids", [])
        project.created_at = data.get("created_at", project.created_at)
        project.updated_at = data.get("updated_at", project.updated_at)
        return project
