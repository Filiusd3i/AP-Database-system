import tkinter as tk
from tkinter import ttk, messagebox
import logging
from datetime import datetime, date, timedelta
import threading
import time

logger = logging.getLogger(__name__)

class ModernDashboard:
    def __init__(self, parent, db_manager=None, llm_client=None):
        """Initialize the modern dashboard with three-panel layout"""
        # Store references
        self.parent = parent
        self.db_manager = db_manager
        self.llm_client = llm_client
        
        # Initialize data values
        self.total_amount = 0
        self.total_paid_current_year = 0
        self.total_unpaid = 0
        self.total_overdue = 0
        self.total_upcoming_payments = 0
        self.fund_allocation_count = 0
        
        # Initialize filter variables
        self.filter_vars = {
            'status': None,
            'date_range': None,
            'fund': None,
            'search': None,
            'vendor_type': None,
            'deal': None,
            'category': None
        }
        
        # UI component references
        self.frame = None
        self.nav_frame = None
        self.list_frame = None
        self.detail_frame = None
        self.invoice_table = None
        self.status_var = None
        self.sort_column = None
        self.sort_reverse = False
        self.selected_invoice_id = None
        
        # Create UI
        self.create_ui()
        
        # Apply modern styling
        self.apply_modern_styling()
        
        # Update data
        self.update_dashboard_data()
        
        # Log initialization
        logger.info("Modern dashboard initialized successfully")
    
    def create_ui(self):
        """Create the main UI with three-panel layout"""
        # Create the main container
        self.frame = ttk.Frame(self.parent)
        self.frame.pack(fill=tk.BOTH, expand=True)
        
        # Create paned window for resizable panels
        self.main_container = ttk.PanedWindow(self.frame, orient=tk.HORIZONTAL)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 1. Left sidebar navigation panel
        self.nav_frame = ttk.Frame(self.main_container, width=80, style="Nav.TFrame")
        
        # 2. Invoice list panel
        self.list_frame = ttk.Frame(self.main_container, style="Modern.TFrame")
        
        # 3. Detail panel showing relationships
        self.detail_frame = ttk.Frame(self.main_container, style="Modern.TFrame")
        
        # Add panels to paned window with weights
        self.main_container.add(self.nav_frame, weight=1)
        self.main_container.add(self.list_frame, weight=4)
        self.main_container.add(self.detail_frame, weight=6)
        
        # Set up each panel
        self.setup_nav_panel()
        self.setup_list_panel()
        self.setup_detail_panel()
        
        # Add status bar
        self.create_status_bar()
    
    def apply_modern_styling(self):
        """Apply modern styling to all UI components"""
        # Create custom styles
        style = ttk.Style()
        
        # Color scheme
        primary_color = '#3498db'    # Blue
        success_color = '#27ae60'    # Green
        warning_color = '#e67e22'    # Orange  
        danger_color = '#e74c3c'     # Red
        bg_light = '#ffffff'         # White
        bg_medium = '#f5f5f5'        # Light gray
        text_dark = '#2c3e50'        # Dark blue/gray
        
        # Navigation panel style
        style.configure("Nav.TFrame", background="#2c3e50")
        
        # Modern frame style
        style.configure("Modern.TFrame", background=bg_light)
        
        # Card-like frame with border
        style.configure("Card.TFrame", 
                      background=bg_light, 
                      borderwidth=1, 
                      relief="solid")
        
        # Table styling
        style.configure("Treeview", 
                      background=bg_light,
                      rowheight=40,
                      fieldbackground=bg_light)
        
        style.map("Treeview",
                background=[("selected", "#e1f0fd")],
                foreground=[("selected", text_dark)])
        
        # Custom heading style
        style.configure("Treeview.Heading", 
                      font=('Arial', 10, 'bold'),
                      borderwidth=0)
        
        # Modern button style
        style.configure("Accent.TButton", 
                      background=primary_color, 
                      foreground="white")
        
        # Status label styles
        style.configure("Paid.TLabel", foreground=success_color)
        style.configure("Pending.TLabel", foreground=warning_color)
        style.configure("Overdue.TLabel", foreground=danger_color)
    
    def setup_nav_panel(self):
        """Set up the navigation sidebar"""
        # Navigation icons
        nav_items = [
            {"text": "Dashboard", "icon": "🏠"},
            {"text": "Invoices", "icon": "📄", "active": True},
            {"text": "Vendors", "icon": "👥"},
            {"text": "Funds", "icon": "💰"},
            {"text": "Reports", "icon": "📊"},
            {"text": "Settings", "icon": "⚙️"}
        ]
        
        # Add icon buttons
        for i, item in enumerate(nav_items):
            # Frame for each nav item
            item_frame = ttk.Frame(self.nav_frame)
            item_frame.pack(pady=10, padx=5, fill=tk.X)
            
            # Background color for active item
            if item.get("active", False):
                item_frame.configure(style="Card.TFrame")
            
            # Icon label
            icon_label = ttk.Label(item_frame, text=item["icon"], 
                                 font=("Arial", 16))
            icon_label.pack(pady=(5, 2), anchor="center")
            
            # Text label
            text_label = ttk.Label(item_frame, text=item["text"], 
                                 font=("Arial", 8))
            text_label.pack(pady=(0, 5), anchor="center")
            
            # Configure foreground color
            icon_label.configure(foreground="white")
            text_label.configure(foreground="white")
            
            # Bind click event
            item_frame.bind("<Button-1>", lambda e, t=item["text"]: self.nav_item_clicked(t))
            icon_label.bind("<Button-1>", lambda e, t=item["text"]: self.nav_item_clicked(t))
            text_label.bind("<Button-1>", lambda e, t=item["text"]: self.nav_item_clicked(t))
    
    def nav_item_clicked(self, item_name):
        """Handle navigation item click"""
        logger.info(f"Navigation item clicked: {item_name}")
        # Implement navigation logic here
        messagebox.showinfo("Navigation", f"Navigated to: {item_name}")
    
    def setup_list_panel(self):
        """Set up the invoice list panel"""
        # Title and filter section
        header_frame = ttk.Frame(self.list_frame, style="Modern.TFrame")
        header_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(header_frame, text="Invoices", 
                font=("Arial", 12, "bold")).pack(side=tk.LEFT)
        
        # Filter dropdown
        ttk.Label(header_frame, text="Status:").pack(side=tk.LEFT, padx=(20,5))
        
        self.filter_vars['status'] = tk.StringVar(value="All")
        status_combo = ttk.Combobox(header_frame, textvariable=self.filter_vars['status'],
                                  values=["All", "Paid", "Unpaid", "Pending", "Approved", "Overdue"], 
                                  width=10)
        status_combo.pack(side=tk.LEFT)
        status_combo.bind("<<ComboboxSelected>>", self.filter_invoices)
        
        # New button
        new_btn = ttk.Button(header_frame, text="New", style="Accent.TButton")
        new_btn.pack(side=tk.RIGHT)
        
        # Invoice table
        table_frame = ttk.Frame(self.list_frame, style="Modern.TFrame")
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        columns = ("vendor", "amount", "date", "status")
        self.invoice_table = ttk.Treeview(table_frame, columns=columns, 
                                        show="headings", selectmode="browse", 
                                        height=20)
        
        # Configure columns
        self.invoice_table.heading("vendor", text="Vendor")
        self.invoice_table.heading("amount", text="Amount")
        self.invoice_table.heading("date", text="Date")
        self.invoice_table.heading("status", text="Status")
        
        self.invoice_table.column("vendor", width=150)
        self.invoice_table.column("amount", width=100, anchor="e")
        self.invoice_table.column("date", width=100, anchor="center")
        self.invoice_table.column("status", width=80, anchor="center")
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, 
                                command=self.invoice_table.yview)
        self.invoice_table.configure(yscrollcommand=scrollbar.set)
        
        # Pack table and scrollbar
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.invoice_table.pack(fill=tk.BOTH, expand=True)
        
        # Bind selection event to show details
        self.invoice_table.bind("<<TreeviewSelect>>", self.show_invoice_details)
        
        # Load invoices (sample data for now)
        self.load_sample_invoices()
    
    def setup_detail_panel(self):
        """Set up the invoice detail panel"""
        # Status and actions header
        header_frame = ttk.Frame(self.detail_frame, style="Modern.TFrame")
        header_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.status_label = ttk.Label(header_frame, text="STATUS: SENT", 
                                   foreground="#3498db", font=("Arial", 10, "bold"))
        self.status_label.pack(side=tk.LEFT)
        
        export_btn = ttk.Button(header_frame, text="Export", style="Accent.TButton")
        export_btn.pack(side=tk.RIGHT)
        
        # Invoice details container
        self.detail_container = ttk.Frame(self.detail_frame, style="Modern.TFrame")
        self.detail_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Default message
        ttk.Label(self.detail_container, text="Select an invoice to view details", 
                font=("Arial", 12)).pack(pady=50)
    
    def create_status_bar(self):
        """Create status bar at bottom of window"""
        status_frame = ttk.Frame(self.frame, style="Modern.TFrame")
        status_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=2)
        
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(status_frame, textvariable=self.status_var, 
                               font=('Segoe UI', 9))
        status_label.pack(side=tk.LEFT, padx=5)
    
    def load_sample_invoices(self):
        """Load sample invoice data for demo purposes"""
        # Clear existing items
        for item in self.invoice_table.get_children():
            self.invoice_table.delete(item)
        
        # Sample data
        sample_invoices = [
            {"id": "1", "vendor": "Nexage Digital", "amount": 2200.00, 
             "date": "10/05/2023", "status": "Sent"},
            {"id": "2", "vendor": "Lily Rodriguez", "amount": 1290.50, 
             "date": "09/28/2023", "status": "Pending"},
            {"id": "3", "vendor": "Owen Lee", "amount": 2100.00, 
             "date": "09/23/2023", "status": "Paid"},
            {"id": "4", "vendor": "Chloe Nygua", "amount": 1580.00, 
             "date": "09/15/2023", "status": "Paid"},
            {"id": "5", "vendor": "Xavier Davis", "amount": 3353.00, 
             "date": "09/12/2023", "status": "Sent"},
            {"id": "6", "vendor": "Harper Martinez", "amount": 2450.00, 
             "date": "09/05/2023", "status": "Pending"},
            {"id": "7", "vendor": "Logan Wright", "amount": 1490.00, 
             "date": "08/28/2023", "status": "Paid"},
            {"id": "8", "vendor": "Avery Khan", "amount": 1300.00, 
             "date": "08/22/2023", "status": "Paid"},
            {"id": "9", "vendor": "Evan Thomas", "amount": 1470.00, 
             "date": "08/15/2023", "status": "Pending"}
        ]
        
        # Add invoices to table
        for i, invoice in enumerate(sample_invoices):
            self.invoice_table.insert("", "end", 
                                    values=(
                                        invoice["vendor"],
                                        f"${invoice['amount']:,.2f}",
                                        invoice["date"],
                                        invoice["status"]
                                    ), 
                                    tags=(invoice["id"], "evenrow" if i % 2 == 0 else "oddrow"))
        
        # Apply row style
        self.invoice_table.tag_configure('oddrow', background='#f9f9f9')
        self.invoice_table.tag_configure('evenrow', background='#ffffff')
    
    def load_invoices(self):
        """Load real invoices from database"""
        # Skip if db_manager is not available
        if not self.db_manager or not hasattr(self.db_manager, 'execute_query'):
            self.load_sample_invoices()
            return
            
        try:
            # Query to get invoices
            query = """
            SELECT 
                i.invoice_id, 
                v.vendor_name, 
                i.amount, 
                i.invoice_date, 
                i.payment_status
            FROM 
                invoices i
            JOIN 
                vendors v ON i.vendor_id = v.vendor_id
            ORDER BY 
                i.invoice_date DESC
            LIMIT 100
            """
            
            result = self.db_manager.execute_query(query)
            
            # Check for error or no results
            if result.get('error') or not result.get('rows'):
                logger.error(f"Error loading invoices: {result.get('error', 'No results')}")
                self.load_sample_invoices()
                return
                
            # Clear existing items
            for item in self.invoice_table.get_children():
                self.invoice_table.delete(item)
            
            # Add invoices to table
            for i, row in enumerate(result['rows']):
                # Format date
                date_str = row[3].strftime("%m/%d/%Y") if isinstance(row[3], (date, datetime)) else str(row[3])
                
                # Format amount
                try:
                    amount = float(row[2])
                    amount_str = f"${amount:,.2f}"
                except (ValueError, TypeError):
                    amount_str = f"${0:,.2f}"
                
                # Add to table
                self.invoice_table.insert("", "end", 
                                        values=(
                                            row[1],  # vendor_name
                                            amount_str,
                                            date_str,
                                            row[4]   # payment_status
                                        ), 
                                        tags=(row[0], "evenrow" if i % 2 == 0 else "oddrow"))
            
            # Apply row style
            self.invoice_table.tag_configure('oddrow', background='#f9f9f9')
            self.invoice_table.tag_configure('evenrow', background='#ffffff')
                
        except Exception as e:
            logger.error(f"Error loading invoices: {str(e)}")
            self.load_sample_invoices()
    
    def filter_invoices(self, event=None):
        """Filter invoices based on selected filters"""
        status = self.filter_vars['status'].get()
        
        if status == "All":
            # Reload all invoices
            self.load_invoices()
            return
            
        # Skip if db_manager is not available
        if not self.db_manager or not hasattr(self.db_manager, 'execute_query'):
            return
            
        try:
            # Query to get filtered invoices
            query = f"""
            SELECT 
                i.invoice_id, 
                v.vendor_name, 
                i.amount, 
                i.invoice_date, 
                i.payment_status
            FROM 
                invoices i
            JOIN 
                vendors v ON i.vendor_id = v.vendor_id
            WHERE 
                i.payment_status = '{status}'
            ORDER BY 
                i.invoice_date DESC
            LIMIT 100
            """
            
            result = self.db_manager.execute_query(query)
            
            # Check for error or no results
            if result.get('error'):
                logger.error(f"Error filtering invoices: {result.get('error')}")
                return
                
            # Clear existing items
            for item in self.invoice_table.get_children():
                self.invoice_table.delete(item)
            
            # Add invoices to table
            for i, row in enumerate(result.get('rows', [])):
                # Format date
                date_str = row[3].strftime("%m/%d/%Y") if isinstance(row[3], (date, datetime)) else str(row[3])
                
                # Format amount
                try:
                    amount = float(row[2])
                    amount_str = f"${amount:,.2f}"
                except (ValueError, TypeError):
                    amount_str = f"${0:,.2f}"
                
                # Add to table
                self.invoice_table.insert("", "end", 
                                        values=(
                                            row[1],  # vendor_name
                                            amount_str,
                                            date_str,
                                            row[4]   # payment_status
                                        ), 
                                        tags=(row[0], "evenrow" if i % 2 == 0 else "oddrow"))
            
            # Apply row style
            self.invoice_table.tag_configure('oddrow', background='#f9f9f9')
            self.invoice_table.tag_configure('evenrow', background='#ffffff')
            
            # Update status
            if not result.get('rows'):
                self.status_var.set(f"No invoices found with status: {status}")
            else:
                self.status_var.set(f"Found {len(result['rows'])} invoices with status: {status}")
                
        except Exception as e:
            logger.error(f"Error filtering invoices: {str(e)}")
    
    def update_dashboard_data(self):
        """Update dashboard data"""
        # This would query the database for metrics
        # For now, just set the status
        self.status_var.set("Dashboard data refreshed")
        
        # Load invoices
        self.load_invoices()
    
    def show_invoice_details(self, event):
        """Show detailed view of invoice when selected"""
        # Get selected item
        selected_items = self.invoice_table.selection()
        if not selected_items:
            return
            
        selected_item = selected_items[0]
        invoice_id = self.invoice_table.item(selected_item, "tags")[0]
        
        # Store selected invoice ID
        self.selected_invoice_id = invoice_id
        
        # Clear existing detail view
        for widget in self.detail_container.winfo_children():
            widget.destroy()
        
        # Get status from table
        values = self.invoice_table.item(selected_item, "values")
        status = values[3]
        
        # Update status label
        self.status_label.configure(text=f"STATUS: {status.upper()}")
        
        # If using sample data
        if not self.db_manager or not hasattr(self.db_manager, 'execute_query'):
            self.show_sample_invoice_details(invoice_id, values)
            return
            
        # Get invoice details from database
        self.show_db_invoice_details(invoice_id)
    
    def show_sample_invoice_details(self, invoice_id, values):
        """Show invoice details using sample data"""
        vendor_name, amount_str, date_str, status = values
        
        # Sample invoice details
        invoice = {
            "invoice_number": f"INV-{invoice_id}",
            "vendor_name": vendor_name,
            "amount": amount_str,
            "created_date": datetime.now() - timedelta(days=30),
            "due_date": datetime.now() + timedelta(days=15),
            "status": status,
            "vendor_type": "Technology",
            "contact_email": "contact@example.com"
        }
        
        # Sample items
        items = [
            {"item_description": "Network Cable", "quantity": 4, "rate": 45.00, "amount": 180.00},
            {"item_description": "Network Router", "quantity": 2, "rate": 220.00, "amount": 440.00}
        ]
        
        # Sample allocations
        allocations = [
            {"fund_name": "Fund I", "allocation_percentage": 60, "allocated_amount": 1320.00},
            {"fund_name": "Fund II", "allocation_percentage": 40, "allocated_amount": 880.00}
        ]
        
        # Create detail view
        self.create_detail_view(invoice, allocations, items)
    
    def show_db_invoice_details(self, invoice_id):
        """Show invoice details from database"""
        try:
            # Query invoice details
            query = f"""
            SELECT 
                i.invoice_id, 
                i.invoice_number, 
                i.amount,
                i.invoice_date,
                i.due_date,
                i.payment_status,
                v.vendor_name,
                v.vendor_type,
                v.email as contact_email
            FROM 
                invoices i
            JOIN 
                vendors v ON i.vendor_id = v.vendor_id
            WHERE 
                i.invoice_id = '{invoice_id}'
            """
            
            result = self.db_manager.execute_query(query)
            
            if result.get('error') or not result.get('rows'):
                logger.error(f"Error getting invoice details: {result.get('error', 'No results')}")
                return
                
            invoice_data = result['rows'][0]
            
            # Convert to dict format
            invoice = {
                "invoice_id": invoice_data[0],
                "invoice_number": invoice_data[1],
                "amount": invoice_data[2],
                "created_date": invoice_data[3],
                "due_date": invoice_data[4],
                "status": invoice_data[5],
                "vendor_name": invoice_data[6],
                "vendor_type": invoice_data[7],
                "contact_email": invoice_data[8]
            }
            
            # Query items
            items_query = f"""
            SELECT 
                item_description, 
                quantity, 
                unit_price as rate, 
                (quantity * unit_price) as amount
            FROM 
                invoice_items
            WHERE 
                invoice_id = '{invoice_id}'
            """
            
            items_result = self.db_manager.execute_query(items_query)
            items = items_result.get('rows', [])
            
            # Query allocations
            allocations_query = f"""
            SELECT 
                f.fund_name, 
                a.allocation_percentage,
                (i.amount * a.allocation_percentage / 100) as allocated_amount
            FROM 
                expense_allocation a
            JOIN 
                funds f ON a.fund_id = f.fund_id
            JOIN 
                invoices i ON a.invoice_id = i.invoice_id
            WHERE 
                a.invoice_id = '{invoice_id}'
            """
            
            allocations_result = self.db_manager.execute_query(allocations_query)
            allocations = allocations_result.get('rows', [])
            
            # Create detail view
            self.create_detail_view(invoice, allocations, items)
            
        except Exception as e:
            logger.error(f"Error showing invoice details: {str(e)}")
    
    def create_detail_view(self, invoice, allocations, items):
        """Create the detail view for an invoice"""
        # Invoice header
        ttk.Label(self.detail_container, text=f"Invoice - {invoice['invoice_number']}", 
                 font=("Arial", 14, "bold")).pack(anchor="w", pady=(0,20))
        
        # Invoice details in two columns
        detail_frame = ttk.Frame(self.detail_container, style="Modern.TFrame")
        detail_frame.pack(fill=tk.X, pady=10)
        
        # Left column - Invoice info
        left_col = ttk.Frame(detail_frame, style="Modern.TFrame")
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        ttk.Label(left_col, text="Invoice Number:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", pady=2)
        ttk.Label(left_col, text=invoice['invoice_number']).grid(row=0, column=1, sticky="w", pady=2)
        
        # Format created date
        created_date_str = ""
        if isinstance(invoice.get('created_date'), (date, datetime)):
            created_date_str = invoice['created_date'].strftime("%m/%d/%Y")
        else:
            created_date_str = str(invoice.get('created_date', ""))
            
        ttk.Label(left_col, text="Created Date:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="w", pady=2)
        ttk.Label(left_col, text=created_date_str).grid(row=1, column=1, sticky="w", pady=2)
        
        # Format due date
        due_date_str = ""
        if isinstance(invoice.get('due_date'), (date, datetime)):
            due_date_str = invoice['due_date'].strftime("%m/%d/%Y")
        else:
            due_date_str = str(invoice.get('due_date', ""))
            
        ttk.Label(left_col, text="Due Date:", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky="w", pady=2)
        ttk.Label(left_col, text=due_date_str).grid(row=2, column=1, sticky="w", pady=2)
        
        # Right column - Vendor info
        right_col = ttk.Frame(detail_frame, style="Modern.TFrame")
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        ttk.Label(right_col, text="Vendor:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", pady=2)
        ttk.Label(right_col, text=invoice.get('vendor_name', "")).grid(row=0, column=1, sticky="w", pady=2)
        
        ttk.Label(right_col, text="Type:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="w", pady=2)
        ttk.Label(right_col, text=invoice.get('vendor_type', "")).grid(row=1, column=1, sticky="w", pady=2)
        
        ttk.Label(right_col, text="Contact:", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky="w", pady=2)
        ttk.Label(right_col, text=invoice.get('contact_email', "")).grid(row=2, column=1, sticky="w", pady=2)
        
        # Items table
        ttk.Label(self.detail_container, text="Items & Description", 
                 font=("Arial", 11, "bold")).pack(anchor="w", pady=(20,10))
        
        # Create items table
        items_frame = ttk.Frame(self.detail_container, style="Modern.TFrame")
        items_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        item_cols = ("no", "description", "qty", "rate", "amount")
        items_table = ttk.Treeview(items_frame, columns=item_cols, show="headings", height=5)
        
        items_table.heading("no", text="#")
        items_table.heading("description", text="Item & Description")
        items_table.heading("qty", text="Qty")
        items_table.heading("rate", text="Rate")
        items_table.heading("amount", text="Amount")
        
        items_table.column("no", width=40, anchor="center")
        items_table.column("description", width=250)
        items_table.column("qty", width=60, anchor="e")
        items_table.column("rate", width=80, anchor="e")
        items_table.column("amount", width=100, anchor="e")
        
        # Add items to table
        for i, item in enumerate(items):
            # Handle different formats of data
            # If item is a tuple/list
            if isinstance(item, (list, tuple)):
                description = item[0] if len(item) > 0 else ""
                quantity = item[1] if len(item) > 1 else 0
                rate = item[2] if len(item) > 2 else 0.0
                amount = item[3] if len(item) > 3 else 0.0
            # If item is a dict
            else:
                description = item.get('item_description', "")
                quantity = item.get('quantity', 0)
                rate = item.get('rate', 0.0)
                amount = item.get('amount', 0.0)
            
            # Format item values
            rate_str = f"${float(rate):.2f}"
            amount_str = f"${float(amount):.2f}"
            
            # Add to table
            items_table.insert("", "end", values=(
                i+1,
                description,
                quantity,
                rate_str,
                amount_str
            ))
        
        # Add scrollbar if needed
        if len(items) > 5:
            scrollbar = ttk.Scrollbar(items_frame, orient=tk.VERTICAL, 
                                    command=items_table.yview)
            items_table.configure(yscrollcommand=scrollbar.set)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Totals
        totals_frame = ttk.Frame(self.detail_container, style="Modern.TFrame")
        totals_frame.pack(fill=tk.X, pady=10)
        
        # Empty space on left
        ttk.Frame(totals_frame, style="Modern.TFrame").pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Totals on right
        total_details = ttk.Frame(totals_frame, style="Modern.TFrame")
        total_details.pack(side=tk.RIGHT)
        
        # Format amount string if needed
        if isinstance(invoice.get('amount'), str) and invoice['amount'].startswith('$'):
            amount_str = invoice['amount']
        else:
            try:
                amount = float(invoice.get('amount', 0))
                amount_str = f"${amount:.2f}"
            except (ValueError, TypeError):
                amount_str = "$0.00"
        
        ttk.Label(total_details, text="Sub-Total:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="e", pady=2)
        ttk.Label(total_details, text=amount_str).grid(row=0, column=1, sticky="e", pady=2, padx=(10, 0))
        
        ttk.Label(total_details, text="Total:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="e", pady=2)
        ttk.Label(total_details, text=amount_str, font=("Arial", 10, "bold")).grid(row=1, column=1, sticky="e", pady=2, padx=(10, 0))
        
        ttk.Label(total_details, text="Balance Due:", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky="e", pady=2)
        ttk.Label(total_details, text=amount_str, foreground="red").grid(row=2, column=1, sticky="e", pady=2, padx=(10, 0))
        
        # Fund allocations
        if allocations:
            ttk.Label(self.detail_container, text="Fund Allocations", 
                    font=("Arial", 11, "bold")).pack(anchor="w", pady=(20,10))
            
            alloc_frame = ttk.Frame(self.detail_container, style="Modern.TFrame")
            alloc_frame.pack(fill=tk.BOTH, expand=True, pady=10)
            
            alloc_cols = ("fund", "percentage", "amount")
            alloc_table = ttk.Treeview(alloc_frame, columns=alloc_cols, show="headings", height=3)
            
            alloc_table.heading("fund", text="Fund")
            alloc_table.heading("percentage", text="Percentage")
            alloc_table.heading("amount", text="Amount")
            
            alloc_table.column("fund", width=200)
            alloc_table.column("percentage", width=100, anchor="e")
            alloc_table.column("amount", width=100, anchor="e")
            
            for alloc in allocations:
                # Handle different formats of data
                if isinstance(alloc, (list, tuple)):
                    fund_name = alloc[0] if len(alloc) > 0 else ""
                    percentage = alloc[1] if len(alloc) > 1 else 0
                    alloc_amount = alloc[2] if len(alloc) > 2 else 0.0
                else:
                    fund_name = alloc.get('fund_name', "")
                    percentage = alloc.get('allocation_percentage', 0)
                    alloc_amount = alloc.get('allocated_amount', 0.0)
                
                # Format values
                percentage_str = f"{float(percentage):.1f}%"
                alloc_amount_str = f"${float(alloc_amount):.2f}"
                
                alloc_table.insert("", "end", values=(
                    fund_name,
                    percentage_str,
                    alloc_amount_str
                ))
            
            alloc_table.pack(fill=tk.BOTH, expand=True)
            
            # Add relationship visualization
            self.create_relationship_diagram(self.detail_container, invoice.get('invoice_id', self.selected_invoice_id))
    
    def create_relationship_diagram(self, parent, invoice_id):
        """Create a visualization of relationships for this invoice"""
        # Create frame for diagram
        diagram_frame = ttk.LabelFrame(parent, text="Relationship Diagram", style="Modern.TFrame")
        diagram_frame.pack(fill=tk.BOTH, expand=True, pady=(20, 10))
        
        # Create canvas for visualization
        canvas = tk.Canvas(diagram_frame, width=500, height=200, bg="white")
        canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # If using sample data
        if not self.db_manager or not hasattr(self.db_manager, 'execute_query'):
            # Draw invoice node at center
            canvas.create_oval(225, 75, 275, 125, fill="#3498db", outline="")
            canvas.create_text(250, 100, text="Invoice", fill="white", font=("Arial", 10, "bold"))
            
            # Draw vendor relationship
            canvas.create_line(225, 100, 125, 50, fill="#2c3e50", width=2)
            canvas.create_rectangle(75, 25, 175, 75, fill="#e74c3c", outline="")
            canvas.create_text(125, 50, text="Vendor\nNexage Digital", 
                            fill="white", font=("Arial", 9), justify="center")
            
            # Draw fund relationships
            y_pos1 = 150
            canvas.create_line(250, 125, 150, y_pos1, fill="#2c3e50", width=2, dash=(4, 2))
            canvas.create_text(200, 137, text="60%", fill="#2c3e50", font=("Arial", 8))
            canvas.create_rectangle(100, y_pos1 - 25, 200, y_pos1 + 25, fill="#27ae60", outline="")
            canvas.create_text(150, y_pos1, text="Fund\nFund I", fill="white", font=("Arial", 9), justify="center")
            
            y_pos2 = 150
            canvas.create_line(250, 125, 350, y_pos2, fill="#2c3e50", width=2, dash=(4, 2))
            canvas.create_text(300, 137, text="40%", fill="#2c3e50", font=("Arial", 8))
            canvas.create_rectangle(300, y_pos2 - 25, 400, y_pos2 + 25, fill="#27ae60", outline="")
            canvas.create_text(350, y_pos2, text="Fund\nFund II", fill="white", font=("Arial", 9), justify="center")
            
            return canvas
        
        # Query relationships from database
        try:
            query = f"""
            SELECT 
                i.invoice_id, i.invoice_number, 
                v.vendor_id, v.vendor_name,
                f.fund_id, f.fund_name,
                a.allocation_percentage
            FROM 
                invoices i
            JOIN 
                vendors v ON i.vendor_id = v.vendor_id
            LEFT JOIN 
                expense_allocation a ON i.invoice_id = a.invoice_id
            LEFT JOIN 
                funds f ON a.fund_id = f.fund_id
            WHERE 
                i.invoice_id = '{invoice_id}'
            """
            
            result = self.db_manager.execute_query(query)
            
            if result.get('error') or not result.get('rows'):
                # Draw empty diagram with message
                canvas.create_text(250, 100, text="No relationship data available", 
                                 font=("Arial", 10), fill="#666666")
                return canvas
                
            relationships = result['rows']
            
            # Draw invoice node at center
            canvas.create_oval(225, 75, 275, 125, fill="#3498db", outline="")
            canvas.create_text(250, 100, text="Invoice", fill="white", font=("Arial", 10, "bold"))
            
            # Draw vendor relationship
            if relationships:
                vendor_name = relationships[0][3]  # vendor_name
                canvas.create_line(225, 100, 125, 50, fill="#2c3e50", width=2)
                canvas.create_rectangle(75, 25, 175, 75, fill="#e74c3c", outline="")
                canvas.create_text(125, 50, text=f"Vendor\n{vendor_name}", 
                                 fill="white", font=("Arial", 9), justify="center")
            
            # Draw fund relationships
            for i, rel in enumerate(relationships):
                if rel[4]:  # If fund_id exists
                    fund_name = rel[5]  # fund_name
                    percentage = rel[6]  # allocation_percentage
                    
                    # Calculate position based on number of funds
                    offset = i * 50
                    if i % 2 == 0:
                        x_pos = 150 - offset
                    else:
                        x_pos = 350 + offset
                    
                    y_pos = 150 + (i // 2) * 50
                    
                    # Draw line from invoice to fund
                    canvas.create_line(250, 125, x_pos, y_pos, fill="#2c3e50", width=2, dash=(4, 2))
                    
                    # Add allocation percentage as text on the line
                    mid_x, mid_y = (250 + x_pos) // 2, (125 + y_pos) // 2
                    canvas.create_text(mid_x, mid_y, text=f"{percentage}%", 
                                     fill="#2c3e50", font=("Arial", 8))
                    
                    # Draw fund node
                    canvas.create_rectangle(x_pos - 50, y_pos - 25, x_pos + 50, y_pos + 25, 
                                         fill="#27ae60", outline="")
                    canvas.create_text(x_pos, y_pos, text=f"Fund\n{fund_name}", 
                                     fill="white", font=("Arial", 9), justify="center")
            
            return canvas
            
        except Exception as e:
            logger.error(f"Error creating relationship diagram: {str(e)}")
            # Draw empty diagram with message
            canvas.create_text(250, 100, text=f"Error creating diagram: {str(e)}", 
                             font=("Arial", 10), fill="#666666")
            return canvas
