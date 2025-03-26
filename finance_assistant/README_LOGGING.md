# Enhanced Logging System

This document provides an overview of the enhanced logging system implemented in the Finance Assistant application. 

## Features

- **Structured Logging**: JSON-formatted logs with consistent structure for easier parsing and analysis
- **ELK Stack Integration**: Direct connection to Logstash for centralized log management
- **Performance Tracking**: Tools to measure and log execution time of operations
- **Method Call Tracing**: Decorators to automatically log method entry/exit with parameters
- **Context-Rich Logs**: Extra metadata fields to provide additional context to log entries
- **Graceful Fallbacks**: Continues working even if ELK Stack connection fails
- **Multiple Output Formats**: Console, file, and ELK stack outputs

## Robust Dependency Handling

The logging system is designed to work in two modes:

1. **Full Mode** - With ELK Stack integration (when `python-logstash-async` is installed)
2. **Fallback Mode** - Basic structured logging without ELK Stack (when dependencies are missing)

This ensures the application will always start and function correctly, even if the ELK Stack components are unavailable.

### Installation of ELK Dependencies

To enable full ELK Stack integration:

1. Run the `install_logging_deps.bat` script which will install all required packages into your virtual environment
2. Verify the installation using the `test_logging.py` script

```batch
# Install dependencies
.\install_logging_deps.bat

# Test that everything is working
python test_logging.py
```

## Components

### 1. `logging_config.py`

The main configuration module that sets up the logging system:

- Configures loggers with appropriate handlers based on environment
- Connects to Logstash (ELK Stack) in production/staging environments
- Falls back to file-based logging in development environments
- Registers custom logger class with enhanced functionality
- Gracefully handles missing dependencies

```python
from finance_assistant.logging_config import configure_logging

# Get a configured logger
logger = configure_logging('my_component')

# Use the logger
logger.info("Operation completed successfully", extra={
    'operation_id': '12345',
    'items_processed': 42
})
```

### 2. `logging_utils.py`

Provides utility classes and functions for enhanced logging:

- **StructuredLogger**: Custom logger class that creates enhanced log records
- **JSONFormatter**: Formats logs as JSON for better parsability
- **log_execution_time**: Context manager to track and log execution time
- **log_method_calls**: Decorator to automatically log method entry/exit with parameters
- **configure_enhanced_logging**: Set up a logger with structured logging capabilities

```python
from finance_assistant.logging_utils import log_execution_time

# Log execution time of a block of code
with log_execution_time(logger, "Database query", extra={'query_id': '12345'}):
    results = db.execute_query("SELECT * FROM users")

# The execution time will be automatically logged when the block exits
```

```python
from finance_assistant.logging_utils import log_method_calls

class UserService:
    @log_method_calls(logger)
    def get_user(self, user_id):
        # Method implementation
        return user
        
# When get_user is called, the method entry and exit will be automatically logged
# with parameter values and execution time
```

### 3. `logging_example.py`

A demonstration module showing how to use the logging system effectively:

- Examples of structured logging
- Performance tracking
- Method call tracing
- Error handling
- Run this file to see the logging in action: `python -m finance_assistant.logging_example`

## Best Practices

1. **Use Structured Logging**: Always use the `extra` parameter to add context to your logs:

```python
# Good
logger.info("User authenticated", extra={
    'user_id': user.id,
    'event_type': 'authentication'
})

# Avoid
logger.info(f"User {user.id} authenticated")
```

2. **Log at Appropriate Levels**:
   - `DEBUG`: Detailed information for debugging
   - `INFO`: Confirmation that things are working as expected
   - `WARNING`: Indication that something unexpected happened
   - `ERROR`: Due to a more serious problem, the software couldn't perform some function
   - `CRITICAL`: A serious error indicating that the program itself may be unable to continue running

3. **Include Event Type**: Use the `event_type` field to categorize logs:

```python
logger.info("Database migration complete", extra={
    'event_type': 'database_migration',
    'tables_migrated': 15
})
```

4. **Log Start and End of Operations**: Especially for long-running operations:

```python
logger.info("Starting data import", extra={'event_type': 'import_start'})
# ... import process ...
logger.info("Data import complete", extra={'event_type': 'import_end'})
```

5. **Track Performance**: Use the `log_execution_time` context manager for critical operations:

```python
with log_execution_time(logger, "Invoice generation"):
    # Generate invoice
```

## Monitoring and Analysis

The structured logs produced by this system can be analyzed using:

1. **Kibana Dashboard**: If connected to ELK Stack
2. **Log Analysis Tools**: The JSON format makes parsing and analysis easier
3. **Local Log Files**: Check `logs/application.log` and `logs/app_structured.jsonl`

## Configuration

The logging system can be configured using environment variables:

- `ENVIRONMENT`: Set to 'development', 'staging', or 'production'
- `LOGSTASH_HOST`: Hostname or IP of the Logstash server
- `LOGSTASH_PORT`: Port number for Logstash connection

For local development, the system will fall back to file-based logging if Logstash connection fails.

## Troubleshooting

### Missing Dependencies

If you see a warning about missing `logstash_async` package:

```
ELK Stack integration disabled - logstash_async package not installed. Install with: pip install python-logstash-async
```

Run the `install_logging_deps.bat` script to install the missing package.

### Connection Issues

If you see logs about failing to connect to Logstash:

```
Failed to connect to Logstash: Connection refused
```

This is normal in development environments without an ELK Stack. The system will automatically fall back to file-based logging.

### Testing the Logging System

Run the included test script to verify that logging is working correctly:

```bash
python test_logging.py
```

This will test both the basic logging functionality and, if installed, the ELK Stack integration.
