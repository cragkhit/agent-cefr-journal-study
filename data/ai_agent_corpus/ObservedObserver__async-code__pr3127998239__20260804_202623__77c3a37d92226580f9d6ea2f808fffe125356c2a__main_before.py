from flask import Flask, jsonify, request
from flask_cors import CORS
import docker
import os
import subprocess
import json
import time
import threading
from github import Github
from dotenv import load_dotenv
import uuid
import logging
import time

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Docker client
docker_client = docker.from_env()

# In-memory task storage (for MVP - in production use proper database)
tasks = {}

# Simple persistence for tasks (save to file)
TASKS_FILE = 'tasks_backup.json'

def save_tasks():
    """Save tasks to file for persistence"""
    try:
        with open(TASKS_FILE, 'w') as f:
            json.dump(tasks, f, indent=2, default=str)
        logger.info(f"💾 Saved {len(tasks)} tasks to {TASKS_FILE}")
    except Exception as e:
        logger.warning(f"⚠️ Failed to save tasks: {e}")

def load_tasks():
    """Load tasks from file"""
    global tasks
    try:
        if os.path.exists(TASKS_FILE):
            with open(TASKS_FILE, 'r') as f:
                tasks = json.load(f)
            logger.info(f"📂 Loaded {len(tasks)} tasks from {TASKS_FILE}")
        else:
            logger.info(f"📂 No tasks file found, starting fresh")
    except Exception as e:
        logger.warning(f"⚠️ Failed to load tasks: {e}")
        tasks = {}

# Load tasks on startup
load_tasks()

class TaskStatus:
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"

@app.route('/ping', methods=['GET'])
def ping():
    """Health check endpoint"""
    return jsonify({
        'status': 'success',
        'message': 'pong',
        'timestamp': time.time()
    })

@app.route('/', methods=['GET'])
def home():
    """Root endpoint"""
    return jsonify({
        'status': 'success',
        'message': 'Claude Code Automation API',
        'endpoints': ['/ping', '/start-task', '/task-status', '/git-diff', '/create-pr']
    })

@app.route('/start-task', methods=['POST'])
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

@app.route('/task-status/<task_id>', methods=['GET'])
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

@app.route('/git-diff/<task_id>', methods=['GET'])
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

@app.route('/tasks', methods=['GET'])
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

@app.route('/validate-token', methods=['POST'])
def validate_github_token():
    """Validate GitHub token and check permissions"""
    try:
        data = request.get_json()
        github_token = data.get('github_token')
        repo_url = data.get('repo_url', '')
        
        if not github_token:
            return jsonify({'error': 'github_token is required'}), 400
        
        # Create GitHub client
        g = Github(github_token)
        
        # Test basic authentication
        user = g.get_user()
        logger.info(f"🔐 Token belongs to user: {user.login}")
        
        # Test token scopes
        rate_limit = g.get_rate_limit()
        logger.info(f"📊 Rate limit info: {rate_limit.core.remaining}/{rate_limit.core.limit}")
        
        # If repo URL provided, test repo access
        repo_info = {}
        if repo_url:
            try:
                repo_parts = repo_url.replace('https://github.com/', '').replace('.git', '')
                repo = g.get_repo(repo_parts)
                
                # Test various permissions
                permissions = {
                    'read': True,  # If we got here, we can read
                    'write': False,
                    'admin': False
                }
                
                try:
                    # Test if we can read branches
                    branches = list(repo.get_branches())
                    permissions['read_branches'] = True
                    logger.info(f"✅ Can read branches ({len(branches)} found)")
                    
                    # Test if we can create branches (this is what's actually failing)
                    test_branch_name = f"test-permissions-{int(time.time())}"
                    try:
                        # Try to create a test branch
                        main_branch = repo.get_branch(repo.default_branch)
                        test_ref = repo.create_git_ref(f"refs/heads/{test_branch_name}", main_branch.commit.sha)
                        permissions['create_branches'] = True
                        logger.info(f"✅ Can create branches - test successful")
                        
                        # Clean up test branch immediately
                        test_ref.delete()
                        logger.info(f"🧹 Cleaned up test branch")
                        
                    except Exception as branch_error:
                        permissions['create_branches'] = False
                        logger.warning(f"❌ Cannot create branches: {branch_error}")
                        
                except Exception as e:
                    permissions['read_branches'] = False
                    permissions['create_branches'] = False
                    logger.warning(f"❌ Cannot read branches: {e}")
                
                try:
                    # Check if we can write (without actually writing)
                    repo_perms = repo.permissions
                    permissions['write'] = repo_perms.push
                    permissions['admin'] = repo_perms.admin
                    logger.info(f"📋 Repo permissions: push={repo_perms.push}, admin={repo_perms.admin}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not check repo permissions: {e}")
                
                repo_info = {
                    'name': repo.full_name,
                    'private': repo.private,
                    'permissions': permissions,
                    'default_branch': repo.default_branch
                }
                
            except Exception as repo_error:
                return jsonify({
                    'error': f'Cannot access repository: {str(repo_error)}',
                    'user': user.login
                }), 403
        
        return jsonify({
            'status': 'success',
            'user': user.login,
            'repo': repo_info,
            'message': 'Token is valid and has repository access'
        })
        
    except Exception as e:
        logger.error(f"Token validation error: {str(e)}")
        return jsonify({'error': f'Token validation failed: {str(e)}'}), 401

