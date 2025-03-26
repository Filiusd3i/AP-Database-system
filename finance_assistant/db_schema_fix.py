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

def add_approver_column(db_manager):
    """Add the approver column to the invoices table if it doesn't exist
    
    Args:
        db_manager: The database manager instance
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info("Checking for approver column in invoices table")
        
        # Check if the approver column already exists
        columns_result = db_manager.execute_query(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'invoices' AND column_name = 'approver'"
        )
        
        if columns_result['rows'] and len(columns_result['rows']) > 0:
            logger.info("approver column already exists in invoices table")
            return True
        
        logger.info("Adding approver column to invoices table")
        
        # Create a backup of the invoices table first
        backup_check = db_manager.execute_query(
            "SELECT to_regclass('public.invoices_backup')"
        )
        
        if backup_check['rows'][0][0] is None:
            logger.info("Creating backup table before adding column")
            backup_query = """
            CREATE TABLE invoices_backup AS SELECT * FROM invoices;
            """
            
            result = db_manager.execute_query(backup_query)
            if 'error' in result and result['error']:
                logger.error(f"Error creating backup table: {result['error']}")
                return False
                
            logger.info("Created backup table 'invoices_backup'")
        
        # Start a transaction
        db_manager.execute_query("BEGIN")
        
        # Add the approver column
        add_column_query = """
        ALTER TABLE invoices
        ADD COLUMN approver VARCHAR(100);
        """
        
        result = db_manager.execute_query(add_column_query)
        
        if 'error' in result and result['error']:
            db_manager.execute_query("ROLLBACK")
            logger.error(f"Error adding approver column: {result['error']}")
            return False
        
        # Commit the transaction
        db_manager.execute_query("COMMIT")
        
        logger.info("Successfully added approver column to invoices table")
        
        # Update the changelog
        try:
            update_changelog("Added approver column to invoices table for tracking approval workflow")
        except Exception as e:
            logger.warning(f"Could not update changelog: {str(e)}")
        
        return True
        
    except Exception as e:
        # Ensure transaction is rolled back in case of error
        try:
            db_manager.execute_query("ROLLBACK")
        except:
            pass
            
        logger.error(f"Error adding approver column: {str(e)}")
        return False

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
        clean_query = r"""
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

