import os
import pyodbc
import sqlite3
import logging
import math
import warnings
from datetime import datetime

# Add compatibility warning
warnings.warn(
    "Some applications are using deprecated AccessDatabaseFix functionality. "
    "Please update to use the new DatabaseConnection class directly.",
    DeprecationWarning, 
    stacklevel=2
)

logger = logging.getLogger("database.connection")

class DatabaseConnection:
    """Single unified database connection manager with automatic fallbacks"""
    
    def __init__(self, db_path=None, dsn_name=None, use_sqlite=False):
        """
        Initialize database connection manager
        
        Args:
            db_path: Path to Access database file (required unless use_sqlite=True)
            dsn_name: DSN name for ODBC connection (optional)
            use_sqlite: Force using SQLite instead of Access (uses in-memory if db_path=':memory:')
        """
        self.db_path = db_path
        self.dsn_name = dsn_name or os.environ.get("ACCESS_DSN", "MyAccessDB")
        self.use_sqlite = use_sqlite
        self.connection = None
        self._connected = False
        self._tables = []
        self.table_schemas = {}
        
        logger.info("DatabaseConnection initialized")
    
    def connect(self):
        """Connect to database using the most appropriate method"""
        # Close any existing connection
        self.close()
        
        # If SQLite mode is forced or db_path is :memory:, use SQLite
        if self.use_sqlite or self.db_path == ':memory:':
            return self._connect_sqlite()
        
        # If we have a db_path, try Access connection
        if self.db_path:
            logger.info(f"Attempting to connect to Access database: {self.db_path}")
            
            # Try DSN connection first if provided
            if self.dsn_name and self._connect_with_dsn():
                logger.info("Connected using DSN")
                return True
            
            # Try direct connection with primary method
            if self._connect_direct():
                logger.info("Connected using direct method")
                return True
            
            # Try direct connection with alternative methods
            if self._connect_direct_alternative():
                logger.info("Connected using alternative method")
                return True
            
            # If user has specified they want only Access (not SQLite fallback)
            if not self.use_sqlite:
                logger.error("All Access connection methods failed and SQLite fallback is disabled")
                return False
            
            # Fall back to SQLite if Access connection fails
            logger.warning("All Access connection methods failed, falling back to SQLite")
            self.use_sqlite = True
            return self._connect_sqlite()
        
        # No connection possible without db_path and not using in-memory SQLite
        logger.error("Cannot connect: No database path provided")
        return False
    
    def _connect_with_dsn(self):
        """Connect using DSN"""
        try:
            logger.info(f"Connecting to Access database using DSN: {self.dsn_name}")
            conn_str = f"DSN={self.dsn_name}"
            self.connection = pyodbc.connect(conn_str)
            self._connected = True
            self._analyze_schema()
            return True
        except Exception as e:
            logger.error(f"DSN connection failed: {str(e)}")
            return False
    
    def _connect_direct(self):
        """Connect directly to Access file with better error handling"""
        try:
            # Ensure we have the full path to the database file
            full_path = os.path.abspath(self.db_path)
            
            # Check if the file exists
            if not os.path.exists(full_path):
                logger.error(f"Database file does not exist at {full_path}")
                return False
            
            # Use the direct connection string with the Access Database Engine
            conn_str = f"Driver={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={full_path};"
            logger.info(f"Attempting direct connection with: {conn_str}")
            
            # Connect using pyodbc
            self.connection = pyodbc.connect(conn_str)
            logger.info(f"Successfully connected to {os.path.basename(full_path)}")
            
            self._connected = True
            self._analyze_schema()
            return True
            
        except Exception as e:
            error_msg = str(e).lower()
            logger.error(f"Direct connection failed: {str(e)}")
            
            # Provide specific guidance based on the error
            if "not a valid file name" in error_msg:
                logger.error(f"The database file path may be incorrect or inaccessible: {self.db_path}")
            elif "registry key" in error_msg:
                logger.error("Registry permission issue detected. Try running as administrator or restart after installation.")
            elif "password" in error_msg:
                logger.error("This database may be password protected. Include password in connection string.")
            
            return False
    
    def _connect_direct_alternative(self):
        """Try alternative connection strings for Access"""
        try:
            # Ensure we have the full path to the database file
            full_path = os.path.abspath(self.db_path)
            directory = os.path.dirname(full_path)
            
            # Try alternative connection strings
            conn_strings = [
                # With DefaultDir parameter
                f"Driver={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={full_path};DefaultDir={directory};",
                
                # Using OLEDB provider
                f"Provider=Microsoft.ACE.OLEDB.12.0;Data Source={full_path};",
                
                # Extended parameters
                f"Driver={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={full_path};ExtendedAnsiSQL=1;"
            ]
            
            for i, conn_str in enumerate(conn_strings):
                try:
                    logger.info(f"Trying alternative connection string #{i+1}")
                    self.connection = pyodbc.connect(conn_str)
                    logger.info(f"Alternative connection method #{i+1} successful")
                    
                    self._connected = True
                    self._analyze_schema()
                    return True
                except Exception as e:
                    logger.error(f"Alternative connection method #{i+1} failed: {str(e)}")
            
            return False
            
        except Exception as e:
            logger.error(f"All alternative connection methods failed: {str(e)}")
            return False
    
    def _connect_sqlite(self):
        """Connect using SQLite (file or in-memory)"""
        try:
            if self.db_path == ':memory:' or not self.db_path:
                logger.info("Connecting to in-memory SQLite database")
                self.connection = sqlite3.connect(':memory:')
            else:
                # Use file-based SQLite with the same path but .sqlite extension
                sqlite_path = os.path.splitext(self.db_path)[0] + '.sqlite'
                logger.info(f"Connecting to SQLite database: {sqlite_path}")
                self.connection = sqlite3.connect(sqlite_path)
                
            # Enable dictionary access for rows
            self.connection.row_factory = sqlite3.Row
            
            self._connected = True
            self._analyze_schema()
            return True
        except Exception as e:
            logger.error(f"SQLite connection failed: {str(e)}")
            self._connected = False
            return False
    
    def _analyze_schema(self):
        """Analyze database schema and detect tables"""
        try:
            if not self._connected:
                return
                
            self._tables = []
            self.table_schemas = {}
            
            # Get list of tables
            if self.use_sqlite:
                # SQLite approach
                cursor = self.connection.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                self._tables = [row[0] for row in cursor.fetchall()]
            else:
                # Access approach
                cursor = self.connection.cursor()
                for table_info in cursor.tables(tableType='TABLE'):
                    if table_info.table_name.startswith('MSys'):
                        continue  # Skip system tables
                    self._tables.append(table_info.table_name)
            
            # Get column info for each table
            for table in self._tables:
                self.table_schemas[table] = {
                    'columns': [],
                    'column_types': {},
                    'problem_columns': []
                }
                
                if self.use_sqlite:
                    # SQLite approach
                    cursor = self.connection.cursor()
                    cursor.execute(f"PRAGMA table_info({table})")
                    for col_info in cursor.fetchall():
                        col_name = col_info[1]
                        col_type = col_info[2]
                        self.table_schemas[table]['columns'].append(col_name)
                        self.table_schemas[table]['column_types'][col_name] = col_type
                else:
                    # Access approach
                    cursor = self.connection.cursor()
                    try:
                        columns = cursor.columns(table=table)
                        for column in columns:
                            col_name = column.column_name
                            col_type = column.type_name
                            self.table_schemas[table]['columns'].append(col_name)
                            self.table_schemas[table]['column_types'][col_name] = col_type
                            
                            # Detect potentially problematic columns
                            if col_name in ['Check', 'Order', 'Date', 'Group', 'Key'] or \
                               col_name.lower() in ['check', 'order', 'date', 'group', 'key']:
                                self.table_schemas[table]['problem_columns'].append(col_name)
                    except Exception as e:
                        logger.error(f"Error getting columns for table {table}: {str(e)}")
            
            logger.info(f"Schema analysis complete: Found {len(self._tables)} tables")
        except Exception as e:
            logger.error(f"Error analyzing schema: {str(e)}")
    
    def execute_query(self, query, params=None):
        """Execute a query and return results as a dictionary"""
        try:
            if not self._connected:
                logger.error("Cannot execute query: Not connected to database")
                return {'error': 'Not connected to database'}
            
            cursor = self.connection.cursor()
            
            # Handle Access reserved words - many Access queries fail with these without parameters
            # If certain patterns are detected in the query, add appropriate parameters
            access_reserved_words = ['check', 'order', 'date', 'group', 'key', 'amount']
            
            if not self.use_sqlite:
                # Fix problematic Access queries by providing actual parameters instead of bracketed names
                if 'Check' in query or '[Check]' in query:
                    # Replace the query with a parameterized version
                    if '[Check] <> \'\'' in query:
                        query = query.replace('[Check] <> \'\'', '[Check] <> ?')
                        params = [''] if params is None else params + ['']
                    elif '[Check] = \'\'' in query:
                        query = query.replace('[Check] = \'\'', '[Check] = ?')
                        params = [''] if params is None else params + ['']
                
                # Handle QZ columns (appears to need parameters)
                for yr in ['2019', '2020', '2022', '2024']:
                    pattern = f'[QZ {yr}] <> \'\''
                    if pattern in query:
                        query = query.replace(pattern, '[QZ ' + yr + '] <> ?')
                        params = [''] if params is None else params + ['']
            
            # Execute the query
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # For SELECT queries, return the results
            if query.strip().upper().startswith('SELECT'):
                rows = cursor.fetchall()
                
                # Get column names from cursor description
                if cursor.description:
                    columns = [column[0] for column in cursor.description]
                else:
                    columns = []
                
                # Convert to list of dicts for consistent return format
                if self.use_sqlite:
                    # SQLite's Row objects work like dicts
                    results = [dict(row) for row in rows]
                else:
                    # Convert pyodbc rows to dicts
                    results = []
                    for row in rows:
                        # Handle potential NaN values
                        converted_row = {}
                        for i, value in enumerate(row):
                            if i < len(columns):  # Make sure we have a corresponding column
                                col_name = columns[i]
                                if value is not None and isinstance(value, float) and math.isnan(value):
                                    converted_row[col_name] = None
                                else:
                                    converted_row[col_name] = value
                        results.append(converted_row)
                
                return {'columns': columns, 'rows': results}
            else:
                # For other queries, commit and return row count
                self.connection.commit()
                return {'affected_rows': cursor.rowcount}
                
        except Exception as e:
            logger.error(f"Error executing query: {str(e)}")
            if 'Check' in query:
                logger.error("Query contains 'Check' keyword which is reserved in Access")
            return {'error': str(e)}
    
    def execute_update(self, query, params=None):
        """Execute an update/insert/delete query and return success status"""
        try:
            if not self._connected:
                return False
                
            cursor = self.connection.cursor()
            
            # Execute the query with or without parameters
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
                
            # Commit the changes
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Error executing update: {str(e)}")
            return False
    
    def close(self):
        """Close the database connection"""
        if self.connection:
            try:
                self.connection.close()
                logger.info("Database connection closed")
            except Exception as e:
                logger.error(f"Error closing connection: {str(e)}")
                
        self.connection = None
        self._connected = False 

    @property
    def tables(self):
        """Get list of tables"""
        return self._tables
        
    @property
    def connected(self):
        """Check if connected"""
        return self._connected
        
    @connected.setter
    def connected(self, value):
        """Set connection state"""
        self._connected = value
        
    def check_connection_health(self):
        """Check if the connection is still active"""
        if not self._connected or not self.connection:
            return False
            
        try:
            # Execute a simple query to test connection
            if self.use_sqlite:
                self.connection.execute("SELECT 1")
            else:
                cursor = self.connection.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
            return True
        except Exception as e:
            logger.error(f"Connection health check failed: {str(e)}")
            return False
            
    def get_table_schema(self, table_name):
        """Get schema for a specific table"""
        if not self._connected or table_name not in self.table_schemas:
            return None
        return self.table_schemas.get(table_name)
        
    def execute_safe_insert(self, query_builder):
        """Compatibility method for the old execute_safe_insert"""
        if not self._connected:
            return False
            
        try:
            # Extract the SQL and parameters from the query builder
            sql, params = query_builder.get_sql_and_params()
            
            # Execute the query
            cursor = self.connection.cursor()
            cursor.execute(sql, params)
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Error executing safe insert: {str(e)}")
            return False
            
    def execute_safe_query(self, query, params=None):
        """Compatibility method for the old execute_safe_query"""
        return self.execute_query_safely(query, params)
            
    def execute_query_safely(self, query, params=None):
        """Execute a query with extra safety measures"""
        result = self.execute_query(query, params)
        
        # Convert to the format expected by the old code
        if 'error' in result:
            return []
        elif 'rows' in result:
            return result['rows']
        else:
            return []
            
    def execute_parameterized_query(self, query, params):
        """Execute a parameterized query"""
        return self.execute_query_safely(query, params)
        
    def get_vendor_data(self):
        """Get vendor data for compatibility"""
        if not self._connected:
            return []
            
        try:
            # Try to find the vendor table
            vendor_tables = ['vendors', 'vendor list', 'vendorlist']
            table_name = None
            
            for table in vendor_tables:
                if table in self._tables:
                    table_name = table
                    break
                    
            if not table_name:
                return []
                
            # Get the data
            result = self.execute_query(f"SELECT * FROM [{table_name}]")
            if 'rows' in result:
                return result['rows']
            return []
        except Exception as e:
            logger.error(f"Error getting vendor data: {str(e)}")
            return []
    
    def get_invoice_data(self):
        """Get invoice data for compatibility"""
        if not self._connected:
            return []
            
        try:
            # Try to find the invoice table
            invoice_tables = ['invoices', 'invoice list', 'invoicelist']
            table_name = None
            
            for table in invoice_tables:
                if table in self._tables:
                    table_name = table
                    break
                    
            if not table_name:
                return []
                
            # Get the data
            result = self.execute_query(f"SELECT * FROM [{table_name}]")
            if 'rows' in result:
                return result['rows']
            return []
        except Exception as e:
            logger.error(f"Error getting invoice data: {str(e)}")
            return []
    
    def get_basic_invoices(self, limit=100):
        """Get basic invoice data for compatibility"""
        return self.get_invoice_data()[:limit]
        
    def get_total_invoice_amount(self):
        """Get total invoice amount for compatibility"""
        if not self._connected:
            return 0
            
        try:
            # Try to find the invoice table
            invoice_tables = ['invoices', 'invoice list', 'invoicelist']
            table_name = None
            
            for table in invoice_tables:
                if table in self._tables:
                    table_name = table
                    break
                    
            if not table_name:
                return 0
                
            # Find the amount column
            amount_columns = ['amount', 'total', 'invoiceamount', 'invoice_amount']
            amount_col = None
            
            for col in amount_columns:
                if table_name in self.table_schemas:
                    schema = self.table_schemas[table_name]
                    if col in schema['columns']:
                        amount_col = col
                        break
                        
            if not amount_col:
                return 0
                
            # Get the sum
            result = self.execute_query(f"SELECT SUM([{amount_col}]) as total FROM [{table_name}]")
            if 'rows' in result and result['rows'] and 'total' in result['rows'][0]:
                return result['rows'][0]['total'] or 0
            return 0
        except Exception as e:
            logger.error(f"Error getting total invoice amount: {str(e)}")
            return 0


