#!/usr/bin/env python3

"""
Product service containing business logic for product management.
"""

from datetime import datetime
from data.database import db
from models.product import Product
from utils.logger import Logger, app_logger

class ProductService:
    """Service for managing products."""
    
    @staticmethod
    def create_product(name, price, category_id=None, description=None, sku=None):
        """Create a new product."""
        try:
            # Validate product data
            if not name or not isinstance(name, str):
                raise ValueError("Product name is required and must be a string")
            
            try:
                price = float(price)
                if price < 0:
                    raise ValueError()
            except (ValueError, TypeError):
                raise ValueError("Price must be a positive number")
            
            # Validate category if provided
            if category_id:
                category = db.get("categories", category_id)
                if not category:
                    raise ValueError(f"Category with ID {category_id} not found")
            
            # Validate SKU if provided
            if sku:
                existing_products = db.query("products", lambda p: p["sku"] == sku)
                if existing_products:
                    raise ValueError(f"Product with SKU '{sku}' already exists")
            
            # Create and save product
            product = Product(
                name=name,
                price=price,
                category_id=category_id,
                description=description,
                sku=sku
            )
            saved_product = db.insert("products", product.to_dict())
            Logger.info(app_logger, f"Created product: {name}")
            return saved_product
        except Exception as e:
            Logger.error(app_logger, f"Error creating product: {str(e)}", exc_info=True)
            raise
    
    @staticmethod
    def get_product(product_id):
        """Get a product by ID."""
        try:
            product_data = db.get("products", product_id)
            if not product_data:
                Logger.warning(app_logger, f"Product not found: {product_id}")
                return None
            return product_data
        except Exception as e:
            Logger.error(app_logger, f"Error getting product: {str(e)}", exc_info=True)
            raise
    
    @staticmethod
    def get_by_sku(sku):
        """Get a product by SKU."""
        try:
            products = db.query("products", lambda p: p["sku"] == sku)
            if not products:
                Logger.warning(app_logger, f"Product with SKU '{sku}' not found")
                return None
            return products[0]
        except Exception as e:
            Logger.error(app_logger, f"Error getting product by SKU: {str(e)}", exc_info=True)
            raise
    
    @staticmethod
    def get_all_products():
        """Get all products."""
        try:
            products = db.get_all("products")
            Logger.info(app_logger, f"Retrieved {len(products)} products")
            return products
        except Exception as e:
            Logger.error(app_logger, f"Error getting all products: {str(e)}", exc_info=True)
            raise
    
    @staticmethod
    def get_products_by_category(category_id):
        """Get all products in a category."""
        try:
            products = db.query("products", lambda p: p["category_id"] == category_id)
            Logger.info(app_logger, f"Retrieved {len(products)} products for category {category_id}")
            return products
        except Exception as e:
            Logger.error(app_logger, f"Error getting products by category: {str(e)}", exc_info=True)
            raise
    
    @staticmethod
    def update_product(product_id, name=None, price=None, category_id=None, description=None, sku=None):
        """Update a product."""
        try:
            # Get existing product
            product_data = db.get("products", product_id)
            if not product_data:
                Logger.warning(app_logger, f"Cannot update: Product not found: {product_id}")
                return None
            
            # Validate price if provided
            if price is not None:
                try:
                    price = float(price)
                    if price < 0:
                        raise ValueError()
                except (ValueError, TypeError):
                    raise ValueError("Price must be a positive number")
            
            # Validate category if provided
            if category_id:
                category = db.get("categories", category_id)
                if not category:
                    raise ValueError(f"Category with ID {category_id} not found")
            
            # Validate SKU if provided
            if sku and sku != product_data["sku"]:
                existing_products = db.query("products", lambda p: p["sku"] == sku and p["id"] != product_id)
                if existing_products:
                    raise ValueError(f"Product with SKU '{sku}' already exists")
            
            # Update fields
            if name:
                product_data["name"] = name
            if price is not None:
                product_data["price"] = price
            if category_id is not None:
                product_data["category_id"] = category_id
            if description is not None:
                product_data["description"] = description
            if sku is not None:
                product_data["sku"] = sku
            
            # Update timestamp
            product_data["updated_at"] = datetime.now().isoformat()
            
            # Save to database
            updated_product = db.update("products", product_id, product_data)
            Logger.info(app_logger, f"Updated product: {product_id}")
            return updated_product
        except Exception as e:
            Logger.error(app_logger, f"Error updating product: {str(e)}", exc_info=True)
            raise
    
    @staticmethod
    def delete_product(product_id):
        """Delete a product."""
        try:
            # Check if product exists
            product_data = db.get("products", product_id)
            if not product_data:
                Logger.warning(app_logger, f"Cannot delete: Product not found: {product_id}")
                return False
            
            # Delete product
            result = db.delete("products", product_id)
            Logger.info(app_logger, f"Deleted product: {product_id}")
            return result
        except Exception as e:
            Logger.error(app_logger, f"Error deleting product: {str(e)}", exc_info=True)
            raise
