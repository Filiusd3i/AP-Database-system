#!/usr/bin/env python3
"""
Dashboard Visualization Module

Provides visualizations for invoice data from PostgreSQL.
This is a simplified version that replaces the previous complex visualization system.
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
import threading
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

# Import the ultimate logger
from ultimate_logger import (
    configure_ultimate_logging, 
    log_execution_time, 
    log_context, 
    log_with_error_code,
    log_state_transition
)

# Configure component logger
logger = configure_ultimate_logging(
    app_name="finance_db_assistant",
    component_name="dashboard",
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    console_output=True,
    file_output=True,
    file_path="logs/finance_app.log"
)

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
        with log_context(logger, action="initialize_dashboard"):
        self.parent = parent
        self.db_manager = db_manager
        
        # Initialize UI elements as None so we can check if they exist
        self.pie_ax = None
        self.bar_ax = None
        self.invoice_tree = None
        
        # Create the UI
            logger.info("Creating dashboard UI")
        self.create_dashboard_ui()
        
        # Load initial data
            logger.info("Loading initial dashboard data")
        self.update_dashboard()
        
            logger.info("Invoice dashboard initialized", extra={"ui_state": "ready"})
    
    @log_execution_time(logger)
    def create_dashboard_ui(self):
        """Create the dashboard UI elements"""
        with log_context(logger, action="create_dashboard_ui"):
        # Main frame
        self.frame = ttk.Frame(self.parent)
        self.frame.pack(fill=tk.BOTH, expand=True)
        
        # Create summary cards at the top
            logger.debug("Creating summary cards")
        self.create_summary_cards()
        
        # Create filter section
            logger.debug("Creating filter section")
        self.create_filter_section()
        
        # Create chart section - make sure this initializes self.pie_ax and self.bar_ax
            logger.debug("Creating charts section")
        self.create_charts_section()
        
        # Create invoice table section - make sure this initializes self.invoice_tree
            logger.debug("Creating invoice table")
        self.create_invoice_table()
            
            logger.info("Dashboard UI created successfully")
    
    def create_filter_section(self):
        """Create the filter section in the dashboard"""
        with log_context(logger, action="create_filter_section"):
            # Create a frame for filters
            filter_frame = ttk.LabelFrame(self.frame, text="Filters")
            filter_frame.pack(fill=tk.X, padx=10, pady=5)
            
            # Create a container for the filters
            filters_container = ttk.Frame(filter_frame)
            filters_container.pack(fill=tk.X, padx=5, pady=5)
            
            # Status filter
            ttk.Label(filters_container, text="Status:").pack(side=tk.LEFT, padx=(0, 5))
            self.status_var = tk.StringVar()
            status_combo = ttk.Combobox(filters_container, textvariable=self.status_var, 
                                      values=["All", "Paid", "Unpaid", "Overdue"], width=10)
            status_combo.pack(side=tk.LEFT, padx=(0, 15))
            status_combo.current(0)  # Default to "All"
            
            # Fund filter
            ttk.Label(filters_container, text="Fund:").pack(side=tk.LEFT, padx=(0, 5))
            self.fund_var = tk.StringVar()
            self.fund_combo = ttk.Combobox(filters_container, textvariable=self.fund_var, width=15)
            self.fund_combo.pack(side=tk.LEFT, padx=(0, 15))
            
            # Date range filters
            ttk.Label(filters_container, text="From:").pack(side=tk.LEFT, padx=(0, 5))
            self.start_date_var = tk.StringVar()
            start_date = ttk.Entry(filters_container, textvariable=self.start_date_var, width=10)
            start_date.pack(side=tk.LEFT, padx=(0, 5))
            
            ttk.Label(filters_container, text="To:").pack(side=tk.LEFT, padx=(0, 5))
            self.end_date_var = tk.StringVar()
            end_date = ttk.Entry(filters_container, textvariable=self.end_date_var, width=10)
            end_date.pack(side=tk.LEFT, padx=(0, 15))
            
            # Apply filter button
            apply_button = ttk.Button(filters_container, text="Apply Filters", command=self.apply_filters)
            apply_button.pack(side=tk.LEFT)
            
            # Update the fund filter combobox
            self._update_fund_filter()
            
            logger.debug("Filter section created")
    
    @log_execution_time(logger)
    def create_charts_section(self):
        """Create the charts section"""
        with log_context(logger, action="create_charts_section"):
        try:
            # Import matplotlib only when needed
                logger.debug("Initializing matplotlib figures")
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
            
                logger.info("Charts initialized successfully")
                
            except ImportError as e:
            # If matplotlib is not available, create a label instead
                log_with_error_code(
                    logger, 
                    "UI_CHARTS_001", 
                    "Matplotlib not available, charts disabled",
                    error_details=str(e)
                )
            charts_frame = ttk.LabelFrame(self.frame, text="Charts")
            charts_frame.pack(fill=tk.X, padx=10, pady=5)
            
            label = ttk.Label(charts_frame, text="Charts disabled (matplotlib not available)")
            label.pack(pady=10)
            
            # Initialize as None but with a flag
            self.pie_ax = None
            self.bar_ax = None
            self.charts_disabled = True
    
            except Exception as e:
                # Handle other exceptions
                logger.exception_with_context(f"Error creating charts: {str(e)}")
                
                charts_frame = ttk.LabelFrame(self.frame, text="Charts")
                charts_frame.pack(fill=tk.X, padx=10, pady=5)
                
                label = ttk.Label(charts_frame, text=f"Charts disabled: {str(e)}")
                label.pack(pady=10)
                
                self.pie_ax = None
                self.bar_ax = None
                self.charts_disabled = True
    
    @log_execution_time(logger)
    def create_invoice_table(self):
        """Create the invoice table section"""
        with log_context(logger, action="create_invoice_table"):
        # Create a frame for the table
        table_frame = ttk.LabelFrame(self.frame, text="Invoices")
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create columns for the table
        columns = ("id", "invoice_number", "date", "vendor", "amount", 
                  "status", "due_date", "fund")
        
        # Create the treeview
            logger.debug("Creating invoice treeview with columns")
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
            logger.debug("Adding scrollbars to invoice table")
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.invoice_tree.yview)
        self.invoice_tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.invoice_tree.xview)
        self.invoice_tree.configure(xscrollcommand=hsb.set)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Pack the treeview
        self.invoice_tree.pack(fill=tk.BOTH, expand=True)
    
            # Add right-click menu
            self._add_context_menu()
            
            logger.info("Invoice table created successfully")
    
    def _add_context_menu(self):
        """Add a context menu to the invoice table"""
        with log_context(logger, action="add_context_menu"):
            # Create a popup menu
            self.popup_menu = tk.Menu(self.invoice_tree, tearoff=0)
            self.popup_menu.add_command(label="View Invoice Details", command=self._view_invoice_details)
            self.popup_menu.add_command(label="Mark as Paid", command=self._mark_as_paid)
            self.popup_menu.add_separator()
            self.popup_menu.add_command(label="Delete", command=self._delete_invoice)
            
            # Bind right-click event
            self.invoice_tree.bind("<Button-3>", self._show_popup_menu)
            
            logger.debug("Context menu added to invoice table")
    
    def _show_popup_menu(self, event):
        """Show the popup menu on right-click"""
        with log_context(logger, action="show_context_menu"):
            # Select the item under the mouse
            item = self.invoice_tree.identify_row(event.y)
            if item:
                logger.debug(f"Showing context menu for item {item}")
                self.invoice_tree.selection_set(item)
                self.popup_menu.post(event.x_root, event.y_root)
    
    def _view_invoice_details(self):
        """View details of the selected invoice"""
        with log_context(logger, action="view_invoice_details"):
            selected = self.invoice_tree.selection()
            if not selected:
                logger.warning("No invoice selected for viewing")
                return
                
            # Get the invoice ID from the selected item
            invoice_id = self.invoice_tree.item(selected[0], "values")[0]
            logger.info(f"Viewing details for invoice ID: {invoice_id}")
            
            # TODO: Implement invoice details view
            messagebox.showinfo("Invoice Details", f"Details for Invoice ID: {invoice_id}\n\nThis feature is coming soon!")
    
    def _mark_as_paid(self):
        """Mark the selected invoice as paid"""
        with log_context(logger, action="mark_as_paid"):
            selected = self.invoice_tree.selection()
            if not selected:
                logger.warning("No invoice selected to mark as paid")
                return
                
            # Get the invoice ID from the selected item
            invoice_id = self.invoice_tree.item(selected[0], "values")[0]
            
            # Confirm with the user
            confirm = messagebox.askyesno("Confirm", f"Mark invoice #{invoice_id} as paid?")
            if not confirm:
                logger.info("User cancelled marking invoice as paid")
                return
                
            logger.info(f"Marking invoice {invoice_id} as paid")
            
            # Update the database
            query = "UPDATE invoices SET payment_status = 'Paid', paid_date = CURRENT_DATE WHERE id = %s"
            result = self.db_manager.execute_query(query, [invoice_id])
            
            if result and 'error' not in result:
                log_state_transition(
                    logger,
                    "Invoice",
                    "Unpaid",
                    "Paid",
                    invoice_id=invoice_id
                )
                messagebox.showinfo("Success", "Invoice marked as paid")
                # Refresh the dashboard
                self.update_dashboard()
            else:
                error_msg = result.get('error', 'Unknown error')
                log_with_error_code(
                    logger,
                    "DB_UPDATE_001",
                    f"Error marking invoice as paid: {error_msg}",
                    invoice_id=invoice_id,
                    error_details=error_msg
                )
                messagebox.showerror("Error", f"Failed to update invoice: {error_msg}")
    
    def _delete_invoice(self):
        """Delete the selected invoice"""
        with log_context(logger, action="delete_invoice"):
            selected = self.invoice_tree.selection()
            if not selected:
                logger.warning("No invoice selected for deletion")
                return
                
            # Get the invoice ID and number from the selected item
            values = self.invoice_tree.item(selected[0], "values")
            invoice_id = values[0]
            invoice_number = values[1]
            
            # Confirm with the user
            confirm = messagebox.askyesno(
                "Confirm Delete", 
                f"Are you sure you want to delete invoice #{invoice_number}?\n\nThis action cannot be undone.",
                icon="warning"
            )
            
            if not confirm:
                logger.info("User cancelled invoice deletion")
                return
                
            logger.info(f"Deleting invoice {invoice_id} (#{invoice_number})")
            
            # Delete from the database
            query = "DELETE FROM invoices WHERE id = %s"
            result = self.db_manager.execute_query(query, [invoice_id])
            
            if result and 'error' not in result:
                log_state_transition(
                    logger,
                    "Invoice",
                    "Exists",
                    "Deleted",
                    invoice_id=invoice_id,
                    invoice_number=invoice_number
                )
                messagebox.showinfo("Success", "Invoice deleted successfully")
                # Refresh the dashboard
                self.update_dashboard()
            else:
                error_msg = result.get('error', 'Unknown error')
                log_with_error_code(
                    logger,
                    "DB_DELETE_001",
                    f"Error deleting invoice: {error_msg}",
                    invoice_id=invoice_id,
                    invoice_number=invoice_number,
                    error_details=error_msg
                )
                messagebox.showerror("Error", f"Failed to delete invoice: {error_msg}")
    
    @log_execution_time(logger)
    def update_charts(self):
        """Update the charts with current data"""
        with log_context(logger, action="update_charts"):
        # Skip if charts are disabled or not initialized
        if not hasattr(self, 'pie_ax') or self.pie_ax is None:
                log_with_error_code(
                    logger, 
                    "UI_CHARTS_002", 
                    "Charts not initialized, skipping update"
                )
            return
            
        if hasattr(self, 'charts_disabled') and self.charts_disabled:
                logger.debug("Charts disabled, skipping update")
            return
            
        try:
            # Clear the charts
                logger.debug("Clearing existing charts")
            self.pie_ax.clear()
            self.bar_ax.clear()
            
            # Get data for pie chart (status distribution)
                logger.debug("Fetching invoice count data for pie chart")
            result = self.db_manager.get_invoice_counts()
            
            if result and isinstance(result, dict):
                labels = list(result.keys())
                values = list(result.values())
                
                # Create pie chart
                self.pie_ax.pie(values, labels=labels, autopct='%1.1f%%')
                self.pie_ax.set_title('Invoice Status')
                
                # Redraw
                self.pie_ax.figure.canvas.draw()
                    logger.debug(f"Updated pie chart with {len(labels)} status categories")
                else:
                    logger.warning("No invoice count data for pie chart")
            
            # Get data for bar chart (monthly totals)
                logger.debug("Fetching fund distribution data for bar chart")
                result = self.db_manager.get_fund_distribution()
                
                if result and isinstance(result, dict):
                    funds = list(result.keys())
                    amounts = list(result.values())
            
            # Create bar chart
                    self.bar_ax.bar(funds, amounts)
                    self.bar_ax.set_title('Funding Sources')
                    
                    # Set x-axis labels at an angle for better readability
                    self.bar_ax.set_xticklabels(funds, rotation=45, ha='right')
                    
                    # Adjust layout to make room for rotated labels
                    self.bar_ax.figure.tight_layout()
            
            # Redraw
            self.bar_ax.figure.canvas.draw()
                    logger.debug(f"Updated bar chart with {len(funds)} funding sources")
                else:
                    logger.warning("No fund distribution data for bar chart")
            
        except Exception as e:
                logger.exception_with_context(f"Error updating charts: {str(e)}")
    
    @log_execution_time(logger)
    def update_invoice_table(self):
        """Update the invoice table with data"""
        with log_context(logger, action="update_invoice_table"):
        # Check if invoice_tree is initialized
        if not hasattr(self, 'invoice_tree') or self.invoice_tree is None:
                log_with_error_code(
                    logger, 
                    "UI_TABLE_001", 
                    "Invoice table not initialized, skipping update"
                )
            return
            
        try:
            # Clear existing items
                logger.debug("Clearing existing invoice table entries")
            for item in self.invoice_tree.get_children():
                self.invoice_tree.delete(item)
            
            # Get invoice data
                logger.debug("Fetching recent invoice data")
            result = self.db_manager.get_recent_invoices(50)  # Get up to 50 recent invoices
            
            if result and 'rows' in result and result['rows']:
                # Format and insert rows
                    logger.debug(f"Processing {len(result['rows'])} invoices for display")
                for i, row in enumerate(result['rows']):
                    # Format values appropriately
                    formatted_row = []
                        for j, val in enumerate(row):
                            if isinstance(val, (datetime, datetime.date)):
                            formatted_row.append(val.strftime('%Y-%m-%d'))
                            elif isinstance(val, (int, float)) and j == 4:  # Assuming 5th column is amount
                            formatted_row.append(f"${val:,.2f}")
                        else:
                            formatted_row.append(str(val) if val is not None else "")
                    
                    # Insert into treeview
                    self.invoice_tree.insert("", tk.END, values=formatted_row)
                        
                        # Add color-coding based on status
                        if len(formatted_row) > 5:  # Make sure status column exists
                            status = formatted_row[5].lower()
                            item_id = self.invoice_tree.get_children()[-1]
                            
                            if status == 'paid':
                                self.invoice_tree.item(item_id, tags=('paid',))
                            elif status == 'overdue':
                                self.invoice_tree.item(item_id, tags=('overdue',))
                    
                    # Configure tags for coloring
                    self.invoice_tree.tag_configure('paid', background='#e6ffe6')  # Light green
                    self.invoice_tree.tag_configure('overdue', background='#ffe6e6')  # Light red
                
                logger.info(f"Updated invoice table with {len(result['rows'])} invoices")
            else:
                logger.info("No invoice data to display")
                
        except Exception as e:
                logger.exception_with_context(f"Error updating invoice table: {str(e)}")
    
    @log_execution_time(logger)
    def update_dashboard(self):
        """Update all dashboard elements"""
        with log_context(logger, action="update_dashboard"):
            try:
                # Validate the invoices table exists
                if not self._validate_invoices_table():
                    log_with_error_code(
                        logger, 
                        "DB_TABLE_MISSING", 
                        "Invoices table is missing or invalid"
                    )
                    return
                
            # Update summary cards
                logger.debug("Updating summary cards")
            self.update_summary_cards()
            
            # Update charts
                logger.debug("Updating charts")
            self.update_charts()
            
            # Update invoice table
                logger.debug("Updating invoice table")
            self.update_invoice_table()
            
                # Update fund filter
                logger.debug("Updating fund filter")
                self._update_fund_filter()
                
                logger.info("Dashboard updated successfully")
            
        except Exception as e:
                logger.exception_with_context(f"Error updating dashboard: {str(e)}")
                messagebox.showerror("Error", f"Failed to update dashboard: {str(e)}")
                
    def create_summary_cards(self):
        """Create the summary cards section"""
        # Implementation for summary cards
        pass
        
    def update_summary_cards(self):
        """Update the summary cards with current data"""
        # Implementation for updating summary cards
        pass
    
    def _validate_invoices_table(self):
        """Validate that the invoices table exists and has the right schema"""
        with log_context(logger, action="validate_invoices_table"):
            # Check if the table exists
            if not hasattr(self.db_manager, 'tables') or 'invoices' not in self.db_manager.tables:
                logger.warning("Invoices table does not exist")
                
                # Ask if we should create it
                create = messagebox.askyesno(
                    "Table Missing", 
                    "The invoices table doesn't exist. Would you like to create it now?"
                )
                
                if create:
                    logger.info("Creating invoices table")
                    # Implementation for creating the invoices table
                    return self.db_manager.ensure_valid_schema('invoices')
                    else:
                    logger.info("User chose not to create invoices table")
                    return False
            
            # Ensure the schema is valid
            return self.db_manager.ensure_valid_schema('invoices')
    
    @log_execution_time(logger)
    def _update_fund_filter(self):
        """Update the fund filter dropdown with available funds"""
        with log_context(logger, action="update_fund_filter"):
            # Check if fund_combo is initialized
            if not hasattr(self, 'fund_combo'):
                logger.warning("Fund combo box not initialized")
                return
                
            try:
                # Query the database for unique fund names
                query = "SELECT DISTINCT fund_paid_by FROM invoices WHERE fund_paid_by IS NOT NULL ORDER BY fund_paid_by"
                result = self.db_manager.execute_query(query)
                
                if result and 'rows' in result and result['rows']:
                    # Extract fund names
                    funds = ["All"]  # Add "All" as the first option
                    for row in result['rows']:
                        funds.append(row[0])
                    
                    # Update the combobox values
                    self.fund_combo['values'] = funds
                    self.fund_combo.current(0)  # Set to "All"
                    
                    logger.info(f"Updated fund filter with {len(funds) - 1} funds", 
                               extra={"funds": funds[1:]})
                else:
                    # No funds found
                    self.fund_combo['values'] = ["All"]
                    self.fund_combo.current(0)
                    logger.info("No funds found for filter")
                    
        except Exception as e:
                logger.exception_with_context(f"Error updating fund filter: {str(e)}")
                self.fund_combo['values'] = ["All"]
                self.fund_combo.current(0)
    
    @log_execution_time(logger)
    def apply_filters(self):
        """Apply the selected filters to the data"""
        with log_context(logger, action="apply_filters"):
            # Get filter values
            status = self.status_var.get()
            fund = self.fund_var.get()
            start_date = self.start_date_var.get()
            end_date = self.end_date_var.get()
            
            # Create filters dictionary
            filters = {}
            
            # Only add non-empty, non-"All" values
            if status and status != "All":
                filters["status"] = status
                logger.debug(f"Applying status filter: {status}")
            
            if fund and fund != "All":
                filters["fund"] = fund
                logger.debug(f"Applying fund filter: {fund}")
            
            if start_date:
                # Validate date format (YYYY-MM-DD)
                if self._validate_date(start_date):
                    filters["start_date"] = start_date
                    logger.debug(f"Applying start date filter: {start_date}")
                else:
                    logger.warning(f"Invalid start date format: {start_date}")
                    messagebox.showerror("Error", "Start date must be in YYYY-MM-DD format")
                    return
            
            if end_date:
                # Validate date format (YYYY-MM-DD)
                if self._validate_date(end_date):
                    filters["end_date"] = end_date
                    logger.debug(f"Applying end date filter: {end_date}")
                else:
                    logger.warning(f"Invalid end date format: {end_date}")
                    messagebox.showerror("Error", "End date must be in YYYY-MM-DD format")
                    return
            
            # Log the filter application
            logger.info(f"Applying filters to dashboard", extra={"filters": filters})
            
            # Update the dashboard with the filters
            self._update_data(filters)
            
    def _validate_date(self, date_str):
        """Validate that a string is in YYYY-MM-DD format"""
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            return False
    
    def _update_data(self, filters=None):
        """Update the data based on filters"""
        with log_context(logger, action="update_filtered_data"):
            try:
                # Update the UI with filtered data
                # This is a placeholder for the actual implementation
                
                # Example of how this might be implemented:
                if hasattr(self, 'invoice_tree') and self.invoice_tree:
                    # Clear existing items
                    for item in self.invoice_tree.get_children():
                        self.invoice_tree.delete(item)
                    
                    # Get filtered invoice data
            result = self.db_manager.get_invoice_data(filters)
            
                    if result and 'rows' in result and result['rows']:
                        # Format and insert rows
                        for row in result['rows']:
                            # Format and insert as before
                            formatted_row = self._format_invoice_row(row)
                            self.invoice_tree.insert('', 'end', values=formatted_row)
                            
                        logger.info(f"Updated table with {len(result['rows'])} filtered invoices")
                    else:
                        logger.info("No invoices match the selected filters")
                
                # Update summary cards and charts with filtered data
                # ...
                
        except Exception as e:
                logger.exception_with_context(f"Error updating filtered data: {str(e)}")
                messagebox.showerror("Error", f"Failed to apply filters: {str(e)}")
    
    @log_execution_time(logger)
    def show(self):
        """Show the dashboard"""
        with log_context(logger, action="show_dashboard"):
            logger.info("Showing dashboard")
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