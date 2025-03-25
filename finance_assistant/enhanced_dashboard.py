import tkinter as tk
from tkinter import ttk, messagebox
import logging
from datetime import datetime, date, timedelta
import os
import platform
import threading
try:
    from tkcalendar import DateEntry
except ImportError:
    # Fallback if tkcalendar is not installed
    class DateEntry(ttk.Entry):
        def __init__(self, master=None, **kw):
            self.date_var = tk.StringVar()
            ttk.Entry.__init__(self, master, textvariable=self.date_var, **kw)
            self.insert(0, datetime.now().strftime('%Y-%m-%d'))
            
        def get_date(self):
            try:
                return datetime.strptime(self.date_var.get(), '%Y-%m-%d').date()
            except:
                return datetime.now().date()
            
        def set_date(self, date):
            self.date_var.set(date.strftime('%Y-%m-%d'))

# Configure logging
logger = logging.getLogger(__name__)

class EnhancedInvoiceDashboard:
    def __init__(self, parent, db_manager):
        """Initialize the enhanced invoice dashboard with dark theme and SQL library"""
        self.parent = parent
        self.db_manager = db_manager
        
        # Configure colors for dark theme
        self.bg_dark = '#1e1e2e'
        self.bg_medium = '#2a2a3a' 
        self.bg_light = '#313145'
        self.accent_color = '#7e57c2'
        self.text_color = '#e0e0e0'
        self.highlight_color = '#bb86fc'
        
        # Initialize status variable
        self.status_var = tk.StringVar(value="Ready")
        
        # Load platform-specific font
        if platform.system() == "Windows":
            self.font_family = "Segoe UI"
        elif platform.system() == "Darwin":  # macOS
            self.font_family = "SF Pro Text"
        else:  # Linux
            self.font_family = "Ubuntu"
        
        # Initialize SQL library
        self.sql_library = {}
        self.load_sql_library_from_db()
        
        # Initialize sort direction
        self.sort_reverse = False
        
        # Create dashboard UI
        self._create_dashboard_ui()
    
    def _create_dashboard_ui(self):
        """Create the main dashboard UI with gradient headers and panels"""
        # Configure parent window background
        self.parent.configure(bg=self.bg_dark)
        
        # Create main content frame
        self.main_frame = ttk.Frame(self.parent)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Add menu bar
        self._create_menu_bar()
        
        # Add status bar
        self._create_status_bar()
        
        # Create content area with three sections
        # 1. Summary cards at top
        # 2. Filters in middle
        # 3. Invoice table at bottom
        self._create_summary_cards()
        self._create_filter_section()
        self._create_invoice_table()
        
        # Load initial data
        self._load_dashboard_data()
    
    def _create_menu_bar(self):
        """Create dashboard menu bar"""
        menubar = tk.Menu(self.parent)
        self.parent.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Export Results", command=self._export_results)
        file_menu.add_separator()
        file_menu.add_command(label="Close Dashboard", command=self.parent.destroy)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="SQL Query Library", command=self.show_sql_library)
        tools_menu.add_command(label="Schema Inspector", command=self._show_schema_inspector)
        tools_menu.add_separator()
        tools_menu.add_command(label="Refresh Data", command=self._load_dashboard_data)
    
    def _create_status_bar(self):
        """Create status bar at bottom of window"""
        status_frame = tk.Frame(self.parent, height=25, bg=self.bg_medium)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        status_label = ttk.Label(status_frame, textvariable=self.status_var,
                               anchor=tk.W, background=self.bg_medium)
        status_label.pack(fill=tk.X, padx=10, pady=4)
    
    def show(self):
        """Show the dashboard (placeholder method for compatibility)"""
        # This method exists for compatibility with other dashboard classes
        # The UI is already created in __init__, so nothing needed here
        self.status_var.set("Dashboard ready")

    def show_sql_library(self):
        """Show SQL query library dialog for managing and executing queries"""
        # Create library window
        sql_window = tk.Toplevel(self.parent)
        sql_window.title("SQL Query Library")
        sql_window.geometry("800x600")
        sql_window.configure(bg="#1e1e2e")
        
        # Main content frame
        main_frame = ttk.Frame(sql_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Create split view
        paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True)
        
        # Left panel - Query list
        left_frame = ttk.Frame(paned_window)
        paned_window.add(left_frame, weight=1)
        
        # Query list header
        list_header = ttk.Label(left_frame, text="Available Queries", font=('Segoe UI', 12, 'bold'))
        list_header.pack(pady=(0, 10), anchor=tk.W)
        
        # Create listbox for queries
        query_listbox = tk.Listbox(left_frame, bg="#2a2a3a", fg="#e0e0e0", 
                                  font=('Segoe UI', 11),
                                  selectbackground="#7e57c2", selectforeground="#ffffff")
        query_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Add scrollbar
        list_scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=query_listbox.yview)
        query_listbox.configure(yscrollcommand=list_scrollbar.set)
        list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Populate with query names
        for query_name in sorted(self.sql_library.keys()):
            query_listbox.insert(tk.END, query_name)
        
        # Right panel - Query editor and results
        right_frame = ttk.Frame(paned_window)
        paned_window.add(right_frame, weight=2)
        
        # Query name field
        name_frame = ttk.Frame(right_frame)
        name_frame.pack(fill=tk.X, pady=(0, 10))
        
        name_label = ttk.Label(name_frame, text="Query Name:")
        name_label.pack(side=tk.LEFT, padx=(0, 5))
        
        query_name_var = tk.StringVar()
        name_entry = ttk.Entry(name_frame, textvariable=query_name_var, width=30)
        name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Query editor
        editor_label = ttk.Label(right_frame, text="SQL Query:")
        editor_label.pack(anchor=tk.W, pady=(0, 5))
        
        query_editor = tk.Text(right_frame, height=8, bg="#2a2a3a", fg="#e0e0e0", 
                              font=('Consolas', 11))
        query_editor.pack(fill=tk.X, pady=(0, 10))
        
        # Button frame for query actions
        button_frame = ttk.Frame(right_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        execute_button = ttk.Button(button_frame, text="Execute Query")
        execute_button.pack(side=tk.LEFT, padx=5)
        
        save_button = ttk.Button(button_frame, text="Save to Library")
        save_button.pack(side=tk.LEFT, padx=5)
        
        delete_button = ttk.Button(button_frame, text="Delete Query") 
        delete_button.pack(side=tk.LEFT, padx=5)
        
        # Results area
        results_label = ttk.Label(right_frame, text="Query Results:")
        results_label.pack(anchor=tk.W, pady=(0, 5))
        
        # Results tree
        result_frame = ttk.Frame(right_frame)
        result_frame.pack(fill=tk.BOTH, expand=True)
        
        results_tree = ttk.Treeview(result_frame)
        results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbars for results
        results_vsb = ttk.Scrollbar(result_frame, orient="vertical", command=results_tree.yview)
        results_tree.configure(yscrollcommand=results_vsb.set)
        results_vsb.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Fix: Move horizontal scrollbar to result_frame (was incorrectly on right_frame)
        results_hsb = ttk.Scrollbar(result_frame, orient="horizontal", command=results_tree.xview)
        results_tree.configure(xscrollcommand=results_hsb.set)
        results_hsb.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Function to load selected query
        def load_selected_query(event):
            selection = query_listbox.curselection()
            if not selection:
                return
                
            query_name = query_listbox.get(selection[0])
            query_name_var.set(query_name)
            
            # Load query to editor
            query_text = self.sql_library.get(query_name, "")
            query_editor.delete("1.0", tk.END)
            query_editor.insert("1.0", query_text)
        
        # Bind selection event
        query_listbox.bind('<<ListboxSelect>>', load_selected_query)
        
        # Function to execute and display results in the treeview
        def execute_and_show_results():
            # Get query from editor
            query = query_editor.get("1.0", tk.END).strip()
            if not query:
                return
                
            # Execute query
            result = self.db_manager.db.execute_query(query)
            
            # Clear previous results
            for col in results_tree["columns"]:
                results_tree.heading(col, text="")
            
            results_tree["columns"] = ()
            
            for item in results_tree.get_children():
                results_tree.delete(item)
            
            # Check for error
            if result.get('error'):
                messagebox.showerror("SQL Error", result['error'], parent=sql_window)
                return
                
            # No results
            if not result.get('rows'):
                messagebox.showinfo("Query Complete", "Query executed successfully with no results.", parent=sql_window)
                return
            
            # Configure columns
            column_names = [desc[0] for desc in result['description']]
            results_tree["columns"] = column_names
            
            for col in column_names:
                results_tree.heading(col, text=col)
                results_tree.column(col, width=100)
            
            # Add data rows
            for row in result['rows']:
                formatted_row = []
                for val in row:
                    if isinstance(val, (datetime, date)):
                        formatted_row.append(val.strftime('%Y-%m-%d'))
                    elif isinstance(val, (int, float)):
                        formatted_row.append(f"{val:,}")
                    else:
                        formatted_row.append(str(val) if val is not None else "")
                
                results_tree.insert("", "end", values=formatted_row)
        
        # Link execute button to the function
        execute_button.configure(command=execute_and_show_results)
        
        # Handle save query function
        def save_query():
            name = query_name_var.get().strip()
            query = query_editor.get("1.0", tk.END).strip()
            
            if not name:
                messagebox.showerror("Error", "Please enter a name for the query", parent=sql_window)
                return
                
            if not query:
                messagebox.showerror("Error", "Please enter a SQL query", parent=sql_window)
                return
            
            # Check if overwrites existing
            if name in self.sql_library and name in query_listbox.get(0, tk.END):
                overwrite = messagebox.askyesno(
                    "Confirm Overwrite", 
                    f"Query '{name}' already exists. Do you want to overwrite it?",
                    parent=sql_window
                )
                if not overwrite:
                    return
            elif name not in query_listbox.get(0, tk.END):
                # Add to listbox if new
                query_listbox.insert(tk.END, name)
            
            # Save to library
            self.sql_library[name] = query
            self.save_sql_library_to_db()
            
            messagebox.showinfo("Success", f"Query '{name}' saved to library", parent=sql_window)
        
        # Link save button to function
        save_button.configure(command=save_query)
        
        # Handle delete query function
        def delete_query():
            name = query_name_var.get().strip()
            
            if not name or name not in self.sql_library:
                messagebox.showerror("Error", "Please select a valid query to delete", parent=sql_window)
                return
            
            confirm = messagebox.askyesno(
                "Confirm Delete", 
                f"Are you sure you want to delete the query '{name}'?",
                parent=sql_window
            )
            
            if not confirm:
                return
            
            # Delete from library
            del self.sql_library[name]
            self.save_sql_library_to_db()
            
            # Update listbox
            for i in range(query_listbox.size()):
                if query_listbox.get(i) == name:
                    query_listbox.delete(i)
                    break
            
            # Clear editor if showing deleted query
            if query_name_var.get() == name:
                query_name_var.set("")
                query_editor.delete("1.0", tk.END)
            
            messagebox.showinfo("Success", f"Query '{name}' deleted from library", parent=sql_window)
        
        # Link delete button to function
        delete_button.configure(command=delete_query)

    def execute_sql_query(self, query_text):
        """Execute a custom SQL query and return results"""
        query = query_text.strip()
        if not query:
            self.status_var.set("No query to execute")
            return None
        
        # Execute the query
        result = self.db_manager.db.execute_query(query)
        
        if result.get('error'):
            self.status_var.set(f"SQL Error: {result['error']}")
            return None
        
        self.status_var.set("Query executed successfully")
        return result

    def save_sql_library_to_db(self):
        """Save the SQL library to the database for persistence"""
        try:
            # Check if we have a sql_queries table
            create_table_query = """
            CREATE TABLE IF NOT EXISTS sql_queries (
                name VARCHAR(100) PRIMARY KEY,
                query_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
            self.db_manager.db.execute_update(create_table_query)
            
            # Clear existing queries
            self.db_manager.db.execute_update("DELETE FROM sql_queries")
            
            # Insert all queries
            for name, query_text in self.sql_library.items():
                insert_query = "INSERT INTO sql_queries (name, query_text) VALUES (%s, %s)"
                self.db_manager.db.execute_update(insert_query, [name, query_text])
            
            return True
        except Exception as e:
            self.status_var.set(f"Error saving SQL library: {str(e)}")
            logger.error(f"Error saving SQL library: {str(e)}")
            return False

    def load_sql_library_from_db(self):
        """Load the SQL library from the database"""
        try:
            # Check if table exists
            check_query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'sql_queries'
            )
            """
            result = self.db_manager.db.execute_query(check_query)
            
            if not result.get('rows') or not result['rows'][0][0]:
                # Table doesn't exist yet
                self.sql_library = {}
                return
            
            # Load queries
            query = "SELECT name, query_text FROM sql_queries"
            result = self.db_manager.db.execute_query(query)
            
            if result.get('error') or not result.get('rows'):
                self.sql_library = {}
                return
            
            # Update library
            self.sql_library = {}
            for row in result['rows']:
                self.sql_library[row[0]] = row[1]
                
        except Exception as e:
            self.status_var.set(f"Error loading SQL library: {str(e)}")
            logger.error(f"Error loading SQL library: {str(e)}")
            self.sql_library = {} 

    def _show_tree_tooltip(self, event):
        """Show tooltip when hovering over tree items"""
        # Get the current item the mouse is hovering over
        item_id = self.invoice_tree.identify_row(event.y)
        if not item_id:
            # Not hovering over an item, clear any existing tooltip
            self._hide_tooltip()
            return
            
        # Check if we have a tooltip window
        if not hasattr(self, 'tooltip_window') or not self.tooltip_window:
            # Get the item values
            values = self.invoice_tree.item(item_id, 'values')
            if not values:
                return
                
            # Invoice details
            invoice_id, invoice_number, date, vendor, description, amount, status, due_date, fund = values
            
            # Create tooltip window
            self.tooltip_window = tw = tk.Toplevel(self.parent)
            tw.wm_overrideredirect(True)  # Remove window decorations
            
            # Calculate position - display near the cursor
            x, y = event.x_root + 15, event.y_root + 10
            
            # Position the tooltip
            tw.wm_geometry(f"+{x}+{y}")
            tw.configure(bg=self.bg_dark, relief=tk.SOLID, borderwidth=1)
            
            # Create frame for tooltip content
            frame = tk.Frame(tw, bg=self.bg_dark, padx=5, pady=5)
            frame.pack()
            
            # Add invoice details to tooltip
            tk.Label(frame, text=f"Invoice: {invoice_number}", bg=self.bg_dark, 
                    fg=self.highlight_color, font=(self.font_family, 10, 'bold')).pack(anchor='w')
            tk.Label(frame, text=f"Date: {date}", bg=self.bg_dark, 
                    fg=self.text_color, font=(self.font_family, 9)).pack(anchor='w')
            tk.Label(frame, text=f"Vendor: {vendor}", bg=self.bg_dark, 
                    fg=self.text_color, font=(self.font_family, 9)).pack(anchor='w')
            tk.Label(frame, text=f"Amount: {amount}", bg=self.bg_dark, 
                    fg=self.text_color, font=(self.font_family, 9)).pack(anchor='w')
            tk.Label(frame, text=f"Status: {status}", bg=self.bg_dark, 
                    fg=self.text_color, font=(self.font_family, 9)).pack(anchor='w')
            
            if description:
                # Add description with wrapping
                desc_frame = tk.Frame(frame, bg=self.bg_dark)
                desc_frame.pack(fill='x', pady=(5, 0))
                
                tk.Label(desc_frame, text="Description:", bg=self.bg_dark, 
                        fg=self.text_color, font=(self.font_family, 9, 'bold')).pack(anchor='w')
                
                # Description text with wrapping
                desc_text = tk.Text(desc_frame, wrap='word', bg=self.bg_dark, fg=self.text_color,
                                  height=3, width=40, font=(self.font_family, 9))
                desc_text.insert('1.0', description)
                desc_text.configure(state='disabled')  # Make read-only
                desc_text.pack()
            
            # Schedule the tooltip to be destroyed after 5 seconds
            self.parent.after(5000, self._hide_tooltip)
    
    def _hide_tooltip(self):
        """Hide the tooltip window if it exists"""
        if hasattr(self, 'tooltip_window') and self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None
    
    def _apply_filters(self):
        """Apply the current filter settings and refresh data"""
        try:
            # Get filter values
            status = self.status_filter.get()
            date_range_type = self.date_filter.get()
            fund = self.fund_filter.get()
            search = self.search_var.get().strip()
            
            # Process date range
            date_range = None
            if date_range_type != 'All Time':
                from datetime import datetime, timedelta
                
                today = datetime.now()
                
                if date_range_type == 'This Year':
                    start_date = datetime(today.year, 1, 1)
                    end_date = datetime(today.year, 12, 31)
                    date_range = (start_date, end_date)
                    
                elif date_range_type == 'Last Year':
                    start_date = datetime(today.year - 1, 1, 1)
                    end_date = datetime(today.year - 1, 12, 31)
                    date_range = (start_date, end_date)
                    
                elif date_range_type == 'This Month':
                    start_date = datetime(today.year, today.month, 1)
                    # Get last day of the month
                    if today.month == 12:
                        end_date = datetime(today.year + 1, 1, 1) - timedelta(days=1)
                    else:
                        end_date = datetime(today.year, today.month + 1, 1) - timedelta(days=1)
                    date_range = (start_date, end_date)
                    
                elif date_range_type == 'Last Month':
                    # Get first day of last month
                    if today.month == 1:
                        start_date = datetime(today.year - 1, 12, 1)
                        end_date = datetime(today.year, 1, 1) - timedelta(days=1)
                    else:
                        start_date = datetime(today.year, today.month - 1, 1)
                        end_date = datetime(today.year, today.month, 1) - timedelta(days=1)
                    date_range = (start_date, end_date)
                    
                elif date_range_type == 'Custom':
                    # For custom, we'd show a date picker dialog
                    from tkcalendar import DateEntry
                    
                    # Create custom date range dialog
                    date_dialog = tk.Toplevel(self.parent)
                    date_dialog.title("Select Date Range")
                    date_dialog.geometry("300x180")
                    date_dialog.configure(bg=self.bg_dark)
                    date_dialog.transient(self.parent)
                    date_dialog.grab_set()
                    
                    # Create content
                    frame = ttk.Frame(date_dialog, padding=15)
                    frame.pack(fill=tk.BOTH, expand=True)
                    
                    ttk.Label(frame, text="Start Date:").grid(row=0, column=0, sticky=tk.W, pady=5)
                    ttk.Label(frame, text="End Date:").grid(row=1, column=0, sticky=tk.W, pady=5)
                    
                    # Date pickers
                    start_date_picker = DateEntry(frame, width=12, background=self.accent_color,
                                                foreground=self.text_color, borderwidth=2)
                    start_date_picker.grid(row=0, column=1, padx=5, pady=5)
                    
                    end_date_picker = DateEntry(frame, width=12, background=self.accent_color,
                                              foreground=self.text_color, borderwidth=2)
                    end_date_picker.grid(row=1, column=1, padx=5, pady=5)
                    
                    # Set default dates (30 days ago to today)
                    start_date_picker.set_date(today - timedelta(days=30))
                    end_date_picker.set_date(today)
                    
                    # Variables to store selected dates
                    selected_start_date = [None]
                    selected_end_date = [None]
                    
                    def apply_custom_dates():
                        selected_start_date[0] = start_date_picker.get_date()
                        selected_end_date[0] = end_date_picker.get_date()
                        date_dialog.destroy()
                    
                    # Add buttons
                    button_frame = ttk.Frame(frame)
                    button_frame.grid(row=2, column=0, columnspan=2, pady=15)
                    
                    ttk.Button(button_frame, text="Apply", command=apply_custom_dates).pack(side=tk.LEFT, padx=5)
                    ttk.Button(button_frame, text="Cancel", command=date_dialog.destroy).pack(side=tk.LEFT, padx=5)
                    
                    # Wait for dialog to close
                    self.parent.wait_window(date_dialog)
                    
                    # Check if dates were selected
                    if selected_start_date[0] and selected_end_date[0]:
                        date_range = (selected_start_date[0], selected_end_date[0])
                    else:
                        return  # User cancelled, abort filtering
            
            # Build filters dictionary
            filters = {}
            if status != 'All':
                filters['status'] = status
            if date_range:
                filters['date_range'] = date_range
            if fund != 'All':
                filters['fund'] = fund
            if search:
                filters['search'] = search
            
            # Show loading indicator
            self.status_var.set("Loading data...")
            
            # Create loading overlay
            self._show_loading_overlay()
            
            # Use threading to prevent UI freeze
            def load_data_thread():
                try:
                    # Load filtered data
                    filtered_data = self._get_filtered_data(filters)
                    
                    # Update UI in the main thread
                    self.parent.after(0, lambda: self._update_ui_with_data(filtered_data, filters))
                
                except Exception as e:
                    logger.error(f"Error applying filters: {str(e)}")
                    # Update UI in the main thread
                    self.parent.after(0, lambda: self._handle_filter_error(str(e)))
            
            # Start loading thread
            thread = threading.Thread(target=load_data_thread)
            thread.daemon = True
            thread.start()
            
        except Exception as e:
            logger.error(f"Error setting up filters: {str(e)}")
            self.status_var.set(f"Error: {str(e)}")
    
    def _get_filtered_data(self, filters):
        """Get filtered data in a background thread"""
        # Query the database with filters
        query = """
        SELECT i.id, i.invoice_number, i.date, v.name as vendor, i.description,
               i.amount, i.status, i.due_date, f.fund
        FROM invoices i
        LEFT JOIN vendors v ON i.vendor_id = v.id
        LEFT JOIN funds f ON i.fund_id = f.id
        """
        
        # Add WHERE clause for filters
        where_clauses = []
        params = []
        
        if filters:
            # Status filter
            if filters.get('status') and filters['status'] != 'All':
                where_clauses.append("i.status = %s")
                params.append(filters['status'])
            
            # Date range filter
            if filters.get('date_range'):
                if filters['date_range'][0] and filters['date_range'][1]:
                    where_clauses.append("i.date BETWEEN %s AND %s")
                    params.extend(filters['date_range'])
            
            # Fund filter
            if filters.get('fund') and filters['fund'] != 'All':
                where_clauses.append("f.fund = %s")
                params.append(filters['fund'])
            
            # Search terms
            if filters.get('search'):
                search_terms = filters['search'].split()
                for term in search_terms:
                    search_clause = """
                    (i.invoice_number LIKE %s OR 
                     v.name LIKE %s OR 
                     i.description LIKE %s OR
                     f.fund LIKE %s)
                    """
                    where_clauses.append(search_clause)
                    search_param = f"%{term}%"
                    params.extend([search_param, search_param, search_param, search_param])
        
        # Add WHERE clause if we have conditions
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        # Add ORDER BY
        query += " ORDER BY i.date DESC"
        
        # Execute query
        return self.db_manager.db.execute_query(query, params)
    
    def _update_ui_with_data(self, result, filters):
        """Update the UI with data (called in the main thread)"""
        try:
            # Clear current data
            for item in self.invoice_tree.get_children():
                self.invoice_tree.delete(item)
                
            if result.get('error'):
                self.status_var.set(f"Error: {result['error']}")
                self._hide_loading_overlay()
                return
                
            # Process results
            for i, row in enumerate(result.get('rows', [])):
                # Format values
                invoice_id = row[0]
                invoice_number = row[1] or ""
                date_str = row[2].strftime('%Y-%m-%d') if row[2] else ""
                vendor = row[3] or ""
                description = row[4] or ""
                
                # Format amount as currency
                amount = float(row[5]) if row[5] is not None else 0.0
                amount_str = f"${amount:,.2f}"
                
                status = row[6] or ""
                due_date_str = row[7].strftime('%Y-%m-%d') if row[7] else ""
                fund = row[8] or ""
                
                # Insert with alternating row background
                tag = "odd" if i % 2 == 1 else "even"
                
                # Add status-based tag
                if status.lower() == "paid":
                    tag = f"{tag}_paid"
                elif status.lower() == "overdue":
                    tag = f"{tag}_overdue"
                
                self.invoice_tree.insert(
                    "", tk.END, 
                    values=(invoice_id, invoice_number, date_str, vendor, description, 
                            amount_str, status, due_date_str, fund),
                    tags=(tag,)
                )
            
            # Configure row appearance
            self.invoice_tree.tag_configure("odd", background=self.bg_medium)
            self.invoice_tree.tag_configure("even", background=self.bg_light)
            self.invoice_tree.tag_configure("odd_paid", background=self.bg_medium, foreground="#4caf50")
            self.invoice_tree.tag_configure("even_paid", background=self.bg_light, foreground="#4caf50")
            self.invoice_tree.tag_configure("odd_overdue", background="#5a2a2a", foreground="#ff9800")
            self.invoice_tree.tag_configure("even_overdue", background="#4a1a1a", foreground="#ff9800")
            
            # Update summary cards
            self._update_summary_cards()
            
            # Update status
            row_count = len(result.get('rows', []))
            self.status_var.set(f"Applied filters: {row_count} invoices found")
            
            # Remove loading indicator
            self._hide_loading_overlay()
            
        except Exception as e:
            logger.error(f"Error updating UI with data: {str(e)}")
            self.status_var.set(f"Error updating UI: {str(e)}")
            self._hide_loading_overlay()
    
    def _handle_filter_error(self, error_message):
        """Handle errors in the filtering process (called in the main thread)"""
        self.status_var.set(f"Error: {error_message}")
        self._hide_loading_overlay()

    def _show_loading_overlay(self):
        """Show a loading animation overlay"""
        # Create a semi-transparent overlay over the invoice table
        if hasattr(self, 'loading_frame') and self.loading_frame:
            return  # Already showing
            
        # Get the table position and size
        table_frame = self.invoice_tree.master
        x = table_frame.winfo_rootx() - self.parent.winfo_rootx()
        y = table_frame.winfo_rooty() - self.parent.winfo_rooty()
        width = table_frame.winfo_width()
        height = table_frame.winfo_height()
        
        # Create overlay frame - fixing transparency issue
        self.loading_frame = tk.Frame(self.parent, bg=self.bg_dark)
        self.loading_frame.place(x=x, y=y, width=width, height=height)
        
        # Fix transparency by setting a partially transparent background
        self.loading_frame.configure(bg='#1e1e2e')  # Using explicit color instead of self.bg_dark
        
        # Add gradient effect for better appearance
        canvas = tk.Canvas(self.loading_frame, highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)
        canvas.configure(bg='#1e1e2e')
        
        # Semi-transparent overlay
        canvas.create_rectangle(0, 0, width, height, fill='#1e1e2e', stipple='gray50')
        
        # Add loading indicator with better visibility
        loading_label = tk.Label(self.loading_frame, text="Loading data...", font=(self.font_family, 14, 'bold'),
                                bg='#1e1e2e', fg=self.highlight_color)
        loading_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        # Add animation dots
        self.dots_count = 0
        
        def update_dots():
            if not hasattr(self, 'loading_frame') or not self.loading_frame:
                return  # Overlay was destroyed
                
            self.dots_count = (self.dots_count + 1) % 4
            dots = "." * self.dots_count
            loading_label.config(text=f"Loading data{dots}")
            self.parent.after(500, update_dots)
        
        # Start animation
        update_dots()
    
    def _hide_loading_overlay(self):
        """Hide the loading animation overlay"""
        if hasattr(self, 'loading_frame') and self.loading_frame:
            self.loading_frame.destroy()
            self.loading_frame = None
    
    def _show_invoice_details(self, event):
        """Show detailed invoice information when double-clicking an invoice"""
        # Get selected item
        selection = self.invoice_tree.selection()
        if not selection:
            return
            
        # Get invoice data
        values = self.invoice_tree.item(selection[0], 'values')
        if not values or len(values) < 9:
            return
            
        # Extract invoice information
        invoice_id = values[0]
        invoice_number = values[1]
        date_str = values[2]
        vendor = values[3]
        description = values[4]
        amount_str = values[5]
        status = values[6]
        due_date_str = values[7]
        fund = values[8]
        
        # Create detail dialog
        detail_window = tk.Toplevel(self.parent)
        detail_window.title(f"Invoice Details: {invoice_number}")
        detail_window.geometry("500x450")
        detail_window.configure(bg=self.bg_dark)
        detail_window.transient(self.parent)
        detail_window.grab_set()
        
        # Create gradient header
        header_frame = tk.Frame(detail_window, height=60, bg=self.bg_dark)
        header_frame.pack(fill=tk.X)
        
        # Canvas for gradient
        header_canvas = tk.Canvas(header_frame, height=60, bg=self.bg_dark, highlightthickness=0)
        header_canvas.pack(fill=tk.X)
        
        # Draw gradient
        width = 500  # same as window width
        for i in range(60):
            # Calculate gradient color (purple to dark purple)
            r1, g1, b1 = 126, 87, 194  # #7e57c2
            r2, g2, b2 = 63, 43, 97    # #3f2b61
            
            r = int(r1 + (r2-r1) * (i/60))
            g = int(g1 + (g2-g1) * (i/60))
            b = int(b1 + (b2-b1) * (i/60))
            
            color = f'#{r:02x}{g:02x}{b:02x}'
            header_canvas.create_line(0, i, width, i, fill=color)
        
        # Add title to header
        header_canvas.create_text(20, 30, text=f"Invoice: {invoice_number}", 
                                 fill=self.text_color, font=(self.font_family, 16, 'bold'),
                                 anchor='w')
        
        # Create content frame
        content_frame = ttk.Frame(detail_window, padding=15)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create two columns
        left_col = ttk.Frame(content_frame)
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        right_col = ttk.Frame(content_frame)
        right_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Left column - basic info
        ttk.Label(left_col, text="Date:", font=(self.font_family, 10, 'bold')).pack(anchor=tk.W, pady=(0, 2))
        ttk.Label(left_col, text=date_str).pack(anchor=tk.W, pady=(0, 10))
        
        ttk.Label(left_col, text="Vendor:", font=(self.font_family, 10, 'bold')).pack(anchor=tk.W, pady=(0, 2))
        ttk.Label(left_col, text=vendor).pack(anchor=tk.W, pady=(0, 10))
        
        ttk.Label(left_col, text="Amount:", font=(self.font_family, 10, 'bold')).pack(anchor=tk.W, pady=(0, 2))
        ttk.Label(left_col, text=amount_str).pack(anchor=tk.W, pady=(0, 10))
        
        ttk.Label(left_col, text="Status:", font=(self.font_family, 10, 'bold')).pack(anchor=tk.W, pady=(0, 2))
        status_frame = ttk.Frame(left_col)
        status_frame.pack(anchor=tk.W, pady=(0, 10), fill=tk.X)
        
        # Create colored status indicator
        status_color = "#4caf50" if status.lower() == "paid" else "#f44336" if status.lower() == "overdue" else "#ffc107"
        status_indicator = tk.Canvas(status_frame, width=12, height=12, bg=self.bg_dark, highlightthickness=0)
        status_indicator.create_oval(2, 2, 10, 10, fill=status_color, outline="")
        status_indicator.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Label(status_frame, text=status).pack(side=tk.LEFT)
        
        # Right column - more info
        ttk.Label(right_col, text="Due Date:", font=(self.font_family, 10, 'bold')).pack(anchor=tk.W, pady=(0, 2))
        ttk.Label(right_col, text=due_date_str).pack(anchor=tk.W, pady=(0, 10))
        
        ttk.Label(right_col, text="Fund:", font=(self.font_family, 10, 'bold')).pack(anchor=tk.W, pady=(0, 2))
        ttk.Label(right_col, text=fund).pack(anchor=tk.W, pady=(0, 10))
        
        ttk.Label(right_col, text="Invoice ID:", font=(self.font_family, 10, 'bold')).pack(anchor=tk.W, pady=(0, 2))
        ttk.Label(right_col, text=invoice_id).pack(anchor=tk.W, pady=(0, 10))
        
        # Bottom section - description
        desc_frame = ttk.LabelFrame(content_frame, text="Description")
        desc_frame.pack(fill=tk.X, pady=(15, 0), side=tk.BOTTOM)
        
        desc_text = tk.Text(desc_frame, height=5, width=50, bg=self.bg_medium, fg=self.text_color,
                          font=(self.font_family, 10))
        desc_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        desc_text.insert("1.0", description)
        desc_text.config(state=tk.DISABLED)  # Make read-only
        
        # Get related documents if any
        documents_frame = ttk.LabelFrame(content_frame, text="Related Documents")
        documents_frame.pack(fill=tk.X, pady=(15, 0), side=tk.BOTTOM)
        
        # Query for related documents
        documents_query = """
        SELECT id, filename, document_type, upload_date 
        FROM documents 
        WHERE invoice_id = %s
        ORDER BY upload_date DESC
        """
        
        result = self.db_manager.db.execute_query(documents_query, [invoice_id])
        
        if result.get('error') or not result.get('rows'):
            ttk.Label(documents_frame, text="No related documents found").pack(padx=5, pady=10)
        else:
            # Create mini-treeview for documents
            doc_tree = ttk.Treeview(documents_frame, columns=("filename", "type", "date"), show="headings", height=3)
            doc_tree.heading("filename", text="Filename")
            doc_tree.heading("type", text="Type")
            doc_tree.heading("date", text="Date")
            
            doc_tree.column("filename", width=200)
            doc_tree.column("type", width=100)
            doc_tree.column("date", width=100)
            
            doc_tree.pack(fill=tk.X, padx=5, pady=5)
            
            # Add documents
            for doc in result['rows']:
                doc_id, filename, doc_type, upload_date = doc
                date_str = upload_date.strftime('%Y-%m-%d') if upload_date else ""
                doc_tree.insert("", tk.END, values=(filename, doc_type, date_str))
        
        # Add buttons
        button_frame = ttk.Frame(detail_window)
        button_frame.pack(fill=tk.X, pady=15)
        
        def edit_invoice():
            # Show edit dialog
            messagebox.showinfo("Edit Invoice", "Invoice editing would open here", parent=detail_window)
            detail_window.destroy()
        
        edit_button = ttk.Button(button_frame, text="Edit Invoice", command=edit_invoice)
        edit_button.pack(side=tk.LEFT, padx=5)
        
        close_button = ttk.Button(button_frame, text="Close", command=detail_window.destroy)
        close_button.pack(side=tk.RIGHT, padx=5)

    def _create_invoice_table(self):
        """Create the invoice data table"""
        # Create frame for the table
        table_frame = ttk.Frame(self.main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        
        # Create treeview for invoices
        self.invoice_tree = ttk.Treeview(table_frame, columns=(
            "id", "invoice_number", "date", "vendor", "description", 
            "amount", "status", "due_date", "fund"
        ))
        
        # Configure columns
        self.invoice_tree.heading("id", text="ID")
        self.invoice_tree.heading("invoice_number", text="Invoice #")
        self.invoice_tree.heading("date", text="Date")
        self.invoice_tree.heading("vendor", text="Vendor")
        self.invoice_tree.heading("description", text="Description")
        self.invoice_tree.heading("amount", text="Amount")
        self.invoice_tree.heading("status", text="Status")
        self.invoice_tree.heading("due_date", text="Due Date")
        self.invoice_tree.heading("fund", text="Fund")
        
        # Set column widths
        self.invoice_tree.column("id", width=50)
        self.invoice_tree.column("invoice_number", width=100)
        self.invoice_tree.column("date", width=100)
        self.invoice_tree.column("vendor", width=150)
        self.invoice_tree.column("description", width=200)
        self.invoice_tree.column("amount", width=100)
        self.invoice_tree.column("status", width=100)
        self.invoice_tree.column("due_date", width=100)
        self.invoice_tree.column("fund", width=100)
        
        # Hide the first column (tree column)
        self.invoice_tree["show"] = "headings"
        
        # Add scrollbars
        y_scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.invoice_tree.yview)
        x_scrollbar = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.invoice_tree.xview)
        self.invoice_tree.configure(yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set)
        
        # Add tooltip support
        self.invoice_tree.bind("<Motion>", self._show_tree_tooltip)
        
        # Add double-click handler for invoice details
        self.invoice_tree.bind("<Double-1>", self._show_invoice_details)
        
        # Enable sorting when clicking on headers
        for col in self.invoice_tree["columns"]:
            self.invoice_tree.heading(col, command=lambda _col=col: self._sort_tree_column(_col))
        
        # Pack components
        y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        x_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.invoice_tree.pack(fill=tk.BOTH, expand=True)
    
    def _sort_tree_column(self, col):
        """Sort treeview by the selected column"""
        # Get all tree items
        data = [(self.invoice_tree.set(item, col), item) for item in self.invoice_tree.get_children('')]
        
        # Determine if we're sorting numerically
        numeric_cols = ['amount', 'id']
        date_cols = ['date', 'due_date']
        
        # Sort function that handles different types
        def sort_func(item):
            value = item[0]
            if col in numeric_cols:
                # Remove currency symbol and commas for sorting
                try:
                    # Handle edge cases like empty strings or non-numeric values
                    cleaned_value = value.replace('$', '').replace(',', '')
                    return float(cleaned_value) if cleaned_value else 0
                except (ValueError, AttributeError):
                    return 0
            elif col in date_cols:
                # Sort dates properly
                if not value:
                    return datetime.min
                try:
                    return datetime.strptime(value, '%Y-%m-%d')
                except (ValueError, TypeError):
                    return datetime.min
            else:
                # Default string sort - handle None values
                return str(value).lower() if value is not None else ""
        
        # Sort the data
        data.sort(key=sort_func, reverse=self.sort_reverse)
        
        # Rearrange items in sorted positions
        for index, (_, item) in enumerate(data):
            self.invoice_tree.move(item, '', index)
        
        # Switch sort direction next time this column is clicked
        self.sort_reverse = not self.sort_reverse
        
        # Update heading to indicate sort direction
        for heading in self.invoice_tree["columns"]:
            # Get current heading text without any arrows
            current_text = self.invoice_tree.heading(heading)["text"]
            base_text = current_text
            if " ↓" in current_text:
                base_text = current_text.replace(" ↓", "")
            elif " ↑" in current_text:
                base_text = current_text.replace(" ↑", "")
            
            # Set the appropriate heading text
            if heading == col:
                direction = " ↓" if self.sort_reverse else " ↑"
                self.invoice_tree.heading(heading, text=base_text + direction)
            else:
                self.invoice_tree.heading(heading, text=base_text) 

    def _update_summary_cards(self):
        """Update the summary card values based on database data"""
        try:
            # Load summary metrics for each year and status
            current_year = datetime.now().year
            
            # Get paid amounts by year
            years_query = """
            SELECT EXTRACT(YEAR FROM date) as year, SUM(amount) as total
            FROM invoices
            WHERE status = 'Paid'
            GROUP BY EXTRACT(YEAR FROM date)
            ORDER BY year DESC
            """
            years_result = self.db_manager.db.execute_query(years_query)
            
            # Get unpaid and overdue totals
            status_query = """
            SELECT status, SUM(amount) as total
            FROM invoices
            WHERE status IN ('Unpaid', 'Overdue')
            GROUP BY status
            """
            status_result = self.db_manager.db.execute_query(status_query)
            
            # Process year totals
            year_totals = {}
            if not years_result.get('error') and years_result.get('rows'):
                for row in years_result['rows']:
                    year = int(row[0])
                    total = float(row[1]) if row[1] is not None else 0.0
                    year_totals[year] = total
            
            # Process status totals
            status_totals = {}
            if not status_result.get('error') and status_result.get('rows'):
                for row in status_result['rows']:
                    status = row[0]
                    total = float(row[1]) if row[1] is not None else 0.0
                    status_totals[status] = total
            
            # Check if we have summary cards to update
            if not hasattr(self, 'summary_cards') or not self.summary_cards:
                return
            
            # Update card values
            # Current year card
            current_year_total = year_totals.get(current_year, 0)
            self._update_card_value('current_year', f"${current_year_total:,.2f}")
            
            # Previous year card
            prev_year_total = year_totals.get(current_year - 1, 0)
            self._update_card_value('prev_year', f"${prev_year_total:,.2f}")
            
            # 2023 card
            year_2023_total = year_totals.get(2023, 0)
            self._update_card_value('year_2023', f"${year_2023_total:,.2f}")
            
            # Unpaid card
            unpaid_total = status_totals.get('Unpaid', 0)
            self._update_card_value('unpaid', f"${unpaid_total:,.2f}")
            
            # Overdue card
            overdue_total = status_totals.get('Overdue', 0)
            self._update_card_value('overdue', f"${overdue_total:,.2f}")
            
        except Exception as e:
            logger.error(f"Failed to update summary cards: {str(e)}")
    
    def _update_card_value(self, card_key, value):
        """Update the value of a specific summary card"""
        if card_key in self.summary_cards:
            card = self.summary_cards[card_key]
            self.cards_canvas.itemconfig(card['value'], text=value)

    def _export_results(self):
        """Export the current results to a CSV file"""
        try:
            from tkinter import filedialog
            import csv
            
            # Get file path from user
            file_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
            )
            
            if not file_path:
                return  # User cancelled
            
            # Get data from treeview
            if not hasattr(self, 'invoice_tree') or not self.invoice_tree.get_children():
                messagebox.showinfo("Export", "No data to export")
                return
            
            # Show loading indication
            self.status_var.set("Exporting data...")
            
            # Use a thread for export to avoid freezing UI
            def export_thread():
                try:
                    # Export headers and data
                    headers = self.invoice_tree['columns']
                    with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                        writer = csv.writer(csvfile)
                        
                        # Write headers - clean up headers to remove sort indicators
                        clean_headers = []
                        for col in headers:
                            header_text = self.invoice_tree.heading(col)["text"]
                            if " ↓" in header_text:
                                header_text = header_text.replace(" ↓", "")
                            elif " ↑" in header_text:
                                header_text = header_text.replace(" ↑", "")
                            clean_headers.append(header_text)
                        
                        writer.writerow(clean_headers)
                        
                        # Write data rows - get all values from tree
                        for item_id in self.invoice_tree.get_children():
                            row_data = []
                            for col in headers:
                                # Clean up currency formatting for export
                                value = self.invoice_tree.set(item_id, col)
                                if col == 'amount' and value.startswith('$'):
                                    # Remove $ and commas for better data analysis
                                    value = value.replace('$', '').replace(',', '')
                                row_data.append(value)
                            writer.writerow(row_data)
                    
                    # Update UI in the main thread
                    self.parent.after(0, lambda: self._export_complete(file_path))
                    
                except Exception as e:
                    logger.error(f"Export error: {str(e)}")
                    # Update UI in the main thread
                    self.parent.after(0, lambda: self._export_error(str(e)))
            
            # Start export thread
            thread = threading.Thread(target=export_thread)
            thread.daemon = True
            thread.start()
            
        except Exception as e:
            logger.error(f"Failed to export data: {str(e)}")
            self.status_var.set(f"Export failed: {str(e)}")
            messagebox.showerror("Export Error", f"Failed to export data: {str(e)}")
    
    def _export_complete(self, file_path):
        """Called when export completes successfully (in main thread)"""
        self.status_var.set(f"Exported data to {file_path}")
        messagebox.showinfo("Export Complete", f"Data has been exported to {file_path}")
    
    def _export_error(self, error_message):
        """Called when export encounters an error (in main thread)"""
        self.status_var.set(f"Export failed: {error_message}")
        messagebox.showerror("Export Error", f"Failed to export data: {error_message}")

    def _show_schema_inspector(self):
        """Open the schema inspector dialog"""
        try:
            # Create schema inspector dialog
            inspector_window = tk.Toplevel(self.parent)
            inspector_window.title("Database Schema Inspector")
            inspector_window.geometry("800x600")
            inspector_window.configure(bg=self.bg_dark)
            inspector_window.transient(self.parent)
            
            # Create main content frame
            main_frame = ttk.Frame(inspector_window, padding=15)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # Create header
            header_label = ttk.Label(main_frame, text="Database Schema Inspector", 
                                   font=(self.font_family, 16, 'bold'))
            header_label.pack(pady=(0, 15), anchor=tk.W)
            
            # Create table selector
            selector_frame = ttk.Frame(main_frame)
            selector_frame.pack(fill=tk.X, pady=(0, 15))
            
            ttk.Label(selector_frame, text="Select Table:").pack(side=tk.LEFT, padx=(0, 10))
            
            # Get list of tables
            tables_query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema='public'
            ORDER BY table_name
            """
            
            result = self.db_manager.db.execute_query(tables_query)
            
            if result.get('error') or not result.get('rows'):
                tables = []
            else:
                tables = [row[0] for row in result['rows']]
            
            # Table combobox
            table_var = tk.StringVar()
            table_combo = ttk.Combobox(selector_frame, textvariable=table_var, values=tables, width=30)
            table_combo.pack(side=tk.LEFT, padx=(0, 10))
            
            if tables:
                table_combo.current(0)
            
            # Inspect button
            inspect_button = ttk.Button(selector_frame, text="Inspect Table")
            inspect_button.pack(side=tk.LEFT)
            
            # Create notebook for table info
            notebook = ttk.Notebook(main_frame)
            notebook.pack(fill=tk.BOTH, expand=True)
            
            # Structure tab
            structure_frame = ttk.Frame(notebook, padding=10)
            notebook.add(structure_frame, text="Structure")
            
            # Columns tab
            columns_frame = ttk.Frame(notebook, padding=10)
            notebook.add(columns_frame, text="Columns")
            
            # Data tab
            data_frame = ttk.Frame(notebook, padding=10)
            notebook.add(data_frame, text="Sample Data")
            
            # Issues tab
            issues_frame = ttk.Frame(notebook, padding=10)
            notebook.add(issues_frame, text="Potential Issues")
            
            # Function to inspect selected table
            def inspect_table():
                selected_table = table_var.get()
                if not selected_table:
                    return
                
                # Clear previous content
                for widget in structure_frame.winfo_children():
                    widget.destroy()
                for widget in columns_frame.winfo_children():
                    widget.destroy()
                for widget in data_frame.winfo_children():
                    widget.destroy()
                for widget in issues_frame.winfo_children():
                    widget.destroy()
                
                # Get table structure
                structure_query = f"""
                SELECT column_name, data_type, character_maximum_length,
                       is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position
                """
                
                structure_result = self.db_manager.db.execute_query(structure_query, [selected_table])
                
                if structure_result.get('error'):
                    ttk.Label(structure_frame, text=f"Error: {structure_result['error']}").pack()
                    return
                
                # Create structure tree
                structure_tree = ttk.Treeview(structure_frame, columns=("name", "type", "length", "nullable", "default"))
                structure_tree.heading("name", text="Column Name")
                structure_tree.heading("type", text="Data Type")
                structure_tree.heading("length", text="Length")
                structure_tree.heading("nullable", text="Nullable")
                structure_tree.heading("default", text="Default")
                
                structure_tree.column("#0", width=0, stretch=tk.NO)
                structure_tree.column("name", width=150)
                structure_tree.column("type", width=100)
                structure_tree.column("length", width=80)
                structure_tree.column("nullable", width=80)
                structure_tree.column("default", width=150)
                
                structure_tree.pack(fill=tk.BOTH, expand=True)
                
                # Add scrollbar
                structure_scrollbar = ttk.Scrollbar(structure_frame, orient=tk.VERTICAL, command=structure_tree.yview)
                structure_tree.configure(yscrollcommand=structure_scrollbar.set)
                structure_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                
                # Populate structure tree
                for row in structure_result['rows']:
                    column_name, data_type, max_length, nullable, default = row
                    length_str = str(max_length) if max_length is not None else ""
                    nullable_str = "YES" if nullable == "YES" else "NO"
                    default_str = str(default) if default is not None else ""
                    
                    structure_tree.insert("", tk.END, values=(column_name, data_type, length_str, nullable_str, default_str))
                
                # Create columns analysis in columns tab
                columns_text = tk.Text(columns_frame, wrap=tk.WORD, bg=self.bg_medium, fg=self.text_color,
                                     font=('Consolas', 11))
                columns_text.pack(fill=tk.BOTH, expand=True)
                
                # Add scrollbar for columns text
                columns_scrollbar = ttk.Scrollbar(columns_frame, orient=tk.VERTICAL, command=columns_text.yview)
                columns_text.configure(yscrollcommand=columns_scrollbar.set)
                columns_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                
                # Add column analysis
                columns_text.insert(tk.END, f"Column Analysis for Table: {selected_table}\n\n")
                
                # Get column statistics
                for col in [row[0] for row in structure_result['rows']]:
                    # Get stats for this column
                    stats_query = f"""
                    SELECT 
                        COUNT(*) as total_rows,
                        COUNT({col}) as non_null_count,
                        COUNT(DISTINCT {col}) as unique_values
                    FROM {selected_table}
                    """
                    
                    try:
                        stats_result = self.db_manager.db.execute_query(stats_query)
                        
                        if not stats_result.get('error') and stats_result.get('rows'):
                            total, non_null, unique = stats_result['rows'][0]
                            
                            columns_text.insert(tk.END, f"Column: {col}\n")
                            columns_text.insert(tk.END, f"  - Total rows: {total}\n")
                            if total > 0:
                                columns_text.insert(tk.END, f"  - Non-null values: {non_null} ({non_null/total*100:.1f}% filled)\n")
                                if non_null > 0:
                                    columns_text.insert(tk.END, f"  - Unique values: {unique} ({unique/non_null*100:.1f}% unique)\n")
                                else:
                                    columns_text.insert(tk.END, f"  - Unique values: 0 (0.0% unique)\n")
                                
                                # Determine if it could be a key
                                if unique == total and non_null == total and total > 0:
                                    columns_text.insert(tk.END, "  - Potential primary key (unique, non-null)\n")
                                elif unique == non_null and non_null > 0:
                                    columns_text.insert(tk.END, "  - Potential unique key (all values unique where present)\n")
                            else:
                                columns_text.insert(tk.END, "  - Table is empty\n")
                            
                            columns_text.insert(tk.END, "\n")
                    except Exception as e:
                        columns_text.insert(tk.END, f"  - Error analyzing column {col}: {str(e)}\n\n")
                
                # Make columns text read-only
                columns_text.configure(state=tk.DISABLED)
                
                # Get sample data
                data_query = f"""
                SELECT *
                FROM {selected_table}
                LIMIT 10
                """
                
                data_result = self.db_manager.db.execute_query(data_query)
                
                if data_result.get('error'):
                    ttk.Label(data_frame, text=f"Error: {data_result['error']}").pack()
                else:
                    if not data_result.get('rows'):
                        ttk.Label(data_frame, text="No data found in this table").pack(pady=10)
                    else:
                        # Create data tree
                        data_columns = [desc[0] for desc in data_result['description']]
                        
                        data_tree = ttk.Treeview(data_frame, columns=data_columns, show='headings')
                        
                        # Set headings
                        for col in data_columns:
                            data_tree.heading(col, text=col)
                            data_tree.column(col, width=100)
                        
                        # Add scrollbars
                        data_frame_with_scrollbars = ttk.Frame(data_frame)
                        data_frame_with_scrollbars.pack(fill=tk.BOTH, expand=True)
                        
                        data_tree.pack(in_=data_frame_with_scrollbars, side=tk.TOP, fill=tk.BOTH, expand=True)
                        
                        data_y_scrollbar = ttk.Scrollbar(data_frame_with_scrollbars, orient=tk.VERTICAL, command=data_tree.yview)
                        data_tree.configure(yscrollcommand=data_y_scrollbar.set)
                        data_y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                        
                        data_x_scrollbar = ttk.Scrollbar(data_frame, orient=tk.HORIZONTAL, command=data_tree.xview)
                        data_tree.configure(xscrollcommand=data_x_scrollbar.set)
                        data_x_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
                        
                        # Add data
                        for row in data_result['rows']:
                            formatted_row = []
                            for val in row:
                                if isinstance(val, (datetime, date)):
                                    formatted_row.append(val.strftime('%Y-%m-%d'))
                                elif val is None:
                                    formatted_row.append("")
                                else:
                                    formatted_row.append(str(val))
                            
                            data_tree.insert("", tk.END, values=formatted_row)
                
                # Identify potential issues
                issues_text = tk.Text(issues_frame, wrap=tk.WORD, bg=self.bg_medium, fg=self.text_color,
                                    font=('Consolas', 11))
                issues_text.pack(fill=tk.BOTH, expand=True)
                
                # Add scrollbar for issues text
                issues_scrollbar = ttk.Scrollbar(issues_frame, orient=tk.VERTICAL, command=issues_text.yview)
                issues_text.configure(yscrollcommand=issues_scrollbar.set)
                issues_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                
                # Check for common issues
                issues_text.insert(tk.END, f"Potential Issues for Table: {selected_table}\n\n")
                issue_count = 0
                
                # Check for missing primary key
                pk_query = """
                SELECT COUNT(*)
                FROM information_schema.table_constraints
                WHERE table_name = %s
                AND constraint_type = 'PRIMARY KEY'
                """
                
                pk_result = self.db_manager.db.execute_query(pk_query, [selected_table])
                
                if not pk_result.get('error') and pk_result.get('rows'):
                    pk_count = pk_result['rows'][0][0]
                    if pk_count == 0:
                        issues_text.insert(tk.END, "⚠️ No primary key defined for this table.\n")
                        issues_text.insert(tk.END, "   Consider adding a primary key for better data integrity.\n\n")
                        issue_count += 1
                
                # Check for columns with potential type issues
                for col, data_type in [(row[0], row[1]) for row in structure_result['rows']]:
                    if data_type == 'text':
                        # Check if the column might contain dates
                        date_check_query = f"""
                        SELECT COUNT(*) as matching_count
                        FROM {selected_table}
                        WHERE {col} ~ '^\d{{4}}-\d{{2}}-\d{{2}}$'
                        """
                        
                        try:
                            date_result = self.db_manager.db.execute_query(date_check_query)
                            if not date_result.get('error') and date_result.get('rows'):
                                matching_count = date_result['rows'][0][0]
                                total_count_query = f"SELECT COUNT(*) FROM {selected_table} WHERE {col} IS NOT NULL"
                                total_result = self.db_manager.db.execute_query(total_count_query)
                                
                                if not total_result.get('error') and total_result.get('rows'):
                                    total_count = total_result['rows'][0][0]
                                    if total_count > 0 and matching_count / total_count > 0.9:  # If over 90% match date pattern
                                        issues_text.insert(tk.END, f"⚠️ Column '{col}' is text but contains date-like values.\n")
                                        issues_text.insert(tk.END, f"   Consider changing to DATE type for better data handling.\n\n")
                                        issue_count += 1
                        except Exception:
                            pass  # Skip if the regex check fails
                            
                        # Check if the column might contain numeric values
                        numeric_check_query = f"""
                        SELECT COUNT(*) as matching_count
                        FROM {selected_table}
                        WHERE {col} ~ '^\d+(\.\d+)?$'
                        """
                        
                        try:
                            numeric_result = self.db_manager.db.execute_query(numeric_check_query)
                            if not numeric_result.get('error') and numeric_result.get('rows'):
                                matching_count = numeric_result['rows'][0][0]
                                total_count_query = f"SELECT COUNT(*) FROM {selected_table} WHERE {col} IS NOT NULL"
                                total_result = self.db_manager.db.execute_query(total_count_query)
                                
                                if not total_result.get('error') and total_result.get('rows'):
                                    total_count = total_result['rows'][0][0]
                                    if total_count > 0 and matching_count / total_count > 0.9:  # If over 90% match numeric pattern
                                        issues_text.insert(tk.END, f"⚠️ Column '{col}' is text but contains numeric values.\n")
                                        issues_text.insert(tk.END, f"   Consider changing to NUMERIC type for better data handling.\n\n")
                                        issue_count += 1
                        except Exception:
                            pass  # Skip if the regex check fails
                
                # Check for nullable columns that could be NOT NULL
                for col in [row[0] for row in structure_result['rows'] if row[3] == 'YES']:  # Get nullable columns
                    null_check_query = f"""
                    SELECT COUNT(*) as null_count
                    FROM {selected_table}
                    WHERE {col} IS NULL
                    """
                    
                    try:
                        null_result = self.db_manager.db.execute_query(null_check_query)
                        if not null_result.get('error') and null_result.get('rows'):
                            null_count = null_result['rows'][0][0]
                            if null_count == 0:
                                issues_text.insert(tk.END, f"ℹ️ Column '{col}' is nullable but contains no NULL values.\n")
                                issues_text.insert(tk.END, f"   Consider setting as NOT NULL to enforce data integrity.\n\n")
                                issue_count += 1
                    except Exception:
                        pass  # Skip if the check fails
                
                # If no issues found
                if issue_count == 0:
                    issues_text.insert(tk.END, "✅ No potential issues detected for this table.\n")
                
                # Make issues text read-only
                issues_text.configure(state=tk.DISABLED)
            
            # Link the inspect button
            inspect_button.configure(command=inspect_table)
            
            # Inspect the initially selected table
            if tables:
                inspector_window.after(100, inspect_table)
                
        except Exception as e:
            logger.error(f"Failed to open schema inspector: {str(e)}")
            self.status_var.set(f"Error opening schema inspector: {str(e)}")
            messagebox.showerror("Error", f"Failed to open schema inspector: {str(e)}")

    def _create_filter_section(self):
        """Create filter controls for invoices"""
        # Create frame for filters
        filter_frame = ttk.LabelFrame(self.main_frame, text="Filters")
        filter_frame.pack(fill=tk.X, padx=15, pady=(0, 15))
        
        # Create filter controls
        controls_frame = ttk.Frame(filter_frame)
        controls_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Status filter
        ttk.Label(controls_frame, text="Status:").grid(row=0, column=0, padx=(0, 5), pady=5, sticky=tk.W)
        self.status_filter = ttk.Combobox(controls_frame, width=15, values=["All", "Paid", "Unpaid", "Overdue"])
        self.status_filter.current(0)
        self.status_filter.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # Date range filter
        ttk.Label(controls_frame, text="Date Range:").grid(row=0, column=2, padx=(15, 5), pady=5, sticky=tk.W)
        self.date_filter = ttk.Combobox(controls_frame, width=15, 
                                      values=["All Time", "This Year", "Last Year", "This Month", "Last Month", "Custom"])
        self.date_filter.current(0)
        self.date_filter.grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)
        
        # Fund filter
        ttk.Label(controls_frame, text="Fund:").grid(row=0, column=4, padx=(15, 5), pady=5, sticky=tk.W)
        self.fund_filter = ttk.Combobox(controls_frame, width=15, values=["All"])
        self.fund_filter.current(0)
        self.fund_filter.grid(row=0, column=5, padx=5, pady=5, sticky=tk.W)
        
        # Search box
        ttk.Label(controls_frame, text="Search:").grid(row=1, column=0, padx=(0, 5), pady=5, sticky=tk.W)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(controls_frame, textvariable=self.search_var, width=40)
        search_entry.grid(row=1, column=1, columnspan=3, padx=5, pady=5, sticky=tk.W+tk.E)
        
        # Search button with accent style
        search_button = ttk.Button(controls_frame, text="Search", command=self._apply_filters)
        search_button.grid(row=1, column=4, padx=5, pady=5, sticky=tk.W)
        
        # Reset button
        reset_button = ttk.Button(controls_frame, text="Reset Filters", command=self._reset_filters)
        reset_button.grid(row=1, column=5, padx=5, pady=5, sticky=tk.W)
    
    def _reset_filters(self):
        """Reset all filters to default values"""
        try:
            # Reset filter controls
            self.status_filter.set("All")
            self.date_filter.set("All Time")
            self.fund_filter.set("All")
            self.search_var.set("")
            
            # Apply the reset filters (load all data)
            self._apply_filters()
            
        except Exception as e:
            logger.error(f"Error resetting filters: {str(e)}")
            self.status_var.set(f"Error: {str(e)}")

    def _load_dashboard_data(self):
        """Load all dashboard data from the database"""
        try:
            self.status_var.set("Loading dashboard data...")
            
            # Show loading overlay
            self._show_loading_overlay()
            
            # Use threading to prevent UI freeze
            def load_data_thread():
                try:
                    # Load fund options for filter
                    fund_options = self._get_fund_options()
                    
                    # Get all invoice data
                    all_data = self._get_filtered_data({})
                    
                    # Update UI in the main thread
                    self.parent.after(0, lambda: self._update_ui_with_initial_data(fund_options, all_data))
                
                except Exception as e:
                    logger.error(f"Failed to load dashboard data: {str(e)}")
                    # Update UI in the main thread
                    self.parent.after(0, lambda: self._handle_filter_error(f"Failed to load data: {str(e)}"))
            
            # Start loading thread
            thread = threading.Thread(target=load_data_thread)
            thread.daemon = True
            thread.start()
            
        except Exception as e:
            logger.error(f"Failed to initiate dashboard data loading: {str(e)}")
            self.status_var.set(f"Error loading data: {str(e)}")
    
    def _get_fund_options(self):
        """Get fund options for the filter dropdown"""
        try:
            # Query to get distinct funds
            query = "SELECT DISTINCT fund FROM funds ORDER BY fund"
            result = self.db_manager.db.execute_query(query)
            
            if not result.get('error') and result.get('rows'):
                # Extract fund names
                return ["All"] + [row[0] for row in result['rows'] if row[0]]
            else:
                return ["All"]
            
        except Exception as e:
            logger.error(f"Failed to load fund options: {str(e)}")
            return ["All"]
    
    def _update_ui_with_initial_data(self, fund_options, result):
        """Update UI with initial data load (called in main thread)"""
        try:
            # Update fund filter options
            self.fund_filter['values'] = fund_options
            self.fund_filter.current(0)
            
            # Update invoice table data
            self._update_ui_with_data(result, {})
            
            # Remove loading indicator
            self._hide_loading_overlay()
            
            # Update status
            row_count = len(result.get('rows', []))
            self.status_var.set(f"Loaded {row_count} invoices")
            
        except Exception as e:
            logger.error(f"Error updating UI with initial data: {str(e)}")
            self.status_var.set(f"Error updating UI: {str(e)}")
            self._hide_loading_overlay() 