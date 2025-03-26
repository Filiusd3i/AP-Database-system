"""
Logging utilities and enhancements for the Financial Assistant application.
Provides structured logging, performance tracking, and custom formatters with full
ELK Stack integration support.
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
import inspect
import platform
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

# Thread-local storage for request/transaction IDs and context
thread_local = threading.local()

def get_correlation_id():
    """Get the current correlation ID for tracking events in distributed systems"""
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

class StructuredLogRecord(logging.LogRecord):
    """Enhanced LogRecord with additional structured data fields for ELK Stack."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add hostname for distributed deployments
        self.hostname = socket.gethostname()
        # Add unique identifier for log correlation
        self.log_id = str(uuid.uuid4())
        # Add correlation ID for tracking events across services
        self.correlation_id = get_correlation_id()
        # Add timestamp in ISO format for easier parsing
        self.iso_timestamp = datetime.utcnow().isoformat() + 'Z'
        # Add environment information
        self.environment = os.environ.get('ENVIRONMENT', 'development')
        # Add process ID for debugging and monitoring
        self.process_id = os.getpid()
        # Add thread ID for multithreaded applications
        self.thread_id = threading.get_ident()
        # Add system information
        self.platform = sys.platform
        self.python_version = platform.python_version()
        # Add application version if available
        self.app_version = os.environ.get('APP_VERSION', '')
        # Add the thread-local context to every log record
        self.context = get_context()

class StructuredLogger(logging.Logger):
    """Logger that creates StructuredLogRecord instances with ELK Stack compatibility."""
    
    def makeRecord(self, name, level, fn, lno, msg, args, exc_info,
                  func=None, extra=None, sinfo=None):
        """Override to use our custom LogRecord."""
        # Create our enhanced structured log record
        record = StructuredLogRecord(name, level, fn, lno, msg, args, exc_info,
                                    func, sinfo)
                                    
        # Add stack information for higher levels
        if level >= logging.ERROR and not sinfo:
            # Grab more detailed stack info for errors
            record.stack_info = ''.join(traceback.format_stack(limit=10))
                    
        # Add extra fields if provided
        if extra:
            for key, value in extra.items():
                setattr(record, key, value)
                
        # Add caller information for better tracing (file, line, caller)
        if level >= logging.WARNING:
            try:
                # Get caller frame (more detailed than standard)
                frame = inspect.currentframe().f_back
                while frame and frame.f_code.co_filename.endswith(('logging_utils.py', 'logging/__init__.py')):
                    frame = frame.f_back
                
                if frame:
                    record.caller_file = os.path.basename(frame.f_code.co_filename)
                    record.caller_function = frame.f_code.co_name
                    record.caller_line = frame.f_lineno
            except Exception:
                # Don't fail logging if frame inspection fails
                pass
                
        return record
        
    def audit(self, msg, *args, **kwargs):
        """Special audit log level for security and compliance.
        
        Similar to INFO, but tagged for security monitoring.
        """
        if self.isEnabledFor(logging.INFO):
            extra = kwargs.pop('extra', {})
            extra['log_type'] = 'audit'
            extra['audit'] = True
            self.info(msg, *args, extra=extra, **kwargs)
            
    def metric(self, metric_name, value, unit=None, **kwargs):
        """Log a metric for monitoring and dashboards."""
        if self.isEnabledFor(logging.INFO):
            extra = kwargs.pop('extra', {})
            extra.update({
                'log_type': 'metric', 
                'metric_name': metric_name,
                'metric_value': value,
                'metric_unit': unit
            })
            self.info(f"METRIC {metric_name}={value}{f' {unit}' if unit else ''}", 
                     extra=extra, **kwargs)

# Register our custom logger class
logging.setLoggerClass(StructuredLogger)