@app.route('/create-pr/<task_id>', methods=['POST'])
def create_pull_request(task_id):
    """Create a pull request by applying the saved patch to a fresh repo clone"""
    try:
        logger.info(f"🔍 PR creation requested for task: {task_id}")
        logger.info(f"📋 Available tasks: {list(tasks.keys())}")
        
        if task_id not in tasks:
            logger.error(f"❌ Task {task_id} not found. Available tasks: {list(tasks.keys())}")
            return jsonify({
                'error': 'Task not found', 
                'task_id': task_id,
                'available_tasks': list(tasks.keys())
            }), 404
        
        task = tasks[task_id]
        
        if task['status'] != TaskStatus.COMPLETED:
            return jsonify({'error': 'Task not completed yet'}), 400
            
        if not task.get('git_patch'):
            return jsonify({'error': 'No patch data available for this task'}), 400
        
        data = request.get_json() or {}
        pr_title = data.get('title', f"Claude Code: {task['prompt'][:50]}...")
        pr_body = data.get('body', f"Automated changes generated by Claude Code.\n\nPrompt: {task['prompt']}\n\nChanged files:\n" + '\n'.join(f"- {f}" for f in task.get('changed_files', [])))
        
        logger.info(f"🚀 Creating PR for task {task_id}")
        
        # Extract repo info from URL
        repo_parts = task['repo_url'].replace('https://github.com/', '').replace('.git', '')
        
        # Create GitHub client
        g = Github(task['github_token'])
        repo = g.get_repo(repo_parts)
        
        # Determine branch strategy
        base_branch = task['branch']
        pr_branch = f"claude-code-{task_id[:8]}"
        
        logger.info(f"📋 Creating PR branch '{pr_branch}' from base '{base_branch}'")
        
        # Get the latest commit from the base branch
        base_branch_obj = repo.get_branch(base_branch)
        base_sha = base_branch_obj.commit.sha
        
        # Create new branch for the PR
        try:
            # Check if branch already exists
            try:
                existing_branch = repo.get_branch(pr_branch)
                logger.warning(f"⚠️ Branch '{pr_branch}' already exists, deleting it first...")
                repo.get_git_ref(f"heads/{pr_branch}").delete()
                logger.info(f"🗑️ Deleted existing branch '{pr_branch}'")
            except:
                pass  # Branch doesn't exist, which is what we want
            
            # Create the new branch
            new_ref = repo.create_git_ref(f"refs/heads/{pr_branch}", base_sha)
            logger.info(f"✅ Created branch '{pr_branch}' from {base_sha[:8]}")
            
        except Exception as branch_error:
            logger.error(f"❌ Failed to create branch '{pr_branch}': {str(branch_error)}")
            
            # Provide specific error messages based on the error
            error_msg = str(branch_error).lower()
            if "resource not accessible" in error_msg:
                detailed_error = (
                    f"GitHub token lacks permission to create branches. "
                    f"Please ensure your token has 'repo' scope (not just 'public_repo'). "
                    f"Error: {branch_error}"
                )
            elif "already exists" in error_msg:
                detailed_error = f"Branch '{pr_branch}' already exists. Please try again or use a different task."
            else:
                detailed_error = f"Failed to create branch '{pr_branch}': {branch_error}"
                
            return jsonify({'error': detailed_error}), 403
        
        # Apply the patch by creating/updating files
        logger.info(f"📦 Applying patch with {len(task['changed_files'])} changed files...")
        
        # Parse the patch to extract file changes
        patch_content = task['git_patch']
        files_to_update = apply_patch_to_github_repo(repo, pr_branch, patch_content, task)
        
        if not files_to_update:
            return jsonify({'error': 'Failed to apply patch - no file changes extracted'}), 500
        
        logger.info(f"✅ Applied patch, updated {len(files_to_update)} files")
        
        # Create pull request
        pr = repo.create_pull(
            title=pr_title,
            body=pr_body,
            head=pr_branch,
            base=base_branch
        )
        
        logger.info(f"🎉 Created PR #{pr.number}: {pr.html_url}")
        
        return jsonify({
            'status': 'success',
            'pr_url': pr.html_url,
            'pr_number': pr.number,
            'branch': pr_branch,
            'files_updated': len(files_to_update)
        })
        
    except Exception as e:
        logger.error(f"Error creating PR: {str(e)}")
        return jsonify({'error': str(e)}), 500

