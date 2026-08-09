from flask import Blueprint, jsonify, request
import time
import logging
from github import Github
from models import TaskStatus
from utils import tasks

logger = logging.getLogger(__name__)

github_bp = Blueprint('github', __name__)

@github_bp.route('/validate-token', methods=['POST'])
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

@github_bp.route('/create-pr/<task_id>', methods=['POST'])
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