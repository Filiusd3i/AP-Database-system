#!/usr/bin/env python3
"""
Database Schema Checker

This script performs detailed checks on the database schema to identify
common issues, particularly focusing on the vendor/vendor_name column
inconsistency that has been identified as a common problem.
"""

import os
import sys
import psycopg2
import json
import argparse
from datetime import datetime
from dotenv import load_dotenv

def load_env_vars():
    """Load environment variables from .env file"""
    load_dotenv()
    
    # Database connection settings
    db_settings = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': os.getenv('DB_PORT', '5432'),
        'database': os.getenv('DB_NAME', 'postgres'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', ''),
    }
    
    return db_settings

def connect_to_db(settings):
    """Connect to the database"""
    try:
        conn = psycopg2.connect(
            host=settings['host'],
            port=settings['port'],
            database=settings['database'],
            user=settings['user'],
            password=settings['password']
        )
        return conn
    except Exception as e:
        print(f"Error connecting to database: {str(e)}")
        return None

def execute_query(conn, query, params=None):
    """Execute a query and return results"""
    if not conn:
        return {'error': 'No database connection'}
    
    try:
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        try:
            rows = cursor.fetchall()
            return {'rows': rows}
        except:
            # No results to fetch (for UPDATE, INSERT, etc.)
            return {'affected_rows': cursor.rowcount}
    except Exception as e:
        return {'error': str(e)}
    finally:
        if cursor:
            cursor.close()
            
def check_table_exists(conn, table_name):
    """Check if a table exists in the database"""
    query = """
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_name = %s
    )
    """
    result = execute_query(conn, query, (table_name,))
    
    if result.get('error') or not result.get('rows'):
        return False
    
    return result['rows'][0][0]

def check_column_exists(conn, table_name, column_name):
    """Check if a column exists in a table"""
    query = """
    SELECT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_name = %s AND column_name = %s
    )
    """
    result = execute_query(conn, query, (table_name, column_name))
    
    if result.get('error') or not result.get('rows'):
        return False
    
    return result['rows'][0][0]

def get_column_info(conn, table_name, column_name):
    """Get detailed information about a column"""
    query = """
    SELECT data_type, character_maximum_length, is_nullable, column_default
    FROM information_schema.columns
    WHERE table_name = %s AND column_name = %s
    """
    result = execute_query(conn, query, (table_name, column_name))
    
    if result.get('error') or not result.get('rows'):
        return None
    
    col_data = result['rows'][0]
    return {
        'data_type': col_data[0],
        'max_length': col_data[1],
        'nullable': col_data[2] == 'YES',
        'default': col_data[3]
    }

def check_null_values(conn, table_name, column_name):
    """Check if a column has NULL values"""
    if not check_column_exists(conn, table_name, column_name):
        return {'error': f"Column {column_name} does not exist in table {table_name}"}
    
    query = f"SELECT COUNT(*) FROM {table_name} WHERE {column_name} IS NULL"
    result = execute_query(conn, query)
    
    if result.get('error'):
        return {'error': result['error']}
    
    return {
        'null_count': result['rows'][0][0]
    }

