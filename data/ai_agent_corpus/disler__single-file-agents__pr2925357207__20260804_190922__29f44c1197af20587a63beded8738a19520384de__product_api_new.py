#!/usr/bin/env python3

"""
Product API endpoints.
"""

from services.product_service import ProductService
from utils.logger import Logger, app_logger

class ProductAPI:
    """API endpoints for product management."""
    
    @staticmethod
    def create_product(name, price, category_id=None, description=None, sku=None):
        """Create a new product."""
        try:
            product = ProductService.create_product(name, price, category_id, description, sku)
            return {
                "success": True,
                "message": "Product created successfully",
                "data": product
            }
        except ValueError as e:
            Logger.warning(app_logger, f"Validation error in create_product: {str(e)}")
            return {
                "success": False,
                "message": str(e)
            }
        except Exception as e:
            Logger.error(app_logger, f"Error in create_product: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": "An error occurred while creating the product"
            }
    
    @staticmethod
    def get_product(product_id):
        """Get a product by ID."""
        try:
            product = ProductService.get_product(product_id)
            if not product:
                return {
                    "success": False,
                    "message": f"Product with ID {product_id} not found"
                }
            return {
                "success": True,
                "data": product
            }
        except Exception as e:
            Logger.error(app_logger, f"Error in get_product: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": "An error occurred while retrieving the product"
            }
    
    @staticmethod
    def get_by_sku(sku):
        """Get a product by SKU."""
        try:
            product = ProductService.get_by_sku(sku)
            if not product:
                return {
                    "success": False,
                    "message": f"Product with SKU '{sku}' not found"
                }
            return {
                "success": True,
                "data": product
            }
        except Exception as e:
            Logger.error(app_logger, f"Error in get_by_sku: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": "An error occurred while retrieving the product"
            }
    
    @staticmethod
    def get_all_products():
        """Get all products."""
        try:
            products = ProductService.get_all_products()
            return {
                "success": True,
                "data": products
            }
        except Exception as e:
            Logger.error(app_logger, f"Error in get_all_products: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": "An error occurred while retrieving products"
            }
    
    @staticmethod
    def get_products_by_category(category_id):
        """Get all products in a category."""
        try:
            products = ProductService.get_products_by_category(category_id)
            return {
                "success": True,
                "data": products
            }
        except Exception as e:
            Logger.error(app_logger, f"Error in get_products_by_category: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": "An error occurred while retrieving products"
            }
    
    @staticmethod
    def update_product(product_id, name=None, price=None, category_id=None, description=None, sku=None):
        """Update a product."""
        try:
            product = ProductService.update_product(product_id, name, price, category_id, description, sku)
            if not product:
                return {
                    "success": False,
                    "message": f"Product with ID {product_id} not found"
                }
            return {
                "success": True,
                "message": "Product updated successfully",
                "data": product
            }
        except ValueError as e:
            Logger.warning(app_logger, f"Validation error in update_product: {str(e)}")
            return {
                "success": False,
                "message": str(e)
            }
        except Exception as e:
            Logger.error(app_logger, f"Error in update_product: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": "An error occurred while updating the product"
            }
    
    @staticmethod
    def delete_product(product_id):
        """Delete a product."""
        try:
            result = ProductService.delete_product(product_id)
            if not result:
                return {
                    "success": False,
                    "message": f"Product with ID {product_id} not found"
                }
            return {
                "success": True,
                "message": "Product deleted successfully"
            }
        except Exception as e:
            Logger.error(app_logger, f"Error in delete_product: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": "An error occurred while deleting the product"
            }
