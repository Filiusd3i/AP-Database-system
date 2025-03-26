import logging
import json
import os
import sys
import time
import uuid
import socket
import inspect
import traceback
import threading
import platform
import hashlib
import copy
import re
from datetime import datetime
from functools import wraps
from contextlib import contextmanager
from logging.handlers import RotatingFileHandler
import queue
import concurrent.futures

# Ensure logs directory exists
logs_dir = os.path.join(os.getcwd(), 'logs')
try:
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
        print(f"Created logs directory at {logs_dir}")
except Exception as e:
    print(f"Warning: Could not create logs directory: {str(e)}")

# Try to import optional packages
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    from opentelemetry import trace
    from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False

# List of sensitive fields to sanitize in logs
DEFAULT_SENSITIVE_FIELDS = [
    'password', 'passwd', 'secret', 'token', 'api_key', 'apikey', 'auth',
    'credential', 'ssn', 'credit_card', 'creditcard', 'cvv', 'social_security',
    'private_key', 'authorization'
]

class LogBuffer:
    """Thread-safe buffer for batching logs before sending"""
    def __init__(self, max_size=100, flush_interval=5.0):
        self.buffer = queue.Queue()
        self.max_size = max_size
        self.flush_interval = flush_interval
        self.last_flush = time.time()
        self._lock = threading.Lock()
        self._flush_callbacks = []
        
    def add(self, log_record):
        """Add a log record to the buffer"""
        self.buffer.put(log_record)
        
        # Auto-flush if buffer is full or interval passed
        if self.buffer.qsize() >= self.max_size or (time.time() - self.last_flush) > self.flush_interval:
            self.flush()
    
    def register_flush_callback(self, callback):
        """Register a callback to be called when flushing logs"""
        self._flush_callbacks.append(callback)
    
    def flush(self):
        """Flush all buffered logs to registered callbacks"""
        with self._lock:
            if self.buffer.empty():
                return
                
            # Collect all records in buffer
            records = []
            while not self.buffer.empty():
                try:
                    records.append(self.buffer.get_nowait())
                except queue.Empty:
                    break
            
            # Process all records through callbacks
            for callback in self._flush_callbacks:
                try:
                    callback(records)
                except Exception as e:
                    sys.stderr.write(f"Error in log flush callback: {str(e)}\n")
            
            self.last_flush = time.time()

class StateCapture:
    """Utilities for capturing program state"""
    
    @staticmethod
    def capture_locals(frame_depth=1, max_var_size=10000):
        """Capture local variables from the caller's frame"""
        frame = inspect.currentframe()
        try:
            # Navigate up to caller's frame
            for _ in range(frame_depth):
                if frame.f_back is not None:
                    frame = frame.f_back
            
            # Get all local variables
            locals_dict = {}
            for key, value in frame.f_locals.items():
                # Skip private variables and functions
                if key.startswith('__') or callable(value):
                    continue
                
                try:
                    # Try to serialize the value to ensure it's loggable
                    # Truncate large variables to prevent excessive logging
                    str_repr = str(value)
                    if len(str_repr) > max_var_size:
                        str_repr = str_repr[:max_var_size] + "... [truncated]"
                    
                    locals_dict[key] = str_repr
                except:
                    locals_dict[key] = f"<Unable to serialize: {type(value).__name__}>"
            
            return locals_dict
            
        finally:
            del frame  # Prevent reference cycles
    
    @staticmethod
    def capture_stack(skip_frames=1, limit=None):
        """Capture the current stack trace"""
        stack_frames = []
        try:
            stack = inspect.stack()[skip_frames:limit] if limit else inspect.stack()[skip_frames:]
            
            for frame_info in stack:
                frame_data = {
                    'filename': frame_info.filename,
                    'line': frame_info.lineno,
                    'function': frame_info.function,
                    'code_context': frame_info.code_context[0].strip() if frame_info.code_context else None
                }
                stack_frames.append(frame_data)
                
        except Exception as e:
            stack_frames.append({'error': f"Failed to capture stack: {str(e)}"})
            
        return stack_frames
    
    @staticmethod
    def capture_system_info():
        """Capture system and process info"""
        try:
            system_info = {
                'hostname': socket.gethostname(),
                'platform': platform.platform(),
                'python_version': platform.python_version(),
                'cpu_count': os.cpu_count(),
                'process': {
                    'pid': os.getpid(),
                }
            }
            
            if PSUTIL_AVAILABLE:
                try:
                    process = psutil.Process()
                    system_info['process'].update({
                        'memory_percent': process.memory_percent(),
                        'cpu_percent': process.cpu_percent(interval=0.1),
                        'threads': len(process.threads()),
                        'open_files': len(process.open_files())
                    })
                except Exception as e:
                    system_info['process']['error'] = f"Failed to collect psutil metrics: {str(e)}"
            else:
                # psutil not available, add basic information
                system_info['process']['psutil_available'] = False
                
            return system_info
        except Exception as e:
            return {'error': f"Failed to capture system info: {str(e)}"}

