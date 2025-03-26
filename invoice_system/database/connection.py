"""
Database connection module for the invoice system.

This module provides a wrapper around the finance_assistant database
connection to ensure a consistent interface for the invoice system.
"""

import logging
import contextlib
from typing import Optional, Dict, Any, Generator

from finance_assistant.database.connection import DatabaseConnection as BaseConnection
from finance_assistant.database.manager import DatabaseManager

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Database connection manager for the invoice system."""
    
    def __init__(self, db_path=None, dsn_name=None):
        """Initialize the database connection.
        
        Args:
            db_path: Path to database file (optional)
            dsn_name: DSN name for ODBC connection (optional)
        """
        self.db_path = db_path
        self.dsn_name = dsn_name
        
        # Initialize the base connection
        self.base_connection = BaseConnection(db_path, dsn_name)
        self.db_manager = None
        self._connected = False
        
        logger.info("Invoice system database connection initialized")
    
    def initialize_database(self) -> bool:
        """Initialize the database connection and ensure schema.
        
        Returns:
            bool: True if initialization was successful
        """
        try:
            # Connect to the database
            if not self.base_connection.connect():
                logger.error("Failed to connect to database")
                return False
            
            # Initialize database manager
            self.db_manager = DatabaseManager()
            
            # Try to connect to PostgreSQL database
            success, message = self.db_manager.connect_to_database(
                db_name="finance_db",
                host="localhost",
                port=5432,
                user="postgres"
            )
            
            if not success:
                logger.error(f"Failed to connect to PostgreSQL database: {message}")
                return False
            
            # Ensure the private equity schema is set up
            success = self.db_manager.ensure_private_equity_schema()
            if not success:
                logger.warning("Failed to ensure private equity schema")
                # Continue anyway, as basic functionality should still work
            
            self._connected = True
            logger.info("Database initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}", exc_info=True)
            return False
    
    @contextlib.contextmanager
    def session(self) -> Generator[Any, None, None]:
        """Get a database session as a context manager.
        
        Yields:
            Session object
        """
        if not self._connected and not self.initialize_database():
            raise RuntimeError("Database not connected")
        
        try:
            # For now, we'll just yield the connection itself
            # In a real SQLAlchemy setup, this would yield a Session
            yield self.base_connection.connection
        except Exception as e:
            logger.error(f"Error in database session: {str(e)}", exc_info=True)
            raise
    
    def execute_query(self, query: str, params=None) -> Dict[str, Any]:
        """Execute a SQL query.
        
        Args:
            query: SQL query to execute
            params: Query parameters
            
        Returns:
            Dict: Query results
        """
        if not self._connected and not self.initialize_database():
            return {'error': 'Database not connected'}
        
        return self.base_connection.execute_query(query, params)
    
    def is_connected(self) -> bool:
        """Check if connected to database.
        
        Returns:
            bool: True if connected
        """
        return self._connected
    
    def close(self) -> None:
        """Close the database connection."""
        if hasattr(self, 'base_connection') and self.base_connection:
            self.base_connection.close()
        self._connected = False
        logger.info("Database connection closed") 