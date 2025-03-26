# Enhanced Logging System with ELK Stack Integration

This document provides an overview of the enhanced logging system implemented in the Finance Assistant application.

## Features

- **Robust**: Multiple logging paths, graceful degradation, retry logic
- **Comprehensive**: Structured logs with rich context and metadata
- **Performance-oriented**: Asynchronous logging, batching, low overhead
- **Fully integrated**: Direct integration with ELK Stack for centralized log management
- **Developer-friendly**: Easy to use API with context managers and decorators

## Key Components

1. **Core Logger Configuration**: `finance_assistant/logging_config.py`
   - Sets up logging based on environment
   - Configures multiple handlers for redundancy
   - Dynamically adapts to available dependencies

2. **Logging Utilities**: `finance_assistant/logging_utils.py`
   - Enhanced structured logging
   - Performance tracking tools
   - Context-aware logging
   - Colored console output

3. **Elasticsearch Integration**: `finance_assistant/elasticsearch_handler.py`
   - Direct integration with Elasticsearch
   - Buffering with disk persistence
   - Automatic retry logic
   - Proper index templates for efficient storage

## Robust Dependency Handling

The logging system is designed to work in three modes:

1. **Full ELK Stack Mode** - With both Logstash and direct Elasticsearch integration
2. **Logstash-only Mode** - With Logstash integration but without direct Elasticsearch
3. **Fallback Mode** - Basic structured logging without ELK Stack (when dependencies are missing)

This ensures the application will always start and function correctly, even if the ELK Stack components are unavailable.

### Installation of ELK Dependencies

To enable full ELK Stack integration:

```bash
pip install python-logstash-async elasticsearch elasticsearch-dsl
```

## Using the Logging System

### Basic Logging

```python
# Get a logger for your module
from finance_assistant.logging_config import get_logger
logger = get_logger(__name__)

# Use standard logging methods
logger.debug("Debug message")
logger.info("Information message")
logger.warning("Warning message")
logger.error("Error message", exc_info=True)  # Include exception info
logger.critical("Critical error")

# Add structured context
logger.info("User logged in", extra={
    'user_id': user.id,
    'username': user.username,
    'ip_address': request.remote_addr
})
```

### Advanced Features

#### Performance Tracking

```python
from finance_assistant.logging_utils import log_execution_time

# Track execution time of a code block
with log_execution_time(logger, "Database query"):
    results = db.execute_query("SELECT * FROM users")
```

#### Method Call Tracking

```python
from finance_assistant.logging_utils import log_method_calls

class UserService:
    @log_method_calls(logger, log_args=True, performance_threshold_ms=100)
    def get_user(self, user_id):
        # Method implementation
        return user
```

#### Request Context

```python
from finance_assistant.logging_utils import request_context

# In a web request handler
with request_context(request_id=request.id, user_id=user.id, endpoint=request.path):
    # All logs within this block will include this context
    logger.info("Processing request")
    process_request()
```

#### Audit Logging

```python
# Log security and compliance events
logger.audit("User changed permissions", extra={
    'user_id': admin.id,
    'target_user': user.id,
    'permission': 'admin',
    'action': 'grant'
})
```

#### Metrics

```python
# Log metrics for monitoring dashboards
logger.metric("query_time", 35.2, unit="ms")
logger.metric("active_users", 1250)
```

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

4. **Use Correlation IDs**: For tracking related events:

```python
with request_context(request_id="12345"):
    # All logs within this block will have the same correlation ID
    logger.info("Processing payment")
```

## Configuration

The logging system is configured through environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| ENVIRONMENT | Environment name (development, staging, production) | development |
| LOG_LEVEL | Minimum log level to record | INFO |
| LOG_DIR | Directory for log files | logs |
| LOGSTASH_HOST | Hostname of Logstash server | localhost |
| LOGSTASH_PORT | Port for Logstash server | 5959 |
| ELASTICSEARCH_HOST | URL for Elasticsearch | http://localhost:9200 |
| ELASTICSEARCH_API_KEY | API key for Elasticsearch (if required) | |
| APP_NAME | Application name for namespacing | finance_assistant |
| APP_VERSION | Application version | |
| LOG_RETENTION_DAYS | Days to retain log files | 90 |
| MAX_LOG_SIZE_MB | Maximum size of log files before rotation | 10 |

## ELK Stack Integration Details

### Logstash Configuration

Sample Logstash configuration for receiving logs:

```
input {
  tcp {
    port => 5959
    codec => json
  }
}

filter {
  date {
    match => [ "@timestamp", "ISO8601" ]
  }
}

output {
  elasticsearch {
    hosts => ["http://elasticsearch:9200"]
    index => "logs-%{[app_name]}-%{+YYYY.MM.dd}"
  }
}
```

### Kibana Dashboard

Sample queries for Kibana:

- Error tracking: `level:ERROR OR level:CRITICAL`
- Performance issues: `duration_ms:>100 AND status:success`
- Security events: `log_type:audit`
- User activity: `context.user_id:* AND NOT level:DEBUG`

## Monitoring and Analysis

The structured logs produced by this system can be analyzed using:

1. **Kibana Dashboard**: For visualization and analysis of logs in ELK Stack
2. **Elasticsearch Query Language**: For advanced querying and filtering
3. **Log Analysis Tools**: The JSON format makes parsing and analysis easier
4. **Local Log Files**: Check the log files in the configured log directory

## Troubleshooting

### Log Locations

- Console output
- Standard logs: `logs/{app_name}.log`
- Rotating logs: `logs/{app_name}_rotating.log`
- JSON structured logs: `logs/app_structured.jsonl`
- Buffer files:
  - Logstash buffer: `logs/logstash_buffer.db`
  - Elasticsearch buffer: `logs/elasticsearch_buffer.json`

### Common Issues

- **Missing logs in ELK**: Check connectivity to Logstash and Elasticsearch
- **Log formatting issues**: Ensure serializable data in log records
- **Performance concerns**: Adjust buffer sizes and flush intervals

### Missing Dependencies

If you see a warning about missing ELK Stack packages:

```
ELK Stack integration disabled - required packages not installed. Install with: pip install python-logstash-async elasticsearch elasticsearch-handler
```

Install the required packages as instructed.

### Connection Issues

If you see logs about failing to connect to Logstash or Elasticsearch:

```
Failed to connect to Logstash at localhost:5959: Connection refused
```

This is normal in development environments without an ELK Stack. The system will automatically fall back to file-based logging.