# Compatibility classes for the old access_db_fix.py

class QueryBuilder:
    """Query builder for compatibility with the old access_db_fix.py"""
    
    def __init__(self, db_connection, table_name):
        """Initialize the query builder"""
        self.db_connection = db_connection
        self.table_name = table_name
        self.query_type = None
        self._columns = []
        self._values = []
        self._where_clauses = []
        self._where_params = []
        self._order_by = None
        self._limit = None
        
    def reset(self):
        """Reset the query builder"""
        self.query_type = None
        self._columns = []
        self._values = []
        self._where_clauses = []
        self._where_params = []
        self._order_by = None
        self._limit = None
        return self
        
    def select(self, columns=None):
        """Start a SELECT query"""
        self.query_type = 'SELECT'
        if columns:
            if isinstance(columns, str):
                self._columns = [columns]
            else:
                self._columns = list(columns)
        return self
        
    def insert(self):
        """Start an INSERT query"""
        self.query_type = 'INSERT'
        return self
        
    def update(self):
        """Start an UPDATE query"""
        self.query_type = 'UPDATE'
        return self
        
    def delete(self):
        """Start a DELETE query"""
        self.query_type = 'DELETE'
        return self
        
    def columns(self, columns):
        """Set columns for INSERT or UPDATE"""
        self._columns = columns
        return self
        
    def values(self, values):
        """Set values for INSERT or UPDATE"""
        self._values = values
        return self
        
    def where(self, clause, params=None):
        """Add a WHERE clause"""
        self._where_clauses.append(clause)
        if params:
            if isinstance(params, list):
                self._where_params.extend(params)
            else:
                self._where_params.append(params)
        return self
        
    def order_by(self, column, direction='ASC'):
        """Add an ORDER BY clause"""
        self._order_by = f"{column} {direction}"
        return self
        
    def limit(self, limit):
        """Add a LIMIT clause"""
        self._limit = limit
        return self
        
    def get_sql_and_params(self):
        """Get the SQL statement and parameters"""
        sql = ''
        params = []
        
        if self.query_type == 'SELECT':
            columns_str = '*'
            if self._columns:
                columns_str = ', '.join([f'[{col}]' for col in self._columns])
                
            sql = f"SELECT {columns_str} FROM [{self.table_name}]"
            
            if self._where_clauses:
                sql += f" WHERE {' AND '.join(self._where_clauses)}"
                params.extend(self._where_params)
                
            if self._order_by:
                sql += f" ORDER BY {self._order_by}"
                
            if self._limit:
                sql += f" LIMIT {self._limit}"
                
        elif self.query_type == 'INSERT':
            columns_str = ', '.join([f'[{col}]' for col in self._columns])
            placeholders = ', '.join(['?' for _ in self._values])
            
            sql = f"INSERT INTO [{self.table_name}] ({columns_str}) VALUES ({placeholders})"
            params.extend(self._values)
            
        elif self.query_type == 'UPDATE':
            set_clauses = [f"[{col}] = ?" for col in self._columns]
            sql = f"UPDATE [{self.table_name}] SET {', '.join(set_clauses)}"
            params.extend(self._values)
            
            if self._where_clauses:
                sql += f" WHERE {' AND '.join(self._where_clauses)}"
                params.extend(self._where_params)
                
        elif self.query_type == 'DELETE':
            sql = f"DELETE FROM [{self.table_name}]"
            
            if self._where_clauses:
                sql += f" WHERE {' AND '.join(self._where_clauses)}"
                params.extend(self._where_params)
        
        return sql, params
        
    def execute(self):
        """Execute the query"""
        sql, params = self.get_sql_and_params()
        
        if self.query_type == 'SELECT':
            return self.db_connection.execute_query_safely(sql, params)
        elif self.query_type == 'INSERT':
            return self.db_connection.execute_safe_insert(self)
        elif self.query_type in ('UPDATE', 'DELETE'):
            try:
                cursor = self.db_connection.connection.cursor()
                cursor.execute(sql, params)
                self.db_connection.connection.commit()
                return True
            except Exception as e:
                logger.error(f"Error executing {self.query_type}: {str(e)}")
                return False
        
        return None