class JSONFormatter(logging.Formatter):
    """Formatter that outputs logs as JSON objects optimized for ELK Stack."""
    
    def __init__(self, include_stack_info=True, max_stack_lines=20, 
                include_fields=None, exclude_fields=None):
        """Initialize the JSON formatter.
        
        Args:
            include_stack_info: Whether to include stack traces
            max_stack_lines: Maximum number of lines in stack traces
            include_fields: List of fields to include (None for all)
            exclude_fields: List of fields to exclude
        """
        super().__init__()
        self.include_stack_info = include_stack_info
        self.max_stack_lines = max_stack_lines
        self.include_fields = include_fields
        self.exclude_fields = exclude_fields or ['args', 'msg', 'levelno']
        
    def format(self, record):
        """Format the specified record as JSON."""
        # Start with the message and basic fields
        log_entry = {
            '@timestamp': record.iso_timestamp,  # ELK standard field
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'log_id': record.log_id,
            'correlation_id': getattr(record, 'correlation_id', ''),
            'hostname': record.hostname,
            'environment': getattr(record, 'environment', 'development'),
            'file': record.pathname,
            'line': record.lineno,
            'function': record.funcName,
            'process_id': getattr(record, 'process_id', os.getpid()),
            'thread_id': getattr(record, 'thread_id', threading.get_ident())
        }
        
        # Add log type for different kinds of logs
        log_entry['log_type'] = getattr(record, 'log_type', 'application')
        
        # Add context from thread-local storage if available
        context = getattr(record, 'context', {})
        if context:
            log_entry['context'] = context
        
        # Add caller information if available (for stack traces)
        if hasattr(record, 'caller_file'):
            log_entry['caller'] = {
                'file': record.caller_file,
                'function': record.caller_function,
                'line': record.caller_line
            }
        
        # Add exception info if present
        if record.exc_info:
            exception_type = record.exc_info[0].__name__ if record.exc_info[0] else ''
            exception_message = str(record.exc_info[1]) if record.exc_info[1] else ''
            
            log_entry['exception'] = {
                'type': exception_type,
                'message': exception_message
            }
            
            # Format traceback if stack info included
            if self.include_stack_info:
                traceback_lines = traceback.format_exception(*record.exc_info)
                if self.max_stack_lines and len(traceback_lines) > self.max_stack_lines:
                    traceback_lines = (
                        traceback_lines[:self.max_stack_lines-1] + 
                        [f"... (truncated, {len(traceback_lines) - self.max_stack_lines + 1} more lines)"]
                    )
                log_entry['exception']['traceback'] = traceback_lines
        
        # Add stack info if available and enabled
        if self.include_stack_info and getattr(record, 'stack_info', None):
            stack_lines = record.stack_info.splitlines()
            if self.max_stack_lines and len(stack_lines) > self.max_stack_lines:
                stack_lines = (
                    stack_lines[:self.max_stack_lines-1] + 
                    [f"... (truncated, {len(stack_lines) - self.max_stack_lines + 1} more lines)"]
                )
            log_entry['stack'] = stack_lines
        
        # Add extra attributes from record
        for key, value in record.__dict__.items():
            # Skip internal attributes, already processed ones, and excluded fields
            if (key not in log_entry and 
                not key.startswith('_') and
                key not in self.exclude_fields and
                (not self.include_fields or key in self.include_fields)):
                try:
                    json.dumps({key: value})  # Check if serializable
                    log_entry[key] = value
                except (TypeError, OverflowError):
                    log_entry[key] = str(value)  # Convert to string if not serializable
        
        return json.dumps(log_entry)

class ColoredConsoleFormatter(logging.Formatter):
    """Formatter that adds ANSI colors to console output."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[41m',  # Red background
        'RESET': '\033[0m'       # Reset
    }
    
    def __init__(self, fmt=None, datefmt=None, style='%'):
        """Initialize with optional format string."""
        super().__init__(fmt, datefmt, style)
        self.use_colors = sys.stderr.isatty()  # Only use colors for TTY
        
    def format(self, record):
        """Format the record with ANSI colors."""
        result = super().format(record)
        
        if self.use_colors:
            # Add color based on log level
            color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
            reset = self.COLORS['RESET']
            result = f"{color}{result}{reset}"
            
        return result

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
    
    # Set up special correlation ID for the operation if not already present
    if 'correlation_id' not in extra_data:
        extra_data['correlation_id'] = get_correlation_id()
    
    # Log operation start with the same correlation ID
    logger.log(log_level, f"Starting {operation_name}", extra={
        'operation': operation_name,
        'status': 'starting',
        'correlation_id': extra_data['correlation_id'],
        **extra_data
    })
    
    try:
        yield
    except Exception as e:
        elapsed_time = time.time() - start_time
        
        log_data = {
            'operation': operation_name,
            'duration_ms': round(elapsed_time * 1000, 2),
            'status': 'error',
            'error': str(e),
            'error_type': type(e).__name__,
            'correlation_id': extra_data['correlation_id'],
            **extra_data
        }
        
        logger.log(logging.ERROR if log_level < logging.ERROR else log_level, 
                  f"{operation_name} failed after {log_data['duration_ms']}ms: {str(e)}", 
                  exc_info=True, extra=log_data)
        raise
    else:
        elapsed_time = time.time() - start_time
        
        log_data = {
            'operation': operation_name,
            'duration_ms': round(elapsed_time * 1000, 2),
            'status': 'success',
            'correlation_id': extra_data['correlation_id'],
            **extra_data
        }
        
        logger.log(log_level, f"{operation_name} completed in {log_data['duration_ms']}ms", extra=log_data)

def log_method_calls(logger, log_level=logging.DEBUG, log_args=True, log_result=False, 
                    performance_threshold_ms=None):
    """Decorator to log method calls with parameters and execution time.
    
    Args:
        logger: The logger instance to use
        log_level: Logging level to use
        log_args: Whether to log method arguments
        log_result: Whether to log method return value
        performance_threshold_ms: If set, only log performance warning if 
                                 execution time exceeds this threshold
        
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
            arg_details = ""
            if log_args:
                arg_str = ', '.join([repr(a) for a in args[1:]]) if len(args) > 1 else ''
                kwarg_str = ', '.join([f"{k}={repr(v)}" for k, v in kwargs.items()])
                params = ', '.join(filter(None, [arg_str, kwarg_str]))
                arg_details = f"({params})"
            
            # Get method information
            method_name = func.__name__
            class_name = args[0].__class__.__name__ if args else None
            full_name = f"{class_name}.{method_name}" if class_name else method_name
            
            # Extract context information for logging
            extra = {
                'call_id': call_id,
                'method': full_name,
                'class': class_name,
                'function': method_name
            }
            
            # Log method entry
            logger.log(log_level, f"CALL:{call_id} → {full_name}{arg_details}", extra=extra)
            
            # Execute and time the method
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                # Calculate elapsed time
                elapsed_ms = (time.time() - start_time) * 1000
                
                # Add performance data to log context
                extra['duration_ms'] = round(elapsed_ms, 2)
                
                # Determine if this is a slow operation
                is_slow = performance_threshold_ms and elapsed_ms > performance_threshold_ms
                
                # Log at warning level for slow operations
                log_fn = logger.warning if is_slow else logger.log
                level = logging.WARNING if is_slow else log_level
                
                # Log method exit
                result_details = f" = {repr(result)}" if log_result else ""
                status = "SLOW:" if is_slow else "RETURN:"
                log_fn(level, f"{status}{call_id} ← {full_name} completed in {elapsed_ms:.2f}ms{result_details}", 
                      extra=extra)
                
                return result
            except Exception as e:
                # Calculate elapsed time
                elapsed_ms = (time.time() - start_time) * 1000
                
                # Add exception details to log context
                extra.update({
                    'duration_ms': round(elapsed_ms, 2),
                    'error': str(e),
                    'error_type': type(e).__name__
                })
                
                # Log method exception - always at ERROR level
                logger.error(
                    f"ERROR:{call_id} ← {full_name} failed in {elapsed_ms:.2f}ms: {type(e).__name__}: {str(e)}",
                    exc_info=True,
                    extra=extra
                )
                raise
        
        return wrapper
    
    return decorator

