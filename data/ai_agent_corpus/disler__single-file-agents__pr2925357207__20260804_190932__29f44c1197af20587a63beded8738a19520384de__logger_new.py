#!/usr/bin/env python3

"""
Logger utility for the application.
"""

import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class Logger:
    """Logger class for application logging."""
    
    @staticmethod
    def get_logger(name):
        """Get a logger instance for the given name."""
        return logging.getLogger(name)
    
    @staticmethod
    def info(logger, message):
        """Log an info message."""
        logger.info(message)
    
    @staticmethod
    def error(logger, message, exc_info=None):
        """Log an error message."""
        logger.error(message, exc_info=exc_info)
    
    @staticmethod
    def warning(logger, message):
        """Log a warning message."""
        logger.warning(message)
    
    @staticmethod
    def debug(logger, message):
        """Log a debug message."""
        logger.debug(message)

# Create a default logger
app_logger = Logger.get_logger("app")
