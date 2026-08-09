#!/usr/bin/env -S uv run --script

# /// script
# dependencies = [
# ]
# ///

"""
Main application entry point for the Vertical Slice Architecture example.
"""

from features.users.api import UserAPI
from features.tasks.api import TaskAPI
from features.projects.api import ProjectAPI

def display_header(text):
    """Display a header with the given text."""
    print("\n" + "=" * 50)
    print(f" {text}")
    print("=" * 50)

def display_result(result):
    """Display a result."""
    if isinstance(result, list):
        for item in result:
            print(f"- {item}")
    elif isinstance(result, dict):
        for key, value in result.items():
            print(f"{key}: {value}")
    else:
        print(result)

def main():
    """Run the application."""
    display_header("Vertical Slice Architecture Example")
    
    # Create users
    display_header("Creating Users")
    user1 = UserAPI.create_user("johndoe", "john@example.com", "John Doe")
    display_result(user1)
    
    user2 = UserAPI.create_user("janedoe", "jane@example.com", "Jane Doe")
    display_result(user2)
    
    # Try to create a user with an existing username
    duplicate_user = UserAPI.create_user("johndoe", "another@example.com")
    display_result(duplicate_user)
    
    # Get all users
    display_header("All Users")
    all_users = UserAPI.get_all_users()
    for user in all_users:
        display_result(user)
    
    # Create tasks
    display_header("Creating Tasks")
    task1 = TaskAPI.create_task("Complete project", "Finish the architecture example", user1["id"])
    display_result(task1)
    
    task2 = TaskAPI.create_task("Review code", "Check for bugs and improvements", user2["id"])
    display_result(task2)
    
    task3 = TaskAPI.create_task("Write documentation", "Document the architecture", user1["id"])
    display_result(task3)
    
    # Get user tasks
    display_header(f"Tasks for {user1['name']}")
    user1_tasks = TaskAPI.get_user_tasks(user1["id"])
    for task in user1_tasks:
        display_result(task)
    
    # Update a task
    display_header("Updating a Task")
    updated_task = TaskAPI.update_task(task1["id"], {"status": "completed"})
    display_result(updated_task)
    
    # Delete a task
    display_header("Deleting a Task")
    delete_result = TaskAPI.delete_task(task2["id"])
    display_result(delete_result)
    
    # Get all remaining tasks
    display_header("All Remaining Tasks")
    all_tasks = TaskAPI.get_all_tasks()
    for task in all_tasks:
        display_result(task)
    
    # Create a project
    display_header("Creating a Project")
    project = ProjectAPI.create_project("Task Management System", "A project for managing tasks", user1["id"])
    display_result(project)
    
    # Add tasks to the project
    display_header("Adding Tasks to Project")
    add_task1 = ProjectAPI.add_task_to_project(project["id"], task1["id"])
    display_result(add_task1)
    
    add_task3 = ProjectAPI.add_task_to_project(project["id"], task3["id"])
    display_result(add_task3)
    
    # Get project tasks
    display_header(f"Tasks in Project: {project['name']}")
    project_tasks = ProjectAPI.get_project_tasks(project["id"])
    for task in project_tasks:
        display_result(task)
    
    # Get user projects
    display_header(f"Projects for {user1['name']}")
    user_projects = ProjectAPI.get_user_projects(user1["id"])
    for proj in user_projects:
        display_result(proj)

if __name__ == "__main__":
    main()
