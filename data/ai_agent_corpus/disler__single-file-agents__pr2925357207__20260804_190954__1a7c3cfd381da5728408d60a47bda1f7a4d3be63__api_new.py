#!/usr/bin/env python3

"""
Project API endpoints.
"""

from .service import ProjectService
from features.tasks.service import TaskService

class ProjectAPI:
    """API endpoints for project management."""
    
    @staticmethod
    def create_project(name, description=None, user_id=None):
        """Create a new project."""
        project_data = {
            "name": name,
            "description": description,
            "user_id": user_id
        }
        return ProjectService.create_project(project_data)
    
    @staticmethod
    def get_project(project_id):
        """Get a project by ID."""
        project = ProjectService.get_project(project_id)
        if not project:
            return {"error": f"Project with ID {project_id} not found"}
        return project
    
    @staticmethod
    def get_all_projects():
        """Get all projects."""
        return ProjectService.get_all_projects()
    
    @staticmethod
    def get_user_projects(user_id):
        """Get all projects for a specific user."""
        return ProjectService.get_user_projects(user_id)
    
    @staticmethod
    def update_project(project_id, project_data):
        """Update a project."""
        project = ProjectService.update_project(project_id, project_data)
        if not project:
            return {"error": f"Project with ID {project_id} not found"}
        return project
    
    @staticmethod
    def delete_project(project_id):
        """Delete a project."""
        success = ProjectService.delete_project(project_id)
        if not success:
            return {"error": f"Project with ID {project_id} not found"}
        return {"message": f"Project with ID {project_id} deleted successfully"}
    
    @staticmethod
    def add_task_to_project(project_id, task_id):
        """Add a task to a project."""
        success = ProjectService.add_task_to_project(project_id, task_id)
        if not success:
            return {"error": "Project or task not found"}
        return {"message": f"Task added to project successfully"}
    
    @staticmethod
    def remove_task_from_project(project_id, task_id):
        """Remove a task from a project."""
        success = ProjectService.remove_task_from_project(project_id, task_id)
        if not success:
            return {"error": "Project or task not found, or task is not in project"}
        return {"message": f"Task removed from project successfully"}
    
    @staticmethod
    def get_project_tasks(project_id):
        """Get all tasks for a specific project."""
        project = ProjectService.get_project(project_id)
        if not project:
            return {"error": f"Project with ID {project_id} not found"}
        
        tasks = ProjectService.get_project_tasks(project_id)
        return tasks