class ErrorFingerprinter:
    """Generate consistent fingerprints for similar errors for grouping"""
    
    @staticmethod
    def fingerprint(exception, context=None):
        """Generate a fingerprint for an exception"""
        if not exception:
            return None
            
        # Get exception details
        exc_type = type(exception).__name__
        exc_msg = str(exception)
        
        # Normalize the message (remove variable parts)
        normalized_msg = ErrorFingerprinter._normalize_message(exc_msg)
        
        # Get stack elements (focusing on application code, not library code)
        stack_elements = []
        tb = traceback.extract_tb(sys.exc_info()[2])
        for frame in tb:
            # Skip library code
            if any(lib in frame.filename for lib in ['site-packages', 'dist-packages', '/lib/']):
                continue
                
            # Add frame info
            stack_elements.append(f"{os.path.basename(frame.filename)}:{frame.name}:{frame.lineno}")
        
        # Create fingerprint data
        fingerprint_data = {
            'exception_type': exc_type,
            'normalized_message': normalized_msg,
            'stack_signature': ':'.join(stack_elements[-3:]) if stack_elements else ''
        }
        
        # Add context categorization if available
        if context and isinstance(context, dict):
            if 'action' in context:
                fingerprint_data['action'] = context['action']
            if 'component' in context:
                fingerprint_data['component'] = context['component']
        
        # Create hash of the fingerprint
        fingerprint_str = json.dumps(fingerprint_data, sort_keys=True)
        return hashlib.md5(fingerprint_str.encode()).hexdigest()
    
    @staticmethod
    def _normalize_message(message):
        """Normalize error messages by removing variable parts"""
        # Replace IDs, timestamps, memory addresses
        normalized = re.sub(r'\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b', '<uuid>', message)
        normalized = re.sub(r'\b\d{4}-\d{2}-\d{2}\b', '<date>', normalized)
        normalized = re.sub(r'\b\d{2}:\d{2}:\d{2}\b', '<time>', normalized)
        normalized = re.sub(r'0x[0-9a-f]+', '<memory-addr>', normalized)
        normalized = re.sub(r'\b\d+\b', '<num>', normalized)
        
        return normalized

class CorrelationIdManager:
    """Manages correlation IDs across the application"""
    _local = threading.local()
    
    @classmethod
    def get_correlation_id(cls):
        """Get the current correlation ID or create a new one"""
        if not hasattr(cls._local, 'correlation_id'):
            cls._local.correlation_id = str(uuid.uuid4())
        return cls._local.correlation_id
    
    @classmethod
    def set_correlation_id(cls, correlation_id):
        """Set a specific correlation ID for the current context"""
        cls._local.correlation_id = correlation_id
        return correlation_id
    
    @classmethod
    def clear_correlation_id(cls):
        """Clear the correlation ID from the current thread"""
        if hasattr(cls._local, 'correlation_id'):
            del cls._local.correlation_id

