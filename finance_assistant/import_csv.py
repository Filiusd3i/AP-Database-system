import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
import os
import traceback
import re
import math
import pyodbc
from datetime import datetime
import csv
import numpy as np
import logging
from finance_assistant.database.connection import DatabaseConnection, QueryBuilder
from finance_assistant.schema_validator import SchemaValidator

# Set up logging for import errors
logger = logging.getLogger("csv_import")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    # Create file handler
    fh = logging.FileHandler("csv_import_errors.log")
    fh.setLevel(logging.INFO)
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    # Add handlers to logger
    logger.addHandler(fh)

class CSVImportManager:
    def __init__(self, app):
        self.app = app
        self.import_window = None
        self.preview_table = None
        self.file_path_var = None
        self.table_combo = None
        self.import_data = None
        self.preview_frame = None
        self.row_count_label = None
        self.column_mappings = {}
        self.csv_file = None
        self.csv_data = None
        self.table_mappings = {}
        self.dialog = None
        self.column_mapping_vars = {}
        self.preview_tree = None
        self.selected_table = None
        self.table_var = None
        self.current_page = 0
        self.rows_per_page = 10
        self.status_var = None
        self.progress = None
        self.vendor_cache = {}  # Cache for vendor lookup
        self.missing_vendors = set()  # Track missing vendors
        self.create_missing_vendors = False  # Option to create missing vendors
        self.create_table_var = None  # Variable for "Create table if not exists" checkbox
        self.create_table_if_not_exists = False
        self.schema_validator = None  # Will be initialized when needed
        
    def show_import_dialog(self):
        """Display the import dialog to select a CSV file and map columns"""
        # Select CSV file first
        csv_file = filedialog.askopenfilename(
            title="Select CSV File to Import",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        
        if not csv_file:
            return
            
        # Store the selected file
        self.csv_file = csv_file
        
        # Load the CSV data
        try:
            self.csv_data = pd.read_csv(csv_file)
            
            # Display import dialog
            self._create_import_dialog()
            
        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to load CSV file: {str(e)}")
    
    def _create_import_dialog(self):
        """Create the import dialog window"""
        self.dialog = tk.Toplevel(self.app.root)
        self.dialog.title(f"Import Data from {os.path.basename(self.csv_file)}")
        self.dialog.geometry("900x700")
        self.dialog.grab_set()
        
        # Create status variable
        self.status_var = tk.StringVar()
        self.status_var.set(f"Loaded {len(self.csv_data)} rows from CSV")
        
        # Main frame
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Status label
        status_label = ttk.Label(main_frame, textvariable=self.status_var)
        status_label.pack(anchor=tk.W, pady=(0, 10))
        
        # Select table frame
        table_frame = ttk.LabelFrame(main_frame, text="Select Target Table")
        table_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Get the list of tables
        if self.app.database_manager.is_connected():
            tables = self.app.database_manager.tables
        else:
            messagebox.showerror("Error", "Not connected to a database")
            self.dialog.destroy()
            return
        
        # Table selector
        self.table_var = tk.StringVar()
        if tables:
            self.table_var.set(tables[0])
        
        table_label = ttk.Label(table_frame, text="Target Table:")
        table_label.pack(side=tk.LEFT, padx=(5, 5))
        
        table_dropdown = ttk.Combobox(table_frame, textvariable=self.table_var, values=tables)
        table_dropdown.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5), pady=5)
        table_dropdown.bind("<<ComboboxSelected>>", self._on_table_selected)
        
        # Add "Create table if not exists" checkbox
        self.create_table_var = tk.BooleanVar(value=False)
        create_table_cb = ttk.Checkbutton(
            table_frame,
            text="Create table if not exists",
            variable=self.create_table_var,
            command=self._toggle_create_table
        )
        create_table_cb.pack(side=tk.RIGHT, padx=5)
        
        # Preview frame
        preview_frame = ttk.LabelFrame(main_frame, text="CSV Preview")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Create Treeview for preview
        preview_tree_frame = ttk.Frame(preview_frame)
        preview_tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scrollbars
        tree_scroll_y = ttk.Scrollbar(preview_tree_frame, orient=tk.VERTICAL)
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        tree_scroll_x = ttk.Scrollbar(preview_tree_frame, orient=tk.HORIZONTAL)
        tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Create the Treeview
        self.preview_tree = ttk.Treeview(
            preview_tree_frame, 
            show="headings",
            yscrollcommand=tree_scroll_y.set,
            xscrollcommand=tree_scroll_x.set
        )
        
        tree_scroll_y.config(command=self.preview_tree.yview)
        tree_scroll_x.config(command=self.preview_tree.xview)
        
        self.preview_tree.pack(fill=tk.BOTH, expand=True)
        
        # Add columns to the treeview
        columns = list(self.csv_data.columns)
        self.preview_tree["columns"] = columns
        
        for col in columns:
            self.preview_tree.heading(col, text=col)
            self.preview_tree.column(col, width=100, minwidth=50)
        
        # Populate with preview data
        self._update_preview()
        
        # Navigation buttons
        nav_frame = ttk.Frame(preview_frame)
        nav_frame.pack(fill=tk.X, padx=5, pady=5)
        
        prev_btn = ttk.Button(nav_frame, text="Previous", command=self._prev_page)
        prev_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        next_btn = ttk.Button(nav_frame, text="Next", command=self._next_page)
        next_btn.pack(side=tk.LEFT)
        
        # Page info
        self.page_var = tk.StringVar()
        self._update_page_info()
        page_label = ttk.Label(nav_frame, textvariable=self.page_var)
        page_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Column mapping frame
        mapping_frame = ttk.LabelFrame(main_frame, text="Column Mapping")
        mapping_frame.pack(fill=tk.BOTH, pady=(0, 10))
        
        # Create column mapping UI
        self.mapping_inner_frame = ttk.Frame(mapping_frame)
        self.mapping_inner_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Initialize mapping controls
        if tables:
            self._on_table_selected(None)
        
        # Buttons frame
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 5))
        
        cancel_btn = ttk.Button(
            btn_frame, 
            text="Cancel", 
            command=self.dialog.destroy
        )
        cancel_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        import_btn = ttk.Button(
            btn_frame, 
            text="Start Import", 
            command=self._start_import
        )
        import_btn.pack(side=tk.RIGHT)
    
    def _update_preview(self):
        """Update the preview treeview with current page of data"""
        # Clear existing items
        for item in self.preview_tree.get_children():
            self.preview_tree.delete(item)
        
        # Calculate slice for current page
        start_idx = self.current_page * self.rows_per_page
        end_idx = min((self.current_page + 1) * self.rows_per_page, len(self.csv_data))
        
        # Add data rows
        for i in range(start_idx, end_idx):
            row_values = list(self.csv_data.iloc[i])
            # Convert NaN to 'NULL' for display
            row_values = [str(val) if not pd.isna(val) else 'NULL' for val in row_values]
            self.preview_tree.insert("", tk.END, values=row_values)
    
    def _prev_page(self):
        """Go to previous page in preview"""
        if self.current_page > 0:
            self.current_page -= 1
            self._update_preview()
            self._update_page_info()
    
    def _next_page(self):
        """Go to next page in preview"""
        max_pages = (len(self.csv_data) + self.rows_per_page - 1) // self.rows_per_page
        if self.current_page < max_pages - 1:
            self.current_page += 1
            self._update_preview()
            self._update_page_info()
    
    def _update_page_info(self):
        """Update the page information label"""
        max_pages = (len(self.csv_data) + self.rows_per_page - 1) // self.rows_per_page
        self.page_var.set(f"Page {self.current_page + 1} of {max_pages}")
    
    def _on_table_selected(self, event):
        """Handle table selection change"""
        # Clear the mapping frame
        for widget in self.mapping_inner_frame.winfo_children():
            widget.destroy()
        
        # Get selected table
        self.selected_table = self.table_var.get()
        
        # Create mapping UI based on selected table
        if not self.selected_table:
            return
        
        # Initialize schema validator if needed
        if not self.schema_validator:
            self.schema_validator = SchemaValidator(self.app.database_manager)
        
        # Get table schema from database
        db_columns = []
        
        if not self.create_table_if_not_exists:
            # Use database schema if table exists
            result = self.app.database_manager.db.get_columns(self.selected_table)
            if 'columns' in result:
                db_columns = [col['name'] for col in result['columns']]
        else:
            # Use expected schema from validator if we'll create the table
            if self.selected_table.lower() in self.schema_validator.expected_schemas:
                schema = self.schema_validator.expected_schemas[self.selected_table.lower()]
                db_columns = list(schema['required_columns'].keys()) + list(schema['optional_columns'].keys())
                db_columns.append('id')  # Add id column which is always present
                db_columns.append('created_at')  # Add created_at which is always present
        
        # Create header
        ttk.Label(self.mapping_inner_frame, text="CSV Column").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Label(self.mapping_inner_frame, text="Database Column").grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Create mapping controls for each CSV column
        csv_columns = list(self.csv_data.columns)
        db_columns_with_none = ["None"] + db_columns
        
        # If we have the schema validator and CSV headers, try automatic mapping
        if self.schema_validator and csv_columns:
            auto_mapping = self.schema_validator.get_csv_import_mapping(self.selected_table, csv_columns)
            
            # Apply automatic mapping to our table mappings
            if self.selected_table not in self.table_mappings:
                self.table_mappings[self.selected_table] = {}
                
            self.table_mappings[self.selected_table].update(auto_mapping)
            
            logger.info(f"Applied automatic mapping for {len(auto_mapping)} columns: {auto_mapping}")
        
        for i, csv_col in enumerate(csv_columns):
            ttk.Label(self.mapping_inner_frame, text=csv_col).grid(row=i+1, column=0, sticky=tk.W, padx=5, pady=2)
            
            # Combobox for DB column
            var = tk.StringVar()
            if csv_col in self.table_mappings.get(self.selected_table, {}):
                var.set(self.table_mappings[self.selected_table][csv_col])
            else:
                var.set("None")
                
            self.column_mapping_vars[csv_col] = var
            
            combo = ttk.Combobox(
                self.mapping_inner_frame, 
                textvariable=var, 
                values=db_columns_with_none,
                width=30
            )
            combo.grid(row=i+1, column=1, sticky=tk.W, padx=5, pady=2)
            combo.bind("<<ComboboxSelected>>", lambda e, col=csv_col: self._on_mapping_changed(col))
        
        # Add auto-map button
        if self.schema_validator:
            auto_map_btn = ttk.Button(
                self.mapping_inner_frame, 
                text="Auto-Map Columns",
                command=self._auto_map_columns
            )
            auto_map_btn.grid(row=len(csv_columns)+1, column=0, columnspan=2, sticky=tk.W, padx=5, pady=10)
        
        # Add validate vendors button if needed
        if self.selected_table.lower() == 'invoices':
            validate_frame = ttk.Frame(self.mapping_inner_frame)
            validate_frame.grid(row=len(csv_columns)+2, column=0, columnspan=2, sticky=tk.W, padx=5, pady=10)
            
            validate_btn = ttk.Button(
                validate_frame, 
                text="Validate Vendors",
                command=self._validate_vendors
            )
            validate_btn.pack(side=tk.LEFT, padx=(0, 10))
            
            # Add checkbox for auto-creating missing vendors
            self.create_vendors_var = tk.BooleanVar(value=False)
            create_vendors_cb = ttk.Checkbutton(
                validate_frame,
                text="Auto-create missing vendors",
                variable=self.create_vendors_var,
                command=self._toggle_create_vendors
            )
            create_vendors_cb.pack(side=tk.LEFT)
            
            # Load vendors into cache for validation
            self._load_vendors()
    
    def _load_vendors(self):
        """Load vendors from the database into the cache"""
        try:
            access_db = self.app.database_manager.access_db
            if not access_db or not access_db.connected:
                return
                
            # Check if the vendor table exists
            if 'vendor list' not in access_db.tables:
                return
                
            # Get vendor data
            vendors = access_db.get_vendor_data()
            if not vendors:
                return
                
            # Reset the cache
            self.vendor_cache = {}
            
            # Find the vendor name and ID columns
            name_fields = ['name', 'vendor_name', 'vendorname']
            id_fields = ['id', 'vendor_id', 'vendorid']
            
            # Determine which columns to use
            name_col = None
            id_col = None
            
            if vendors and len(vendors) > 0:
                first_vendor = vendors[0]
                
                # Look for name column
                for field in name_fields:
                    if field in first_vendor:
                        name_col = field
                        break
                
                # Look for ID column
                for field in id_fields:
                    if field in first_vendor:
                        id_col = field
                        break
                
                # If we have both columns, build the cache
                if name_col and id_col:
                    for vendor in vendors:
                        vendor_name = vendor[name_col]
                        vendor_id = vendor[id_col]
                        if vendor_name:
                            # Store normalized vendor name for case-insensitive lookup
                            self.vendor_cache[vendor_name.lower()] = {
                                'id': vendor_id,
                                'name': vendor_name  # Keep original case
                            }
                    
                    print(f"Loaded {len(self.vendor_cache)} vendors into cache")
                
        except Exception as e:
            print(f"Error loading vendors: {e}")
    
    def _validate_vendors(self):
        """Validate vendors in the CSV data against vendors in the database"""
        try:
            if not self.csv_data.empty and self.vendor_cache:
                # Find vendor name mapping
                vendor_col = None
                for csv_col, db_col in self.table_mappings[self.selected_table].items():
                    if db_col.lower() in ['vendor', 'vendor_name', 'vendorname']:
                        vendor_col = csv_col
                        break
                
                if not vendor_col:
                    messagebox.showinfo("Validation", "No vendor column mapped. Please map a vendor column first.")
                    return
                
                # Reset missing vendors
                self.missing_vendors = set()
                
                # Check each vendor
                for idx, row in self.csv_data.iterrows():
                    vendor_name = row[vendor_col]
                    if pd.isna(vendor_name) or not vendor_name:
                        continue  # Skip empty vendors
                        
                    # Check if vendor exists
                    if vendor_name.lower() not in self.vendor_cache:
                        self.missing_vendors.add(vendor_name)
                
                # Show results
                if self.missing_vendors:
                    missing_list = "\n".join(self.missing_vendors)
                    result = messagebox.askquestion(
                        "Missing Vendors", 
                        f"Found {len(self.missing_vendors)} vendors not in the database:\n\n{missing_list}\n\n"
                        "Would you like to automatically create these vendors during import?",
                        icon='warning'
                    )
                    
                    # Set flag based on user choice
                    self.create_missing_vendors = (result == 'yes')
                    self.create_vendors_var.set(self.create_missing_vendors)
                else:
                    messagebox.showinfo("Validation", "All vendors found in the database.")
            else:
                messagebox.showinfo("Validation", "Please load vendor data first.")
                
        except Exception as e:
            messagebox.showerror("Error", f"Error validating vendors: {str(e)}")
            print(f"Error validating vendors: {e}")
    
    def _toggle_create_vendors(self):
        """Handle checkbox state change for creating vendors"""
        self.create_missing_vendors = self.create_vendors_var.get()
    
    def _on_mapping_changed(self, csv_column):
        """Handle mapping selection change"""
        if self.selected_table not in self.table_mappings:
            self.table_mappings[self.selected_table] = {}
            
        # Update the mapping
        self.table_mappings[self.selected_table][csv_column] = self.column_mapping_vars[csv_column].get()
    
    def _auto_map_columns(self):
        """Automatically map CSV columns to database columns"""
        if not self.schema_validator:
            self.schema_validator = SchemaValidator(self.app.database_manager)
            
        # Get the CSV headers
        csv_headers = list(self.csv_data.columns)
        
        # Get automatic mapping
        auto_mapping = self.schema_validator.get_csv_import_mapping(self.selected_table, csv_headers)
        
        # Update the UI
        for csv_col, db_col in auto_mapping.items():
            if csv_col in self.column_mapping_vars:
                self.column_mapping_vars[csv_col].set(db_col)
                self._on_mapping_changed(csv_col)
        
        # Show a confirmation message
        messagebox.showinfo(
            "Auto-Mapping Complete", 
            f"Automatically mapped {len(auto_mapping)} columns between CSV and database."
        )
    
    def _toggle_create_table(self):
        """Handle checkbox state change for creating table"""
        self.create_table_if_not_exists = self.create_table_var.get()
        logger.info(f"Set create_table_if_not_exists to {self.create_table_if_not_exists}")
    
    def _start_import(self):
        """Start the import process"""
        # Check if database is connected
        if not self.app.database_manager.is_connected():
            messagebox.showerror("Error", "Not connected to a database.")
            return
            
        # Get the current mapping for selected table
        if self.selected_table not in self.table_mappings:
            messagebox.showerror("Error", "Please select a table and map columns first.")
            return
            
        current_mapping = self.table_mappings[self.selected_table]
        
        # Check if at least one column is mapped
        has_mapping = False
        for csv_col, db_col in current_mapping.items():
            if db_col != "None":
                has_mapping = True
                break
                
        if not has_mapping:
            messagebox.showerror("Error", "Please map at least one column before importing.")
            return
        
        # Initialize schema validator if needed
        if not self.schema_validator:
            self.schema_validator = SchemaValidator(self.app.database_manager)
        
        # Check if table exists, create it if necessary
        table_exists = self.schema_validator.check_table_exists(self.selected_table)
        
        if not table_exists:
            if self.create_table_if_not_exists:
                # Try to create the table
                if not self.schema_validator.check_table_exists(self.selected_table, create_if_missing=True):
                    messagebox.showerror(
                        "Error", 
                        f"Failed to create table '{self.selected_table}'. Please check the logs for details."
                    )
                    return
                logger.info(f"Created table '{self.selected_table}' for import")
            else:
                # Table doesn't exist and we're not creating it
                messagebox.showerror(
                    "Error", 
                    f"Table '{self.selected_table}' does not exist. Enable 'Create table if not exists' to create it."
                )
                return
        
        # Validate schema and fix if needed
        schema_result = self.schema_validator.validate_table(self.selected_table, auto_fix=True)
        if not schema_result['valid']:
            messagebox.showerror(
                "Schema Error", 
                f"Failed to validate/fix table schema for '{self.selected_table}'. Please check the logs for details."
            )
            return
            
        # Create progress window
        progress_window = tk.Toplevel(self.dialog)
        progress_window.title("Importing Data")
        progress_window.geometry("400x150")
        progress_window.grab_set()
        
        ttk.Label(progress_window, text="Importing data, please wait...").pack(pady=(10, 5))
        
        # Progress bar
        self.progress = ttk.Progressbar(progress_window, orient=tk.HORIZONTAL, length=350, mode='determinate')
        self.progress.pack(padx=20, pady=5)
        
        # Progress info
        self.progress_info = tk.StringVar()
        self.progress_info.set("Preparing data...")
        progress_label = ttk.Label(progress_window, textvariable=self.progress_info)
        progress_label.pack(pady=5)
        
        # Maximum value for progress bar
        self.progress['maximum'] = len(self.csv_data)
        self.progress['value'] = 0
        
        # Schedule the import process to run after UI updates
        self.dialog.after(100, lambda: self._perform_import(progress_window))
    
    def _perform_import(self, progress_window):
        """Perform the actual import process"""
        try:
            # Get the database connection
            db = self.app.database_manager.db
            
            # Get the current mapping
            current_mapping = self.table_mappings[self.selected_table]
            
            # Process each row
            total_rows = len(self.csv_data)
            success_count = 0
            error_count = 0
            
            for idx, row in self.csv_data.iterrows():
                try:
                    # Update progress
                    self.progress_info.set(f"Processing row {idx+1}/{total_rows}")
                    self.progress['value'] = idx + 1
                    progress_window.update()
                    
                    # Skip completely empty rows
                    if row.isna().all():
                        continue
                    
                    # Build column data
                    column_data = {}
                    
                    for csv_col, db_col in current_mapping.items():
                        if db_col != "None" and csv_col in row:
                            value = row[csv_col]
                            
                            # Skip None or NaN values
                            if pd.isna(value):
                                continue
                                
                            # Convert based on data type
                            if isinstance(value, (int, float, bool)):
                                column_data[db_col] = value
                            elif isinstance(value, pd.Timestamp):
                                column_data[db_col] = value.to_pydatetime()
                            else:
                                # Convert to string
                                column_data[db_col] = str(value)
                    
                    # Skip if no columns left after filtering
                    if not column_data:
                        logger.warning(f"Skipping row {idx+1} (no valid columns)")
                        continue
                    
                    # Build INSERT query
                    columns = list(column_data.keys())
                    placeholders = ["%s"] * len(columns)
                    query = f"INSERT INTO {self.selected_table} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
                    values = [column_data[col] for col in columns]
                    
                    # Execute the INSERT
                    result = db.execute_update(query, values)
                    
                    if 'error' in result and result['error']:
                        logger.error(f"Error importing row {idx+1}: {result['error']}")
                        error_count += 1
                    else:
                        success_count += 1
                        
                except Exception as e:
                    logger.error(f"Error processing row {idx+1}: {str(e)}")
                    error_count += 1
            
            # Show completion message
            self.progress_info.set(f"Import completed: {success_count} rows imported, {error_count} errors")
            progress_window.update()
            
            messagebox.showinfo(
                "Import Complete", 
                f"Import completed with {success_count} rows imported successfully and {error_count} errors.\n\n"
                f"See 'csv_import_errors.log' for details on any errors."
            )
            
            # Close the progress window and dialog
            progress_window.destroy()
            self.dialog.destroy()
            
        except Exception as e:
            logger.error(f"Error during import: {str(e)}")
            traceback.print_exc()
            messagebox.showerror("Import Error", f"An error occurred during import: {str(e)}")
            progress_window.destroy() 