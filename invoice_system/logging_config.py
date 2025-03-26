"""
Logging configuration for the invoice system.

This module provides a unified logging configuration for all components
of the invoice system with file and console output.
"""

import os
import sys
import logging
import logging.handlers
from datetime import datetime


def configure_logging(log_dir="logs", log_level=logging.INFO):
    """Configure logging for the invoice system.
    
    Args:
        log_dir: Directory for log files
        log_level: Default logging level
        
    Returns:
        logging.Logger: Root logger
    """
    # Create logs directory if it doesn't exist
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers if any
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Define the log file name with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"invoice_system_{timestamp}.log")
    
    # Create file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(log_level)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # Create formatter and add it to handlers
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Log initialization message
    root_logger.info(f"Logging initialized at {log_level} level, writing to {log_file}")
    
    return root_logger


def get_logger(name):
    """Get a logger with the specified name.
    
    Args:
        name: Logger name
        
    Returns:
        logging.Logger: Logger instance
    """
    return logging.getLogger(name)


class InvoiceSystemLogFilter(logging.Filter):
    """Filter for invoice system logs."""
    
    def __init__(self, name=""):
        """Initialize the filter.
        
        Args:
            name: Filter name
        """
        super().__init__(name)
    
    def filter(self, record):
        """Filter the log record.
        
        Args:
            record: Log record to filter
            
        Returns:
            bool: True if the record should be logged, False otherwise
        """
        # Add request ID if available
        if not hasattr(record, 'request_id'):
            record.request_id = ""
        
        return True 