def apply_patch_to_github_repo(repo, branch, patch_content, task):
    """Apply a git patch to a GitHub repository using the GitHub API"""
    try:
        logger.info(f"🔧 Parsing patch content...")
        
        # Parse git patch format to extract file changes
        files_to_update = {}
        current_file = None
        new_content_lines = []
        
        # This is a simplified patch parser - for production you might want a more robust one
        lines = patch_content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Look for file headers in patch format
            if line.startswith('--- a/') or line.startswith('--- /dev/null'):
                # Next line should be +++ b/filename
                if i + 1 < len(lines) and lines[i + 1].startswith('+++ b/'):
                    current_file = lines[i + 1][6:]  # Remove '+++ b/'
                    logger.info(f"📄 Found file change: {current_file}")
                    
                    # Get the original file content if it exists
                    try:
                        file_obj = repo.get_contents(current_file, ref=branch)
                        original_content = file_obj.decoded_content.decode('utf-8')
                        logger.info(f"📥 Got original content for {current_file}")
                    except:
                        original_content = ""  # New file
                        logger.info(f"📝 New file: {current_file}")
                    
                    # For simplicity, we'll reconstruct the file from the diff
                    # Skip to the actual diff content (after @@)
                    j = i + 2
                    while j < len(lines) and not lines[j].startswith('@@'):
                        j += 1
                    
                    if j < len(lines):
                        # Apply the diff changes
                        new_content = apply_diff_to_content(original_content, lines[j:], current_file)
                        if new_content is not None:
                            files_to_update[current_file] = new_content
                            logger.info(f"✅ Prepared update for {current_file}")
                    
                    i = j
            i += 1
        
        # Now update all the files via GitHub API
        updated_files = []
        commit_message = f"Claude Code: {task['prompt'][:100]}"
        
        for file_path, new_content in files_to_update.items():
            try:
                # Check if file exists
                try:
                    file_obj = repo.get_contents(file_path, ref=branch)
                    # Update existing file
                    repo.update_file(
                        path=file_path,
                        message=commit_message,
                        content=new_content,
                        sha=file_obj.sha,
                        branch=branch
                    )
                    logger.info(f"📝 Updated existing file: {file_path}")
                except:
                    # Create new file
                    repo.create_file(
                        path=file_path,
                        message=commit_message,
                        content=new_content,
                        branch=branch
                    )
                    logger.info(f"🆕 Created new file: {file_path}")
                
                updated_files.append(file_path)
                
            except Exception as file_error:
                logger.error(f"❌ Failed to update {file_path}: {file_error}")
        
        return updated_files
        
    except Exception as e:
        logger.error(f"💥 Error applying patch: {str(e)}")
        return []

