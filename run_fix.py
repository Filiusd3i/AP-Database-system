#!/usr/bin/env python3
"""
Vendor Column Fix Tool

This script runs a standalone version of the vendor_name column fix functionality.
It handles database connections properly and provides detailed error reporting.
"""

import os
import sys
import logging
from pathlib import Path
import traceback

# Try to load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Look for .env file in current directory and parent directories
    env_path = Path('.') / '.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        print(f"Loaded environment from {env_path.absolute()}")
    else:
        # Try parent directory
        env_path = Path('..') / '.env'
        if env_path.exists():
            load_dotenv(dotenv_path=env_path)
            print(f"Loaded environment from {env_path.absolute()}")
except ImportError:
    print("python-dotenv not installed. Using existing environment variables.")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("vendor_column_fix")

def get_db_connection_params():
    """Get database connection parameters from environment variables"""
    params = {
        'db_name': os.getenv('DB_NAME'),
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', '5432')),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD')
    }
    
    # Check for missing required parameters
    missing = [k for k, v in params.items() if v is None and k in ['db_name', 'user', 'password']]
    if missing:
        logger.error(f"Missing required database parameters: {', '.join(missing)}")
        logger.info("Please set the following environment variables:")
        for param in missing:
            env_var = f"DB_{param.upper()}"
            logger.info(f"  - {env_var}")
        return None
        
    return params

