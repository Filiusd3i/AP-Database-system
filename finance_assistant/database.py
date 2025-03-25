import pyodbc
import json
import os
import math
import logging
import warnings
from tkinter import filedialog, messagebox
from datetime import datetime

# Import from new structure
from finance_assistant.database.manager import DatabaseManager
from finance_assistant.database.connection import DatabaseConnection
from finance_assistant.demo.in_memory_db import DemoDatabase

# Show deprecation warning
warnings.warn(
    "The finance_assistant.database module is deprecated. "
    "Please use finance_assistant.database.manager.DatabaseManager instead.",
    DeprecationWarning,
    stacklevel=2
)

logger = logging.getLogger("database_manager")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    file_handler = logging.FileHandler("database_manager.log")
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)

# Keep the old DatabaseManager for backward compatibility
# This will be removed in a future version
# All implementation is now in finance_assistant/database/manager.py

class DatabaseManager:
    def __init__(self, app):
        self.app = app
        self.conn = None
        self.cursor = None
        self.db_tables = []
        self.db_schema = {}
        self.db_relationships = []
        self.demo_mode = False
        self.problematic_fields = {}  # Track fields that have NULL/NaN issues
        self.database_path = None
        self.db_connection = None  # DatabaseConnection handler
        self.access_db = None      # New AccessDatabaseFix handler
        self.robust_db = None      # New RobustAccessDB handler
        
        # Initialize DSN name if available
        self.dsn_name = os.environ.get("ACCESS_DSN", "MyAccessDB")
        
        logger.info("DatabaseManager initialized")
    
    def on_demo_mode_changed(self, is_active):
        """
        Observe state changes in demo mode.
        This implements the observer pattern for ApplicationState.
        """
        logger.info(f"DatabaseManager received demo mode change: {is_active}")
        
        if is_active:
            if not self.demo_mode:
                # Only enable if not already in demo mode
                self.enable_demo_mode()
        else:
            if self.demo_mode:
                # Only disable if currently in demo mode
                self.disable_demo_mode()
    
    def is_connected(self):
        """Check if connected to a database or in demo mode"""
        return ((self.db_connection and self.db_connection.connected) or 
                (self.access_db and self.access_db.connected) or 
                (self.robust_db and self.robust_db.connected) or 
                self.demo_mode)
    
    def enable_demo_mode(self):
        """Enable demo mode with synthetic data only - no actual database connection"""
        logger.info("Enabling demo mode with in-memory database only")
        
        # Close any existing connection
        self.close_connection()
        
        # Make sure we have an app_state for the DemoManager
        if not hasattr(self.app, 'app_state') or self.app.app_state is None:
            # Create an ApplicationState if it doesn't exist yet
            self.app.app_state = ApplicationState()
            logger.info("Created new ApplicationState for the application")
            
            # Register self as an observer
            self.app.app_state.register_observer(self)
            logger.info("Registered DatabaseManager as an observer")
        elif not hasattr(self.app.app_state, '_observers'):
            # If app_state exists but doesn't have _observers attribute
            logger.warning("ApplicationState exists but has no _observers attribute")
        elif self not in self.app.app_state._observers:
            # Register self as an observer if not already registered
            self.app.app_state.register_observer(self)
            logger.info("Registered DatabaseManager as an observer")
        
        # Initialize demo manager if not already done
        if not hasattr(self, 'demo_manager'):
            # Pass both app and app_state to DemoManager
            self.demo_manager = DemoManager(self.app, self.app.app_state)
            logger.info("Initialized DemoManager with ApplicationState")
        
        # Set demo mode flag
        self.demo_mode = True
        
        # Set demo mode in the ApplicationState
        self.app.app_state.set_demo_mode(True)
        
        # Use only in-memory SQLite for demo mode, no Access database at all
        try:
            logger.info("Setting up in-memory database for demo mode")
            self.robust_db = DbConnectionWrapper(":memory:", dsn_name=None, use_sqlite=True)
            connected = self.robust_db.connect()
            
            if connected:
                logger.info("Connected to in-memory SQLite database for demo mode")
                
                # Set up synthetic data
                self._generate_demo_schema()
                self._populate_demo_data()
                
                # Extract schema information
                self.db_tables = self.robust_db.tables
                
                # Generate sample data for demo dashboard
                self._generate_demo_relationships()
                
                return True, "Demo Mode"
            else:
                logger.error("Failed to connect to in-memory database")
        except Exception as e:
            logger.error(f"Error setting up in-memory database: {str(e)}")
        
        # Even if connection fails, still return success since we're in demo mode
        # and can use hardcoded data
        return True, "Demo Mode (Fallback)"
    
    def disable_demo_mode(self):
        """Disable demo mode"""
        logger.info("Disabling demo mode")
        self.demo_mode = False
        self.db_tables = []
        self.db_schema = {}
        self.db_relationships = []
        
        # Close any open connections
        if self.robust_db:
            self.robust_db.close()
            self.robust_db = None
            
        if self.access_db:
            try:
                self.access_db.close_connection()
            except:
                pass
            self.access_db = None
        
        # Update ApplicationState if it exists
        if hasattr(self.app, 'app_state'):
            self.app.app_state.set_demo_mode(False)
            logger.info("Disabled demo mode in ApplicationState")
        else:
            logger.warning("ApplicationState not found when disabling demo mode")
    
    def connect_to_access_database(self):
        """Connect to a Microsoft Access database with enhanced error handling for NaN values"""
        try:
            # Ask for database file first
            db_path = filedialog.askopenfilename(
                title="Select Microsoft Access Database",
                filetypes=[("Access Database", "*.accdb;*.mdb"), ("All files", "*.*")]
            )
            
            if not db_path:
                return False, "Cancelled"
                
            # Store the database path
            self.database_path = db_path
            
            # Use our robust database connection
            try:
                logger.info(f"Connecting to database using robust connection: {db_path}")
                self.robust_db = DbConnectionWrapper(db_path, self.dsn_name)
                connected = self.robust_db.connect()
                
                if connected:
                    logger.info("Connected to database using robust connection")
                    
                    # Extract schema information
                    self.db_tables = self.robust_db.tables
                    
                    # Map table_schemas to our format
                    self.db_schema = {}
                    self.problematic_fields = {}
                    
                    for table, schema in self.robust_db.table_schemas.items():
                        self.db_schema[table] = []
                        for col in schema['columns']:
                            col_info = {
                                'name': col,
                                'type': schema['column_types'].get(col, 'TEXT')
                            }
                            if col in schema['problem_columns']:
                                col_info['problematic'] = True
                            self.db_schema[table].append(col_info)
                        
                        # Track problematic fields
                        if schema['problem_columns']:
                            self.problematic_fields[table] = schema['problem_columns']
                    
                    logger.info(f"Found {len(self.db_tables)} user tables")
                    return True, os.path.basename(db_path)
                else:
                    logger.error("Failed to connect to database using robust connection")
            except Exception as e:
                logger.error(f"Error in robust connection: {str(e)}")
                
            # Fall back to old method if robust connection fails
            try:
                logger.info(f"Falling back to old connection method: {db_path}")
                self.access_db = AccessDatabaseFix(db_path)
                connected = self.access_db.connect()
                
                if connected:
                    logger.info("Connected to database using old connection method")
                    
                    # Update our table list and schema from the connection
                    self.db_tables = self.access_db.tables
                    
                    # Extract schema information
                    self.db_schema = {}
                    self.problematic_fields = {}
                    
                    # Map table_schemas to our expected format
                    for table, schema in self.access_db.table_schemas.items():
                        self.db_schema[table] = []
                        for col in schema['columns']:
                            col_info = {
                                'name': col,
                                'type': schema['column_types'].get(col, 'TEXT')
                            }
                            if col in schema['problem_columns']:
                                col_info['problematic'] = True
                            self.db_schema[table].append(col_info)
                        
                        # Track problematic fields
                        if schema['problem_columns']:
                            self.problematic_fields[table] = schema['problem_columns']
                    
                    logger.info(f"Found {len(self.db_tables)} user tables")
                    return True, os.path.basename(db_path)
                else:
                    logger.error("Failed to connect to database")
                    return False, "Connection failed"
            except Exception as e:
                logger.error(f"Error in fallback connection: {str(e)}")
                return False, f"Connection failed: {str(e)}"
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Unexpected connection error: {error_msg}")
            messagebox.showerror("Connection Error", f"Could not connect to database: {error_msg}")
            return False, str(e)

    def reconnect(self):
        """Attempt to reconnect to the database using the stored path"""
        if not self.database_path:
            return False, "No database path stored"
        
        logger.info(f"Attempting to reconnect to: {self.database_path}")
            
        try:
            # Try to reconnect using the robust connection first
            if self.robust_db:
                logger.info("Reconnecting using robust connection")
                self.robust_db = DbConnectionWrapper(self.database_path, self.dsn_name)
                connected = self.robust_db.connect()
                
                if connected:
                    logger.info("Reconnection successful using robust connection")
                    
                    # Update our data structures
                    self.db_tables = self.robust_db.tables
                    
                    # Update UI status if app and UI manager exist
                    try:
                        if self.app and hasattr(self.app, 'ui_manager'):
                            self.app.ui_manager.update_status(f"Connected to {os.path.basename(self.database_path)}")
                            self.app.ui_manager.display_message("System", f"Reconnected to database")
                    except:
                        pass
                        
                    return True, os.path.basename(self.database_path)
            
            # Fall back to old method if robust connection fails or wasn't used
            if self.access_db:
                logger.info("Reconnecting using old connection method")
                self.access_db = AccessDatabaseFix(self.database_path)
                connected = self.access_db.connect()
                
                if connected:
                    logger.info("Reconnection successful using old connection method")
                    
                    # Update our data structures
                    self.db_tables = self.access_db.tables
                    
                    # Update UI status if app and UI manager exist
                    try:
                        if self.app and hasattr(self.app, 'ui_manager'):
                            self.app.ui_manager.update_status(f"Connected to {os.path.basename(self.database_path)}")
                            self.app.ui_manager.display_message("System", f"Reconnected to database")
                    except:
                        pass
                        
                    return True, os.path.basename(self.database_path)
            
            logger.error("Reconnection failed - no connection method available")
            return False, "Reconnection failed"
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Reconnection failed: {error_msg}")
            return False, f"Reconnection failed: {error_msg}"
                
    def analyze_database(self):
        """Extract database schema with enhanced handling of NaN values"""
        if self.robust_db and self.robust_db.connected:
            logger.info("Analyzing database using robust connection")
            
            # Get tables from our connection
            self.db_tables = self.robust_db.tables
            
            # Map table_schemas to our expected format
            for table, schema in self.robust_db.table_schemas.items():
                self.db_schema[table] = []
                for col in schema['columns']:
                    col_info = {
                        'name': col,
                        'type': schema['column_types'].get(col, 'TEXT')
                    }
                    if col in schema['problem_columns']:
                        col_info['problematic'] = True
                    self.db_schema[table].append(col_info)
                
                # Track problematic fields
                if schema['problem_columns']:
                    self.problematic_fields[table] = schema['problem_columns']
            
            logger.info(f"Connected to database: {os.path.basename(self.database_path)}")
            logger.info(f"Found {len(self.db_tables)} user tables")
            return
            
        elif self.access_db and self.access_db.connected:
            logger.info("Analyzing database using old connection method")
            
            # Get tables from our connection
            self.db_tables = self.access_db.tables
            
            # Map table_schemas to our expected format
            for table, schema in self.access_db.table_schemas.items():
                self.db_schema[table] = []
                for col in schema['columns']:
                    col_info = {
                        'name': col,
                        'type': schema['column_types'].get(col, 'TEXT')
                    }
                    if col in schema['problem_columns']:
                        col_info['problematic'] = True
                    self.db_schema[table].append(col_info)
                
                # Track problematic fields
                if schema['problem_columns']:
                    self.problematic_fields[table] = schema['problem_columns']
            
            logger.info(f"Connected to database: {os.path.basename(self.database_path)}")
            logger.info(f"Found {len(self.db_tables)} user tables")
            return
            
        logger.warning("Cannot analyze database: Not connected")
    
    def execute_query(self, query):
        """Execute a SQL query with special handling for NaN values and brackets for the Check column"""
        if self.demo_mode:
            # Handle demo mode
            return self._generate_demo_results(query)
        
        # Try to use the robust database connection first
        if self.robust_db and self.robust_db.connected:
            logger.info(f"Executing query using robust connection: {query}")
            return self.robust_db.execute_query(query)
            
        # Fall back to old method if robust connection not available
        if self.access_db and self.access_db.connected:
            logger.info(f"Executing query using old connection method: {query}")
            
            try:
                # Handle 'Invoices' queries specially to avoid the Check column
                if "Invoices" in query:
                    if "SELECT" in query.upper() and "*" in query:
                        # Replace SELECT * with safe column list
                        logger.info(f"Using get_invoice_data for: {query}")
                        result = self.access_db.get_invoice_data()
                        
                    elif "COUNT(*)" in query:
                        # For count queries
                        logger.info(f"Using get_invoice_totals for: {query}")
                        totals = self.access_db.get_invoice_totals()
                        if totals and 'total_invoices' in totals:
                            result = [{'COUNT': totals['total_invoices']}]
                        else:
                            result = [{'COUNT': 0}]
                            
                    elif "SUM" in query.upper() and "total_amount" in query:
                        # For sum of amount queries
                        logger.info(f"Using get_invoice_totals for: {query}")
                        totals = self.access_db.get_invoice_totals()
                        if totals and 'total_amount' in totals:
                            result = [{'SUM(total_amount)': totals['total_amount']}]
                        else:
                            result = [{'SUM(total_amount)': 0}]
                    
                    elif "SUM" in query.upper() and "Amount" in query:
                        # Handle troublesome Amount column in SUM queries
                        logger.info(f"Using get_invoice_totals for SUM(Amount) query")
                        totals = self.access_db.get_invoice_totals()
                        if totals and 'total_amount' in totals:
                            result = [{'SUM(Amount)': totals['total_amount']}]
                        else:
                            result = [{'SUM(Amount)': 0}]
                    
                    else:
                        # For other Invoice queries, try safe parameterized query
                        result = self.access_db.execute_query(query)
                else:
                    # Non-Invoice queries
                    result = self.access_db.execute_query(query)
                
                return result
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Error executing query: {error_msg}")
                if "Check" in query or "Amount" in query:
                    logger.error("Error may be related to problematic column names like 'Check' or 'Amount'")
                return {'error': error_msg}
                
        return {'error': 'Not connected to a database.'}
    
    def close_connection(self):
        """Close the database connection"""
        logger.info("Closing database connections")
        
        # Close robust connection if it exists
        if self.robust_db:
            try:
                self.robust_db.close()
                logger.info("Closed robust database connection")
            except Exception as e:
                logger.error(f"Error closing robust connection: {str(e)}")
            self.robust_db = None
            
        # Close old connection if it exists
        if self.access_db:
            try:
                self.access_db.close_connection()
                logger.info("Closed old database connection")
            except Exception as e:
                logger.error(f"Error closing old connection: {str(e)}")
            self.access_db = None
            
        # Reset other connection properties
        self.conn = None
        self.cursor = None
        
        # Clear cached data
        self.db_tables = []
        self.db_schema = {}
        self.problematic_fields = {}
        
        logger.info("All database connections closed")

    def _generate_demo_results(self, query):
        """Return demo data based on the query"""
        # Simple regex-based query parser for demo mode
        sql_lower = query.lower()
        
        # Check for JOIN queries
        if ' join ' in sql_lower:
            return self._get_demo_join_data(query)
        
        # Sample data for each table
        demo_data = {
            'expenses': {
                'columns': ['ID', 'Date', 'Category', 'Amount', 'Description', 'Vendor'],
                'rows': [
                    (1, datetime(2023, 1, 15), 'Office Supplies', 125.75, 'Printer paper and ink', 'Office Depot'),
                    (2, datetime(2023, 1, 22), 'Utilities', 230.50, 'Electricity bill', 'Power Company'),
                    (3, datetime(2023, 2, 5), 'Rent', 1500.00, 'Office space monthly rent', 'ABC Properties'),
                    (4, datetime(2023, 2, 14), 'Software', 49.99, 'Cloud storage subscription', 'Dropbox'),
                    (5, datetime(2023, 3, 3), 'Travel', 350.25, 'Client meeting travel expenses', 'Uber')
                ]
            },
            'invoices': {
                'columns': ['ID', 'InvoiceNumber', 'Date', 'DueDate', 'Amount', 'Status', 'Client'],
                'rows': [
                    (1, 'INV-001', datetime(2023, 1, 10), datetime(2023, 2, 10), 1500.00, 'Paid', 'ACME Corp'),
                    (2, 'INV-002', datetime(2023, 1, 25), datetime(2023, 2, 25), 2750.00, 'Paid', 'XYZ Industries'),
                    (3, 'INV-003', datetime(2023, 2, 5), datetime(2023, 3, 5), 1200.00, 'Unpaid', 'Global Tech'),
                    (4, 'INV-004', datetime(2023, 2, 15), datetime(2023, 3, 15), 3500.00, 'Unpaid', 'ABC Company'),
                    (5, 'INV-005', datetime(2023, 3, 1), datetime(2023, 4, 1), 950.00, 'Outstanding', 'Smith Consulting')
                ]
            },
            'vendors': {
                'columns': ['ID', 'Name', 'Contact', 'Phone', 'Email', 'Address'],
                'rows': [
                    (1, 'Office Depot', 'John Smith', '555-1234', 'john@officedepot.com', '123 Main St, Anytown'),
                    (2, 'Power Company', 'Customer Service', '555-2345', 'service@power.com', '456 Oak Ave, Anytown'),
                    (3, 'ABC Properties', 'Jane Doe', '555-3456', 'jane@abcproperties.com', '789 Park Blvd, Anytown'),
                    (4, 'Dropbox', 'Support Team', '555-4567', 'support@dropbox.com', 'Online'),
                    (5, 'Uber', 'Driver Relations', '555-5678', 'drivers@uber.com', 'Mobile')
                ]
            },
            'revenue': {
                'columns': ['ID', 'Date', 'Category', 'Amount', 'Description', 'Client'],
                'rows': [
                    (1, datetime(2023, 1, 5), 'Consulting', 2500.00, 'Financial analysis project', 'ACME Corp'),
                    (2, datetime(2023, 1, 15), 'Services', 1800.00, 'Website development', 'XYZ Industries'),
                    (3, datetime(2023, 2, 10), 'Maintenance', 950.00, 'Monthly maintenance contract', 'Global Tech'),
                    (4, datetime(2023, 2, 20), 'Consulting', 3200.00, 'Market research project', 'ABC Company'),
                    (5, datetime(2023, 3, 5), 'Training', 1500.00, 'Staff training session', 'Smith Consulting')
                ]
            }
        }
        
        # For SELECT * queries, just return the whole table
        if "select * from" in sql_lower:
            table_name = sql_lower.split("from")[1].strip().split()[0].lower()
            if table_name in demo_data:
                return demo_data[table_name]
            else:
                return {'columns': [], 'rows': [], 'sql': query}
                
        # Determine which table the query is for
        result_table = None
        for table in self.db_tables:
            if table.lower() in sql_lower:
                result_table = table.lower()
                break
        
        if not result_table:
            # Default to expenses if no table found
            result_table = 'expenses'
        
        # Check for specific query patterns
        if 'unpaid' in sql_lower and 'invoices' in sql_lower:
            # Filter for unpaid invoices
            table_data = demo_data['invoices']
            filtered_rows = [row for row in table_data['rows'] if row[5] == 'Unpaid']
            return {'columns': table_data['columns'], 'rows': filtered_rows, 'sql': query}
        
        if 'sum' in sql_lower and 'amount' in sql_lower:
            # Handle sum query for amount
            if 'expenses' in sql_lower:
                total = sum(row[3] for row in demo_data['expenses']['rows'])
                return {'columns': ['TotalExpenses'], 'rows': [(total,)], 'sql': query}
            elif 'revenue' in sql_lower:
                total = sum(row[3] for row in demo_data['revenue']['rows'])
                return {'columns': ['TotalRevenue'], 'rows': [(total,)], 'sql': query}
        
        # If it's a month-specific query, filter by month
        months = ['january', 'february', 'march', 'april', 'may', 'june', 
                  'july', 'august', 'september', 'october', 'november', 'december']
        for i, month in enumerate(months, 1):
            if month in sql_lower:
                table_data = demo_data[result_table]
                filtered_rows = [row for row in table_data['rows'] if row[1].month == i]
                return {'columns': table_data['columns'], 'rows': filtered_rows, 'sql': query}
        
        # Default: return all data for the table
        return {'columns': demo_data[result_table]['columns'], 
                'rows': demo_data[result_table]['rows'], 
                'sql': query}
    
    def _get_demo_join_data(self, query):
        """Generate demo data for JOIN queries"""
        sql_lower = query.lower()
        
        # Demo data for common JOIN queries
        if ('invoices' in sql_lower and 'vendors' in sql_lower) or ('invoices' in sql_lower and 'client' in sql_lower):
            # Joining invoices and vendors/clients
            return {
                'columns': ['InvoiceNumber', 'Date', 'Amount', 'Status', 'Client', 'Contact', 'Email'],
                'rows': [
                    ('INV-001', datetime(2023, 1, 10), 1500.00, 'Paid', 'ACME Corp', 'John Smith', 'john@acme.com'),
                    ('INV-002', datetime(2023, 1, 25), 2750.00, 'Paid', 'XYZ Industries', 'Jane Doe', 'jane@xyz.com'),
                    ('INV-003', datetime(2023, 2, 5), 1200.00, 'Unpaid', 'Global Tech', 'Bob Johnson', 'bob@globaltech.com'),
                    ('INV-004', datetime(2023, 2, 15), 3500.00, 'Unpaid', 'ABC Company', 'Alice Brown', 'alice@abc.com'),
                    ('INV-005', datetime(2023, 3, 1), 950.00, 'Outstanding', 'Smith Consulting', 'Mike Smith', 'mike@smith.com')
                ],
                'sql': query
            }
        elif 'expenses' in sql_lower and 'vendors' in sql_lower:
            # Joining expenses and vendors
            return {
                'columns': ['Date', 'Category', 'Amount', 'Description', 'Vendor', 'Contact', 'Phone'],
                'rows': [
                    (datetime(2023, 1, 15), 'Office Supplies', 125.75, 'Printer paper and ink', 'Office Depot', 'John Smith', '555-1234'),
                    (datetime(2023, 1, 22), 'Utilities', 230.50, 'Electricity bill', 'Power Company', 'Customer Service', '555-2345'),
                    (datetime(2023, 2, 5), 'Rent', 1500.00, 'Office space monthly rent', 'ABC Properties', 'Jane Doe', '555-3456'),
                    (datetime(2023, 2, 14), 'Software', 49.99, 'Cloud storage subscription', 'Dropbox', 'Support Team', '555-4567'),
                    (datetime(2023, 3, 3), 'Travel', 350.25, 'Client meeting travel expenses', 'Uber', 'Driver Relations', '555-5678')
                ],
                'sql': query
            }
        elif 'invoices' in sql_lower and 'fund' in sql_lower.lower():
            # Invoices grouped by fund
            return {
                'columns': ['Fund', 'InvoiceCount', 'TotalAmount'],
                'rows': [
                    ('MIPPGF', 12, 15000.00),
                    ('QZ', 8, 9500.00),
                    ('Income Fund', 5, 5200.00)
                ],
                'sql': query
            }
        
        # Generic JOIN query result
        return {
            'columns': ['TableA_ID', 'TableA_Name', 'TableB_ID', 'TableB_Name', 'Related_Value'],
            'rows': [
                (1, 'Item A1', 101, 'Item B1', 'Value 1'),
                (2, 'Item A2', 102, 'Item B2', 'Value 2'),
                (3, 'Item A3', 103, 'Item B3', 'Value 3'),
                (4, 'Item A4', 104, 'Item B4', 'Value 4'),
                (5, 'Item A5', 105, 'Item B5', 'Value 5')
            ],
            'sql': query
        }

    def process_nl_query(self, user_question):
        """Process a natural language query using demo manager or templates"""
        # If in demo mode, use the demo manager
        if self.demo_mode and hasattr(self, 'demo_manager'):
            result, template_id, source = self.demo_manager.process_query(user_question)
            if result:
                # Add metadata about how the query was processed
                result['_query_metadata'] = {
                    'template_id': template_id,
                    'source': source,
                    'demo_mode': True
                }
            return result
        
        # If not in demo mode but we have templates, try using them
        elif hasattr(self, 'demo_manager') and self.is_connected():
            # Use only templates, not OpenAI
            # Find matching template
            template = self.demo_manager.template_manager.find_matching_template(user_question)
            if template:
                # Calculate confidence
                confidence = self.demo_manager.template_manager.calculate_template_confidence(
                    template, user_question)
                
                # Only use if confidence is high
                if confidence >= 0.7:
                    safe_query, params = template.apply(user_question)
                    if safe_query:
                        # Execute against real database
                        # This is safe because our templates only use safe methods
                        try:
                            access_db = self.access_db
                            
                            # Check if query is calling a method or is raw SQL
                            if safe_query.startswith("access_db."):
                                # Execute method call
                                local_vars = {'access_db': access_db}
                                result = eval(safe_query, {'__builtins__': {}}, local_vars)
                                
                                # Format result if needed
                                if isinstance(result, list) and result:
                                    columns = list(result[0].keys())
                                    rows = []
                                    for item in result:
                                        rows.append([item[col] for col in columns])
                                    
                                    result = {
                                        'columns': columns,
                                        'rows': rows,
                                        'row_count': len(rows)
                                    }
                                
                                # Add metadata
                                if isinstance(result, dict):
                                    result['_query_metadata'] = {
                                        'template_id': template.id,
                                        'source': 'template',
                                        'demo_mode': False
                                    }
                                
                                return result
                            else:
                                # It's a SQL query, execute it
                                return self.execute_query(safe_query)
                        except Exception as e:
                            print(f"Error executing template query: {str(e)}")
        
        # Fall back to normal query processing
        return None 

    def _generate_demo_schema(self):
        """Create tables in the in-memory database for demo mode"""
        logger.info("Generating demo schema in in-memory database")
        
        if not self.robust_db or not self.robust_db.connected:
            logger.error("Cannot generate demo schema: No database connection")
            return
        
        try:
            # Create tables for common financial data
            self.robust_db.execute_update("""
                CREATE TABLE Invoices (
                    ID INTEGER PRIMARY KEY,
                    InvoiceNumber TEXT,
                    Date TEXT,
                    DueDate TEXT,
                    Amount REAL,
                    Status TEXT,
                    Client TEXT
                )
            """)
            
            self.robust_db.execute_update("""
                CREATE TABLE Vendors (
                    ID INTEGER PRIMARY KEY,
                    Name TEXT,
                    Contact TEXT,
                    Phone TEXT,
                    Email TEXT,
                    Address TEXT
                )
            """)
            
            self.robust_db.execute_update("""
                CREATE TABLE Expenses (
                    ID INTEGER PRIMARY KEY,
                    Date TEXT,
                    Category TEXT,
                    Amount REAL,
                    Description TEXT,
                    Vendor TEXT
                )
            """)
            
            self.robust_db.execute_update("""
                CREATE TABLE Revenue (
                    ID INTEGER PRIMARY KEY,
                    Date TEXT,
                    Category TEXT,
                    Amount REAL,
                    Description TEXT,
                    Client TEXT
                )
            """)
            
            logger.info("Demo schema created successfully")
        except Exception as e:
            logger.error(f"Error creating demo schema: {str(e)}")

    def _populate_demo_data(self):
        """Populate in-memory database with sample data for demo mode"""
        logger.info("Populating demo database with sample data")
        
        if not self.robust_db or not self.robust_db.connected:
            logger.error("Cannot populate demo data: No database connection")
            return
        
        try:
            # Sample invoices
            invoices = [
                (1, 'INV-001', '2023-01-10', '2023-02-10', 1500.00, 'Paid', 'ACME Corp'),
                (2, 'INV-002', '2023-01-25', '2023-02-25', 2750.00, 'Paid', 'XYZ Industries'),
                (3, 'INV-003', '2023-02-05', '2023-03-05', 1200.00, 'Unpaid', 'Global Tech'),
                (4, 'INV-004', '2023-02-15', '2023-03-15', 3500.00, 'Unpaid', 'ABC Company'),
                (5, 'INV-005', '2023-03-01', '2023-04-01', 950.00, 'Outstanding', 'Smith Consulting')
            ]
            
            for invoice in invoices:
                self.robust_db.execute_update(
                    "INSERT INTO Invoices VALUES (?, ?, ?, ?, ?, ?, ?)",
                    invoice
                )
            
            # Sample vendors
            vendors = [
                (1, 'Office Depot', 'John Smith', '555-1234', 'john@officedepot.com', '123 Main St, Anytown'),
                (2, 'Power Company', 'Customer Service', '555-2345', 'service@power.com', '456 Oak Ave, Anytown'),
                (3, 'ABC Properties', 'Jane Doe', '555-3456', 'jane@abcproperties.com', '789 Park Blvd, Anytown'),
                (4, 'Dropbox', 'Support Team', '555-4567', 'support@dropbox.com', 'Online'),
                (5, 'Uber', 'Driver Relations', '555-5678', 'drivers@uber.com', 'Mobile')
            ]
            
            for vendor in vendors:
                self.robust_db.execute_update(
                    "INSERT INTO Vendors VALUES (?, ?, ?, ?, ?, ?)",
                    vendor
                )
            
            # Sample expenses
            expenses = [
                (1, '2023-01-15', 'Office Supplies', 125.75, 'Printer paper and ink', 'Office Depot'),
                (2, '2023-01-22', 'Utilities', 230.50, 'Electricity bill', 'Power Company'),
                (3, '2023-02-05', 'Rent', 1500.00, 'Office space monthly rent', 'ABC Properties'),
                (4, '2023-02-14', 'Software', 49.99, 'Cloud storage subscription', 'Dropbox'),
                (5, '2023-03-03', 'Travel', 350.25, 'Client meeting travel expenses', 'Uber')
            ]
            
            for expense in expenses:
                self.robust_db.execute_update(
                    "INSERT INTO Expenses VALUES (?, ?, ?, ?, ?, ?)",
                    expense
                )
            
            # Sample revenue
            revenues = [
                (1, '2023-01-05', 'Consulting', 2500.00, 'Financial analysis project', 'ACME Corp'),
                (2, '2023-01-15', 'Services', 1800.00, 'Website development', 'XYZ Industries'),
                (3, '2023-02-10', 'Maintenance', 950.00, 'Monthly maintenance contract', 'Global Tech'),
                (4, '2023-02-20', 'Consulting', 3200.00, 'Market research project', 'ABC Company'),
                (5, '2023-03-05', 'Training', 1500.00, 'Staff training session', 'Smith Consulting')
            ]
            
            for revenue in revenues:
                self.robust_db.execute_update(
                    "INSERT INTO Revenue VALUES (?, ?, ?, ?, ?, ?)",
                    revenue
                )
            
            logger.info("Demo data populated successfully")
        except Exception as e:
            logger.error(f"Error populating demo data: {str(e)}") 