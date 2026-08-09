#!/usr/bin/env python3

"""
Database module for data persistence.
"""

import uuid
from utils.logger import Logger, app_logger

class InMemoryDatabase:
    """In-memory database implementation."""
    
    def __init__(self):
        """Initialize the database."""
        self.data = {}
        self.logger = Logger.get_logger("database")
        Logger.info(self.logger, "Database initialized")
    
    def create_table(self, table_name):
        """Create a new table if it doesn't exist."""
        if table_name not in self.data:
            self.data[table_name] = {}
            Logger.info(self.logger, f"Table '{table_name}' created")
    
    def insert(self, table_name, item):
        """Insert an item into a table."""
        if table_name not in self.data:
            self.create_table(table_name)
        
        # Generate ID if not provided
        if "id" not in item:
            item["id"] = str(uuid.uuid4())
        
        self.data[table_name][item["id"]] = item
        Logger.info(self.logger, f"Item inserted into '{table_name}' with ID {item['id']}")
        return item
    
    def get(self, table_name, item_id):
        """Get an item from a table by ID."""
        if table_name not in self.data or item_id not in self.data[table_name]:
            Logger.warning(self.logger, f"Item with ID {item_id} not found in '{table_name}'")
            return None
        
        Logger.debug(self.logger, f"Retrieved item with ID {item_id} from '{table_name}'")
        return self.data[table_name][item_id]
    
    def get_all(self, table_name):
        """Get all items from a table."""
        if table_name not in self.data:
            Logger.warning(self.logger, f"Table '{table_name}' not found")
            return []
        
        items = list(self.data[table_name].values())
        Logger.debug(self.logger, f"Retrieved {len(items)} items from '{table_name}'")
        return items
    
    def update(self, table_name, item_id, item):
        """Update an item in a table."""
        if table_name not in self.data or item_id not in self.data[table_name]:
            Logger.warning(self.logger, f"Cannot update: Item with ID {item_id} not found in '{table_name}'")
            return None
        
        # Ensure ID remains the same
        item["id"] = item_id
        self.data[table_name][item_id] = item
        Logger.info(self.logger, f"Updated item with ID {item_id} in '{table_name}'")
        return item
    
    def delete(self, table_name, item_id):
        """Delete an item from a table."""
        if table_name not in self.data or item_id not in self.data[table_name]:
            Logger.warning(self.logger, f"Cannot delete: Item with ID {item_id} not found in '{table_name}'")
            return False
        
        del self.data[table_name][item_id]
        Logger.info(self.logger, f"Deleted item with ID {item_id} from '{table_name}'")
        return True
    
    def query(self, table_name, filter_func):
        """Query items from a table using a filter function."""
        if table_name not in self.data:
            Logger.warning(self.logger, f"Table '{table_name}' not found for query")
            return []
        
        items = list(self.data[table_name].values())
        filtered_items = [item for item in items if filter_func(item)]
        Logger.debug(self.logger, f"Query returned {len(filtered_items)} items from '{table_name}'")
        return filtered_items

# Create a singleton database instance
db = InMemoryDatabase()