def configure_enhanced_logging(logger, include_json=True, colored_console=True):
    """Configure a logger with enhanced formatting and handlers.
    
    Args:
        logger: The logger instance to configure
        include_json: Whether to add JSON formatting
        colored_console: Whether to use colored console output
        
    Returns:
        The configured logger
    """
    # Determine if colors should be used
    use_colors = colored_console and sys.stderr.isatty()
    
    # Create a standard formatter for console output
    if use_colors:
        console_formatter = ColoredConsoleFormatter(
            '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
        )
    else:
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
        )
    
    # Configure console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # Add JSON formatter if requested
    if include_json:
        try:
            # Create logs directory if it doesn't exist
            logs_dir = os.environ.get('LOG_DIR', 'logs')
            os.makedirs(logs_dir, exist_ok=True)
            
            # Add a file handler with JSON formatting
            json_handler = logging.FileHandler(os.path.join(logs_dir, 'app_structured.jsonl'))
            
            # Create JSON formatter with appropriate configuration
            json_formatter = JSONFormatter(
                include_stack_info=True,
                max_stack_lines=30
            )
            json_handler.setFormatter(json_formatter)
            logger.addHandler(json_handler)
        except Exception as e:
            # Log the error but continue - console logging will still work
            logger.warning(f"Could not configure JSON logging: {str(e)}")
    
    return logger

# Define global log context managers for use in web frameworks and APIs
@contextmanager
def request_context(request_id=None, user_id=None, **context):
    """Context manager to set request context for all logs in this thread/request.
    
    Args:
        request_id: Unique identifier for the request
        user_id: User ID associated with the request
        **context: Additional context values to include
        
    Example:
        with request_context(request_id='123', user_id='user456', endpoint='/api/data'):
            # All logs within this block will have this context
            logger.info("Processing request")
    """
    # Generate request ID if not provided
    request_id = request_id or str(uuid.uuid4())
    
    # Save old correlation ID to restore later
    old_correlation_id = get_correlation_id() if hasattr(thread_local, 'correlation_id') else None
    
    # Save old context to restore later
    old_context = get_context()
    
    try:
        # Set correlation ID to request ID
        set_correlation_id(request_id)
        
        # Clear existing context
        clear_context()
        
        # Set new context values
        set_context('request_id', request_id)
        if user_id:
            set_context('user_id', user_id)
            
        # Set any additional context
        for key, value in context.items():
            set_context(key, value)
            
        yield
    finally:
        # Restore old correlation ID
        if old_correlation_id:
            set_correlation_id(old_correlation_id)
            
        # Restore old context
        clear_context()
        for key, value in old_context.items():
            set_context(key, value)