def fix_column_misalignment(db_manager):
    """Fix misaligned columns in the invoices table
    
    This function fixes an issue where some expected columns are empty
    but the data exists in other columns with different names.
    
    Args:
        db_manager: The database manager instance
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info("Fixing invoices table data alignment")
        
        # Create backup table
        backup_query = """
        DROP TABLE IF EXISTS invoices_backup;
        CREATE TABLE invoices_backup AS SELECT * FROM invoices;
        """
        
        result = db_manager.execute_query(backup_query)
        if 'error' in result and result['error']:
            logger.error(f"Error creating backup table: {result['error']}")
            return False
            
        logger.info("Created backup table 'invoices_backup'")
        
        # Fix the data by populating the expected columns
        update_query = """
        UPDATE invoices 
        SET 
            vendor = vendor_name,
            amount = CASE 
                WHEN amount IS NULL AND total_amount ~ '^[0-9,.]+$' 
                THEN CAST(REPLACE(REPLACE(total_amount, ',', ''), '$', '') AS NUMERIC) 
                ELSE amount 
            END,
            payment_status = status1,
            fund_paid_by = CASE 
                WHEN fund_id IS NOT NULL THEN CAST(fund_id AS TEXT)
                ELSE fund_paid_by
            END
        """
        
        result = db_manager.execute_query(update_query)
        if 'error' in result and result['error']:
            logger.error(f"Error updating misaligned columns: {result['error']}")
            # Attempt to restore from backup
            restore_query = """
            DROP TABLE IF EXISTS invoices;
            ALTER TABLE invoices_backup RENAME TO invoices;
            """
            db_manager.execute_query(restore_query)
            logger.info("Restored from backup after failed update")
            return False
        
        logger.info("Successfully fixed column misalignment in invoices table")
        return True
        
    except Exception as e:
        logger.error(f"Error fixing column misalignment: {str(e)}")
        return False

def fix_amount_column_types(db_manager):
    """Fix the data types of amount-related columns in the invoices table
    
    This function converts text amount columns to numeric types and removes redundant columns.
    
    Args:
        db_manager: The database manager instance
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info("Fixing amount column types in invoices table")
        
        # Create backup table if it doesn't exist
        backup_check = db_manager.execute_query(
            "SELECT to_regclass('public.invoices_backup')"
        )
        
        if backup_check['rows'][0][0] is None:
            backup_query = """
            CREATE TABLE invoices_backup AS SELECT * FROM invoices;
            """
            
            result = db_manager.execute_query(backup_query)
            if 'error' in result and result['error']:
                logger.error(f"Error creating backup table: {result['error']}")
                return False
                
            logger.info("Created backup table 'invoices_backup'")
        else:
            logger.info("Backup table 'invoices_backup' already exists")
        
        # Check columns and their data types
        columns_result = db_manager.execute_query(
            "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'invoices'"
        )
        
        column_types = {}
        for row in columns_result['rows']:
            column_types[row[0]] = row[1]
            
        logger.info(f"Current column types: {column_types}")
        
        # 1. Fix total_amount to numeric
        if 'total_amount' in column_types and column_types['total_amount'].lower() != 'numeric':
            logger.info("Converting total_amount from text to numeric")
            conversion_query = """
            ALTER TABLE invoices 
            ALTER COLUMN total_amount TYPE NUMERIC(10,2) 
            USING CASE 
                WHEN total_amount ~ '^[$]?[0-9,.]+$' 
                    THEN REPLACE(REPLACE(total_amount, ',', ''), '$', '')::NUMERIC(10,2)
                ELSE NULL 
            END;
            """
            
            result = db_manager.execute_query(conversion_query)
            if 'error' in result and result['error']:
                logger.error(f"Error converting total_amount: {result['error']}")
                return False
                
            logger.info("Successfully converted total_amount to NUMERIC")
        
        # 2. Fix amount_paid to numeric
        if 'amount_paid' in column_types and column_types['amount_paid'].lower() != 'numeric':
            logger.info("Converting amount_paid from text to numeric")
            conversion_query = """
            ALTER TABLE invoices 
            ALTER COLUMN amount_paid TYPE NUMERIC(10,2) 
            USING CASE 
                WHEN amount_paid ~ '^[$]?[0-9,.]+$' 
                    THEN REPLACE(REPLACE(amount_paid, ',', ''), '$', '')::NUMERIC(10,2)
                ELSE NULL 
            END;
            """
            
            result = db_manager.execute_query(conversion_query)
            if 'error' in result and result['error']:
                logger.error(f"Error converting amount_paid: {result['error']}")
                return False
                
            logger.info("Successfully converted amount_paid to NUMERIC")
        
        # 3. Fix dateofpayment to date
        if 'dateofpayment' in column_types and column_types['dateofpayment'].lower() != 'date':
            logger.info("Converting dateofpayment from text to date")
            
            # First, update any MM/DD/YYYY format to YYYY-MM-DD
            format_query = """
            UPDATE invoices
            SET dateofpayment = 
                CASE 
                    WHEN dateofpayment ~ '^[0-9]{1,2}/[0-9]{1,2}/[0-9]{4}$' THEN
                        to_char(to_date(dateofpayment, 'MM/DD/YYYY'), 'YYYY-MM-DD')
                    ELSE dateofpayment
                END
            WHERE dateofpayment IS NOT NULL AND dateofpayment ~ '^[0-9]{1,2}/[0-9]{1,2}/[0-9]{4}$';
            """
            
            result = db_manager.execute_query(format_query)
            if 'error' in result and result['error']:
                logger.error(f"Error formatting dateofpayment: {result['error']}")
                # Continue anyway, it might still work with the conversion
            
            # Convert to date type
            conversion_query = """
            ALTER TABLE invoices 
            ALTER COLUMN dateofpayment TYPE DATE 
            USING CASE 
                WHEN dateofpayment ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' THEN
                    dateofpayment::DATE
                ELSE NULL 
            END;
            """
            
            result = db_manager.execute_query(conversion_query)
            if 'error' in result and result['error']:
                logger.error(f"Error converting dateofpayment: {result['error']}")
                return False
                
            logger.info("Successfully converted dateofpayment to DATE")
        
        # 4. Remove vendor column (copying to vendor_name if needed)
        if 'vendor' in column_types:
            logger.info("Removing redundant vendor column")
            
            # First ensure vendor_name has all the data
            if 'vendor_name' in column_types:
                update_query = """
                UPDATE invoices
                SET vendor_name = COALESCE(vendor_name, vendor)
                WHERE vendor_name IS NULL AND vendor IS NOT NULL;
                """
                
                result = db_manager.execute_query(update_query)
                if 'error' in result and result['error']:
                    logger.error(f"Error updating vendor_name: {result['error']}")
            
            # Then drop the column
            drop_query = """
            ALTER TABLE invoices DROP COLUMN vendor;
            """
            
            result = db_manager.execute_query(drop_query)
            if 'error' in result and result['error']:
                logger.error(f"Error dropping vendor column: {result['error']}")
                return False
                
            logger.info("Successfully removed redundant vendor column")
        
        # 5. Ensure status1 values are copied to payment_status
        if 'status1' in column_types and 'payment_status' in column_types:
            logger.info("Syncing payment_status from status1")
            
            update_query = """
            UPDATE invoices
            SET payment_status = status1
            WHERE status1 IS NOT NULL AND (payment_status IS NULL OR payment_status = '');
            """
            
            result = db_manager.execute_query(update_query)
            if 'error' in result and result['error']:
                logger.error(f"Error updating payment_status: {result['error']}")
                return False
                
            logger.info("Successfully synced payment_status from status1")
        
        # 6. Sync amount with total_amount if needed
        if 'amount' in column_types and 'total_amount' in column_types:
            logger.info("Syncing amount with total_amount")
            
            update_query = """
            UPDATE invoices
            SET amount = total_amount
            WHERE total_amount IS NOT NULL AND (amount IS NULL);
            """
            
            result = db_manager.execute_query(update_query)
            if 'error' in result and result['error']:
                logger.error(f"Error updating amount: {result['error']}")
                return False
                
            logger.info("Successfully synced amount with total_amount")
        
        # Update the changelog
        try:
            update_changelog("Fixed amount column types and redundancy issues")
        except Exception as e:
            logger.warning(f"Could not update changelog: {str(e)}")
            
        return True
        
    except Exception as e:
        logger.error(f"Error fixing amount column types: {str(e)}")
        return False

