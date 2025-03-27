"""
Logging configuration for the Finance Assistant CSV-based application.

This module provides a unified logging configuration for CSV-based operations
with a focus on simplicity, performance, and effective troubleshooting.
"""

import logging
import os
import sys
import json
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import traceback
from datetime import datetime
from pathlib import Path

# Import custom logging utilities with fallback for circular imports
try:
    from finance_assistant.logging_utils import (
        JSONFormatter, configure_csv_logging, log_duration,
        log_csv_operation, csv_audit_logger, get_correlation_id
    )
except ImportError as e:
    print(f"Enhanced logging unavailable, using standard logging: {str(e)}")
    # Define minimal implementations
    class JSONFormatter(logging.Formatter):
        def format(self, record):
            log_data = {
                'timestamp': self.formatTime(record),
                'level': record.levelname,
                'logger': record.name,
                'message': record.getMessage()
            }
            return json.dumps(log_data)
    
    def configure_csv_logging(app_name, log_dir='logs'):
        logger = logging.getLogger(app_name)
        console = logging.StreamHandler()
        console.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(console)
        return logger
    
    def log_duration(logger, operation_name):
        class DummyContextManager:
            def __enter__(self): pass
            def __exit__(self, *args): pass
        return DummyContextManager()
    
    def log_csv_operation(logger):
        def decorator(func):
            return func
        return decorator
    
    class DummyAuditLogger:
        def log_action(self, user, action, table=None, record_id=None, details=None):
            pass
    
    csv_audit_logger = DummyAuditLogger()
    
    def get_correlation_id():
        return "dummy-correlation-id"

def get_environment_config():
    """Get environment-specific logging configuration"""
    # Get environment (default to development if not specified)
    env = os.environ.get('ENVIRONMENT', 'development')
    
    # Default configuration
    config = {
        'environment': env,
        'log_level': logging.INFO,
        'file_logging_enabled': True,
        'console_logging_enabled': True, 
        'json_logging_enabled': True,
        'log_dir': os.environ.get('LOG_DIR', 'logs'),
        'app_name': os.environ.get('APP_NAME', 'finance_assistant'),
        'log_retention_days': int(os.environ.get('LOG_RETENTION_DAYS', 30)),
        'max_log_size_mb': int(os.environ.get('MAX_LOG_SIZE_MB', 10))
    }
    
    # Set environment-specific configurations
    if env == 'production':
        config['log_level'] = logging.WARNING
    elif env == 'staging':
        config['log_level'] = logging.INFO
    else:  # development
        config['log_level'] = logging.DEBUG
    
    return config

def safe_add_handler(logger, handler, formatter=None):
    """Safely add a handler to the logger, with error handling"""
    try:
        if formatter:
            handler.setFormatter(formatter)
        logger.addHandler(handler)
        return True
    except Exception as e:
        error_msg = f"Failed to add handler {handler.__class__.__name__}: {str(e)}"
        print(error_msg)
        traceback.print_exc()
        return False

def configure_logging(app_name=None, structured=True):
    """Configure logging for CSV-based operations
    
    Args:
        app_name: Name of the application for logging namespace
        structured: Whether to enable structured/JSON logging
        
    Returns:
        Configured logger instance
    """
    # Load configuration
    config = get_environment_config()
    app_name = app_name or config['app_name']
    
    # Create logger
    logger = logging.getLogger(app_name)
    logger.setLevel(config['log_level'])
    
    # Clear any existing handlers
    if logger.handlers:
        logger.handlers.clear()
    
    # Ensure the log directory exists
    log_dir = Path(config['log_dir'])
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Apply structured logging if enabled
    if structured:
        try:
            # Use our custom CSV logging configuration
            logger = configure_csv_logging(app_name, str(log_dir))
            logger.info(f"Structured logging configured for {app_name}")
        except Exception as e:
            print(f"Failed to configure enhanced logging: {str(e)}")
            # Fall back to basic configuration below
    
    # Set up basic handlers as fallback if needed
    if not logger.handlers:
        if config['console_logging_enabled']:
            # Add a console handler
            console_handler = logging.StreamHandler(sys.stdout)
            console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            safe_add_handler(logger, console_handler, console_formatter)
        
        if config['file_logging_enabled']:
            # Configure daily rotating file handler
            standard_file = log_dir / f"{app_name}.log"
            daily_handler = TimedRotatingFileHandler(
                standard_file,
                when='midnight',
                interval=1,
                backupCount=config['log_retention_days']
            )
            standard_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            safe_add_handler(logger, daily_handler, standard_formatter)
    
    # Log initialization
    logger.info(f"Logging initialized for {app_name} in {config['environment']} environment")
    
    return logger

def get_audit_logger():
    """Get the CSV audit logger instance"""
    return csv_audit_logger

def get_table_logger(table_name):
    """Get a logger specifically for operations on a table"""
    logger = logging.getLogger(f"tables.{table_name}")
    if not logger.handlers:
        # Inherit configuration from parent
        parent_logger = logging.getLogger('tables')
        logger.setLevel(parent_logger.level)
        
        # Configure handlers if parent doesn't have any
        if not parent_logger.handlers:
            configure_logging('tables')
    
    return logger

def log_table_operation(user, action, table, record_id=None, details=None):
    """Log a table operation to the audit log"""
    # Get the audit logger
    audit_logger = get_audit_logger()
    
    # Log the action
    audit_logger.log_action(user, action, table, record_id, details)
    
    # Also log to the regular logger
    logger = get_table_logger(table)
    logger.info(f"User '{user}' performed '{action}' on {table}{f' ID {record_id}' if record_id else ''}")

def log_application_start():
    """Log application startup information"""
    logger = logging.getLogger('finance_assistant')
    
    # Log basic application info
    logger.info("=" * 60)
    logger.info(f"Finance Assistant CSV Application starting")
    logger.info(f"Environment: {os.environ.get('ENVIRONMENT', 'development')}")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Platform: {sys.platform}")
    logger.info(f"Current directory: {os.getcwd()}")
    logger.info("=" * 60)
