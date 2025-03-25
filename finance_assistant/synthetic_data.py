import random
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import logging
import pyodbc
import math

# Set up logger
logger = logging.getLogger("synthetic_data")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler("synthetic_data.log")
    fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(fh)

class SyntheticDataGenerator:
    """Generate synthetic data for demo mode that mimics real Access database structure"""
    
    def __init__(self, output_path="demo_data.accdb"):
        self.output_path = output_path
        self.conn = None
        self.cursor = None
        
        # Fake data generators
        self.company_names = [
            "Acme Corporation", "Globex", "Initech", "Umbrella Corp", "Stark Industries",
            "Wayne Enterprises", "Cyberdyne Systems", "Soylent Corp", "Massive Dynamic",
            "Weyland-Yutani", "Tyrell Corporation", "Oscorp", "LexCorp", "Gekko & Co",
            "Wonka Industries", "Stark Enterprises", "Dunder Mifflin", "Bluth Company",
            "Sirius Cybernetics", "Aperture Science", "InGen", "Prestige Worldwide",
            "Vandelay Industries", "Goliath National Bank", "Sterling Cooper",
            "TechCorp Solutions", "Virtual Dynamics", "Stratton Oakmont", "Genco Pura",
            "Oceanic Airlines", "Virtucon", "Nakatomi Trading Corp.", "Parker Industries"
        ]
        
        self.vendor_types = ["Supplier", "Contractor", "Service Provider", "Utility", "Consultant"]
        self.payment_terms = ["Net 30", "Net 60", "Net 15", "Due on Receipt", "Net 45"]
        self.fund_names = ["General Fund", "Capital Projects", "Special Revenue", "Enterprise Fund", "Debt Service"]
        self.expense_categories = ["Office Supplies", "IT Equipment", "Professional Services", "Utilities", "Rent", "Travel", "Maintenance", "Insurance", "Advertising", "Training"]
        self.status_options = ["Approved", "Pending", "Rejected", "In Review", "On Hold"]
        self.payment_status = ["Paid", "Unpaid", "Partial", "Voided", "Processing"]
        
    def connect_to_mdb(self):
        """Connect to Microsoft Access database for output"""
        try:
            # Only works on Windows with MS Access installed
            conn_str = f"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={self.output_path};"
            self.conn = pyodbc.connect(conn_str, autocommit=True)
            self.cursor = self.conn.cursor()
            logger.info(f"Connected to Access database at {self.output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Access: {str(e)}")
            logger.info("Falling back to SQLite for demo data")
            # Fallback to SQLite
            self.output_path = self.output_path.replace('.accdb', '.db')
            self.conn = sqlite3.connect(self.output_path)
            self.cursor = self.conn.cursor()
            return False
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None
    
    def create_schema(self):
        """Create database schema mimicking a real financial database"""
        try:
            # Create vendor list table (common in financial databases)
            self.cursor.execute('''
                CREATE TABLE [vendor list] (
                    ID INTEGER PRIMARY KEY,
                    [Name] TEXT,
                    [Vendor Type] TEXT,
                    [Contact Email] TEXT,
                    [Contact Phone] TEXT,
                    [Address] TEXT,
                    [Payment Terms] TEXT,
                    [Is 1099] BIT,
                    [Status] TEXT,
                    [Description] TEXT
                )
            ''')
            
            # Create Invoices table with problematic columns like "Check" and "Amount"
            self.cursor.execute('''
                CREATE TABLE Invoices (
                    ID INTEGER PRIMARY KEY,
                    [Vendor ID] INTEGER,
                    [Vendor] TEXT,
                    [Fund Paid By] TEXT,
                    [Invoice#] TEXT,
                    [Invoice Date] DATETIME,
                    [Due Date] DATETIME,
                    [total_amount] REAL,
                    [Status] TEXT,
                    [Payment Status] TEXT,
                    [Date of Payment] DATETIME,
                    [Check] TEXT,
                    [Amount] REAL,
                    [Days Overdue] INTEGER,
                    [Notes] TEXT
                )
            ''')
            
            # Create Expenses table (for expense tracking)
            self.cursor.execute('''
                CREATE TABLE Expenses (
                    ID INTEGER PRIMARY KEY,
                    [Date] DATETIME,
                    [Category] TEXT,
                    [Amount] REAL,
                    [Description] TEXT,
                    [Vendor ID] INTEGER,
                    [Vendor] TEXT,
                    [Fund] TEXT,
                    [Status] TEXT,
                    [Notes] TEXT
                )
            ''')
            
            # Create Revenue table (for revenue tracking)
            self.cursor.execute('''
                CREATE TABLE Revenue (
                    ID INTEGER PRIMARY KEY,
                    [Date] DATETIME,
                    [Source] TEXT,
                    [Amount] REAL,
                    [Description] TEXT,
                    [Fund] TEXT,
                    [Status] TEXT,
                    [Notes] TEXT
                )
            ''')
            
            # Create Funds table (for fund tracking)
            self.cursor.execute('''
                CREATE TABLE Funds (
                    ID INTEGER PRIMARY KEY,
                    [Name] TEXT,
                    [Description] TEXT,
                    [Balance] REAL,
                    [Start Date] DATETIME,
                    [End Date] DATETIME,
                    [Status] TEXT
                )
            ''')
            
            logger.info("Created database schema")
            return True
        except Exception as e:
            logger.error(f"Error creating schema: {str(e)}")
            return False
    
    def generate_vendors(self, count=30):
        """Generate synthetic vendor data"""
        try:
            for i in range(1, count + 1):
                vendor_name = random.choice(self.company_names) if random.random() < 0.8 else f"Vendor {i}"
                vendor_type = random.choice(self.vendor_types)
                payment_terms = random.choice(self.payment_terms)
                is_1099 = random.choice([0, 1])
                status = "Active" if random.random() < 0.8 else "Inactive"
                
                self.cursor.execute('''
                    INSERT INTO [vendor list] (
                        [Name], [Vendor Type], [Contact Email], [Contact Phone],
                        [Address], [Payment Terms], [Is 1099], [Status], [Description]
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    vendor_name,
                    vendor_type,
                    f"contact@{vendor_name.lower().replace(' ', '')}.com",
                    f"{random.randint(100, 999)}-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
                    f"{random.randint(100, 9999)} Main St, City {i%10}, State",
                    payment_terms,
                    is_1099,
                    status,
                    f"Description for {vendor_name}"
                ))
            
            logger.info(f"Generated {count} vendor records")
            return True
        except Exception as e:
            logger.error(f"Error generating vendors: {str(e)}")
            return False
    
    def generate_funds(self, count=5):
        """Generate synthetic fund data"""
        try:
            for i in range(1, count + 1):
                fund_name = self.fund_names[i-1] if i <= len(self.fund_names) else f"Fund {i}"
                start_date = datetime.now() - timedelta(days=random.randint(365, 730))
                end_date = start_date + timedelta(days=random.randint(365, 730))
                
                self.cursor.execute('''
                    INSERT INTO Funds (
                        [Name], [Description], [Balance], [Start Date], [End Date], [Status]
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    fund_name,
                    f"Description for {fund_name}",
                    random.uniform(10000, 1000000),
                    start_date,
                    end_date,
                    "Active" if random.random() < 0.8 else "Closed"
                ))
            
            logger.info(f"Generated {count} fund records")
            return True
        except Exception as e:
            logger.error(f"Error generating funds: {str(e)}")
            return False
    
    def generate_invoices(self, count=100):
        """Generate synthetic invoice data with problematic fields"""
        try:
            # Get vendor IDs and names
            vendors = []
            try:
                self.cursor.execute("SELECT ID, [Name] FROM [vendor list]")
                vendors = self.cursor.fetchall()
            except Exception as e:
                logger.error(f"Error fetching vendors: {str(e)}")
                vendors = [(i, f"Vendor {i}") for i in range(1, 31)]
            
            # Get fund names
            funds = []
            try:
                self.cursor.execute("SELECT [Name] FROM Funds")
                funds = [row[0] for row in self.cursor.fetchall()]
            except Exception as e:
                logger.error(f"Error fetching funds: {str(e)}")
                funds = self.fund_names
            
            # Generate invoices
            for i in range(1, count + 1):
                # Select a random vendor
                vendor = random.choice(vendors)
                vendor_id = vendor[0]
                vendor_name = vendor[1]
                
                # Generate dates with some invoices overdue
                invoice_date = datetime.now() - timedelta(days=random.randint(0, 180))
                due_date = invoice_date + timedelta(days=random.randint(15, 60))
                days_overdue = max(0, (datetime.now() - due_date).days)
                
                # Payment status and details
                is_paid = random.random() < 0.6  # 60% chance of being paid
                payment_status = random.choice(["Paid", "Complete"]) if is_paid else random.choice(["Unpaid", "Pending"])
                payment_date = invoice_date + timedelta(days=random.randint(1, 45)) if is_paid else None
                
                # Critical field: Check number (problematic in Access)
                check_number = f"CHK{random.randint(1000, 9999)}" if is_paid else ""
                
                # Critical field: Amount (problematic in Access)
                amount = round(random.uniform(100, 10000), 2)
                
                # Sometimes include NULL values to mimic real data
                fund = random.choice(funds) if random.random() < 0.9 else None
                
                self.cursor.execute('''
                    INSERT INTO Invoices (
                        [Vendor ID], [Vendor], [Fund Paid By], [Invoice#], [Invoice Date],
                        [Due Date], [total_amount], [Status], [Payment Status],
                        [Date of Payment], [Check], [Amount], [Days Overdue], [Notes]
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    vendor_id,
                    vendor_name,
                    fund,
                    f"INV-{random.randint(10000, 99999)}",
                    invoice_date,
                    due_date,
                    amount,
                    random.choice(self.status_options),
                    payment_status,
                    payment_date,
                    check_number,  # Problematic "Check" column
                    amount,        # Problematic "Amount" column
                    days_overdue,
                    f"Notes for invoice {i}" if random.random() < 0.3 else None
                ))
            
            logger.info(f"Generated {count} invoice records")
            return True
        except Exception as e:
            logger.error(f"Error generating invoices: {str(e)}")
            return False
    
    def generate_expenses(self, count=150):
        """Generate synthetic expense data"""
        try:
            # Get vendor IDs and names
            vendors = []
            try:
                self.cursor.execute("SELECT ID, [Name] FROM [vendor list]")
                vendors = self.cursor.fetchall()
            except Exception as e:
                logger.error(f"Error fetching vendors: {str(e)}")
                vendors = [(i, f"Vendor {i}") for i in range(1, 31)]
            
            # Get fund names
            funds = []
            try:
                self.cursor.execute("SELECT [Name] FROM Funds")
                funds = [row[0] for row in self.cursor.fetchall()]
            except Exception as e:
                logger.error(f"Error fetching funds: {str(e)}")
                funds = self.fund_names
            
            # Generate expenses
            for i in range(1, count + 1):
                # Select a random vendor
                vendor = random.choice(vendors) if random.random() < 0.8 else (None, None)
                vendor_id = vendor[0]
                vendor_name = vendor[1]
                
                # Random date within last year
                expense_date = datetime.now() - timedelta(days=random.randint(0, 365))
                
                # Amount and category
                amount = round(random.uniform(50, 5000), 2)
                category = random.choice(self.expense_categories)
                
                # Fund allocation
                fund = random.choice(funds) if random.random() < 0.9 else None
                
                self.cursor.execute('''
                    INSERT INTO Expenses (
                        [Date], [Category], [Amount], [Description], [Vendor ID],
                        [Vendor], [Fund], [Status], [Notes]
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    expense_date,
                    category,
                    amount,
                    f"{category} expense {i}",
                    vendor_id,
                    vendor_name,
                    fund,
                    random.choice(self.status_options),
                    f"Notes for expense {i}" if random.random() < 0.3 else None
                ))
            
            logger.info(f"Generated {count} expense records")
            return True
        except Exception as e:
            logger.error(f"Error generating expenses: {str(e)}")
            return False
    
    def generate_revenue(self, count=80):
        """Generate synthetic revenue data"""
        try:
            # Get fund names
            funds = []
            try:
                self.cursor.execute("SELECT [Name] FROM Funds")
                funds = [row[0] for row in self.cursor.fetchall()]
            except Exception as e:
                logger.error(f"Error fetching funds: {str(e)}")
                funds = self.fund_names
            
            # Revenue sources
            revenue_sources = ["Sales", "Services", "Grants", "Investments", "Donations", "Fees", "Interest"]
            
            # Generate revenue
            for i in range(1, count + 1):
                # Random date within last year
                revenue_date = datetime.now() - timedelta(days=random.randint(0, 365))
                
                # Amount and source
                amount = round(random.uniform(500, 50000), 2)
                source = random.choice(revenue_sources)
                
                # Fund allocation
                fund = random.choice(funds) if random.random() < 0.9 else None
                
                self.cursor.execute('''
                    INSERT INTO Revenue (
                        [Date], [Source], [Amount], [Description], [Fund], [Status], [Notes]
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    revenue_date,
                    source,
                    amount,
                    f"{source} revenue {i}",
                    fund,
                    random.choice(self.status_options),
                    f"Notes for revenue {i}" if random.random() < 0.3 else None
                ))
            
            logger.info(f"Generated {count} revenue records")
            return True
        except Exception as e:
            logger.error(f"Error generating revenue: {str(e)}")
            return False
    
    def generate_all(self):
        """Generate all synthetic data sets"""
        logger.info("Starting synthetic data generation")
        
        # Connect to database
        if not self.connect_to_mdb():
            logger.warning("Using SQLite instead of MS Access for demo data")
        
        # Create schema
        if not self.create_schema():
            logger.error("Failed to create schema, aborting data generation")
            self.close()
            return False
        
        # Generate data
        self.generate_vendors(30)
        self.generate_funds(5)
        self.generate_invoices(100)
        self.generate_expenses(150)
        self.generate_revenue(80)
        
        logger.info("Completed synthetic data generation")
        self.close()
        return True
    
    def generate_csv_data(self, output_dir="demo_csv"):
        """Generate CSV files for importing in demo mode"""
        try:
            # Create output directory if it doesn't exist
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # Generate vendor data
            vendors = []
            for i in range(1, 31):
                vendor_name = random.choice(self.company_names) if random.random() < 0.8 else f"Vendor {i}"
                vendors.append({
                    "ID": i,
                    "Name": vendor_name,
                    "Vendor_Type": random.choice(self.vendor_types),
                    "Contact_Email": f"contact@{vendor_name.lower().replace(' ', '')}.com",
                    "Contact_Phone": f"{random.randint(100, 999)}-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
                    "Address": f"{random.randint(100, 9999)} Main St, City {i%10}, State",
                    "Payment_Terms": random.choice(self.payment_terms),
                    "Is_1099": random.choice([0, 1]),
                    "Status": "Active" if random.random() < 0.8 else "Inactive",
                    "Description": f"Description for {vendor_name}"
                })
            
            vendor_df = pd.DataFrame(vendors)
            vendor_df.to_csv(os.path.join(output_dir, "vendors.csv"), index=False)
            
            # Generate invoice data with problematic fields
            invoices = []
            for i in range(1, 101):
                vendor_idx = random.randint(0, len(vendors)-1)
                vendor = vendors[vendor_idx]
                
                invoice_date = datetime.now() - timedelta(days=random.randint(0, 180))
                due_date = invoice_date + timedelta(days=random.randint(15, 60))
                days_overdue = max(0, (datetime.now() - due_date).days)
                
                is_paid = random.random() < 0.6
                payment_status = random.choice(["Paid", "Complete"]) if is_paid else random.choice(["Unpaid", "Pending"])
                payment_date = invoice_date + timedelta(days=random.randint(1, 45)) if is_paid else None
                
                # Critical field: Check number (problematic in Access)
                check_number = f"CHK{random.randint(1000, 9999)}" if is_paid else ""
                
                # Critical field: Amount (problematic in Access)
                amount = round(random.uniform(100, 10000), 2)
                
                # Include some NaN values
                fund = random.choice(self.fund_names) if random.random() < 0.9 else np.nan
                
                invoices.append({
                    "ID": i,
                    "Vendor_ID": vendor["ID"],
                    "Vendor": vendor["Name"],
                    "Fund_Paid_By": fund,
                    "Invoice_Number": f"INV-{random.randint(10000, 99999)}",
                    "Invoice_Date": invoice_date.strftime("%Y-%m-%d"),
                    "Due_Date": due_date.strftime("%Y-%m-%d"),
                    "total_amount": amount,
                    "Status": random.choice(self.status_options),
                    "Payment_Status": payment_status,
                    "Date_of_Payment": payment_date.strftime("%Y-%m-%d") if payment_date else np.nan,
                    "Check": check_number,  # Problematic "Check" column 
                    "Amount": amount,       # Problematic "Amount" column
                    "Days_Overdue": days_overdue,
                    "Notes": f"Notes for invoice {i}" if random.random() < 0.3 else np.nan
                })
            
            invoice_df = pd.DataFrame(invoices)
            invoice_df.to_csv(os.path.join(output_dir, "invoices.csv"), index=False)
            
            # Generate expenses
            expenses = []
            for i in range(1, 151):
                if random.random() < 0.8:
                    vendor_idx = random.randint(0, len(vendors)-1)
                    vendor = vendors[vendor_idx]
                    vendor_id = vendor["ID"]
                    vendor_name = vendor["Name"]
                else:
                    vendor_id = np.nan
                    vendor_name = np.nan
                
                expense_date = datetime.now() - timedelta(days=random.randint(0, 365))
                amount = round(random.uniform(50, 5000), 2)
                category = random.choice(self.expense_categories)
                
                expenses.append({
                    "ID": i,
                    "Date": expense_date.strftime("%Y-%m-%d"),
                    "Category": category,
                    "Amount": amount,
                    "Description": f"{category} expense {i}",
                    "Vendor_ID": vendor_id,
                    "Vendor": vendor_name,
                    "Fund": random.choice(self.fund_names) if random.random() < 0.9 else np.nan,
                    "Status": random.choice(self.status_options),
                    "Notes": f"Notes for expense {i}" if random.random() < 0.3 else np.nan
                })
            
            expense_df = pd.DataFrame(expenses)
            expense_df.to_csv(os.path.join(output_dir, "expenses.csv"), index=False)
            
            logger.info(f"Generated CSV files in {output_dir}")
            return True
        except Exception as e:
            logger.error(f"Error generating CSV data: {str(e)}")
            return False

def create_demo_database():
    """Create a demo database with synthetic data"""
    generator = SyntheticDataGenerator()
    return generator.generate_all()
    
def create_demo_csv_files():
    """Create demo CSV files for import testing"""
    generator = SyntheticDataGenerator()
    return generator.generate_csv_data() 