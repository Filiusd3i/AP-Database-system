import tkinter as tk
from tkinter import ttk, messagebox
import logging
from datetime import datetime, date
import threading
import time

logger = logging.getLogger(__name__)

class UnifiedDashboard:
    def __init__(self, parent, db_manager, llm_client=None):
        """Initialize the dashboard with all components properly set up"""
        # Store references
        self.parent = parent
        self.db_manager = db_manager
        self.llm_client = llm_client
        
        # Initialize UI component references BEFORE they're used
        self.frame = None
        self.invoice_tree = None
        self.pie_ax = None
        self.bar_ax = None
        self.sql_display = None
        self.status_var = None
        self.summary_cards = []
        
        # Initialize data values
        self.total_amount = 0
        self.total_paid_current_year = 0
        self.total_paid_last_year = 0  
        self.total_paid_prev_year = 0
        self.total_unpaid = 0
        self.total_overdue = 0
        
        # Initialize filter variables
        self.filter_vars = {
            'status': None,
            'date_range': None,
            'fund': None,
            'search': None
        }
        
        # Create UI components - THIS MUST HAPPEN BEFORE ANY UPDATES
        self.create_ui()
        
        # Now that UI exists, we can update data
        self.update_dashboard_data()
        
        # Log initialization
        logger.info("Unified dashboard initialized successfully")

    def create_ui(self):
        """Create all UI components in the correct order"""
        # Set up theme and colors
        self.style = ttk.Style()
        
        # Color scheme
        bg_dark = '#1e1e2e'      # Dark background
        bg_medium = '#2a2a3a'    # Medium background
        accent_color = '#7e57c2' # Purple accent
        text_color = '#e0e0e0'   # Light text
        
        # Configure theme
        self.style.configure('TFrame', background=bg_dark)
        self.style.configure('TLabelframe', background=bg_dark, foreground=text_color)
        self.style.configure('TLabelframe.Label', background=bg_dark, foreground=text_color)
        self.style.configure('TLabel', background=bg_dark, foreground=text_color)
        self.style.configure('TButton', background=accent_color, foreground=text_color)
        
        # Configure Treeview
        self.style.configure('Treeview', 
                           background=bg_medium, 
                           foreground=text_color,
                           fieldbackground=bg_medium)
        
        # Create main frame
        self.frame = ttk.Frame(self.parent)
        self.frame.pack(fill=tk.BOTH, expand=True)
        
        # Create header
        self.create_header(bg_dark, text_color)
        
        # Create content area
        content_frame = ttk.Frame(self.frame)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Create components in order
        self.create_search_section(content_frame)
        self.create_summary_cards(content_frame)
        self.create_filter_panel(content_frame)
        self.create_sql_display(content_frame, bg_medium)
        self.create_invoice_table(content_frame)
        self.create_charts_section(content_frame, bg_medium)
        
        # Create status bar
        self.create_status_bar()
    
    def create_header(self, bg_color, text_color):
        """Create the dashboard header with gradient"""
        header_frame = tk.Frame(self.frame, height=60, bg=bg_color)
        header_frame.pack(fill=tk.X)
        
        header_canvas = tk.Canvas(header_frame, height=60, bg=bg_color, highlightthickness=0)
        header_canvas.pack(fill=tk.X, expand=True)
        
        # Create gradient effect
        for i in range(60):
            r = int(30 + (i/60) * 18)
            g = int(30 + (i/60) * 18)
            b = int(46 + (i/60) * 23)
            color = f'#{r:02x}{g:02x}{b:02x}'
            header_canvas.create_line(0, i, 2000, i, fill=color)
        
        # Add title
        header_canvas.create_text(20, 30, text="Unified Invoice Dashboard", 
                               fill=text_color, font=('Segoe UI', 16, 'bold'),
                               anchor='w')
        
        # Add refresh and aging report buttons
        refresh_button = ttk.Button(header_frame, text="⟳ Refresh", 
                                  command=self.update_dashboard_data)
        refresh_button.place(x=620, y=15)
        
        aging_button = ttk.Button(header_frame, text="Generate Aging Report", 
                                command=self.generate_aging_report)
        aging_button.place(x=720, y=15)
    
    def create_search_section(self, parent_frame):
        """Create natural language search section"""
        search_frame = ttk.LabelFrame(parent_frame, text="Natural Language Search")
        search_frame.pack(fill=tk.X, pady=10)
        
        # Search entry
        self.filter_vars['search'] = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.filter_vars['search'], 
                               font=('Segoe UI', 11), width=50)
        search_entry.pack(side=tk.LEFT, padx=8, pady=10, fill=tk.X, expand=True)
        
        # Bind Enter key
        search_entry.bind("<Return>", lambda event: self.execute_search())
        
        # Search button
        search_button = ttk.Button(search_frame, text="Search", 
                                 command=self.execute_search)
        search_button.pack(side=tk.LEFT, padx=5, pady=10)
        
        # Suggestions button
        suggestions_button = ttk.Button(search_frame, text="Suggestions", 
                                      command=self.show_search_suggestions)
        suggestions_button.pack(side=tk.LEFT, padx=5, pady=10)
        
        # Schema button
        schema_button = ttk.Button(search_frame, text="Schema Tools", 
                                 command=self.show_schema_tools)
        schema_button.pack(side=tk.LEFT, padx=5, pady=10)
    
    def create_summary_cards(self, parent_frame):
        """Create summary cards showing key financial metrics"""
        cards_frame = ttk.Frame(parent_frame)
        cards_frame.pack(fill=tk.X, pady=10)
        
        # Define card styles
        card_styles = [
            {"from": "#303F9F", "to": "#1A237E", "title": "Total Amount", 
             "value_attr": "total_amount", "format": "${:,.2f}"},
            {"from": "#00796B", "to": "#004D40", "title": "Paid This Year", 
             "value_attr": "total_paid_current_year", "format": "${:,.2f}"},
            {"from": "#6A1B9A", "to": "#4A148C", "title": "Current Invoices", 
             "value_attr": "total_unpaid", "format": "${:,.2f}"},
            {"from": "#C62828", "to": "#B71C1C", "title": "Overdue Invoices", 
             "value_attr": "total_overdue", "format": "${:,.2f}"}
        ]
        
        # Clear existing cards
        self.summary_cards = []
        
        # Create each card
        for style in card_styles:
            card = tk.Frame(cards_frame, width=200, height=120, background=style["from"])
            card.pack(side=tk.LEFT, padx=8, pady=5, expand=True, fill=tk.X)
            card.pack_propagate(False)  # Prevent frame from shrinking
            
            # Create gradient
            canvas = tk.Canvas(card, background=style["from"], 
                             highlightthickness=0, bd=0)
            canvas.pack(fill=tk.BOTH, expand=True)
            
            # Draw gradient
            for y in range(120):
                r1, g1, b1 = int(style["from"][1:3], 16), int(style["from"][3:5], 16), int(style["from"][5:7], 16)
                r2, g2, b2 = int(style["to"][1:3], 16), int(style["to"][3:5], 16), int(style["to"][5:7], 16)
                
                r = int(r1 + (r2-r1) * (y/120))
                g = int(g1 + (g2-g1) * (y/120))
                b = int(b1 + (b2-b1) * (y/120))
                
                color = f'#{r:02x}{g:02x}{b:02x}'
                canvas.create_line(0, y, 200, y, fill=color)
            
            # Add title
            title_id = canvas.create_text(15, 25, anchor='w', text=style["title"], 
                                        fill="#FFFFFF", font=('Segoe UI', 12, 'bold'))
            
            # Store card info
            card_info = {
                "canvas": canvas,
                "value_attr": style["value_attr"],
                "format": style["format"]
            }
            
            # Create value text
            value_id = canvas.create_text(15, 70, anchor='w', text="$0.00", 
                                        fill="#FFFFFF", font=('Segoe UI', 24, 'bold'))
            
            card_info["value_id"] = value_id
            self.summary_cards.append(card_info)
    
    def create_filter_panel(self, parent_frame):
        """Create filter panel with filtering options"""
        filter_frame = ttk.LabelFrame(parent_frame, text="Filters")
        filter_frame.pack(fill=tk.X, pady=10)
        
        # Create filter row
        row = ttk.Frame(filter_frame)
        row.pack(fill=tk.X, padx=10, pady=5)
        
        # Date Range filter
        date_label = ttk.Label(row, text="Date Range:")
        date_label.pack(side=tk.LEFT, padx=5)
        
        self.filter_vars['date_range'] = tk.StringVar(value="All")
        date_options = ["All", "This Year (2025)", "Last Year (2024)", "2023", 
                       "This Month", "Last Month", "Last 90 Days"]
        
        date_combo = ttk.Combobox(row, textvariable=self.filter_vars['date_range'], 
                                 values=date_options, width=15)
        date_combo.pack(side=tk.LEFT, padx=5)
        
        # Status filter
        status_label = ttk.Label(row, text="Status:")
        status_label.pack(side=tk.LEFT, padx=(20, 5))
        
        self.filter_vars['status'] = tk.StringVar(value="All")
        status_options = ["All", "Paid", "Unpaid", "Pending", "Approved", "Overdue"]
        
        status_combo = ttk.Combobox(row, textvariable=self.filter_vars['status'], 
                                   values=status_options, width=15)
        status_combo.pack(side=tk.LEFT, padx=5)
        
        # Fund filter
        fund_label = ttk.Label(row, text="Fund:")
        fund_label.pack(side=tk.LEFT, padx=(20, 5))
        
        self.filter_vars['fund'] = tk.StringVar(value="All")
        
        # Get funds from database
        funds = self.get_fund_list()
        fund_options = ["All"] + funds
        
        fund_combo = ttk.Combobox(row, textvariable=self.filter_vars['fund'], 
                                 values=fund_options, width=15)
        fund_combo.pack(side=tk.LEFT, padx=5)
        
        # Apply button
        apply_button = ttk.Button(row, text="Apply Filters", 
                                command=self.apply_filters)
        apply_button.pack(side=tk.RIGHT, padx=5)
        
        # Clear button
        clear_button = ttk.Button(row, text="Clear Filters",
                                command=self.clear_filters)
        clear_button.pack(side=tk.RIGHT, padx=5)
    
    def create_sql_display(self, parent_frame, bg_color):
        """Create SQL display area"""
        sql_frame = ttk.LabelFrame(parent_frame, text="Generated SQL")
        sql_frame.pack(fill=tk.X, pady=10)
        
        self.sql_display = tk.Text(sql_frame, height=4, wrap=tk.WORD, 
                                 bg=bg_color, fg='#a5d6a7', 
                                 font=('Consolas', 11))
        self.sql_display.pack(fill=tk.X, padx=5, pady=5)

    def create_invoice_table(self, parent_frame):
        """Create the invoice table with sorting capabilities"""
        table_frame = ttk.LabelFrame(parent_frame, text="Invoices")
        table_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Define columns - reordered to put fund_paid_by first, vendor_name before invoice_number, and added dateofpayment and approver
        columns = ("fund_paid_by", "vendor_name", "invoice_number", "amount", "invoice_date", 
                  "due_date", "payment_status", "dateofpayment", "approver")
        
        # Create treeview
        self.invoice_tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        
        # Add scrollbars
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.invoice_tree.yview)
        self.invoice_tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.invoice_tree.xview)
        self.invoice_tree.configure(xscrollcommand=hsb.set)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Configure columns
        for col in columns:
            display_name = col.replace("_", " ").title()
            self.invoice_tree.heading(col, text=display_name, 
                                    command=lambda c=col: self.sort_treeview(c))
            
            width = 150 if col in ('vendor_name', 'fund_paid_by') else 100
            self.invoice_tree.column(col, width=width, minwidth=80)
        
        # Bind double-click for details
        self.invoice_tree.bind("<Double-1>", self.show_invoice_details)
        
        # Pack the treeview
        self.invoice_tree.pack(fill=tk.BOTH, expand=True)
    
    def create_charts_section(self, parent_frame, bg_color):
        """Create charts section for data visualization"""
        try:
            # Import necessary modules
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            import calendar
            
            # Create container frame
            charts_frame = ttk.LabelFrame(parent_frame, text="Analytics")
            charts_frame.pack(fill=tk.X, pady=10)
            
            # Create frame for charts
            charts_container = ttk.Frame(charts_frame)
            charts_container.pack(fill=tk.X, padx=10, pady=10)
            
            # Create pie chart
            fig1 = Figure(figsize=(5, 3), dpi=100)
            self.pie_ax = fig1.add_subplot(111)
            fig1.patch.set_facecolor(bg_color)
            self.pie_ax.set_facecolor(bg_color)
            self.pie_ax.tick_params(colors='white')
            
            canvas1 = FigureCanvasTkAgg(fig1, charts_container)
            canvas1.draw()
            canvas1.get_tk_widget().pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            # Create bar chart
            fig2 = Figure(figsize=(5, 3), dpi=100)
            self.bar_ax = fig2.add_subplot(111)
            fig2.patch.set_facecolor(bg_color)
            self.bar_ax.set_facecolor(bg_color)
            self.bar_ax.tick_params(colors='white')
            
            canvas2 = FigureCanvasTkAgg(fig2, charts_container)
            canvas2.draw()
            canvas2.get_tk_widget().pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            logger.info("Charts initialized successfully")
            
        except ImportError as e:
            logger.error(f"Failed to create charts, missing dependency: {str(e)}")
            # Create placeholder with message
            charts_frame = ttk.LabelFrame(parent_frame, text="Analytics (Disabled)")
            charts_frame.pack(fill=tk.X, pady=10)
            
            msg = ttk.Label(charts_frame, 
                          text="Charts require matplotlib. Install with: pip install matplotlib")
            msg.pack(pady=20)
            
            # Set axes to None so other methods know charts are disabled
            self.pie_ax = None
            self.bar_ax = None
        
        except Exception as e:
            logger.error(f"Failed to create charts: {str(e)}")
            self.pie_ax = None
            self.bar_ax = None
    
    def create_status_bar(self):
        """Create status bar at bottom of window"""
        status_frame = ttk.Frame(self.frame)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=5)
        
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(status_frame, textvariable=self.status_var, 
                               font=('Segoe UI', 9))
        status_label.pack(side=tk.LEFT, padx=5)
        
        # SQL Library button
        sql_button = ttk.Button(status_frame, text="SQL Query Library", 
                              command=self.show_sql_library)
        sql_button.pack(side=tk.RIGHT, padx=5)
    
    def generate_aging_report(self):
        """Generate an accounts payable aging report"""
        try:
            # Create a top-level window for the aging report
            report_window = tk.Toplevel(self.parent)
            report_window.title("Accounts Payable Aging Report")
            report_window.geometry("900x600")
            report_window.configure(bg="#1e1e2e")
            
            # Create a main frame
            main_frame = ttk.Frame(report_window)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            
            # Title and date
            header_frame = ttk.Frame(main_frame)
            header_frame.pack(fill=tk.X, pady=(0, 20))
            
            title_label = ttk.Label(header_frame, text="Accounts Payable Aging Report", 
                                  font=('Segoe UI', 16, 'bold'))
            title_label.pack(side=tk.LEFT)
            
            # Today's date
            today = datetime.now().strftime("%m/%d/%Y")
            date_label = ttk.Label(header_frame, text=f"Report Date: {today}", 
                                 font=('Segoe UI', 12))
            date_label.pack(side=tk.RIGHT)
            
            # Query to get aging data
            query = """
            SELECT 
                vendor_name,
                invoice_number,
                invoice_date,
                due_date,
                amount,
                CASE
                    WHEN due_date::DATE >= CURRENT_DATE THEN 'Current'
                    WHEN due_date::DATE >= CURRENT_DATE - INTERVAL '30 days' THEN '1-30 Days'
                    WHEN due_date::DATE >= CURRENT_DATE - INTERVAL '60 days' THEN '31-60 Days'
                    WHEN due_date::DATE >= CURRENT_DATE - INTERVAL '90 days' THEN '61-90 Days'
                    ELSE 'Over 90 Days'
                END AS aging_bucket
            FROM invoices
            WHERE payment_status = 'Unpaid'
            ORDER BY due_date ASC
            """
            
            result = self.db_manager.db.execute_query(query)
            
            if result.get('error'):
                messagebox.showerror("Query Error", f"Error retrieving aging data: {result['error']}")
                return
            
            # Initialize buckets for summary
            buckets = {
                'Current': 0,
                '1-30 Days': 0,
                '31-60 Days': 0,
                '61-90 Days': 0,
                'Over 90 Days': 0
            }
            
            # Process data
            report_data = []
            for row in result.get('rows', []):
                vendor = row[0]
                invoice_num = row[1]
                invoice_date = row[2].strftime('%m/%d/%Y') if row[2] else 'N/A'
                due_date = row[3].strftime('%m/%d/%Y') if row[3] else 'N/A'
                amount = float(row[4]) if row[4] is not None else 0
                bucket = row[5]
                
                # Add to summary
                buckets[bucket] += amount
                
                # Add to detail data
                report_data.append({
                    'vendor': vendor,
                    'invoice_num': invoice_num,
                    'invoice_date': invoice_date,
                    'due_date': due_date,
                    'amount': amount,
                    'bucket': bucket
                })
            
            # Summary section
            summary_frame = ttk.LabelFrame(main_frame, text="Summary")
            summary_frame.pack(fill=tk.X, pady=(0, 20))
            
            # Create a grid for summary
            summary_grid = ttk.Frame(summary_frame)
            summary_grid.pack(padx=10, pady=10)
            
            # Header row for summary
            headers = ["Current", "1-30 Days", "31-60 Days", "61-90 Days", "Over 90 Days", "Total"]
            for col, header in enumerate(headers):
                header_label = ttk.Label(summary_grid, text=header, font=('Segoe UI', 11, 'bold'))
                header_label.grid(row=0, column=col, padx=10, pady=5)
            
            # Calculate total
            total = sum(buckets.values())
            
            # Values row for summary
            values = [buckets['Current'], buckets['1-30 Days'], buckets['31-60 Days'], 
                     buckets['61-90 Days'], buckets['Over 90 Days'], total]
            
            for col, value in enumerate(values):
                value_label = ttk.Label(summary_grid, text=f"${value:,.2f}", font=('Segoe UI', 11))
                value_label.grid(row=1, column=col, padx=10, pady=5)
            
            # Detail section
            detail_frame = ttk.LabelFrame(main_frame, text="Invoice Details")
            detail_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
            
            # Create treeview for details
            columns = ("vendor", "invoice_num", "invoice_date", "due_date", "amount", "bucket")
            detail_tree = ttk.Treeview(detail_frame, columns=columns, show="headings")
            
            # Configure columns
            column_widths = {
                "vendor": 200,
                "invoice_num": 120,
                "invoice_date": 100,
                "due_date": 100,
                "amount": 100,
                "bucket": 100
            }
            
            column_texts = {
                "vendor": "Vendor",
                "invoice_num": "Invoice #",
                "invoice_date": "Invoice Date",
                "due_date": "Due Date",
                "amount": "Amount",
                "bucket": "Aging"
            }
            
            for col in columns:
                detail_tree.heading(col, text=column_texts[col])
                detail_tree.column(col, width=column_widths[col])
            
            # Add scrollbars
            vsb = ttk.Scrollbar(detail_frame, orient="vertical", command=detail_tree.yview)
            detail_tree.configure(yscrollcommand=vsb.set)
            
            hsb = ttk.Scrollbar(detail_frame, orient="horizontal", command=detail_tree.xview)
            detail_tree.configure(xscrollcommand=hsb.set)
            
            # Pack treeview and scrollbars
            detail_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            vsb.pack(side=tk.RIGHT, fill=tk.Y)
            hsb.pack(side=tk.BOTTOM, fill=tk.X)
            
            # Populate treeview
            for item in report_data:
                values = (
                    item['vendor'],
                    item['invoice_num'],
                    item['invoice_date'],
                    item['due_date'],
                    f"${item['amount']:,.2f}",
                    item['bucket']
                )
                detail_tree.insert("", tk.END, values=values)
            
            # Button frame
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill=tk.X, pady=10)
            
            # Export button
            export_button = ttk.Button(button_frame, text="Export to CSV", 
                                    command=lambda: self.export_aging_report(report_data))
            export_button.pack(side=tk.LEFT)
            
            # Close button
            close_button = ttk.Button(button_frame, text="Close", 
                                   command=report_window.destroy)
            close_button.pack(side=tk.RIGHT)
            
            # Status
            status_label = ttk.Label(main_frame, text=f"Found {len(report_data)} unpaid invoices",
                                   font=('Segoe UI', 10))
            status_label.pack(side=tk.BOTTOM, anchor=tk.W)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate aging report: {str(e)}")
            logger.error(f"Aging report error: {str(e)}")
    
    def export_aging_report(self, report_data):
        """Export the aging report to a CSV file"""
        try:
            import csv
            from tkinter import filedialog
            
            # Ask for file location
            filename = filedialog.asksaveasfilename(
                initialdir="/",
                title="Save Aging Report",
                filetypes=(("CSV files", "*.csv"), ("All files", "*.*")),
                defaultextension=".csv"
            )
            
            if not filename:  # User cancelled
                return
                
            # Write to CSV
            with open(filename, 'w', newline='') as csvfile:
                fieldnames = ['Vendor', 'Invoice #', 'Invoice Date', 'Due Date', 'Amount', 'Aging']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for item in report_data:
                    writer.writerow({
                        'Vendor': item['vendor'],
                        'Invoice #': item['invoice_num'],
                        'Invoice Date': item['invoice_date'],
                        'Due Date': item['due_date'],
                        'Amount': f"${item['amount']:,.2f}",
                        'Aging': item['bucket']
                    })
            
            messagebox.showinfo("Export Successful", f"Report exported to {filename}")
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export report: {str(e)}")
            logger.error(f"Report export error: {str(e)}")

    def update_dashboard_data(self):
        """Update all dashboard data safely"""
        try:
            self.status_var.set("Updating dashboard data...")
            
            # Calculate summary values
            current_year = datetime.now().year
            
            # Total amount - get sum of all invoices
            query = "SELECT COALESCE(SUM(amount), 0) FROM invoices"
            result = self.db_manager.db.execute_query(query)
            if not result.get('error') and result['rows']:
                self.total_amount = result['rows'][0][0] or 0
            
            # Current year paid - properly filter by payment_status and year
            query = f"""
            SELECT COALESCE(SUM(amount), 0) FROM invoices 
            WHERE payment_status = 'Paid' 
            AND EXTRACT(YEAR FROM invoice_date::DATE) = {current_year}
            """
            result = self.db_manager.db.execute_query(query)
            if not result.get('error') and result['rows']:
                self.total_paid_current_year = result['rows'][0][0] or 0
            
            # Previous year paid
            query = f"""
            SELECT COALESCE(SUM(amount), 0) FROM invoices 
            WHERE payment_status = 'Paid' 
            AND EXTRACT(YEAR FROM invoice_date::DATE) = {current_year-1}
            """
            result = self.db_manager.db.execute_query(query)
            if not result.get('error') and result['rows']:
                self.total_paid_last_year = result['rows'][0][0] or 0
            
            # 2023 paid
            query = """
            SELECT COALESCE(SUM(amount), 0) FROM invoices 
            WHERE payment_status = 'Paid' 
            AND EXTRACT(YEAR FROM invoice_date::DATE) = 2023
            """
            result = self.db_manager.db.execute_query(query)
            if not result.get('error') and result['rows']:
                self.total_paid_prev_year = result['rows'][0][0] or 0
            
            # Total current (unpaid but not overdue)
            query = """
            SELECT COALESCE(SUM(amount), 0) FROM invoices 
            WHERE payment_status = 'Unpaid'
            AND (due_date::DATE >= CURRENT_DATE OR due_date IS NULL)
            """
            result = self.db_manager.db.execute_query(query)
            if not result.get('error') and result['rows']:
                self.total_unpaid = result['rows'][0][0] or 0
            
            # Total overdue
            query = """
            SELECT COALESCE(SUM(amount), 0) FROM invoices 
            WHERE payment_status = 'Unpaid' 
            AND due_date::DATE < CURRENT_DATE
            """
            result = self.db_manager.db.execute_query(query)
            if not result.get('error') and result['rows']:
                self.total_overdue = result['rows'][0][0] or 0
            
            # Update UI components safely with error handling
            self.update_summary_cards()
            self.apply_filters()
            self.update_charts()
            
            self.status_var.set("Dashboard updated successfully")
        except Exception as e:
            self.status_var.set(f"Error updating dashboard: {str(e)}")
            logger.error(f"Dashboard update error: {str(e)}")
    
    def update_summary_cards(self):
        """Update the summary cards with current data"""
        try:
            for card in self.summary_cards:
                # Get the attribute value
                value_attr = card["value_attr"]
                if hasattr(self, value_attr):
                    value = getattr(self, value_attr)
                    
                    # Format the value
                    try:
                        value = float(value) if value is not None else 0
                        if card["format"] == "${:,.2f}":
                            formatted_value = f"${value:,.2f}"
                        else:
                            formatted_value = card["format"].format(value)
                    except (ValueError, TypeError):
                        formatted_value = "$0.00"
                    
                    # Update the display
                    card["canvas"].itemconfig(card["value_id"], text=formatted_value)
        except Exception as e:
            logger.error(f"Error updating summary cards: {str(e)}")
    
    def update_charts(self):
        """Update charts with current data if initialized"""
        # Skip if charts are not initialized
        if not hasattr(self, 'pie_ax') or self.pie_ax is None:
            logger.info("Charts not initialized, skipping update")
            return
            
        if not hasattr(self, 'bar_ax') or self.bar_ax is None:
            logger.info("Bar chart not initialized, skipping update")
            return
        
        try:
            # Import calendar module for month names
            import calendar
            
            # Clear existing charts
            self.pie_ax.clear()
            self.bar_ax.clear()
            
            # Get payment status distribution
            query = """
            SELECT payment_status, COUNT(*) as count 
            FROM invoices 
            GROUP BY payment_status
            """
            result = self.db_manager.db.execute_query(query)
            
            if not result.get('error') and result['rows']:
                # Process data for pie chart
                labels = [row[0] for row in result['rows']]
                sizes = [row[1] for row in result['rows']]
                
                # Create pie chart
                self.pie_ax.pie(sizes, labels=labels, autopct='%1.1f%%', 
                             startangle=90, colors=['#bb86fc', '#03dac5', '#cf6679', '#8ab4f8'])
                self.pie_ax.set_title('Invoice Status Distribution', color='white')
                
                # Force redraw
                self.pie_ax.figure.canvas.draw()
            
            # Get monthly totals
            query = """
            SELECT 
                EXTRACT(MONTH FROM invoice_date::DATE) as month,
                EXTRACT(YEAR FROM invoice_date::DATE) as year,
                SUM(amount) as total
            FROM invoices
            WHERE invoice_date::DATE >= CURRENT_DATE - INTERVAL '6 months'
            GROUP BY month, year
            ORDER BY year, month
            """
            result = self.db_manager.db.execute_query(query)
            
            if not result.get('error') and result['rows']:
                # Process data for bar chart
                months = []
                totals = []
                
                for row in result['rows']:
                    month_num = int(row[0])
                    year = int(row[1])
                    try:
                        total = float(row[2]) if row[2] is not None else 0
                    except (ValueError, TypeError):
                        total = 0
                    
                    month_name = calendar.month_abbr[month_num]
                    months.append(f"{month_name} {year}")
                    totals.append(total)
                
                # Create bar chart
                bars = self.bar_ax.bar(months, totals, color='#bb86fc')
                self.bar_ax.set_title('Monthly Invoice Totals', color='white')
                self.bar_ax.set_ylabel('Amount ($)', color='white')
                self.bar_ax.tick_params(axis='x', rotation=45)
                
                # Add dollar values on top of bars
                for i, v in enumerate(totals):
                    self.bar_ax.text(i, v + (max(totals) * 0.03), 
                                   f"${v:,.0f}", 
                                   ha='center', 
                                   color='white',
                                   fontsize=8)
                
                # Force redraw
                self.bar_ax.figure.canvas.draw()
                
        except Exception as e:
            logger.error(f"Error updating charts: {str(e)}")
    
    def get_fund_list(self):
        """Get list of unique funds from the database"""
        query = "SELECT DISTINCT fund_paid_by FROM invoices WHERE fund_paid_by IS NOT NULL"
        result = self.db_manager.db.execute_query(query)
        
        if result.get('error') or not result.get('rows'):
            return []
        
        return [row[0] for row in result['rows']]
    
    def apply_filters(self):
        """Apply filters to the invoice table"""
        # Skip if tree is not initialized
        if not hasattr(self, 'invoice_tree') or self.invoice_tree is None:
            logger.error("Invoice tree not initialized, cannot apply filters")
            return
            
        try:
            # Clear existing rows
            for item in self.invoice_tree.get_children():
                self.invoice_tree.delete(item)
            
            # Build query based on filters
            conditions = []
            params = []
            
            # Status filter
            status = self.filter_vars['status'].get()
            if status and status != "All":
                if status == "Overdue":
                    conditions.append("payment_status = 'Unpaid' AND due_date::DATE < CURRENT_DATE")
                else:
                    conditions.append("payment_status = %s")
                    params.append(status)
            
            # Date range filter
            date_range = self.filter_vars['date_range'].get()
            if date_range and date_range != "All":
                current_year = datetime.now().year
                current_month = datetime.now().month
                
                if date_range == "This Year (2025)":
                    conditions.append("EXTRACT(YEAR FROM invoice_date::DATE) = %s")
                    params.append(current_year)
                elif date_range == "Last Year (2024)":
                    conditions.append("EXTRACT(YEAR FROM invoice_date::DATE) = %s")
                    params.append(current_year - 1)
                elif date_range == "2023":
                    conditions.append("EXTRACT(YEAR FROM invoice_date::DATE) = %s")
                    params.append(2023)
                elif date_range == "This Month":
                    conditions.append("EXTRACT(YEAR FROM invoice_date::DATE) = %s AND EXTRACT(MONTH FROM invoice_date::DATE) = %s")
                    params.extend([current_year, current_month])
                elif date_range == "Last Month":
                    last_month = current_month - 1 if current_month > 1 else 12
                    last_month_year = current_year if current_month > 1 else current_year - 1
                    conditions.append("EXTRACT(YEAR FROM invoice_date::DATE) = %s AND EXTRACT(MONTH FROM invoice_date::DATE) = %s")
                    params.extend([last_month_year, last_month])
                elif date_range == "Last 90 Days":
                    conditions.append("invoice_date::DATE >= CURRENT_DATE - INTERVAL '90 days'")
            
            # Fund filter
            fund = self.filter_vars['fund'].get()
            if fund and fund != "All":
                conditions.append("fund_paid_by = %s")
                params.append(fund)
            
            # Build the query with specific columns in the right order - matching the treeview display order
            query = """
            SELECT 
                fund_paid_by,
                vendor_name,
                invoice_number, 
                amount, 
                invoice_date, 
                due_date, 
                payment_status,
                dateofpayment,
                approver,
                invoice_id
            FROM invoices
            """
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY invoice_date DESC"
            
            # Execute the query
            logger.info(f"Executing filter query: {query} with params: {params}")
            result = self.db_manager.db.execute_query(query, params)
            
            if result.get('error'):
                error_msg = f"Error: {result['error']}"
                logger.error(error_msg)
                self.status_var.set(error_msg)
                return
            
            # Log the result for debugging
            row_count = len(result.get('rows', []))
            logger.info(f"Query returned {row_count} rows")
            
            if row_count == 0:
                # Run a simple query to check if there's data at all
                check_query = "SELECT COUNT(*) FROM invoices"
                check_result = self.db_manager.db.execute_query(check_query)
                if not check_result.get('error') and check_result['rows']:
                    total_count = check_result['rows'][0][0]
                    logger.info(f"Total invoices in database: {total_count}")
                    if total_count > 0:
                        logger.warning("Database has records but filter returned none")
            
            # Populate treeview
            for row in result.get('rows', []):
                # Format values for display - excluding invoice_id which is the last column
                try:
                    if len(row) == 0:
                        logger.warning("Empty row returned from query")
                        continue
                        
                    invoice_id = row[-1] if len(row) > 9 else None  # Save invoice_id for potential future use
                    display_values = row[:-1] if len(row) > 9 else row  # Get all columns except the last one (invoice_id)
                    
                    # Log the row for debugging
                    logger.debug(f"Processing row: {row}")
                    
                    # Format all values according to their type
                    formatted_values = []
                    for i, value in enumerate(display_values):
                        if isinstance(value, (datetime, date)):
                            formatted_values.append(value.strftime('%m/%d/%Y'))
                        elif isinstance(value, (int, float)) and i == 3:  # Amount column (index 3 with new order)
                            try:
                                num_value = float(value)
                                formatted_values.append(f"${num_value:,.2f}")
                            except (ValueError, TypeError):
                                formatted_values.append("$0.00")
                        else:
                            formatted_values.append(str(value) if value is not None else "")
                    
                    # Insert into tree
                    self.invoice_tree.insert("", "end", values=formatted_values)
                except Exception as row_error:
                    logger.error(f"Error processing row {row}: {str(row_error)}")
            
            self.status_var.set(f"Displaying {row_count} invoices")
            
        except Exception as e:
            error_msg = f"Error applying filters: {str(e)}"
            logger.error(error_msg)
            self.status_var.set(error_msg)
    
    def clear_filters(self):
        """Reset all filters to default values"""
        self.filter_vars['status'].set("All")
        self.filter_vars['date_range'].set("All")
        self.filter_vars['fund'].set("All")
        
        # Apply the cleared filters
        self.apply_filters()

    def execute_search(self):
        """Execute a search using natural language query if available, otherwise use keyword search"""
        query_text = self.filter_vars['search'].get()
        if not query_text:
            self.status_var.set("Please enter a search query")
            return
        
        self.status_var.set("Processing query...")
        
        if self.llm_client:
            # Use LLM if available
            try:
                sql_query = self.llm_client.generate_sql_query(query_text)
                self.run_search_query(sql_query)
            except Exception as e:
                logger.error(f"LLM search error: {str(e)}")
                # Fall back to keyword search
                self.keyword_search(query_text)
        else:
            # Use keyword search
            self.keyword_search(query_text)
    
    def keyword_search(self, query_text):
        """Perform keyword-based search when LLM is not available"""
        query_lower = query_text.lower()
        
        # Use consistent column selection for all queries
        columns = """
                fund_paid_by,
                invoice_number, 
                vendor_name, 
                amount, 
                invoice_date, 
                due_date, 
                payment_status,
                dateofpayment,
                approver,
                invoice_id
        """
        
        if "unpaid" in query_lower:
            sql = f"SELECT {columns} FROM invoices WHERE payment_status = 'Unpaid' ORDER BY due_date ASC"
        elif "paid" in query_lower:
            sql = f"SELECT {columns} FROM invoices WHERE payment_status = 'Paid' ORDER BY invoice_date DESC"
        elif "overdue" in query_lower:
            sql = f"SELECT {columns} FROM invoices WHERE payment_status = 'Unpaid' AND due_date < CURRENT_DATE ORDER BY due_date ASC"
        elif "this year" in query_lower:
            sql = f"SELECT {columns} FROM invoices WHERE EXTRACT(YEAR FROM invoice_date::DATE) = {datetime.now().year}"
        elif "last year" in query_lower:
            sql = f"SELECT {columns} FROM invoices WHERE EXTRACT(YEAR FROM invoice_date::DATE) = {datetime.now().year - 1}"
        else:
            # Search across multiple fields - ensure we're using proper column names
            sql = f"""
            SELECT 
                fund_paid_by,
                invoice_number, 
                vendor_name, 
                amount, 
                invoice_date, 
                due_date, 
                payment_status,
                dateofpayment,
                approver,
                invoice_id
            FROM invoices 
            WHERE invoice_number ILIKE '%{query_text}%' 
               OR vendor_name ILIKE '%{query_text}%'
               OR payment_status ILIKE '%{query_text}%'
               OR fund_paid_by ILIKE '%{query_text}%'
            ORDER BY invoice_date DESC
            LIMIT 100
            """
        
        self.run_search_query(sql)
    
    def run_search_query(self, sql_query):
        """Execute and display results for a SQL query"""
        # Update SQL display
        if hasattr(self, 'sql_display') and self.sql_display:
            self.sql_display.delete("1.0", tk.END)
            self.sql_display.insert(tk.END, sql_query)
        
        # Execute query
        result = self.db_manager.db.execute_query(sql_query)
        
        # Check for error
        if result.get('error'):
            self.status_var.set(f"Error: {result['error']}")
            return
        
        # Update tree if initialized
        if hasattr(self, 'invoice_tree') and self.invoice_tree:
            # Clear existing rows
            for item in self.invoice_tree.get_children():
                self.invoice_tree.delete(item)
                
            # Check for rows
            if not result.get('rows'):
                self.status_var.set("No results found")
                return
                
            # Add rows to tree
            for row in result['rows']:
                # Extract needed columns for display - preserve all columns that match treeview
                display_values = row
                
                # Remove any extra columns beyond what treeview displays (like invoice_id)
                if len(row) > 9:  # We display 9 columns in the treeview
                    display_values = row[:9]
                
                # Format values for display
                formatted_values = []
                for i, value in enumerate(display_values):
                    if isinstance(value, (datetime, date)):
                        formatted_values.append(value.strftime('%m/%d/%Y'))
                    elif isinstance(value, (int, float)) and i == 3:  # Amount column (index 3 with new order)
                        try:
                            num_value = float(value)
                            formatted_values.append(f"${num_value:,.2f}")
                        except (ValueError, TypeError):
                            formatted_values.append("$0.00")
                    else:
                        formatted_values.append(str(value) if value is not None else "")
            
                # Insert into tree
                self.invoice_tree.insert("", "end", values=formatted_values)
            
            self.status_var.set(f"Found {len(result['rows'])} results")
    
    def sort_treeview(self, column):
        """Sort treeview by the selected column"""
        # Skip if tree not initialized
        if not hasattr(self, 'invoice_tree') or self.invoice_tree is None:
            return
            
        # Initialize sort_reverse if not exists
        if not hasattr(self, 'sort_reverse'):
            self.sort_reverse = False
        else:
            self.sort_reverse = not self.sort_reverse
        
        # Get all items
        data = [(self.invoice_tree.set(item, column), item) 
                for item in self.invoice_tree.get_children('')]
        
        # Sort data
        data.sort(reverse=self.sort_reverse)
        
        # Rearrange items
        for index, (val, item) in enumerate(data):
            self.invoice_tree.move(item, '', index)
    
    def show_invoice_details(self, event):
        """Show detailed view of the selected invoice"""
        # Skip if tree not initialized
        if not hasattr(self, 'invoice_tree') or self.invoice_tree is None:
            return
            
        selected_items = self.invoice_tree.selection()
        if not selected_items:
            return
        
        item = selected_items[0]
        values = self.invoice_tree.item(item, "values")
        
        # Get invoice_id for this invoice - needed for updates
        query = f"""
        SELECT invoice_id FROM invoices 
        WHERE invoice_number = '{values[1]}'
        LIMIT 1
        """
        result = self.db_manager.db.execute_query(query)
        invoice_id = None
        if not result.get('error') and result['rows']:
            invoice_id = result['rows'][0][0]
        
        # Create details window
        details_window = tk.Toplevel(self.parent)
        details_window.title(f"Invoice Details: {values[1]}")  # Using invoice_number (index 1)
        details_window.geometry("550x480")
        details_window.configure(bg="#1e1e2e")
        
        # Main content frame
        content_frame = ttk.Frame(details_window)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Header
        header_label = ttk.Label(content_frame, text=f"Invoice #{values[1]}", 
                               font=('Segoe UI', 16, 'bold'))
        header_label.pack(pady=(0, 15))
        
        # Details grid
        details_frame = ttk.Frame(content_frame)
        details_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create variables to hold editable fields
        approver_var = tk.StringVar(value=values[8] if len(values) > 8 and values[8] else "")
        status_var = tk.StringVar(value=values[6] if values[6] else "")
        
        # Get valid status options
        status_options = ["Paid", "Unpaid", "Pending", "Approved", "Overdue"]
        
        # Field labels and values - updated for the new column order
        fields = [
            ("Fund", values[0], None),
            ("Invoice Number", values[1], None),
            ("Vendor Name", values[2], None),
            ("Amount", values[3], None),
            ("Invoice Date", values[4], None),
            ("Due Date", values[5], None),
            ("Status", values[6], status_var),
            ("Payment Date", values[7] if len(values) > 7 else "", None),
            ("Approver", values[8] if len(values) > 8 else "", approver_var)
        ]
        
        row = 0
        for label, value, var in fields:
            # Label
            field_label = ttk.Label(details_frame, text=f"{label}:", 
                                  font=('Segoe UI', 11, 'bold'))
            field_label.grid(row=row, column=0, sticky=tk.W, padx=5, pady=8)
            
            # Value - either static or editable
            if var is not None:
                if label == "Status":
                    field_input = ttk.Combobox(details_frame, textvariable=var, 
                                           values=status_options, width=20)
                    field_input.grid(row=row, column=1, sticky=tk.W, padx=5, pady=8)
                else:
                    field_input = ttk.Entry(details_frame, textvariable=var, width=25)
                    field_input.grid(row=row, column=1, sticky=tk.W, padx=5, pady=8)
            else:
                value_label = ttk.Label(details_frame, text=value, font=('Segoe UI', 11))
                value_label.grid(row=row, column=1, sticky=tk.W, padx=5, pady=8)
            
            row += 1
        
        # Add helpful text for approver field
        hint_label = ttk.Label(details_frame, text="Enter the name of the person who approved this invoice",
                             font=('Segoe UI', 9, 'italic'), foreground="#aaaaaa")
        hint_label.grid(row=8, column=1, sticky=tk.W, padx=5, pady=(0, 8))
        
        # Button frame
        button_frame = ttk.Frame(details_window)
        button_frame.pack(fill=tk.X, padx=20, pady=15)
        
        # Save button - only show if invoice_id was found
        if invoice_id:
            save_button = ttk.Button(button_frame, text="Save Changes", 
                                   command=lambda: self.save_invoice_changes(
                                       invoice_id, approver_var.get(), status_var.get(), details_window))
            save_button.pack(side=tk.RIGHT, padx=5)
        
        # Close button
        close_button = ttk.Button(button_frame, text="Close", 
                                command=details_window.destroy)
        close_button.pack(side=tk.RIGHT)
    
    def show_search_suggestions(self):
        """Show search suggestions dialog"""
        suggestions = [
            "Show all unpaid invoices",
            "Find invoices due this month",
            "Show invoices over $5000",
            "Show invoices from Vendor X",
            "Find overdue invoices",
            "Show invoices from last year",
            "Find invoices paid from Growth Fund"
        ]
        
        suggest_window = tk.Toplevel(self.parent)
        suggest_window.title("Search Suggestions")
        suggest_window.geometry("400x300")
        suggest_window.configure(bg="#1e1e2e")
        
        # Content frame
        content_frame = ttk.Frame(suggest_window)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Header
        header_label = ttk.Label(content_frame, text="Try these search queries:", 
                               font=('Segoe UI', 14, 'bold'))
        header_label.pack(pady=(0, 15))
        
        # Suggestions list
        for suggestion in suggestions:
            suggest_frame = ttk.Frame(content_frame)
            suggest_frame.pack(fill=tk.X, pady=5)
            
            bullet = ttk.Label(suggest_frame, text="•", font=('Segoe UI', 12))
            bullet.pack(side=tk.LEFT, padx=(0, 10))
            
            label = ttk.Label(suggest_frame, text=suggestion, font=('Segoe UI', 11))
            label.pack(side=tk.LEFT)
            
            # Add button to use this suggestion
            use_button = ttk.Button(suggest_frame, text="Use", 
                                  command=lambda s=suggestion: self.use_suggestion(s, suggest_window))
            use_button.pack(side=tk.RIGHT)
        
        # Close button
        close_button = ttk.Button(content_frame, text="Close", 
                                command=suggest_window.destroy)
        close_button.pack(pady=15)
    
    def use_suggestion(self, suggestion, window):
        """Use a suggested search query"""
        if hasattr(self, 'filter_vars') and 'search' in self.filter_vars:
            self.filter_vars['search'].set(suggestion)
            window.destroy()
            self.execute_search()
    
    def show_sql_library(self):
        """Show SQL library dialog - placeholder"""
        messagebox.showinfo("SQL Library", "SQL Library feature coming soon!")

    def show_schema_tools(self):
        """Show schema tools dialog"""
        tools_window = tk.Toplevel(self.parent)
        tools_window.title("Schema Tools")
        tools_window.geometry("600x500")
        tools_window.configure(bg="#1e1e2e")
        
        # Content frame
        content_frame = ttk.Frame(tools_window)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Header
        header_label = ttk.Label(content_frame, text="Database Schema Tools", 
                               font=('Segoe UI', 14, 'bold'))
        header_label.pack(pady=(0, 15))
        
        # Create a notebook with tabs
        notebook = ttk.Notebook(content_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create tabs
        schema_tab = ttk.Frame(notebook)
        fix_tab = ttk.Frame(notebook)
        diag_tab = ttk.Frame(notebook)
        
        notebook.add(schema_tab, text="Schema Info")
        notebook.add(fix_tab, text="Fix Issues")
        notebook.add(diag_tab, text="Diagnostics")
        
        # Schema Info tab
        self.create_schema_info_tab(schema_tab)
        
        # Fix Issues tab
        self.create_fix_issues_tab(fix_tab)
        
        # Diagnostics tab
        self.create_diagnostics_tab(diag_tab)
    
    def create_schema_info_tab(self, parent):
        """Create schema info tab content"""
        # Create table selection
        select_frame = ttk.Frame(parent)
        select_frame.pack(fill=tk.X, pady=10)
        
        select_label = ttk.Label(select_frame, text="Select Table:")
        select_label.pack(side=tk.LEFT, padx=5)
        
        table_var = tk.StringVar()
        
        # Get tables from database
        tables = []
        tables_result = self.db_manager.db.execute_query("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
        if not tables_result.get('error') and tables_result.get('rows'):
            tables = [row[0] for row in tables_result['rows']]
        
        table_combo = ttk.Combobox(select_frame, textvariable=table_var, 
                                 values=tables, width=30)
        table_combo.pack(side=tk.LEFT, padx=5)
        
        view_button = ttk.Button(select_frame, text="View Schema", 
                               command=lambda: self.view_table_schema(table_var.get()))
        view_button.pack(side=tk.LEFT, padx=5)
        
        # Schema display area
        schema_frame = ttk.LabelFrame(parent, text="Table Schema")
        schema_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Column display
        columns = ("column_name", "data_type", "nullable", "default")
        
        self.schema_tree = ttk.Treeview(schema_frame, columns=columns, show="headings")
        
        # Configure columns
        self.schema_tree.heading("column_name", text="Column Name")
        self.schema_tree.heading("data_type", text="Data Type")
        self.schema_tree.heading("nullable", text="Nullable")
        self.schema_tree.heading("default", text="Default Value")
        
        self.schema_tree.column("column_name", width=150)
        self.schema_tree.column("data_type", width=100)
        self.schema_tree.column("nullable", width=80)
        self.schema_tree.column("default", width=150)
        
        # Add scrollbar
        schema_scroll = ttk.Scrollbar(schema_frame, orient=tk.VERTICAL, 
                                    command=self.schema_tree.yview)
        self.schema_tree.configure(yscrollcommand=schema_scroll.set)
        
        self.schema_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        schema_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    
    def view_table_schema(self, table_name):
        """View schema for selected table"""
        if not table_name:
            return
            
        # Clear existing items
        for item in self.schema_tree.get_children():
            self.schema_tree.delete(item)
            
        # Query schema information
        query = """
        SELECT column_name, data_type, 
               CASE WHEN is_nullable = 'YES' THEN 'Yes' ELSE 'No' END as nullable,
               column_default
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position
        """
        
        result = self.db_manager.db.execute_query(query, [table_name])
        
        if result.get('error'):
            self.status_var.set(f"Error: {result['error']}")
            return
            
        # Populate treeview
        for row in result['rows']:
            self.schema_tree.insert("", "end", values=row)
    
    def create_fix_issues_tab(self, parent):
        """Create fix issues tab content"""
        # Add fix buttons
        fix_frame = ttk.Frame(parent)
        fix_frame.pack(fill=tk.X, pady=10)
        
        fix_label = ttk.Label(fix_frame, text="Fix Database Issues:")
        fix_label.pack(anchor=tk.W, pady=(0, 10))
        
        # Fix type issues button
        fix_types_button = ttk.Button(fix_frame, text="Fix Column Types", 
                                    command=self.fix_column_types)
        fix_types_button.pack(fill=tk.X, pady=5)
        
        # Fix date fields button
        fix_dates_button = ttk.Button(fix_frame, text="Fix Date Fields", 
                                    command=self.fix_date_fields)
        fix_dates_button.pack(fill=tk.X, pady=5)
        
        # Fix missing columns
        fix_columns_button = ttk.Button(fix_frame, text="Fix Missing Columns", 
                                      command=self.fix_missing_columns)
        fix_columns_button.pack(fill=tk.X, pady=5)
        
        # Fix vendor column button
        fix_vendor_button = ttk.Button(fix_frame, text="Fix Vendor Name Column", 
                                     command=self.fix_vendor_column_issue)
        fix_vendor_button.pack(fill=tk.X, pady=5)
        
        # Log area
        log_frame = ttk.LabelFrame(parent, text="Fix Operations Log")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.fix_log = tk.Text(log_frame, height=10, bg="#2a2a3a", fg="#e0e0e0")
        self.fix_log.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def create_diagnostics_tab(self, parent):
        """Create diagnostics tab content"""
        # Add diagnostic buttons
        diag_frame = ttk.Frame(parent)
        diag_frame.pack(fill=tk.X, pady=10)
        
        diag_label = ttk.Label(diag_frame, text="Database Diagnostics:")
        diag_label.pack(anchor=tk.W, pady=(0, 10))
        
        # Check data integrity
        integrity_button = ttk.Button(diag_frame, text="Check Data Integrity", 
                                    command=self.check_data_integrity)
        integrity_button.pack(fill=tk.X, pady=5)
        
        # Run query performance test
        perf_button = ttk.Button(diag_frame, text="Test Query Performance", 
                               command=self.test_query_performance)
        perf_button.pack(fill=tk.X, pady=5)
        
        # Log area
        diag_log_frame = ttk.LabelFrame(parent, text="Diagnostics Results")
        diag_log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.diag_log = tk.Text(diag_log_frame, height=10, bg="#2a2a3a", fg="#e0e0e0")
        self.diag_log.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def fix_column_types(self):
        """Fix column type mismatches"""
        try:
            self.fix_log.delete(1.0, tk.END)
            self.fix_log.insert(tk.END, "Starting column type fix...\n")
            
            # Fix each table
            for table in ['invoices', 'vendors', 'funds']:
                self.fix_log.insert(tk.END, f"Checking table: {table}...\n")
                
                # Get current column types
                columns_query = f"""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = '{table}'
                ORDER BY ordinal_position
                """
                
                columns_result = self.db_manager.db.execute_query(columns_query)
                
                if columns_result.get('error') or not columns_result.get('rows'):
                    self.fix_log.insert(tk.END, f"Error getting columns for {table}\n")
                    continue
                    
                fixed_columns = []
                
                # Check for character varying and convert to VARCHAR
                for col_info in columns_result['rows']:
                    col_name = col_info[0]
                    col_type = col_info[1]
                    
                    if col_type == 'character varying':
                        try:
                            # Alter column to VARCHAR
                            alter_query = f"""
                            ALTER TABLE {table} 
                            ALTER COLUMN {col_name} TYPE VARCHAR
                            USING {col_name}::VARCHAR
                            """
                            
                            alter_result = self.db_manager.db.execute_query(alter_query)
                            
                            if not alter_result.get('error'):
                                fixed_columns.append(col_name)
                                self.fix_log.insert(tk.END, f"  Fixed column {col_name} from 'character varying' to 'VARCHAR'\n")
                        except Exception as e:
                            self.fix_log.insert(tk.END, f"  Error fixing {col_name}: {str(e)}\n")
                
                if fixed_columns:
                    self.fix_log.insert(tk.END, f"Fixed columns in {table}: {', '.join(fixed_columns)}\n")
                else:
                    self.fix_log.insert(tk.END, f"No column type issues found in {table}\n")
            
            self.fix_log.insert(tk.END, "Column type fix complete.\n")
        except Exception as e:
            self.fix_log.insert(tk.END, f"Error during column type fix: {str(e)}\n")
    
    def fix_date_fields(self):
        """Fix date fields with wrong format or type"""
        try:
            self.fix_log.delete(1.0, tk.END)
            self.fix_log.insert(tk.END, "Starting date field fix...\n")
            
            # Get date columns
            query = """
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
            AND (data_type = 'text' OR data_type = 'varchar' OR data_type = 'character varying')
            AND (column_name LIKE '%date%' OR column_name LIKE '%_dt%' OR column_name LIKE '%_at')
            """
            
            result = self.db_manager.db.execute_query(query)
            
            if result.get('error'):
                self.fix_log.insert(tk.END, f"Error: {result['error']}\n")
                return
                
            # Process each potential date column
            for row in result['rows']:
                table = row[0]
                column = row[1]
                data_type = row[2]
                
                self.fix_log.insert(tk.END, f"Checking {table}.{column} ({data_type})...\n")
                
                # Check for date-like content in the column
                date_check_query = f"""
                SELECT COUNT(*) FROM {table}
                WHERE {column} ~ '^\\d{{4}}-\\d{{2}}-\\d{{2}}$'
                   OR {column} ~ '^\\d{{2}}/\\d{{2}}/\\d{{4}}$'
                   OR {column} ~ '^\\d{{2}}-\\d{{2}}-\\d{{4}}$'
                """
                
                check_result = self.db_manager.db.execute_query(date_check_query)
                
                if check_result.get('error') or not check_result.get('rows'):
                    self.fix_log.insert(tk.END, f"  Error checking date patterns: {check_result.get('error', 'No data')}\n")
                    continue
                
                date_count = check_result['rows'][0][0]
                
                # If we found date patterns, try to convert
                if date_count > 0:
                    self.fix_log.insert(tk.END, f"  Found {date_count} potential dates in {table}.{column}\n")
                    
                    try:
                        # Create a temporary column
                        temp_col = f"temp_{column}"
                        
                        # Add the temporary column
                        add_query = f"ALTER TABLE {table} ADD COLUMN {temp_col} DATE"
                        self.db_manager.db.execute_query(add_query)
                        
                        # Copy and convert data
                        update_query = f"""
                        UPDATE {table} 
                        SET {temp_col} = 
                            CASE 
                                WHEN {column} ~ E'^\\d{{4}}-\\d{{2}}-\\d{{2}}$' THEN {column}::DATE
                                WHEN {column} ~ E'^\\d{{2}}/\\d{{2}}/\\d{{4}}$' THEN to_date({column}, 'MM/DD/YYYY')
                                WHEN {column} ~ E'^\\d{{2}}-\\d{{2}}-\\d{{4}}$' THEN to_date({column}, 'MM-DD-YYYY')
                                ELSE NULL 
                            END
                        """
                        self.db_manager.db.execute_query(update_query)
                        
                        # Drop original column
                        drop_query = f"ALTER TABLE {table} DROP COLUMN {column}"
                        self.db_manager.db.execute_query(drop_query)
                        
                        # Rename temp column
                        rename_query = f"ALTER TABLE {table} RENAME COLUMN {temp_col} TO {column}"
                        self.db_manager.db.execute_query(rename_query)
                        
                        self.fix_log.insert(tk.END, f"  Successfully converted {table}.{column} to DATE type\n")
                        
                    except Exception as e:
                        self.fix_log.insert(tk.END, f"  Error fixing {table}.{column}: {str(e)}\n")
                else:
                    self.fix_log.insert(tk.END, f"  No date patterns found in {table}.{column}\n")
            
            self.fix_log.insert(tk.END, "Date field fix complete.\n")
        except Exception as e:
            self.fix_log.insert(tk.END, f"Error during date field fix: {str(e)}\n")
    
    def fix_missing_columns(self):
        """Fix missing columns in database tables"""
        try:
            self.fix_log.delete(1.0, tk.END)
            self.fix_log.insert(tk.END, "Checking for missing columns...\n")
            
            # Define expected schemas
            expected_schemas = {
                'invoices': {
                    'required': {
                        'id': 'SERIAL PRIMARY KEY',
                        'invoice_number': 'VARCHAR(50)',
                        'invoice_date': 'DATE',
                        'amount': 'NUMERIC(15,2)',
                        'vendor_name': 'VARCHAR(100)',
                        'payment_status': 'VARCHAR(20)'
                    },
                    'optional': {
                        'due_date': 'DATE',
                        'fund_paid_by': 'VARCHAR(50)',
                        'description': 'TEXT',
                        'notes': 'TEXT',
                        'created_at': 'TIMESTAMP',
                        'updated_at': 'TIMESTAMP'
                    }
                },
                'vendors': {
                    'required': {
                        'id': 'SERIAL PRIMARY KEY',
                        'name': 'VARCHAR(100)'
                    },
                    'optional': {
                        'contact_name': 'VARCHAR(100)',
                        'email': 'VARCHAR(100)',
                        'phone': 'VARCHAR(20)',
                        'address': 'TEXT',
                        'notes': 'TEXT'
                    }
                },
                'funds': {
                    'required': {
                        'id': 'SERIAL PRIMARY KEY',
                        'name': 'VARCHAR(100)'
                    },
                    'optional': {
                        'description': 'TEXT',
                        'balance': 'NUMERIC(15,2)',
                        'active': 'BOOLEAN'
                    }
                }
            }
            
            # Check each table
            for table_name, schema in expected_schemas.items():
                self.fix_log.insert(tk.END, f"Checking table: {table_name}...\n")
                
                # Get current columns
                columns_query = f"""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = '{table_name}'
                """
                
                result = self.db_manager.db.execute_query(columns_query)
                
                if result.get('error'):
                    self.fix_log.insert(tk.END, f"  Error getting columns: {result['error']}\n")
                    continue
                
                if not result.get('rows'):
                    self.fix_log.insert(tk.END, f"  Table {table_name} does not exist or has no columns\n")
                    continue
                
                # Get existing columns
                existing_columns = [row[0].lower() for row in result['rows']]
                
                # Check for missing required columns
                missing_required = []
                for col, col_type in schema['required'].items():
                    if col.lower() not in existing_columns:
                        missing_required.append((col, col_type))
                
                # Check for missing optional columns
                missing_optional = []
                for col, col_type in schema['optional'].items():
                    if col.lower() not in existing_columns:
                        missing_optional.append((col, col_type))
                
                # Add missing required columns
                for col, col_type in missing_required:
                    self.fix_log.insert(tk.END, f"  Adding required column {col} ({col_type})\n")
                    
                    try:
                        alter_query = f"ALTER TABLE {table_name} ADD COLUMN {col} {col_type}"
                        self.db_manager.db.execute_query(alter_query)
                        self.fix_log.insert(tk.END, f"  Added column {col} successfully\n")
                    except Exception as e:
                        self.fix_log.insert(tk.END, f"  Error adding column {col}: {str(e)}\n")
                
                # Add missing optional columns
                for col, col_type in missing_optional:
                    self.fix_log.insert(tk.END, f"  Adding optional column {col} ({col_type})\n")
                    
                    try:
                        alter_query = f"ALTER TABLE {table_name} ADD COLUMN {col} {col_type}"
                        self.db_manager.db.execute_query(alter_query)
                        self.fix_log.insert(tk.END, f"  Added column {col} successfully\n")
                    except Exception as e:
                        self.fix_log.insert(tk.END, f"  Error adding column {col}: {str(e)}\n")
                
                # Summary for this table
                if not missing_required and not missing_optional:
                    self.fix_log.insert(tk.END, f"  No missing columns in {table_name}\n")
                else:
                    total_added = len(missing_required) + len(missing_optional)
                    self.fix_log.insert(tk.END, f"  Added {total_added} columns to {table_name}\n")
            
            self.fix_log.insert(tk.END, "Missing column fix complete.\n")
        except Exception as e:
            self.fix_log.insert(tk.END, f"Error during missing column fix: {str(e)}\n")
    
    def check_data_integrity(self):
        """Check data integrity in the database"""
        try:
            self.diag_log.delete(1.0, tk.END)
            self.diag_log.insert(tk.END, "Running data integrity checks...\n\n")
            
            # Check table schema first
            self.diag_log.insert(tk.END, "Checking database schema structure:\n")
            schema_query = """
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'invoices'
            ORDER BY ordinal_position
            """
            
            schema_result = self.db_manager.db.execute_query(schema_query)
            if not schema_result.get('error') and schema_result['rows']:
                self.diag_log.insert(tk.END, "Columns in invoices table:\n")
                for col in schema_result['rows']:
                    self.diag_log.insert(tk.END, f"- {col[0]} ({col[1]})\n")
                
                # Check for vendor_name column specifically
                vendor_col_found = False
                for col in schema_result['rows']:
                    if col[0].lower() == 'vendor_name':
                        vendor_col_found = True
                        self.diag_log.insert(tk.END, f"\nVendor name column found as '{col[0]}' with type {col[1]}\n")
                        break
                
                if not vendor_col_found:
                    self.diag_log.insert(tk.END, "\nWARNING: vendor_name column not found in schema!\n")
                    
                    # Check if vendor column exists instead
                    for col in schema_result['rows']:
                        if col[0].lower() == 'vendor':
                            self.diag_log.insert(tk.END, f"Found 'vendor' column instead with type {col[1]}\n")
                            self.diag_log.insert(tk.END, "This may cause display issues in the dashboard.\n")
                            break
            else:
                self.diag_log.insert(tk.END, f"Error checking schema: {schema_result.get('error', 'Unknown error')}\n")
            
            # Check for NULL values in important columns
            self.diag_log.insert(tk.END, "\nChecking for NULL values in important columns:\n")
            
            null_check_queries = [
                "SELECT COUNT(*) FROM invoices WHERE invoice_number IS NULL",
                "SELECT COUNT(*) FROM invoices WHERE vendor_name IS NULL",
                "SELECT COUNT(*) FROM invoices WHERE amount IS NULL",
                "SELECT COUNT(*) FROM invoices WHERE payment_status IS NULL"
            ]
            
            for query in null_check_queries:
                result = self.db_manager.db.execute_query(query)
                if not result.get('error') and result['rows']:
                    count = result['rows'][0][0]
                    column = query.split("WHERE ")[1].split(" IS NULL")[0]
                    self.diag_log.insert(tk.END, f"- {column}: {count} NULL values\n")
                elif result.get('error'):
                    # Check if the error is due to a missing column
                    error_msg = str(result.get('error', ''))
                    if "column" in error_msg and "does not exist" in error_msg:
                        column = query.split("WHERE ")[1].split(" IS NULL")[0]
                        self.diag_log.insert(tk.END, f"- ERROR: Column {column} does not exist\n")
            
            # Check for a sample of data
            self.diag_log.insert(tk.END, "\nSample data (first 3 rows):\n")
            sample_query = """
            SELECT invoice_number, vendor_name, amount, payment_status, fund_paid_by
            FROM invoices
            LIMIT 3
            """
            
            sample_result = self.db_manager.db.execute_query(sample_query)
            if not sample_result.get('error') and sample_result['rows']:
                for i, row in enumerate(sample_result['rows']):
                    self.diag_log.insert(tk.END, f"Row {i+1}: {row}\n")
            elif sample_result.get('error'):
                error_msg = str(sample_result.get('error', ''))
                self.diag_log.insert(tk.END, f"Error fetching sample: {error_msg}\n")
                
                # Try alternative query without vendor_name
                alt_query = """
                SELECT invoice_number, amount, payment_status, fund_paid_by
                FROM invoices
                LIMIT 3
                """
                
                alt_result = self.db_manager.db.execute_query(alt_query)
                if not alt_result.get('error') and alt_result['rows']:
                    self.diag_log.insert(tk.END, "Alternative query without vendor_name succeeded:\n")
                    for i, row in enumerate(alt_result['rows']):
                        self.diag_log.insert(tk.END, f"Row {i+1}: {row}\n")
            
            # Check for future dates
            self.diag_log.insert(tk.END, "\nChecking for future invoice dates:\n")
            
            future_query = """
            SELECT COUNT(*) FROM invoices 
            WHERE invoice_date::DATE > CURRENT_DATE
            """
            
            result = self.db_manager.db.execute_query(future_query)
            if not result.get('error') and result['rows']:
                count = result['rows'][0][0]
                self.diag_log.insert(tk.END, f"- Future invoice dates: {count} records\n")
            
            # Check for inconsistent status
            self.diag_log.insert(tk.END, "\nChecking for inconsistent payment status:\n")
            
            status_query = """
            SELECT DISTINCT payment_status FROM invoices
            """
            
            result = self.db_manager.db.execute_query(status_query)
            if not result.get('error') and result['rows']:
                statuses = [row[0] for row in result['rows']]
                self.diag_log.insert(tk.END, f"- Unique status values: {', '.join(statuses)}\n")
            
            self.diag_log.insert(tk.END, "\nData integrity check complete.\n")
        except Exception as e:
            self.diag_log.insert(tk.END, f"Error during data integrity check: {str(e)}\n")
    
    def test_query_performance(self):
        """Test query performance"""
        try:
            import time
            
            self.diag_log.delete(1.0, tk.END)
            self.diag_log.insert(tk.END, "Running query performance tests...\n\n")
            
            test_queries = [
                ("Simple SELECT", "SELECT COUNT(*) FROM invoices"),
                ("Filtered SELECT", "SELECT COUNT(*) FROM invoices WHERE payment_status = 'Paid'"),
                ("Join Query", "SELECT i.invoice_number, v.name FROM invoices i JOIN vendors v ON i.vendor_name = v.name LIMIT 10"),
                ("Group By Query", "SELECT payment_status, COUNT(*) FROM invoices GROUP BY payment_status")
            ]
            
            for name, query in test_queries:
                self.diag_log.insert(tk.END, f"Testing: {name}\n")
                self.diag_log.insert(tk.END, f"Query: {query}\n")
                
                start_time = time.time()
                result = self.db_manager.db.execute_query(query)
                end_time = time.time()
                
                execution_time = end_time - start_time
                
                if result.get('error'):
                    self.diag_log.insert(tk.END, f"Error: {result['error']}\n")
                else:
                    self.diag_log.insert(tk.END, f"Execution time: {execution_time:.4f} seconds\n")
                    if result.get('rows'):
                        self.diag_log.insert(tk.END, f"Result rows: {len(result['rows'])}\n")
                
                self.diag_log.insert(tk.END, "\n")
            
            self.diag_log.insert(tk.END, "Performance testing complete.\n")
        except Exception as e:
            self.diag_log.insert(tk.END, f"Error during performance testing: {str(e)}\n")

    def save_invoice_changes(self, invoice_id, approver, status, details_window):
        """Save changes to invoice approver and status"""
        try:
            # Validate the invoice_id
            if not invoice_id:
                messagebox.showerror("Error", "Cannot update invoice: missing invoice ID")
                return
                
            # Format and validate the approver value
            approver = approver.strip() if approver else None
            
            # Update the database
            update_query = """
            UPDATE invoices
            SET approver = %s, payment_status = %s
            WHERE invoice_id = %s
            """
            
            result = self.db_manager.db.execute_query(update_query, [approver, status, invoice_id])
            
            if 'error' in result and result['error']:
                messagebox.showerror("Update Error", f"Failed to update invoice: {result['error']}")
                return
                
            # Show success message and close window
            messagebox.showinfo("Success", "Invoice updated successfully")
            details_window.destroy()
            
            # Refresh the view to show updated data
            self.apply_filters()
            
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while updating: {str(e)}")
            logger.error(f"Error saving invoice changes: {str(e)}")
    
    def fix_vendor_column_issue(self):
        """Fix vendor/vendor_name column inconsistency issues"""
        try:
            self.fix_log.delete(1.0, tk.END)
            self.fix_log.insert(tk.END, "Starting vendor column fix...\n")
            
            # Check if invoices table exists
            table_check_query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'invoices'
            )
            """
            table_result = self.db_manager.db.execute_query(table_check_query)
            
            if not table_result.get('error') and table_result['rows'] and table_result['rows'][0][0]:
                self.fix_log.insert(tk.END, "Invoices table found, checking columns...\n")
                
                # Check for vendor and vendor_name columns
                columns_query = """
                SELECT column_name, data_type, column_default, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'invoices' 
                AND column_name IN ('vendor', 'vendor_name')
                """
                
                columns_result = self.db_manager.db.execute_query(columns_query)
                
                if not columns_result.get('error') and columns_result['rows']:
                    # Create lookup dictionaries for the columns
                    columns = {}
                    for col in columns_result['rows']:
                        col_name = col[0].lower()
                        columns[col_name] = {
                            'data_type': col[1],
                            'default': col[2],
                            'nullable': col[3] == 'YES'
                        }
                    
                    has_vendor = 'vendor' in columns
                    has_vendor_name = 'vendor_name' in columns
                    
                    self.fix_log.insert(tk.END, f"Found vendor column: {has_vendor}\n")
                    self.fix_log.insert(tk.END, f"Found vendor_name column: {has_vendor_name}\n")
                    
                    # Fix scenario 1: Only vendor exists, rename to vendor_name
                    if has_vendor and not has_vendor_name:
                        self.fix_log.insert(tk.END, "Only vendor column exists. Renaming to vendor_name...\n")
                        
                        rename_query = """
                        ALTER TABLE invoices
                        RENAME COLUMN vendor TO vendor_name
                        """
                        
                        result = self.db_manager.db.execute_query(rename_query)
                        
                        if not result.get('error'):
                            self.fix_log.insert(tk.END, "Successfully renamed vendor column to vendor_name\n")
                        else:
                            self.fix_log.insert(tk.END, f"Error renaming column: {result.get('error')}\n")
                    
                    # Fix scenario 2: Both columns exist, copy data to vendor_name and drop vendor
                    elif has_vendor and has_vendor_name:
                        self.fix_log.insert(tk.END, "Both vendor and vendor_name columns exist\n")
                        
                        # Check if vendor_name has NULL values that could be filled from vendor
                        check_query = """
                        SELECT COUNT(*) FROM invoices 
                        WHERE vendor_name IS NULL AND vendor IS NOT NULL
                        """
                        
                        check_result = self.db_manager.db.execute_query(check_query)
                        
                        if not check_result.get('error') and check_result['rows']:
                            null_count = check_result['rows'][0][0]
                            
                            if null_count > 0:
                                self.fix_log.insert(tk.END, f"Found {null_count} rows where vendor_name is NULL but vendor has values\n")
                                self.fix_log.insert(tk.END, "Copying data from vendor to vendor_name where needed...\n")
                                
                                # Copy data from vendor to vendor_name where vendor_name is NULL
                                update_query = """
                                UPDATE invoices
                                SET vendor_name = vendor
                                WHERE vendor_name IS NULL AND vendor IS NOT NULL
                                """
                                
                                update_result = self.db_manager.db.execute_query(update_query)
                                
                                if not update_result.get('error'):
                                    self.fix_log.insert(tk.END, f"Successfully copied data for {null_count} rows\n")
                                else:
                                    self.fix_log.insert(tk.END, f"Error copying data: {update_result.get('error')}\n")
                            else:
                                self.fix_log.insert(tk.END, "No NULL vendor_name values that need filling from vendor\n")
                        
                        # Drop the vendor column since vendor_name is the column our code uses
                        self.fix_log.insert(tk.END, "Dropping redundant vendor column...\n")
                        
                        drop_query = """
                        ALTER TABLE invoices
                        DROP COLUMN vendor
                        """
                        
                        drop_result = self.db_manager.db.execute_query(drop_query)
                        
                        if not drop_result.get('error'):
                            self.fix_log.insert(tk.END, "Successfully dropped vendor column\n")
                        else:
                            self.fix_log.insert(tk.END, f"Error dropping column: {drop_result.get('error')}\n")
                    
                    # Fix scenario 3: Neither column exists, add vendor_name
                    elif not has_vendor and not has_vendor_name:
                        self.fix_log.insert(tk.END, "Neither vendor nor vendor_name columns exist\n")
                        self.fix_log.insert(tk.END, "Adding vendor_name column...\n")
                        
                        add_query = """
                        ALTER TABLE invoices
                        ADD COLUMN vendor_name VARCHAR(100)
                        """
                        
                        add_result = self.db_manager.db.execute_query(add_query)
                        
                        if not add_result.get('error'):
                            self.fix_log.insert(tk.END, "Successfully added vendor_name column\n")
                        else:
                            self.fix_log.insert(tk.END, f"Error adding column: {add_result.get('error')}\n")
                    
                    # Scenario 4: Only vendor_name exists, which is correct
                    else:
                        self.fix_log.insert(tk.END, "vendor_name column already exists - no fix needed\n")
                        
                    # Validate foreign key relationship with vendors table
                    self.fix_log.insert(tk.END, "\nChecking relationship with vendors table...\n")
                    
                    vendors_check_query = """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'vendors'
                    )
                    """
                    vendors_result = self.db_manager.db.execute_query(vendors_check_query)
                    
                    if not vendors_result.get('error') and vendors_result['rows'] and vendors_result['rows'][0][0]:
                        self.fix_log.insert(tk.END, "Vendors table exists\n")
                        
                        # Check if vendors table has name column (used in JOIN with vendor_name)
                        name_check_query = """
                        SELECT EXISTS (
                            SELECT FROM information_schema.columns
                            WHERE table_name = 'vendors' AND column_name = 'name'
                        )
                        """
                        name_result = self.db_manager.db.execute_query(name_check_query)
                        
                        if not name_result.get('error') and name_result['rows'] and name_result['rows'][0][0]:
                            self.fix_log.insert(tk.END, "Vendors table has 'name' column - correct for joins\n")
                        else:
                            self.fix_log.insert(tk.END, "WARNING: Vendors table does not have 'name' column\n")
                            self.fix_log.insert(tk.END, "This may cause join issues with the vendor_name column\n")
                    else:
                        self.fix_log.insert(tk.END, "Vendors table does not exist\n")
                    
                else:
                    self.fix_log.insert(tk.END, f"Error checking columns: {columns_result.get('error', 'No columns found')}\n")
            else:
                self.fix_log.insert(tk.END, "Invoices table does not exist or could not be checked\n")
            
            # Verify the dashboard works with the current column structure
            verify_query = """
            SELECT
                invoice_number,
                vendor_name,
                amount,
                payment_status
            FROM invoices
            LIMIT 5
            """
            
            verify_result = self.db_manager.db.execute_query(verify_query)
            
            if not verify_result.get('error'):
                self.fix_log.insert(tk.END, "\nVerification query succeeded using vendor_name column\n")
                self.fix_log.insert(tk.END, f"Found {len(verify_result.get('rows', []))} sample rows\n")
                self.fix_log.insert(tk.END, "Dashboard should now work correctly with vendor_name column\n")
            else:
                self.fix_log.insert(tk.END, f"\nVerification query failed: {verify_result.get('error')}\n")
                self.fix_log.insert(tk.END, "There may still be issues with the vendor_name column\n")
            
            self.fix_log.insert(tk.END, "\nVendor column fix complete.\n")
            
        except Exception as e:
            self.fix_log.insert(tk.END, f"Error during vendor column fix: {str(e)}\n")
