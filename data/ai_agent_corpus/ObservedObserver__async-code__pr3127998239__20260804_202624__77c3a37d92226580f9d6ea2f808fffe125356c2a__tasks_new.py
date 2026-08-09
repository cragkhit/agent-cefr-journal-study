from flask import Blueprint, jsonify, request
import uuid
import time
import threading
import logging
from models import TaskStatus
from utils import tasks, save_tasks, run_ai_code_task

logger = logging.getLogger(__name__)

tasks_bp = Blueprint('tasks', __name__)

@tasks_bp.route('/start-task', methods=['POST'])
def start_task():
    """Start a new Claude Code automation task"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        prompt = data.get('prompt')
        repo_url = data.get('repo_url')
        branch = data.get('branch', 'main')
        github_token = data.get('github_token')
        model = data.get('model', 'claude')  # Default to claude for backward compatibility
        
        if not all([prompt, repo_url, github_token]):
            return jsonify({'error': 'prompt, repo_url, and github_token are required'}), 400
        
        # Validate model selection
        if model not in ['claude', 'codex']:
            return jsonify({'error': 'model must be either "claude" or "codex"'}), 400
        
        # Generate unique task ID
        task_id = str(uuid.uuid4())
        
        # Initialize task
        tasks[task_id] = {
            'id': task_id,
            'status': TaskStatus.PENDING,
            'prompt': prompt,
            'repo_url': repo_url,
            'branch': branch,
            'github_token': github_token,
            'model': model,
            'container_id': None,
            'commit_hash': None,
            'git_diff': None,
            'error': None,
            'created_at': time.time()
        }
        
        # Save tasks after creating
        save_tasks()
        
        # Start task in background thread
        thread = threading.Thread(target=run_ai_code_task, args=(task_id,))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'status': 'success',
            'task_id': task_id,
            'message': 'Task started successfully'
        })
        
    except Exception as e:
        logger.error(f"Error starting task: {str(e)}")
        return jsonify({'error': str(e)}), 500

@tasks_bp.route('/task-status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """Get the status of a specific task"""
    if task_id not in tasks:
        logger.warning(f"🔍 Frontend polling for unknown task: {task_id}")
        return jsonify({'error': 'Task not found'}), 404
    
    task = tasks[task_id]
    logger.info(f"📊 Frontend polling task {task_id}: status={task['status']}")
    
    return jsonify({
        'status': 'success',
        'task': {
            'id': task['id'],
            'status': task['status'],
            'prompt': task['prompt'],
            'repo_url': task['repo_url'],
            'branch': task['branch'],
            'model': task.get('model', 'claude'),  # Include model in response
            'commit_hash': task.get('commit_hash'),
            'changed_files': task.get('changed_files', []),
            'error': task.get('error'),
            'created_at': task['created_at']
        }
    })

@tasks_bp.route('/tasks', methods=['GET'])
def list_all_tasks():
    """List all tasks for debugging"""
    return jsonify({
        'status': 'success',
        'tasks': {
            task_id: {
                'id': task['id'],
                'status': task['status'],
                'created_at': task['created_at'],
                'prompt': task['prompt'][:50] + '...' if len(task['prompt']) > 50 else task['prompt'],
                'has_patch': bool(task.get('git_patch'))
            }
            for task_id, task in tasks.items()
        },
        'total_tasks': len(tasks)
    })