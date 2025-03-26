#!/usr/bin/env python3
"""
Financial Database Assistant

A simplified tool for managing financial data with a user-friendly interface.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import sys
import logging
import platform
from dotenv import load_dotenv
import re
import difflib
import threading
import csv

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from finance_assistant.database.manager import DatabaseManager

# Load environment variables from .env file
load_dotenv()

# Configure logging
try:
    # Try to use enhanced logging with ELK Stack support
    from finance_assistant.logging_config import configure_logging
    logger = configure_logging('finance_assistant')
except ImportError as e:
    # Fall back to basic logging if there's an issue with the logging module
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("finance_app.log"),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)
    logger.warning(f"Enhanced logging not available, using basic logging: {str(e)}")

class FinancialAssistant:
    """Main application class - simplified version"""
    
    def __init__(self):
        """Initialize the application"""
        # Create main window
        self.root = tk.Tk()
        self.root.title("Financial Database Assistant")
        self.root.geometry("1200x800")
        
        # Initialize database manager
        self.db_manager = DatabaseManager()
        
        # Initialize LLM client
        try:
            from finance_assistant.llm_client import LLMClient
            self.llm_client = LLMClient()
            logger.info("LLM client initialized")
        except Exception as e:
            logger.error(f"Error initializing LLM client: {str(e)}")
            self.llm_client = None
        
        # Configure theme
        self._configure_theme()
        
        # Create main layout
        self._create_layout()
        
        # Try to auto-connect using .env file
        self._try_auto_connect()
        
    def _configure_theme(self):
        """Configure the dark gradient theme for the application"""
        # Define color palette
        self.bg_dark = '#1e1e2e'  # Dark background
        self.bg_medium = '#2a2a3a'  # Medium background
        self.bg_light = '#313145'  # Lighter background
        self.accent_color = '#7e57c2'  # Purple accent
        self.text_color = '#e0e0e0'  # Light text
        self.highlight_color = '#bb86fc'  # Highlight color

        # Determine platform-specific font
        if platform.system() == "Windows":
            self.font_family = "Segoe UI"
        elif platform.system() == "Darwin":  # macOS
            self.font_family = "SF Pro Text"
        else:  # Linux
            self.font_family = "Ubuntu"
            
        # Configure style
        self.style = ttk.Style()
        self.style.theme_use('clam')  # Most customizable built-in theme
        
        # Configure base styles
        self.style.configure('TFrame', background=self.bg_dark)
        self.style.configure('TLabelframe', background=self.bg_dark, foreground=self.text_color)
        self.style.configure('TLabelframe.Label', background=self.bg_dark, foreground=self.text_color, font=(self.font_family, 10))
        self.style.configure('TLabel', background=self.bg_dark, foreground=self.text_color, font=(self.font_family, 10))
        self.style.configure('TButton', background=self.accent_color, foreground=self.text_color, font=(self.font_family, 10))
        self.style.map('TButton', 
                      background=[('active', self.highlight_color), ('pressed', self.bg_light)],
                      foreground=[('active', 'white')])
        self.style.configure('TEntry', fieldbackground=self.bg_light, foreground=self.text_color, font=(self.font_family, 10))
        
        # Configure Treeview colors
        self.style.configure('Treeview', 
                           background=self.bg_medium, 
                           foreground=self.text_color,
                           fieldbackground=self.bg_medium,
                           font=(self.font_family, 10))
        self.style.map('Treeview', 
                      background=[('selected', self.accent_color)],
                      foreground=[('selected', 'white')])
        self.style.configure('Treeview.Heading', font=(self.font_family, 10, 'bold'))
        
        # Configure menu appearance
        self.root.option_add('*Menu.background', self.bg_medium)
        self.root.option_add('*Menu.foreground', self.text_color)
        self.root.option_add('*Menu.activeBackground', self.accent_color)
        self.root.option_add('*Menu.activeForeground', 'white')
        
        # Accent style for important buttons
        self.style.configure('Accent.TButton', font=(self.font_family, 10, 'bold'))
        
        # Configure window background
        self.root.configure(background=self.bg_dark)
        
    def _create_layout(self):
        """Create the main layout"""
        # Create menu bar
        self._create_menu()
        
        # Create main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Add gradient header
        header_frame = tk.Frame(main_frame, height=60, bg=self.bg_dark)
        header_frame.pack(fill=tk.X)
        
        # Create gradient effect with Canvas
        header_canvas = tk.Canvas(header_frame, height=60, bg=self.bg_dark, highlightthickness=0)
        header_canvas.pack(fill=tk.X, expand=True)
        
        # Draw gradient in header
        for i in range(60):
            # Calculate color for each line to create gradient
            r = int(30 + (i/60) * 18)
            g = int(30 + (i/60) * 18)
            b = int(46 + (i/60) * 23)
            color = f'#{r:02x}{g:02x}{b:02x}'
            header_canvas.create_line(0, i, 2000, i, fill=color)
        
        # Add title to header
        header_canvas.create_text(20, 30, text="Financial Database Assistant", 
                                 fill=self.text_color, font=(self.font_family, 16, 'bold'),
                                 anchor='w')
        
        # Create toolbar with styled buttons
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, padx=10, pady=10)
        
        # Create styled button frame with subtle background
        button_frame = tk.Frame(toolbar, bg=self.bg_medium, padx=5, pady=5)
        button_frame.pack(fill=tk.X)
        
        # Add toolbar buttons with icons using the accent style
        ttk.Button(button_frame, text="Connect Database", style="Accent.TButton", 
                  command=self._connect_database).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Unified Dashboard", style="Accent.TButton", 
                  command=self._show_unified_dashboard).pack(side=tk.LEFT, padx=5)
        
        # Create status bar with gradient effect
        status_frame = tk.Frame(main_frame, height=25, bg=self.bg_medium)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_label = ttk.Label(status_frame, textvariable=self.status_var, 
                               anchor=tk.W, background=self.bg_medium)
        status_label.pack(fill=tk.X, padx=10, pady=4)
        
        # Create content area
        self.content_frame = ttk.Frame(main_frame)
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Add welcome message
        welcome_frame = ttk.Frame(self.content_frame)
        welcome_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(welcome_frame, text="Welcome to Financial Database Assistant", 
                font=(self.font_family, 18, 'bold')).pack(pady=(50, 20))
        
        ttk.Label(welcome_frame, text="Connect to a database to get started, or use the toolbar to access dashboards.",
                font=(self.font_family, 12)).pack(pady=10)
        
        # Add quick access buttons
        button_frame = ttk.Frame(welcome_frame)
        button_frame.pack(pady=30)
        
        ttk.Button(button_frame, text="Connect to Database", style="Accent.TButton",
                 command=self._connect_database, width=25).pack(pady=5)
        ttk.Button(button_frame, text="Open Unified Dashboard", style="Accent.TButton",
                 command=self._show_unified_dashboard, width=25).pack(pady=5)
        
    def _create_menu(self):
        """Create the menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Connect Database", command=self._connect_database)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Database menu
        db_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Database", menu=db_menu)
        db_menu.add_command(label="Unified Dashboard", command=self._show_unified_dashboard)
        db_menu.add_separator()
        db_menu.add_command(label="Fix Database Schema", command=self._fix_database_schema)
        db_menu.add_command(label="Schema Inspector", command=self._show_schema_inspector)
        
        # Import/Export menu
        impexp_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Import/Export", menu=impexp_menu)
        impexp_menu.add_command(label="Import CSV to Table", command=self._show_import_dialog)
        impexp_menu.add_command(label="Export Data to CSV", command=self._show_export_dialog)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Fix Database Schema", command=self._fix_database_schema)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)
        
        # Add Dashboard menu
        dashboard_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Dashboards", menu=dashboard_menu)
        
        dashboard_menu.add_command(label="Unified Dashboard", command=self._show_unified_dashboard)
        
    def _try_auto_connect(self):
        """Try to automatically connect using environment variables"""
        # Get database connection params from .env file
        host = os.getenv("DB_HOST", "localhost")
        port_str = os.getenv("DB_PORT", "5432")
        db_name = os.getenv("DB_NAME", "")
        username = os.getenv("DB_USER", "postgres")
        password = os.getenv("DB_PASSWORD", "")
        
        # Only try to connect if we have a database name
        if db_name:
            try:
                # Convert port to integer
                port = int(port_str)
                
                logger.info(f"Attempting auto-connect to {db_name} on {host}:{port}")
                self.status_var.set(f"Connecting to {db_name}...")
                self.root.update()
                
                # Store tables before validation for comparison
                if hasattr(self.db_manager, 'tables'):
                    self.db_manager.tables_before_validation = self.db_manager.tables.copy()
                else:
                    self.db_manager.tables_before_validation = []
                
                # Connect to the database
                success, message = self.db_manager.connect_to_database(db_name, host, port, username, password)
                
                if success:
                    self.status_var.set(f"Connected to {db_name}")
                    logger.info(f"Auto-connected to database: {db_name}")
                    
                    # Automatically validate and fix schema issues
                    self._validate_and_fix_database_schema()
                    
                    # Show the unified dashboard
                    self._show_unified_dashboard()
                else:
                    self.status_var.set("Connection failed")
                    logger.warning(f"Auto-connect failed: {message}")
                    messagebox.showwarning("Connection Failed", message)
                    
            except ValueError:
                logger.error(f"Invalid port in environment variable: {port_str}")
            except Exception as e:
                logger.error(f"Error in auto-connect: {str(e)}")
                messagebox.showerror("Connection Error", str(e))

    def _validate_and_fix_database_schema(self):
        """Automatically validate and fix database schema issues"""
        try:
            self.status_var.set("Validating database schema...")
            self.root.update()
            
            # Check and fix schema for core tables
            tables_to_check = ['invoices', 'vendors', 'funds']
            schema_results = {}
            fixes_applied = False
            conversions_performed = []
            
            for table in tables_to_check:
                # Check if table exists, create if missing
                if not self.db_manager.schema_validator.check_table_exists(table, create_if_missing=True):
                    if table not in self.db_manager.tables:
                        # New table was created
                        fixes_applied = True
                        logger.info(f"Created missing {table} table")
                
                # Update tables list if we created any
                self.db_manager._fetch_tables()
                
                # Only continue if the table exists
                if table in self.db_manager.tables:
                    # Check for missing columns
                    column_result = self.db_manager.schema_validator.validate_table(table, auto_fix=True)
                    if not column_result['valid']:
                        fixes_applied = True
                        logger.info(f"Added missing columns to {table}")
                    
                    # Check for and fix type mismatches
                    type_result = self.db_manager.schema_validator.validate_and_fix_column_types(table)
                    if type_result.get('fixed', False):
                        fixes_applied = True
                        logger.info(f"Fixed column types in {table}")
                        if 'fixed_columns' in type_result and type_result['fixed_columns']:
                            fixed_cols = ', '.join(type_result['fixed_columns'])
                            logger.info(f"Fixed columns in {table}: {fixed_cols}")
                    
                    schema_results[table] = {
                        'columns': column_result,
                        'types': type_result
                    }
            
            # Check if any type conversions were performed
            type_conversions = []
            if (hasattr(self.db_manager.schema_validator, 'type_conversions_performed') and 
                self.db_manager.schema_validator.type_conversions_performed):
                type_conversions = self.db_manager.schema_validator.type_conversions_performed
                if type_conversions:
                    fixes_applied = True
                    conversions_performed = type_conversions
            
            # Show a message if fixes were applied
            if fixes_applied:
                # Build a detailed message about what was fixed
                message = "The following automatic fixes were applied to your database:\n\n"
                
                # Any tables created
                created_tables = [table for table in tables_to_check if table in self.db_manager.tables 
                                 and not table in self.db_manager.tables_before_validation]
                if created_tables:
                    message += "Tables created:\n"
                    for table in created_tables:
                        message += f"- {table}\n"
                    message += "\n"
                    
                # Any columns added
                columns_added = []
                for table, result in schema_results.items():
                    if 'columns' in result and not result['columns']['valid'] and 'missing_columns' in result['columns']:
                        for col in result['columns']['missing_columns']:
                            columns_added.append(f"{table}.{col['name']} ({col['type']})")
                
                if columns_added:
                    message += "Columns added:\n"
                    for col in columns_added:
                        message += f"- {col}\n"
                    message += "\n"
                
                # Any type conversions
                if conversions_performed:
                    message += "Column types fixed:\n"
                    for conv in conversions_performed:
                        message += f"- {conv['table']}.{conv['column']}: {conv['from_type']} → {conv['to_type']}\n"
                
                messagebox.showinfo("Database Schema Fixed", message)
            
            # Update status
            self.status_var.set("Ready")
            
        except Exception as e:
            logger.error(f"Error validating and fixing database schema: {str(e)}")
            self.status_var.set(f"Error: {str(e)}")
        
    def _connect_database(self):
        """Connect to the database"""
        try:
            # Show connection dialog
            dialog = tk.Toplevel(self.root)
            dialog.title("Connect to Database")
            dialog.geometry("400x250")
            dialog.configure(background=self.bg_dark)
            dialog.transient(self.root)
            dialog.grab_set()
            
            frame = ttk.Frame(dialog, padding="20")
            frame.pack(fill=tk.BOTH, expand=True)
            
            # Add header with gradient effect
            header_frame = tk.Frame(frame, height=40, bg=self.bg_dark)
            header_frame.pack(fill=tk.X, pady=(0, 15))
            
            ttk.Label(header_frame, text="Database Connection", 
                    font=(self.font_family, 14, 'bold')).pack(anchor=tk.W)
            
            # Connection parameters with improved styling
            param_frame = ttk.Frame(frame)
            param_frame.pack(fill=tk.X, pady=5)
            
            # Connection parameters
            ttk.Label(param_frame, text="Host:").pack(anchor=tk.W)
            host_entry = ttk.Entry(param_frame, font=(self.font_family, 10))
            host_entry.pack(fill=tk.X, pady=(0, 10))
            host_entry.insert(0, "localhost")
            
            ttk.Label(param_frame, text="Port:").pack(anchor=tk.W)
            port_entry = ttk.Entry(param_frame, font=(self.font_family, 10))
            port_entry.pack(fill=tk.X, pady=(0, 10))
            port_entry.insert(0, "5432")
            
            ttk.Label(param_frame, text="Database:").pack(anchor=tk.W)
            db_entry = ttk.Entry(param_frame, font=(self.font_family, 10))
            db_entry.pack(fill=tk.X, pady=(0, 10))
            
            ttk.Label(param_frame, text="Username:").pack(anchor=tk.W)
            user_entry = ttk.Entry(param_frame, font=(self.font_family, 10))
            user_entry.pack(fill=tk.X, pady=(0, 10))
            user_entry.insert(0, "postgres")
            
            ttk.Label(param_frame, text="Password:").pack(anchor=tk.W)
            pass_entry = ttk.Entry(param_frame, show="•", font=(self.font_family, 10))
            pass_entry.pack(fill=tk.X, pady=(0, 10))
            
            # Button frame
            button_frame = ttk.Frame(frame)
            button_frame.pack(fill=tk.X, pady=(15, 0))
            
            def connect():
                """Connect to database"""
                try:
                    # Get connection parameters
                    host = host_entry.get()
                    port = int(port_entry.get())  # Convert to integer
                    database = db_entry.get()
                    username = user_entry.get()
                    password = pass_entry.get()
                    
                    # Connect to database
                    success, message = self.db_manager.connect_to_database(database, host, port, username, password)
                    
                    # Update status
                    if success:
                        self.status_var.set(f"Connected to {database}")
                        dialog.destroy()
                        messagebox.showinfo("Success", message)
                        
                        # Show the unified dashboard
                        self._show_unified_dashboard()
                    else:
                        messagebox.showerror("Connection Error", message)
                    
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to connect to database: {str(e)}")
            
            # Add styled buttons
            ttk.Button(button_frame, text="Connect", style="Accent.TButton", 
                     command=connect).pack(side=tk.RIGHT, padx=5)
            ttk.Button(button_frame, text="Cancel", 
                     command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
            
            # Set focus to first field
            host_entry.focus_set()
            
            # Make Enter key trigger connect
            dialog.bind("<Return>", lambda event: connect())
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to show connection dialog: {str(e)}")
            
    def _show_invoice_dashboard(self):
        """Open the invoice dashboard"""
        try:
            # Create a new window for the dashboard
            dashboard_window = tk.Toplevel(self.root)
            dashboard_window.title("Invoice Dashboard")
            dashboard_window.geometry("1000x700")
            
            # Create the dashboard
            from finance_assistant.dashboard import InvoiceDashboard
            dashboard = InvoiceDashboard(dashboard_window, self.db_manager)
            
            # Log the action
            logger.info("Invoice dashboard opened")
            
        except Exception as e:
            logger.error(f"Failed to open invoice dashboard: {str(e)}")
            messagebox.showerror("Error", f"Failed to open invoice dashboard: {str(e)}")
            
    def _show_import_dialog(self):
        """Show dialog for importing data from CSV to a database table"""
        if not self.db_manager.is_connected:
            messagebox.showwarning("Warning", "Please connect to a database first")
            return
            
        # Create dialog window
        dialog = tk.Toplevel(self.root)
        dialog.title("Import Data from CSV")
        dialog.geometry("500x320")
        dialog.configure(background=self.bg_dark)
        
        # Create main frame
        main_frame = ttk.Frame(dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Target table
        ttk.Label(main_frame, text="Target Table:").pack(anchor=tk.W)
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.X, pady=(0, 10))
        
        table_var = tk.StringVar()
        table_combo = ttk.Combobox(table_frame, textvariable=table_var, width=30)
        table_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Fetch existing tables
        self.db_manager._fetch_tables()
        table_combo['values'] = sorted(self.db_manager.tables)
        
        def refresh_tables():
            self.db_manager._fetch_tables()
            table_combo['values'] = sorted(self.db_manager.tables)
            
        ttk.Button(table_frame, text="Refresh", command=refresh_tables).pack(side=tk.RIGHT, padx=(5, 0))
        
        # Create new table checkbox
        create_table_var = tk.BooleanVar(value=False)
        create_table_check = ttk.Checkbutton(main_frame, text="Create new table if not exists", variable=create_table_var)
        create_table_check.pack(anchor=tk.W, pady=(0, 10))
        
        # New table name entry (initially hidden)
        new_table_frame = ttk.Frame(main_frame)
        
        ttk.Label(new_table_frame, text="New Table Name:").pack(side=tk.LEFT, padx=(0, 10))
        new_table_entry = ttk.Entry(new_table_frame, width=30)
        new_table_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Function to toggle table input
        def toggle_table_input():
            if create_table_var.get():
                # Show new table entry
                new_table_frame.pack(fill=tk.X, pady=5)
            else:
                # Hide new table entry
                new_table_frame.pack_forget()
        
        # Bind checkbox to toggle function
        create_table_check.config(command=toggle_table_input)
        
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
        
        # Options frame
        options_frame = ttk.LabelFrame(main_frame, text="Import Options")
        options_frame.pack(fill=tk.X, pady=(0, 10))
        
        # CSV Options
        ttk.Label(options_frame, text="Delimiter:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        delimiter_var = tk.StringVar(value=",")
        delimiter_combo = ttk.Combobox(options_frame, textvariable=delimiter_var, values=[",", ";", "\\t", "|"], width=5)
        delimiter_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Has header row
        header_var = tk.BooleanVar(value=True)
        header_check = ttk.Checkbutton(options_frame, text="CSV has header row", variable=header_var)
        header_check.grid(row=1, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
        
        # Smart Mapping option
        smart_map_var = tk.BooleanVar(value=True)
        smart_map_check = ttk.Checkbutton(options_frame, text="Use smart column mapping", variable=smart_map_var)
        smart_map_check.grid(row=2, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
        
        # Auto-fix schema
        auto_fix_var = tk.BooleanVar(value=True)
        auto_fix_check = ttk.Checkbutton(options_frame, text="Auto-fix schema issues", variable=auto_fix_var)
        auto_fix_check.grid(row=3, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
        
        # Mode selection (append or replace)
        ttk.Label(options_frame, text="Import Mode:").grid(row=0, column=2, sticky=tk.W, padx=(15, 5), pady=2)
        mode_var = tk.StringVar(value="append")
        mode_combo = ttk.Combobox(options_frame, textvariable=mode_var, values=["append", "replace"], width=10)
        mode_combo.grid(row=0, column=3, sticky=tk.W, padx=5, pady=2)
        
        def import_data():
            """Start the CSV import process"""
            # Check required fields
            if not file_path.get():
                messagebox.showerror("Error", "Please select a CSV file", parent=dialog)
                return
            
            # Determine table name
            if create_table_var.get():
                table = new_table_entry.get().strip()
                if not table:
                    messagebox.showerror("Error", "Please enter a name for the new table", parent=dialog)
                    return
            else:
                table = table_var.get().strip()
                if not table:
                    messagebox.showerror("Error", "Please select a target table", parent=dialog)
                    return
            
            # Close the dialog
            dialog.destroy()
            
            # Prepare options
            import_options = {
                'delimiter': delimiter_var.get() if delimiter_var.get() != "\\t" else "\t",
                'has_header': header_var.get(),
                'auto_fix': auto_fix_var.get(),
                'mode': mode_var.get()
            }
            
            # Choose import method based on user selection
            if smart_map_var.get():
                # Use smart mapping
                self._show_smart_import_dialog(file_path.get(), table)
            else:
                # Use traditional import with progress dialog
                self._show_import_progress(file_path.get(), table, import_options)
        
        # Add buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        cancel_button = ttk.Button(button_frame, text="Cancel", command=dialog.destroy)
        cancel_button.pack(side=tk.RIGHT, padx=5)
        
        import_button = ttk.Button(button_frame, text="Import Data", command=import_data,
                                style="Accent.TButton")
        import_button.pack(side=tk.RIGHT, padx=5)
        
        # Make dialog modal
        dialog.transient(self.root)
        dialog.grab_set()
        self.root.wait_window(dialog)
    
    def _show_export_dialog(self):
        """Show dialog for exporting data to CSV"""
        if not self.db_manager.is_connected:
            messagebox.showwarning("Warning", "Please connect to a database first")
            return
            
        # Create dialog window
        dialog = tk.Toplevel(self.root)
        dialog.title("Export Data to CSV")
        dialog.geometry("500x320")
        
        # Create main frame
        main_frame = ttk.Frame(dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Source table selection
        ttk.Label(main_frame, text="Source Table:").pack(anchor=tk.W)
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.X, pady=(0, 10))
        
        table_var = tk.StringVar()
        table_combo = ttk.Combobox(table_frame, textvariable=table_var, width=30)
        table_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Fetch existing tables
        self.db_manager._fetch_tables()
        table_combo['values'] = sorted(self.db_manager.tables)
        
        def refresh_tables():
            self.db_manager._fetch_tables()
            table_combo['values'] = sorted(self.db_manager.tables)
            
        ttk.Button(table_frame, text="Refresh", command=refresh_tables).pack(side=tk.RIGHT, padx=(5, 0))
        
        # Custom query option
        ttk.Label(main_frame, text="SQL Query (Optional):").pack(anchor=tk.W, pady=(10, 0))
        query_text = tk.Text(main_frame, height=5)
        query_text.pack(fill=tk.X, pady=(0, 10))
        
        # Output file selection
        ttk.Label(main_frame, text="Output CSV File:").pack(anchor=tk.W)
        file_frame = ttk.Frame(main_frame)
        file_frame.pack(fill=tk.X, pady=(0, 10))
        
        file_path = tk.StringVar()
        file_entry = ttk.Entry(file_frame, textvariable=file_path)
        file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        def browse_file():
            filename = filedialog.asksaveasfilename(
                title="Save As",
                defaultextension=".csv",
                filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
            )
            if filename:
                file_path.set(filename)
        
        ttk.Button(file_frame, text="Browse", command=browse_file).pack(side=tk.RIGHT, padx=(5, 0))
        
        # Export options
        options_frame = ttk.LabelFrame(main_frame, text="Export Options")
        options_frame.pack(fill=tk.X, pady=(0, 10))
        
        # CSV Options
        ttk.Label(options_frame, text="Delimiter:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        delimiter_var = tk.StringVar(value=",")
        delimiter_combo = ttk.Combobox(options_frame, textvariable=delimiter_var, values=[",", ";", "\\t", "|"], width=5)
        delimiter_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Include header row
        header_var = tk.BooleanVar(value=True)
        header_check = ttk.Checkbutton(options_frame, text="Include header row", variable=header_var)
        header_check.grid(row=1, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
        
        def export_data():
            """Export data to CSV"""
            import pandas as pd
            table = table_var.get().strip()
            custom_query = query_text.get("1.0", tk.END).strip()
            output_file = file_path.get()
            
            if not output_file:
                messagebox.showerror("Error", "Please specify an output file")
                return
                
            if not table and not custom_query:
                messagebox.showerror("Error", "Please select a table or provide a SQL query")
                return
            
            try:
                # Determine the query to use
                if custom_query:
                    query = custom_query
                else:
                    query = f"SELECT * FROM {table}"
                
                # Execute the query and get results as DataFrame
                df = self.db_manager.db.query_to_dataframe(query)
                
                if df.empty:
                    messagebox.showwarning("Warning", "No data to export")
                    return
                
                # Export to CSV
                delimiter = delimiter_var.get()
                if delimiter == "\\t":  # Handle tab character
                    delimiter = "\t"
                    
                df.to_csv(output_file, index=False, header=header_var.get(), sep=delimiter)
                
                messagebox.showinfo("Success", f"Data exported successfully to {output_file}")
                dialog.destroy()
                
            except Exception as e:
                logger.error(f"Failed to export data: {str(e)}")
                messagebox.showerror("Error", f"Failed to export data: {str(e)}")
        
        # Export button
        ttk.Button(main_frame, text="Export Data", command=export_data).pack(fill=tk.X, pady=(10, 0))
    
    def _show_about(self):
        """Show the about dialog"""
        # Create dialog window with dark theme
        dialog = tk.Toplevel(self.root)
        dialog.title("About")
        dialog.geometry("400x300")
        dialog.configure(background=self.bg_dark)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Create frame
        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Create logo/icon area with gradient background
        logo_frame = tk.Frame(frame, width=360, height=60, bg=self.bg_dark)
        logo_frame.pack(pady=(0, 15))
        logo_frame.pack_propagate(False)
        
        # Create canvas for gradient
        canvas = tk.Canvas(logo_frame, bg=self.bg_dark, highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)
        
        # Draw gradient background
        for y in range(60):
            # Calculate color for gradient (purple to dark purple)
            r1, g1, b1 = 126, 87, 194  # #7e57c2
            r2, g2, b2 = 98, 0, 234    # #6200ea
            
            r = int(r1 + (r2-r1) * (y/60))
            g = int(g1 + (g2-g1) * (y/60))
            b = int(b1 + (b2-b1) * (y/60))
            
            color = f'#{r:02x}{g:02x}{b:02x}'
            canvas.create_line(0, y, 360, y, fill=color)
        
        # Add title text
        canvas.create_text(180, 30, text="Financial Database Assistant", 
                         fill="white", font=(self.font_family, 16, 'bold'))
        
        # Add content
        content_frame = ttk.Frame(frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Version info
        ttk.Label(content_frame, text="Version 1.0.0", 
                font=(self.font_family, 12)).pack(pady=(0, 15))
        
        # Description
        description = (
            "A simplified tool for managing invoice data "
            "with a user-friendly interface and LLM-powered search capabilities."
        )
        
        desc_label = ttk.Label(content_frame, text=description, wraplength=340, 
                            justify=tk.CENTER, font=(self.font_family, 10))
        desc_label.pack(fill=tk.X, pady=10)
        
        # Features list
        features_text = (
            "• Invoice database management\n"
            "• Natural language search powered by LLM\n"
            "• CSV import and export\n"
            "• Interactive dashboards\n"
            "• Dark theme UI"
        )
        
        ttk.Label(content_frame, text=features_text, justify=tk.LEFT,
                font=(self.font_family, 10)).pack(fill=tk.X, pady=10)
        
        # Close button
        ttk.Button(content_frame, text="Close", command=dialog.destroy,
                 style="Accent.TButton", width=15).pack(pady=(15, 0))
    
    def _show_llm_dashboard(self):
        """Show the LLM-powered invoice dashboard"""
        try:
            if not self.db_manager.is_connected:
                messagebox.showwarning("Warning", "Please connect to a database first")
                return
            
            # Import the LLM dashboard class
            from finance_assistant.llm_dashboard import LLMInvoiceDashboard
            
            # Create and show the LLM dashboard
            dashboard = LLMInvoiceDashboard(self.root, self.db_manager, self.llm_client)
            dashboard.show()
            
            logger.info("LLM Invoice dashboard opened")
            
        except Exception as e:
            logger.error(f"Failed to show LLM invoice dashboard: {str(e)}")
            messagebox.showerror("Error", f"Failed to show LLM dashboard: {str(e)}")
    
    def _fix_database_schema(self):
        """Fix database schema issues automatically"""
        try:
            if not self.db_manager.is_connected:
                messagebox.showwarning("Warning", "Please connect to a database first")
                return
            
            # Create confirmation dialog
            if not messagebox.askyesno("Confirm", 
                                      "This will automatically detect and fix database schema issues, including:\n\n"
                                      "- Adding missing required columns\n"
                                      "- Converting text columns to proper date, numeric, and integer types\n"
                                      "- Fixing case sensitivity issues\n\n"
                                      "Data will be preserved where possible. Do you want to proceed?"):
                return
            
            # Set status
            self.status_var.set("Analyzing database schema...")
            self.root.update()
            
            # Create progress dialog
            progress_window = tk.Toplevel(self.root)
            progress_window.title("Database Schema Fix")
            progress_window.geometry("400x250")
            progress_window.configure(background=self.bg_dark)
            progress_window.transient(self.root)
            progress_window.grab_set()
            
            # Create content frame
            frame = ttk.Frame(progress_window, padding="20")
            frame.pack(fill=tk.BOTH, expand=True)
            
            # Add heading
            ttk.Label(frame, text="Schema Correction Progress", 
                    font=(self.font_family, 14, 'bold')).pack(pady=(0, 15))
            
            # Create status text widget
            status_text = tk.Text(frame, height=10, width=50, 
                                bg=self.bg_light, fg=self.text_color,
                                font=(self.font_family, 10))
            status_text.pack(fill=tk.BOTH, expand=True, pady=10)
            
            # Add scrollbar
            scrollbar = ttk.Scrollbar(status_text, orient=tk.VERTICAL, command=status_text.yview)
            status_text.configure(yscrollcommand=scrollbar.set)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Update function to add status messages
            def update_status(message):
                status_text.configure(state=tk.NORMAL)
                status_text.insert(tk.END, message + "\n")
                status_text.see(tk.END)
                status_text.configure(state=tk.DISABLED)
                self.root.update()
            
            # Show initial message
            update_status("Starting schema analysis...")
            
            # Initialize tables to check
            tables_to_check = ['invoices', 'vendors', 'funds']
            
            # First, ensure all tables exist
            for table in tables_to_check:
                update_status(f"Checking if {table} table exists...")
                if not self.db_manager.schema_validator.check_table_exists(table, create_if_missing=True):
                    update_status(f"⚠️ Failed to create {table} table")
                elif table not in self.db_manager.tables:
                    update_status(f"✓ Created {table} table")
                else:
                    update_status(f"✓ {table} table exists")
            
            # Update tables list after potential table creation
            self.db_manager._fetch_tables()
            
            # Then, fix missing columns and types for each table
            all_fixed = True
            for table in tables_to_check:
                if table in self.db_manager.tables:
                    # Check for missing columns
                    update_status(f"Checking for missing columns in {table}...")
                    column_result = self.db_manager.schema_validator.validate_table(table, auto_fix=True)
                    if column_result['valid']:
                        update_status(f"✓ All required columns exist in {table}")
                    else:
                        update_status(f"⚠️ Column validation failed for {table}: {column_result}")
                        all_fixed = False
                    
                    # Check for and fix type mismatches
                    update_status(f"Checking column types in {table}...")
                    type_result = self.db_manager.schema_validator.validate_and_fix_column_types(table)
                    if type_result['fixed']:
                        update_status(f"✓ All column types are correct in {table}")
                    else:
                        update_status(f"⚠️ Type validation failed for {table}: {type_result}")
                        all_fixed = False
            
            # Report column type conversions
            if hasattr(self.db_manager.schema_validator, 'type_conversions_performed'):
                conversions = self.db_manager.schema_validator.type_conversions_performed
                if conversions:
                    update_status(f"\nPerformed {len(conversions)} column type conversions:")
                    for conv in conversions:
                        update_status(f"• Converted {conv['table']}.{conv['column']} from {conv['from_type']} to {conv['to_type']}")
            
            # Update final status
            self.status_var.set("Schema correction completed")
            
            # Add close button
            ttk.Button(frame, text="Close", command=progress_window.destroy,
                     style="Accent.TButton").pack(pady=(15, 0))
            
            # Show result message based on success
            if all_fixed:
                messagebox.showinfo("Success", "Database schema has been fixed successfully.")
            else:
                messagebox.showwarning("Partial Success", 
                                      "Some schema issues were fixed, but others remain.\n"
                                      "See the progress window for details.")
            
        except Exception as e:
            logger.error(f"Failed to fix database schema: {str(e)}")
            self.status_var.set("Error fixing schema")
            messagebox.showerror("Error", f"Failed to fix database schema: {str(e)}")
    
    def _show_schema_inspector(self):
        """Show the database schema inspector dialog"""
        try:
            if not self.db_manager.is_connected:
                messagebox.showwarning("Warning", "Please connect to a database first")
                return
                
            # Create inspector window
            inspector = tk.Toplevel(self.root)
            inspector.title("Database Schema Inspector")
            inspector.geometry("700x500")
            inspector.configure(background=self.bg_dark)
            inspector.transient(self.root)
            
            # Create main frame
            frame = ttk.Frame(inspector, padding="10")
            frame.pack(fill=tk.BOTH, expand=True)
            
            # Add header with gradient
            header_frame = tk.Frame(frame, height=40, bg=self.bg_dark)
            header_frame.pack(fill=tk.X, pady=(0, 15))
            
            ttk.Label(header_frame, text="Database Schema Inspector", 
                    font=(self.font_family, 14, 'bold')).pack(anchor=tk.W)
            
            # Add tabs for different tables
            notebook = ttk.Notebook(frame)
            notebook.pack(fill=tk.BOTH, expand=True)
            
            # Query to get tables
            tables_query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            result = self.db_manager.db.execute_query(tables_query)
            
            if 'error' in result and result['error']:
                ttk.Label(frame, text=f"Error: {result['error']}").pack()
                return
            
            # Add option to fix all tables
            fix_all_frame = ttk.Frame(frame)
            fix_all_frame.pack(fill=tk.X, pady=10)
            
            fix_all_button = ttk.Button(fix_all_frame, text="Fix All Tables", 
                                      command=lambda: self._fix_all_tables(inspector),
                                      style="Accent.TButton")
            fix_all_button.pack(side=tk.RIGHT, padx=5)
            
            # Run analysis on all tables
            analyze_all_button = ttk.Button(fix_all_frame, text="Analyze All Tables", 
                                         command=lambda: self._analyze_all_tables(inspector))
            analyze_all_button.pack(side=tk.RIGHT, padx=5)
            
            # Create a tab for each table
            for table_row in result['rows']:
                table_name = table_row[0]
                
                # Create tab
                tab = ttk.Frame(notebook)
                notebook.add(tab, text=table_name)
                
                # Get table columns
                columns_query = """
                SELECT column_name, data_type, udt_name, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = %s
                ORDER BY ordinal_position
                """
                result = self.db_manager.db.execute_query(columns_query, (table_name,))
                
                if 'error' in result and result['error']:
                    ttk.Label(tab, text=f"Error: {result['error']}").pack()
                    continue
                
                # Create treeview for columns
                columns_tree = ttk.Treeview(tab, columns=("name", "type", "underlying_type", "nullable"), show="headings")
                columns_tree.heading("name", text="Column Name")
                columns_tree.heading("type", text="Data Type")
                columns_tree.heading("underlying_type", text="UDT Name")
                columns_tree.heading("nullable", text="Nullable")
                
                columns_tree.column("name", width=150)
                columns_tree.column("type", width=150)
                columns_tree.column("underlying_type", width=100)
                columns_tree.column("nullable", width=80)
                
                columns_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
                
                # Add scrollbar
                scrollbar = ttk.Scrollbar(tab, orient=tk.VERTICAL, command=columns_tree.yview)
                columns_tree.configure(yscrollcommand=scrollbar.set)
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                
                # Add columns data
                for i, col_row in enumerate(result['rows']):
                    # Check if this type might need conversion
                    col_name = col_row[0]
                    data_type = col_row[1]
                    udt_name = col_row[2]
                    
                    # Identify potential type issues
                    tag = "normal"
                    if data_type.lower() in ('text', 'character varying', 'varchar') and ('date' in col_name.lower()):
                        tag = "warning"
                    elif data_type.lower() in ('text', 'character varying', 'varchar') and ('amount' in col_name.lower() or 'price' in col_name.lower()):
                        tag = "warning"
                    
                    # Alternate row colors
                    if i % 2 == 0:
                        tag = f"{tag}_even" if tag != "normal" else "even"
                    else:
                        tag = f"{tag}_odd" if tag != "normal" else "odd"
                    
                    columns_tree.insert('', tk.END, values=(col_row[0], col_row[1], col_row[2], col_row[3]), tags=(tag,))
                
                # Configure row colors
                columns_tree.tag_configure("odd", background=self.bg_medium)
                columns_tree.tag_configure("even", background=self.bg_light)
                columns_tree.tag_configure("warning_odd", background="#8B4000", foreground="white")  # Dark orange for warnings
                columns_tree.tag_configure("warning_even", background="#A55000", foreground="white")  # Lighter orange for warnings
                
                # Add buttons for this table
                button_frame = ttk.Frame(tab)
                button_frame.pack(fill=tk.X, pady=10)
                
                fix_button = ttk.Button(button_frame, text="Fix Schema Types", 
                                      command=lambda t=table_name: self._fix_table_schema(t, inspector),
                                      style="Accent.TButton")
                fix_button.pack(side=tk.RIGHT, padx=5)
                
                analyze_button = ttk.Button(button_frame, text="Analyze Data", 
                                         command=lambda t=table_name: self._analyze_table_data(t, inspector))
                analyze_button.pack(side=tk.RIGHT, padx=5)
            
            # Add status bar at bottom
            status_var = tk.StringVar(value="Ready")
            status_bar = ttk.Label(frame, textvariable=status_var, anchor=tk.W)
            status_bar.pack(fill=tk.X, side=tk.BOTTOM, pady=5)
            
        except Exception as e:
            logger.error(f"Error showing schema inspector: {str(e)}")
            messagebox.showerror("Error", f"Failed to open schema inspector: {str(e)}")
    
    def _show_smart_import_dialog(self, csv_file, table_name):
        """Show dialog with intelligent column mapping suggestions
        
        Args:
            csv_file: Path to the CSV file
            table_name: Target table name
        """
        # Analyze CSV and get mapping suggestions
        suggested_mapping = self.db_manager.import_csv_with_smart_mapping(csv_file, table_name)
        
        if 'error' in suggested_mapping:
            messagebox.showerror("Error", f"Failed to analyze CSV: {suggested_mapping['error']}")
            return
        
        # Create dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Smart CSV Import")
        dialog.geometry("800x600")
        dialog.configure(bg=self.bg_dark)
        
        # Header
        header_frame = tk.Frame(dialog, bg=self.bg_dark)
        header_frame.pack(fill=tk.X, padx=15, pady=15)
        
        header_label = tk.Label(header_frame, 
                              text="Smart Column Mapping", 
                              font=(self.font_family, 16, "bold"),
                              bg=self.bg_dark, fg=self.text_color)
        header_label.pack(side=tk.LEFT)
        
        # Main content
        content_frame = ttk.Frame(dialog)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)
        
        # Mapping section
        mapping_frame = ttk.LabelFrame(content_frame, text="Column Mapping")
        mapping_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Create scrollable frame for mappings
        canvas = tk.Canvas(mapping_frame, bg=self.bg_medium, highlightthickness=0)
        scrollbar = ttk.Scrollbar(mapping_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill=tk.Y)
        
        # Add headers
        header_frame = ttk.Frame(scrollable_frame)
        header_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(header_frame, text="CSV Column", width=25, font=(self.font_family, 10, "bold")).grid(row=0, column=0, padx=5)
        ttk.Label(header_frame, text="Database Column", width=25, font=(self.font_family, 10, "bold")).grid(row=0, column=1, padx=5)
        ttk.Label(header_frame, text="Action", width=20, font=(self.font_family, 10, "bold")).grid(row=0, column=2, padx=5)
        
        # Store mapping variables
        mapping_vars = {}
        action_vars = {}
        
        # Add rows for each mapping
        for i, (csv_col, db_col) in enumerate(suggested_mapping['mappings'].items()):
            row_frame = ttk.Frame(scrollable_frame)
            row_frame.pack(fill=tk.X, padx=5, pady=3)
            
            # CSV column label (with sample data)
            csv_label = ttk.Label(row_frame, text=csv_col, width=25)
            csv_label.grid(row=0, column=0, padx=5)
            
            # Database column dropdown
            mapping_vars[csv_col] = tk.StringVar(value=db_col if db_col else "-- Create New Column --")
            
            # All possible database columns plus "create new"
            db_options = ["-- Create New Column --"] + suggested_mapping['existing_columns']
            
            db_dropdown = ttk.Combobox(row_frame, textvariable=mapping_vars[csv_col], 
                                     values=db_options, width=25)
            db_dropdown.grid(row=0, column=1, padx=5)
            
            # Action radio buttons
            action_frame = ttk.Frame(row_frame)
            action_frame.grid(row=0, column=2, padx=5)
            
            # Default action: map if we found a match, create if it's new
            is_new = db_col not in suggested_mapping['existing_columns']
            default_action = "create" if is_new else "map"
            
            action_vars[csv_col] = tk.StringVar(value=default_action)
            
            ttk.Radiobutton(action_frame, text="Map", value="map", 
                          variable=action_vars[csv_col]).pack(side=tk.LEFT, padx=5)
            ttk.Radiobutton(action_frame, text="Create New", value="create", 
                          variable=action_vars[csv_col]).pack(side=tk.LEFT, padx=5)
            ttk.Radiobutton(action_frame, text="Skip", value="skip", 
                          variable=action_vars[csv_col]).pack(side=tk.LEFT, padx=5)
        
        # Add info about new columns being created
        if suggested_mapping['new_columns']:
            new_cols_frame = ttk.LabelFrame(content_frame, text="New Columns to Create")
            new_cols_frame.pack(fill=tk.X, pady=10)
            
            for col, col_type in suggested_mapping['new_columns'].items():
                col_frame = ttk.Frame(new_cols_frame)
                col_frame.pack(fill=tk.X, padx=5, pady=3)
                
                ttk.Label(col_frame, text=col, width=25).pack(side=tk.LEFT, padx=5)
                ttk.Label(col_frame, text=col_type, width=25).pack(side=tk.LEFT, padx=5)
        
        # Preview section
        preview_frame = ttk.LabelFrame(content_frame, text="Data Preview")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Create tree view for preview
        preview_tree = ttk.Treeview(preview_frame)
        preview_tree["columns"] = suggested_mapping['csv_headers']
        preview_tree["show"] = "headings"
        
        # Set column headings
        for header in suggested_mapping['csv_headers']:
            preview_tree.heading(header, text=header)
            preview_tree.column(header, width=100)
        
        # Add sample data
        for row in suggested_mapping['sample_rows']:
            if len(row) == len(suggested_mapping['csv_headers']):  # Ensure complete row
                preview_tree.insert("", tk.END, values=row)
        
        # Add scrollbars
        preview_y = ttk.Scrollbar(preview_frame, orient="vertical", command=preview_tree.yview)
        preview_x = ttk.Scrollbar(preview_frame, orient="horizontal", command=preview_tree.xview)
        preview_tree.configure(yscrollcommand=preview_y.set, xscrollcommand=preview_x.set)
        
        preview_y.pack(side=tk.RIGHT, fill=tk.Y)
        preview_x.pack(side=tk.BOTTOM, fill=tk.X)
        preview_tree.pack(fill=tk.BOTH, expand=True)
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=15, pady=15)
        
        # Auto-fix button
        auto_fix_button = ttk.Button(
            button_frame, 
            text="Auto-Fix All Issues",
            command=lambda: self._auto_fix_and_import(dialog, csv_file, table_name, suggested_mapping)
        )
        auto_fix_button.pack(side=tk.LEFT, padx=5)
        
        # Help button
        help_button = ttk.Button(
            button_frame, 
            text="Help",
            command=lambda: messagebox.showinfo(
                "Smart Import Help", 
                "This tool automatically maps CSV columns to database fields and identifies new columns that need to be created.\n\n"
                "For each CSV column, you can:\n"
                "• Map to an existing database column\n"
                "• Create a new column in the database\n"
                "• Skip the column entirely\n\n"
                "The 'Auto-Fix All Issues' button will automatically add missing columns and import your data using the best mapping.",
                parent=dialog
            )
        )
        help_button.pack(side=tk.LEFT, padx=5)
        
        # Cancel button
        cancel_button = ttk.Button(button_frame, text="Cancel", command=dialog.destroy)
        cancel_button.pack(side=tk.RIGHT, padx=5)
        
        # Import button
        import_button = ttk.Button(
            button_frame, 
            text="Import with Selected Mapping",
            command=lambda: self._execute_mapped_import_from_ui(
                dialog, csv_file, table_name, mapping_vars, action_vars, suggested_mapping
            )
        )
        import_button.pack(side=tk.RIGHT, padx=5)
        
        # Make dialog modal
        dialog.transient(self.root)
        dialog.grab_set()
        self.root.wait_window(dialog)

    def _auto_fix_and_import(self, dialog, csv_file, table_name, mapping_info):
        """Automatically fix all issues and import the data
        
        Args:
            dialog: The parent dialog
            csv_file: Path to the CSV file
            table_name: Target table name
            mapping_info: Mapping information dictionary
        """
        try:
            # Show progress dialog
            progress = tk.Toplevel(dialog)
            progress.title("Fixing Issues")
            progress.geometry("400x150")
            progress.configure(bg=self.bg_dark)
            
            # Center dialog
            progress.update_idletasks()
            x = (progress.winfo_screenwidth() // 2) - (progress.winfo_width() // 2)
            y = (progress.winfo_screenheight() // 2) - (progress.winfo_height() // 2)
            progress.geometry('{}x{}+{}+{}'.format(progress.winfo_width(), progress.winfo_height(), x, y))
            
            # Progress label
            status_var = tk.StringVar(value="Analyzing table structure...")
            status_label = tk.Label(progress, textvariable=status_var, 
                                  bg=self.bg_dark, fg=self.text_color, wraplength=380)
            status_label.pack(pady=20)
            
            progress_bar = ttk.Progressbar(progress, mode="indeterminate", length=360)
            progress_bar.pack(pady=10)
            progress_bar.start(10)
            
            progress.update()
            
            # Run in separate thread
            def fix_and_import_thread():
                try:
                    # Step 1: Create missing columns
                    status_var.set("Adding missing columns to the database...")
                    progress.update()
                    
                    for col, col_type in mapping_info['new_columns'].items():
                        # Add column to database
                        self.db_manager.add_column_to_table(table_name, col, col_type)
                    
                    # Step 2: Create final mapping dictionary
                    final_mapping = {
                        csv_col: db_col 
                        for csv_col, db_col in mapping_info['mappings'].items() 
                        if db_col  # Skip any unmapped columns
                    }
                    
                    # Step 3: Execute import
                    status_var.set("Importing data...")
                    progress.update()
                    
                    result = self.db_manager._execute_mapped_import(csv_file, table_name, final_mapping)
                    
                    # Close progress dialog
                    progress.destroy()
                    
                    # Close mapping dialog
                    dialog.destroy()
                    
                    # Show result
                    if result['success']:
                        messagebox.showinfo(
                            "Import Complete", 
                            f"Successfully imported {result.get('successful_rows', 0)} of {result.get('total_rows', 0)} rows."
                        )
                    else:
                        error_msg = result.get('error', 'Unknown error')
                        messagebox.showerror("Import Failed", f"Failed to import data: {error_msg}")
                
                except Exception as e:
                    progress.destroy()
                    messagebox.showerror("Error", f"Auto-fix failed: {str(e)}", parent=dialog)
            
            threading.Thread(target=fix_and_import_thread, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Error", f"Auto-fix setup failed: {str(e)}", parent=dialog)

    def _execute_mapped_import_from_ui(self, dialog, csv_file, table_name, mapping_vars, action_vars, mapping_info):
        """Execute import using user-selected mappings from UI
        
        Args:
            dialog: The parent dialog
            csv_file: Path to the CSV file
            table_name: Target table name
            mapping_vars: Dictionary of mapping variables
            action_vars: Dictionary of action variables
            mapping_info: Mapping information dictionary
        """
        try:
            # Step 1: Process user selections
            final_mapping = {}
            new_columns = {}
            
            for csv_col, action_var in action_vars.items():
                action = action_var.get()
                if action == "skip":
                    continue  # Skip this column
                    
                db_col = mapping_vars[csv_col].get()
                
                if db_col == "-- Create New Column --" or action == "create":
                    # Create a new column
                    safe_col = re.sub(r'[^a-z0-9_]', '_', csv_col.lower())
                    safe_col = re.sub(r'_+', '_', safe_col).strip('_')
                    
                    # Infer column type if needed
                    col_index = mapping_info['csv_headers'].index(csv_col)
                    col_data = [row[col_index] for row in mapping_info['sample_rows'] if col_index < len(row)]
                    col_type = self.db_manager._infer_column_type(col_data)
                    
                    new_columns[safe_col] = col_type
                    final_mapping[csv_col] = safe_col
                else:
                    # Map to existing column
                    final_mapping[csv_col] = db_col
            
            # Show progress dialog
            progress = tk.Toplevel(dialog)
            progress.title("Importing Data")
            progress.geometry("400x150")
            progress.configure(bg=self.bg_dark)
            
            # Center dialog
            progress.update_idletasks()
            x = (progress.winfo_screenwidth() // 2) - (progress.winfo_width() // 2)
            y = (progress.winfo_screenheight() // 2) - (progress.winfo_height() // 2)
            progress.geometry(f"{progress.winfo_width()}x{progress.winfo_height()}+{x}+{y}")
            
            # Progress content
            status_var = tk.StringVar(value="Preparing import...")
            status_label = tk.Label(progress, textvariable=status_var, 
                                  bg=self.bg_dark, fg=self.text_color, wraplength=380)
            status_label.pack(pady=20)
            
            progress_bar = ttk.Progressbar(progress, mode="indeterminate", length=360)
            progress_bar.pack(pady=10)
            progress_bar.start(10)
            
            progress.update()
            
            # Run import in a separate thread
            def import_thread():
                try:
                    # Step 2: Create new columns if needed
                    if new_columns:
                        status_var.set(f"Creating {len(new_columns)} new columns...")
                        progress.update()
                        
                        for col, col_type in new_columns.items():
                            self.db_manager.add_column_to_table(table_name, col, col_type)
                    
                    # Step 3: Execute the import
                    status_var.set("Importing data...")
                    progress.update()
                    
                    result = self.db_manager._execute_mapped_import(csv_file, table_name, final_mapping)
                    
                    # Close progress dialog
                    progress.destroy()
                    
                    # Close mapping dialog
                    dialog.destroy()
                    
                    # Show result
                    if result['success']:
                        messagebox.showinfo(
                            "Import Complete", 
                            f"Successfully imported {result.get('successful_rows', 0)} of {result.get('total_rows', 0)} rows."
                        )
                        
                        # Refresh UI if needed
                        if hasattr(self, '_show_invoice_dashboard'):
                            self._show_invoice_dashboard()
                    else:
                        messagebox.showerror(
                            "Import Error", 
                            f"Error during import: {result.get('error', 'Unknown error')}"
                        )
                
                except Exception as e:
                    progress.destroy()
                    messagebox.showerror("Error", f"Import failed: {str(e)}", parent=dialog)
            
            threading.Thread(target=import_thread, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to process mapping: {str(e)}", parent=dialog)
    
    def _show_import_progress(self, csv_file, table_name, column_mapping):
        """Show import progress dialog
        
        Args:
            csv_file: Path to the CSV file
            table_name: Target table name
            column_mapping: Dictionary mapping CSV columns to DB columns
        """
        # Create progress dialog
        progress_dialog = tk.Toplevel(self.root)
        progress_dialog.title("Importing Data")
        progress_dialog.geometry("500x300")
        progress_dialog.configure(background=self.bg_dark)
        progress_dialog.transient(self.root)
        
        # Header
        header_label = tk.Label(progress_dialog, 
                              text="Importing CSV Data", 
                              font=(self.font_family, 16, "bold"),
                              bg=self.bg_dark, fg=self.text_color)
        header_label.pack(pady=(20, 10))
        
        # Status text
        status_var = tk.StringVar(value="Preparing to import data...")
        status_label = tk.Label(progress_dialog, textvariable=status_var,
                              bg=self.bg_dark, fg=self.text_color,
                              font=(self.font_family, 10),
                              wraplength=460)
        status_label.pack(pady=5)
        
        # Progress bar
        progress_bar = ttk.Progressbar(progress_dialog, mode="indeterminate", length=460)
        progress_bar.pack(pady=10, padx=20)
        progress_bar.start(10)
        
        # Status details
        details_frame = tk.Frame(progress_dialog, bg=self.bg_dark)
        details_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(5, 20))
        
        details_text = tk.Text(details_frame, height=8, width=50,
                             bg=self.bg_medium, fg=self.text_color,
                             font=(self.font_family, 9))
        details_scroll = ttk.Scrollbar(details_frame, command=details_text.yview)
        details_text.configure(yscrollcommand=details_scroll.set)
        
        details_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        details_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Disable editing
        details_text.config(state=tk.DISABLED)
        
        # Function to add log entries
        def add_log(message):
            details_text.config(state=tk.NORMAL)
            details_text.insert(tk.END, f"{message}\n")
            details_text.see(tk.END)
            details_text.config(state=tk.DISABLED)
            progress_dialog.update()
        
        # Update UI
        progress_dialog.update()
        
        # Function to run import process
        def run_import():
            try:
                # Count rows for progress
                with open(csv_file, 'r', encoding='utf-8-sig') as f:
                    reader = csv.reader(f)
                    next(reader)  # Skip header
                    row_count = sum(1 for _ in reader)
                
                # Get column types
                table_structure = self.db_manager.get_table_structure(table_name)
                column_types = {col['name'].lower(): col['type'].lower() for col in table_structure}
                
                # Update status
                status_var.set(f"Importing {row_count} rows with type conversion...")
                add_log(f"Found {row_count} rows to import into {table_name}")
                
                # List column mappings
                add_log("\nColumn Mappings:")
                for csv_col, db_col in column_mapping.items():
                    col_type = column_types.get(db_col.lower(), "unknown")
                    add_log(f"  • {csv_col} → {db_col} ({col_type})")
                
                # Switch to determinate mode
                progress_bar.stop()
                progress_bar["mode"] = "determinate"
                progress_bar["maximum"] = row_count
                progress_bar["value"] = 0
                
                # Custom value cleaner that updates progress
                def progress_updater(current_row):
                    if current_row % 10 == 0 or current_row == row_count:
                        progress_bar["value"] = current_row
                        percentage = int((current_row / row_count) * 100)
                        status_var.set(f"Importing row {current_row} of {row_count} ({percentage}%)...")
                        progress_dialog.update()
                    
                    if current_row % 100 == 0 or current_row == row_count:
                        add_log(f"Processed {current_row} of {row_count} rows")
                
                # Execute import with progress updates
                result = self.db_manager._execute_mapped_import_with_progress(
                    csv_file, table_name, column_mapping, progress_updater)
                
                # Show final results
                if result['success']:
                    success_count = result.get('successful_rows', 0)
                    percentage = int((success_count / row_count) * 100) if row_count > 0 else 0
                    
                    status_var.set(f"Import complete: {success_count} of {row_count} rows imported ({percentage}%)")
                    add_log(f"\nImport completed successfully!")
                    add_log(f"• Total rows in CSV: {row_count}")
                    add_log(f"• Successfully imported: {success_count}")
                    
                    if success_count < row_count:
                        add_log(f"• Rows with errors: {row_count - success_count}")
                else:
                    error_msg = result.get('error', 'Unknown error')
                    status_var.set(f"Import failed: {error_msg}")
                    add_log(f"\nImport failed: {error_msg}")
                
                # Add close button
                close_button = ttk.Button(progress_dialog, text="Close", command=progress_dialog.destroy)
                close_button.pack(pady=10)
                
            except Exception as e:
                status_var.set(f"Error during import: {str(e)}")
                add_log(f"\nError: {str(e)}")
                
                # Add close button
                close_button = ttk.Button(progress_dialog, text="Close", command=progress_dialog.destroy)
                close_button.pack(pady=10)
        
        # Run import in a separate thread
        threading.Thread(target=run_import, daemon=True).start()
        
        # Make dialog modal
        progress_dialog.grab_set()
        self.root.wait_window(progress_dialog)
    
    def _show_enhanced_invoice_dashboard(self):
        """Open the enhanced invoice dashboard with dynamic year-based totals and SQL library"""
        try:
            # Create a new window for the dashboard
            dashboard_window = tk.Toplevel(self.root)
            dashboard_window.title("Enhanced Invoice Dashboard")
            dashboard_window.geometry("1200x800")
            dashboard_window.minsize(1000, 700)
            
            # Create the dashboard
            from finance_assistant.enhanced_dashboard import EnhancedInvoiceDashboard
            dashboard = EnhancedInvoiceDashboard(dashboard_window, self.db_manager)
            
            # Show the dashboard (call the show method for consistency with other dashboards)
            dashboard.show()
            
            # Log the action
            logger.info("Enhanced Invoice dashboard opened")
            
        except Exception as e:
            logger.error(f"Failed to open enhanced invoice dashboard: {str(e)}")
            messagebox.showerror("Error", f"Failed to open invoice dashboard: {str(e)}")
    
    def _show_sql_library(self):
        """Show the SQL Query Library dialog directly"""
        try:
            # Create a temporary invisible window
            temp_window = tk.Toplevel(self.root)
            temp_window.withdraw()  # Hide it
            
            # Create dashboard instance just to access SQL library
            from finance_assistant.enhanced_dashboard import EnhancedInvoiceDashboard
            dashboard = EnhancedInvoiceDashboard(temp_window, self.db_manager)
            
            # Show SQL library
            dashboard.show_sql_library()
            
            # Schedule temp window for destruction after SQL library is closed
            def check_sql_library():
                found = False
                for child in self.root.winfo_children():
                    if isinstance(child, tk.Toplevel) and child.title() == "SQL Query Library":
                        found = True
                        self.root.after(1000, check_sql_library)
                        break
                
                # If SQL library window is closed (not found), destroy temp window
                if not found:
                    temp_window.destroy()
            
            # Start checking for SQL library window
            self.root.after(1000, check_sql_library)
            
        except Exception as e:
            logger.error(f"Failed to open SQL library: {str(e)}")
            messagebox.showerror("Error", f"Failed to open SQL library: {str(e)}")
    
    def _show_unified_dashboard(self):
        """Open the unified invoice dashboard"""
        try:
            # Create a new window for the dashboard
            dashboard_window = tk.Toplevel(self.root)
            dashboard_window.title("Unified Invoice Dashboard")
            dashboard_window.geometry("1200x800")
            dashboard_window.configure(bg="#1e1e2e")
            
            # Import and create the dashboard
            from finance_assistant.unified_dashboard import UnifiedDashboard
            dashboard = UnifiedDashboard(dashboard_window, self.db_manager, self.llm_client)
            
            # Log the action
            logger.info("Unified Invoice dashboard opened")
            
        except Exception as e:
            logger.error(f"Failed to open unified dashboard: {str(e)}")
            messagebox.showerror("Error", f"Failed to open dashboard: {str(e)}")
    
    def run(self):
        """Run the application"""
        self.root.mainloop()
        
if __name__ == "__main__":
    app = FinancialAssistant()
    app.run()
