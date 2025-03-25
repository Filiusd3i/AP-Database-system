import pyodbc
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sqlalchemy import create_engine, text
import logging
import os
import re

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseConnection:
    def __init__(self, db_path):
        self.db_path = db_path
        self.connection = None
        self.cursor = None
        self.connected = False
        self.tables = []
        
    def connect(self):
        """Establish connection to the Access database with enhanced error handling"""
        try:
            # Clean and normalize the path
            clean_path = os.path.normpath(self.db_path)
            logger.info(f"Attempting to connect to: {clean_path}")
            
            # Try multiple connection methods
            self._try_connection_methods(clean_path)
            
            if not self.connected:
                raise Exception("Failed to connect to database after trying all methods")
                
            # Get table list with error handling
            self._get_tables()
            
            # Examine table structure to create safe column lists
            self.examine_table_structure()
            
            return True
            
        except Exception as e:
            logger.error(f"Error in connect_database: {str(e)}")
            if self.connection:
                self.connection.close()
            return False
    
    def _try_connection_methods(self, clean_path):
        """Try multiple connection methods to ensure success"""
        # Method 1: ODBC Driver with special parameters
        if not self.connected:
            try:
                conn_str = (
                    f"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};"
                    f"DBQ={clean_path};"
                    f"NULLTYPE=0;"
                    f"Extended Properties=\"Excel 12.0;IMEX=1;TypeGuessRows=0;ImportMixedTypes=Text\";"
                )
                logger.info(f"Using connection string: {conn_str}")
                
                # Make sure to wrap this in a try/except
                try:
                    self.connection = pyodbc.connect(conn_str)
                    # Set specific ODBC options
                    self.connection.setdecoding(pyodbc.SQL_CHAR, encoding='utf-8')
                    self.connection.setdecoding(pyodbc.SQL_WCHAR, encoding='utf-8')
                    self.connection.setencoding(encoding='utf-8')
                    logger.info("Connection successful using Microsoft Access Driver with NULL handling")
                    self.connected = True
                except pyodbc.Error as e:
                    if "Additional properties not allowed" in str(e):
                        # Try without the extended properties
                        logger.info("Could not set additional properties - continuing")
                        conn_str = (
                            f"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};"
                            f"DBQ={clean_path};"
                            f"NULLTYPE=0;"
                        )
                        self.connection = pyodbc.connect(conn_str)
                        logger.info("Connection successful with fallback connection string")
                        self.connected = True
                    else:
                        raise
            except Exception as e:
                logger.warning(f"Method 1 failed: {str(e)}")

        # Method 2: ACE OLEDB Provider
        if not self.connected:
            try:
                import pypyodbc  # Try alternative ODBC library
                conn_str = (
                    f"Provider=Microsoft.ACE.OLEDB.12.0;"
                    f"Data Source={clean_path};"
                    f"Persist Security Info=False;"
                )
                self.connection = pypyodbc.connect(conn_str)
                logger.info("Connection successful using ACE OLEDB Provider")
                self.connected = True
            except Exception as e:
                logger.warning(f"Method 2 failed: {str(e)}")
        
        # If connected, create cursor
        if self.connected:
            self.cursor = self.connection.cursor()
            
    def _get_tables(self):
        """Get list of tables with enhanced error handling"""
        try:
            logger.info("Starting database analysis with NaN protection...")
            
            # Method 1: Using pyodbc's tables method
            tables = [table_info[2] for table_info in self.cursor.tables(tableType='TABLE') 
                     if not table_info[2].startswith('MSys')]
            
            # Method 2: If that didn't work, try direct SQL
            if not tables:
                self.cursor.execute("SELECT Name FROM MSysObjects WHERE Type=1 AND Flags=0")
                tables = [row[0] for row in self.cursor.fetchall()]
            
            self.tables = tables
            logger.info(f"Found {len(tables)} tables: {tables}")
            
            # Scan for problematic fields to handle later
            self._scan_for_null_fields()
            
            return True
        except Exception as e:
            logger.error(f"Error getting tables: {str(e)}")
            return False

    def _scan_for_null_fields(self):
        """Scan database for NULL fields to help with query construction"""
        self.null_fields = {}
        
        for table in self.tables:
            try:
                # Get columns for this table
                columns = self._get_table_columns(table)
                problematic = []
                
                # Check each column for NULLs
                for column in columns:
                    try:
                        # Use parameterized query to avoid issues with special characters
                        safe_table = self._safe_table_name(table)
                        safe_column = self._safe_column_name(column)
                        
                        query = f"SELECT COUNT(*) FROM {safe_table} WHERE {safe_column} IS NULL"
                        self.cursor.execute(query)
                        null_count = self.cursor.fetchone()[0]
                        
                        if null_count > 0:
                            logger.info(f"Field with NULL values found: {table}.{column} ({null_count} NULLs)")
                            problematic.append(column)
                    except Exception as e:
                        logger.warning(f"Error checking NULL in {table}.{column}: {str(e)}")
                
                if problematic:
                    self.null_fields[table] = problematic
                    logger.info(f"Problematic fields in {table}: {', '.join(problematic)}")
            except Exception as e:
                logger.warning(f"Error scanning table {table}: {str(e)}")
    
    def _get_table_columns(self, table_name):
        """Get column names for a table with error handling"""
        try:
            safe_table = self._safe_table_name(table_name)
            self.cursor.execute(f"SELECT TOP 1 * FROM {safe_table}")
            return [column[0] for column in self.cursor.description]
        except Exception as e:
            logger.warning(f"Error getting columns for {table_name}: {str(e)}")
            return []

    def execute_query(self, query, params=None, enable_fallbacks=True):
        """Execute SQL query with enhanced error handling and NaN protection"""
        if not self.connected:
            logger.error("Cannot execute query - not connected to database")
            return None
            
        try:
            # Check for reserved words in the query
            self._check_and_fix_reserved_words(query)
            
            # Execute the query
            logger.info(f"Executing query: {query}")
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
                
            # Fetch results with NaN protection
            try:
                rows = self.cursor.fetchall()
                # Convert to list of dictionaries with NaN protection
                columns = [column[0] for column in self.cursor.description]
                result = []
                
                for row in rows:
                    row_dict = {}
                    for i, value in enumerate(row):
                        # Handle NaN values cautiously
                        if isinstance(value, float) and np.isnan(value):
                            row_dict[columns[i]] = None
                        else:
                            row_dict[columns[i]] = value
                    result.append(row_dict)
                    
                return result
            except pyodbc.ProgrammingError:
                # No results to fetch (e.g., for INSERT/UPDATE)
                self.connection.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error executing query: {str(e)}")
            logger.error(f"Problematic SQL: {query}")
            
            # Special handling for the "Check" column issue
            if "Check" in query and enable_fallbacks:
                return self._handle_check_column_error(query)
                
            # Try to recover with alternative query
            if enable_fallbacks and self._should_try_fallback(query, str(e)):
                return self._execute_fallback_query(query)
                
            return None
    
    def _handle_check_column_error(self, query):
        """Special handling for the Check column issues"""
        logger.info("Rewriting Check column query: " + query)
        
        # Try with square brackets
        try:
            new_query = query.replace("Check ", "[Check] ")
            logger.info("Executing query: " + new_query)
            self.cursor.execute(new_query)
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Error executing query: {str(e)}")
            logger.error(f"Problematic SQL: {new_query}")
        
        # Try with Len function
        try:
            if "IS NOT NULL" in query:
                new_query = query.replace("[Check] IS NOT NULL", "Len([Check]) IS NOT NULL")
                logger.info("Retrying with Length function: " + new_query)
                self.cursor.execute(new_query)
                return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Error executing query: {str(e)}")
            logger.error(f"Problematic SQL: {new_query}")
        
        # Try with <> comparison
        try:
            new_query = query.replace("[Check] IS NOT NULL", "Check <> ''")
            logger.error(f"Problematic SQL: {new_query}")
            # Don't actually execute - just log for diagnosis
        except Exception as e:
            pass
            
        # If all attempts fail, return empty result
        return []

    def _should_try_fallback(self, query, error_msg):
        """Determine if we should try a fallback query"""
        # Check for common error patterns
        if "NaN" in error_msg or "convert float" in error_msg:
            return True
        if "Too few parameters" in error_msg:
            return True
        if "syntax error" in error_msg:
            return True
        return False
        
    def _execute_fallback_query(self, query):
        """Try alternative query approaches"""
        logger.info("Attempting fallback query...")
        
        # Try casting problematic columns to text
        modified_query = self._convert_numeric_to_text(query)
        if modified_query != query:
            try:
                logger.info(f"Fallback query: {modified_query}")
                self.cursor.execute(modified_query)
                return self.cursor.fetchall()
            except Exception as e:
                logger.error(f"Fallback query failed: {str(e)}")
        
        # Try selecting just a few columns
        if "SELECT *" in query:
            table_match = re.search(r"FROM\s+(\w+)", query)
            if table_match:
                table = table_match.group(1)
                try:
                    safe_query = f"SELECT TOP 5 * FROM {table}"
                    logger.info(f"Safe fallback query: {safe_query}")
                    self.cursor.execute(safe_query)
                    columns = [column[0] for column in self.cursor.description]
                    
                    # Create a new query with explicit column names
                    column_list = ", ".join([self._safe_column_name(col) for col in columns 
                                          if col.lower() not in ('check')])
                    new_query = query.replace("SELECT *", f"SELECT {column_list}")
                    
                    logger.info(f"Restructured query: {new_query}")
                    self.cursor.execute(new_query)
                    return self.cursor.fetchall()
                except Exception as e:
                    logger.error(f"Structured fallback query failed: {str(e)}")
        
        return None
        
    def _convert_numeric_to_text(self, query):
        """Convert numeric comparisons to text to avoid NaN issues"""
        # Pattern for numeric comparisons
        pattern = r'(\w+)\s*(=|>|<|>=|<=|<>)\s*(\d+\.?\d*)'
        
        def replace_with_cast(match):
            column, operator, value = match.groups()
            return f"CSTR({column}) {operator} '{value}'"
            
        return re.sub(pattern, replace_with_cast, query)
    
    def _check_and_fix_reserved_words(self, query):
        """Check for reserved words in query and log warnings"""
        reserved_words = ['check', 'date', 'name', 'text', 'value']
        for word in reserved_words:
            if re.search(r'\b' + word + r'\b', query, re.IGNORECASE):
                logger.warning(f"Query contains reserved word '{word}'. This might cause issues.")
                
    def _safe_table_name(self, table_name):
        """Make table name safe for queries"""
        # If table name has spaces or special chars, wrap in brackets
        if re.search(r'[\s\W]', table_name):
            return f"[{table_name}]"
        return table_name
        
    def _safe_column_name(self, column_name):
        """Make column name safe for queries"""
        # If column name has spaces or special chars or is a reserved word, wrap in brackets
        reserved_words = ['check', 'date', 'name', 'text', 'value', 'table', 'group', 'order']
        if (re.search(r'[\s\W]', column_name) or 
            column_name.lower() in reserved_words):
            return f"[{column_name}]"
        return column_name
        
    def close(self):
        """Close the database connection"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        self.connected = False 

    def inspect_invoice_table(self):
        """
        Inspect the Invoices table structure to determine the actual nature of the Check column
        """
        try:
            # First, get all column information
            self.cursor.execute("SELECT TOP 0 * FROM Invoices")
            columns_info = self.cursor.description
            
            # Log all column information to understand their structure
            logger.info("Invoice Table Columns:")
            for idx, col_info in enumerate(columns_info):
                col_name = col_info[0]
                col_type = col_info[1].__name__ if hasattr(col_info[1], '__name__') else str(col_info[1])
                logger.info(f"  Column {idx}: {col_name} - Type: {col_type}")
                
                # Special check for the Check column
                if col_name.lower() == 'check':
                    logger.info(f"  *** Found 'Check' column at position {idx} ***")
                    # Store this information for future use
                    self.check_column_index = idx
                    
            # Create a safe column list excluding the Check column
            column_list = [col_info[0] for col_info in columns_info]
            safe_columns = []
            
            for col in column_list:
                if col.lower() != 'check':
                    safe_columns.append(f"[{col}]")
                else:
                    # Skip the Check column completely
                    logger.info(f"  Excluding 'Check' column from queries")
            
            # Create a safe column list for future queries
            self.safe_invoice_columns = ", ".join(safe_columns)
            logger.info(f"Safe column list created: {self.safe_invoice_columns}")
            
            # Test a query with the safe column list
            test_query = f"SELECT {self.safe_invoice_columns} FROM Invoices WHERE 1=1"
            logger.info(f"Testing query: {test_query}")
            self.cursor.execute(test_query)
            test_result = self.cursor.fetchone()
            logger.info(f"Test query successful, first row retrieved")
            
            return True
            
        except Exception as e:
            logger.error(f"Error inspecting Invoices table: {str(e)}")
            return False 

    def get_invoice_data_safely(self):
        """
        Get invoice data using a safe approach that avoids the Check column
        """
        try:
            # Make sure we've inspected the table first
            if not hasattr(self, 'safe_invoice_columns'):
                self.inspect_invoice_table()
            
            if hasattr(self, 'safe_invoice_columns'):
                # We know which columns are safe to use
                query = f"SELECT {self.safe_invoice_columns} FROM Invoices"
            else:
                # Fall back to manually specifying safe columns
                query = """
                    SELECT [invoice_number], [vendor_name], [fund_id], 
                           [invoice_date], [due_date], [total_amount], 
                           [amount_paid], [Status], [Date of Payment]
                    FROM Invoices
                """
            
            logger.info(f"Executing safe query: {query}")
            self.cursor.execute(query)
            
            columns = [column[0] for column in self.cursor.description]
            results = []
            
            for row in self.cursor.fetchall():
                row_dict = {}
                for i, value in enumerate(row):
                    # Convert any problem values
                    if isinstance(value, float) and np.isnan(value):  # NaN check
                        row_dict[columns[i]] = None
                    else:
                        row_dict[columns[i]] = value
                results.append(row_dict)
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting invoice data safely: {str(e)}")
            return [] 

    def examine_table_structure(self):
        """
        Examine the structure of all tables and create safe column lists
        """
        if not self.connected:
            logger.error("Cannot examine tables - not connected to database")
            return False
        
        try:
            self.safe_columns = {}  # Dictionary to store safe column lists for each table
            
            for table in self.tables:
                logger.info(f"Examining table: {table}")
                
                # Get column information
                safe_table = self._safe_table_name(table)
                self.cursor.execute(f"SELECT TOP 0 * FROM {safe_table}")
                columns = self.cursor.description
                
                # Check each column
                column_list = []
                for idx, col in enumerate(columns):
                    col_name = col[0]
                    col_type = col[1].__name__ if hasattr(col[1], '__name__') else str(col[1])
                    
                    # Check for reserved words
                    if col_name.lower() in ['check', 'date', 'name', 'value', 'table', 'group', 'order']:
                        logger.warning(f"'{col_name}' in {table} is a reserved word")
                        column_list.append(f"[{col_name}]")
                    else:
                        column_list.append(f"[{col_name}]")
                
                # Store the safe column list
                self.safe_columns[table] = ", ".join(column_list)
                
                # Create version that excludes 'Check' column
                if table.lower() == 'invoices':
                    no_check_columns = []
                    for idx, col in enumerate(columns):
                        col_name = col[0]
                        if col_name.lower() != 'check':
                            no_check_columns.append(f"[{col_name}]")
                    
                    self.safe_invoice_columns = ", ".join(no_check_columns)
                    logger.info(f"Created safe column list for Invoices (excluding Check): {self.safe_invoice_columns}")
            
            return True
        except Exception as e:
            logger.error(f"Error examining table structure: {str(e)}")
            return False 

    def execute_invoices_query(self, query_type="all"):
        """
        Execute Invoices queries safely without using the Check column
        """
        if not self.connected:
            logger.error("Cannot execute query - not connected to database")
            return None
        
        try:
            # Make sure we have the safe column list
            if not hasattr(self, 'safe_invoice_columns'):
                self.inspect_invoice_table()
            
            if query_type == "all":
                # Get all invoices
                query = f"SELECT {self.safe_invoice_columns} FROM Invoices"
            elif query_type == "unpaid":
                # Get unpaid invoices
                query = f"SELECT {self.safe_invoice_columns} FROM Invoices WHERE [Status] = 'Unpaid'"
            elif query_type == "count":
                # Get invoice count
                query = "SELECT COUNT(*) FROM Invoices"
            elif query_type == "sum":
                # Get sum of invoice amounts
                query = "SELECT SUM([total_amount]) FROM Invoices"
            else:
                # Custom query - must avoid Check column
                query = query_type.replace("Check", "").replace("*", self.safe_invoice_columns)
            
            logger.info(f"Executing safe Invoices query: {query}")
            self.cursor.execute(query)
            
            if query_type == "count" or query_type == "sum":
                result = self.cursor.fetchone()[0]
                return result
            else:
                columns = [column[0] for column in self.cursor.description]
                results = []
                
                for row in self.cursor.fetchall():
                    row_dict = {}
                    for i, value in enumerate(row):
                        if isinstance(value, float) and np.isnan(value):
                            row_dict[columns[i]] = None
                        else:
                            row_dict[columns[i]] = value
                    results.append(row_dict)
                    
                return results
            
        except Exception as e:
            logger.error(f"Error executing Invoices query: {str(e)}")
            return None 