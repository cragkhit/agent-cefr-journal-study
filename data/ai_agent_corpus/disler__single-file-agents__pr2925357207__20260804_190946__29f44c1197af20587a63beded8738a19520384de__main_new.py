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

if __name__ == "__main__":
    main()
