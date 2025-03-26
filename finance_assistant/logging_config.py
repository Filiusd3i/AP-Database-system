import logging
import os
import sys
import json
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import traceback

# Enhanced ELK Stack integration with better error handling and retry logic
ELK_AVAILABLE = False
try:
    from logstash_async.handler import AsynchronousLogstashHandler
    from logstash_async.formatter import LogstashFormatter
    from logstash_async.constants import constants
    # Set more resilient async logstash defaults
    constants.SOCKET_TIMEOUT = 5.0  # Shorter socket timeout
    constants.QUEUE_CHECK_INTERVAL = 2.0  # More frequent queue checks
    constants.QUEUED_EVENTS_FLUSH_INTERVAL = 0.5  # Quicker flushing
    constants.QUEUED_EVENTS_FLUSH_COUNT = 100  # Flush after fewer events
    
    # Also try to import elasticsearch client for direct integration
    try:
        from elasticsearch import Elasticsearch
        ELASTICSEARCH_AVAILABLE = True
    except ImportError:
        ELASTICSEARCH_AVAILABLE = False
    
    ELK_AVAILABLE = True
except ImportError as e:
    # More detailed error reporting
    print(f"ELK Stack integration unavailable: {str(e)}")
    ELASTICSEARCH_AVAILABLE = False

# Import custom logging utilities, with fallback for circular imports
try:
    from finance_assistant.logging_utils import StructuredLogger, JSONFormatter, configure_enhanced_logging
    # Register our custom logger class if available
    logging.setLoggerClass(StructuredLogger)
except ImportError as e:
    # Detailed error and fallback to standard Logger
    print(f"Enhanced logging unavailable, using standard logging: {str(e)}")
    
    # Define minimal implementations to prevent errors if the real ones aren't available
    class JSONFormatter(logging.Formatter):
        def format(self, record):
            log_data = {
                'timestamp': self.formatTime(record),
                'level': record.levelname,
                'logger': record.name,
                'message': record.getMessage()
            }
            return json.dumps(log_data)
    
    def configure_enhanced_logging(logger, include_json=True):
        console = logging.StreamHandler()
        console.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(console)
        return logger

def get_environment_config():
    """Get environment-specific logging configuration"""
    # Get environment (default to development if not specified)
    env = os.environ.get('ENVIRONMENT', 'development')
    
    # Default configuration
    config = {
        'environment': env,
        'log_level': logging.INFO,
        'elk_enabled': True,
        'file_logging_enabled': True,
        'console_logging_enabled': True,
        'json_logging_enabled': True,
        'logstash_host': os.environ.get('LOGSTASH_HOST', 'localhost'),
        'logstash_port': int(os.environ.get('LOGSTASH_PORT', 5959)),
        'elasticsearch_host': os.environ.get('ELASTICSEARCH_HOST', 'http://localhost:9200'),
        'log_dir': os.environ.get('LOG_DIR', 'logs'),
        'app_name': os.environ.get('APP_NAME', 'finance_assistant'),
        'ssl_enabled': env in ('production', 'staging'),
        'log_retention_days': int(os.environ.get('LOG_RETENTION_DAYS', 90)),
        'max_log_size_mb': int(os.environ.get('MAX_LOG_SIZE_MB', 10))
    }
    
    # Set environment-specific configurations
    if env == 'production':
        config['log_level'] = logging.WARNING
        # In production, ensure we have all logs, even if some handlers fail
        config['fail_silently'] = True
    elif env == 'staging':
        config['log_level'] = logging.INFO
        config['fail_silently'] = True
    else:  # development
        config['log_level'] = logging.DEBUG
        config['fail_silently'] = False
    
    return config

def safe_add_handler(logger, handler, formatter=None, config=None):
    """Safely add a handler to the logger, with error handling"""
    config = config or get_environment_config()
    try:
        if formatter:
            handler.setFormatter(formatter)
        logger.addHandler(handler)
        return True
    except Exception as e:
        error_msg = f"Failed to add handler {handler.__class__.__name__}: {str(e)}"
        if not config['fail_silently']:
            print(error_msg)
            traceback.print_exc()
        
        # Try to log if we have at least one working handler
        if logger.handlers:
            logger.warning(error_msg)
        return False

