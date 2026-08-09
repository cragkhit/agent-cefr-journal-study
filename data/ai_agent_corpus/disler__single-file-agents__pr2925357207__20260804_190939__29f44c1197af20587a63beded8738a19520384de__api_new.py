#!/usr/bin/env python3

"""
Task API endpoints.
"""

from .service import TaskService

class TaskAPI:
    """API endpoints for task management."""
    
    @staticmethod
    def create_task(title, description=None, user_id=None):
        """Create a new task."""
        task_data = {
            "title": title,
            "description": description,
            "user_id": user_id
        }
        return TaskService.create_task(task_data)
    
    @staticmethod
    def get_task(task_id):
        """Get a task by ID."""
        task = TaskService.get_task(task_id)
        if not task:
            return {"error": f"Task with ID {task_id} not found"}
        return task
    
    @staticmethod
    def get_all_tasks():
        """Get all tasks."""
        return TaskService.get_all_tasks()
    
    @staticmethod
    def get_user_tasks(user_id):
        """Get all tasks for a specific user."""
        return TaskService.get_user_tasks(user_id)
    
    @staticmethod
    def update_task(task_id, task_data):
        """Update a task."""
        task = TaskService.update_task(task_id, task_data)
        if not task:
            return {"error": f"Task with ID {task_id} not found"}
        return task
    
    @staticmethod
    def delete_task(task_id):
        """Delete a task."""
        success = TaskService.delete_task(task_id)
        if not success:
            return {"error": f"Task with ID {task_id} not found"}
        return {"message": f"Task with ID {task_id} deleted successfully"}
