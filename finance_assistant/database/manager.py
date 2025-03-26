#!/usr/bin/env python3
"""
Database Manager Module

Provides a unified interface for database operations.
"""

import logging
import os
import time
from typing import Dict, List, Any, Optional
from .postgres_db import PostgresDatabase
from finance_assistant.schema_validator import SchemaValidator
import csv
import threading
import re
import difflib
import tkinter as tk
from tkinter import ttk, messagebox

# Import the ultimate logger
from ultimate_logger import (
    configure_ultimate_logging, 
    log_execution_time, 
    log_context, 
    log_with_error_code,
    log_state_transition,
    log_database_query
)

# Configure component logger
logger = configure_ultimate_logging(
    app_name="finance_db_assistant",
    component_name="database_manager",
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    console_output=True,
    file_output=True,
    file_path="logs/finance_app.log"
)

class DatabaseManager:
    """Database manager that provides a unified interface for database operations"""
    
    def __init__(self, app=None):
        """Initialize the database manager
        
        Args:
            app: Optional reference to the main application
        """
        with log_context(logger, action="initialize_db_manager"):
            self.app = app
            self.db = PostgresDatabase()
            self.connected = False
            self.tables = []  # Add tables list attribute
            self.schema_validator = None  # Schema validator instance
            logger.info("Database manager initialized")
            
    @log_execution_time(logger)
    def connect_to_database(self, db_name: str, host: str = "localhost", 
                          port: int = 5432, user: str = "postgres", 
                          password: str = None) -> tuple[bool, str]:
        """Connect to the database
        
        Args:
            db_name: Name of the database
            host: Database host
            port: Database port
            user: Username
            password: Password
            
        Returns:
            tuple: (success, message)
        """
        conn_context = {
            "db_name": db_name,
            "host": host,
            "port": port,
            "user": user,
            "action": "connect_database"
        }
        
        with log_context(logger, **conn_context):
            try:
                # Connect using PostgresDatabase
                logger.info(f"Attempting to connect to database '{db_name}' on {host}:{port}")
                if self.db.connect(db_name, host, port, user, password):
                    self.connected = True
                    self.db_name = db_name  # Store the database name
                    
                    # Retrieve table list after successful connection
                    self._fetch_tables()
                    
                    # Initialize and use schema validator
                    self._initialize_schema_validator()
                    
                    logger.info(f"Successfully connected to database '{db_name}'", 
                                extra={"table_count": len(self.tables)})
                    return True, f"Successfully connected to database '{db_name}'"
                else:
                    error_msg = self.db.error
                    log_with_error_code(
                        logger, 
                        "DB_CONN_FAIL", 
                        f"Failed to connect to database: {error_msg}",
                        error_details=error_msg
                    )
                    return False, f"Failed to connect: {error_msg}"
            except Exception as e:
                error_msg = str(e)
                logger.exception_with_context(f"Exception connecting to database: {error_msg}")
                return False, f"Failed to connect: {error_msg}"
    
    @log_execution_time(logger)
    def _initialize_schema_validator(self):
        """Initialize the schema validator and validate critical tables"""
        with log_context(logger, action="initialize_schema_validator"):
            try:
                # Create schema validator instance
                logger.info("Initializing schema validator")
                self.schema_validator = SchemaValidator(self)
                
                # Define tables to validate and fix
                tables_to_validate = ['invoices', 'vendors', 'funds']
                validation_results = {}
                
                for table in tables_to_validate:
                    if table in self.tables:
                        logger.info(f"Validating and auto-fixing {table} table schema")
                        
                        # First check for missing columns (traditional validation)
                        column_result = self.schema_validator.validate_table(table, auto_fix=True)
                        
                        # Then check and fix column types (enhanced validation)
                        type_result = self.schema_validator.validate_table_schema(table, auto_fix=True)
                        
                        validation_results[table] = {
                            'column_validation': column_result,
                            'type_validation': type_result,
                            'valid': column_result['valid'] and type_result['valid']
                        }
                        
                        # Log validation results
                        if validation_results[table]['valid']:
                            logger.info(f"{table} table schema is valid")
                        else:
                            log_with_error_code(
                                logger, 
                                "SCHEMA_INVALID", 
                                f"{table} table schema validation failed",
                                table=table,
                                validation_results=validation_results[table]
                            )
                    else:
                        logger.info(f"{table} table not found, will be created when needed")
                
                # Report any type conversions that were performed
                if hasattr(self.schema_validator, 'type_conversions_performed') and self.schema_validator.type_conversions_performed:
                    conversions = self.schema_validator.type_conversions_performed
                    logger.info(f"Performed {len(conversions)} column type conversions")
                    for conversion in conversions:
                        log_state_transition(
                            logger,
                            "Column Type",
                            conversion['from_type'],
                            conversion['to_type'],
                            table=conversion['table'],
                            column=conversion['column']
                        )
                    
                return validation_results
                    
            except Exception as e:
                error_msg = str(e)
                logger.exception_with_context(f"Error initializing schema validator: {error_msg}")
            return None
        
    @log_execution_time(logger)
    def ensure_valid_schema(self, table_name: str) -> bool:
        """Ensure that a table exists and has the correct schema
        
        Args:
            table_name: The name of the table to check/fix
            
        Returns:
            bool: True if the table has a valid schema, False otherwise
        """
        with log_context(logger, action="ensure_valid_schema", table=table_name):
            if not self.connected:
                log_with_error_code(logger, "DB_NOT_CONNECTED", "Not connected to database")
                return False
                
            # Make sure schema validator is initialized
            if not self.schema_validator:
                logger.info("Schema validator not initialized, initializing now")
                self._initialize_schema_validator()
                
            # Check and fix schema
            logger.info(f"Ensuring valid schema for table {table_name}")
            result = self.schema_validator.ensure_valid_schema(table_name)
            
            if result:
                logger.info(f"Table {table_name} has valid schema")
            else:
                log_with_error_code(
                    logger, 
                    "SCHEMA_VALIDATION_FAILED", 
                    f"Failed to ensure valid schema for table {table_name}",
                    table=table_name
                )
                
            return result
    
    @log_execution_time(logger)
    def _fetch_tables(self):
        """Fetch the list of tables from the database"""
        with log_context(logger, action="fetch_tables"):
            if not self.connected or not self.db:
                log_with_error_code(logger, "DB_NOT_CONNECTED", "Cannot fetch tables: Not connected to database")
                return
                
            try:
                # Use the get_tables method from PostgresDatabase
                logger.debug("Fetching tables from database")
                result = self.db.get_tables()
                
                if 'error' in result and result['error']:
                    log_with_error_code(
                        logger, 
                        "DB_FETCH_TABLES_ERROR", 
                        f"Error fetching tables: {result['error']}",
                        error_details=result['error']
                    )
                elif 'tables' in result:
                    prev_tables = set(self.tables) if hasattr(self, 'tables') else set()
                    self.tables = result['tables']
                    new_tables = set(self.tables)
                    
                    added_tables = new_tables - prev_tables
                    removed_tables = prev_tables - new_tables
                    
                    if added_tables:
                        logger.info(f"Added tables: {', '.join(added_tables)}", extra={"added_tables": list(added_tables)})
                    
                    if removed_tables:
                        logger.info(f"Removed tables: {', '.join(removed_tables)}", extra={"removed_tables": list(removed_tables)})
                    
                    logger.info(f"Fetched {len(self.tables)} tables from database", extra={"tables": self.tables})
                    
                    if not self.tables:
                        logger.warning("No tables found in database. You may need to initialize with sample tables.")
                
            except Exception as e:
                logger.exception_with_context(f"Exception in _fetch_tables: {str(e)}")
    
    @property
    def is_connected(self):
        """Check if connected to a database
        
        Returns:
            bool: True if connected, False otherwise
        """
        return self.connected
        
    @log_execution_time(logger, level=logging.DEBUG)  # Lower level since this is called frequently
    def execute_query(self, query: str, params: List = None) -> Dict:
        """Execute a SQL query
        
        Args:
            query: The SQL query to execute
            params: Optional parameters for the query
            
        Returns:
            Dict: Query results
        """
        with log_context(logger, action="execute_query"):
            if not self.connected:
                log_with_error_code(logger, "DB_NOT_CONNECTED", "Not connected to a database")
                return {'error': 'Not connected to a database'}
            
            # Record start time for performance measurement
            start_time = time.time()
            
            # Execute the query
            result = self.db.execute_query(query, params)
            
            # Calculate execution time
            execution_time = (time.time() - start_time) * 1000  # Convert to ms
            
            # Use the enhanced database query logging
            log_database_query(logger, query, params, result, execution_time)
                
            return result
    
    def get_invoice_data(self, filters=None):
        """Get invoice data with optional filters
        
        Args:
            filters: Optional dictionary of filters to apply
            
        Returns:
            Dict: Query results with invoice data
        """
        if not self.connected:
            return {'error': 'Not connected to a database', 'rows': []}
            
        # Ensure invoices table exists and has correct schema
        if not self.ensure_valid_schema('invoices'):
            return {'error': 'Invoices table has invalid schema', 'rows': []}
            
        # Build the query
        query = "SELECT * FROM invoices"
        params = []
        
        # Apply filters if provided
        if filters:
            where_clauses = []
            
            # Filter by status
            if 'status' in filters and filters['status']:
                where_clauses.append("payment_status = %s")
                params.append(filters['status'])
                
            # Filter by fund
            if 'fund' in filters and filters['fund']:
                where_clauses.append("fund_paid_by = %s")
                params.append(filters['fund'])
                
            # Filter by date range
            if 'start_date' in filters and filters['start_date']:
                where_clauses.append("invoice_date >= %s")
                params.append(filters['start_date'])
                
            if 'end_date' in filters and filters['end_date']:
                where_clauses.append("invoice_date <= %s")
                params.append(filters['end_date'])
                
            # Add WHERE clause if filters were applied
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
        
        # Add ORDER BY
        query += " ORDER BY invoice_date DESC"
        
        # Execute the query
        return self.db.execute_query(query, params)
    
    def get_invoice_summary(self):
        """Get summary statistics for invoices
        
        Returns:
            Dict: Summary statistics
        """
        if not self.connected:
            return {
                'total_amount': 0,
                'paid_count': 0,
                'unpaid_count': 0,
                'overdue_count': 0
            }
            
        # Ensure invoices table exists and has correct schema
        if not self.ensure_valid_schema('invoices'):
            return {
                'total_amount': 0,
                'paid_count': 0,
                'unpaid_count': 0,
                'overdue_count': 0
            }
            
        try:
            # Get total amount
            result = self.db.execute_query(
                "SELECT SUM(amount) AS total FROM invoices"
            )
            total_amount = 0
            if 'rows' in result and result['rows'] and result['rows'][0][0]:
                total_amount = float(result['rows'][0][0])
                
            # Get paid count
            result = self.db.execute_query(
                "SELECT COUNT(*) FROM invoices WHERE payment_status = 'Paid'"
            )
            paid_count = 0
            if 'rows' in result and result['rows']:
                paid_count = int(result['rows'][0][0])
                
            # Get unpaid count
            result = self.db.execute_query(
                "SELECT COUNT(*) FROM invoices WHERE payment_status = 'Unpaid'"
            )
            unpaid_count = 0
            if 'rows' in result and result['rows']:
                unpaid_count = int(result['rows'][0][0])
                
            # Get overdue count
            result = self.db.execute_query(
                "SELECT COUNT(*) FROM invoices WHERE payment_status = 'Unpaid' AND due_date < CURRENT_DATE"
            )
            overdue_count = 0
            if 'rows' in result and result['rows']:
                overdue_count = int(result['rows'][0][0])
                
            return {
                'total_amount': total_amount,
                'paid_count': paid_count,
                'unpaid_count': unpaid_count,
                'overdue_count': overdue_count
            }
            
        except Exception as e:
            logger.error(f"Error getting invoice summary: {str(e)}")
            return {
                'total_amount': 0,
                'paid_count': 0,
                'unpaid_count': 0,
                'overdue_count': 0
            }
            
    def close(self):
        """Close the database connection"""
        if self.db and self.connected:
            try:
                self.db.connection.close()
                self.connected = False
                self.tables = []
                logger.info("Database connection closed")
            except Exception as e:
                logger.error(f"Error closing database connection: {str(e)}")
    
    # Dashboard-specific methods
    
    def get_invoice_counts(self):
        """Get counts of invoices by status
        
        Returns:
            dict: Counts of paid, unpaid, and overdue invoices
        """
        if not self.connected:
            return {'paid': 0, 'unpaid': 0, 'overdue': 0}
        
        return self.db.get_invoice_counts()
    
    def get_invoice_total(self):
        """Get the total amount of all invoices
        
        Returns:
            float: Total invoice amount
        """
        if not self.connected:
            return 0.0
        
        return self.db.get_invoice_total()
    
    def get_impact_distribution(self):
        """Get the distribution of invoices by impact
        
        Returns:
            dict: Query result with impact distribution data
        """
        if not self.connected:
            return {'rows': [], 'columns': []}
        
        return self.db.get_impact_distribution()
    
    def get_fund_distribution(self):
        """Get the distribution of invoice amounts by fund
        
        Returns:
            dict: Query result with fund distribution data
        """
        if not self.connected:
            return {'rows': [], 'columns': []}
        
        return self.db.get_fund_distribution()
    
    def get_recent_invoices(self, limit=10):
        """Get recent invoices
        
        Args:
            limit: Maximum number of invoices to return
            
        Returns:
            dict: Query result with recent invoice data
        """
        if not self.connected:
            return {'rows': [], 'columns': []}
        
        return self.db.get_recent_invoices(limit)
    
    def rename_table_to_snake_case(self, original_table_name: str) -> bool:
        """Rename a table with spaces or special characters to snake_case format
        
        Args:
            original_table_name: The current table name
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.connected:
            logger.error("Not connected to database")
            return False
            
        try:
            # Create a snake_case version of the table name
            # Replace spaces with underscores
            snake_name = original_table_name.replace(' ', '_')
            # Replace any special characters with underscores
            snake_name = re.sub(r'[^a-zA-Z0-9_]', '_', snake_name)
            # Convert to lowercase
            snake_name = snake_name.lower()
            
            logger.info(f"Renaming table '{original_table_name}' to '{snake_name}'")
            
            # Use safe quoting for both table names
            quoted_original = self.quote_identifier(original_table_name)
            
            # Execute the rename
            query = f"ALTER TABLE {quoted_original} RENAME TO {snake_name}"
            result = self.db.execute_query(query)
            
            if "error" in result and result["error"]:
                logger.error(f"Error renaming table: {result['error']}")
                return False
                
            # Update the tables list after successful rename
            self._fetch_tables()
            
            return True
        except Exception as e:
            logger.error(f"Exception in rename_table_to_snake_case: {str(e)}")
            return False
    
    def rename_tables_with_spaces(self) -> Dict[str, str]:
        """Find and rename all tables with spaces to snake_case format
        
        Returns:
            Dict: Mapping of original table names to new snake_case names
        """
        if not self.connected:
            logger.error("Not connected to database")
            return {}
            
        try:
            # Get all tables
            self._fetch_tables()
            
            # Find tables with spaces
            tables_with_spaces = [t for t in self.tables if ' ' in t]
            
            if not tables_with_spaces:
                logger.info("No tables with spaces found")
                return {}
                
            # Keep track of renamed tables
            renamed_map = {}
            
            # Rename each table
            for table in tables_with_spaces:
                # Create a snake_case version of the table name
                # Replace spaces with underscores
                snake_name = table.replace(' ', '_')
                # Replace any special characters with underscores
                snake_name = re.sub(r'[^a-zA-Z0-9_]', '_', snake_name)
                # Convert to lowercase
                snake_name = snake_name.lower()
                
                logger.info(f"Renaming table '{table}' to '{snake_name}'")
                
                # Use safe quoting for the original table name
                quoted_original = self.quote_identifier(table)
                
                # Execute the rename
                query = f"ALTER TABLE {quoted_original} RENAME TO {snake_name}"
                result = self.db.execute_query(query)
                
                if "error" in result and result["error"]:
                    logger.error(f"Error renaming table '{table}': {result['error']}")
                    continue
                    
                # Add to the mapping
                renamed_map[table] = snake_name
                
            # Update the tables list after all renames
            self._fetch_tables()
            
            return renamed_map
            
        except Exception as e:
            logger.error(f"Exception in rename_tables_with_spaces: {str(e)}")
            return {}
    
    def connect(self, db_name: str, host: str = "localhost", 
                 port: int = 5432, user: str = "postgres", 
                 password: str = None) -> bool:
        """Deprecated connect method (for backward compatibility)
        
        Args:
            db_name: Name of the database
            host: Database host
            port: Database port
            user: Username
            password: Password
            
        Returns:
            bool: True if successful, False otherwise
        """
        success, _ = self.connect_to_database(db_name, host, port, user, password)
        return success
    
    @property
    def is_connected(self):
        """Check if the database is connected
        
        Returns:
            bool: True if connected, False otherwise
        """
        return self.connected
    
    def is_connected(self):
        """Check if the database is connected (method form)
        
        Returns:
            bool: True if connected, False otherwise
        """
        return self.connected
    
    def quote_identifier(self, identifier):
        """Quote an identifier (table name, column name) safely for PostgreSQL
        
        Args:
            identifier: The identifier to quote
            
        Returns:
            str: The safely quoted identifier
        """
        if not self.db:
            return f'"{identifier}"'
            
        # Use the database's quoting function if available
        if hasattr(self.db, 'safe_quote_identifier'):
            return self.db.safe_quote_identifier(identifier)
        
        # Basic fallback quoting
        return f'"{identifier}"'

    def import_csv_with_smart_mapping(self, csv_file, table_name):
        """Import CSV with intelligent schema adaptation
        
        Args:
            csv_file: Path to the CSV file
            table_name: Target table name
            
        Returns:
            dict: Import results
        """
        try:
            # Step 1: Read CSV headers and sample data
            with open(csv_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                csv_headers = next(reader)
                
                # Get sample rows for type inference
                sample_rows = []
                for _ in range(5):  # Get up to 5 rows
                    try:
                        sample_rows.append(next(reader))
                    except StopIteration:
                        break
                
                # Reset file pointer and count total rows
                f.seek(0)
                next(reader)  # Skip header
                total_rows = sum(1 for _ in reader)
            
            # Step 2: Get existing table structure
            table_structure = self.get_table_structure(table_name)
            existing_columns = [col['name'].lower() for col in table_structure]
            
            # Step 3: Analyze differences
            unknown_columns = []
            column_mapping = {}
            
            for csv_header in csv_headers:
                # Try different variations to find matches
                variations = [
                    csv_header.lower(),                         # exact lowercase match
                    csv_header.lower().replace(' ', '_'),       # spaces to underscores
                    re.sub(r'[^a-z0-9]', '_', csv_header.lower()),  # any non-alphanumeric to underscore
                    ''.join(re.findall(r'[a-z0-9]+', csv_header.lower()))  # remove all non-alphanumeric
                ]
                
                # Find best match
                matched = False
                for var in variations:
                    if var in existing_columns:
                        column_mapping[csv_header] = var
                        matched = True
                        break
                
                if not matched:
                    # Check for semantic similarities
                    if 'date' in csv_header.lower():
                        date_cols = [col for col in existing_columns if 'date' in col]
                        if date_cols:
                            # Find most similar date column
                            best_match = max(date_cols, key=lambda x: difflib.SequenceMatcher(None, x, csv_header.lower()).ratio())
                            column_mapping[csv_header] = best_match
                            matched = True
                    elif any(term in csv_header.lower() for term in ['amount', 'payment', 'cost', 'price', 'total']):
                        amount_cols = [col for col in existing_columns 
                                      if any(term in col for term in ['amount', 'payment', 'cost', 'price', 'total'])]
                        if amount_cols:
                            best_match = max(amount_cols, key=lambda x: difflib.SequenceMatcher(None, x, csv_header.lower()).ratio())
                            column_mapping[csv_header] = best_match
                            matched = True
                    elif any(term in csv_header.lower() for term in ['vendor', 'supplier', 'company']):
                        vendor_cols = [col for col in existing_columns 
                                      if any(term in col for term in ['vendor', 'supplier', 'company'])]
                        if vendor_cols:
                            best_match = max(vendor_cols, key=lambda x: difflib.SequenceMatcher(None, x, csv_header.lower()).ratio())
                            column_mapping[csv_header] = best_match
                            matched = True
                
                if not matched:
                    unknown_columns.append(csv_header)
            
            # Step 4: Handle unknown columns
            new_columns = {}
            if unknown_columns:
                logger.info(f"Found {len(unknown_columns)} unknown columns in CSV")
                
                for col in unknown_columns:
                    # Infer type from sample data
                    col_index = csv_headers.index(col)
                    col_data = [row[col_index] for row in sample_rows if col_index < len(row)]
                    col_type = self._infer_column_type(col_data)
                    
                    # Sanitize column name for SQL
                    safe_col_name = re.sub(r'[^a-z0-9_]', '_', col.lower())
                    safe_col_name = re.sub(r'_+', '_', safe_col_name).strip('_')
                    
                    # Store for UI display
                    new_columns[safe_col_name] = col_type
                    
                    # Update mapping
                    column_mapping[col] = safe_col_name
            
            # Return analysis results
            return {
                'csv_headers': csv_headers,
                'existing_columns': existing_columns,
                'mappings': column_mapping,
                'new_columns': new_columns,
                'sample_rows': sample_rows,
                'total_rows': total_rows
            }
            
        except Exception as e:
            logger.error(f"Error analyzing CSV: {str(e)}")
            return {'success': False, 'error': str(e)}

    def _infer_column_type(self, values):
        """Intelligently infer column type from sample values
        
        Args:
            values: List of sample values
            
        Returns:
            str: SQL data type
        """
        # Remove empty values
        values = [v for v in values if v]
        if not values:
            return "VARCHAR(255)"
        
        # Check if all values are dates
        date_patterns = [
            r'^\d{4}-\d{2}-\d{2}$',            # YYYY-MM-DD
            r'^\d{1,2}/\d{1,2}/\d{4}$',         # MM/DD/YYYY
            r'^\d{1,2}/\d{1,2}/\d{2}$',         # MM/DD/YY
            r'^\d{1,2}-\d{1,2}-\d{4}$',         # MM-DD-YYYY
            r'^\d{1,2}-\d{1,2}-\d{2}$'          # MM-DD-YY
        ]
        
        all_dates = True
        for v in values:
            is_date = any(re.match(pattern, v) for pattern in date_patterns)
            if not is_date:
                all_dates = False
                break
        
        if all_dates:
            return "DATE"
        
        # Check if all values are numeric
        all_numeric = True
        has_decimal = False
        for v in values:
            # Remove currency symbols
            test_value = v.replace('$', '').replace('€', '').replace('£', '').replace(',', '')
            try:
                float_val = float(test_value)
                has_decimal = has_decimal or ('.' in test_value)
            except ValueError:
                all_numeric = False
                break
        
        if all_numeric:
            if has_decimal:
                return "DECIMAL(15,2)"
            else:
                return "INTEGER"
        
        # Check text length
        max_length = max(len(v) for v in values)
        if max_length > 255:
            return "TEXT"
        else:
            return f"VARCHAR({min(max_length * 2, 255)})"

    def get_table_structure(self, table_name):
        """Get structure of a table
        
        Args:
            table_name: The name of the table
            
        Returns:
            list: List of column definitions
        """
        query = """
        SELECT column_name, data_type, character_maximum_length, is_nullable
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position
        """
        
        result = self.db.execute_query(query, (table_name,))
        
        if 'error' in result and result['error']:
            logger.error(f"Error getting table structure: {result['error']}")
            return []
        
        columns = []
        for row in result['rows']:
            column_name = row[0]
            data_type = row[1]
            max_length = row[2]
            is_nullable = row[3] == 'YES'
            
            columns.append({
                'name': column_name,
                'type': data_type,
                'max_length': max_length,
                'nullable': is_nullable
            })
        
        return columns

    def add_column_to_table(self, table_name, column_name, column_type):
        """Add a new column to existing table
        
        Args:
            table_name: The name of the table
            column_name: The name of the column to add
            column_type: The data type for the column
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if column already exists
            table_structure = self.get_table_structure(table_name)
            existing_columns = [col['name'].lower() for col in table_structure]
            
            if column_name.lower() in existing_columns:
                return True  # Column already exists
            
            # Add the column
            query = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
            result = self.db.execute_update(query)
            
            if 'error' in result and result['error']:
                logger.error(f"Error adding column: {result['error']}")
                return False
            
            logger.info(f"Added column '{column_name}' with type '{column_type}' to table '{table_name}'")
            return True
            
        except Exception as e:
            logger.error(f"Error adding column: {str(e)}")
            return False

    def _execute_mapped_import(self, csv_file, table_name, column_mapping):
        """Execute the import using column mapping
        
        Args:
            csv_file: Path to the CSV file
            table_name: Target table name
            column_mapping: Dictionary mapping CSV columns to DB columns
            
        Returns:
            dict: Import results
        """
        try:
            total_rows = 0
            successful_rows = 0
            
            # Get column types from database
            table_structure = self.get_table_structure(table_name)
            column_types = {col['name'].lower(): col['type'].lower() for col in table_structure}
            
            # Read CSV data
            with open(csv_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            if not rows:
                return {'success': True, 'message': 'CSV file is empty', 'rows_imported': 0}
            
            # Get target columns for insert
            target_columns = list(set(column_mapping.values()))
            
            # Process in batches
            batch_size = 100
            for i in range(0, len(rows), batch_size):
                batch = rows[i:i+batch_size]
                total_rows += len(batch)
                
                values_list = []
                for row in batch:
                    row_values = []
                    for col in target_columns:
                        # Find original CSV column that maps to this target
                        source_col = None
                        for src, tgt in column_mapping.items():
                            if tgt.lower() == col.lower():
                                source_col = src
                                break
                        
                        if source_col and source_col in row:
                            # Get the value and clean it based on column type
                            value = row[source_col]
                            col_type = column_types.get(col.lower(), 'varchar')
                            cleaned_value = self._clean_value_for_type(value, col_type)
                            row_values.append(cleaned_value)
                        else:
                            row_values.append(None)
                    
                    values_list.append(row_values)
                
                # Build the insert query
                placeholders = ", ".join(["%s"] * len(target_columns))
                columns_str = ", ".join(target_columns)
                
                query = f"INSERT INTO {table_name} ({columns_str}) VALUES "
                query += ", ".join([f"({placeholders})"] * len(batch))
                
                # Flatten values for parameterized query
                flat_values = [val for sublist in values_list for val in sublist]
                
                # Execute insert
                result = self.db.execute_update(query, flat_values)
                
                if 'error' in result and result['error']:
                    logger.error(f"Error inserting batch: {result['error']}")
                    # Fall back to individual inserts to handle problematic rows
                    individual_success = self._insert_rows_individually(table_name, batch, target_columns, column_mapping, column_types)
                    successful_rows += individual_success
                else:
                    successful_rows += len(batch)
            
            # Return result
            return {
                'success': successful_rows > 0,
                'table': table_name,
                'total_rows': total_rows,
                'successful_rows': successful_rows,
                'column_mapping': column_mapping
            }
            
        except Exception as e:
            logger.error(f"Error executing import: {str(e)}")
            return {'success': False, 'error': str(e)}

    def import_csv_to_table(self, csv_file, table_name, options=None):
        """Import CSV to an existing table
        
        Args:
            csv_file: Path to CSV file
            table_name: Name of the target table
            options: Dictionary of import options
            
        Returns:
            dict: Results of the import operation
        """
        if options is None:
            options = {}
        
        try:
            if not self.table_exists(table_name):
                return {'success': False, 'error': f"Table '{table_name}' does not exist"}
            
            # Get table structure to validate columns
            table_structure = self.get_table_structure(table_name)
            table_columns = [col['name'].lower() for col in table_structure]
            
            # Read CSV headers
            delimiter = options.get('delimiter', ',')
            has_header = options.get('has_header', True)
            
            with open(csv_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f, delimiter=delimiter)
                
                if has_header:
                    headers = [h.lower() for h in next(reader)]
                else:
                    # Generate column names if no headers
                    sample_row = next(reader)
                    headers = [f"column{i+1}" for i in range(len(sample_row))]
                    f.seek(0)  # Reset to beginning
                
                # Check if headers match table columns
                unknown_columns = [h for h in headers if h not in table_columns]
                
                # For required columns, check if they're in the CSV
                required_columns = [col['name'].lower() for col in table_structure if not col['nullable']]
                missing_required = [col for col in required_columns if col not in headers]
                
                if missing_required:
                    return {
                        'success': False, 
                        'error': f"CSV file is missing required columns: {', '.join(missing_required)}"
                    }
                
                # Read data
                data = list(reader)
                if not data:
                    return {'success': True, 'message': 'CSV file is empty', 'rows_imported': 0}
                
                # Map CSV columns to table columns
                column_mapping = {}
                for i, header in enumerate(headers):
                    if header in table_columns:
                        column_mapping[i] = header
                
                # Check if we have enough mappings
                if not column_mapping:
                    return {
                        'success': False, 
                        'error': f"No columns in CSV match table columns"
                    }
                
                # Generate SQL for insert
                target_columns = list(column_mapping.values())
                placeholders = ", ".join(["%s"] * len(target_columns))
                
                insert_sql = f"INSERT INTO {table_name} ({', '.join(target_columns)}) VALUES ({placeholders})"
                
                # Process in batches for large files
                batch_size = 100
                rows_imported = 0
                
                for i in range(0, len(data), batch_size):
                    batch = data[i:i+batch_size]
                    batch_values = []
                    
                    for row in batch:
                        # Map values according to column mapping
                        row_values = [row[idx] if idx < len(row) else None for idx in column_mapping.keys()]
                        batch_values.append(row_values)
                    
                    # Flatten values for query parameters
                    flat_values = [val for sublist in batch_values for val in sublist]
                    
                    # Execute batch insert
                    result = self.db.execute_update(insert_sql, flat_values)
                    
                    if 'error' in result and result['error']:
                        return {'success': False, 'error': result['error']}
                    
                    rows_imported += len(batch)
                
                return {
                    'success': True,
                    'rows_imported': rows_imported,
                    'table': table_name
                }
            
        except Exception as e:
            logger.error(f"Error importing CSV to table: {str(e)}")
            return {'success': False, 'error': str(e)}

    def import_csv_to_new_table(self, csv_file, table_name, options=None):
        """Import CSV to a new table
        
        Args:
            csv_file: Path to CSV file
            table_name: Name of the target table to create
            options: Dictionary of import options
            
        Returns:
            dict: Results of the import operation
        """
        if options is None:
            options = {}
        
        try:
            # Check if table already exists
            if self.table_exists(table_name):
                mode = options.get('mode', 'append')
                if mode == 'replace':
                    # Drop existing table
                    result = self.db.execute_update(f"DROP TABLE {table_name}")
                    if 'error' in result and result['error']:
                        return {'success': False, 'error': f"Error dropping existing table: {result['error']}"}
                else:
                    return {'success': False, 'error': f"Table '{table_name}' already exists"}
            
            # Read CSV headers and sample data
            delimiter = options.get('delimiter', ',')
            has_header = options.get('has_header', True)
            
            with open(csv_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f, delimiter=delimiter)
                
                if has_header:
                    # Use headers from CSV
                    headers = next(reader)
                    
                    # Clean header names for SQL
                    clean_headers = []
                    for header in headers:
                        # Replace spaces and special chars with underscores
                        clean_name = re.sub(r'[^a-zA-Z0-9]', '_', header)
                        # Ensure it starts with a letter
                        if not clean_name[0].isalpha():
                            clean_name = 'col_' + clean_name
                        # Lowercase for consistency
                        clean_name = clean_name.lower()
                        clean_headers.append(clean_name)
                else:
                    # Generate column names
                    sample_row = next(reader)
                    clean_headers = [f"column{i+1}" for i in range(len(sample_row))]
                    f.seek(0)  # Reset to beginning
                
                # Read sample rows for type inference
                sample_rows = []
                for _ in range(5):  # Get up to 5 rows
                    try:
                        sample_rows.append(next(reader))
                    except StopIteration:
                        break
                
                # Reset file pointer
                f.seek(0)
                if has_header:
                    next(reader)  # Skip header again
                
                # Infer column types
                column_types = []
                for i, header in enumerate(clean_headers):
                    # Get sample data for this column
                    column_data = [row[i] if i < len(row) else "" for row in sample_rows]
                    column_types.append(self._infer_column_type(column_data))
                
                # Create table
                create_columns = []
                for i, (header, data_type) in enumerate(zip(clean_headers, column_types)):
                    create_columns.append(f"{header} {data_type}")
                
                create_sql = f"CREATE TABLE {table_name} (\n"
                create_sql += ",\n".join(create_columns)
                create_sql += "\n)"
                
                result = self.db.execute_update(create_sql)
                if 'error' in result and result['error']:
                    return {'success': False, 'error': f"Error creating table: {result['error']}"}
                
                # Import data
                all_data = list(reader)
                if not all_data:
                    return {'success': True, 'message': 'Created table but CSV file has no data', 'rows_imported': 0}
                
                # Generate SQL for insert
                placeholders = ", ".join(["%s"] * len(clean_headers))
                
                insert_sql = f"INSERT INTO {table_name} ({', '.join(clean_headers)}) VALUES ({placeholders})"
                
                # Process in batches for large files
                batch_size = 100
                rows_imported = 0
                
                for i in range(0, len(all_data), batch_size):
                    batch = all_data[i:i+batch_size]
                    batch_values = []
                    
                    for row in batch:
                        # Pad row if needed
                        padded_row = row + [None] * (len(clean_headers) - len(row))
                        batch_values.append(padded_row[:len(clean_headers)])
                    
                    # Flatten values for query parameters
                    flat_values = [val for sublist in batch_values for val in sublist]
                    
                    # Execute batch insert
                    result = self.db.execute_update(insert_sql, flat_values)
                    
                    if 'error' in result and result['error']:
                        return {'success': False, 'error': result['error']}
                    
                    rows_imported += len(batch)
                
                return {
                    'success': True,
                    'rows_imported': rows_imported,
                    'table': table_name,
                    'columns': list(zip(clean_headers, column_types))
                }
            
        except Exception as e:
            logger.error(f"Error importing CSV to new table: {str(e)}")
            return {'success': False, 'error': str(e)}

    def table_exists(self, table_name):
        """Check if a table exists in the database
        
        Args:
            table_name: The name of the table to check
            
        Returns:
            bool: True if the table exists, False otherwise
        """
        # Make sure we have an up-to-date list of tables
        self._fetch_tables()
        return table_name.lower() in [t.lower() for t in self.tables]

    def get_table_expected_columns(self, table_name):
        """Get expected columns for a table
        
        Args:
            table_name: The table name
            
        Returns:
            list: List of expected column definitions
        """
        # Check if we have schema validator with expected schemas
        if hasattr(self, 'schema_validator') and hasattr(self.schema_validator, 'expected_schemas'):
            # Use schema validator's expected schemas
            if table_name.lower() in self.schema_validator.expected_schemas:
                schema = self.schema_validator.expected_schemas[table_name.lower()]
                
                # Convert to list of column definitions
                columns = []
                
                # Add required columns
                for col_name, col_type in schema['required_columns'].items():
                    columns.append({
                        'name': col_name,
                        'type': col_type,
                        'required': True
                    })
                
                # Add optional columns
                for col_name, col_type in schema.get('optional_columns', {}).items():
                    columns.append({
                        'name': col_name,
                        'type': col_type,
                        'required': False
                    })
                
                return columns
        
        # Fallback: Get columns from database if table exists
        if self.table_exists(table_name):
            columns_query = """
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = %s
            ORDER BY ordinal_position
            """
            
            result = self.db.execute_query(columns_query, (table_name,))
            
            if 'error' not in result and result['rows']:
                columns = []
                
                for row in result['rows']:
                    col_name = row[0]
                    data_type = row[1]
                    is_nullable = row[2] == 'YES'
                    
                    columns.append({
                        'name': col_name,
                        'type': data_type,
                        'required': not is_nullable
                    })
                
                return columns
        
        # Return empty list if no information available
        return [] 

    def _clean_value_for_type(self, value, column_type):
        """Clean a value based on the target column type
        
        Args:
            value: The value to clean
            column_type: The target column's data type
            
        Returns:
            The cleaned value appropriate for the column type
        """
        if value is None or value == '':
            return None
        
        # Handle numeric types
        if any(num_type in column_type for num_type in ['numeric', 'decimal', 'double', 'float', 'real']):
            # Remove any formatting characters like commas and currency symbols
            if isinstance(value, str):
                cleaned = re.sub(r'[^0-9.\-]', '', value)
                if not cleaned:
                    return None
                try:
                    return float(cleaned)
                except ValueError:
                    return None
            elif isinstance(value, (int, float)):
                return value
            return None
            
        # Handle integer types
        if any(int_type in column_type for int_type in ['int', 'serial', 'bigint', 'smallint']):
            # Remove any formatting characters
            if isinstance(value, str):
                cleaned = re.sub(r'[^0-9\-]', '', value)
                if not cleaned:
                    return None
                try:
                    return int(cleaned)
                except ValueError:
                    return None
            elif isinstance(value, int):
                return value
            elif isinstance(value, float):
                return int(value)
            return None
            
        # Handle date types
        if 'date' in column_type:
            if isinstance(value, str):
                # Try different date formats
                date_formats = ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%m-%d-%Y']
                for fmt in date_formats:
                    try:
                        from datetime import datetime
                        date_obj = datetime.strptime(value, fmt)
                        return date_obj.strftime('%Y-%m-%d')  # Format consistently for SQL
                    except ValueError:
                        continue
        
            # If we can't parse the date, return NULL
            return None
        
        # For other types, return as is
        return value 

    def _insert_rows_individually(self, table_name, rows, target_columns, column_mapping, column_types):
        """Insert rows one by one to isolate and handle problematic rows
        
        Args:
            table_name: Target table name
            rows: List of row dictionaries from CSV
            target_columns: List of target database columns
            column_mapping: Dictionary mapping CSV columns to DB columns
            column_types: Dictionary of column types
            
        Returns:
            int: Number of successfully inserted rows
        """
        successful = 0
        
        for row in rows:
            try:
                row_values = []
                for col in target_columns:
                    # Find original CSV column that maps to this target
                    source_col = None
                    for src, tgt in column_mapping.items():
                        if tgt.lower() == col.lower():
                            source_col = src
                            break
                    
                    if source_col and source_col in row:
                        # Get the value and clean it based on column type
                        value = row[source_col]
                        col_type = column_types.get(col.lower(), 'varchar')
                        cleaned_value = self._clean_value_for_type(value, col_type)
                        row_values.append(cleaned_value)
                    else:
                        row_values.append(None)
                
                # Build query for a single row
                placeholders = ", ".join(["%s"] * len(target_columns))
                columns_str = ", ".join(target_columns)
                
                query = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"
                
                # Execute query
                result = self.db.execute_update(query, row_values)
                
                if not ('error' in result and result['error']):
                    successful += 1
                else:
                    # Log the problematic row data (safely)
                    safe_row = {}
                    for src, tgt in column_mapping.items():
                        if src in row:
                            value = row[src]
                            if isinstance(value, str) and len(value) > 50:
                                safe_row[tgt] = value[:50] + "..."
                            else:
                                safe_row[tgt] = str(value)
                    
                    logger.warning(f"Could not import row: {safe_row}")
                    logger.warning(f"Error: {result.get('error', 'Unknown error')}")
            except Exception as e:
                logger.warning(f"Error importing individual row: {str(e)}")
        
        logger.info(f"Individually inserted {successful} out of {len(rows)} rows")
        return successful 

    def _execute_mapped_import_with_progress(self, csv_file, table_name, column_mapping, progress_callback=None):
        """Execute import with progress reporting
        
        Args:
            csv_file: Path to the CSV file
            table_name: Target table name
            column_mapping: Dictionary mapping CSV columns to DB columns
            progress_callback: Function to call with progress updates
            
        Returns:
            dict: Import results
        """
        try:
            total_rows = 0
            successful_rows = 0
            
            # Get column types from database
            table_structure = self.get_table_structure(table_name)
            column_types = {col['name'].lower(): col['type'].lower() for col in table_structure}
            
            # Read CSV data
            with open(csv_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                row_count = 0
                
                # Process in batches
                batch_size = 50
                current_batch = []
                
                for row in reader:
                    row_count += 1
                    total_rows += 1
                    
                    # Add to current batch
                    current_batch.append(row)
                    
                    # Update progress if callback provided
                    if progress_callback:
                        progress_callback(row_count)
                    
                    # Process batch when it reaches batch size
                    if len(current_batch) >= batch_size:
                        # Process batch
                        batch_success = self._process_import_batch(table_name, current_batch, column_mapping, column_types)
                        successful_rows += batch_success
                        current_batch = []
                
                # Process any remaining rows
                if current_batch:
                    batch_success = self._process_import_batch(table_name, current_batch, column_mapping, column_types)
                    successful_rows += batch_success
            
            # Return result
            return {
                'success': True,
                'table': table_name,
                'total_rows': total_rows,
                'successful_rows': successful_rows,
                'column_mapping': column_mapping
            }
            
        except Exception as e:
            logger.error(f"Error executing import with progress: {str(e)}")
            return {'success': False, 'error': str(e)}

    def _process_import_batch(self, table_name, rows, column_mapping, column_types):
        """Process a batch of rows for import
        
        Args:
            table_name: Target table name
            rows: List of row dictionaries from CSV
            column_mapping: Dictionary mapping CSV columns to DB columns
            column_types: Dictionary of column types
            
        Returns:
            int: Number of successfully inserted rows
        """
        if not rows:
            return 0
        
        try:
            # Get target columns
            target_columns = list(set(column_mapping.values()))
            
            # Prepare values
            values_list = []
            for row in rows:
                row_values = []
                for col in target_columns:
                    # Find original CSV column that maps to this target
                    source_col = None
                    for src, tgt in column_mapping.items():
                        if tgt.lower() == col.lower():
                            source_col = src
                            break
                    
                    if source_col and source_col in row:
                        # Get the value and clean it based on column type
                        value = row[source_col]
                        col_type = column_types.get(col.lower(), 'varchar')
                        cleaned_value = self._clean_value_for_type(value, col_type)
                        row_values.append(cleaned_value)
                    else:
                        row_values.append(None)
                
                values_list.append(row_values)
            
            # Build the insert query
            placeholders = ", ".join(["%s"] * len(target_columns))
            columns_str = ", ".join(target_columns)
            
            query = f"INSERT INTO {table_name} ({columns_str}) VALUES "
            query += ", ".join([f"({placeholders})"] * len(rows))
            
            # Flatten values for parameterized query
            flat_values = [val for sublist in values_list for val in sublist]
            
            # Execute insert
            result = self.db.execute_update(query, flat_values)
            
            if 'error' in result and result['error']:
                logger.error(f"Error inserting batch: {result['error']}")
                # Fall back to individual inserts
                return self._insert_rows_individually(table_name, rows, target_columns, column_mapping, column_types)
            
            return len(rows)
            
        except Exception as e:
            logger.error(f"Error processing import batch: {str(e)}")
            # Try individual rows as fallback
            return self._insert_rows_individually(table_name, rows, target_columns, column_mapping, column_types) 