def apply_diff_to_content(original_content, diff_lines, filename):
    """Apply diff changes to original content - simplified implementation"""
    try:
        # For now, let's use a simple approach: reconstruct from + lines
        # This is not a complete diff parser, but works for basic cases
        
        result_lines = []
        original_lines = original_content.split('\n') if original_content else []
        
        # Find the actual diff content starting from @@ line
        diff_start = 0
        for i, line in enumerate(diff_lines):
            if line.startswith('@@'):
                diff_start = i + 1
                break
        
        # Simple reconstruction: take context and + lines, skip - lines
        for line in diff_lines[diff_start:]:
            if line.startswith('+++') or line.startswith('---'):
                continue
            elif line.startswith('+') and not line.startswith('+++'):
                result_lines.append(line[1:])  # Remove the +
            elif line.startswith(' '):  # Context line
                result_lines.append(line[1:])  # Remove the space
            elif line.startswith('-'):
                continue  # Skip removed lines
            elif line.strip() == '':
                continue  # Skip empty lines in diff
            else:
                # Check if we've reached the next file
                if line.startswith('diff --git') or line.startswith('--- a/'):
                    break
        
        # If we got content, return it, otherwise fall back to using the git diff directly
        if result_lines:
            return '\n'.join(result_lines)
        else:
            # Fallback: return original content (no changes applied)
            logger.warning(f"⚠️ Could not parse diff for {filename}, keeping original")
            return original_content
            
    except Exception as e:
        logger.error(f"❌ Error applying diff to {filename}: {str(e)}")
        return None

