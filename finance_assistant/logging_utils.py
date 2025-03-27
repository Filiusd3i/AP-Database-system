"""
Logging utilities for the Finance Assistant application.
Provides structured logging, performance tracking, and custom formatters.
Optimized for CSV-based data operations.
"""

import logging
import time
import uuid
import functools
import json
import traceback
import os
import socket
import sys
import threading
from datetime import datetime
from pathlib import Path

# Constants for log levels mapping to integers for easy filtering
LOG_LEVELS = {
    'DEBUG': 10,
    'INFO': 20,
    'WARNING': 30,
    'ERROR': 40,
    'CRITICAL': 50
}

# Thread-local storage for request/transaction IDs and context
thread_local = threading.local()

def get_correlation_id():
    """Get the current correlation ID for tracking events"""
    if not hasattr(thread_local, 'correlation_id'):
        thread_local.correlation_id = str(uuid.uuid4())
    return thread_local.correlation_id

def set_correlation_id(correlation_id):
    """Set the correlation ID for the current thread"""
    thread_local.correlation_id = correlation_id
    
def get_context():
    """Get the current logging context dictionary"""
    if not hasattr(thread_local, 'context'):
        thread_local.context = {}
    return thread_local.context.copy()

def set_context(key, value):
    """Set a value in the logging context dictionary"""
    if not hasattr(thread_local, 'context'):
        thread_local.context = {}
    thread_local.context[key] = value

def clear_context():
    """Clear the logging context dictionary"""
    if hasattr(thread_local, 'context'):
        thread_local.context.clear()

class CSVAuditLogger:
    """Logger that writes audit records to a CSV file"""
    
    def __init__(self, csv_path="logs/audit_log.csv"):
        """Initialize with path to CSV file"""
        self.csv_path = Path(csv_path)
        
        # Create directory if it doesn't exist
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create CSV file with headers if it doesn't exist
        if not self.csv_path.exists():
            import csv
            with open(self.csv_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'user', 'action', 'table', 'record_id', 
                    'details', 'correlation_id'
                ])
    
    def log_action(self, user, action, table=None, record_id=None, details=None):
        """
        Log an action to the CSV audit log
        
        Args:
            user: User performing the action
            action: Action being performed (e.g., 'create', 'update', 'delete')
            table: Table being modified
            record_id: ID of the record being modified
            details: Additional details about the action
        """
        import csv
        
        timestamp = datetime.now().isoformat()
        correlation_id = get_correlation_id()
        
        with open(self.csv_path, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                timestamp, user, action, table or '', 
                record_id or '', details or '', correlation_id
            ])

class JSONFormatter(logging.Formatter):
    """Formatter that outputs logs as JSON objects"""
    
    def __init__(self, include_stack_info=True):
        """Initialize the JSON formatter"""
        super().__init__()
        self.include_stack_info = include_stack_info
        
    def format(self, record):
        """Format the specified record as JSON structured data"""
        # Create a standardized JSON structure
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'correlation_id': getattr(record, 'correlation_id', get_correlation_id()),
            'file': record.pathname,
            'line': record.lineno,
            'function': record.funcName
        }
        
        # Add exception info if present
        if record.exc_info:
            exception_type = record.exc_info[0].__name__ if record.exc_info[0] else ''
            exception_message = str(record.exc_info[1]) if record.exc_info[1] else ''
            
            log_entry['exception'] = {
                'type': exception_type,
                'message': exception_message
            }
            
            if self.include_stack_info:
                log_entry['exception']['traceback'] = traceback.format_exception(*record.exc_info)
        
        # Add context from thread-local storage if available
        context = get_context()
        if context:
            log_entry['context'] = context
            
        # Add extra attributes from record
        for key, value in record.__dict__.items():
            # Skip internal attributes and already processed ones
            if (key not in log_entry and 
                not key.startswith('_') and
                key not in ('args', 'msg', 'levelno', 'pathname', 'filename', 
                           'module', 'exc_info', 'exc_text', 'lineno', 'funcName',
                           'created', 'msecs', 'relativeCreated', 'levelname', 'name')):
                try:
                    # Try to include the field as is
                    log_entry[key] = value
                except (TypeError, OverflowError):
                    # Convert to string if not serializable
                    log_entry[key] = str(value)
        
        return json.dumps(log_entry)

@contextmanager
def log_duration(logger, operation_name):
    """
    Context manager to log the duration of an operation
    
    Args:
        logger: Logger to use
        operation_name: Name of the operation being timed
    """
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        logger.info(f"{operation_name} completed in {duration:.3f} seconds")

def log_csv_operation(logger):
    """
    Decorator to log CSV operations and catch exceptions
    
    Args:
        logger: Logger to use
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            operation = func.__name__
            logger.debug(f"Starting {operation}")
            try:
                result = func(*args, **kwargs)
                logger.debug(f"Completed {operation}")
                return result
            except Exception as e:
                logger.error(f"Error in {operation}: {str(e)}", exc_info=True)
                raise
        return wrapper
    return decorator

def configure_csv_logging(app_name='csv_operations', log_dir='logs'):
    """
    Configure logging for CSV-based operations
    
    Args:
        app_name: Application name to use in log filenames
        log_dir: Directory to store log files
        
    Returns:
        Logger instance
    """
    # Create logs directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger(app_name)
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers
    if logger.handlers:
        logger.handlers = []
    
    # File handler for regular logs
    log_file = os.path.join(log_dir, f"{app_name}.log")
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Rotating file handler for backup
    from logging.handlers import RotatingFileHandler
    rotating_file = os.path.join(log_dir, f"{app_name}_rotating.log")
    rotating_handler = RotatingFileHandler(
        rotating_file, 
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5
    )
    rotating_handler.setLevel(logging.INFO)
    rotating_handler.setFormatter(file_formatter)
    logger.addHandler(rotating_handler)
    
    # JSON file handler for structured logs
    json_file = os.path.join(log_dir, f"{app_name}_structured.jsonl")
    json_handler = logging.FileHandler(json_file)
    json_handler.setLevel(logging.INFO)
    json_handler.setFormatter(JSONFormatter())
    logger.addHandler(json_handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(file_formatter)
    logger.addHandler(console_handler)
    
    return logger

# Global CSV audit logger instance
csv_audit_logger = CSVAuditLogger()