class EnhancedLogRecord(logging.LogRecord):
    """Extended LogRecord with additional context"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add correlation ID
        self.correlation_id = CorrelationIdManager.get_correlation_id()
        
        # Add timestamp with high precision
        self.timestamp = datetime.utcnow().isoformat() + 'Z'
        
        # Add process and thread information
        self.process_name = threading.current_thread().name
        
        # Add caller information beyond what LogRecord provides
        current_frame = inspect.currentframe()
        try:
            # Navigate up the call stack to find the real caller (beyond logging framework)
            frame = current_frame
            frames_up = 0
            while frame and (frames_up < 10):  # Limit to prevent infinite loops
                if frame.f_code.co_filename == __file__:
                    # Skip frames from this logging module
                    frame = frame.f_back
                    frames_up += 1
                    continue
                
                if frame.f_code.co_name in ('debug', 'info', 'warning', 'error', 'critical', 'exception'):
                    # Skip the logging call itself
                    frame = frame.f_back
                    frames_up += 1
                    continue
                
                # Found the real caller
                self.real_module = frame.f_globals.get('__name__', 'unknown')
                self.real_function = frame.f_code.co_name
                self.real_line = frame.f_lineno
                self.real_filename = os.path.basename(frame.f_code.co_filename)
                break
                
            else:
                # If we didn't find a suitable frame
                self.real_module = 'unknown'
                self.real_function = 'unknown'
                self.real_line = 0
                self.real_filename = 'unknown'
                
        finally:
            del current_frame  # Prevent reference cycles
            del frame

        # Link with OpenTelemetry if available
        if OPENTELEMETRY_AVAILABLE:
            try:
                current_span = trace.get_current_span()
                span_context = current_span.get_span_context()
                if span_context and span_context.is_valid:
                    self.trace_id = format(span_context.trace_id, '032x')
                    self.span_id = format(span_context.span_id, '016x')
                    self.trace_flags = span_context.trace_flags
            except Exception:
                pass  # Ignore errors in OpenTelemetry integration

class AdaptiveLogger(logging.Logger):
    """Logger that can automatically adjust its verbosity based on error rates"""
    
    def __init__(self, name, level=logging.NOTSET):
        super().__init__(name, level)
        self._context = {}
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self._buffer = LogBuffer()
        self.error_count = 0
        self.normal_level = level
        self.escalation_threshold = 5  # Number of errors before increasing verbosity
        self.escalation_duration = 300  # Seconds to keep elevated verbosity
        self.last_escalation = 0
        
        # Register default flush handler
        self._buffer.register_flush_callback(self._process_buffered_logs)
        
        # Start background thread for periodic flushing
        self._start_background_flush()
    
    def _start_background_flush(self):
        """Start background thread to periodically flush logs"""
        def flush_periodically():
            while True:
                time.sleep(self._buffer.flush_interval)
                self._buffer.flush()
        
        thread = threading.Thread(target=flush_periodically, daemon=True)
        thread.start()
    
    def _process_buffered_logs(self, records):
        """Process buffered log records through normal logging channels"""
        for record in records:
            super().handle(record)
    
    def makeRecord(self, name, level, fn, lno, msg, args, exc_info, func=None, extra=None, sinfo=None):
        """Create an enhanced log record with additional context"""
        if extra is None:
            extra = {}
            
        # Merge thread-local context
        context_extra = {**self._context, **extra}
        
        # Create a record using the enhanced class
        record = EnhancedLogRecord(
            name, level, fn, lno, msg, args, exc_info, func, sinfo
        )
        
        # Add all extra attributes
        for key, value in context_extra.items():
            setattr(record, key, value)
        
        return record
    
    def bind(self, **kwargs):
        """Create a new logger with additional context data"""
        logger = self.manager.getLogger(self.name)
        logger._context = {**self._context, **kwargs}
        return logger
    
    def with_correlation_id(self, correlation_id=None):
        """Create a logger with a specific correlation ID"""
        if correlation_id is None:
            correlation_id = str(uuid.uuid4())
            
        CorrelationIdManager.set_correlation_id(correlation_id)
        return self.bind(correlation_id=correlation_id)
    
    def debug_with_context(self, msg, *args, **kwargs):
        """Log a DEBUG message with additional context capture"""
        if not self.isEnabledFor(logging.DEBUG):
            return
            
        # Capture additional context
        extra = kwargs.get('extra', {})
        extra['locals'] = StateCapture.capture_locals(frame_depth=2)
        extra['stack'] = StateCapture.capture_stack(skip_frames=2, limit=10)
        kwargs['extra'] = extra
        
        self.debug(msg, *args, **kwargs)
    
    def exception_with_context(self, msg, *args, **kwargs):
        """Log an exception with enhanced context information"""
        if not self.isEnabledFor(logging.ERROR):
            return
            
        # Capture additional context
        extra = kwargs.get('extra', {})
        extra['locals'] = StateCapture.capture_locals(frame_depth=2)
        extra['stack'] = StateCapture.capture_stack(skip_frames=2)
        extra['system_info'] = StateCapture.capture_system_info()
        
        # Generate error fingerprint for grouping similar errors
        try:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            if exc_type and exc_value:
                # Use the more sophisticated error fingerprinting
                fingerprint = ErrorFingerprinter.fingerprint(exc_value, extra)
                extra['error_fingerprint'] = fingerprint
        except:
            pass
            
        kwargs['extra'] = extra
        kwargs['exc_info'] = True
        
        self.error(msg, *args, **kwargs)
    
    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False, **kwargs):
        """Override to buffer logs and handle additional processing"""
        if not self.isEnabledFor(level):
            return
            
        # Merge context with any extra data provided
        if extra is None:
            extra = {}
        
        # Add our context to the extra data
        context_extra = {**self._context, **extra}
        
        # If correlation_id not in context, generate one
        if "correlation_id" not in context_extra:
            context_extra["correlation_id"] = CorrelationIdManager.get_correlation_id()
        
        # Sanitize sensitive data
        sanitized_extra = sanitize_sensitive_data(context_extra)
        
        # Create the log record
        record = self.makeRecord(
            self.name, level, kwargs.get('filename', ''), 
            kwargs.get('lineno', 0), msg, args, exc_info,
            kwargs.get('func', None), sanitized_extra, None
        )
        
        # Add to buffer instead of direct handling
        self._buffer.add(record)
        
        # Track errors for adaptive logging
        if level >= logging.ERROR:
            self.error_count += 1
            
            # Check if we should escalate logging level
            if self.error_count >= self.escalation_threshold:
                now = time.time()
                if now - self.last_escalation > self.escalation_duration:
                    self._escalate_logging()
                    self.last_escalation = now
                    self.error_count = 0
    
    def _escalate_logging(self):
        """Temporarily increase logging verbosity"""
        # Store original level
        self.normal_level = self.level
        
        # Increase verbosity (e.g., from INFO to DEBUG)
        if self.level > logging.DEBUG:
            self.setLevel(self.level - 10)  # Increase one level
            self.info(f"Logging level temporarily increased to {logging.getLevelName(self.level)} due to error frequency")
            
        # Schedule return to normal level
        def restore_level():
            time.sleep(self.escalation_duration)
            self._restore_logging()
            
        threading.Thread(target=restore_level, daemon=True).start()
        
    def _restore_logging(self):
        """Restore normal logging level"""
        prev_level = self.level
        self.setLevel(self.normal_level)
        self.info(f"Logging level restored from {logging.getLevelName(prev_level)} to {logging.getLevelName(self.level)}")

class LogAnalyzer:
    """Hook into log stream for real-time analysis"""
    
    def __init__(self):
        self.patterns = []
        self.alerts = []
        self.mutex = threading.Lock()
        
    def register_pattern(self, pattern, level=logging.WARNING, callback=None):
        """Register a pattern to watch for in logs"""
        with self.mutex:
            self.patterns.append({
                'pattern': pattern,
                'level': level,
                'callback': callback,
                'hits': 0,
                'first_seen': None,
                'last_seen': None
            })
            
    def process_log(self, log_entry):
        """Process a log entry against registered patterns"""
        if not isinstance(log_entry, dict):
            return
            
        message = log_entry.get('message', '')
        level = log_entry.get('level', '')
        now = datetime.utcnow()
        
        with self.mutex:
            for pattern in self.patterns:
                if re.search(pattern['pattern'], message):
                    pattern['hits'] += 1
                    pattern['last_seen'] = now
                    
                    if pattern['first_seen'] is None:
                        pattern['first_seen'] = now
                    
                    # Add to alerts if needed
                    if level and logging.getLevelName(level) >= pattern['level']:
                        self.alerts.append({
                            'timestamp': now.isoformat(),
                            'pattern': pattern['pattern'],
                            'message': message,
                            'level': level,
                            'hits': pattern['hits']
                        })
                    
                    # Call callback if registered
                    if pattern['callback']:
                        try:
                            pattern['callback'](log_entry, pattern['hits'])
                        except Exception as e:
                            print(f"Error in log analysis callback: {e}")
                            
    def get_alerts(self, max_alerts=100):
        """Get recent alerts"""
        with self.mutex:
            return sorted(self.alerts[-max_alerts:], key=lambda x: x['timestamp'], reverse=True)
            
    def get_pattern_stats(self):
        """Get statistics about registered patterns"""
        with self.mutex:
            return [
                {
                    'pattern': p['pattern'],
                    'hits': p['hits'],
                    'first_seen': p['first_seen'].isoformat() if p['first_seen'] else None,
                    'last_seen': p['last_seen'].isoformat() if p['last_seen'] else None
                }
                for p in self.patterns
            ]

class EnhancedJsonFormatter(logging.Formatter):
    """Formatter that outputs logs as detailed JSON objects"""
    
    def __init__(self, include_fields=None, exclude_fields=None):
        super().__init__()
        self.include_fields = include_fields or []
        self.exclude_fields = exclude_fields or ['args', 'msg', 'levelno', 'pathname', 'module']
    
    def format(self, record):
        """Format the log record as a JSON object"""
        # Start with all record attributes
        log_object = {}
        
        for key, value in record.__dict__.items():
            # Skip excluded fields
            if key in self.exclude_fields:
                continue
                
            # Skip fields not explicitly included if inclusion list exists
            if self.include_fields and key not in self.include_fields:
                continue
                
            # Skip internal fields
            if key.startswith('_'):
                continue
                
            try:
                # Try to serialize the value
                json.dumps({key: value})
                log_object[key] = value
            except (TypeError, OverflowError):
                # If value is not JSON serializable, convert to string
                log_object[key] = str(value)
        
        # Always include these core fields
        log_object.update({
            'timestamp': getattr(record, 'timestamp', datetime.utcnow().isoformat() + 'Z'),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'correlation_id': getattr(record, 'correlation_id', 'unknown')
        })
        
        # Add distributed tracing info if available
        if hasattr(record, 'trace_id'):
            log_object['trace_id'] = record.trace_id
        if hasattr(record, 'span_id'):
            log_object['span_id'] = record.span_id
        
        # Add exception info if available
        if record.exc_info:
            exception_data = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': ''.join(traceback.format_exception(*record.exc_info))
            }
            log_object['exception'] = exception_data
        
        return json.dumps(log_object)

class LogDestinationHandler:
    """Factory for creating handlers to various log destinations"""
    
    @staticmethod
    def create_console_handler(level=logging.INFO, formatter=None):
        """Create a handler for console output"""
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        if formatter:
            handler.setFormatter(formatter)
        return handler
    
    @staticmethod
    def create_file_handler(filename, level=logging.INFO, formatter=None, 
                           max_bytes=10*1024*1024, backup_count=5):
        """Create a handler for file output with rotation"""
        os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
        handler = RotatingFileHandler(
            filename=filename,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        handler.setLevel(level)
        if formatter:
            handler.setFormatter(formatter)
        return handler
    
    @staticmethod
    def create_socket_handler(host, port, level=logging.INFO, formatter=None):
        """Create a handler for sending logs to a socket"""
        handler = SocketHandler(host, port)
        handler.setLevel(level)
        if formatter:
            handler.setFormatter(formatter)
        return handler

def sanitize_sensitive_data(data, sensitive_fields=None):
    """Mask sensitive data in logs (PII, credentials, etc.)"""
    if sensitive_fields is None:
        sensitive_fields = DEFAULT_SENSITIVE_FIELDS
    
    # Handle None case
    if data is None:
        return None
        
    # Handle dict case
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            # Check if this key might contain sensitive data
            if any(sensitive in str(key).lower() for sensitive in sensitive_fields):
                result[key] = "********"
            elif isinstance(value, (dict, list)):
                result[key] = sanitize_sensitive_data(value, sensitive_fields)
            else:
                result[key] = value
        return result
    
    # Handle list/tuple case
    elif isinstance(data, (list, tuple)):
        result = []
        for item in data:
            result.append(sanitize_sensitive_data(item, sensitive_fields))
        return type(data)(result)  # Convert back to original type
    
    # Handle string case - check for patterns like credit cards, SSNs
    elif isinstance(data, str):
        # Look for credit card patterns
        if re.search(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', data):
            return re.sub(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', '********', data)
        
        # Look for SSN patterns
        if re.search(r'\b\d{3}[\s-]?\d{2}[\s-]?\d{4}\b', data):
            return re.sub(r'\b\d{3}[\s-]?\d{2}[\s-]?\d{4}\b', '********', data)
            
        return data
    
    # Other types pass through unchanged
    return data

def log_health_metrics(logger, interval=300):
    """Log system health metrics at regular intervals"""
    if not PSUTIL_AVAILABLE:
        logger.warning("Cannot log health metrics: psutil not available")
        return None
    
    def log_metrics():
        while True:
            try:
                # Capture system metrics
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                metrics = {
                    'memory': {
                        'total_gb': round(memory.total / (1024**3), 2),
                        'used_percent': memory.percent,
                        'available_gb': round(memory.available / (1024**3), 2)
                    },
                    'cpu': {
                        'percent': psutil.cpu_percent(interval=1),
                        'cores': psutil.cpu_count(logical=True)
                    },
                    'disk': {
                        'total_gb': round(disk.total / (1024**3), 2),
                        'used_percent': disk.percent,
                        'free_gb': round(disk.free / (1024**3), 2)
                    },
                    'process': {
                        'pid': os.getpid(),
                        'memory_percent': psutil.Process().memory_percent(),
                        'cpu_percent': psutil.Process().cpu_percent(),
                        'threads': len(psutil.Process().threads()),
                        'open_files': len(psutil.Process().open_files())
                    }
                }
                
                # Determine log level based on thresholds
                level = logging.INFO
                if (metrics['memory']['used_percent'] > 85 or 
                    metrics['cpu']['percent'] > 80 or
                    metrics['disk']['used_percent'] > 90):
                    level = logging.WARNING
                    
                logger.log(level, "System health metrics", extra={
                    'event_type': 'health_check',
                    'metrics': metrics
                })
            except Exception as e:
                logger.warning(f"Failed to log health metrics: {str(e)}")
                
            time.sleep(interval)
    
    # Start in background thread
    thread = threading.Thread(target=log_metrics, daemon=True)
    thread.start()
    return thread

def link_to_tracing(logger, span_context=None):
    """Link logger with OpenTelemetry tracing system"""
    if not OPENTELEMETRY_AVAILABLE:
        return logger
        
    if span_context is None:
        current_span = trace.get_current_span()
        span_context = current_span.get_span_context()
            
    if span_context and span_context.is_valid:
        return logger.bind(
            trace_id=format(span_context.trace_id, '032x'),
            span_id=format(span_context.span_id, '016x'),
            trace_flags=span_context.trace_flags
        )
    return logger

def log_database_query(logger, query, params=None, result=None, execution_time=None):
    """Log database query with proper structure and sanitization"""
    # Don't log actual parameter values for security
    if params:
        param_count = len(params) if isinstance(params, (list, tuple)) else 1
        param_placeholder = f"<{param_count} params>"
    else:
        param_placeholder = "None"
        
    # Truncate long queries
    truncated_query = query[:500] + "..." if len(query) > 500 else query
    
    # Get query type
    query_type = "unknown"
    query_start = query.strip().lower().split()[0] if query else ""
    if query_start in ["select", "insert", "update", "delete", "create", "alter", "drop"]:
        query_type = query_start
        
    # Log basic or detailed version based on success/failure
    if result and "error" in result and result["error"]:
        # Log full details for errors
        logger.error(
            f"Database query failed: {result['error']}",
            extra={
                "query_type": query_type,
                "query": truncated_query,
                "params": param_placeholder,
                "error": result["error"],
                "execution_time_ms": execution_time
            }
        )
    else:
        # Log success with fewer details
        row_count = len(result.get("rows", [])) if result and "rows" in result else 0
        logger.debug(
            f"Database query executed ({row_count} rows)",
            extra={
                "query_type": query_type,
                "execution_time_ms": execution_time,
                "row_count": row_count
            }
        )

def configure_ultimate_logging(
    app_name="app",
    component_name=None,
    log_level=None,
    console_output=True,
    file_output=True,
    file_path=None,
    log_server=None,
    include_state_info=True,
    sample_rate=1.0,
    log_dir='logs',
    enable_health_metrics=True,
    health_check_interval=300,
    log_analyzer=None
):
    """
    Configure the ultimate logging system with extensive diagnostics.
    
    Args:
        app_name (str): Name of the application
        component_name (str): Name of the specific component/module
        log_level (str): Level of logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        console_output (bool): Whether to output logs to the console
        file_output (bool): Whether to output logs to a file
        file_path (str): Path to the log file, defaults to app_name.log
        log_server (dict): Configuration for remote log server (host, port)
        include_state_info (bool): Whether to include detailed state information
        sample_rate (float): Percentage of logs to keep (1.0 = all, 0.1 = 10%)
        log_dir (str): Directory to store log files
        enable_health_metrics (bool): Whether to enable periodic health metrics logging
        health_check_interval (int): Interval in seconds between health checks
        log_analyzer (LogAnalyzer): Optional log analyzer instance for real-time analysis
    """
    # Create logs directory if it doesn't exist
    if file_output and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    # Determine log level from environment or parameter
    if log_level is None:
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    numeric_level = getattr(logging, log_level, logging.INFO)
    
    # Set AdaptiveLogger as the default logger class
    logging.setLoggerClass(AdaptiveLogger)
    
    # Full logger name with component if provided
    full_logger_name = f"{app_name}.{component_name}" if component_name else app_name
    
    # Get logger
    logger = logging.getLogger(full_logger_name)
    logger.setLevel(numeric_level)
    
    # Store original properties in case of adaptive logging
    logger.normal_level = numeric_level
    
    # Clear existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create formatter
    formatter = EnhancedJsonFormatter()
    
    # Console handler
    if console_output:
        console_handler = LogDestinationHandler.create_console_handler(
            level=numeric_level,
            formatter=formatter
        )
        logger.addHandler(console_handler)
    
    # File handler
    if file_output:
        if file_path is None:
            logs_dir = os.path.join(os.getcwd(), log_dir)
            os.makedirs(logs_dir, exist_ok=True)
            file_path = os.path.join(logs_dir, f"{app_name}.log")
        
        file_handler = LogDestinationHandler.create_file_handler(
            filename=file_path,
            level=numeric_level,
            formatter=formatter
        )
        logger.addHandler(file_handler)
    
    # Remote log server
    if log_server:
        socket_handler = LogDestinationHandler.create_socket_handler(
            host=log_server.get('host', 'localhost'),
            port=log_server.get('port', 9020),
            level=numeric_level,
            formatter=formatter
        )
        logger.addHandler(socket_handler)
    
    # Register with log analyzer if provided
    if log_analyzer:
        def analyze_log_record(records):
            for record in records:
                # Convert LogRecord to dict for analysis
                log_dict = {
                    'timestamp': getattr(record, 'timestamp', datetime.utcnow().isoformat()),
                    'level': record.levelname,
                    'logger': record.name,
                    'message': record.getMessage(),
                    'module': getattr(record, 'real_module', record.module),
                    'function': getattr(record, 'real_function', record.funcName),
                    'line': getattr(record, 'real_line', record.lineno)
                }
                
                # Add all other attributes
                for key, value in record.__dict__.items():
                    if key not in log_dict and not key.startswith('_'):
                        try:
                            # Ensure it's serializable
                            json.dumps({key: value})
                            log_dict[key] = value
                        except:
                            log_dict[key] = str(value)
                
                log_analyzer.process_log(log_dict)
                
        # Add as a buffer flush callback
        if hasattr(logger, '_buffer'):
            logger._buffer.register_flush_callback(analyze_log_record)
    
    # Create a function to handle uncaught exceptions
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            # Don't log keyboard interrupt
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
            
        logger.critical("Uncaught exception", 
                       exc_info=(exc_type, exc_value, exc_traceback),
                       extra={
                           'event_type': 'uncaught_exception',
                           'system_info': StateCapture.capture_system_info(),
                           'error_fingerprint': ErrorFingerprinter.fingerprint(exc_value)
                       })
    
    # Set up global exception handler
    sys.excepthook = handle_exception
    
    # Start health metrics logging if enabled
    if enable_health_metrics and PSUTIL_AVAILABLE:
        health_thread = log_health_metrics(logger, interval=health_check_interval)
        
    # Log initialization
    logger.info(f"Logging initialized for {full_logger_name}",
               extra={
                   'event_type': 'logging_initialized',
                   'log_level': log_level,
                   'app_name': app_name,
                   'component_name': component_name
               })
    
    return logger

def log_execution_time(logger=None, level=logging.INFO, capture_args=True):
    """
    Decorator to log execution time and details of a function.
    
    Args:
        logger: The logger to use. If None, uses the module logger.
        level: The log level to use.
        capture_args: Whether to capture function arguments.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get the appropriate logger
            log = logger or logging.getLogger(func.__module__)
            
            # Generate a unique ID for this execution
            execution_id = str(uuid.uuid4())
            
            # Prepare context information
            log_context = {
                'execution_id': execution_id,
                'function': func.__name__,
                'module': func.__module__,
                'event_type': 'function_execution'
            }
            
            # Capture arguments if requested
            if capture_args:
                # Safely convert args to string representations
                str_args = []
                for arg in args:
                    try:
                        arg_str = str(arg)
                        # Truncate very long args
                        if len(arg_str) > 1000:
                            arg_str = arg_str[:1000] + "... [truncated]"
                        str_args.append(arg_str)
                    except:
                        str_args.append(f"<unable to serialize: {type(arg).__name__}>")
                
                # Do the same for kwargs
                str_kwargs = {}
                for key, value in kwargs.items():
                    try:
                        value_str = str(value)
                        if len(value_str) > 1000:
                            value_str = value_str[:1000] + "... [truncated]"
                        str_kwargs[key] = value_str
                    except:
                        str_kwargs[key] = f"<unable to serialize: {type(value).__name__}>"
                
                log_context['args'] = str_args
                log_context['kwargs'] = str_kwargs
            
            # Log function entry with enhanced context
            start_time = time.time()
            
            # Create a logger with the execution context
            exec_logger = log.bind(**log_context)
            exec_logger.log(level, f"Executing {func.__name__}")
            
            result = None
            error = None
            
            try:
                # Execute the function
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                error = e
                # Don't log the exception here, it will be logged below
                raise
            finally:
                end_time = time.time()
                execution_time = (end_time - start_time) * 1000  # Convert to ms
                
                # Update context with execution result
                log_context.update({
                    'execution_time_ms': execution_time,
                    'success': error is None
                })
                
                if error:
                    # Log error with full context
                    error_logger = log.bind(**log_context)
                    error_logger.exception_with_context(
                        f"Exception in {func.__name__}: {str(error)}",
                        extra={'event_type': 'function_error'}
                    )
                else:
                    # Log successful completion
                    # Try to safely include result in the log
                    try:
                        result_str = str(result)
                        if len(result_str) > 1000:
                            result_str = result_str[:1000] + "... [truncated]"
                        log_context['result'] = result_str
                    except:
                        log_context['result'] = f"<unable to serialize: {type(result).__name__}>"
                    
                    completion_logger = log.bind(**log_context)
                    completion_logger.log(
                        level, 
                        f"Completed {func.__name__} in {execution_time:.2f}ms"
                    )
        
        return wrapper
    return decorator

@contextmanager
def log_context(logger, **context):
    """
    Context manager to add temporary context to logs.
    
    Args:
        logger: The logger to use
        **context: Context key-value pairs to add to logs
    """
    # Create a new logger with the context
    context_logger = logger.bind(**context)
    
    try:
        yield context_logger
    except Exception as e:
        # Log exception with the context
        context_logger.exception_with_context(
            f"Exception in context: {str(e)}",
            extra={'event_type': 'context_exception'}
        )
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