def run_ai_code_task(task_id):
    """Run AI Code automation (Claude or Codex) in a container"""
    try:
        task = tasks[task_id]
        task['status'] = TaskStatus.RUNNING
        
        model_name = task.get('model', 'claude').upper()
        logger.info(f"🚀 Starting {model_name} Code task {task_id}")
        logger.info(f"📋 Task details: prompt='{task['prompt'][:50]}...', repo={task['repo_url']}, branch={task['branch']}, model={model_name}")
        logger.info(f"Starting {model_name} task {task_id}")
        
        # Escape special characters in prompt for shell safety
        escaped_prompt = task['prompt'].replace('"', '\\"').replace('$', '\\$').replace('`', '\\`')
        
        # Create container environment variables
        env_vars = {
            'CI': 'true',  # Indicate we're in CI/non-interactive environment
            'TERM': 'dumb',  # Use dumb terminal to avoid interactive features
            'NO_COLOR': '1',  # Disable colors for cleaner output
            'FORCE_COLOR': '0',  # Disable colors for cleaner output
            'NONINTERACTIVE': '1',  # Common flag for non-interactive mode
            'DEBIAN_FRONTEND': 'noninteractive',  # Non-interactive package installs
        }
        
        # Add model-specific API keys and environment variables
        model_cli = task.get('model', 'claude')
        if model_cli == 'claude':
            env_vars.update({
                'ANTHROPIC_API_KEY': os.getenv('ANTHROPIC_API_KEY'),
                'ANTHROPIC_NONINTERACTIVE': '1'  # Custom flag for Anthropic tools
            })
        elif model_cli == 'codex':
            env_vars.update({
                'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
                'OPENAI_NONINTERACTIVE': '1',  # Custom flag for OpenAI tools
                'CODEX_QUIET_MODE': '1'  # Official Codex non-interactive flag
            })
        
        # Use specialized container images based on model
        if model_cli == 'codex':
            container_image = 'codex-automation:latest'
        else:
            container_image = 'claude-code-automation:latest'
        
        # Create the command to run in container
        container_command = f'''
set -e
echo "Setting up repository..."

# Clone repository
git clone -b {task['branch']} {task['repo_url']} /workspace/repo
cd /workspace/repo

# Configure git
git config user.email "claude-code@automation.com"
git config user.name "Claude Code Automation"

# We'll extract the patch instead of pushing directly
echo "📋 Will extract changes as patch for later PR creation..."

echo "Starting {model_cli.upper()} Code with prompt..."

# Create a temporary file with the prompt
echo "{escaped_prompt}" > /tmp/prompt.txt

# Check which CLI tool to use based on model selection
if [ "{model_cli}" = "codex" ]; then
    echo "Using Codex (OpenAI Codex) CLI..."
    
    # Set environment variables for non-interactive mode
    export CODEX_QUIET_MODE=1
    
    # Read the prompt from file
    PROMPT_TEXT=$(cat /tmp/prompt.txt)
    
    # Check for codex installation
    if [ -f /usr/local/bin/codex ]; then
        echo "Found codex at /usr/local/bin/codex"
        echo "Running Codex in non-interactive mode..."
        
        # Use non-interactive flags for Docker environment
        # --dangerously-auto-approve-everything is required when running in Docker
        /usr/local/bin/codex --quiet --approval-mode full-auto --dangerously-auto-approve-everything "$PROMPT_TEXT"
        CODEX_EXIT_CODE=$?
        echo "Codex finished with exit code: $CODEX_EXIT_CODE"
        
        if [ $CODEX_EXIT_CODE -ne 0 ]; then
            echo "ERROR: Codex failed with exit code $CODEX_EXIT_CODE"
            exit $CODEX_EXIT_CODE
        fi
        
        echo "✅ Codex completed successfully"
    elif command -v codex >/dev/null 2>&1; then
        echo "Using codex from PATH..."
        echo "Running Codex in non-interactive mode..."
        
        # Use non-interactive flags for Docker environment
        # --dangerously-auto-approve-everything is required when running in Docker
        codex --quiet --approval-mode full-auto --dangerously-auto-approve-everything "$PROMPT_TEXT"
        CODEX_EXIT_CODE=$?
        echo "Codex finished with exit code: $CODEX_EXIT_CODE"
        if [ $CODEX_EXIT_CODE -ne 0 ]; then
            echo "ERROR: Codex failed with exit code $CODEX_EXIT_CODE"
            exit $CODEX_EXIT_CODE
        fi
        echo "✅ Codex completed successfully"
    else
        echo "ERROR: codex command not found anywhere"
        echo "Please ensure Codex CLI is installed in the container"
        exit 1
    fi
    
else
    echo "Using Claude CLI..."
    
    # Try different ways to invoke claude
    echo "Checking claude installation..."

if [ -f /usr/local/bin/claude ]; then
    echo "Found claude at /usr/local/bin/claude"
    echo "File type:"
    file /usr/local/bin/claude || echo "file command not available"
    echo "First few lines:"
    head -5 /usr/local/bin/claude || echo "head command failed"
    
    # Check if it's a shell script
    if head -1 /usr/local/bin/claude | grep -q "#!/bin/sh\|#!/bin/bash\|#!/usr/bin/env bash"; then
        echo "Detected shell script, running with sh..."
        sh /usr/local/bin/claude < /tmp/prompt.txt
    # Check if it's a Node.js script (including env -S node pattern)
    elif head -1 /usr/local/bin/claude | grep -q "#!/usr/bin/env.*node\|#!/usr/bin/node"; then
        echo "Detected Node.js script..."
        if command -v node >/dev/null 2>&1; then
            echo "Running with node..."
            # Try different approaches for Claude CLI
            
            # First try with --help to see available options
            echo "Checking claude options..."
            node /usr/local/bin/claude --help 2>/dev/null || echo "Help not available"
            
            # Try non-interactive approaches
            echo "Attempting non-interactive execution..."
            
            # Method 1: Use the official --print flag for non-interactive mode
            echo "Using --print flag for non-interactive mode..."
            cat /tmp/prompt.txt | node /usr/local/bin/claude --print --allowedTools "Edit,Bash"
            CLAUDE_EXIT_CODE=$?
            echo "Claude Code finished with exit code: $CLAUDE_EXIT_CODE"
            
            if [ $CLAUDE_EXIT_CODE -ne 0 ]; then
                echo "ERROR: Claude Code failed with exit code $CLAUDE_EXIT_CODE"
                exit $CLAUDE_EXIT_CODE
            fi
            
            echo "✅ Claude Code completed successfully"
        else
            echo "Node.js not found, trying direct execution..."
            /usr/local/bin/claude < /tmp/prompt.txt
            CLAUDE_EXIT_CODE=$?
            echo "Claude Code finished with exit code: $CLAUDE_EXIT_CODE"
            if [ $CLAUDE_EXIT_CODE -ne 0 ]; then
                echo "ERROR: Claude Code failed with exit code $CLAUDE_EXIT_CODE"
                exit $CLAUDE_EXIT_CODE
            fi
            echo "✅ Claude Code completed successfully"
        fi
    # Check if it's a Python script
    elif head -1 /usr/local/bin/claude | grep -q "#!/usr/bin/env python\|#!/usr/bin/python"; then
        echo "Detected Python script..."
        if command -v python3 >/dev/null 2>&1; then
            echo "Running with python3..."
            python3 /usr/local/bin/claude < /tmp/prompt.txt
            CLAUDE_EXIT_CODE=$?
        elif command -v python >/dev/null 2>&1; then
            echo "Running with python..."
            python /usr/local/bin/claude < /tmp/prompt.txt
            CLAUDE_EXIT_CODE=$?
        else
            echo "Python not found, trying direct execution..."
            /usr/local/bin/claude < /tmp/prompt.txt
            CLAUDE_EXIT_CODE=$?
        fi
        echo "Claude Code finished with exit code: $CLAUDE_EXIT_CODE"
        if [ $CLAUDE_EXIT_CODE -ne 0 ]; then
            echo "ERROR: Claude Code failed with exit code $CLAUDE_EXIT_CODE"
            exit $CLAUDE_EXIT_CODE
        fi
        echo "✅ Claude Code completed successfully"
    else
        echo "Unknown script type, trying direct execution..."
        /usr/local/bin/claude < /tmp/prompt.txt
        CLAUDE_EXIT_CODE=$?
        echo "Claude Code finished with exit code: $CLAUDE_EXIT_CODE"
        if [ $CLAUDE_EXIT_CODE -ne 0 ]; then
            echo "ERROR: Claude Code failed with exit code $CLAUDE_EXIT_CODE"
            exit $CLAUDE_EXIT_CODE
        fi
        echo "✅ Claude Code completed successfully"
    fi
elif command -v claude >/dev/null 2>&1; then
    echo "Using claude from PATH..."
    CLAUDE_PATH=$(which claude)
    echo "Claude found at: $CLAUDE_PATH"
    claude < /tmp/prompt.txt
    CLAUDE_EXIT_CODE=$?
    echo "Claude Code finished with exit code: $CLAUDE_EXIT_CODE"
    if [ $CLAUDE_EXIT_CODE -ne 0 ]; then
        echo "ERROR: Claude Code failed with exit code $CLAUDE_EXIT_CODE"
        exit $CLAUDE_EXIT_CODE
    fi
    echo "✅ Claude Code completed successfully"
else
    echo "ERROR: claude command not found anywhere"
    echo "Checking available interpreters:"
    which python3 2>/dev/null && echo "python3: available" || echo "python3: not found"
    which python 2>/dev/null && echo "python: available" || echo "python: not found"
    which node 2>/dev/null && echo "node: available" || echo "node: not found"
    which sh 2>/dev/null && echo "sh: available" || echo "sh: not found"
    exit 1
fi

fi  # End of model selection (claude vs codex)

# Check if there are changes
if git diff --quiet; then
    echo "No changes made"
    exit 1
fi

# Commit changes locally
git add .
git commit -m "{model_cli.capitalize()}: {escaped_prompt[:100]}"

# Get commit info
COMMIT_HASH=$(git rev-parse HEAD)
echo "COMMIT_HASH=$COMMIT_HASH"

# Generate patch file for later application
echo "📦 Generating patch file..."
git format-patch HEAD~1 --stdout > /tmp/changes.patch
echo "=== PATCH START ==="
cat /tmp/changes.patch
echo "=== PATCH END ==="

# Also get the diff for display
echo "=== GIT DIFF START ==="
git diff HEAD~1 HEAD
echo "=== GIT DIFF END ==="

# List changed files for reference
echo "=== CHANGED FILES START ==="
git diff --name-only HEAD~1 HEAD
echo "=== CHANGED FILES END ==="

# Explicitly exit with success code
echo "Container work completed successfully"
exit 0
'''
        
        # Run container with unified AI Code tools (supports both Claude and Codex)
        logger.info(f"🐳 Creating Docker container for task {task_id} using {container_image} (model: {model_name})")
        container = docker_client.containers.run(
            container_image,
            command=['bash', '-c', container_command],
            environment=env_vars,
            detach=True,
            remove=False,  # Don't auto-remove so we can get logs
            working_dir='/workspace',
            network_mode='bridge',  # Ensure proper networking
            tty=False,  # Don't allocate TTY - may prevent clean exit
            stdin_open=False  # Don't keep stdin open - may prevent clean exit
        )
        
        task['container_id'] = container.id
        logger.info(f"✅ Container created successfully: {container.id[:12]}")
        logger.info(f"⏳ Waiting for container to complete (timeout: 300s)...")
        
        # Wait for container to finish - should exit naturally when script completes
        try:
            logger.info(f"🔄 Waiting for container script to complete naturally...")
            
            # Check initial container state
            container.reload()
            logger.info(f"🔍 Container initial state: {container.status}")
            
            # Use standard wait - container should exit when bash script finishes
            logger.info(f"🔄 Calling container.wait() - container should exit when script completes...")
            result = container.wait(timeout=300)  # 5 minute timeout
            logger.info(f"🎯 Container exited naturally! Exit code: {result['StatusCode']}")
            
            # Verify final container state
            container.reload()
            logger.info(f"🔍 Final container state: {container.status}")
            
            # Get logs before any cleanup operations
            logger.info(f"📜 Retrieving container logs...")
            try:
                logs = container.logs().decode('utf-8')
                logger.info(f"📝 Retrieved {len(logs)} characters of logs")
                logger.info(f"🔍 First 200 chars of logs: {logs[:200]}...")
            except Exception as log_error:
                logger.warning(f"❌ Failed to get container logs: {log_error}")
                logs = f"Failed to retrieve logs: {log_error}"
            
            # Clean up container after getting logs
            try:
                container.reload()  # Refresh container state
                container.remove()
                logger.info(f"Successfully removed container {container.id}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to remove container {container.id}: {cleanup_error}")
                # Try force removal as fallback
                try:
                    container.remove(force=True)
                    logger.info(f"Force removed container {container.id}")
                except Exception as force_cleanup_error:
                    logger.error(f"Failed to force remove container: {force_cleanup_error}")
                
        except Exception as e:
            logger.error(f"⏰ Container timeout or error: {str(e)}")
            logger.error(f"🔄 Updating task status to FAILED due to timeout/error...")
            task['status'] = TaskStatus.FAILED
            task['error'] = f"Container execution timeout or error: {str(e)}"
            
            # Try to get logs even on error
            try:
                logs = container.logs().decode('utf-8')
            except Exception as log_error:
                logs = f"Container failed and logs unavailable: {log_error}"
            
            # Try to clean up container on error
            try:
                container.reload()  # Refresh container state
                container.remove(force=True)
                logger.info(f"Cleaned up failed container {container.id}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to remove failed container {container.id}: {cleanup_error}")
            return
        
        if result['StatusCode'] == 0:
            logger.info(f"✅ Container exited successfully (code 0) - parsing results...")
            # Parse output to extract commit hash, diff, and patch
            lines = logs.split('\n')
            commit_hash = None
            git_diff = []
            git_patch = []
            changed_files = []
            capturing_diff = False
            capturing_patch = False
            capturing_files = False
            
            for line in lines:
                if line.startswith('COMMIT_HASH='):
                    commit_hash = line.split('=', 1)[1]
                    logger.info(f"🔑 Found commit hash: {commit_hash}")
                elif line == '=== PATCH START ===':
                    capturing_patch = True
                    logger.info(f"📦 Starting to capture git patch...")
                elif line == '=== PATCH END ===':
                    capturing_patch = False
                    logger.info(f"📦 Finished capturing git patch ({len(git_patch)} lines)")
                elif line == '=== GIT DIFF START ===':
                    capturing_diff = True
                    logger.info(f"📊 Starting to capture git diff...")
                elif line == '=== GIT DIFF END ===':
                    capturing_diff = False
                    logger.info(f"📊 Finished capturing git diff ({len(git_diff)} lines)")
                elif line == '=== CHANGED FILES START ===':
                    capturing_files = True
                    logger.info(f"📁 Starting to capture changed files...")
                elif line == '=== CHANGED FILES END ===':
                    capturing_files = False
                    logger.info(f"📁 Finished capturing changed files ({len(changed_files)} files)")
                elif capturing_patch:
                    git_patch.append(line)
                elif capturing_diff:
                    git_diff.append(line)
                elif capturing_files:
                    if line.strip():  # Only add non-empty lines
                        changed_files.append(line.strip())
            
            logger.info(f"🔄 Updating task status to COMPLETED...")
            task['status'] = TaskStatus.COMPLETED
            task['commit_hash'] = commit_hash
            task['git_diff'] = '\n'.join(git_diff)
            task['git_patch'] = '\n'.join(git_patch)
            task['changed_files'] = changed_files
            
            # Save tasks after completion
            save_tasks()
            
            logger.info(f"🎉 {model_name} Task {task_id} completed successfully! Commit: {commit_hash[:8] if commit_hash else 'N/A'}, Diff lines: {len(git_diff)}")
            
        else:
            logger.error(f"❌ Container exited with error code {result['StatusCode']}")
            task['status'] = TaskStatus.FAILED
            task['error'] = f"Container exited with code {result['StatusCode']}: {logs}"
            save_tasks()  # Save failed task
            logger.error(f"💥 {model_name} Task {task_id} failed: {task['error'][:200]}...")
            
    except Exception as e:
        model_name = task.get('model', 'claude').upper()
        logger.error(f"💥 Unexpected exception in {model_name} task {task_id}: {str(e)}")
        task['status'] = TaskStatus.FAILED
        task['error'] = str(e)
        logger.error(f"🔄 {model_name} Task {task_id} failed with exception: {str(e)}")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
