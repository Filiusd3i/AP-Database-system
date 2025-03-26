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
import argparse

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
    
    def __init__(self, use_modern_ui=False):
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
        
        # Store UI preference
        self.use_modern_ui = use_modern_ui
        
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
                  
        # Button for Unified Dashboard
        ttk.Button(button_frame, text="Unified Dashboard", style="Accent.TButton", 
                  command=self._show_unified_dashboard).pack(side=tk.LEFT, padx=5)
                  
        # Button for Modern Dashboard 
        ttk.Button(button_frame, text="Modern Dashboard", style="Accent.TButton", 
                  command=self._show_modern_dashboard).pack(side=tk.LEFT, padx=5)
        
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
        ttk.Button(button_frame, text="Open Modern Dashboard", style="Accent.TButton", 
                 command=self._show_modern_dashboard, width=25).pack(pady=5)
        
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
        db_menu.add_command(label="Modern Dashboard", command=self._show_modern_dashboard)
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
        dashboard_menu.add_command(label="Modern Dashboard", command=self._show_modern_dashboard)
        
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
                    
                    # Show the appropriate dashboard based on preferences
                    if self.use_modern_ui:
                        self._show_modern_dashboard()
                    else:
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
                        
                        # Show the dashboard based on user preference
                        if self.use_modern_ui:
                            self._show_modern_dashboard()
                        else:
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
            
    def _show_modern_dashboard(self):
        """Open the modern three-panel dashboard interface"""
        try:
            # Create a new window for the dashboard
            dashboard_window = tk.Toplevel(self.root)
            dashboard_window.title("Modern Invoice Dashboard")
            dashboard_window.geometry("1200x800")
            dashboard_window.configure(bg="#1e1e2e")
            
            # Import and create the dashboard
            from finance_assistant.modern_dashboard import ModernDashboard
            dashboard = ModernDashboard(dashboard_window, self.db_manager, self.llm_client)
            
            # Log the action
            logger.info("Modern Dashboard opened")
            
        except Exception as e:
            logger.error(f"Failed to open modern dashboard: {str(e)}")
            messagebox.showerror("Error", f"Failed to open dashboard: {str(e)}")
            
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
            
        # Dialog implementation goes here
        messagebox.showinfo("Export", "The CSV export dialog would be shown here")
    
    def _fix_database_schema(self):
        """Fix database schema issues automatically"""
        if not self.db_manager.is_connected:
            messagebox.showwarning("Warning", "Please connect to a database first")
            return
        
        # Run schema fixes
        self._validate_and_fix_database_schema()
        messagebox.showinfo("Schema Fix", "Database schema has been checked and fixed if needed")
    
    def _show_schema_inspector(self):
        """Show the database schema inspector dialog"""
        if not self.db_manager.is_connected:
            messagebox.showwarning("Warning", "Please connect to a database first")
            return
            
        messagebox.showinfo("Schema Inspector", "The schema inspector would be shown here")
    
    def _show_about(self):
        """Show the about dialog"""
        # Create dialog window with dark theme
        about_dialog = tk.Toplevel(self.root)
        about_dialog.title("About")
        about_dialog.geometry("400x300")
        about_dialog.configure(background=self.bg_dark)
        about_dialog.transient(self.root)
        about_dialog.grab_set()
        
        # Create frame
        frame = ttk.Frame(about_dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        ttk.Label(frame, text="Financial Database Assistant", 
                font=(self.font_family, 16, "bold")).pack(pady=(0,10))
        
        # Version
        ttk.Label(frame, text="Version 1.0.0").pack(pady=5)
        
        # Description
        description = "A powerful tool for managing financial data with both traditional and modern UI options."
        ttk.Label(frame, text=description, wraplength=350).pack(pady=10)
        
        # Close button
        ttk.Button(frame, text="Close", command=about_dialog.destroy).pack(pady=20)
    
    def _show_unified_dashboard(self):
        """Open the unified invoice dashboard with private equity enhancements"""
        try:
            if not self.db_manager.is_connected:
                messagebox.showwarning("Warning", "Please connect to a database first")
                return
                
            # Create a new window for the dashboard
            dashboard_window = tk.Toplevel(self.root)
            dashboard_window.title("Private Equity Fund Management Dashboard")
            dashboard_window.geometry("1200x800")
            dashboard_window.configure(bg="#1e1e2e")
            
            # Import and create the dashboard
            from finance_assistant.unified_dashboard import UnifiedDashboard
            dashboard = UnifiedDashboard(dashboard_window, self.db_manager, self.llm_client)
            
            # Log the action
            logger.info("Private Equity Fund Management dashboard opened")
            
        except Exception as e:
            logger.error(f"Failed to open unified dashboard: {str(e)}")
            messagebox.showerror("Error", f"Failed to open dashboard: {str(e)}")
    
    def run(self):
        """Run the application"""
        self.root.mainloop()

# Entry point for the application
if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Financial Database Assistant")
    parser.add_argument("--modern-ui", action="store_true", help="Use the modern UI by default")
    args = parser.parse_args()
    
    # Create and run the application
    app = FinancialAssistant(use_modern_ui=args.modern_ui)
    app.run()
