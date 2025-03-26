def log_with_error_code(logger, code, message, **kwargs):
    """Log with a standardized error code."""
    logger.error(message, extra={"error_code": code, **kwargs})

# Example
log_with_error_code(logger, "DB_CONN_001", "Database connection failed", 
                   host=db_host, retry_count=retries) 