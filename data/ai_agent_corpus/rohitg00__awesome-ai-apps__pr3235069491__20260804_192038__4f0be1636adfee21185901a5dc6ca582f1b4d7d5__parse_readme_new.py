#!/usr/bin/env python3
"""
Script to parse the main README.md and extract app information
to generate Hugo content files.
"""

import os
import re
import json
import yaml
import argparse
from pathlib import Path
from datetime import datetime


def parse_readme_content(readme_path):
    """Parse README.md and extract app information."""
    with open(readme_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    apps = []
    categories = {
        'starter-agents': 'Starter Agents',
        'advanced-agents': 'Advanced Agents', 
        'multi-agent-teams': 'Multi-Agent Teams',
        'rag-applications': 'RAG Applications',
        'multimodal-apps': 'Multimodal Apps'
    }
    
    # Extract each category section
    for category_key, category_name in categories.items():
        # Find the category section
        pattern = rf'### [^#]*{re.escape(category_name)}.*?\n(.*?)(?=\n### |\n## |\nTrack our progress|\Z)'
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        
        if match:
            section_content = match.group(1)
            
            # Extract individual app entries
            app_pattern = r'- <img[^>]*>\s*\*\*\[([^\]]+)\]\(([^)]+)\)\*\*\s*-\s*([^-\n]+)'
            app_matches = re.findall(app_pattern, section_content)
            
            for app_match in app_matches:
                app_name = app_match[0]
                app_path = app_match[1]
                app_description = app_match[2].strip()
                
                # Extract logo info if present
                logo_match = re.search(r'<img[^>]*src="([^"]+)"[^>]*alt="([^"]*)"', section_content)
                logo_url = logo_match.group(1) if logo_match else ""
                logo_alt = logo_match.group(2) if logo_match else ""
                
                # Extract technology from logo or description
                tech_stack = extract_tech_stack(logo_alt, app_description)
                
                app_info = {
                    'name': app_name,
                    'path': app_path,
                    'description': app_description,
                    'category': category_key,
                    'category_name': category_name,
                    'logo_url': logo_url,
                    'tech_stack': tech_stack,
                    'github_url': f"https://github.com/rohitg00/awesome-ai-apps/tree/main{app_path}"
                }
                
                apps.append(app_info)
    
    return apps


def extract_tech_stack(logo_alt, description):
    """Extract technology stack information from logo alt text and description."""
    tech_stack = []
    
    # Tech mapping from logos and descriptions
    tech_map = {
        'OpenAI': ['openai', 'gpt', 'chatgpt'],
        'Gemini': ['gemini', 'google gemini'],
        'Claude': ['claude', 'anthropic'],
        'Meta': ['meta', 'llama'],
        'ElevenLabs': ['elevenlabs', 'voice'],
        'Together AI': ['together', 'streaming'],
        'AI21': ['ai21', 'jurassic'],
        'LangChain': ['langchain'],
        'CrewAI': ['crewai', 'multi-agent'],
        'Agno': ['agno']
    }
    
    text_to_check = f"{logo_alt} {description}".lower()
    
    for tech, keywords in tech_map.items():
        if any(keyword in text_to_check for keyword in keywords):
            tech_stack.append(tech)
    
    return tech_stack


def create_app_content_file(app_info, content_dir):
    """Create a Hugo content file for an app."""
    # Create directory structure
    app_dir = content_dir / 'apps' / app_info['category']
    app_dir.mkdir(parents=True, exist_ok=True)
    
    # Create slug from app name
    slug = app_info['name'].lower().replace(' ', '-').replace('&', 'and')
    filename = f"{slug}.md"
    filepath = app_dir / filename
    
    # Create frontmatter
    frontmatter = {
        'title': app_info['name'],
        'description': app_info['description'],
        'category': app_info['category'],
        'categoryName': app_info['category_name'],
        'path': app_info['path'],
        'githubUrl': app_info['github_url'],
        'logoUrl': app_info['logo_url'],
        'techStack': app_info['tech_stack'],
        'date': datetime.now().strftime('%Y-%m-%d'),
        'draft': False,
        'weight': 1
    }
    
    # Generate content
    content = f"""---
{yaml.dump(frontmatter, default_flow_style=False)}---

# {app_info['name']}

{app_info['description']}

## Technology Stack

{', '.join(app_info['tech_stack']) if app_info['tech_stack'] else 'Not specified'}

## Links

- [View Source Code]({app_info['github_url']})
- [Local Path]({app_info['path']})

## Category

This app belongs to the **{app_info['category_name']}** category.
"""
    
    # Write file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return filepath


def create_category_pages(apps, content_dir):
    """Create category listing pages."""
    categories = {}
    
    # Group apps by category
    for app in apps:
        category = app['category']
        if category not in categories:
            categories[category] = {
                'name': app['category_name'],
                'apps': []
            }
        categories[category]['apps'].append(app)
    
    # Create category pages
    for category_key, category_data in categories.items():
        category_dir = content_dir / 'categories'
        category_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"{category_key}.md"
        filepath = category_dir / filename
        
        frontmatter = {
            'title': category_data['name'],
            'description': f"Apps in the {category_data['name']} category",
            'type': 'category',
            'layout': 'category',
            'date': datetime.now().strftime('%Y-%m-%d'),
            'draft': False
        }
        
        content = f"""---
{yaml.dump(frontmatter, default_flow_style=False)}---

# {category_data['name']}

This category contains {len(category_data['apps'])} applications.

"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)


def create_apps_index(apps, content_dir):
    """Create main apps index page."""
    apps_dir = content_dir / 'apps'
    apps_dir.mkdir(parents=True, exist_ok=True)
    
    filepath = apps_dir / '_index.md'
    
    frontmatter = {
        'title': 'All Apps',
        'description': 'Browse all AI applications in the collection',
        'type': 'apps',
        'layout': 'apps',
        'date': datetime.now().strftime('%Y-%m-%d'),
        'draft': False
    }
    
    content = f"""---
{yaml.dump(frontmatter, default_flow_style=False)}---

# All AI Applications

Browse our collection of {len(apps)} AI applications organized by category.

"""
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)


def generate_apps_data(apps, data_dir):
    """Generate JSON data file for apps."""
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Create apps data file
    apps_data_file = data_dir / 'apps.json'
    with open(apps_data_file, 'w', encoding='utf-8') as f:
        json.dump(apps, f, indent=2, ensure_ascii=False)
    
    # Create categories data file
    categories = {}
    for app in apps:
        category = app['category']
        if category not in categories:
            categories[category] = {
                'name': app['category_name'],
                'count': 0,
                'apps': []
            }
        categories[category]['count'] += 1
        categories[category]['apps'].append(app)
    
    categories_data_file = data_dir / 'categories.json'
    with open(categories_data_file, 'w', encoding='utf-8') as f:
        json.dump(categories, f, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description='Parse README.md and generate Hugo content')
    parser.add_argument('--readme', required=True, help='Path to README.md file')
    parser.add_argument('--output', required=True, help='Output directory (Hugo site root)')
    
    args = parser.parse_args()
    
    readme_path = Path(args.readme)
    output_dir = Path(args.output)
    content_dir = output_dir / 'content'
    data_dir = output_dir / 'data'
    
    # Parse README
    print("Parsing README.md...")
    apps = parse_readme_content(readme_path)
    print(f"Found {len(apps)} applications")
    
    # Generate content files
    print("Creating content files...")
    for app in apps:
        filepath = create_app_content_file(app, content_dir)
        print(f"Created: {filepath}")
    
    # Create category pages
    print("Creating category pages...")
    create_category_pages(apps, content_dir)
    
    # Create apps index
    print("Creating apps index...")
    create_apps_index(apps, content_dir)
    
    # Generate data files
    print("Generating data files...")
    generate_apps_data(apps, data_dir)
    
    print(f"Successfully processed {len(apps)} applications!")


if __name__ == '__main__':
    main()