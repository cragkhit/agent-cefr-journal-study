from flask import Blueprint, jsonify
import time

health_bp = Blueprint('health', __name__)

@health_bp.route('/ping', methods=['GET'])
def ping():
    """Health check endpoint"""
    return jsonify({
        'status': 'success',
        'message': 'pong',
        'timestamp': time.time()
    })

@health_bp.route('/', methods=['GET'])
def home():
    """Root endpoint"""
    return jsonify({
        'status': 'success',
        'message': 'Claude Code Automation API',
        'endpoints': ['/ping', '/start-task', '/task-status', '/git-diff', '/create-pr']
    })