def update_changelog(change_description):
    """Update the CHANGELOG.md file with the latest changes
    
    Args:
        change_description: Description of the changes made
    """
    import datetime
    
    # Define the changelog path - at the project root
    changelog_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "CHANGELOG.md")
    
    # Get the current date
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # Check if changelog exists
    if os.path.exists(changelog_path):
        # Read existing content
        with open(changelog_path, 'r') as file:
            content = file.read()
    else:
        # Create new content with header
        content = "# Changelog\n\nAll notable changes to this project will be documented in this file.\n\n"
    
    # Create the new entry
    new_entry = f"## [{today}] - Schema Fix\n\n"
    new_entry += "### Changes:\n"
    new_entry += f"- {change_description}\n\n"
    
    # Add the entry after the header (before any existing entries)
    if "## [" in content:
        parts = content.split("## [", 1)
        content = parts[0] + new_entry + "## [" + parts[1]
    else:
        content += new_entry
    
    # Write back to the file
    with open(changelog_path, 'w') as file:
        file.write(content)
    
    logger.info(f"Updated CHANGELOG.md with latest changes")

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
        clean_query = r"""
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
    parser.add_argument("--fix-columns", action="store_true", help="Fix misaligned columns in invoices table")
    parser.add_argument("--fix-amounts", action="store_true", help="Fix amount column types and redundancy issues")
    parser.add_argument("--add-approver", action="store_true", help="Add approver column to invoices table")
    
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
        
        if args.all or args.fix_columns:
            if fix_column_misalignment(db_manager):
                logger.info("Successfully fixed column misalignment in invoices table")
            else:
                logger.error("Failed to fix column misalignment in invoices table")
        
        if args.all or args.fix_amounts:
            if fix_amount_column_types(db_manager):
                logger.info("Successfully fixed amount column types and redundancy issues")
            else:
                logger.error("Failed to fix amount column types")
        
        if args.all or args.add_approver:
            if add_approver_column(db_manager):
                logger.info("Successfully added approver column to invoices table")
            else:
                logger.error("Failed to add approver column to invoices table")
                
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
