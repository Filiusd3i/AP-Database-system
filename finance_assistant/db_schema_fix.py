#!/usr/bin/env python3
"""
Database Schema Fix

A script to fix database schema issues, including data type conversions.
"""

import logging
import argparse
import os
import sys
from dotenv import load_dotenv

# Add parent directory to Python path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from finance_assistant.database.manager import DatabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("schema_fix.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def connect_database():
    """Connect to the database using environment variables
    
    Returns:
        tuple: (database_manager, success)
    """
    # Load environment variables
    load_dotenv()
    
    # Get database parameters from environment variables
    host = os.getenv("DB_HOST", "localhost")
    port_str = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "")
    username = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "")
    
    if not db_name:
        logger.error("No database name specified in environment variables")
        return None, False
    
    try:
        port = int(port_str)
        
        # Create database manager
        db_manager = DatabaseManager()
        
        # Connect to database
        success, message = db_manager.connect_to_database(db_name, host, port, username, password)
        
        if success:
            logger.info(f"Connected to database: {db_name}")
            return db_manager, True
        else:
            logger.error(f"Failed to connect to database: {message}")
            return None, False
            
    except ValueError:
        logger.error(f"Invalid port number: {port_str}")
        return None, False
    except Exception as e:
        logger.error(f"Error connecting to database: {str(e)}")
        return None, False

def fix_due_date_type(db_manager):
    """Fix the data type of the due_date column in the invoices table
    
    Args:
        db_manager: The database manager instance
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info("Fixing due_date column data type")
        
        # Check if the invoices table exists
        tables_result = db_manager.execute_query(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        )
        
        tables = [row[0] for row in tables_result['rows']]
        if 'invoices' not in tables:
            logger.error("Invoices table does not exist")
            return False
        
        # Check the current data type of the due_date column
        columns_result = db_manager.execute_query(
            "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'invoices'"
        )
        
        due_date_type = None
        for row in columns_result['rows']:
            if row[0] == 'due_date':
                due_date_type = row[1]
                break
        
        if not due_date_type:
            logger.error("due_date column not found in invoices table")
            return False
        
        logger.info(f"Current due_date column type: {due_date_type}")
        
        # Only fix if it's not already a date type
        if due_date_type.lower() == 'date':
            logger.info("due_date column already has correct data type")
            return True
        
        # Clean the data first (remove any invalid values)
        clean_query = """
        UPDATE invoices
        SET due_date = NULL
        WHERE due_date IS NOT NULL AND due_date !~ '^\d{4}-\d{2}-\d{2}$'
        """
        
        clean_result = db_manager.execute_query(clean_query)
        if 'error' in clean_result and clean_result['error']:
            logger.error(f"Error cleaning due_date values: {clean_result['error']}")
            return False
        
        # Alter the column type
        alter_query = """
        ALTER TABLE invoices
        ALTER COLUMN due_date TYPE DATE
        USING due_date::DATE
        """
        
        result = db_manager.execute_query(alter_query)
        
        if 'error' in result and result['error']:
            logger.error(f"Error altering due_date column type: {result['error']}")
            return False
        
        logger.info("Successfully changed due_date column to DATE type")
        return True
        
    except Exception as e:
        logger.error(f"Error fixing due_date type: {str(e)}")
        return False

def fix_invoice_date_type(db_manager):
    """Fix the data type of the invoice_date column in the invoices table
    
    Args:
        db_manager: The database manager instance
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info("Fixing invoice_date column data type")
        
        # Check the current data type of the invoice_date column
        columns_result = db_manager.execute_query(
            "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'invoices'"
        )
        
        invoice_date_type = None
        for row in columns_result['rows']:
            if row[0] == 'invoice_date':
                invoice_date_type = row[1]
                break
        
        if not invoice_date_type:
            logger.error("invoice_date column not found in invoices table")
            return False
        
        logger.info(f"Current invoice_date column type: {invoice_date_type}")
        
        # Only fix if it's not already a date type
        if invoice_date_type.lower() == 'date':
            logger.info("invoice_date column already has correct data type")
            return True
        
        # Clean the data first (remove any invalid values)
        clean_query = """
        UPDATE invoices
        SET invoice_date = NULL
        WHERE invoice_date IS NOT NULL AND invoice_date !~ '^\d{4}-\d{2}-\d{2}$'
        """
        
        clean_result = db_manager.execute_query(clean_query)
        if 'error' in clean_result and clean_result['error']:
            logger.error(f"Error cleaning invoice_date values: {clean_result['error']}")
            return False
        
        # Alter the column type
        alter_query = """
        ALTER TABLE invoices
        ALTER COLUMN invoice_date TYPE DATE
        USING invoice_date::DATE
        """
        
        result = db_manager.execute_query(alter_query)
        
        if 'error' in result and result['error']:
            logger.error(f"Error altering invoice_date column type: {result['error']}")
            return False
        
        logger.info("Successfully changed invoice_date column to DATE type")
        return True
        
    except Exception as e:
        logger.error(f"Error fixing invoice_date type: {str(e)}")
        return False

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Fix database schema issues")
    parser.add_argument("--all", action="store_true", help="Fix all schema issues")
    parser.add_argument("--due-date", action="store_true", help="Fix due_date column type")
    parser.add_argument("--invoice-date", action="store_true", help="Fix invoice_date column type")
    
    args = parser.parse_args()
    
    # Connect to database
    db_manager, success = connect_database()
    if not success:
        logger.error("Failed to connect to database")
        return 1
    
    try:
        if args.all or args.due_date:
            if fix_due_date_type(db_manager):
                logger.info("Successfully fixed due_date column type")
            else:
                logger.error("Failed to fix due_date column type")
        
        if args.all or args.invoice_date:
            if fix_invoice_date_type(db_manager):
                logger.info("Successfully fixed invoice_date column type")
            else:
                logger.error("Failed to fix invoice_date column type")
                
        return 0
        
    except Exception as e:
        logger.error(f"Error fixing schema: {str(e)}")
        return 1
    finally:
        # Close database connection
        if db_manager:
            db_manager.close()

if __name__ == "__main__":
    sys.exit(main()) 