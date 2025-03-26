import logging
import os
import sys
from logging.handlers import RotatingFileHandler

# Try to import ELK Stack components, but don't fail if they're not available
ELK_AVAILABLE = False
try:
    from logstash_async.handler import AsynchronousLogstashHandler
    from logstash_async.formatter import LogstashFormatter
    ELK_AVAILABLE = True
except ImportError:
    # If imports fail, we'll use basic logging instead
    pass

# Import custom logging utilities, with fallback for circular imports
try:
    from finance_assistant.logging_utils import StructuredLogger, configure_enhanced_logging
    # Register our custom logger class if available
    logging.setLoggerClass(StructuredLogger)
except ImportError:
    # Fall back to standard Logger if our custom one isn't available
    pass

def configure_logging(app_name='finance_assistant', structured=True):
    """Configure logging to send logs to ELK Stack and console/file based on environment
    
    Args:
        app_name: Name of the application for logging namespace
        structured: Whether to enable structured/JSON logging
        
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(app_name)
    logger.setLevel(logging.INFO)
    
    # Clear any existing handlers (important when reloading config)
    if logger.handlers:
        logger.handlers.clear()
    
    # Get environment (default to development if not specified)
    env = os.environ.get('ENVIRONMENT', 'development')
    
    # Apply enhanced structured logging if requested
    if structured:
        # Add structured logging capabilities
        configure_enhanced_logging(logger, include_json=True)
        
        # Log environment details at startup
        logger.info(f"Starting application in {env} environment", extra={
            'environment': env,
            'python_version': sys.version,
            'app_name': app_name,
            'event_type': 'application_start'
        })
    else:
        # Basic console handler if structured logging not requested
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(console_handler)
    
    # Configure ELK connection based on environment
    if env in ('production', 'staging'):
        # For production/staging, connect to actual ELK instance
        host = os.environ.get('LOGSTASH_HOST', 'logstash.company.com')
        port = int(os.environ.get('LOGSTASH_PORT', 5959))
    else:
        # For development, use local instance or development ELK if available
        host = os.environ.get('LOGSTASH_HOST', 'localhost')
        port = int(os.environ.get('LOGSTASH_PORT', 5959))
    
    # Create logs directory if it doesn't exist (for buffer)
    os.makedirs('logs', exist_ok=True)
    
    # Only attempt ELK configuration if the required packages are available
    if ELK_AVAILABLE:
        try:
            # Configure logstash handler
            logstash_handler = AsynchronousLogstashHandler(
                host=host,
                port=port,
                ssl_enable=env == 'production',  # Enable SSL in production
                database_path='logs/logstash_buffer.db',
                transport='logstash_async.transport.TcpTransport'
            )
            
            # Create a custom formatter
            logstash_formatter = LogstashFormatter(
                message_type='python-logstash',
                extra_prefix='fields',
                extra={
                    'application': app_name,
                    'environment': env
                }
            )
            logstash_handler.setFormatter(logstash_formatter)
            
            # Add the handler to the logger
            logger.addHandler(logstash_handler)
            logger.info("Connected to Logstash", extra={
                'logstash_host': host,
                'logstash_port': port
            })
        except Exception as e:
            # Don't fail if Logstash connection fails - just log it and continue
            logger.warning(f"Failed to connect to Logstash: {str(e)}", extra={
                'error': str(e),
                'logstash_host': host,
                'logstash_port': port
            })
    else:
        # Log a warning if ELK packages aren't available
        logger.warning("ELK Stack integration disabled - logstash_async package not installed. "
                      "Install with: pip install python-logstash-async")
    
    # If in development, also log to a file for easier troubleshooting
    if env == 'development':
        try:
            file_handler = RotatingFileHandler(
                'logs/application.log',
                maxBytes=10*1024*1024,  # 10 MB
                backupCount=5
            )
            file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
            logger.info("Configured file logging", extra={'log_file': 'logs/application.log'})
        except Exception as e:
            logger.warning(f"Could not set up file logging: {str(e)}")
    
    return logger
