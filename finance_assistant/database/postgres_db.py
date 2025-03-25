#!/usr/bin/env python3
"""
PostgreSQL Database Connection Module

Provides a simplified interface for connecting to and querying PostgreSQL databases.
"""

import logging
import os
import psycopg2
import psycopg2.extras
import pandas as pd
from typing import Dict, List, Any, Tuple, Union, Optional

# Configure logging
logger = logging.getLogger(__name__)

class PostgresDatabase:
    """PostgreSQL database connection and query handling"""
    
    def __init__(self):
        """Initialize the PostgreSQL database connection"""
        self.connection = None
        self.cursor = None
        self.connected = False
        self.db_name = None
        self.host = None
        self.port = None
        self.user = None
        self.error = None
        
    def connect(self, db_name: str, host: str = "localhost", port: int = 5432, 
                user: str = "postgres", password: str = None) -> bool:
        """Connect to a PostgreSQL database
        
        Args:
            db_name: Name of the database
            host: Host address
            port: Port number
            user: Username
            password: Password
            
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # Create connection string
            conn_params = {
                "dbname": db_name,
                "user": user,
                "host": host,
                "port": port
            }
            
            # Add password if provided
            if password:
                conn_params["password"] = password
                
            # Connect to database
            self.connection = psycopg2.connect(**conn_params)
            self.cursor = self.connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
            self.connected = True
            self.db_name = db_name
            self.host = host
            self.port = port
            self.user = user
            
            logger.info(f"Connected to PostgreSQL database: {db_name} on {host}:{port}")
            return True
            
        except psycopg2.OperationalError as e:
            err_msg = str(e)
            if "does not exist" in err_msg:
                self.error = f"Database '{db_name}' does not exist. Please create it first."
            elif "Connection refused" in err_msg:
                self.error = f"Connection refused. Is PostgreSQL running on {host}:{port}?"
            elif "authentication failed" in err_msg:
                self.error = "Authentication failed. Check your username and password."
            else:
                self.error = f"Connection error: {err_msg}"
            
            logger.error(f"PostgreSQL connection error: {err_msg}")
            self.connected = False
            return False
            
        except Exception as e:
            self.error = str(e)
            logger.error(f"Error connecting to PostgreSQL database: {str(e)}")
            self.connected = False
            return False
    
    def execute_query(self, query: str, params=None) -> Dict[str, Any]:
        """Execute a SQL query
        
        Args:
            query: The SQL query to execute
            params: Optional parameters for the query
            
        Returns:
            Dict: Query results
        """
        try:
            cur = self.connection.cursor()
            
            try:
                # Execute the query with parameters if provided
                if params is not None:
                    # Ensure params is properly formatted
                    if isinstance(params, tuple):
                        cur.execute(query, params)
                    elif isinstance(params, list):
                        cur.execute(query, params)
                    else:
                        cur.execute(query, (params,))
                else:
                    cur.execute(query)
                
                # Check if this is a SELECT query
                is_select = query.strip().upper().startswith("SELECT")
                
                if is_select:
                    # Get column names
                    columns = [desc[0] for desc in cur.description] if cur.description else []
                    
                    # Get rows
                    rows = cur.fetchall()
                    
                    return {'columns': columns, 'rows': rows}
                else:
                    # Non-SELECT query (INSERT, UPDATE, DELETE, etc.)
                    rowcount = cur.rowcount
                    self.connection.commit()
                    
                    return {'rowcount': rowcount}
                    
            except Exception as e:
                self.connection.rollback()
                self.error = str(e)
                return {'error': str(e)}
                
            finally:
                cur.close()
                
        except Exception as e:
            self.error = str(e)
            return {'error': str(e)}
    
    def execute_update(self, query: str, params=None) -> Dict[str, Any]:
        """Execute a SQL update query (INSERT, UPDATE, DELETE, ALTER, etc.)
        
        This method is specifically for queries that modify the database.
        
        Args:
            query: The SQL query to execute
            params: Optional parameters for the query
            
        Returns:
            Dict: Result with rowcount or error
        """
        try:
            cur = self.connection.cursor()
            
            try:
                # Execute the query with parameters if provided
                if params is not None:
                    # Ensure params is properly formatted
                    if isinstance(params, tuple):
                        cur.execute(query, params)
                    elif isinstance(params, list):
                        cur.execute(query, params)
                    else:
                        cur.execute(query, (params,))
                else:
                    cur.execute(query)
                
                # Commit the changes
                self.connection.commit()
                
                # Return the rowcount (number of affected rows)
                return {'rowcount': cur.rowcount}
                
            except Exception as e:
                self.connection.rollback()
                self.error = str(e)
                return {'error': str(e)}
                
            finally:
                cur.close()
                
        except Exception as e:
            self.error = str(e)
            return {'error': str(e)}
    
    def safe_quote_identifier(self, identifier: str) -> str:
        """Safely quote a table name or column name for PostgreSQL
        
        This handles table names with spaces, special characters, or reserved keywords.
        
        Args:
            identifier: The table or column name to quote
            
        Returns:
            str: The properly quoted identifier
        """
        # Replace any double quotes in the identifier with two double quotes
        # then wrap the whole thing in double quotes
        safe_id = identifier.replace('"', '""')
        return f'"{safe_id}"'
    
    def execute_safe_query(self, query: str, table_names: List[str] = None, params: Optional[List[Any]] = None) -> Dict[str, Any]:
        """Execute a query with safe handling of table names with spaces or special characters
        
        Args:
            query: SQL query to execute
            table_names: List of table names that should be properly quoted in the query
            params: Optional parameters for the query
            
        Returns:
            Dict containing query results or error information
        """
        if not self.connected:
            return {"error": "Not connected to database", "rows": [], "columns": []}
        
        try:
            # If table_names is provided, ensure they are properly quoted in the query
            if table_names:
                modified_query = query
                for table_name in table_names:
                    # Only replace whole words (not substrings)
                    # This regex pattern matches the table name as a whole word
                    import re
                    pattern = r'\b' + re.escape(table_name) + r'\b'
                    quoted_name = self.safe_quote_identifier(table_name)
                    modified_query = re.sub(pattern, quoted_name, modified_query)
                
                logger.info(f"Modified query with quoted table names: {modified_query}")
                return self.execute_query(modified_query, params)
            
            # If no table names provided, try the query as is
            result = self.execute_query(query, params)
            
            # If there's an error that looks like a table name issue, try to fix it
            if "error" in result and result["error"]:
                error_msg = result["error"]
                
                # Check for the "relation does not exist" error
                if "relation" in error_msg and "does not exist" in error_msg:
                    import re
                    # Try to extract the table name from error
                    match = re.search(r'relation "(.*?)" does not exist', error_msg)
                    if match:
                        problematic_table = match.group(1)
                        logger.warning(f"Table name issue detected: {problematic_table}")
                        
                        # Check if the table exists with spaces
                        tables_result = self.get_tables()
                        if "tables" in tables_result:
                            # Look for tables that might match if spaces are ignored
                            for actual_table in tables_result["tables"]:
                                if actual_table.lower().replace(" ", "") == problematic_table.lower().replace(" ", ""):
                                    logger.info(f"Found matching table with spaces: {actual_table}")
                                    
                                    # Replace the problematic table name with the properly quoted one
                                    quoted_table = self.safe_quote_identifier(actual_table)
                                    modified_query = query.replace(problematic_table, quoted_table)
                                    
                                    logger.info(f"Retrying with modified query: {modified_query}")
                                    return self.execute_query(modified_query, params)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in execute_safe_query: {str(e)}")
            return {"error": str(e), "rows": [], "columns": []}
    
    def get_tables(self) -> Dict:
        """Get a list of all tables in the database
        
        Returns:
            Dict: Dictionary containing table names or error message
        """
        if not self.connected:
            logger.error("Not connected to database")
            return {"error": "Not connected to database", "tables": []}
            
        try:
            query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
            """
            
            result = self.execute_query(query)
            
            # If there's an error in the result
            if "error" in result and result["error"]:
                logger.error(f"Error getting tables: {result['error']}")
                return {"error": result["error"], "tables": []}
                
            # Check if we got proper rows back
            if "rows" not in result or not result["rows"]:
                logger.info("No tables found in the database")
                return {"tables": []}
                
            # Extract table names
            tables = [row[0] for row in result["rows"]]
            logger.info(f"Found {len(tables)} tables: {tables}")
            return {"tables": tables}
            
        except Exception as e:
            logger.error(f"Exception in get_tables: {str(e)}")
            return {"error": str(e), "tables": []}
    
    def get_columns(self, table_name: str) -> Dict:
        """Get column information for a table
        
        Args:
            table_name: The name of the table
            
        Returns:
            Dict: A dictionary with column information or error information
        """
        query = """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position;
        """
        result = self.execute_query(query, [table_name])
        
        if 'error' in result:
            return {'error': result['error'], 'columns': []}
        
        columns = []
        for row in result['rows']:
            columns.append({
                'name': row[0],
                'type': row[1],
                'nullable': row[2] == 'YES',
                'default': row[3]
            })
            
        return {'columns': columns}
    
    def create_table(self, table_name: str, columns: Dict[str, str]) -> Dict:
        """Create a new table with the specified columns
        
        Args:
            table_name: Name of the table to create
            columns: Dictionary of column names and types
            
        Returns:
            Dict: Result of the operation
        """
        if not self.connected:
            return {'success': False, 'error': 'Not connected to database'}
        
        try:
            # Build the CREATE TABLE query
            query = f"CREATE TABLE IF NOT EXISTS {table_name} (\n"
            
            # Add each column
            col_definitions = []
            for col_name, col_type in columns.items():
                col_definitions.append(f"    {col_name} {col_type}")
            
            # Join the column definitions
            query += ",\n".join(col_definitions)
            
            # Close the query
            query += "\n);"
            
            # Execute the query
            result = self.execute_update(query)
            
            if 'error' in result and result['error']:
                logger.error(f"Error creating table {table_name}: {result['error']}")
                return {
                    'success': False,
                    'error': result['error']
                }
            
            logger.info(f"Successfully created table {table_name}")
            return {
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Exception creating table {table_name}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def query_to_dataframe(self, query: str, params: List = None) -> pd.DataFrame:
        """Execute a query and return results as a pandas DataFrame
        
        Args:
            query: The SQL query to execute
            params: Optional list of parameters for the query
            
        Returns:
            pd.DataFrame: A pandas DataFrame with the query results
        """
        if not self.connected:
            logger.error("Not connected to database")
            return pd.DataFrame()
        
        try:
            return pd.read_sql_query(query, self.connection, params=params)
        except Exception as e:
            logger.error(f"Error executing query to DataFrame: {str(e)}")
            return pd.DataFrame()
    
    def dataframe_to_table(self, df: pd.DataFrame, table_name: str, if_exists: str = 'replace') -> bool:
        """Write a pandas DataFrame to a database table
        
        Args:
            df: The pandas DataFrame to write
            table_name: The name of the target table
            if_exists: What to do if the table exists ('fail', 'replace', or 'append')
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.connected:
            logger.error("Not connected to database")
            return False
        
        try:
            df.to_sql(table_name, self.connection, if_exists=if_exists, index=False)
            return True
        except Exception as e:
            logger.error(f"Error writing DataFrame to table: {str(e)}")
            return False
    
    def close(self):
        """Close the database connection"""
        try:
            if self.cursor:
                self.cursor.close()
            
            if self.connection:
                self.connection.close()
            
            logger.info("Database connection closed")
        except Exception as e:
            logger.error(f"Error closing database connection: {str(e)}")
        finally:
            self.connected = False
            self.cursor = None
            self.connection = None
            
    # Specialized methods for the invoice dashboard
    
    def get_invoice_counts(self) -> Dict:
        """Get counts of invoices by status
        
        Returns:
            Dict: Counts of paid, unpaid, and overdue invoices
        """
        paid_query = "SELECT COUNT(*) FROM invoices WHERE payment_status = 'Paid'"
        unpaid_query = "SELECT COUNT(*) FROM invoices WHERE payment_status = 'Unpaid'"
        overdue_query = "SELECT COUNT(*) FROM invoices WHERE payment_status = 'Unpaid' AND due_date < CURRENT_DATE"
        
        paid_result = self.execute_query(paid_query)
        unpaid_result = self.execute_query(unpaid_query)
        overdue_result = self.execute_query(overdue_query)
        
        paid_count = paid_result['rows'][0][0] if 'rows' in paid_result and paid_result['rows'] else 0
        unpaid_count = unpaid_result['rows'][0][0] if 'rows' in unpaid_result and unpaid_result['rows'] else 0
        overdue_count = overdue_result['rows'][0][0] if 'rows' in overdue_result and overdue_result['rows'] else 0
        
        return {
            'paid': paid_count,
            'unpaid': unpaid_count,
            'overdue': overdue_count
        }
    
    def get_invoice_total(self) -> float:
        """Get the total amount of all invoices
        
        Returns:
            float: Total invoice amount
        """
        query = "SELECT SUM(amount) FROM invoices"
        result = self.execute_query(query)
        
        if 'rows' in result and result['rows'] and result['rows'][0][0]:
            return float(result['rows'][0][0])
        
        return 0.0
    
    def get_impact_distribution(self) -> Dict:
        """Get the distribution of invoices by impact
        
        Returns:
            Dict: Distribution of invoices by impact
        """
        query = "SELECT impact, COUNT(*) FROM invoices GROUP BY impact"
        return self.execute_query(query)
    
    def get_fund_distribution(self) -> Dict:
        """Get the distribution of invoices by fund
        
        Returns:
            Dict: Distribution of invoices by fund
        """
        query = "SELECT fund_paid_by, SUM(amount) FROM invoices GROUP BY fund_paid_by"
        return self.execute_query(query)
    
    def get_recent_invoices(self, limit: int = 10) -> Dict:
        """Get recent invoices
        
        Args:
            limit: Maximum number of invoices to return
            
        Returns:
            Dict: Recent invoices
        """
        query = f"""
        SELECT fund_paid_by, amount, vendor, invoice_number, 
               invoice_date, due_date, 
               CASE 
                   WHEN payment_status = 'Unpaid' AND due_date < CURRENT_DATE 
                   THEN CURRENT_DATE - due_date 
                   ELSE 0 
               END AS days_overdue,
               payment_reference
        FROM invoices 
        ORDER BY invoice_date DESC
        LIMIT {limit}
        """
        return self.execute_query(query)
    
    def create_invoice_tables(self) -> bool:
        """Create the invoice tables if they don't exist
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create invoices table
            invoices_table = """
            CREATE TABLE IF NOT EXISTS invoices (
                id SERIAL PRIMARY KEY,
                invoice_number VARCHAR(50) UNIQUE NOT NULL,
                vendor VARCHAR(100) NOT NULL,
                invoice_date DATE NOT NULL,
                due_date DATE,
                amount DECIMAL(10, 2) NOT NULL,
                payment_status VARCHAR(20) NOT NULL DEFAULT 'Unpaid',
                payment_date DATE,
                payment_reference VARCHAR(50),
                fund_paid_by VARCHAR(100),
                impact VARCHAR(100),
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            
            # Create vendors table
            vendors_table = """
            CREATE TABLE IF NOT EXISTS vendors (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) UNIQUE NOT NULL,
                contact_name VARCHAR(100),
                email VARCHAR(100),
                phone VARCHAR(20),
                address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            
            # Create funds table
            funds_table = """
            CREATE TABLE IF NOT EXISTS funds (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) UNIQUE NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            
            # Execute the create table queries
            self.execute_update(invoices_table)
            self.execute_update(vendors_table)
            self.execute_update(funds_table)
            
            logger.info("Invoice tables created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error creating invoice tables: {str(e)}")
            return False
    
    def insert_sample_data(self) -> bool:
        """Insert sample data into the tables
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if tables already have data
            result = self.execute_query("SELECT COUNT(*) FROM invoices")
            if 'rows' in result and result['rows'] and result['rows'][0][0] > 0:
                logger.info("Sample data already exists")
                return True
            
            # Insert sample funds
            funds = [
                ("General Fund", "General operating fund"),
                ("Capital Projects", "Fund for capital investments"),
                ("Grant Fund", "Fund for grant-related expenses"),
                ("Reserve Fund", "Emergency reserve fund")
            ]
            
            for fund in funds:
                self.execute_update(
                    "INSERT INTO funds (name, description) VALUES (%s, %s)",
                    fund
                )
            
            # Insert sample vendors
            vendors = [
                ("Acme Supplies", "John Doe", "john@acme.com", "555-1234", "123 Main St"),
                ("Tech Solutions", "Jane Smith", "jane@techsolutions.com", "555-5678", "456 Oak Ave"),
                ("Office Depot", "Bob Johnson", "bob@officedepot.com", "555-9012", "789 Pine Blvd"),
                ("Consulting Group", "Alice Brown", "alice@consulting.com", "555-3456", "321 Elm St")
            ]
            
            for vendor in vendors:
                self.execute_update(
                    "INSERT INTO vendors (name, contact_name, email, phone, address) VALUES (%s, %s, %s, %s, %s)",
                    vendor
                )
            
            # Insert sample invoices
            import datetime
            today = datetime.date.today()
            
            invoices = [
                # Paid invoices
                ("INV-001", "Acme Supplies", today - datetime.timedelta(days=30), 
                 today - datetime.timedelta(days=15), 1250.00, "Paid", 
                 today - datetime.timedelta(days=10), "CHK1001", "General Fund", "Operations"),
                
                ("INV-002", "Tech Solutions", today - datetime.timedelta(days=25), 
                 today - datetime.timedelta(days=10), 3750.25, "Paid", 
                 today - datetime.timedelta(days=5), "CHK1002", "Capital Projects", "Technology"),
                
                ("INV-003", "Office Depot", today - datetime.timedelta(days=20), 
                 today - datetime.timedelta(days=5), 527.80, "Paid", 
                 today - datetime.timedelta(days=3), "CHK1003", "General Fund", "Office Supplies"),
                
                # Unpaid invoices
                ("INV-004", "Consulting Group", today - datetime.timedelta(days=15), 
                 today + datetime.timedelta(days=15), 4500.00, "Unpaid", 
                 None, None, "Grant Fund", "Consulting"),
                
                ("INV-005", "Acme Supplies", today - datetime.timedelta(days=10), 
                 today + datetime.timedelta(days=20), 650.75, "Unpaid", 
                 None, None, "General Fund", "Operations"),
                
                # Overdue invoices
                ("INV-006", "Tech Solutions", today - datetime.timedelta(days=45), 
                 today - datetime.timedelta(days=15), 1875.50, "Unpaid", 
                 None, None, "Capital Projects", "Technology"),
                
                ("INV-007", "Office Depot", today - datetime.timedelta(days=40), 
                 today - datetime.timedelta(days=10), 325.99, "Unpaid", 
                 None, None, "General Fund", "Office Supplies")
            ]
            
            for invoice in invoices:
                self.execute_update(
                    """
                    INSERT INTO invoices (
                        invoice_number, vendor, invoice_date, due_date, 
                        amount, payment_status, payment_date, payment_reference, 
                        fund_paid_by, impact
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    invoice
                )
            
            logger.info("Sample data inserted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error inserting sample data: {str(e)}")
            return False
    
    def begin_transaction(self):
        """Begin a database transaction"""
        try:
            # Turn off autocommit to use transactions
            self.connection.autocommit = False
            logger.info("Transaction started")
            return True
        except Exception as e:
            logger.error(f"Error beginning transaction: {str(e)}")
            return False

    def commit_transaction(self):
        """Commit the current transaction"""
        try:
            self.connection.commit()
            # Reset autocommit to default behavior
            self.connection.autocommit = True
            logger.info("Transaction committed")
            return True
        except Exception as e:
            logger.error(f"Error committing transaction: {str(e)}")
            return False

    def rollback_transaction(self):
        """Rollback the current transaction"""
        try:
            self.connection.rollback()
            # Reset autocommit to default behavior
            self.connection.autocommit = True
            logger.info("Transaction rolled back")
            return True
        except Exception as e:
            logger.error(f"Error rolling back transaction: {str(e)}")
            return False 