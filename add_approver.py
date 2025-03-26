#!/usr/bin/env python3
"""
Add Approver Column Script

This script adds the approver column to the invoices table in the database.
It uses the add_approver_column function from db_schema_fix.py.
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Add parent directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from finance_assistant.db_schema_fix import connect_database, add_approver_column

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("add_approver")

def main():
    """Main entry point for adding approver column"""
    print("=" * 60)
    print("Database Schema Update - Add Approver Column")
    print("=" * 60)
    print()
    
    # Load environment variables
    load_dotenv()
    logger.info("Loaded environment variables")
    
    # Connect to database
    logger.info("Connecting to database...")
    db_manager, success = connect_database()
    
    if not success:
        logger.error("Failed to connect to database")
        return 1
    
    try:
        # Add approver column
        print("Adding approver column to invoices table...")
        result = add_approver_column(db_manager)
        
        if result:
            print("\nSuccess: Approver column added to invoices table!")
            print("\nThis column allows tracking of who approved each invoice for payment,")
            print("providing an audit trail and supporting approval workflow functionality.")
            print("\nNext steps:")
            print("1. Update your application UI to include approver information")
            print("2. Consider adding an approval workflow for new invoices")
        else:
            print("\nError: Failed to add approver column. See logs for details.")
        
        return 0 if result else 1
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return 1
    finally:
        # Close database connection
        if db_manager:
            db_manager.close()
            logger.info("Database connection closed")

if __name__ == "__main__":
    sys.exit(main())
