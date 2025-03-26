"""
Logging utilities and enhancements for the Financial Assistant application.
Provides structured logging, performance tracking, and custom formatters.
"""

import logging
import time
import uuid
import functools
import json
import traceback
import os
import socket
from contextlib import contextmanager
from datetime import datetime

# Constants for log levels mapping to integers for easy filtering
LOG_LEVELS = {
    'DEBUG': 10,
    'INFO': 20,
    'WARNING': 30,
    'ERROR': 40,
    'CRITICAL': 50
}

class StructuredLogRecord(logging.LogRecord):
    """Enhanced LogRecord with additional structured data fields."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add hostname for distributed deployments
        self.hostname = socket.gethostname()
        # Add unique identifier for log correlation
        self.log_id = str(uuid.uuid4())
        # Add timestamp in ISO format for easier parsing
        self.iso_timestamp = datetime.utcnow().isoformat() + 'Z'

class StructuredLogger(logging.Logger):
    """Logger that creates StructuredLogRecord instances."""
    
    def makeRecord(self, name, level, fn, lno, msg, args, exc_info,
                  func=None, extra=None, sinfo=None):
        """Override to use our custom LogRecord."""
        return StructuredLogRecord(name, level, fn, lno, msg, args, exc_info,
                                  func, sinfo)

# Register our custom logger class
logging.setLoggerClass(StructuredLogger)

class JSONFormatter(logging.Formatter):
    """Formatter that outputs logs as JSON objects."""
    
    def format(self, record):
        """Format the specified record as JSON."""
        # Start with the message and basic fields
        log_entry = {
            'timestamp': record.iso_timestamp,
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'log_id': record.log_id,
            'hostname': record.hostname,
            'file': record.pathname,
            'line': record.lineno,
            'function': record.funcName
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # Add extra attributes from record
        for key, value in record.__dict__.items():
            if key not in log_entry and not key.startswith('_') and key != 'args':
                try:
                    json.dumps({key: value})  # Check if serializable
                    log_entry[key] = value
                except (TypeError, OverflowError):
                    log_entry[key] = str(value)  # Convert to string if not serializable
        
        return json.dumps(log_entry)

@contextmanager
def log_execution_time(logger, operation_name, log_level=logging.INFO, extra=None):
    """Context manager to log the execution time of a block of code.
    
    Args:
        logger: The logger instance to use
        operation_name: Name of the operation being timed
        log_level: Logging level to use
        extra: Additional fields to include in the log
    
    Example:
        with log_execution_time(logger, "Database query"):
            results = db.execute_query("SELECT * FROM users")
    """
    start_time = time.time()
    extra_data = extra or {}
    
    try:
        yield
    except Exception as e:
        elapsed_time = time.time() - start_time
        
        log_data = {
            'operation': operation_name,
            'duration_ms': round(elapsed_time * 1000, 2),
            'status': 'error',
            'error': str(e),
            **extra_data
        }
        
        logger.log(log_level, f"{operation_name} failed after {log_data['duration_ms']}ms", extra=log_data)
        raise
    else:
        elapsed_time = time.time() - start_time
        
        log_data = {
            'operation': operation_name,
            'duration_ms': round(elapsed_time * 1000, 2),
            'status': 'success',
            **extra_data
        }
        
        logger.log(log_level, f"{operation_name} completed in {log_data['duration_ms']}ms", extra=log_data)

def log_method_calls(logger, log_level=logging.DEBUG):
    """Decorator to log method calls with parameters and execution time.
    
    Args:
        logger: The logger instance to use
        log_level: Logging level to use
        
    Example:
        @log_method_calls(logger)
        def process_data(self, data, options=None):
            # Method implementation
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate a unique ID for this call
            call_id = str(uuid.uuid4())[:8]
            
            # Format the call arguments (skip self)
            arg_str = ', '.join([repr(a) for a in args[1:]]) if len(args) > 1 else ''
            kwarg_str = ', '.join([f"{k}={repr(v)}" for k, v in kwargs.items()])
            params = ', '.join(filter(None, [arg_str, kwarg_str]))
            
            # Get method information
            method_name = func.__name__
            class_name = args[0].__class__.__name__ if args else None
            full_name = f"{class_name}.{method_name}" if class_name else method_name
            
            # Log method entry
            logger.log(log_level, f"CALL:{call_id} → {full_name}({params})")
            
            # Execute and time the method
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                # Log method exit
                elapsed_ms = (time.time() - start_time) * 1000
                logger.log(log_level, f"RETURN:{call_id} ← {full_name} completed in {elapsed_ms:.2f}ms")
                return result
            except Exception as e:
                # Log method exception
                elapsed_ms = (time.time() - start_time) * 1000
                logger.log(logging.ERROR, 
                          f"ERROR:{call_id} ← {full_name} failed in {elapsed_ms:.2f}ms: {type(e).__name__}: {str(e)}")
                raise
        
        return wrapper
    
    return decorator

def configure_enhanced_logging(logger, include_json=True):
    """Configure a logger with enhanced formatting and handlers.
    
    Args:
        logger: The logger instance to configure
        include_json: Whether to add JSON formatting
        
    Returns:
        The configured logger
    """
    # Create a standard formatter for console output
    standard_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Configure console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(standard_formatter)
    logger.addHandler(console_handler)
    
    # Add JSON formatter if requested
    if include_json:
        try:
            # Create logs directory if it doesn't exist
            os.makedirs('logs', exist_ok=True)
            
            # Add a file handler with JSON formatting
            json_handler = logging.FileHandler('logs/app_structured.jsonl')
            
            # Check if JSONFormatter is available (might not be in case of circular imports)
            if 'JSONFormatter' in globals():
                json_handler.setFormatter(JSONFormatter())
                logger.addHandler(json_handler)
            else:
                # Fall back to standard formatter if JSON formatter isn't available
                json_handler.setFormatter(standard_formatter)
                logger.addHandler(json_handler)
                logger.warning("JSONFormatter not available, using standard formatter for JSON file")
        except Exception as e:
            logger.warning(f"Could not configure JSON logging: {str(e)}")
    
    return logger
