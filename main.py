#!/usr/bin/env python3
"""
Finance Database Assistant

A simplified Python application that connects to a PostgreSQL database
and displays an invoice dashboard with real-time updates.
"""

import logging
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import filedialog
from finance_assistant.database.manager import DatabaseManager
from finance_assistant.dashboard import InvoiceDashboard
import pandas as pd
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class FinanceApp:
    """Main application for the Finance Database Assistant"""
    
    def __init__(self, root):
        """Initialize the application
        
        Args:
            root: Tkinter root window
        """
        self.root = root
        self.root.title("Finance Database Assistant")
        self.root.geometry("1200x800")
        
        # Set icon if available
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except:
                pass  # Ignore if icon can't be set
        
        # Initialize database manager
        self.db_manager = DatabaseManager(self)
        
        # Create main frame
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create status bar
        self.status_bar = ttk.Label(self.root, text="Not connected to database", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Create menu
        self._create_menu()
        
        # Create database connection frame
        self._create_connection_frame()
        
        # Dashboard (will be created after connecting to database)
        self.dashboard = None
        
        # Auto-connect using environment variables if available
        self._try_auto_connect()
        
        logger.info("Application initialized")
    
    def _try_auto_connect(self):
        """Try to automatically connect using environment variables"""
        # Check if all required environment variables are set
        host = os.getenv("DB_HOST")
        port_str = os.getenv("DB_PORT")
        db_name = os.getenv("DB_NAME")
        username = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")
        
        # Only proceed if we have all the necessary connection info
        if host and port_str and db_name and username:
            try:
                # Ensure port is an integer
                port = int(port_str)
                
                # Update the UI fields to match
                self.host_entry.delete(0, tk.END)
                self.host_entry.insert(0, host)
                
                self.port_entry.delete(0, tk.END)
                self.port_entry.insert(0, str(port))
                
                self.db_name_entry.delete(0, tk.END)
                self.db_name_entry.insert(0, db_name)
                
                self.username_entry.delete(0, tk.END)
                self.username_entry.insert(0, username)
                
                if password:
                    self.password_entry.delete(0, tk.END)
                    self.password_entry.insert(0, password)
                
                # Connect to the database
                logger.info(f"Attempting auto-connect to {db_name} on {host}:{port}")
                success, message = self.db_manager.connect_to_database(db_name, host, port, username, password)
                
                if success:
                    # Update status
                    self.status_bar.config(text=f"Connected to {db_name} on {host}:{port}")
                    
                    # Enable initialize button
                    self.init_button.config(state=tk.NORMAL)
                    
                    # Show dashboard
                    self._show_dashboard()
                    
                    logger.info(f"Auto-connected to database: {db_name}")
                else:
                    logger.warning(f"Auto-connect failed: {message}")
                    
            except ValueError:
                logger.error(f"Invalid port in environment variable: {port_str}")
            except Exception as e:
                logger.error(f"Error in auto-connect: {str(e)}")
                messagebox.showerror("Auto-Connect Error", f"Failed to automatically connect: {str(e)}")
    
    def _create_menu(self):
        """Create the application menu"""
        # Create menu bar
        menu_bar = tk.Menu(self.root)
        self.root.config(menu=menu_bar)
        
        # File menu
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Connect to Database", command=self._show_connection_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menu_bar.add_cascade(label="File", menu=file_menu)
        
        # View menu
        view_menu = tk.Menu(menu_bar, tearoff=0)
        view_menu.add_command(label="Dashboard", command=self._show_dashboard)
        menu_bar.add_cascade(label="View", menu=view_menu)
        
        # Database menu
        db_menu = tk.Menu(menu_bar, tearoff=0)
        db_menu.add_command(label="Create New Table", command=self._show_create_table_dialog)
        db_menu.add_command(label="Import Data", command=self._show_import_dialog)
        # Add schema management submenu
        schema_menu = tk.Menu(db_menu, tearoff=0)
        schema_menu.add_command(label="Fix Table Names with Spaces", command=self._fix_table_names)
        schema_menu.add_command(label="Rename Specific Table", command=self._rename_specific_table)
        schema_menu.add_command(label="View Database Schema", command=self._view_database_schema)
        db_menu.add_cascade(label="Schema Management", menu=schema_menu)
        menu_bar.add_cascade(label="Database", menu=db_menu)
        
        # Help menu
        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="About", command=self._show_about)
        menu_bar.add_cascade(label="Help", menu=help_menu)
    
    def _create_connection_frame(self):
        """Create the database connection frame"""
        # Create a frame for database connection
        self.connection_frame = ttk.LabelFrame(self.main_frame, text="Database Connection")
        self.connection_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Connection form
        conn_form = ttk.Frame(self.connection_frame)
        conn_form.pack(padx=20, pady=20)
        
        # Host
        ttk.Label(conn_form, text="Host:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.host_entry = ttk.Entry(conn_form, width=30)
        self.host_entry.grid(row=0, column=1, padx=5, pady=5)
        self.host_entry.insert(0, "localhost")
        
        # Port
        ttk.Label(conn_form, text="Port:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.port_entry = ttk.Entry(conn_form, width=30)
        self.port_entry.grid(row=1, column=1, padx=5, pady=5)
        self.port_entry.insert(0, "5432")
        
        # Database
        ttk.Label(conn_form, text="Database:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.db_name_entry = ttk.Entry(conn_form, width=30)
        self.db_name_entry.grid(row=2, column=1, padx=5, pady=5)
        
        # Username
        ttk.Label(conn_form, text="Username:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self.username_entry = ttk.Entry(conn_form, width=30)
        self.username_entry.grid(row=3, column=1, padx=5, pady=5)
        self.username_entry.insert(0, "postgres")
        
        # Password
        ttk.Label(conn_form, text="Password:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        self.password_entry = ttk.Entry(conn_form, width=30, show="*")
        self.password_entry.grid(row=4, column=1, padx=5, pady=5)
        
        # Connect button
        self.connect_button = ttk.Button(conn_form, text="Connect", command=self._connect_to_database)
        self.connect_button.grid(row=5, column=0, columnspan=2, pady=10)
        
        # Initialize button
        self.init_button = ttk.Button(conn_form, text="Initialize Sample Database", command=self._initialize_database)
        self.init_button.grid(row=6, column=0, columnspan=2, pady=10)
        self.init_button.config(state=tk.DISABLED)
    
    def _connect_to_database(self):
        """Connect to the PostgreSQL database"""
        # Get connection parameters
        host = self.host_entry.get().strip()
        try:
            port = int(self.port_entry.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Port must be a number")
            return
        
        db_name = self.db_name_entry.get().strip()
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip() or None
        
        # Validate inputs
        if not db_name:
            messagebox.showerror("Error", "Database name is required")
            return
        
        # Try to connect
        success, message = self.db_manager.connect_to_database(db_name, host, port, username, password)
        
        if success:
            # Update status
            self.status_bar.config(text=f"Connected to {db_name} on {host}:{port}")
            
            # Enable initialize button
            self.init_button.config(state=tk.NORMAL)
            
            # Show dashboard
            self._show_dashboard()
            
            messagebox.showinfo("Success", message)
        else:
            if "does not exist" in message:
                create = messagebox.askyesno(
                    "Database Not Found", 
                    f"Database '{db_name}' does not exist. Would you like to create it?"
                )
                if create:
                    self._create_database(db_name, host, port, username, password)
                return
            
            messagebox.showerror("Connection Error", message)
            
    def _create_database(self, db_name, host, port, username, password):
        """Create a new PostgreSQL database
        
        Args:
            db_name: Database name
            host: Database host
            port: Database port
            username: Username
            password: Password
        """
        try:
            # Connect to the default 'postgres' database to create a new database
            conn_params = {
                "dbname": "postgres",  # Connect to the default postgres database
                "user": username,
                "host": host,
                "port": port
            }
            
            if password:
                conn_params["password"] = password
                
            # Connect to postgres database
            import psycopg2
            conn = psycopg2.connect(**conn_params)
            conn.autocommit = True  # Required for creating database
            
            # Create a cursor
            cursor = conn.cursor()
            
            # Create the database
            cursor.execute(f"CREATE DATABASE {db_name}")
            
            # Close connection
            cursor.close()
            conn.close()
            
            messagebox.showinfo("Success", f"Database '{db_name}' created successfully. Try connecting again.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create database: {str(e)}")
            logger.error(f"Error creating database: {str(e)}")
    
    def _initialize_database(self):
        """Initialize the database with sample tables and data"""
        if not self.db_manager.connected:
            messagebox.showerror("Error", "Not connected to database")
            return
        
        # Ask for confirmation
        confirm = messagebox.askyesno(
            "Initialize Database",
            "This will create tables and sample data in the database. Continue?"
        )
        
        if not confirm:
            return
        
        # Setup database
        success = self.db_manager.setup_database()
        
        if success:
            messagebox.showinfo("Success", "Database initialized with sample data")
            
            # Refresh dashboard if it exists
            if self.dashboard:
                self.dashboard._update_summary_cards()
                self.dashboard._update_charts()
                self.dashboard._update_invoice_table()
                self.dashboard._update_fund_filter()
        else:
            messagebox.showerror("Error", "Failed to initialize database")
    
    def _show_connection_dialog(self):
        """Show the database connection dialog"""
        # Hide dashboard if visible
        if self.dashboard:
            self.dashboard.frame.pack_forget()
        
        # Show connection frame
        self.connection_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    def _show_dashboard(self):
        """Show the invoice dashboard"""
        if not self.db_manager.connected:
            messagebox.showerror("Error", "Please connect to a database first")
            return
        
        # Hide connection frame
        self.connection_frame.pack_forget()
        
        # Create dashboard if it doesn't exist
        if not self.dashboard:
            self.dashboard = InvoiceDashboard(self.main_frame, self.db_manager)
        
        # Show dashboard
        self.dashboard.show()
    
    def _show_about(self):
        """Show the about dialog"""
        messagebox.showinfo(
            "About",
            "Finance Database Assistant\n\n"
            "A Python application for managing and visualizing invoice data\n"
            "with PostgreSQL database integration."
        )

    def _show_create_table_dialog(self):
        """Show dialog for creating a new table"""
        if not self.db_manager.connected:
            messagebox.showerror("Error", "Please connect to a database first")
            return
            
        # Create dialog window
        create_dialog = tk.Toplevel(self.root)
        create_dialog.title("Create New Table")
        create_dialog.geometry("600x400")
        
        # Create main frame
        main_frame = ttk.Frame(create_dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Table name
        ttk.Label(main_frame, text="Table Name:").pack(anchor=tk.W)
        table_name = ttk.Entry(main_frame, width=40)
        table_name.pack(fill=tk.X, pady=(0, 10))
        
        # Columns frame
        columns_frame = ttk.LabelFrame(main_frame, text="Columns", padding="5")
        columns_frame.pack(fill=tk.BOTH, expand=True)
        
        # Column list
        column_list = ttk.Treeview(columns_frame, columns=("name", "type", "nullable"), show="headings")
        column_list.heading("name", text="Name")
        column_list.heading("type", text="Type")
        column_list.heading("nullable", text="Nullable")
        column_list.pack(fill=tk.BOTH, expand=True)
        
        # Column types
        types = ["VARCHAR", "INTEGER", "DECIMAL", "DATE", "BOOLEAN", "TEXT"]
        
        def add_column():
            """Add a new column"""
            column_dialog = tk.Toplevel(create_dialog)
            column_dialog.title("Add Column")
            column_dialog.geometry("300x200")
            
            frame = ttk.Frame(column_dialog, padding="10")
            frame.pack(fill=tk.BOTH, expand=True)
            
            # Column name
            ttk.Label(frame, text="Column Name:").pack(anchor=tk.W)
            name_entry = ttk.Entry(frame, width=30)
            name_entry.pack(fill=tk.X, pady=(0, 10))
            
            # Column type
            ttk.Label(frame, text="Type:").pack(anchor=tk.W)
            type_var = tk.StringVar(value=types[0])
            type_combo = ttk.Combobox(frame, textvariable=type_var, values=types, state="readonly")
            type_combo.pack(fill=tk.X, pady=(0, 10))
            
            # Nullable
            nullable_var = tk.BooleanVar(value=True)
            nullable_check = ttk.Checkbutton(frame, text="Allow NULL", variable=nullable_var)
            nullable_check.pack(fill=tk.X, pady=(0, 10))
            
            def save_column():
                name = name_entry.get().strip()
                if not name:
                    messagebox.showerror("Error", "Column name is required")
                    return
                    
                column_list.insert("", "end", values=(name, type_var.get(), "Yes" if nullable_var.get() else "No"))
                column_dialog.destroy()
            
            ttk.Button(frame, text="Save", command=save_column).pack(fill=tk.X)
        
        def remove_column():
            """Remove selected column"""
            selected = column_list.selection()
            if selected:
                column_list.delete(selected)
        
        # Buttons frame
        buttons_frame = ttk.Frame(columns_frame)
        buttons_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(buttons_frame, text="Add Column", command=add_column).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Remove Column", command=remove_column).pack(side=tk.LEFT, padx=5)
        
        def create_table():
            """Create the table"""
            name = table_name.get().strip()
            if not name:
                messagebox.showerror("Error", "Table name is required")
                return
                
            if not column_list.get_children():
                messagebox.showerror("Error", "At least one column is required")
                return
            
            # Build CREATE TABLE statement
            columns = []
            for item in column_list.get_children():
                values = column_list.item(item)["values"]
                nullable = "NULL" if values[2] == "Yes" else "NOT NULL"
                columns.append(f"{values[0]} {values[1]} {nullable}")
            
            create_sql = f"CREATE TABLE {name} (\n  " + ",\n  ".join(columns) + "\n)"
            
            # Execute the query
            result = self.db_manager.execute_query(create_sql)
            
            if "error" in result and result["error"]:
                messagebox.showerror("Error", f"Failed to create table: {result['error']}")
            else:
                messagebox.showinfo("Success", f"Table '{name}' created successfully")
                create_dialog.destroy()
        
        # Create button
        ttk.Button(main_frame, text="Create Table", command=create_table).pack(fill=tk.X, pady=(10, 0))
    
    def _show_import_dialog(self):
        """Show dialog for importing data"""
        if not self.db_manager.connected:
            messagebox.showerror("Error", "Not connected to database")
            return
            
        # Create dialog window
        dialog = tk.Toplevel(self.root)
        dialog.title("Import Data")
        dialog.geometry("500x300")
        
        # Create main frame
        main_frame = ttk.Frame(dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Target table
        ttk.Label(main_frame, text="Target Table:").pack(anchor=tk.W)
        table_var = tk.StringVar()
        table_entry = ttk.Entry(main_frame, textvariable=table_var)
        table_entry.pack(fill=tk.X, pady=(0, 10))
        
        # File selection
        ttk.Label(main_frame, text="CSV File:").pack(anchor=tk.W)
        file_frame = ttk.Frame(main_frame)
        file_frame.pack(fill=tk.X, pady=(0, 10))
        
        file_path = tk.StringVar()
        file_entry = ttk.Entry(file_frame, textvariable=file_path)
        file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        def browse_file():
            filename = filedialog.askopenfilename(
                title="Select CSV File",
                filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
            )
            if filename:
                file_path.set(filename)
        
        ttk.Button(file_frame, text="Browse", command=browse_file).pack(side=tk.RIGHT, padx=(5, 0))
        
        def import_data():
            """Import data from CSV"""
            table = table_var.get().strip()
            if not table:
                messagebox.showerror("Error", "Please enter a table name")
                return
                
            file = file_path.get()
            if not file:
                messagebox.showerror("Error", "Please select a CSV file")
                return
            
            try:
                # Read CSV file
                df = pd.read_csv(file)
                
                # Check if table exists
                result = self.db_manager.execute_query(
                    f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}')"
                )
                
                if "error" in result:
                    raise Exception(result["error"])
                    
                table_exists = result["rows"][0][0]
                
                if not table_exists:
                    # Create table based on CSV structure
                    columns = []
                    for col_name, dtype in df.dtypes.items():
                        # Map pandas dtypes to PostgreSQL types
                        if dtype == 'int64':
                            col_type = 'INTEGER'
                        elif dtype == 'float64':
                            col_type = 'DOUBLE PRECISION'
                        elif dtype == 'datetime64[ns]':
                            col_type = 'TIMESTAMP'
                        elif dtype == 'bool':
                            col_type = 'BOOLEAN'
                        else:
                            col_type = 'TEXT'
                            
                        # Clean column name (remove special characters)
                        clean_col = ''.join(c for c in col_name if c.isalnum() or c == '_')
                        if clean_col != col_name:
                            messagebox.showwarning("Warning", f"Column name '{col_name}' was cleaned to '{clean_col}'")
                            
                        columns.append(f"{clean_col} {col_type}")
                    
                    # Create table
                    create_sql = f"CREATE TABLE {table} (\n  " + ",\n  ".join(columns) + "\n)"
                    result = self.db_manager.execute_query(create_sql)
                    
                    if "error" in result:
                        raise Exception(result["error"])
                        
                    messagebox.showinfo("Success", f"Table '{table}' created successfully")
                
                # Get table columns
                columns_result = self.db_manager.execute_query(
                    f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}'"
                )
                if "error" in columns_result:
                    raise Exception(columns_result["error"])
                
                table_columns = [row[0] for row in columns_result["rows"]]
                
                # Check if CSV columns match table columns
                csv_columns = df.columns.tolist()
                missing_columns = set(table_columns) - set(csv_columns)
                if missing_columns:
                    messagebox.showerror("Error", f"CSV file is missing required columns: {', '.join(missing_columns)}")
                    return
                
                # Insert data
                for _, row in df.iterrows():
                    values = [row[col] for col in table_columns]
                    placeholders = ", ".join(["%s"] * len(values))
                    insert_sql = f"INSERT INTO {table} ({', '.join(table_columns)}) VALUES ({placeholders})"
                    
                    result = self.db_manager.execute_query(insert_sql, values)
                    if "error" in result:
                        raise Exception(result["error"])
                
                messagebox.showinfo("Success", "Data imported successfully")
                dialog.destroy()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import data: {str(e)}")
        
        # Import button
        ttk.Button(main_frame, text="Import Data", command=import_data).pack(fill=tk.X, pady=(10, 0))

    def _fix_table_names(self):
        """Fix table names with spaces by renaming them to snake_case format"""
        if not self.db_manager.connected:
            messagebox.showerror("Error", "Not connected to database")
            return
            
        # Ask for confirmation
        confirm = messagebox.askyesno(
            "Fix Table Names", 
            "This will rename all tables with spaces to use snake_case formatting.\n\n"
            "For example: 'Deal Allocations' → 'deal_allocations'\n\n"
            "This operation cannot be undone. Continue?"
        )
        
        if not confirm:
            return
            
        # Rename tables with spaces
        try:
            # Fetch the latest table list
            self.db_manager._fetch_tables()
            
            # Check if there are tables with spaces
            tables_with_spaces = [t for t in self.db_manager.tables if ' ' in t]
            
            if not tables_with_spaces:
                messagebox.showinfo("No Action Needed", "No tables with spaces were found in the database.")
                return
                
            # Rename tables with spaces
            renamed_map = self.db_manager.rename_tables_with_spaces()
            
            if not renamed_map:
                messagebox.showwarning("Warning", "No tables were renamed. Check the log for details.")
                return
                
            # Show results
            result_message = "The following tables were renamed:\n\n"
            for old_name, new_name in renamed_map.items():
                result_message += f"• '{old_name}' → '{new_name}'\n"
                
            messagebox.showinfo("Success", result_message)
            
            # Refresh dashboard if it exists to use the new table names
            if self.dashboard:
                self.dashboard._refresh_dashboard()
                
        except Exception as e:
            logger.error(f"Error fixing table names: {str(e)}")
            messagebox.showerror("Error", f"Failed to fix table names: {str(e)}")
    
    def _rename_specific_table(self):
        """Rename a specific table, especially useful for tables with spaces"""
        if not self.db_manager.connected:
            messagebox.showerror("Error", "Not connected to database")
            return
            
        # Create dialog window
        dialog = tk.Toplevel(self.root)
        dialog.title("Rename Table")
        dialog.geometry("500x250")
        dialog.grab_set()  # Make dialog modal
        
        # Create main frame
        main_frame = ttk.Frame(dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Fetch the latest table list
        self.db_manager._fetch_tables()
        
        # Table selection
        ttk.Label(main_frame, text="Select Table to Rename:").pack(anchor=tk.W)
        table_var = tk.StringVar()
        table_combo = ttk.Combobox(main_frame, textvariable=table_var, state="readonly", width=40)
        table_combo["values"] = sorted(self.db_manager.tables)
        table_combo.pack(fill=tk.X, pady=(0, 10))
        
        # Target name
        ttk.Label(main_frame, text="New Table Name:").pack(anchor=tk.W)
        new_name_var = tk.StringVar()
        new_name_entry = ttk.Entry(main_frame, textvariable=new_name_var, width=40)
        new_name_entry.pack(fill=tk.X, pady=(0, 10))
        
        # Suggestion frame
        suggestion_frame = ttk.Frame(main_frame)
        suggestion_frame.pack(fill=tk.X, pady=(0, 10))
        
        suggestion_label = ttk.Label(suggestion_frame, text="", font=("", 9, "italic"))
        suggestion_label.pack(anchor=tk.W)
        
        def on_table_select(event):
            """Update the suggested name when a table is selected"""
            selected = table_var.get()
            if selected:
                # Create a snake_case suggestion
                import re
                suggested = selected.replace(' ', '_')
                suggested = re.sub(r'[^a-zA-Z0-9_]', '_', suggested).lower()
                new_name_var.set(suggested)
                
                # Update suggestion text
                if ' ' in selected:
                    suggestion_label["text"] = f"Suggestion: Rename '{selected}' to '{suggested}'"
                    suggestion_label["foreground"] = "blue"
                else:
                    suggestion_label["text"] = "This table already follows naming conventions."
                    suggestion_label["foreground"] = "green"
        
        # Bind selection event
        table_combo.bind("<<ComboboxSelected>>", on_table_select)
        
        def rename_table():
            """Rename the selected table"""
            old_name = table_var.get()
            new_name = new_name_var.get().strip()
            
            if not old_name:
                messagebox.showerror("Error", "Please select a table to rename")
                return
                
            if not new_name:
                messagebox.showerror("Error", "Please enter a new table name")
                return
                
            # Validate the new name (only allow letters, numbers, and underscores)
            import re
            if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', new_name):
                messagebox.showerror(
                    "Invalid Name", 
                    "Table name must start with a letter and contain only letters, numbers, and underscores."
                )
                return
                
            # Check if the new name already exists
            if new_name in self.db_manager.tables and new_name != old_name:
                messagebox.showerror("Error", f"A table named '{new_name}' already exists")
                return
                
            # Ask for confirmation
            confirm = messagebox.askyesno(
                "Confirm Rename", 
                f"Rename table '{old_name}' to '{new_name}'?\n\nThis operation cannot be undone."
            )
            
            if not confirm:
                return
                
            try:
                # Safely quote the original table name
                quoted_original = self.db_manager.quote_identifier(old_name)
                
                # Execute the rename query
                query = f"ALTER TABLE {quoted_original} RENAME TO {new_name}"
                result = self.db_manager.execute_query(query)
                
                if "error" in result and result["error"]:
                    raise Exception(result["error"])
                    
                # Update the table list
                self.db_manager._fetch_tables()
                
                messagebox.showinfo("Success", f"Table renamed successfully: '{old_name}' → '{new_name}'")
                
                # Refresh the table list in the dialog
                table_combo["values"] = sorted(self.db_manager.tables)
                
                # Refresh dashboard if it exists
                if self.dashboard:
                    self.dashboard._refresh_dashboard()
                    
                # Close the dialog
                dialog.destroy()
                
            except Exception as e:
                logger.error(f"Error renaming table: {str(e)}")
                messagebox.showerror("Error", f"Failed to rename table: {str(e)}")
        
        # Buttons
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(buttons_frame, text="Rename", command=rename_table).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(buttons_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT)
    
    def _view_database_schema(self):
        """View the database schema, highlighting tables with naming issues"""
        if not self.db_manager.connected:
            messagebox.showerror("Error", "Not connected to database")
            return
            
        # Create dialog window
        dialog = tk.Toplevel(self.root)
        dialog.title("Database Schema")
        dialog.geometry("800x600")
        
        # Create main frame
        main_frame = ttk.Frame(dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab for tables
        tables_frame = ttk.Frame(notebook, padding="10")
        notebook.add(tables_frame, text="Tables")
        
        # Tables treeview with scrollbar
        tree_frame = ttk.Frame(tables_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create scrollbars
        y_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        y_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create treeview
        table_tree = ttk.Treeview(
            tree_frame, 
            columns=("name", "rows", "status"),
            show="headings",
            yscrollcommand=y_scroll.set
        )
        
        # Configure columns
        table_tree.heading("name", text="Table Name")
        table_tree.heading("rows", text="Row Count")
        table_tree.heading("status", text="Naming Status")
        
        # Set column widths
        table_tree.column("name", width=300)
        table_tree.column("rows", width=100)
        table_tree.column("status", width=200)
        
        # Pack the table
        table_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Configure scrollbars
        y_scroll.config(command=table_tree.yview)
        
        # Tab for naming guidelines
        guidelines_frame = ttk.Frame(notebook, padding="10")
        notebook.add(guidelines_frame, text="Naming Guidelines")
        
        # Add guidelines text
        guidelines_text = tk.Text(guidelines_frame, wrap=tk.WORD, padx=10, pady=10)
        guidelines_text.pack(fill=tk.BOTH, expand=True)
        
        guidelines_content = """
## PostgreSQL Table and Column Naming Best Practices

### General Guidelines
- Use snake_case (lowercase with underscores) for all identifiers
- Avoid spaces and special characters
- Use short but descriptive names
- Be consistent across your database schema

### Table Naming
- Use plural form for table names (e.g., users, invoices)
- Prefix related tables with a common term (e.g., invoice_items, invoice_payments)
- Avoid reserved words (like check, order, table, etc.)

### Column Naming
- Use singular form for column names
- Use id as the primary key column name
- Name foreign keys consistently as table_name_id
- Prefix Boolean columns with is_, has_, or can_

### Common Problems
- Table names with spaces require double quotes in SQL queries
- Mixed-case identifiers are case-sensitive and require quotes
- Reserved keywords as identifiers cause syntax errors

Following these conventions will make your database more maintainable and less prone to errors.
"""
        guidelines_text.insert(tk.END, guidelines_content)
        guidelines_text.configure(state=tk.DISABLED)  # Make read-only
        
        # Fetch and display table data
        def load_tables():
            """Load table data and populate the treeview"""
            # Clear existing data
            for row in table_tree.get_children():
                table_tree.delete(row)
                
            # Fetch the latest table list
            self.db_manager._fetch_tables()
            
            if not self.db_manager.tables:
                return
                
            # Add tables to treeview
            for table in sorted(self.db_manager.tables):
                # Get row count
                count_query = f"SELECT COUNT(*) FROM {self.db_manager.quote_identifier(table)}"
                count_result = self.db_manager.execute_query(count_query)
                row_count = count_result["rows"][0][0] if "rows" in count_result and count_result["rows"] else 0
                
                # Determine naming status
                import re
                if ' ' in table:
                    status = "Bad: Contains spaces"
                elif not table.islower():
                    status = "Bad: Mixed case"
                elif not re.match(r'^[a-z][a-z0-9_]*$', table):
                    status = "Bad: Invalid characters"
                else:
                    status = "Good: Follows conventions"
                    
                # Add to treeview with status-based tags
                table_tree.insert("", "end", values=(table, row_count, status), tags=(status,))
                
            # Configure tags for coloring
            table_tree.tag_configure("Good: Follows conventions", foreground="green")
            table_tree.tag_configure("Bad: Contains spaces", foreground="red")
            table_tree.tag_configure("Bad: Mixed case", foreground="orange")
            table_tree.tag_configure("Bad: Invalid characters", foreground="red")
            
        # Add a button frame
        button_frame = ttk.Frame(tables_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Add refresh button
        refresh_btn = ttk.Button(button_frame, text="Refresh", command=load_tables)
        refresh_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Add export button
        def export_schema():
            """Export the schema to a CSV file"""
            try:
                filename = filedialog.asksaveasfilename(
                    defaultextension=".csv",
                    filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                    title="Export Schema"
                )
                
                if not filename:
                    return
                    
                # Create a DataFrame from the table data
                data = []
                for item in table_tree.get_children():
                    values = table_tree.item(item)["values"]
                    data.append({
                        "Table Name": values[0],
                        "Row Count": values[1],
                        "Naming Status": values[2]
                    })
                    
                df = pd.DataFrame(data)
                df.to_csv(filename, index=False)
                
                messagebox.showinfo("Success", f"Schema exported to {filename}")
                
            except Exception as e:
                logger.error(f"Error exporting schema: {str(e)}")
                messagebox.showerror("Error", f"Failed to export schema: {str(e)}")
        
        export_btn = ttk.Button(button_frame, text="Export to CSV", command=export_schema)
        export_btn.pack(side=tk.LEFT)
        
        # Load tables initially
        load_tables()

def main():
    """Main entry point for the application"""
    # Create the main window
    root = tk.Tk()
    
    # Create the application
    app = FinanceApp(root)
    
    # Run the application
    root.mainloop()

if __name__ == "__main__":
    main() 