"""
Example demonstration of the enhanced logging system.

This file shows how to use the various logging features implemented in the system,
including structured logging, performance tracking, and method call tracing.

Execute this file directly to see the logging in action:
```
python -m finance_assistant.logging_example
```
"""

import logging
import time
import random
from finance_assistant.logging_config import configure_logging
from finance_assistant.logging_utils import log_execution_time, log_method_calls

# Configure logging
logger = configure_logging('logging_example', structured=True)

class DatabaseSimulator:
    """Class to simulate database operations with logging."""
    
    def __init__(self):
        self.logger = logging.getLogger('logging_example.database')
        self.logger.info("Database simulator initialized", extra={
            'component': 'database',
            'event_type': 'initialization'
        })
    
    @log_method_calls(logging.getLogger('logging_example.database'))
    def connect(self, host, port=5432, username='admin'):
        """Simulate connecting to a database."""
        # Simulate connection delay
        time.sleep(random.uniform(0.1, 0.3))
        
        self.logger.info(f"Connected to database at {host}:{port}", extra={
            'host': host,
            'port': port,
            'username': username,
            'component': 'database',
            'event_type': 'connection'
        })
        return True
    
    @log_method_calls(logging.getLogger('logging_example.database'))
    def execute_query(self, query, params=None):
        """Simulate executing a database query."""
        # Simulate query execution
        execution_time = random.uniform(0.05, 0.5)
        time.sleep(execution_time)
        
        # Log query details
        self.logger.info(f"Executed query in {execution_time:.2f}s", extra={
            'query': query,
            'params': params,
            'execution_time_ms': execution_time * 1000,
            'component': 'database',
            'event_type': 'query'
        })
        
        # Return simulated results
        row_count = random.randint(0, 100)
        return {'rows': [{'id': i, 'value': f'data_{i}'} for i in range(row_count)], 'count': row_count}
    
    @log_method_calls(logging.getLogger('logging_example.database'))
    def close(self):
        """Simulate closing a database connection."""
        time.sleep(random.uniform(0.05, 0.1))
        self.logger.info("Database connection closed", extra={
            'component': 'database',
            'event_type': 'connection_closed'
        })

class UserService:
    """Service class to demonstrate business logic with logging."""
    
    def __init__(self):
        self.logger = logging.getLogger('logging_example.user_service')
        self.db = DatabaseSimulator()
        self.logger.info("User service initialized", extra={
            'component': 'user_service',
            'event_type': 'initialization'
        })
    
    @log_method_calls(logging.getLogger('logging_example.user_service'))
    def get_user(self, user_id):
        """Get user by ID with execution time logging."""
        try:
            with log_execution_time(self.logger, "get_user operation", extra={'user_id': user_id}):
                # Connect to DB
                self.db.connect('localhost', username='finance_app')
                
                # Execute query
                result = self.db.execute_query("SELECT * FROM users WHERE id = %s", [user_id])
                
                # Simulate processing
                time.sleep(random.uniform(0.1, 0.2))
                
                # Close connection
                self.db.close()
                
                return {'id': user_id, 'username': f'user_{user_id}', 'count': result['count']}
        
        except Exception as e:
            self.logger.error(f"Error getting user {user_id}: {str(e)}", extra={
                'user_id': user_id,
                'error': str(e),
                'component': 'user_service',
                'event_type': 'error'
            })
            raise
    
    @log_method_calls(logging.getLogger('logging_example.user_service'))
    def process_data(self):
        """Process data with occasional errors to demonstrate error logging."""
        try:
            # Occasionally throw an error for demonstration
            if random.random() < 0.3:
                raise ValueError("Simulated random error")
            
            self.logger.info("Data processing completed", extra={
                'items_processed': random.randint(10, 50),
                'component': 'user_service',
                'event_type': 'data_processing'
            })
            return True
        
        except Exception as e:
            self.logger.error(f"Data processing error: {str(e)}", extra={
                'error': str(e),
                'component': 'user_service',
                'event_type': 'error'
            })
            raise

def run_example():
    """Run the example to demonstrate all logging features."""
    logger.info("Starting logging example", extra={'event_type': 'example_start'})
    
    # Create service
    service = UserService()
    
    # Simulate multiple operations
    for i in range(5):
        try:
            # Get user with random ID
            user_id = random.randint(1, 100)
            user = service.get_user(user_id)
            logger.info(f"Retrieved user {user_id}", extra={
                'user': user,
                'event_type': 'user_retrieval'
            })
            
            # Process data (may throw errors randomly)
            try:
                service.process_data()
            except Exception as e:
                logger.warning(f"Caught processing error: {str(e)}")
            
        except Exception as e:
            logger.error(f"Operation failed: {str(e)}")
    
    # Log different levels to demonstrate filtering
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    # Log structured data
    logger.info("Complex data structure", extra={
        'data': {
            'items': [1, 2, 3, 4, 5],
            'metadata': {
                'source': 'example',
                'version': '1.0.0'
            },
            'stats': {
                'min': 1,
                'max': 5,
                'avg': 3.0
            }
        },
        'event_type': 'structured_data'
    })
    
    logger.info("Logging example completed", extra={'event_type': 'example_end'})

if __name__ == "__main__":
    run_example()
