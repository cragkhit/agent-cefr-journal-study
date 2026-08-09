#!/usr/bin/env -S uv run --script

# /// script
# dependencies = [
# ]
# ///

"""
Main application entry point for the Layered Architecture example.
"""

from api.category_api import CategoryAPI
from api.product_api import ProductAPI
from utils.logger import app_logger, Logger

def display_header(text):
    """Display a header with the given text."""
    print("\n" + "=" * 50)
    print(f" {text}")
    print("=" * 50)

def display_result(result):
    """Display a result."""
    if result.get("success"):
        print("✅ " + result.get("message", "Operation successful"))
        
        if "data" in result:
            data = result["data"]
            if isinstance(data, list):
                for item in data:
                    print_item(item)
            else:
                print_item(data)
    else:
        print("❌ " + result.get("message", "Operation failed"))

def print_item(item):
    """Print an item."""
    if isinstance(item, dict):
        for key, value in item.items():
            if key not in ["created_at", "updated_at"]:
                print(f"  {key}: {value}")
        print()

def main():
    """Run the application."""
    Logger.info(app_logger, "Starting Layered Architecture Example")
    
    display_header("Layered Architecture Example")
    
    # Create categories
    display_header("Creating Categories")
    
    electronics_result = CategoryAPI.create_category("Electronics", "Electronic devices and gadgets")
    display_result(electronics_result)
    
    books_result = CategoryAPI.create_category("Books", "Books and e-books")
    display_result(books_result)
    
    clothing_result = CategoryAPI.create_category("Clothing", "Apparel and accessories")
    display_result(clothing_result)
    
    # Try to create a duplicate category
    duplicate_result = CategoryAPI.create_category("Electronics", "Duplicate category")
    display_result(duplicate_result)
    
    # Get all categories
    display_header("All Categories")
    categories_result = CategoryAPI.get_all_categories()
    display_result(categories_result)
    
    # Create products
    display_header("Creating Products")
    
    # Get category IDs
    categories = categories_result["data"]
    electronics_id = next((c["id"] for c in categories if c["name"] == "Electronics"), None)
    books_id = next((c["id"] for c in categories if c["name"] == "Books"), None)
    
    # Create products
    laptop_result = ProductAPI.create_product(
        "Laptop", 
        999.99, 
        electronics_id, 
        "High-performance laptop", 
        "TECH-001"
    )
    display_result(laptop_result)
    
    phone_result = ProductAPI.create_product(
        "Smartphone", 
        499.99, 
        electronics_id, 
        "Latest smartphone model", 
        "TECH-002"
    )
    display_result(phone_result)
    
    book_result = ProductAPI.create_product(
        "Programming Book", 
        29.99, 
        books_id, 
        "Learn programming with this book", 
        "BOOK-001"
    )
    display_result(book_result)
    
    # Try to create a product with invalid price
    invalid_result = ProductAPI.create_product(
        "Invalid Product", 
        "not-a-price", 
        electronics_id
    )
    display_result(invalid_result)
    
    # Get products by category
    display_header("Electronics Products")
    electronics_products = ProductAPI.get_products_by_category(electronics_id)
    display_result(electronics_products)
    
    # Update a product
    display_header("Updating a Product")
    if laptop_result.get("success") and "data" in laptop_result:
        laptop_id = laptop_result["data"]["id"]
        update_result = ProductAPI.update_product(
            laptop_id,
            price=899.99,
            description="High-performance laptop with discount"
        )
        display_result(update_result)
    
    # Try to delete a category with products
    display_header("Trying to Delete a Category with Products")
    delete_result = CategoryAPI.delete_category(electronics_id)
    display_result(delete_result)
    
    # Delete a product
    display_header("Deleting a Product")
    if phone_result.get("success") and "data" in phone_result:
        phone_id = phone_result["data"]["id"]
        delete_product_result = ProductAPI.delete_product(phone_id)
        display_result(delete_product_result)
    
    # Get all products
    display_header("All Remaining Products")
    all_products = ProductAPI.get_all_products()
    display_result(all_products)
    
    Logger.info(app_logger, "Layered Architecture Example completed")

if __name__ == "__main__":
    main()
