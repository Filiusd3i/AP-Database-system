"""
Dashboard visualization module for real-time invoice data display.
Provides summary cards and charts that automatically update based on database changes.
"""

import tkinter as tk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import logging
import datetime
import os

logger = logging.getLogger(__name__)

class DashboardVisualization:
    def __init__(self, app):
        """Initialize the dashboard visualization.
        
        Args:
            app: Main application instance
        """
        self.app = app
        self.last_update = None
        self.update_interval = 5000  # 5 seconds refresh interval
        self.current_filters = {
            'where_sql': '',
            'params': []
        }
        self.frames = {
            'cards_frame': None,
            'charts_frame': None
        }

    def create_summary_cards(self, parent_frame):
        """Create summary cards for key metrics using real-time database data"""
        try:
            # Store reference to the frame
            self.frames['cards_frame'] = parent_frame
            
            # Ensure database connection is active
            if not self.app.database_manager.is_connected():
                try:
                    self.app.database_manager.connect()
                    logger.info("Connected to database for dashboard cards")
                except Exception as e:
                    logger.error(f"Cannot connect to database: {str(e)}")
                    self._show_connection_error(parent_frame, str(e))
                    return
            
            # Use the safe invoice data method to fetch raw data
            invoice_data = self.app.database_manager.get_safe_invoice_data()
            
            if 'error' in invoice_data:
                raise Exception(invoice_data['error'])
            
            # Apply filters if any
            filtered_data = self._filter_invoice_data(invoice_data)
            
            # Calculate metrics in Python using the safe method
            metrics = self.app.database_manager.calculate_dashboard_metrics(filtered_data)
            
            # Create card frame with 4 cards matching Access interface
            cards = [
                {"title": "Paid Invoices", "value": str(metrics.get("paid_count", 0)), "color": "#4CAF50"},
                {"title": "Pending Invoices", "value": str(metrics.get("unpaid_count", 0)), "color": "#FF9800"},
                {"title": "Total Amount", "value": f"${float(metrics.get('total_amount', 0)):,.2f}", "color": "#2196F3"},
                {"title": "Overdue Invoices", "value": str(metrics.get("overdue_count", 0)), "color": "#F44336"}
            ]
            
            # Clear existing cards if any
            for widget in parent_frame.winfo_children():
                widget.destroy()
            
            # Create each card
            for i, card in enumerate(cards):
                card_frame = tk.Frame(parent_frame, bg="white", bd=1, relief=tk.RAISED)
                card_frame.grid(row=0, column=i, padx=10, pady=10, sticky="nsew")
                
                # Card title
                title_label = tk.Label(card_frame, text=card["title"], 
                                     font=("Arial", 12), bg="white", fg="#555555")
                title_label.pack(padx=10, pady=(10, 5))
                
                # Card value
                value_label = tk.Label(card_frame, text=card["value"], 
                                     font=("Arial", 24, "bold"), bg="white", fg=card["color"])
                value_label.pack(padx=10, pady=(5, 10))
            
            # Configure grid columns to be evenly spaced
            for i in range(4):
                parent_frame.grid_columnconfigure(i, weight=1)
            
            # Update timestamp
            self._update_timestamp()
            
            # Schedule next update
            self.schedule_update(parent_frame)
            
        except Exception as e:
            logger.error(f"Error creating summary cards: {str(e)}")
            # Show error state in UI
            error_label = tk.Label(parent_frame, 
                                 text=f"Error loading data: {str(e)}", 
                                 fg="red",
                                 bg="white")
            error_label.pack(padx=10, pady=10)
    
    def schedule_update(self, parent_frame):
        """Schedule the next data update"""
        if parent_frame.winfo_exists():
            parent_frame.after(self.update_interval, lambda: self.create_summary_cards(parent_frame))
    
    def create_visualization_charts(self, parent_frame):
        """Create visualization charts with real-time data"""
        try:
            # Store reference to the frame
            self.frames['charts_frame'] = parent_frame
            
            # Ensure database connection is active
            if not self.app.database_manager.is_connected():
                try:
                    self.app.database_manager.connect()
                    logger.info("Connected to database for dashboard charts")
                except Exception as e:
                    logger.error(f"Cannot connect to database: {str(e)}")
                    self._show_connection_error(parent_frame, str(e))
                    return
            
            # Use safe invoice data method
            invoice_data = self.app.database_manager.get_safe_invoice_data()
            
            if 'error' in invoice_data:
                raise Exception(invoice_data['error'])
            
            # Apply filters if any
            filtered_data = self._filter_invoice_data(invoice_data)
            
            # Process the data for visualization in Python
            status_data = self._calculate_status_distribution(filtered_data)
            quarter_data = self._calculate_quarter_totals(filtered_data)
            
            # Clear existing charts
            for widget in parent_frame.winfo_children():
                widget.destroy()
            
            # Create frames for charts
            left_frame = tk.Frame(parent_frame, bg="white")
            left_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
            
            right_frame = tk.Frame(parent_frame, bg="white")
            right_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
            
            # Configure grid
            parent_frame.grid_columnconfigure(0, weight=1)
            parent_frame.grid_columnconfigure(1, weight=1)
            
            # Create pie chart for status distribution
            fig1 = plt.Figure(figsize=(6, 4), dpi=100)
            ax1 = fig1.add_subplot(111)
            
            if status_data:
                colors = ['#4CAF50', '#FF9800', '#F44336']  # Green, Orange, Red
                wedges, texts, autotexts = ax1.pie(
                    status_data.values(),
                    labels=status_data.keys(),
                    autopct='%1.1f%%',
                    colors=colors[:len(status_data)],
                    startangle=90
                )
                ax1.set_title('Invoice Status Distribution')
            else:
                ax1.text(0.5, 0.5, "No status data available", ha='center', va='center')
                ax1.set_title('Invoice Status Distribution')
            
            canvas1 = FigureCanvasTkAgg(fig1, left_frame)
            canvas1.draw()
            canvas1.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            # Create bar chart for quarterly amounts
            fig2 = plt.Figure(figsize=(6, 4), dpi=100)
            ax2 = fig2.add_subplot(111)
            
            if quarter_data:
                quarters = list(quarter_data.keys())
                amounts = list(quarter_data.values())
                
                ax2.bar(quarters, amounts, color='#2196F3')
                ax2.set_title('Invoice Amounts by Quarter')
                ax2.set_xlabel('Quarter')
                ax2.set_ylabel('Amount ($)')
                
                # Format y-axis as currency
                ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
                
                # Rotate x-axis labels
                plt.setp(ax2.get_xticklabels(), rotation=30, ha='right')
            else:
                ax2.text(0.5, 0.5, "No quarterly data available", ha='center', va='center')
                ax2.set_title('Invoice Amounts by Quarter')
            
            canvas2 = FigureCanvasTkAgg(fig2, right_frame)
            canvas2.draw()
            canvas2.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            # Schedule next update
            self.schedule_chart_update(parent_frame)
            
        except Exception as e:
            logger.error(f"Error creating charts: {str(e)}")
            error_label = tk.Label(parent_frame, 
                                 text=f"Error loading charts: {str(e)}", 
                                 fg="red",
                                 bg="white")
            error_label.pack(padx=10, pady=10)
    
    def schedule_chart_update(self, parent_frame):
        """Schedule the next chart update"""
        if parent_frame.winfo_exists():
            parent_frame.after(self.update_interval, lambda: self.create_visualization_charts(parent_frame))

    def apply_filters(self, start_date=None, end_date=None, fund=None, status=None):
        """Apply filters to the visualization
        
        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            fund: Optional fund filter
            status: Optional status filter
        """
        # Store filters for Python-based filtering
        self.current_filters = {
            'start_date': start_date,
            'end_date': end_date,
            'fund': fund,
            'status': status
        }
        
        # Trigger updates
        self.refresh_all()
    
    def _filter_invoice_data(self, invoice_data):
        """Apply filters to raw invoice data
        
        Args:
            invoice_data: Raw invoice data from get_safe_invoice_data
            
        Returns:
            dict: Filtered invoice data
        """
        import datetime
        
        # If no filters are active, return the original data
        if not any(self.current_filters.values()):
            return invoice_data
        
        # Get filters
        start_date = self.current_filters.get('start_date')
        end_date = self.current_filters.get('end_date') 
        fund = self.current_filters.get('fund')
        status = self.current_filters.get('status')
        
        # Check if we have valid data
        if not invoice_data or 'error' in invoice_data or not invoice_data.get('rows'):
            return invoice_data
        
        # Get column indexes for key fields
        columns = invoice_data.get('columns', [])
        rows = invoice_data.get('rows', [])
        
        # Find important column indexes
        date_idx = -1
        fund_idx = -1
        status_idx = -1
        
        for i, col in enumerate(columns):
            col_name = col.lower() if col else ""
            if col_name == 'date':
                date_idx = i
            elif col_name in ['fund', 'fund paid by', 'fundid', 'fund_id']:
                fund_idx = i
            elif col_name == 'status':
                status_idx = i
        
        # If no filterable columns found, return original data
        if date_idx < 0 and fund_idx < 0 and status_idx < 0:
            return invoice_data
        
        # Parse date strings to datetime objects for comparison
        start_date_obj = None
        end_date_obj = None
        
        if start_date:
            try:
                if isinstance(start_date, str):
                    # Try common date formats
                    formats = ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"]
                    for fmt in formats:
                        try:
                            start_date_obj = datetime.datetime.strptime(start_date, fmt)
                            break
                        except ValueError:
                            continue
                elif isinstance(start_date, datetime.datetime):
                    start_date_obj = start_date
            except:
                pass
        
        if end_date:
            try:
                if isinstance(end_date, str):
                    # Try common date formats
                    formats = ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"]
                    for fmt in formats:
                        try:
                            end_date_obj = datetime.datetime.strptime(end_date, fmt)
                            break
                        except ValueError:
                            continue
                elif isinstance(end_date, datetime.datetime):
                    end_date_obj = end_date
            except:
                pass
        
        # Filter the rows based on criteria
        filtered_rows = []
        
        for row in rows:
            # Check date filters
            if date_idx >= 0 and (start_date_obj or end_date_obj):
                date_value = row[date_idx] if date_idx < len(row) else None
                if date_value:
                    # Parse date value
                    date_obj = None
                    try:
                        if isinstance(date_value, datetime.datetime):
                            date_obj = date_value
                        elif isinstance(date_value, str):
                            # Try common date formats
                            formats = ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"]
                            for fmt in formats:
                                try:
                                    date_obj = datetime.datetime.strptime(date_value, fmt)
                                    break
                                except ValueError:
                                    continue
                    except:
                        pass
                    
                    # Skip if date cannot be parsed
                    if not date_obj:
                        continue
                    
                    # Apply date filters
                    if start_date_obj and date_obj < start_date_obj:
                        continue
                    if end_date_obj and date_obj > end_date_obj:
                        continue
            
            # Check fund filter
            if fund and fund_idx >= 0:
                fund_value = row[fund_idx] if fund_idx < len(row) else None
                if not fund_value or str(fund_value).lower() != fund.lower():
                    continue
            
            # Check status filter
            if status and status_idx >= 0:
                status_value = row[status_idx] if status_idx < len(row) else None
                if not status_value or str(status_value).lower() != status.lower():
                    continue
            
            # All filters passed, include the row
            filtered_rows.append(row)
        
        # Return the filtered data
        return {
            'columns': columns,
            'rows': filtered_rows
        }
    
    def _get_fund_column_name(self):
        """Get the column name for Fund in the database
        
        Returns:
            str: The column name for Fund or None if not found
        """
        # Try different common column names for Fund
        possible_columns = ["Fund Paid By", "Fund", "FundID", "Fund_ID"]
        
        for col in possible_columns:
            try:
                # Try a simple query to check if the column exists
                test_query = f"SELECT [{col}] FROM Invoices WHERE 1=0"
                result = self.app.database_manager.execute_query(test_query)
                
                if 'error' not in result:
                    return col
            except Exception:
                continue
        
        return None
    
    def refresh_all(self):
        """Refresh all visualization components"""
        try:
            # Update connection status
            if hasattr(self, 'connection_status_label') and self.connection_status_label.winfo_exists():
                self.connection_status_label.config(
                    text=self._get_connection_status_text(),
                    fg=self._get_connection_status_color()
                )
            
            # If not connected, attempt to connect
            if not self.app.database_manager.is_connected():
                try:
                    self.app.database_manager.connect()
                except Exception as e:
                    logger.error(f"Cannot connect to database during refresh: {str(e)}")
            
            # Refresh cards if the frame exists
            if self.frames.get('cards_frame') and self.frames['cards_frame'].winfo_exists():
                self.create_summary_cards(self.frames['cards_frame'])
            
            # Refresh charts if the frame exists
            if self.frames.get('charts_frame') and self.frames['charts_frame'].winfo_exists():
                self.create_visualization_charts(self.frames['charts_frame'])
            
            # Update filter status indicator
            self._update_filter_status()
            
            # Update last updated timestamp    
            self._update_timestamp()
                
            logger.info("Dashboard refreshed successfully")
        except Exception as e:
            logger.error(f"Error refreshing dashboard: {str(e)}")
            
            # Show error in status if possible
            if hasattr(self, 'connection_status_label') and self.connection_status_label.winfo_exists():
                self.connection_status_label.config(
                    text=f"Error: {str(e)}",
                    fg="#F44336"  # Red
                )
    
    def add_filter_controls(self, parent_frame):
        """Add filter controls to the dashboard
        
        Args:
            parent_frame: Parent frame to add controls to
        """
        # Create a frame for filters
        filter_frame = tk.Frame(parent_frame, bg="#f0f0f0")
        filter_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Add a title
        title_label = tk.Label(filter_frame, text="Filter Invoices:", font=("Arial", 10, "bold"), bg="#f0f0f0")
        title_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        # Get available fields from database
        available_fields = self.app.database_manager.get_available_invoice_fields()
        
        # Status filter
        status_label = tk.Label(filter_frame, text="Status:", bg="#f0f0f0")
        status_label.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        status_var = tk.StringVar()
        status_combo = ttk.Combobox(filter_frame, textvariable=status_var, width=15)
        status_values = ['All'] + available_fields.get('status_values', ['Paid', 'Unpaid', 'Outstanding']) 
        status_combo['values'] = status_values
        status_combo.current(0)
        status_combo.grid(row=0, column=2, padx=5, pady=5)
        
        # Fund filter
        fund_label = tk.Label(filter_frame, text="Fund:", bg="#f0f0f0")
        fund_label.grid(row=0, column=3, padx=5, pady=5, sticky="w")
        
        fund_var = tk.StringVar()
        fund_combo = ttk.Combobox(filter_frame, textvariable=fund_var, width=15)
        fund_values = ['All'] + available_fields.get('fund_values', [])
        fund_combo['values'] = fund_values
        fund_combo.current(0)
        fund_combo.grid(row=0, column=4, padx=5, pady=5)
        
        # Apply button
        apply_button = tk.Button(filter_frame, text="Apply Filters", 
                               command=lambda: self._apply_selected_filters(status_var.get(), fund_var.get()))
        apply_button.grid(row=0, column=5, padx=10, pady=5)
        
        # Reset button
        reset_button = tk.Button(filter_frame, text="Reset", 
                               command=lambda: self._reset_filters(status_combo, fund_combo))
        reset_button.grid(row=0, column=6, padx=5, pady=5)
        
        # Filter status indicator
        self.filter_status_label = tk.Label(
            filter_frame, 
            text="No filters active", 
            bg="#f0f0f0", 
            fg="#666666",
            font=("Arial", 8, "italic")
        )
        self.filter_status_label.grid(row=0, column=7, padx=10, pady=5, sticky="w")
        
        # Configure grid
        filter_frame.grid_columnconfigure(8, weight=1)
    
    def _update_filter_status(self):
        """Update the filter status indicator"""
        if not hasattr(self, 'filter_status_label') or not self.filter_status_label.winfo_exists():
            return
            
        active_filters = []
        
        if self.current_filters.get('status'):
            active_filters.append(f"Status: {self.current_filters['status']}")
            
        if self.current_filters.get('fund'):
            active_filters.append(f"Fund: {self.current_filters['fund']}")
            
        if self.current_filters.get('start_date'):
            active_filters.append(f"From: {self.current_filters['start_date']}")
            
        if self.current_filters.get('end_date'):
            active_filters.append(f"To: {self.current_filters['end_date']}")
        
        if active_filters:
            self.filter_status_label.config(
                text=f"Active filters: {', '.join(active_filters)}",
                fg="#2196F3"
            )
        else:
            self.filter_status_label.config(
                text="No filters active",
                fg="#666666"
            )
    
    def _apply_selected_filters(self, status, fund):
        """Apply the selected filters"""
        # Convert 'All' to None
        status_filter = None if status == 'All' else status
        fund_filter = None if fund == 'All' else fund
        
        # Apply filters
        self.apply_filters(status=status_filter, fund=fund_filter)
        
        # Update filter status indicator
        self._update_filter_status()
    
    def _reset_filters(self, status_combo, fund_combo):
        """Reset all filters"""
        status_combo.current(0)
        fund_combo.current(0)
        
        # Clear filters and refresh
        self.current_filters = {
            'start_date': None,
            'end_date': None,
            'fund': None,
            'status': None
        }
        
        # Update filter status indicator
        self._update_filter_status()
        
        # Refresh dashboard
        self.refresh_all()
    
    def add_refresh_button(self, parent_frame):
        """Add a refresh button to the dashboard
        
        Args:
            parent_frame: Parent frame to add the button to
        """
        # Create a frame for the refresh button
        refresh_frame = tk.Frame(parent_frame, bg="#f0f0f0")
        refresh_frame.pack(fill=tk.X, padx=10, pady=5, anchor="ne")
        
        # Add database selection button
        db_button = tk.Button(
            refresh_frame,
            text="Select Database",
            command=self.app.select_database,
            bg="#e0e0e0",
            fg="#333333",
            padx=10
        )
        db_button.pack(side=tk.RIGHT, padx=10, pady=5)
        
        # Add refresh button with icon or text
        refresh_button = tk.Button(
            refresh_frame, 
            text="🔄 Refresh Data", 
            command=self.refresh_all,
            bg="#e0e0e0",
            fg="#333333",
            padx=10
        )
        refresh_button.pack(side=tk.RIGHT, padx=10, pady=5)
        
        # Add auto-refresh checkbox
        auto_var = tk.BooleanVar(value=True)
        auto_check = tk.Checkbutton(
            refresh_frame, 
            text="Auto-refresh", 
            variable=auto_var,
            bg="#f0f0f0",
            command=lambda: self._toggle_auto_refresh(auto_var.get())
        )
        auto_check.pack(side=tk.RIGHT, padx=10, pady=5)
        
        # Add database connection status label
        self.connection_status_label = tk.Label(
            refresh_frame,
            text=self._get_connection_status_text(),
            bg="#f0f0f0",
            fg=self._get_connection_status_color(),
            font=("Arial", 8)
        )
        self.connection_status_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        # Add last updated label
        self.last_updated_label = tk.Label(
            refresh_frame,
            text="Last updated: Now",
            bg="#f0f0f0",
            fg="#666666",
            font=("Arial", 8)
        )
        self.last_updated_label.pack(side=tk.RIGHT, padx=10, pady=5)
    
    def _toggle_auto_refresh(self, enabled):
        """Toggle automatic refresh
        
        Args:
            enabled: Whether auto-refresh is enabled
        """
        if enabled:
            self.update_interval = 5000  # 5 seconds
            # Start the refresh cycle for cards and charts
            if self.frames.get('cards_frame') and self.frames['cards_frame'].winfo_exists():
                self.schedule_update(self.frames['cards_frame'])
            if self.frames.get('charts_frame') and self.frames['charts_frame'].winfo_exists():
                self.schedule_chart_update(self.frames['charts_frame'])
        else:
            self.update_interval = 3600000  # 1 hour (effectively disabled)
    
    def _update_timestamp(self):
        """Update the last updated timestamp"""
        if hasattr(self, 'last_updated_label') and self.last_updated_label.winfo_exists():
            now = datetime.datetime.now().strftime("%H:%M:%S")
            self.last_updated_label.config(text=f"Last updated: {now}")
        
        self.last_update = datetime.datetime.now()

    def _calculate_status_distribution(self, invoice_data):
        """Calculate invoice status distribution from raw invoice data
        
        Args:
            invoice_data: Raw invoice data from get_safe_invoice_data
            
        Returns:
            dict: Status distribution data for visualization
        """
        import math
        
        # Default result
        status_counts = {"Paid": 0, "Unpaid": 0, "Overdue": 0}
        
        # Check if we have valid data
        if not invoice_data or 'error' in invoice_data or not invoice_data.get('rows'):
            return status_counts
        
        # Get column indexes for key fields
        columns = invoice_data.get('columns', [])
        rows = invoice_data.get('rows', [])
        
        # Find important column indexes
        check_idx = -1
        status_idx = -1
        days_overdue_idx = -1
        
        for i, col in enumerate(columns):
            col_name = col.lower() if col else ""
            if col_name == 'check':
                check_idx = i
            elif col_name == 'status':
                status_idx = i
            elif col_name == 'days overdue':
                days_overdue_idx = i
        
        # Calculate status counts from data
        for row in rows:
            # First try to use Status field if available
            if status_idx >= 0 and status_idx < len(row):
                status = row[status_idx]
                if status:
                    if status.lower() == 'paid':
                        status_counts["Paid"] += 1
                    elif status.lower() == 'unpaid':
                        status_counts["Unpaid"] += 1
                    elif status.lower() == 'overdue' or status.lower() == 'outstanding':
                        status_counts["Overdue"] += 1
                    else:
                        # For any other status, count as unpaid
                        status_counts["Unpaid"] += 1
            # Fallback to check field logic
            elif check_idx >= 0 and check_idx < len(row):
                check_value = row[check_idx]
                if check_value and str(check_value).strip():
                    status_counts["Paid"] += 1
                else:
                    # Check if overdue
                    if days_overdue_idx >= 0 and days_overdue_idx < len(row):
                        days_overdue = row[days_overdue_idx]
                        if days_overdue is not None and not (isinstance(days_overdue, float) and math.isnan(days_overdue)):
                            try:
                                overdue = float(days_overdue)
                                if overdue > 0:
                                    status_counts["Overdue"] += 1
                                else:
                                    status_counts["Unpaid"] += 1
                            except (ValueError, TypeError):
                                status_counts["Unpaid"] += 1
                        else:
                            status_counts["Unpaid"] += 1
                    else:
                        status_counts["Unpaid"] += 1
        
        # Remove zero counts
        return {k: v for k, v in status_counts.items() if v > 0}
    
    def _calculate_quarter_totals(self, invoice_data):
        """Calculate invoice amounts by quarter from raw invoice data
        
        Args:
            invoice_data: Raw invoice data from get_safe_invoice_data
            
        Returns:
            dict: Quarter total data for visualization
        """
        import datetime
        import math
        
        # Default empty result
        quarter_totals = {}
        
        # Check if we have valid data
        if not invoice_data or 'error' in invoice_data or not invoice_data.get('rows'):
            return quarter_totals
        
        # Get column indexes for key fields
        columns = invoice_data.get('columns', [])
        rows = invoice_data.get('rows', [])
        
        # Find important column indexes
        date_idx = -1
        amount_idx = -1
        
        for i, col in enumerate(columns):
            col_name = col.lower() if col else ""
            if col_name == 'date':
                date_idx = i
            elif col_name == 'amount':
                amount_idx = i
        
        # Cannot calculate without date and amount
        if date_idx < 0 or amount_idx < 0:
            return quarter_totals
        
        # Calculate quarter totals from data
        for row in rows:
            # Get values safely
            date_value = row[date_idx] if date_idx >= 0 and date_idx < len(row) else None
            amount_value = row[amount_idx] if amount_idx >= 0 and amount_idx < len(row) else None
            
            # Handle None/NaN values
            if amount_value is None or (isinstance(amount_value, float) and math.isnan(amount_value)):
                continue
                
            # Skip if amount is not a number
            if not isinstance(amount_value, (int, float)):
                try:
                    amount_value = float(amount_value)
                except (ValueError, TypeError):
                    continue
            
            # Process date to get quarter
            if date_value:
                try:
                    # Try to parse the date in various formats
                    date_obj = None
                    if isinstance(date_value, datetime.datetime):
                        date_obj = date_value
                    elif isinstance(date_value, str):
                        # Try common date formats
                        formats = [
                            "%Y-%m-%d",
                            "%m/%d/%Y",
                            "%d/%m/%Y",
                            "%Y/%m/%d"
                        ]
                        
                        for fmt in formats:
                            try:
                                date_obj = datetime.datetime.strptime(date_value, fmt)
                                break
                            except ValueError:
                                continue
                    
                    if date_obj:
                        # Format as "YYYY-QX"
                        quarter = (date_obj.month - 1) // 3 + 1
                        quarter_key = f"{date_obj.year}-Q{quarter}"
                        
                        # Add to the quarter totals
                        if quarter_key in quarter_totals:
                            quarter_totals[quarter_key] += amount_value
                        else:
                            quarter_totals[quarter_key] = amount_value
                except Exception:
                    # Skip if date cannot be processed
                    continue
        
        # Sort by quarter and limit to the most recent 4 quarters
        sorted_quarters = sorted(quarter_totals.items(), key=lambda x: x[0], reverse=True)
        return dict(sorted_quarters[:4])

    def _show_connection_error(self, parent_frame, error_message):
        """Show a connection error message in the frame
        
        Args:
            parent_frame: The frame to show the error in
            error_message: The error message to display
        """
        # Clear the frame
        for widget in parent_frame.winfo_children():
            widget.destroy()
            
        # Create error label
        error_label = tk.Label(
            parent_frame,
            text=f"Database connection error:\n{error_message}",
            fg="red",
            bg="white",
            justify=tk.LEFT
        )
        error_label.pack(padx=20, pady=20, fill=tk.BOTH, expand=True)
        
        # Create retry button
        retry_button = tk.Button(
            parent_frame,
            text="Retry Connection",
            command=lambda: self.refresh_all()
        )
        retry_button.pack(pady=10)

    def _get_connection_status_text(self):
        """Get the connection status text
        
        Returns:
            str: The connection status text
        """
        if self.app.database_manager.is_connected():
            db_path = getattr(self.app.database_manager, 'db_path', 'Unknown')
            db_name = os.path.basename(db_path) if db_path else 'Unknown'
            return f"Connected to: {db_name}"
        else:
            return "Not connected to database"
    
    def _get_connection_status_color(self):
        """Get the connection status color
        
        Returns:
            str: The connection status color
        """
        if self.app.database_manager.is_connected():
            return "#4CAF50"  # Green
        else:
            return "#F44336"  # Red 