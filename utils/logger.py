import logging
import json
import os
import sys
import traceback
import time
import uuid
import random
from datetime import datetime
from functools import wraps
from contextlib import contextmanager
from logging.handlers import RotatingFileHandler

class StructuredLogFormatter(logging.Formatter):
    """Custom formatter that outputs logs as JSON objects."""
    
    def format(self, record):
        # Base log structure
        log_object = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "filename": record.filename,
            "function": record.funcName,
            "line": record.lineno,
            "process_id": record.process,
            "thread_id": record.thread,
        }
        
        # Add exception info if available
        if record.exc_info:
            log_object["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
            
        # Add any extra fields passed in the log
        if hasattr(record, "correlation_id"):
            log_object["correlation_id"] = record.correlation_id
            
        # Add all extra attributes
        for key, value in record.__dict__.items():
            if key not in ["args", "exc_info", "exc_text", "msg", "message"] and not key.startswith("_"):
                if key not in log_object and isinstance(value, (str, int, float, bool, type(None), list, dict)):
                    log_object[key] = value
        
        return json.dumps(log_object)

class ContextLogger(logging.Logger):
    """Extended logger that supports context tracking."""
    
    def __init__(self, name, level=logging.NOTSET):
        super().__init__(name, level)
        self._context = {}
    
    def bind(self, **kwargs):
        """Create a new logger with additional context data."""
        logger = self.manager.getLogger(self.name)
        logger._context = {**self._context, **kwargs}
        return logger
    
    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False, **kwargs):
        # Merge context with any extra data provided
        if extra is None:
            extra = {}
        
        # Add our context to the extra data
        context_extra = {**self._context, **extra}
        
        # If correlation_id not in context, generate one
        if "correlation_id" not in context_extra:
            context_extra["correlation_id"] = str(uuid.uuid4())
            
        # Delegate to parent implementation with our enhanced extra data
        super()._log(level, msg, args, exc_info, context_extra, stack_info, **kwargs)

class SampledLogger(ContextLogger):
    """Logger that implements sampling to reduce log volume."""
    def __init__(self, name, sample_rate=1.0, level=logging.NOTSET):
        super().__init__(name, level)
        self.sample_rate = sample_rate
        
    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False, **kwargs):
        # Skip some logs based on sample rate (always log errors and above)
        if level < logging.ERROR and self.sample_rate < 1.0:
            if random.random() > self.sample_rate:
                return
                
        super()._log(level, msg, args, exc_info, extra, stack_info, **kwargs)

# Setup our custom logger class
logging.setLoggerClass(ContextLogger)

def configure_logging(
    app_name="app",
    log_level=None,
    console_output=True,
    file_output=True,
    file_path=None,
    max_bytes=10485760,  # 10MB
    backup_count=5,
    external_handler=None,
    sample_rate=1.0,  # Add sampling capability
    log_dir='logs'  # Directory for log files
):
    """
    Configure the logging system with the given parameters.
    
    Args:
        app_name (str): Name of the application
        log_level (str): Level of logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        console_output (bool): Whether to output logs to the console
        file_output (bool): Whether to output logs to a file
        file_path (str): Path to the log file, defaults to app_name.log
        max_bytes (int): Maximum size of each log file
        backup_count (int): Number of backup log files to keep
        external_handler (logging.Handler): Additional handler for external logging services
        sample_rate (float): Percentage of logs to keep (1.0 = all, 0.1 = 10%)
        log_dir (str): Directory to store log files
    """
    # Create logs directory if it doesn't exist
    if file_output and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Determine log level from environment or parameter
    if log_level is None:
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    numeric_level = getattr(logging, log_level, logging.INFO)
    
    # Set the logger class based on sampling configuration
    if sample_rate < 1.0:
        logging.setLoggerClass(SampledLogger)
    else:
        logging.setLoggerClass(ContextLogger)
    
    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(numeric_level)
    
    # If using sampling, set the sample rate
    if sample_rate < 1.0 and isinstance(logger, SampledLogger):
        logger.sample_rate = sample_rate
    
    # Clear existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create formatter
    formatter = StructuredLogFormatter()
    
    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler
    if file_output:
        if file_path is None:
            file_path = os.path.join(log_dir, f"{app_name}.log")
        
        file_handler = RotatingFileHandler(
            file_path,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # External handler (if provided)
    if external_handler:
        external_handler.setFormatter(formatter)
        logger.addHandler(external_handler)
    
    # Return the configured logger for the application
    return logging.getLogger(app_name)

def log_execution_time(logger=None):
    """
    Decorator to log the execution time of a function.
    
    Args:
        logger: The logger to use. If None, uses the module logger.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get the appropriate logger
            log = logger or logging.getLogger(func.__module__)
            
            start_time = time.time()
            result = None
            error = None
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                error = e
                raise
            finally:
                end_time = time.time()
                execution_time = (end_time - start_time) * 1000  # Convert to ms
                
                # Create a log message
                log_data = {
                    "execution_time_ms": execution_time,
                    "function": func.__name__,
                    "module": func.__module__,
                }
                
                if error:
                    log.error(
                        f"Function {func.__name__} failed after {execution_time:.2f}ms",
                        exc_info=error,
                        extra=log_data
                    )
                else:
                    log.info(
                        f"Function {func.__name__} completed in {execution_time:.2f}ms",
                        extra=log_data
                    )
        
        return wrapper
    return decorator

@contextmanager
def log_context(logger, **context):
    """
    Context manager to temporarily add context to logs.
    
    Args:
        logger: The logger to use
        **context: The context data to add to logs
    """
    # Create a new logger with the additional context
    context_logger = logger.bind(**context)
    
    try:
        yield context_logger
    except Exception as e:
        context_logger.exception(f"Exception in log context: {str(e)}")
        raise

def log_with_error_code(logger, code, message, **kwargs):
    """
    Log with a standardized error code.
    
    Args:
        logger: The logger to use
        code: A standardized error code (e.g., "DB_CONN_001")
        message: The error message
        **kwargs: Additional context to include in the log
    """
    logger.error(message, extra={"error_code": code, **kwargs})

def log_state_transition(logger, entity, from_state, to_state, **metadata):
    """
    Log a state transition for an entity.
    
    Args:
        logger: The logger to use
        entity: The entity type (e.g., "Order", "User", "Invoice")
        from_state: The original state
        to_state: The new state
        **metadata: Additional metadata about the transition
    """
    logger.info(
        f"State transition: {entity} changed from {from_state} to {to_state}",
        extra={
            "type": "state_transition",
            "entity": entity,
            "from_state": from_state,
            "to_state": to_state,
            **metadata
        }
    ) 