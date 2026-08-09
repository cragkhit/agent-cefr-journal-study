#!/usr/bin/env python3

"""
Product model definition.
"""

from datetime import datetime

class Product:
    """Product model representing a product in the catalog."""
    
    def __init__(self, name, price, category_id=None, description=None, sku=None, id=None):
        """Initialize a product."""
        self.id = id
        self.name = name
        self.price = price
        self.category_id = category_id
        self.description = description
        self.sku = sku
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
    
    def to_dict(self):
        """Convert product to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "price": self.price,
            "category_id": self.category_id,
            "description": self.description,
            "sku": self.sku,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create a product from dictionary."""
        product = cls(
            name=data["name"],
            price=data["price"],
            category_id=data.get("category_id"),
            description=data.get("description"),
            sku=data.get("sku"),
            id=data.get("id")
        )
        product.created_at = data.get("created_at", product.created_at)
        product.updated_at = data.get("updated_at", product.updated_at)
        return product
