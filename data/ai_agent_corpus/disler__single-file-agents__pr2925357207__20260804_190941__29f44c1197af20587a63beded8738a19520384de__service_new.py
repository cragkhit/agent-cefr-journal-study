#!/usr/bin/env python3

"""
Task service containing business logic for task management.
"""

from shared.db import db
from shared.utils import validate_required_fields, get_timestamp
from .model import Task

class TaskService:
    """Service for managing tasks."""
    
    @staticmethod
    def create_task(task_data):
        """Create a new task."""
        validate_required_fields(task_data, ["title"])
        task = Task(**task_data)
        db.insert("tasks", task.id, task.to_dict())
        return task.to_dict()
    
    @staticmethod
    def get_task(task_id):
        """Get a task by ID."""
        task_data = db.get("tasks", task_id)
        if not task_data:
            return None
        return task_data
    
    @staticmethod
    def get_all_tasks():
        """Get all tasks."""
        return db.get_all("tasks")
    
    @staticmethod
    def get_user_tasks(user_id):
        """Get all tasks for a specific user."""
        all_tasks = db.get_all("tasks")
        return [task for task in all_tasks if task.get("user_id") == user_id]
    
    @staticmethod
    def update_task(task_id, task_data):
        """Update a task."""
        existing_task = db.get("tasks", task_id)
        if not existing_task:
            return None
        
        # Update fields
        for key, value in task_data.items():
            if key not in ["id", "created_at"]:
                existing_task[key] = value
        
        # Update timestamp
        existing_task["updated_at"] = get_timestamp()
        
        # Save to database
        db.update("tasks", task_id, existing_task)
        return existing_task
    
    @staticmethod
    def delete_task(task_id):
        """Delete a task."""
        return db.delete("tasks", task_id)
