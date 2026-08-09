#!/usr/bin/env python3

"""
Category model definition.
"""

from datetime import datetime

class Category:
    """Category model representing a product category."""
    
    def __init__(self, name, description=None, id=None):
        """Initialize a category."""
        self.id = id
        self.name = name
        self.description = description
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
    
    def to_dict(self):
        """Convert category to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create a category from dictionary."""
        category = cls(
            name=data["name"],
            description=data.get("description"),
            id=data.get("id")
        )
        category.created_at = data.get("created_at", category.created_at)
        category.updated_at = data.get("updated_at", category.updated_at)
        return category