def fix_vendor_column():
    """
    CLI-friendly version of the vendor column fix for PostgreSQL's invoices table.
    Uses logging instead of UI widgets for output.
    """
    logger.info("Starting vendor column fix operation...")
    
    # Get database connection parameters
    db_params = get_db_connection_params()
    if not db_params:
        return False
    
    # Import here to avoid circular imports with log setup
    from finance_assistant.database.manager import DatabaseManager
    
    # Initialize the database connection with explicit parameters
    db_manager = DatabaseManager()
    
    # Try connecting with explicit parameters
    try:
        logger.info(f"Connecting to database {db_params['db_name']} on {db_params['host']}:{db_params['port']}...")
        
        # Explicitly pass parameters to connect method
        if not db_manager.connect_to_database(
            db_name=db_params['db_name'],
            host=db_params['host'],
            port=db_params['port'],
            user=db_params['user'],
            password=db_params['password']
        )[0]:
            logger.error("Database connection method returned False. Check connection settings.")
            return False
            
        logger.info("Database connection established successfully.")
    except Exception as e:
        logger.error(f"Failed to connect to database: {str(e)}")
        logger.debug(traceback.format_exc())
        return False
    
    try:
        # Check if invoices table exists
        check_table_query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'invoices'
            )
        """
        table_result = db_manager.execute_query(check_table_query)
        
        if not table_result or 'error' in table_result or not table_result.get('rows') or not table_result['rows'][0][0]:
            logger.error("The 'invoices' table does not exist in the database.")
            return False
        
        # Check if vendor and vendor_name columns exist
        check_query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'invoices' 
            AND column_name IN ('vendor', 'vendor_name')
        """
        columns_result = db_manager.execute_query(check_query)
        
        if 'error' in columns_result or not columns_result.get('rows'):
            logger.error(f"Failed to query column information for 'invoices' table: {columns_result.get('error', 'Unknown error')}")
            return False
            
        existing_columns = [col[0] for col in columns_result['rows']]
        
        has_vendor = 'vendor' in existing_columns
        has_vendor_name = 'vendor_name' in existing_columns
        
        logger.info(f"Column check: vendor={has_vendor}, vendor_name={has_vendor_name}")
        
        if has_vendor and has_vendor_name:
            logger.info("Found both 'vendor' and 'vendor_name' columns. Migrating data...")
            
            # Check if vendor_name has NULL values that could be filled from vendor
            count_query = """
            SELECT COUNT(*) FROM invoices 
            WHERE vendor_name IS NULL AND vendor IS NOT NULL
            """
            
            count_result = db_manager.execute_query(count_query)
            
            if 'error' in count_result or not count_result.get('rows'):
                logger.error(f"Failed to count NULL vendor_name entries: {count_result.get('error', 'Unknown error')}")
                return False
                
            null_count = count_result['rows'][0][0]
            
            if null_count > 0:
                logger.info(f"Found {null_count} rows where vendor_name is NULL but vendor has values")
                logger.info("Copying data from vendor to vendor_name where needed...")
                
                # Copy data from vendor to vendor_name where vendor_name is NULL
                update_query = """
                UPDATE invoices
                SET vendor_name = vendor
                WHERE vendor_name IS NULL AND vendor IS NOT NULL
                """
                
                update_result = db_manager.execute_query(update_query)
                
                if 'error' in update_result:
                    logger.error(f"Error copying data: {update_result['error']}")
                    return False
                else:
                    logger.info(f"Successfully copied data for {null_count} rows")
            else:
                logger.info("No NULL vendor_name values that need filling from vendor")
            
            # Remove the old vendor column using PostgreSQL syntax
            logger.info("Dropping redundant vendor column...")
            
            try:
                # Use a transaction for safety
                db_manager.execute_query("BEGIN")
                
                drop_query = """
                ALTER TABLE invoices
                DROP COLUMN vendor
                """
                
                drop_result = db_manager.execute_query(drop_query)
                
                if 'error' in drop_result:
                    db_manager.execute_query("ROLLBACK")
                    logger.error(f"Error dropping column: {drop_result['error']}")
                    return False
                else:
                    db_manager.execute_query("COMMIT")
                    logger.info("Successfully dropped vendor column")
            except Exception as e:
                db_manager.execute_query("ROLLBACK")
                logger.error(f"Error during transaction: {str(e)}")
                return False
                
        elif not has_vendor and has_vendor_name:
            logger.info("vendor_name column already exists - no fix needed")
        
        elif has_vendor and not has_vendor_name:
            logger.info("Only vendor column exists. Renaming to vendor_name...")
            
            try:
                # Use a transaction for safety
                db_manager.execute_query("BEGIN")
                
                rename_query = """
                ALTER TABLE invoices
                RENAME COLUMN vendor TO vendor_name
                """
                
                rename_result = db_manager.execute_query(rename_query)
                
                if 'error' in rename_result:
                    db_manager.execute_query("ROLLBACK")
                    logger.error(f"Error renaming column: {rename_result['error']}")
                    return False
                else:
                    db_manager.execute_query("COMMIT")
                    logger.info("Successfully renamed vendor column to vendor_name")
            except Exception as e:
                db_manager.execute_query("ROLLBACK")
                logger.error(f"Error during transaction: {str(e)}")
                return False
        
        else:
            logger.info("Neither vendor nor vendor_name columns exist")
            logger.info("Adding vendor_name column...")
            
            try:
                add_query = """
                ALTER TABLE invoices
                ADD COLUMN vendor_name VARCHAR(100)
                """
                
                add_result = db_manager.execute_query(add_query)
                
                if 'error' in add_result:
                    logger.error(f"Error adding column: {add_result['error']}")
                    return False
                else:
                    logger.info("Successfully added vendor_name column")
            except Exception as e:
                logger.error(f"Error adding column: {str(e)}")
                return False
        
        # Verify the fix worked
        verify_query = """
        SELECT
            invoice_number,
            vendor_name,
            amount,
            payment_status
        FROM invoices
        LIMIT 5
        """
        
        verify_result = db_manager.execute_query(verify_query)
        
        if not 'error' in verify_result and verify_result.get('rows'):
            logger.info("\nVerification query succeeded using vendor_name column")
            logger.info(f"Found {len(verify_result.get('rows', []))} sample rows")
            logger.info("Database schema is now correct with vendor_name column")
            return True
        else:
            logger.error(f"\nVerification query failed: {verify_result.get('error', 'Unknown error')}")
            logger.error("There may still be issues with the vendor_name column")
            return False
            
    except Exception as e:
        logger.error(f"Error during vendor column fix: {str(e)}")
        logger.debug(traceback.format_exc())
        return False
    finally:
        if hasattr(db_manager, 'close'):
            logger.info("Closing database connection")
            db_manager.close()

def main():
    """Main function to run the vendor column fix"""
    try:
        success = fix_vendor_column()
        if success:
            logger.info("\nVendor column fix completed successfully!")
            return 0
        else:
            logger.error("\nVendor column fix failed. See errors above.")
            return 1
    except Exception as e:
        logger.error(f"\nUnhandled error: {str(e)}")
        logger.debug(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main())