# For backwards compatibility
class AccessDatabaseFix:
    """Compatibility class to emulate the old AccessDatabaseFix class"""
    
    def __init__(self, db_path, dsn_name=None):
        """Initialize with a database connection"""
        self.db_path = db_path
        self.dsn_name = dsn_name
        self.connection = DatabaseConnection(db_path=db_path, dsn_name=dsn_name)
        self.connected = False
        
    def connect(self):
        """Connect to the database"""
        self.connected = self.connection.connect()
        return self.connected
        
    def close_connection(self):
        """Close the connection"""
        if self.connection:
            self.connection.close()
        self.connected = False
        
    @property
    def tables(self):
        """Get list of tables"""
        return self.connection.tables if self.connected else []
        
    @property
    def table_schemas(self):
        """Get table schemas"""
        return self.connection.table_schemas if self.connected else {}
        
    def get_table_schema(self, table_name):
        """Get schema for a specific table"""
        return self.connection.get_table_schema(table_name)
        
    def execute_query(self, query, params=None):
        """Execute a query"""
        return self.connection.execute_query(query, params)
        
    def execute_safe_query(self, query, params=None):
        """Execute a query safely"""
        return self.connection.execute_query_safely(query, params)
        
    def execute_safe_insert(self, query_builder):
        """Execute a safe insert"""
        return self.connection.execute_safe_insert(query_builder)
        
    def execute_parameterized_query(self, query, params):
        """Execute a parameterized query"""
        return self.connection.execute_parameterized_query(query, params)
        
    def get_vendor_data(self):
        """Get vendor data"""
        return self.connection.get_vendor_data()
        
    def get_invoice_data(self):
        """Get invoice data"""
        return self.connection.get_invoice_data() 