def check_vendor_column_issue(conn):
    """Check for vendor/vendor_name column issue"""
    results = {
        'invoices_exists': False,
        'vendor_exists': False,
        'vendor_name_exists': False,
        'vendor_info': None,
        'vendor_name_info': None,
        'issue_detected': False,
        'recommendation': None,
        'data_counts': {}
    }
    
    # Check if invoices table exists
    results['invoices_exists'] = check_table_exists(conn, 'invoices')
    
    if not results['invoices_exists']:
        results['recommendation'] = "Invoices table does not exist. No vendor column issue to fix."
        return results
    
    # Check for vendor and vendor_name columns
    results['vendor_exists'] = check_column_exists(conn, 'invoices', 'vendor')
    results['vendor_name_exists'] = check_column_exists(conn, 'invoices', 'vendor_name')
    
    # Get column info if columns exist
    if results['vendor_exists']:
        results['vendor_info'] = get_column_info(conn, 'invoices', 'vendor')
        
    if results['vendor_name_exists']:
        results['vendor_name_info'] = get_column_info(conn, 'invoices', 'vendor_name')
    
    # Check data counts
    if results['vendor_exists']:
        # Check total rows with vendor data
        query = "SELECT COUNT(*) FROM invoices WHERE vendor IS NOT NULL"
        vendor_count = execute_query(conn, query)
        if not vendor_count.get('error') and vendor_count.get('rows'):
            results['data_counts']['vendor_not_null'] = vendor_count['rows'][0][0]
    
    if results['vendor_name_exists']:
        # Check total rows with vendor_name data
        query = "SELECT COUNT(*) FROM invoices WHERE vendor_name IS NOT NULL"
        vendor_name_count = execute_query(conn, query)
        if not vendor_name_count.get('error') and vendor_name_count.get('rows'):
            results['data_counts']['vendor_name_not_null'] = vendor_name_count['rows'][0][0]
    
    # Check for rows where one column has data but the other is NULL
    if results['vendor_exists'] and results['vendor_name_exists']:
        query = "SELECT COUNT(*) FROM invoices WHERE vendor IS NOT NULL AND vendor_name IS NULL"
        result = execute_query(conn, query)
        if not result.get('error') and result.get('rows'):
            results['data_counts']['vendor_has_data_vendor_name_null'] = result['rows'][0][0]
        
        query = "SELECT COUNT(*) FROM invoices WHERE vendor IS NULL AND vendor_name IS NOT NULL"
        result = execute_query(conn, query)
        if not result.get('error') and result.get('rows'):
            results['data_counts']['vendor_null_vendor_name_has_data'] = result['rows'][0][0]
    
    # Determine the issue and recommendation
    if results['vendor_exists'] and not results['vendor_name_exists']:
        results['issue_detected'] = True
        results['recommendation'] = "Rename 'vendor' column to 'vendor_name' to match the expected schema."
    elif results['vendor_exists'] and results['vendor_name_exists']:
        # If both exist, we need to check if data needs to be merged
        if results['data_counts'].get('vendor_has_data_vendor_name_null', 0) > 0:
            results['issue_detected'] = True
            results['recommendation'] = "Copy non-NULL values from 'vendor' to 'vendor_name' where 'vendor_name' is NULL, then drop the 'vendor' column."
        else:
            results['issue_detected'] = True
            results['recommendation'] = "Drop the redundant 'vendor' column since 'vendor_name' is the one used by the application."
    elif not results['vendor_exists'] and not results['vendor_name_exists']:
        results['issue_detected'] = True
        results['recommendation'] = "Add the missing 'vendor_name' column with VARCHAR(100) data type."
    
    # Check if joins with vendors table would work
    results['vendors_exists'] = check_table_exists(conn, 'vendors')
    if results['vendors_exists']:
        results['vendors_name_exists'] = check_column_exists(conn, 'vendors', 'name')
        
        if not results['vendors_name_exists']:
            results['warning'] = "vendors table exists but doesn't have a 'name' column, which is expected for joins"
    
    return results

def check_table_columns(conn, table_name, expected_columns):
    """Check if a table has all the expected columns"""
    results = {
        'table_exists': False,
        'missing_columns': [],
        'present_columns': [],
        'unexpected_columns': []
    }
    
    # Check if table exists
    results['table_exists'] = check_table_exists(conn, table_name)
    
    if not results['table_exists']:
        return results
    
    # Get all columns in the table
    query = """
    SELECT column_name
    FROM information_schema.columns
    WHERE table_name = %s
    """
    result = execute_query(conn, query, (table_name,))
    
    if result.get('error') or not result.get('rows'):
        results['error'] = result.get('error', 'No columns found')
        return results
    
    actual_columns = [row[0].lower() for row in result['rows']]
    expected_lower = [col.lower() for col in expected_columns]
    
    # Check for missing and unexpected columns
    for col in expected_lower:
        if col in actual_columns:
            results['present_columns'].append(col)
        else:
            results['missing_columns'].append(col)
    
    for col in actual_columns:
        if col not in expected_lower:
            results['unexpected_columns'].append(col)
    
    return results

def check_data_types(conn, table_name, expected_types):
    """Check if columns have the expected data types"""
    results = {
        'mismatched_types': [],
        'correct_types': [],
    }
    
    # Check each column
    for col_name, expected_type in expected_types.items():
        # Skip if column doesn't exist
        if not check_column_exists(conn, table_name, col_name):
            continue
        
        # Get current type
        col_info = get_column_info(conn, table_name, col_name)
        if not col_info:
            continue
        
        current_type = col_info['data_type'].lower()
        
        # Check if type matches (accounting for type variations)
        type_matches = False
        expected_type_lower = expected_type.lower()
        
        # Handle type variations (e.g., varchar = character varying)
        if (current_type == expected_type_lower or
            (current_type == 'character varying' and expected_type_lower == 'varchar') or
            (current_type == 'varchar' and expected_type_lower == 'character varying') or
            (current_type == 'numeric' and expected_type_lower.startswith('decimal')) or
            (current_type == 'double precision' and expected_type_lower == 'float8')):
            results['correct_types'].append(col_name)
        else:
            results['mismatched_types'].append({
                'column': col_name,
                'current_type': current_type,
                'expected_type': expected_type
            })
    
    return results

def run_query_check(conn, query, description):
    """Run a query and return the results with a description"""
    result = execute_query(conn, query)
    
    return {
        'description': description,
        'result': result
    }

def get_sample_data(conn, table_name, columns=None, limit=5):
    """Get sample data from a table"""
    if not columns:
        columns_str = "*"
    else:
        columns_str = ", ".join(columns)
    
    query = f"SELECT {columns_str} FROM {table_name} LIMIT {limit}"
    return execute_query(conn, query)

def export_report(results, output_file):
    """Export the check results to a JSON file"""
    try:
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"Report exported to {output_file}")
    except Exception as e:
        print(f"Error exporting report: {str(e)}")

