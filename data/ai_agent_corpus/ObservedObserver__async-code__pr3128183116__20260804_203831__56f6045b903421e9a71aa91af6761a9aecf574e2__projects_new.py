from flask import Blueprint, jsonify, request
import logging
from database import DatabaseOperations
import re

logger = logging.getLogger(__name__)

projects_bp = Blueprint('projects', __name__)

def parse_github_url(repo_url: str):
    """Parse GitHub URL to extract owner and repo name"""
    # Handle both https and git URLs
    patterns = [
        r'https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$',
        r'git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$'
    ]
    
    for pattern in patterns:
        match = re.match(pattern, repo_url.strip())
        if match:
            owner, repo = match.groups()
            # Remove .git suffix if present
            if repo.endswith('.git'):
                repo = repo[:-4]
            return owner, repo
    
    raise ValueError(f"Invalid GitHub URL format: {repo_url}")

@projects_bp.route('/projects', methods=['GET'])
def get_projects():
    """Get all projects for the authenticated user"""
    try:
        # For now, we'll use a dummy user_id. In production, this should come from JWT token
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return jsonify({'error': 'User ID required'}), 400
        
        projects = DatabaseOperations.get_user_projects(user_id)
        return jsonify({
            'status': 'success',
            'projects': projects
        })
        
    except Exception as e:
        logger.error(f"Error fetching projects: {str(e)}")
        return jsonify({'error': str(e)}), 500

@projects_bp.route('/projects', methods=['POST'])
def create_project():
    """Create a new project"""
    try:
        data = request.get_json()
        user_id = request.headers.get('X-User-ID')
        
        if not user_id:
            return jsonify({'error': 'User ID required'}), 400
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Required fields
        name = data.get('name')
        repo_url = data.get('repo_url')
        
        if not all([name, repo_url]):
            return jsonify({'error': 'name and repo_url are required'}), 400
        
        # Parse GitHub URL
        try:
            repo_owner, repo_name = parse_github_url(repo_url)
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        
        # Optional fields
        description = data.get('description', '')
        settings = data.get('settings', {})
        
        project = DatabaseOperations.create_project(
            user_id=user_id,
            name=name,
            description=description,
            repo_url=repo_url,
            repo_name=repo_name,
            repo_owner=repo_owner,
            settings=settings
        )
        
        return jsonify({
            'status': 'success',
            'project': project
        })
        
    except Exception as e:
        logger.error(f"Error creating project: {str(e)}")
        return jsonify({'error': str(e)}), 500

@projects_bp.route('/projects/<int:project_id>', methods=['GET'])
def get_project(project_id):
    """Get a specific project"""
    try:
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return jsonify({'error': 'User ID required'}), 400
        
        project = DatabaseOperations.get_project_by_id(project_id, user_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        return jsonify({
            'status': 'success',
            'project': project
        })
        
    except Exception as e:
        logger.error(f"Error fetching project {project_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@projects_bp.route('/projects/<int:project_id>', methods=['PUT'])
def update_project(project_id):
    """Update a project"""
    try:
        data = request.get_json()
        user_id = request.headers.get('X-User-ID')
        
        if not user_id:
            return jsonify({'error': 'User ID required'}), 400
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # If repo_url is being updated, parse it
        if 'repo_url' in data:
            try:
                repo_owner, repo_name = parse_github_url(data['repo_url'])
                data['repo_owner'] = repo_owner
                data['repo_name'] = repo_name
            except ValueError as e:
                return jsonify({'error': str(e)}), 400
        
        project = DatabaseOperations.update_project(project_id, user_id, data)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        return jsonify({
            'status': 'success',
            'project': project
        })
        
    except Exception as e:
        logger.error(f"Error updating project {project_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@projects_bp.route('/projects/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    """Delete a project"""
    try:
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return jsonify({'error': 'User ID required'}), 400
        
        success = DatabaseOperations.delete_project(project_id, user_id)
        if not success:
            return jsonify({'error': 'Project not found'}), 404
        
        return jsonify({
            'status': 'success',
            'message': 'Project deleted successfully'
        })
        
    except Exception as e:
        logger.error(f"Error deleting project {project_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@projects_bp.route('/projects/<int:project_id>/tasks', methods=['GET'])
def get_project_tasks(project_id):
    """Get all tasks for a specific project"""
    try:
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return jsonify({'error': 'User ID required'}), 400
        
        # Verify project exists and belongs to user
        project = DatabaseOperations.get_project_by_id(project_id, user_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        tasks = DatabaseOperations.get_user_tasks(user_id, project_id)
        return jsonify({
            'status': 'success',
            'tasks': tasks
        })
        
    except Exception as e:
        logger.error(f"Error fetching tasks for project {project_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500