def configure_logging(app_name=None, structured=True):
    """Configure logging to send logs to ELK Stack and console/file with enhanced reliability
    
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
    
    # Clear any existing handlers (important when reloading config)
    if logger.handlers:
        logger.handlers.clear()
    
    # Ensure the log directory exists
    log_dir = config['log_dir']
    os.makedirs(log_dir, exist_ok=True)
    
    # Apply enhanced structured logging capabilities if available
    if structured:
        try:
            # Add structured logging capabilities
            configure_enhanced_logging(logger, include_json=config['json_logging_enabled'])
        except Exception as e:
            print(f"Failed to configure enhanced logging: {str(e)}")
            # Fall back to basic configuration
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)
    
    # Set up basic handlers that should always work
    if config['console_logging_enabled']:
        # Always add a console handler for immediate feedback
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        safe_add_handler(logger, console_handler, console_formatter, config)
    
    if config['file_logging_enabled']:
        # Configure daily rotating file handler for standard logs
        standard_file = os.path.join(log_dir, f"{app_name}.log")
        daily_handler = TimedRotatingFileHandler(
            standard_file,
            when='midnight',
            interval=1,
            backupCount=config['log_retention_days']
        )
        standard_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        safe_add_handler(logger, daily_handler, standard_formatter, config)
        
        # Add a size-based rotating handler as backup
        size_handler = RotatingFileHandler(
            os.path.join(log_dir, f"{app_name}_rotating.log"),
            maxBytes=config['max_log_size_mb'] * 1024 * 1024,
            backupCount=5
        )
        safe_add_handler(logger, size_handler, standard_formatter, config)
        
        # Configure JSON file logging
        if config['json_logging_enabled']:
            json_file = os.path.join(log_dir, f"{app_name}_structured.jsonl")
            json_handler = RotatingFileHandler(
                json_file,
                maxBytes=config['max_log_size_mb'] * 1024 * 1024,
                backupCount=5
            )
            try:
                json_formatter = JSONFormatter()
                safe_add_handler(logger, json_handler, json_formatter, config)
            except Exception:
                # Fall back to standard formatter if JSON formatter isn't available
                safe_add_handler(logger, json_handler, standard_formatter, config)
    
    # Configure ELK Stack integration if enabled and available
    if config['elk_enabled'] and ELK_AVAILABLE:
        try:
            # Configure logstash handler with enhanced error handling and retry logic
            logstash_handler = AsynchronousLogstashHandler(
                host=config['logstash_host'],
                port=config['logstash_port'],
                ssl_enable=config['ssl_enabled'],
                database_path=os.path.join(log_dir, 'logstash_buffer.db'),
                transport='logstash_async.transport.TcpTransport',
                event_ttl=86400  # Keep events for 24 hours for retry
            )
            
            # Create a custom formatter with rich metadata
            logstash_formatter = LogstashFormatter(
                message_type='python-logstash',
                extra_prefix='fields',
                extra={
                    'application': app_name,
                    'environment': config['environment'],
                    'hostname': os.environ.get('HOSTNAME', ''),
                    'version': os.environ.get('APP_VERSION', ''),
                    'system': sys.platform
                }
            )
            safe_add_handler(logger, logstash_handler, logstash_formatter, config)
            
            # Log successful Logstash configuration
            logger.info("Connected to Logstash", extra={
                'logstash_host': config['logstash_host'],
                'logstash_port': config['logstash_port'],
                'event_type': 'logstash_connected'
            })
            
            # Configure direct Elasticsearch integration if available (redundant path)
            if ELASTICSEARCH_AVAILABLE:
                try:
                    from elasticsearch_handler import ElasticsearchHandler
                    es_handler = ElasticsearchHandler(
                        hosts=[config['elasticsearch_host']],
                        index_name=f"{app_name.lower()}-logs",
                        auth_type="api_key" if config['ssl_enabled'] else None,
                        api_key=os.environ.get('ELASTICSEARCH_API_KEY', None) if config['ssl_enabled'] else None,
                        es_additional_fields={
                            'application': app_name,
                            'environment': config['environment']
                        }
                    )
                    safe_add_handler(logger, es_handler, None, config)
                    logger.info("Connected directly to Elasticsearch", extra={
                        'es_host': config['elasticsearch_host'],
                        'event_type': 'elasticsearch_connected'
                    })
                except Exception as es_error:
                    logger.warning(f"Could not connect directly to Elasticsearch: {str(es_error)}")
                    
        except Exception as e:
            error_msg = f"Failed to connect to Logstash at {config['logstash_host']}:{config['logstash_port']}: {str(e)}"
            print(error_msg)  # Print to ensure it's seen during startup
            logger.warning(error_msg)
    
    elif config['elk_enabled'] and not ELK_AVAILABLE:
        # Warn about missing ELK Stack integration with installation instructions
        msg = ("ELK Stack integration disabled - required packages not installed. "
              "Install with: pip install python-logstash-async elasticsearch elasticsearch-handler")
        print(msg)  # Print to ensure it's seen during startup
        if logger.handlers:  # Only try to log if we have handlers
            logger.warning(msg)
    
    # Double-check that we have at least one handler
    if not logger.handlers:
        # Last resort - add a basic console handler if everything else failed
        fallback_handler = logging.StreamHandler()
        fallback_formatter = logging.Formatter('%(asctime)s - FALLBACK - %(levelname)s - %(message)s')
        fallback_handler.setFormatter(fallback_formatter)
        logger.addHandler(fallback_handler)
        logger.warning("Using fallback logging configuration as all other handlers failed")
    
    # Log startup information
    logger.info(f"Logging initialized for {app_name} in {config['environment']} environment", extra={
        'environment': config['environment'],
        'python_version': sys.version,
        'app_name': app_name,
        'log_level': logging.getLevelName(config['log_level']),
        'handlers': [h.__class__.__name__ for h in logger.handlers],
        'event_type': 'logging_initialized'
    })
    
    return logger

# Define a global function to get a preconfigured logger easily
def get_logger(name=None):
    """Get a logger configured according to the application standards"""
    config = get_environment_config()
    app_name = config['app_name']
    name = name or app_name
    
    # If this is the root app logger, configure it fully
    if name == app_name:
        return configure_logging(app_name)
    
    # Otherwise, get a child logger which inherits the configuration
    return logging.getLogger(name)
