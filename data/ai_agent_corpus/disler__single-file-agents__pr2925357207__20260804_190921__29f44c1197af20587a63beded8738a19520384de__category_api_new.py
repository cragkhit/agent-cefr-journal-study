#!/usr/bin/env python3

"""
Category API endpoints.
"""

from services.category_service import CategoryService
from utils.logger import Logger, app_logger

class CategoryAPI:
    """API endpoints for category management."""
    
    @staticmethod
    def create_category(name, description=None):
        """Create a new category."""
        try:
            category = CategoryService.create_category(name, description)
            return {
                "success": True,
                "message": "Category created successfully",
                "data": category
            }
        except ValueError as e:
            Logger.warning(app_logger, f"Validation error in create_category: {str(e)}")
            return {
                "success": False,
                "message": str(e)
            }
        except Exception as e:
            Logger.error(app_logger, f"Error in create_category: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": "An error occurred while creating the category"
            }
    
    @staticmethod
    def get_category(category_id):
        """Get a category by ID."""
        try:
            category = CategoryService.get_category(category_id)
            if not category:
                return {
                    "success": False,
                    "message": f"Category with ID {category_id} not found"
                }
            return {
                "success": True,
                "data": category
            }
        except Exception as e:
            Logger.error(app_logger, f"Error in get_category: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": "An error occurred while retrieving the category"
            }
    
    @staticmethod
    def get_all_categories():
        """Get all categories."""
        try:
            categories = CategoryService.get_all_categories()
            return {
                "success": True,
                "data": categories
            }
        except Exception as e:
            Logger.error(app_logger, f"Error in get_all_categories: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": "An error occurred while retrieving categories"
            }
    
    @staticmethod
    def update_category(category_id, name=None, description=None):
        """Update a category."""
        try:
            category = CategoryService.update_category(category_id, name, description)
            if not category:
                return {
                    "success": False,
                    "message": f"Category with ID {category_id} not found"
                }
            return {
                "success": True,
                "message": "Category updated successfully",
                "data": category
            }
        except ValueError as e:
            Logger.warning(app_logger, f"Validation error in update_category: {str(e)}")
            return {
                "success": False,
                "message": str(e)
            }
        except Exception as e:
            Logger.error(app_logger, f"Error in update_category: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": "An error occurred while updating the category"
            }
    
    @staticmethod
    def delete_category(category_id):
        """Delete a category."""
        try:
            result = CategoryService.delete_category(category_id)
            if not result:
                return {
                    "success": False,
                    "message": f"Category with ID {category_id} not found"
                }
            return {
                "success": True,
                "message": "Category deleted successfully"
            }
        except ValueError as e:
            Logger.warning(app_logger, f"Validation error in delete_category: {str(e)}")
            return {
                "success": False,
                "message": str(e)
            }
        except Exception as e:
            Logger.error(app_logger, f"Error in delete_category: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": "An error occurred while deleting the category"
            }