def print_header(title):
    """Print a formatted header"""
    print("\n" + "=" * 70)
    print(f" {title} ".center(70, "="))
    print("=" * 70)

def print_section(title):
    """Print a section header"""
    print("\n" + "-" * 70)
    print(f" {title} ".center(70, "-"))
    print("-" * 70)

def display_vendor_check_results(results):
    """Display the vendor column check results in a readable format"""
    print_header("VENDOR COLUMN ISSUE CHECK")
    
    print(f"Invoices table exists: {results['invoices_exists']}")
    
    if not results['invoices_exists']:
        print("No vendor column checks performed as invoices table doesn't exist")
        return
    
    print(f"Vendor column exists: {results['vendor_exists']}")
    print(f"Vendor_name column exists: {results['vendor_name_exists']}")
    
    if results['vendor_exists']:
        print("\nVendor column details:")
        print(f"  Data type: {results['vendor_info']['data_type']}")
        print(f"  Nullable: {results['vendor_info']['nullable']}")
        print(f"  Max length: {results['vendor_info']['max_length']}")
    
    if results['vendor_name_exists']:
        print("\nVendor_name column details:")
        print(f"  Data type: {results['vendor_name_info']['data_type']}")
        print(f"  Nullable: {results['vendor_name_info']['nullable']}")
        print(f"  Max length: {results['vendor_name_info']['max_length']}")
    
    if 'data_counts' in results and results['data_counts']:
        print("\nData distribution:")
        for key, value in results['data_counts'].items():
            print(f"  {key}: {value}")
    
    if results['issue_detected']:
        print("\nISSUE DETECTED: The vendor column configuration is not optimal")
        print(f"RECOMMENDATION: {results['recommendation']}")
    else:
        print("\nNo vendor column issues detected.")

def main():
    """Main entry point for the script"""
    parser = argparse.ArgumentParser(description='Check database schema issues')
    parser.add_argument('--export', help='Export results to JSON file')
    parser.add_argument('--verbose', action='store_true', help='Show more detailed output')
    args = parser.parse_args()
    
    print_header("DATABASE SCHEMA CHECKER")
    print(f"Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Load environment variables
    db_settings = load_env_vars()
    
    # Connect to database
    conn = connect_to_db(db_settings)
    if not conn:
        print("Failed to connect to database. Please check your database settings.")
        sys.exit(1)
    
    # Run checks
    results = {}
    
    # Check vendor/vendor_name issue
    vendor_results = check_vendor_column_issue(conn)
    results['vendor_check'] = vendor_results
    display_vendor_check_results(vendor_results)
    
    # Check for expected columns in invoices table
    print_section("TABLE STRUCTURE CHECK")
    
    expected_columns = [
        'invoice_id', 'invoice_number', 'vendor_name', 'amount', 
        'invoice_date', 'due_date', 'payment_status', 'fund_paid_by',
        'dateofpayment', 'approver'
    ]
    
    column_check = check_table_columns(conn, 'invoices', expected_columns)
    results['column_check'] = column_check
    
    print(f"Invoices table exists: {column_check['table_exists']}")
    
    if column_check['table_exists']:
        if column_check['missing_columns']:
            print(f"\nMissing columns: {', '.join(column_check['missing_columns'])}")
        else:
            print("\nAll expected columns are present")
        
        if column_check['unexpected_columns']:
            print(f"\nUnexpected columns: {', '.join(column_check['unexpected_columns'])}")
    
    # Check data types for critical columns
    expected_types = {
        'invoice_number': 'VARCHAR',
        'vendor_name': 'VARCHAR',
        'amount': 'NUMERIC',
        'invoice_date': 'DATE',
        'due_date': 'DATE',
        'payment_status': 'VARCHAR',
        'dateofpayment': 'DATE'
    }
    
    type_check = check_data_types(conn, 'invoices', expected_types)
    results['type_check'] = type_check
    
    print_section("DATA TYPE CHECK")
    
    if type_check['mismatched_types']:
        print("Columns with incorrect data types:")
        for mismatch in type_check['mismatched_types']:
            print(f"  {mismatch['column']}: Current={mismatch['current_type']}, Expected={mismatch['expected_type']}")
    else:
        print("All column data types are correct")
    
    # Sample data check
    if args.verbose and check_table_exists(conn, 'invoices'):
        print_section("SAMPLE DATA")
        sample_columns = ['invoice_number', 'vendor_name', 'amount', 'payment_status']
        sample = get_sample_data(conn, 'invoices', sample_columns)
        
        if not sample.get('error') and sample.get('rows'):
            print(f"Sample data from invoices table (first {len(sample['rows'])} rows):")
            for i, row in enumerate(sample['rows']):
                print(f"  Row {i+1}: {row}")
        else:
            print("No sample data available or error fetching data")
    
    # Export results if requested
    if args.export:
        export_report(results, args.export)
    
    # Close database connection
    conn.close()
    
    print("\nCheck completed. See above for any issues detected and recommendations.")

if __name__ == "__main__":
    main()
