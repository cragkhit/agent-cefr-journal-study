#!/usr/bin/env python3

"""
Script to fix imports in all example files.
"""

import os
import re
import glob
import sys

def fix_imports_in_file(file_path):
    """Fix imports in a single file."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # First fix the Runner.run syntax error
    if 'from agents import Agent, Runner.run' in content:
        content = content.replace('from agents import Agent, Runner.run', 'from agents import Agent, Runner')
    
    if 'from agents import Agent, Runner.run_sync' in content:
        content = content.replace('from agents import Agent, Runner.run_sync', 'from agents import Agent, Runner')
    
    # Replace incorrect imports with correct ones based on documentation
    replacements = [
        ('from openai.agents import', 'from agents import'),
        ('import openai.agents', 'import agents'),
        ('from openai_agents import', 'from agents import'),
        ('import openai_agents', 'import agents'),
        ('from agents import Agent, run_agent', 'from agents import Agent, Runner'),
        ('from agents import Agent, run_agent_sync', 'from agents import Agent, Runner'),
        ('result = run_agent_sync', 'result = Runner.run_sync'),
        ('result = run_agent', 'result = Runner.run'),
        ('result = await run_agent_sync', 'result = await Runner.run_sync'),
        ('result = await run_agent', 'result = await Runner.run'),
        ('result.output', 'result.final_output'),
        ('return response, context', 'return result.final_output, result.context'),
        ('responses.append(response)', 'responses.append(result.final_output)'),
    ]
    
    new_content = content
    for old, new in replacements:
        new_content = new_content.replace(old, new)
    
    # Also update dependencies in the script header
    if '# dependencies = [' in new_content:
        # Update to use the correct package name and import path
        new_content = new_content.replace(
            '"openai-agents>=0.0.2",', 
            '"openai>=1.66.0",  # Includes agents module'
        )
        new_content = new_content.replace(
            '"openai>=1.66.0",  # Includes agents module', 
            '"openai>=1.66.0",  # Includes agents module'
        )
    
    if new_content != content:
        with open(file_path, 'w') as f:
            f.write(new_content)
        print(f"Fixed imports in {file_path}")
    else:
        print(f"No changes needed in {file_path}")

def create_agents_symlink():
    """Create a symlink from agents to openai.agents if needed."""
    try:
        import openai
        if hasattr(openai, 'agents'):
            # Create a symlink in site-packages
            site_packages = next(p for p in sys.path if 'site-packages' in p)
            agents_path = os.path.join(site_packages, 'agents')
            if not os.path.exists(agents_path):
                os.symlink(os.path.join(site_packages, 'openai', 'agents'), agents_path)
                print(f"Created symlink from {agents_path} to openai.agents")
            else:
                print(f"Agents path already exists at {agents_path}")
    except (ImportError, StopIteration, OSError) as e:
        print(f"Could not create symlink: {e}")

def main():
    """Fix imports in all Python files in the directory."""
    # Try to create a symlink for agents
    create_agents_symlink()
    
    # Get all Python files
    py_files = glob.glob('*.py')
    
    for file_path in py_files:
        if file_path != 'fix_imports.py':  # Skip this script
            fix_imports_in_file(file_path)
    
    print("Import fixing complete!")

if __name__ == "__main__":
    main()
