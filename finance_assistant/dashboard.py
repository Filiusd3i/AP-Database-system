#!/usr/bin/env python3
"""
Dashboard Visualization Module

Provides visualizations for invoice data from PostgreSQL.
This is a simplified version that replaces the previous complex visualization system.
"""

import logging
import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
import threading
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger(__name__)

# List of tables with spaces in their names
TABLES_WITH_SPACES = ["Deal Allocations", "RAUM Allocations"]

class InvoiceDashboard:
    """Invoice dashboard visualization with real-time updates"""
    
    def __init__(self, parent, db_manager):
        """Initialize the invoice dashboard
        
        Args:
            parent: The parent window
            db_manager: The database manager
        """
        self.parent = parent
        self.db_manager = db_manager
        
        # Initialize UI elements as None so we can check if they exist
        self.pie_ax = None
        self.bar_ax = None
        self.invoice_tree = None
        
        # Create the UI
        self.create_dashboard_ui()
        
        # Load initial data
        self.update_dashboard()
        
        logger.info("Invoice dashboard initialized")
    
    def create_dashboard_ui(self):
        """Create the dashboard UI elements"""
        # Main frame
        self.frame = ttk.Frame(self.parent)
        self.frame.pack(fill=tk.BOTH, expand=True)
        
        # Create summary cards at the top
        self.create_summary_cards()
        
        # Create filter section
        self.create_filter_section()
        
        # Create chart section - make sure this initializes self.pie_ax and self.bar_ax
        self.create_charts_section()
        
        # Create invoice table section - make sure this initializes self.invoice_tree
        self.create_invoice_table()
    
    def create_charts_section(self):
        """Create the charts section"""
        try:
            # Import matplotlib only when needed
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            
            # Create a frame for charts
            charts_frame = ttk.LabelFrame(self.frame, text="Charts")
            charts_frame.pack(fill=tk.X, padx=10, pady=5)
            
            # Create a container for the charts
            charts_container = ttk.Frame(charts_frame)
            charts_container.pack(fill=tk.X, padx=5, pady=5)
            
            # Create pie chart
            fig1 = Figure(figsize=(4, 3), dpi=100)
            self.pie_ax = fig1.add_subplot(111)  # This initializes self.pie_ax
            
            canvas1 = FigureCanvasTkAgg(fig1, charts_container)
            canvas1.draw()
            canvas1.get_tk_widget().pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            # Create bar chart
            fig2 = Figure(figsize=(4, 3), dpi=100)
            self.bar_ax = fig2.add_subplot(111)  # This initializes self.bar_ax
            
            canvas2 = FigureCanvasTkAgg(fig2, charts_container)
            canvas2.draw()
            canvas2.get_tk_widget().pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
        except ImportError:
            # If matplotlib is not available, create a label instead
            logger.error("Matplotlib not available, charts disabled")
            charts_frame = ttk.LabelFrame(self.frame, text="Charts")
            charts_frame.pack(fill=tk.X, padx=10, pady=5)
            
            label = ttk.Label(charts_frame, text="Charts disabled (matplotlib not available)")
            label.pack(pady=10)
            
            # Initialize as None but with a flag
            self.pie_ax = None
            self.bar_ax = None
            self.charts_disabled = True
    
    def create_invoice_table(self):
        """Create the invoice table section"""
        # Create a frame for the table
        table_frame = ttk.LabelFrame(self.frame, text="Invoices")
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create columns for the table
        columns = ("id", "invoice_number", "date", "vendor", "amount", 
                  "status", "due_date", "fund")
        
        # Create the treeview
        self.invoice_tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        
        # Define column headings
        self.invoice_tree.heading("id", text="ID")
        self.invoice_tree.heading("invoice_number", text="Invoice #")
        self.invoice_tree.heading("date", text="Date")
        self.invoice_tree.heading("vendor", text="Vendor")
        self.invoice_tree.heading("amount", text="Amount")
        self.invoice_tree.heading("status", text="Status")
        self.invoice_tree.heading("due_date", text="Due Date")
        self.invoice_tree.heading("fund", text="Fund")
        
        # Set column widths
        self.invoice_tree.column("id", width=50)
        self.invoice_tree.column("invoice_number", width=100)
        self.invoice_tree.column("date", width=100)
        self.invoice_tree.column("vendor", width=150)
        self.invoice_tree.column("amount", width=100)
        self.invoice_tree.column("status", width=100)
        self.invoice_tree.column("due_date", width=100)
        self.invoice_tree.column("fund", width=100)
        
        # Add scrollbars
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.invoice_tree.yview)
        self.invoice_tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.invoice_tree.xview)
        self.invoice_tree.configure(xscrollcommand=hsb.set)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Pack the treeview
        self.invoice_tree.pack(fill=tk.BOTH, expand=True)
    
    def update_charts(self):
        """Update the charts with current data"""
        # Skip if charts are disabled or not initialized
        if not hasattr(self, 'pie_ax') or self.pie_ax is None:
            logger.error("Charts not initialized, skipping update")
            return
            
        if hasattr(self, 'charts_disabled') and self.charts_disabled:
            return
            
        try:
            # Clear the charts
            self.pie_ax.clear()
            self.bar_ax.clear()
            
            # Get data for pie chart (status distribution)
            result = self.db_manager.get_invoice_counts()
            
            if result and isinstance(result, dict):
                labels = list(result.keys())
                values = list(result.values())
                
                # Create pie chart
                self.pie_ax.pie(values, labels=labels, autopct='%1.1f%%')
                self.pie_ax.set_title('Invoice Status')
                
                # Redraw
                self.pie_ax.figure.canvas.draw()
            
            # Get data for bar chart (monthly totals)
            # This would normally come from a database query
            # For now using placeholder data
            months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
            values = [5000, 7000, 3000, 8000, 6000, 9000]
            
            # Create bar chart
            self.bar_ax.bar(months, values)
            self.bar_ax.set_title('Monthly Totals')
            
            # Redraw
            self.bar_ax.figure.canvas.draw()
            
        except Exception as e:
            logger.error(f"Error updating charts: {str(e)}")
    
    def update_invoice_table(self):
        """Update the invoice table with data"""
        # Check if invoice_tree is initialized
        if not hasattr(self, 'invoice_tree') or self.invoice_tree is None:
            logger.error("Invoice table not initialized, skipping update")
            return
            
        try:
            # Clear existing items
            for item in self.invoice_tree.get_children():
                self.invoice_tree.delete(item)
            
            # Get invoice data
            result = self.db_manager.get_recent_invoices(50)  # Get up to 50 recent invoices
            
            if result and 'rows' in result and result['rows']:
                # Format and insert rows
                for i, row in enumerate(result['rows']):
                    # Format values appropriately
                    formatted_row = []
                    for val in row:
                        if isinstance(val, (datetime.datetime, datetime.date)):
                            formatted_row.append(val.strftime('%Y-%m-%d'))
                        elif isinstance(val, (int, float)) and len(formatted_row) == 4:  # Assuming 5th column is amount
                            formatted_row.append(f"${val:,.2f}")
                        else:
                            formatted_row.append(str(val) if val is not None else "")
                    
                    # Insert into treeview
                    self.invoice_tree.insert("", tk.END, values=formatted_row)
                
                logger.info(f"Updated invoice table with {len(result['rows'])} invoices")
            else:
                logger.info("No invoice data to display")
                
        except Exception as e:
            logger.error(f"Error updating invoice table: {str(e)}")
    
    def update_dashboard(self):
        """Update all dashboard elements"""
        try:
            # Update summary cards
            self.update_summary_cards()
            
            # Update charts
            self.update_charts()
            
            # Update invoice table
            self.update_invoice_table()
            
            logger.info(f"Dashboard updated with {len(self.invoice_tree.get_children() if self.invoice_tree else [])} invoices")
            
        except Exception as e:
            logger.error(f"Error updating dashboard: {str(e)}")
    
    def _validate_invoices_table(self):
        """Validate that the invoices table exists and has the required schema
        
        Returns:
            bool: True if the table is valid, False otherwise
        """
        try:
            # Ensure the invoices table has the required columns
            if hasattr(self.db_manager, "schema_validator"):
                # Run validation with diagnostics in case of failure
                valid = self.db_manager.ensure_valid_schema('invoices')
                
                if not valid:
                    # Get detailed diagnostics
                    diagnosis = self.db_manager.schema_validator.diagnose_table_schema('invoices')
                    
                    # Show a more informative error message
                    if 'case_mismatches' in diagnosis and diagnosis['case_mismatches']:
                        mismatch_info = "\n".join([
                            f"- Expected '{m['expected']}', found '{m['actual']}'" 
                            for m in diagnosis['case_mismatches']
                        ])
                        
                        messagebox.showerror(
                            "Schema Error - Column Case Mismatches",
                            f"The invoices table has column case mismatches:\n\n{mismatch_info}\n\n"
                            "This can cause errors when querying the database. "
                            "Would you like the application to attempt to fix these issues?"
                        )
                    else:
                        # Get list of missing columns if available
                        missing_columns = []
                        if 'missing_columns' in diagnosis:
                            missing_columns = [col['name'] for col in diagnosis.get('missing_columns', [])]
                            
                        missing_info = ", ".join(missing_columns) if missing_columns else "unknown columns"
                        
                        messagebox.showerror(
                            "Schema Error",
                            f"The invoices table is missing required columns: {missing_info}\n\n"
                            "Please fix the schema or import data with the correct format."
                        )
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to validate invoices table: {str(e)}")
            messagebox.showerror(
                "Schema Validation Error",
                f"Failed to validate invoices table: {str(e)}\n\n"
                "Please ensure your database is properly set up."
            )
            return False
    
    def _create_layout(self):
        """Create the dashboard layout"""
        # Create frame for summary cards
        self.summary_frame = ttk.Frame(self.frame)
        self.summary_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Create frame for charts
        self.charts_frame = ttk.Frame(self.frame)
        self.charts_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create frame for invoice table
        self.table_frame = ttk.Frame(self.frame)
        self.table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create a frame for filters
        self.filter_frame = ttk.LabelFrame(self.frame, text="Filters")
        self.filter_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Date range filter
        ttk.Label(self.filter_frame, text="Date Range:").grid(row=0, column=0, padx=5, pady=5)
        self.date_range = ttk.Combobox(self.filter_frame, values=["All", "Last 30 Days", "Last 90 Days", "This Year"])
        self.date_range.grid(row=0, column=1, padx=5, pady=5)
        self.date_range.current(0)
        
        # Status filter
        ttk.Label(self.filter_frame, text="Status:").grid(row=0, column=2, padx=5, pady=5)
        self.status_filter = ttk.Combobox(self.filter_frame, values=["All", "Paid", "Unpaid", "Overdue"])
        self.status_filter.grid(row=0, column=3, padx=5, pady=5)
        self.status_filter.current(0)
        
        # Fund filter
        ttk.Label(self.filter_frame, text="Fund:").grid(row=0, column=4, padx=5, pady=5)
        self.fund_filter = ttk.Combobox(self.filter_frame, values=["All"])
        self.fund_filter.grid(row=0, column=5, padx=5, pady=5)
        self.fund_filter.current(0)
        
        # Apply filter button
        self.apply_button = ttk.Button(self.filter_frame, text="Apply Filters", command=self.apply_filters)
        self.apply_button.grid(row=0, column=6, padx=5, pady=5)
        
        # Populate fund filter values
        self._update_fund_filter()
    
    def _update_fund_filter(self):
        """Update the fund filter with values from the database"""
        try:
            # Get fund values from the database
            query = "SELECT DISTINCT fund_paid_by FROM invoices WHERE fund_paid_by IS NOT NULL"
            result = self.db_manager.execute_query(query)
            
            if 'error' not in result and result['rows']:
                # Extract unique fund values
                funds = ["All"] + [row[0] for row in result['rows'] if row[0]]
                
                # Update the combobox values
                self.fund_filter['values'] = funds
                
                logger.info(f"Updated fund filter with {len(funds)-1} values")
        except Exception as e:
            logger.error(f"Error updating fund filter: {str(e)}")
    
    def _create_summary_cards(self):
        """Create summary cards for key metrics"""
        # Create summary card styles
        style = ttk.Style()
        style.configure("Card.TFrame", background="#f0f0f0", relief="raised", borderwidth=1)
        style.configure("CardTitle.TLabel", background="#f0f0f0", font=("Arial", 10, "bold"))
        style.configure("CardValue.TLabel", background="#f0f0f0", font=("Arial", 16, "bold"))
        
        # Create card frames
        self.paid_card = ttk.Frame(self.summary_frame, style="Card.TFrame", width=200, height=100)
        self.paid_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.paid_card.pack_propagate(False)
        
        self.unpaid_card = ttk.Frame(self.summary_frame, style="Card.TFrame", width=200, height=100)
        self.unpaid_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.unpaid_card.pack_propagate(False)
        
        self.total_card = ttk.Frame(self.summary_frame, style="Card.TFrame", width=200, height=100)
        self.total_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.total_card.pack_propagate(False)
        
        self.overdue_card = ttk.Frame(self.summary_frame, style="Card.TFrame", width=200, height=100)
        self.overdue_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.overdue_card.pack_propagate(False)
        
        # Add card content
        ttk.Label(self.paid_card, text="Paid Invoices", style="CardTitle.TLabel").pack(pady=(10, 0))
        self.paid_value = ttk.Label(self.paid_card, text="0", style="CardValue.TLabel")
        self.paid_value.pack(pady=10)
        
        ttk.Label(self.unpaid_card, text="Pending Invoices", style="CardTitle.TLabel").pack(pady=(10, 0))
        self.unpaid_value = ttk.Label(self.unpaid_card, text="0", style="CardValue.TLabel")
        self.unpaid_value.pack(pady=10)
        
        ttk.Label(self.total_card, text="Total Amount", style="CardTitle.TLabel").pack(pady=(10, 0))
        self.total_value = ttk.Label(self.total_card, text="$0.00", style="CardValue.TLabel")
        self.total_value.pack(pady=10)
        
        ttk.Label(self.overdue_card, text="Overdue Invoices", style="CardTitle.TLabel").pack(pady=(10, 0))
        self.overdue_value = ttk.Label(self.overdue_card, text="0", style="CardValue.TLabel")
        self.overdue_value.pack(pady=10)
        
        # Update summary cards
        self._update_summary_cards()
    
    def _update_summary_cards(self):
        """Update the summary cards with data from the database"""
        try:
            # Get invoice summary data
            summary = self.db_manager.get_invoice_summary()
            
            # Safely update values with proper type checking
            try:
                paid_count = int(summary.get('paid_count', 0))
                if hasattr(self.paid_value, 'config'):
                    self.paid_value.config(text=str(paid_count))
                elif isinstance(self.paid_value, int):
                    self.paid_value = paid_count
            except (TypeError, AttributeError) as e:
                logger.error(f"Error updating paid value: {str(e)}")
                if hasattr(self.paid_value, 'config'):
                    self.paid_value.config(text="0")
            
            try:
                unpaid_count = int(summary.get('unpaid_count', 0))
                if hasattr(self.unpaid_value, 'config'):
                    self.unpaid_value.config(text=str(unpaid_count))
                elif isinstance(self.unpaid_value, int):
                    self.unpaid_value = unpaid_count
            except (TypeError, AttributeError) as e:
                logger.error(f"Error updating unpaid value: {str(e)}")
                if hasattr(self.unpaid_value, 'config'):
                    self.unpaid_value.config(text="0")
            
            try:
                overdue_count = int(summary.get('overdue_count', 0))
                if hasattr(self.overdue_value, 'config'):
                    self.overdue_value.config(text=str(overdue_count))
                elif isinstance(self.overdue_value, int):
                    self.overdue_value = overdue_count
            except (TypeError, AttributeError) as e:
                logger.error(f"Error updating overdue value: {str(e)}")
                if hasattr(self.overdue_value, 'config'):
                    self.overdue_value.config(text="0")
            
            # Format total amount as currency
            try:
                total = float(summary.get('total_amount', 0))
                total_str = f"${total:,.2f}"
                if hasattr(self.total_value, 'config'):
                    self.total_value.config(text=total_str)
                elif isinstance(self.total_value, (int, float)):
                    self.total_value = total
            except (TypeError, AttributeError) as e:
                logger.error(f"Error updating total value: {str(e)}")
                if hasattr(self.total_value, 'config'):
                    self.total_value.config(text="$0.00")
            
            logger.info("Updated summary cards")
        except Exception as e:
            logger.error(f"Error updating summary cards: {str(e)}")
            # Set default values in case of error, with safety checks
            if hasattr(self.paid_value, 'config'):
                self.paid_value.config(text="0")
            if hasattr(self.unpaid_value, 'config'):
                self.unpaid_value.config(text="0")
            if hasattr(self.overdue_value, 'config'):
                self.overdue_value.config(text="0")
            if hasattr(self.total_value, 'config'):
                self.total_value.config(text="$0.00")
    
    def _create_charts(self):
        """Create charts for invoice visualization"""
        # Create a figure for the charts
        self.figure = plt.Figure(figsize=(10, 5), dpi=100)
        
        # Create a canvas for the figure
        self.canvas = FigureCanvasTkAgg(self.figure, self.charts_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Create subplots
        self.pie_ax = self.figure.add_subplot(121)
        self.bar_ax = self.figure.add_subplot(122)
        
        # Update charts
        self._update_charts()
    
    def _update_charts(self):
        """Update the charts with data from the database"""
        try:
            # Clear the axes
            self.pie_ax.clear()
            self.bar_ax.clear()
            
            # Get status distribution for pie chart
            status_query = """
            SELECT payment_status, COUNT(*) 
            FROM invoices 
            GROUP BY payment_status
            """
            status_result = self.db_manager.execute_query(status_query)
            
            if 'error' not in status_result and status_result['rows']:
                # Create a dataframe for the status data
                status_df = pd.DataFrame(status_result['rows'], columns=['Status', 'Count'])
                
                # Create pie chart
                self.pie_ax.pie(
                    status_df['Count'], 
                    labels=status_df['Status'], 
                    autopct='%1.1f%%',
                    startangle=90
                )
                self.pie_ax.set_title('Invoice Status Distribution')
                
            # Get fund distribution for bar chart
            fund_query = """
            SELECT fund_paid_by, SUM(amount) 
            FROM invoices 
            WHERE fund_paid_by IS NOT NULL 
            GROUP BY fund_paid_by
            """
            fund_result = self.db_manager.execute_query(fund_query)
            
            if 'error' not in fund_result and fund_result['rows']:
                # Create a dataframe for the fund data
                fund_df = pd.DataFrame(fund_result['rows'], columns=['Fund', 'Amount'])
                
                # Sort by amount descending
                fund_df = fund_df.sort_values('Amount', ascending=False)
                
                # Create bar chart
                self.bar_ax.barh(fund_df['Fund'], fund_df['Amount'])
                self.bar_ax.set_title('Amount by Fund')
                self.bar_ax.set_xlabel('Amount ($)')
                
                # Format y-axis tick labels
                self.bar_ax.tick_params(axis='y', labelsize=8)
                
                # Add amount labels to bars
                for i, amount in enumerate(fund_df['Amount']):
                    self.bar_ax.text(amount + 100, i, f"${amount:,.2f}", va='center', fontsize=8)
            
            # Adjust layout
            self.figure.tight_layout()
            
            # Draw the canvas
            self.canvas.draw()
            
            logger.info("Updated charts")
        except Exception as e:
            logger.error(f"Error updating charts: {str(e)}")
    
    def _create_invoice_table(self):
        """Create the invoice table"""
        # Create a frame for the table
        table_frame = ttk.LabelFrame(self.table_frame, text="Recent Invoices")
        table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create a frame for the treeview and scrollbars
        tree_frame = ttk.Frame(table_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        hsb = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Define columns
        columns = (
            "invoice_number", "vendor", "amount", "invoice_date", 
            "due_date", "payment_status", "fund_paid_by"
        )
        
        # Create treeview
        self.invoice_tree = ttk.Treeview(
            tree_frame, 
            columns=columns,
            show="headings",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set
        )
        
        # Configure scrollbars
        vsb.config(command=self.invoice_tree.yview)
        hsb.config(command=self.invoice_tree.xview)
        
        # Configure column headings
        column_names = {
            "invoice_number": "Invoice #",
            "vendor": "Vendor",
            "amount": "Amount",
            "invoice_date": "Invoice Date",
            "due_date": "Due Date",
            "payment_status": "Status",
            "fund_paid_by": "Fund"
        }
        
        # Set column headings and widths
        for col in columns:
            self.invoice_tree.heading(col, text=column_names.get(col, col.replace("_", " ").title()))
            
            # Set column width based on content type
            if col in ["invoice_date", "due_date"]:
                width = 100
            elif col in ["amount"]:
                width = 80
            elif col in ["invoice_number", "payment_status"]:
                width = 120
            elif col in ["vendor", "fund_paid_by"]:
                width = 150
            else:
                width = 100
                
            self.invoice_tree.column(col, width=width, minwidth=50)
        
        # Pack the treeview
        self.invoice_tree.pack(fill=tk.BOTH, expand=True)
        
        # Update with initial data
        self._update_invoice_table()
    
    def _update_invoice_table(self):
        """Update the invoice table with current data"""
        try:
            # Clear the table
            for item in self.invoice_tree.get_children():
                self.invoice_tree.delete(item)
            
            # Add data from current_invoices to the table
            for invoice in self.current_invoices:
                row_values = []
                
                # Extract values for each column in the treeview
                for col in self.invoice_tree['columns']:
                    # The invoice data could be a dict or a list
                    if isinstance(invoice, dict):
                        # For dictionaries, use column name as key 
                        value = invoice.get(col, "")
                    else:
                        # For lists, try to find the column by column index in the result
                        col_idx = self.invoice_tree['columns'].index(col)
                        value = invoice[col_idx] if col_idx < len(invoice) else ""
                    
                    # Format date values
                    if isinstance(value, datetime):
                        value = value.strftime('%Y-%m-%d')
                    
                    # Format amount values
                    if col == 'amount' and isinstance(value, (int, float)):
                        value = f"${value:,.2f}"
                    
                    row_values.append(value)
                
                # Add the row to the treeview
                self.invoice_tree.insert("", tk.END, values=row_values)
            
            logger.info(f"Updated invoice table with {len(self.current_invoices)} rows")
        except Exception as e:
            logger.error(f"Error updating invoice table: {str(e)}")
    
    def _schedule_updates(self):
        """Schedule regular updates for the dashboard"""
        def update_loop():
            while True:
                try:
                    # Update all dashboard elements
                    self._update_summary_cards()
                    self._update_charts()
                    self._update_invoice_table()
                    
                    # Wait for 5 seconds
                    time.sleep(5)
                except Exception as e:
                    logger.error(f"Error in update loop: {str(e)}")
                    time.sleep(5)
        
        # Start update thread
        update_thread = threading.Thread(target=update_loop, daemon=True)
        update_thread.start()
        
        logger.info("Dashboard updates scheduled")
    
    def apply_filters(self):
        """Apply the selected filters to the dashboard"""
        try:
            # Get filter values
            date_range = self.date_range.get()
            status = self.status_filter.get()
            fund = self.fund_filter.get()
            
            # Build filters dictionary
            filters = {}
            
            # Add date range filter
            if date_range != "All":
                end_date = datetime.now()
                if date_range == "Last 30 Days":
                    start_date = end_date - timedelta(days=30)
                elif date_range == "Last 90 Days":
                    start_date = end_date - timedelta(days=90)
                elif date_range == "This Year":
                    start_date = datetime(end_date.year, 1, 1)
                
                filters['start_date'] = start_date.strftime('%Y-%m-%d')
                filters['end_date'] = end_date.strftime('%Y-%m-%d')
            
            # Add status filter
            if status != "All":
                if status == "Overdue":
                    # Overdue is a special case - it's unpaid invoices past their due date
                    filters['status'] = "Unpaid"
                    filters['overdue'] = True
                else:
                    filters['status'] = status
            
            # Add fund filter
            if fund != "All":
                filters['fund'] = fund
            
            # Update the dashboard with the new filters
            self._update_data(filters)
            
            logger.info(f"Applied filters: {filters}")
        except Exception as e:
            logger.error(f"Error applying filters: {str(e)}")
            messagebox.showerror("Filter Error", f"Failed to apply filters: {str(e)}")
    
    def _update_data(self, filters=None):
        """Update all dashboard components with fresh data
        
        Args:
            filters: Optional filters to apply to the data
        """
        try:
            # Get invoice data with filters
            result = self.db_manager.get_invoice_data(filters)
            
            if 'error' in result and result['error']:
                messagebox.showerror("Data Error", f"Failed to get invoice data: {result['error']}")
                return
                
            # Store the current invoices
            if 'rows' in result:
                self.current_invoices = result['rows']
            
            # Update dashboard components
            self._update_summary_cards()
            self._update_charts()
            self._update_invoice_table()
            
            logger.info(f"Dashboard updated with {len(self.current_invoices)} invoices")
        except Exception as e:
            logger.error(f"Error updating dashboard data: {str(e)}")
            messagebox.showerror("Update Error", f"Failed to update dashboard: {str(e)}")
    
    def show(self):
        """Show the dashboard"""
        self.frame.pack(fill=tk.BOTH, expand=True)

    def execute_deal_allocations_query(self):
        """Example method to safely query the Deal Allocations table"""
        try:
            # 1. Using safe_query method with explicit table names
            query = "SELECT COUNT(*) FROM Deal Allocations"
            result = self.db_manager.execute_safe_query(query)
            
            if "error" not in result or not result["error"]:
                count = result["rows"][0][0] if result["rows"] else 0
                logger.info(f"Deal Allocations count: {count}")
                return count
            else:
                logger.error(f"Error querying Deal Allocations: {result['error']}")
                return 0
        except Exception as e:
            logger.error(f"Exception in execute_deal_allocations_query: {str(e)}")
            return 0

    def _create_window(self):
        """Create the dashboard window"""
        self.window = tk.Toplevel(self.parent)
        self.window.title("Invoice Dashboard")
        self.window.geometry("1200x800")
        self.window.minsize(1000, 700)
        
        # Create main frame
        self.frame = ttk.Frame(self.window)
        self.frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10) 