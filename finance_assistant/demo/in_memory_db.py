import logging
import sqlite3
from datetime import datetime

logger = logging.getLogger("demo.in_memory_db")

class DemoDatabase:
    """Pure in-memory database for demo mode without any Access dependencies"""
    
    def __init__(self):
        """Initialize in-memory SQLite database for demo mode"""
        self.connection = None
        self.connected = False
        self.tables = []
        
        logger.info("DemoDatabase initialized")
        
    def connect(self):
        """Connect to in-memory SQLite database"""
        try:
            # Create in-memory database
            self.connection = sqlite3.connect(':memory:')
            
            # Set row factory for dictionary-like access
            self.connection.row_factory = sqlite3.Row
            
            self.connected = True
            logger.info("Connected to in-memory demo database")
            
            # Create demo schema and populate with data
            self._create_demo_schema()
            self._populate_demo_data()
            
            # Get table list
            cursor = self.connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            self.tables = [row[0] for row in cursor.fetchall()]
            
            return True
        except Exception as e:
            logger.error(f"Error connecting to demo database: {str(e)}")
            return False
    
    def _create_demo_schema(self):
        """Create tables in demo database"""
        logger.info("Creating demo database schema")
        
        tables = [
            """
            CREATE TABLE Invoices (
                ID INTEGER PRIMARY KEY,
                InvoiceNumber TEXT,
                Date TEXT,
                DueDate TEXT,
                Amount REAL,
                Status TEXT,
                Client TEXT
            )
            """,
            """
            CREATE TABLE Vendors (
                ID INTEGER PRIMARY KEY,
                Name TEXT,
                Contact TEXT,
                Phone TEXT,
                Email TEXT,
                Address TEXT
            )
            """,
            """
            CREATE TABLE Expenses (
                ID INTEGER PRIMARY KEY,
                Date TEXT,
                Category TEXT,
                Amount REAL,
                Description TEXT,
                Vendor TEXT
            )
            """,
            """
            CREATE TABLE Revenue (
                ID INTEGER PRIMARY KEY,
                Date TEXT,
                Category TEXT,
                Amount REAL,
                Description TEXT,
                Client TEXT
            )
            """
        ]
        
        try:
            cursor = self.connection.cursor()
            for table_sql in tables:
                cursor.execute(table_sql)
            self.connection.commit()
            logger.info("Demo schema created successfully")
        except Exception as e:
            logger.error(f"Error creating demo schema: {str(e)}")
    
    def _populate_demo_data(self):
        """Populate demo database with sample data"""
        logger.info("Populating demo database with sample data")
        
        # Sample data - simplify this as needed
        data = {
            "Invoices": [
                (1, 'INV-001', '2023-01-10', '2023-02-10', 1500.00, 'Paid', 'ACME Corp'),
                (2, 'INV-002', '2023-01-25', '2023-02-25', 2750.00, 'Paid', 'XYZ Industries'),
                (3, 'INV-003', '2023-02-05', '2023-03-05', 1200.00, 'Unpaid', 'Global Tech'),
                (4, 'INV-004', '2023-02-15', '2023-03-15', 3500.00, 'Unpaid', 'ABC Company'),
                (5, 'INV-005', '2023-03-01', '2023-04-01', 950.00, 'Outstanding', 'Smith Consulting')
            ],
            "Vendors": [
                (1, 'Office Depot', 'John Smith', '555-1234', 'john@officedepot.com', '123 Main St, Anytown'),
                (2, 'Power Company', 'Customer Service', '555-2345', 'service@power.com', '456 Oak Ave, Anytown'),
                (3, 'ABC Properties', 'Jane Doe', '555-3456', 'jane@abcproperties.com', '789 Park Blvd, Anytown'),
                (4, 'Dropbox', 'Support Team', '555-4567', 'support@dropbox.com', 'Online'),
                (5, 'Uber', 'Driver Relations', '555-5678', 'drivers@uber.com', 'Mobile')
            ],
            "Expenses": [
                (1, '2023-01-15', 'Office Supplies', 125.75, 'Printer paper and ink', 'Office Depot'),
                (2, '2023-01-22', 'Utilities', 230.50, 'Electricity bill', 'Power Company'),
                (3, '2023-02-05', 'Rent', 1500.00, 'Office space monthly rent', 'ABC Properties'),
                (4, '2023-02-14', 'Software', 49.99, 'Cloud storage subscription', 'Dropbox'),
                (5, '2023-03-03', 'Travel', 350.25, 'Client meeting travel expenses', 'Uber')
            ],
            "Revenue": [
                (1, '2023-01-05', 'Consulting', 2500.00, 'Financial analysis project', 'ACME Corp'),
                (2, '2023-01-15', 'Services', 1800.00, 'Website development', 'XYZ Industries'),
                (3, '2023-02-10', 'Maintenance', 950.00, 'Monthly maintenance contract', 'Global Tech'),
                (4, '2023-02-20', 'Consulting', 3200.00, 'Market research project', 'ABC Company'),
                (5, '2023-03-05', 'Training', 1500.00, 'Staff training session', 'Smith Consulting')
            ]
        }
        
        try:
            cursor = self.connection.cursor()
            for table, rows in data.items():
                # Create placeholders based on number of columns
                placeholders = ", ".join(["?"] * len(rows[0]))
                query = f"INSERT INTO {table} VALUES ({placeholders})"
                
                # Insert each row
                for row in rows:
                    cursor.execute(query, row)
                    
            self.connection.commit()
            logger.info("Demo data populated successfully")
        except Exception as e:
            logger.error(f"Error populating demo data: {str(e)}")
    
    def execute_query(self, query, params=None):
        """Execute a query on the demo database"""
        try:
            if not self.connected:
                return {'error': 'Not connected to database'}
                
            cursor = self.connection.cursor()
            
            # Execute the query
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # Handle SELECT queries
            if query.strip().upper().startswith('SELECT'):
                rows = cursor.fetchall()
                if not cursor.description:
                    return {'columns': [], 'rows': []}
                    
                columns = [column[0] for column in cursor.description]
                results = [dict(row) for row in rows]
                
                return {'columns': columns, 'rows': results, 'sql': query}
            else:
                # For other queries, commit and return row count
                self.connection.commit()
                return {'affected_rows': cursor.rowcount}
                
        except Exception as e:
            logger.error(f"Error executing query in demo mode: {str(e)}")
            return {'error': str(e)}
    
    def close(self):
        """Close the demo database connection"""
        if self.connection:
            try:
                self.connection.close()
                logger.info("Demo database connection closed")
            except Exception as e:
                logger.error(f"Error closing demo connection: {str(e)}")
                
        self.connection = None
        self.connected = False 