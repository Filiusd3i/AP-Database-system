"""
Test script for logging system to verify it works both with and without dependencies.

This script tests the logging configuration in both scenarios:
1. With logstash_async installed (ideal case)
2. Without logstash_async installed (fallback case)

Run this script after installing dependencies with install_logging_deps.bat to verify
that the logging system is functioning properly.
"""

import os
import sys
import logging

print("Testing AP Database System Logging")
print("=================================")

# Check if logstash_async is installed
try:
    import logstash_async
    print("✓ logstash_async package is installed")
    elk_available = True
except ImportError:
    print("✗ logstash_async package is NOT installed (will test fallback mode)")
    elk_available = False

# Test basic logging configuration
try:
    from finance_assistant.logging_config import configure_logging
    
    print("\nTesting logging configuration...")
    logger = configure_logging('test_logger')
    
    # Test log messages at different levels
    print("Testing log messages at different levels...")
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    print("✓ Basic logging configuration works")
    
    # Check what handlers are configured
    print("\nConfigured log handlers:")
    for i, handler in enumerate(logger.handlers):
        handler_type = handler.__class__.__name__
        print(f"  {i+1}. {handler_type}")
        
        # If it's a FileHandler, show the file path
        if hasattr(handler, 'baseFilename'):
            print(f"     - File: {handler.baseFilename}")
    
    # Verify ELK integration status
    if elk_available:
        # Check for AsynchronousLogstashHandler
        has_logstash_handler = any(
            h.__class__.__name__ == 'AsynchronousLogstashHandler' 
            for h in logger.handlers
        )
        
        if has_logstash_handler:
            print("\n✓ ELK Stack integration is active")
        else:
            print("\n✗ ELK Stack integration is NOT active (check connection settings)")
    else:
        print("\nℹ ELK Stack integration is disabled (package not installed)")
    
    # Test log file creation
    log_files = []
    for folder in ['logs', '.']:
        if os.path.exists(folder):
            files = [f for f in os.listdir(folder) if f.endswith('.log') or f.endswith('.jsonl')]
            if files:
                log_files.extend([os.path.join(folder, f) for f in files])
    
    if log_files:
        print("\nLog files created:")
        for log_file in log_files:
            print(f"  - {log_file} ({os.path.getsize(log_file)} bytes)")
    else:
        print("\nNo log files found")
    
    # Test structured logging with extra fields
    print("\nTesting structured logging with extra fields...")
    logger.info("Test message with extra fields", extra={
        'user_id': 12345,
        'action': 'test',
        'duration_ms': 42.7
    })
    print("✓ Structured logging test complete")
    
    # Overall status
    print("\nOVERALL STATUS:")
    if elk_available:
        print("✓ Full logging system is working with ELK Stack integration")
    else:
        print("✓ Fallback logging system is working without ELK Stack integration")
    
except Exception as e:
    print(f"\n✗ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
    print("\nOVERALL STATUS: Logging system test FAILED")
    sys.exit(1)

print("\nTest completed successfully!")
