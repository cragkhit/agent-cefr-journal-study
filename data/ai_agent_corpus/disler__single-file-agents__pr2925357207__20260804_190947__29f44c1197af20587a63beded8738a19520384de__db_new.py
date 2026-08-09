#!/usr/bin/env python3

"""
Shared database module that provides in-memory storage for the application.
"""

class InMemoryDB:
    """Simple in-memory database implementation."""
    
    def __init__(self):
        self.data = {}
        
    def create_collection(self, collection_name):
        """Create a new collection if it doesn't exist."""
        if collection_name not in self.data:
            self.data[collection_name] = {}
            
    def insert(self, collection_name, id, item):
        """Insert an item into a collection."""
        if collection_name not in self.data:
            self.create_collection(collection_name)
        self.data[collection_name][id] = item
        return id
        
    def get(self, collection_name, id):
        """Get an item from a collection by ID."""
        if collection_name not in self.data or id not in self.data[collection_name]:
            return None
        return self.data[collection_name][id]
        
    def get_all(self, collection_name):
        """Get all items from a collection."""
        if collection_name not in self.data:
            return []
        return list(self.data[collection_name].values())
        
    def update(self, collection_name, id, item):
        """Update an item in a collection."""
        if collection_name not in self.data or id not in self.data[collection_name]:
            return False
        self.data[collection_name][id] = item
        return True
        
    def delete(self, collection_name, id):
        """Delete an item from a collection."""
        if collection_name not in self.data or id not in self.data[collection_name]:
            return False
        del self.data[collection_name][id]
        return True

# Singleton database instance
db = InMemoryDB()
