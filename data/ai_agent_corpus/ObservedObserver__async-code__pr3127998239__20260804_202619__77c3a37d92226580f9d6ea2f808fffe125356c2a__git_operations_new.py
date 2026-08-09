from flask import Blueprint, jsonify
import logging
from models import TaskStatus
from utils import tasks

logger = logging.getLogger(__name__)

git_bp = Blueprint('git', __name__)

@git_bp.route('/git-diff/<task_id>', methods=['GET'])
def get_git_diff(task_id):
    """Get the git diff for a completed task"""
    if task_id not in tasks:
        return jsonify({'error': 'Task not found'}), 404
    
    task = tasks[task_id]
    logger.info(f"📋 Frontend requesting git diff for task {task_id} (status: {task['status']})")
    
    if task['status'] != TaskStatus.COMPLETED:
        logger.warning(f"⚠️ Git diff requested for incomplete task {task_id}")
        return jsonify({'error': 'Task not completed yet'}), 400
    
    diff_length = len(task.get('git_diff', ''))
    logger.info(f"📄 Returning git diff: {diff_length} characters")
    
    return jsonify({
        'status': 'success',
        'git_diff': task.get('git_diff', ''),
        'commit_hash': task.get('commit_hash')
    })