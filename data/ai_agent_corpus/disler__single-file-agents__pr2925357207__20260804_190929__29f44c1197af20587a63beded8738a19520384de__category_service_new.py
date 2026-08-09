#!/usr/bin/env python3

"""
Category service containing business logic for category management.
"""

from datetime import datetime
from data.database import db
from models.category import Category
from utils.logger import Logger, app_logger

class CategoryService:
    """Service for managing categories."""
    
    @staticmethod
    def create_category(name, description=None):
        """Create a new category."""
        try:
            # Validate category name
            if not name or not isinstance(name, str):
                raise ValueError("Category name is required and must be a string")
            
            # Check if category with same name already exists
            existing_categories = db.query("categories", lambda c: c["name"].lower() == name.lower())
            if existing_categories:
                raise ValueError(f"Category with name '{name}' already exists")
            
            # Create and save category
            category = Category(name=name, description=description)
            saved_category = db.insert("categories", category.to_dict())
            Logger.info(app_logger, f"Created category: {name}")
            return saved_category
        except Exception as e:
            Logger.error(app_logger, f"Error creating category: {str(e)}", exc_info=True)
            raise
    
    @staticmethod
    def get_category(category_id):
        """Get a category by ID."""
        try:
            category_data = db.get("categories", category_id)
            if not category_data:
                Logger.warning(app_logger, f"Category not found: {category_id}")
                return None
            return category_data
        except Exception as e:
            Logger.error(app_logger, f"Error getting category: {str(e)}", exc_info=True)
            raise
    
    @staticmethod
    def get_all_categories():
        """Get all categories."""
        try:
            categories = db.get_all("categories")
            Logger.info(app_logger, f"Retrieved {len(categories)} categories")
            return categories
        except Exception as e:
            Logger.error(app_logger, f"Error getting all categories: {str(e)}", exc_info=True)
            raise
    
    @staticmethod
    def update_category(category_id, name=None, description=None):
        """Update a category."""
        try:
            # Get existing category
            category_data = db.get("categories", category_id)
            if not category_data:
                Logger.warning(app_logger, f"Cannot update: Category not found: {category_id}")
                return None
            
            # Check if new name already exists
            if name and name != category_data["name"]:
                existing_categories = db.query("categories", lambda c: c["name"].lower() == name.lower() and c["id"] != category_id)
                if existing_categories:
                    raise ValueError(f"Category with name '{name}' already exists")
            
            # Update fields
            if name:
                category_data["name"] = name
            if description is not None:
                category_data["description"] = description
            
            # Update timestamp
            category_data["updated_at"] = datetime.now().isoformat()
            
            # Save to database
            updated_category = db.update("categories", category_id, category_data)
            Logger.info(app_logger, f"Updated category: {category_id}")
            return updated_category
        except Exception as e:
            Logger.error(app_logger, f"Error updating category: {str(e)}", exc_info=True)
            raise
    
    @staticmethod
    def delete_category(category_id):
        """Delete a category."""
        try:
            # Check if category exists
            category_data = db.get("categories", category_id)
            if not category_data:
                Logger.warning(app_logger, f"Cannot delete: Category not found: {category_id}")
                return False
            
            # Check if category has products
            products = db.query("products", lambda p: p["category_id"] == category_id)
            if products:
                raise ValueError(f"Cannot delete category: {len(products)} products are associated with this category")
            
            # Delete category
            result = db.delete("categories", category_id)
            Logger.info(app_logger, f"Deleted category: {category_id}")
            return result
        except Exception as e:
            Logger.error(app_logger, f"Error deleting category: {str(e)}", exc_info=True)
            raise
