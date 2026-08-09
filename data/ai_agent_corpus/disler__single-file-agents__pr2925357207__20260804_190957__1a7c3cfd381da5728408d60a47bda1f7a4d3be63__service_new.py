#!/usr/bin/env python3

"""
Project service containing business logic for project management.
"""

from shared.db import db
from shared.utils import validate_required_fields, get_timestamp
from .model import Project

class ProjectService:
    """Service for managing projects."""
    
    @staticmethod
    def create_project(project_data):
        """Create a new project."""
        validate_required_fields(project_data, ["name"])
        project = Project(**project_data)
        db.insert("projects", project.id, project.to_dict())
        return project.to_dict()
    
    @staticmethod
    def get_project(project_id):
        """Get a project by ID."""
        project_data = db.get("projects", project_id)
        if not project_data:
            return None
        return project_data
    
    @staticmethod
    def get_all_projects():
        """Get all projects."""
        return db.get_all("projects")
    
    @staticmethod
    def get_user_projects(user_id):
        """Get all projects for a specific user."""
        all_projects = db.get_all("projects")
        return [project for project in all_projects if project.get("user_id") == user_id]
    
    @staticmethod
    def update_project(project_id, project_data):
        """Update a project."""
        existing_project = db.get("projects", project_id)
        if not existing_project:
            return None
        
        # Update fields
        for key, value in project_data.items():
            if key not in ["id", "created_at"]:
                existing_project[key] = value
        
        # Update timestamp
        existing_project["updated_at"] = get_timestamp()
        
        # Save to database
        db.update("projects", project_id, existing_project)
        return existing_project
    
    @staticmethod
    def delete_project(project_id):
        """Delete a project."""
        return db.delete("projects", project_id)
    
    @staticmethod
    def add_task_to_project(project_id, task_id):
        """Add a task to a project."""
        project = db.get("projects", project_id)
        if not project:
            return False
        
        # Check if task exists
        task = db.get("tasks", task_id)
        if not task:
            return False
        
        # Add task to project if not already added
        if task_id not in project["task_ids"]:
            project["task_ids"].append(task_id)
            project["updated_at"] = get_timestamp()
            db.update("projects", project_id, project)
        
        return True
    
    @staticmethod
    def remove_task_from_project(project_id, task_id):
        """Remove a task from a project."""
        project = db.get("projects", project_id)
        if not project:
            return False
        
        # Remove task from project if it exists
        if task_id in project["task_ids"]:
            project["task_ids"].remove(task_id)
            project["updated_at"] = get_timestamp()
            db.update("projects", project_id, project)
            return True
        
        return False
    
    @staticmethod
    def get_project_tasks(project_id):
        """Get all tasks for a specific project."""
        project = db.get("projects", project_id)
        if not project:
            return []
        
        tasks = []
        for task_id in project["task_ids"]:
            task = db.get("tasks", task_id)
            if task:
                tasks.append(task)
        
        return tasks
