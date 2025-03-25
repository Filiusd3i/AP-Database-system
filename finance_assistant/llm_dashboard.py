#!/usr/bin/env python3
"""
LLM-Powered Invoice Dashboard

A dashboard with natural language search capabilities for invoice data.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import logging
import datetime
import threading
import platform
from typing import Dict, List, Any, Optional
import pandas as pd

from finance_assistant.llm_client import LLMClient

# Configure logging
logger = logging.getLogger(__name__)

class LLMInvoiceDashboard:
    """LLM-powered dashboard for invoice data visualization and search"""
    
    def __init__(self, parent, db_manager, llm_client=None):
        """Initialize the LLM dashboard
        
        Args:
            parent: The parent window
            db_manager: The database manager instance
            llm_client: Optional LLM client for natural language processing
        """
        self.parent = parent
        self.db_manager = db_manager
        self.llm_client = llm_client or LLMClient()
        self.window = None
        self.frame = None
        self.results_tree = None
        self.sql_display = None
        self.search_var = None
        self.status_var = None
        self.style = None
        
        # Values for summary cards
        self.total_value = 0
        self.paid_value = 0
        self.unpaid_value = 0
        self.overdue_value = 0
        
        # Ensure the database is connected
        if not self.db_manager.is_connected:
            messagebox.showerror("Error", "Please connect to a database first")
            return
        
        # Check and fix database schema automatically
        self._check_and_fix_schema()
        
        # Create the dashboard window
        self._create_window()
        
    def _check_and_fix_schema(self):
        """Check and automatically fix database schema type issues"""
        try:
            # Create schema validator if not already available through db_manager
            if not hasattr(self.db_manager, 'schema_validator') or self.db_manager.schema_validator is None:
                from finance_assistant.schema_validator import SchemaValidator
                self.db_manager.schema_validator = SchemaValidator(self.db_manager)
            
            # Check and fix invoices table schema
            result = self.db_manager.schema_validator.validate_table_schema('invoices', auto_fix=True)
            
            if not result['valid']:
                logger.info("Schema issues were detected and fixed automatically")
                
            return True
            
        except Exception as e:
            logger.error(f"Schema check error: {str(e)}")
            return False
        
    def _create_window(self):
        """Create the dashboard window with dark gradient theme and search feature"""
        self.window = tk.Toplevel(self.parent)
        self.window.title("LLM-Powered Invoice Dashboard")
        self.window.geometry("1000x700")
        self.window.minsize(800, 600)
        
        # Configure the style for dark theme
        self.style = ttk.Style()
        self.style.theme_use('clam')  # 'clam' is the most customizable built-in theme
        
        # Define color palette
        self.bg_dark = '#1e1e2e'  # Dark background
        self.bg_medium = '#2a2a3a'  # Medium background for frames
        self.bg_light = '#313145'  # Lighter background for input areas
        self.accent_color = '#7e57c2'  # Purple accent color
        self.text_color = '#e0e0e0'  # Light text for readability
        self.highlight_color = '#bb86fc'  # Highlight color for selections
        
        # Configure font based on platform
        self._check_platform_compatibility()
        
        # Configure styles for different widgets
        self.style.configure('TFrame', background=self.bg_dark)
        self.style.configure('TLabelframe', background=self.bg_dark, foreground=self.text_color)
        self.style.configure('TLabelframe.Label', background=self.bg_dark, foreground=self.text_color)
        self.style.configure('TLabel', background=self.bg_dark, foreground=self.text_color)
        self.style.configure('TButton', background=self.accent_color, foreground=self.text_color)
        self.style.map('TButton', 
                      background=[('active', self.highlight_color), ('pressed', self.bg_light)],
                      foreground=[('active', 'white')])
        self.style.configure('TEntry', fieldbackground=self.bg_light, foreground=self.text_color)
        
        # Configure Treeview colors
        self.style.configure('Treeview', 
                           background=self.bg_medium, 
                           foreground=self.text_color,
                           fieldbackground=self.bg_medium)
        self.style.map('Treeview', 
                      background=[('selected', self.accent_color)],
                      foreground=[('selected', 'white')])
        
        # Configure the window background
        self.window.configure(background=self.bg_dark)
        
        # Create gradient background (simulated with frames of different shades)
        self.frame = ttk.Frame(self.window)
        self.frame.pack(fill=tk.BOTH, expand=True)
        
        # Add a gradient header
        header_frame = tk.Frame(self.frame, height=60, bg=self.bg_dark)
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
        header_canvas.create_text(20, 30, text="LLM Invoice Dashboard", 
                                 fill=self.text_color, font=(self.font_family, 16, 'bold'),
                                 anchor='w')
        
        # Main content area
        content_frame = ttk.Frame(self.frame)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Create layout with styled components
        self._create_layout(content_frame)
        
    def _check_platform_compatibility(self):
        """Adjust styling based on platform"""
        system = platform.system()
        if system == "Windows":
            # Windows-specific adjustments
            self.font_family = "Segoe UI"
        elif system == "Darwin":  # macOS
            # macOS-specific adjustments
            self.font_family = "SF Pro Text"
        else:  # Linux
            self.font_family = "Ubuntu"
        
        # Update fonts throughout the application
        self.style.configure('TLabel', font=(self.font_family, 10))
        self.style.configure('TButton', font=(self.font_family, 10))
        self.style.configure('TEntry', font=(self.font_family, 10))
        self.style.configure('Treeview', font=(self.font_family, 10))
        self.style.configure('Treeview.Heading', font=(self.font_family, 10, 'bold'))
        
    def _create_layout(self, parent_frame):
        """Create the dashboard layout with dark theme styling"""
        # Create search frame with rounded corners effect
        search_frame = ttk.LabelFrame(parent_frame, text="Natural Language Search")
        search_frame.pack(fill=tk.X, padx=5, pady=10)
        
        # Add search entry with custom styling
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=50,
                                font=(self.font_family, 11))
        search_entry.pack(side=tk.LEFT, padx=8, pady=10, fill=tk.X, expand=True)
        search_entry.bind("<Return>", lambda event: self._execute_llm_search())
        
        # Custom button style with rounded effect
        self.style.configure('Accent.TButton', font=(self.font_family, 10, 'bold'))
        search_button = ttk.Button(search_frame, text="Search", style='Accent.TButton',
                                  command=self._execute_llm_search)
        search_button.pack(side=tk.LEFT, padx=5, pady=10)
        
        suggest_button = ttk.Button(search_frame, text="Suggestions", 
                                  command=self._show_search_suggestions)
        suggest_button.pack(side=tk.LEFT, padx=5, pady=10)
        
        # Add schema tools button
        tools_button = ttk.Button(search_frame, text="Schema Tools", 
                               command=self._show_schema_tools_menu)
        tools_button.pack(side=tk.LEFT, padx=5, pady=10)
        
        # Create gradient summary cards
        self._create_summary_cards(parent_frame)
        
        # SQL display with styled appearance
        sql_frame = ttk.LabelFrame(parent_frame, text="Generated SQL")
        sql_frame.pack(fill=tk.X, padx=5, pady=10)
        
        # Create SQL display with syntax highlighting colors
        self.sql_display = tk.Text(sql_frame, height=4, wrap=tk.WORD, 
                                font=('Consolas', 11),
                                bg=self.bg_light, fg='#a5d6a7', 
                                insertbackground=self.text_color)
        self.sql_display.pack(fill=tk.X, padx=5, pady=5)
        
        # Create results area with custom border
        results_frame = ttk.LabelFrame(parent_frame, text="Search Results")
        results_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=10)
        
        # Create status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(results_frame, textvariable=self.status_var, anchor=tk.W)
        status_bar.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        # Create frame for treeview and scrollbars
        tree_frame = ttk.Frame(results_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        hsb = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Create treeview for results with alternating row colors
        columns = ("invoice_number", "vendor", "amount", "invoice_date", "due_date", "payment_status", "fund_paid_by")
        self.results_tree = ttk.Treeview(
            tree_frame, 
            columns=columns, 
            show="headings",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set
        )
        
        # Configure columns and headings with improved styling
        column_widths = {
            "invoice_number": 120,
            "vendor": 150,
            "amount": 100,
            "invoice_date": 100,
            "due_date": 100,
            "payment_status": 100,
            "fund_paid_by": 150
        }
        
        for col in columns:
            display_name = col.replace("_", " ").title()
            self.results_tree.heading(col, text=display_name)
            self.results_tree.column(col, width=column_widths.get(col, 100), minwidth=50)
        
        # Pack treeview and configure scrollbars
        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.config(command=self.results_tree.yview)
        hsb.config(command=self.results_tree.xview)
        
        # Configure row tags for alternating colors
        self.results_tree.tag_configure("odd", background=self.bg_medium)
        self.results_tree.tag_configure("even", background=self.bg_light)
        
        # Fill with initial data
        self._execute_query("SELECT * FROM invoices LIMIT 100")
        
        # Update summary cards
        self._update_summary_cards()
        
        # Add database tools frame at the bottom
        self.tools_frame = ttk.Frame(self.frame)
        self.tools_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=5)
        
        # Add Fix Data Types button
        self.fix_types_button = ttk.Button(
            self.tools_frame, 
            text="Fix Data Types", 
            command=self._fix_data_types
        )
        self.fix_types_button.pack(side=tk.LEFT, padx=5)
    
    def _create_summary_cards(self, parent_frame):
        """Create dashboard-style summary cards with gradient backgrounds"""
        cards_frame = ttk.Frame(parent_frame)
        cards_frame.pack(fill=tk.X, padx=5, pady=10)
        
        # Define card colors - different gradient for each card
        card_styles = [
            {"from": "#303F9F", "to": "#1A237E", "title": "Total Amount", "id": "total"},
            {"from": "#00796B", "to": "#004D40", "title": "Paid Invoices", "id": "paid"},
            {"from": "#6A1B9A", "to": "#4A148C", "title": "Unpaid Invoices", "id": "unpaid"},
            {"from": "#C62828", "to": "#B71C1C", "title": "Overdue Invoices", "id": "overdue"}
        ]
        
        # Create a frame for each card
        self.card_canvases = {}
        self.card_values = {}
        
        for i, style in enumerate(card_styles):
            # Create card frame
            card = tk.Frame(cards_frame, width=200, height=120, background=style["from"])
            card.pack(side=tk.LEFT, padx=8, pady=5, expand=True, fill=tk.X)
            card.pack_propagate(False)  # Prevent the frame from shrinking
            
            # Draw gradient background
            canvas = tk.Canvas(card, background=style["from"], 
                              highlightthickness=0, bd=0)
            canvas.pack(fill=tk.BOTH, expand=True)
            
            # Create gradient effect
            for y in range(120):
                # Calculate color for gradient
                r1, g1, b1 = int(style["from"][1:3], 16), int(style["from"][3:5], 16), int(style["from"][5:7], 16)
                r2, g2, b2 = int(style["to"][1:3], 16), int(style["to"][3:5], 16), int(style["to"][5:7], 16)
                
                r = int(r1 + (r2-r1) * (y/120))
                g = int(g1 + (g2-g1) * (y/120))
                b = int(b1 + (b2-b1) * (y/120))
                
                color = f'#{r:02x}{g:02x}{b:02x}'
                canvas.create_line(0, y, 200, y, fill=color)
            
            # Add title
            canvas.create_text(15, 25, anchor='w', text=style["title"], 
                              fill="#FFFFFF", font=(self.font_family, 12, 'bold'))
            
            # Store canvas reference for value updates
            self.card_canvases[style["id"]] = canvas
            
            # Create initial value text item
            value_text = canvas.create_text(15, 70, anchor='w', text="$0", 
                                          fill="#FFFFFF", font=(self.font_family, 24, 'bold'))
            self.card_values[style["id"]] = value_text
        
        # Update summary cards with current data
        self._update_summary_cards()
    
    def _update_summary_cards(self):
        """Update the summary cards with latest data"""
        try:
            # Use date casting in queries to handle text dates
            # Get unpaid invoices total
            unpaid_query = "SELECT COALESCE(SUM(amount), 0) FROM invoices WHERE payment_status = 'Unpaid'"
            result = self.db_manager.db.execute_query(unpaid_query)
            if 'error' not in result or not result.get('error'):
                self.unpaid_value = result['rows'][0][0] or 0
            
            # Get paid invoices this month
            paid_query = """
            SELECT COALESCE(SUM(amount), 0) FROM invoices 
            WHERE payment_status = 'Paid' 
            AND EXTRACT(MONTH FROM invoice_date::DATE) = EXTRACT(MONTH FROM CURRENT_DATE)
            AND EXTRACT(YEAR FROM invoice_date::DATE) = EXTRACT(YEAR FROM CURRENT_DATE)
            """
            result = self.db_manager.db.execute_query(paid_query)
            if 'error' not in result or not result.get('error'):
                self.paid_value = result['rows'][0][0] or 0
            
            # Get overdue invoices
            overdue_query = """
            SELECT COALESCE(SUM(amount), 0) FROM invoices 
            WHERE payment_status = 'Unpaid' 
            AND due_date::DATE < CURRENT_DATE
            """
            result = self.db_manager.db.execute_query(overdue_query)
            if 'error' not in result or not result.get('error'):
                self.overdue_value = result['rows'][0][0] or 0
            
            # Get total outstanding
            total_query = """
            SELECT COALESCE(SUM(amount), 0) FROM invoices 
            WHERE payment_status = 'Unpaid'
            """
            result = self.db_manager.db.execute_query(total_query)
            if 'error' not in result or not result.get('error'):
                self.total_value = result['rows'][0][0] or 0
            
            # Update the card visuals
            if hasattr(self, 'card_values'):
                # Update card values if using canvas-based cards
                if "total" in self.card_values:
                    self.card_canvases["total"].itemconfig(
                        self.card_values["total"], 
                        text=f"${self.total_value:,.2f}"
                    )
                
                if "paid" in self.card_values:
                    self.card_canvases["paid"].itemconfig(
                        self.card_values["paid"], 
                        text=f"${self.paid_value:,.2f}"
                    )
                
                if "unpaid" in self.card_values:
                    self.card_canvases["unpaid"].itemconfig(
                        self.card_values["unpaid"], 
                        text=f"${self.unpaid_value:,.2f}"
                    )
                
                if "overdue" in self.card_values:
                    self.card_canvases["overdue"].itemconfig(
                        self.card_values["overdue"], 
                        text=f"${self.overdue_value:,.2f}"
                    )
                
            logger.info("Updated summary cards with robust type handling")
                
        except Exception as e:
            logger.error(f"Error updating summary cards: {str(e)}")
            self.status_var.set(f"Error updating dashboard: {str(e)}")
            
    def _execute_llm_search(self):
        """Execute a search using natural language query with loading animation"""
        query_text = self.search_var.get().strip()
        if not query_text:
            messagebox.showinfo("Search", "Please enter a search query")
            return
        
        # Clear previous results
        self._clear_results()
        
        # Show loading animation
        loading_window = self._show_loading_animation()
        
        try:
            # Process in a separate thread to keep UI responsive
            def process_query():
                try:
                    # Convert natural language to SQL
                    sql_query = self._natural_language_to_sql(query_text)
                    
                    # Execute the generated SQL
                    result = self.db_manager.db.execute_query(sql_query)
                    
                    # Update UI in the main thread
                    self.window.after(0, lambda: self._display_results(sql_query, result))
                    self.window.after(100, loading_window.destroy)
                    self.window.after(0, lambda: self.status_var.set("Search completed"))
                except Exception as e:
                    error_msg = str(e)
                    self.window.after(0, lambda: self._display_error(error_msg))
                    self.window.after(100, loading_window.destroy)
            
            # Start processing thread
            threading.Thread(target=process_query, daemon=True).start()
            
        except Exception as e:
            loading_window.destroy()
            self._display_error(str(e))
    
    def _clear_results(self):
        """Clear previous search results"""
        # Clear SQL display
        self.sql_display.delete(1.0, tk.END)
        
        # Clear treeview
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
    
    def _show_loading_animation(self):
        """Display a loading animation when processing queries"""
        self.status_var.set("Processing query...")
        loading_window = tk.Toplevel(self.window)
        loading_window.title("Processing")
        loading_window.geometry("300x100")
        loading_window.configure(bg=self.bg_dark)
        loading_window.transient(self.window)
        loading_window.grab_set()
        
        # Configure loading window style
        loading_frame = ttk.Frame(loading_window)
        loading_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        loading_label = ttk.Label(loading_frame, text="Generating SQL and fetching results...",
                                font=(self.font_family, 10))
        loading_label.pack(pady=(0, 15))
        
        # Progress bar with accent color
        self.style.configure("Accent.Horizontal.TProgressbar", 
                            background=self.accent_color)
        progress = ttk.Progressbar(loading_frame, style="Accent.Horizontal.TProgressbar", 
                                 mode="indeterminate", length=250)
        progress.pack()
        progress.start(10)
        
        # Update the display while processing
        loading_window.update()
        return loading_window
    
    def _display_results(self, sql_query, result):
        """Display the query results in the UI
        
        Args:
            sql_query: The executed SQL query
            result: The query results
        """
        # Display the SQL query
        self.sql_display.delete(1.0, tk.END)
        self.sql_display.insert(tk.END, sql_query)
        
        # Check for errors
        if 'error' in result and result['error']:
            self._display_error(result['error'])
            return
        
        # Check if we have results
        if 'rows' not in result or not result['rows']:
            self.status_var.set("No results found")
            return
        
        # Get column names
        columns = result.get('columns', [])
        
        # Display results in treeview
        for i, row in enumerate(result['rows']):
            values = []
            
            # Process each column
            for idx, value in enumerate(row):
                # Format dates
                if isinstance(value, datetime.date):
                    values.append(value.strftime('%Y-%m-%d'))
                # Format amounts - assume column index 2 is amount
                elif isinstance(value, (int, float)) and idx == 2:
                    values.append(f"${value:,.2f}")
                # Handle None values
                elif value is None:
                    values.append("")
                # Default handling
                else:
                    values.append(str(value))
            
            # Add to treeview with alternating row colors
            tag = "even" if i % 2 == 0 else "odd"
            self.results_tree.insert('', tk.END, values=values, tags=(tag,))
        
        # Update status
        self.status_var.set(f"Found {len(result['rows'])} results")
    
    def _display_error(self, error_message):
        """Display an error message in the UI
        
        Args:
            error_message: The error message to display
        """
        self.status_var.set(f"Error: {error_message}")
        
        # Display error in SQL area with highlighting
        self.sql_display.delete(1.0, tk.END)
        self.sql_display.insert(tk.END, "-- ERROR: ")
        self.sql_display.insert(tk.END, error_message)
        
        # Log the error
        logger.error(f"Search error: {error_message}")
    
    def _natural_language_to_sql(self, query_text):
        """Convert natural language query to SQL using LLM
        
        Args:
            query_text: The natural language query
            
        Returns:
            str: The generated SQL query
        """
        if not self.llm_client:
            # Fallback if no LLM client is provided
            return self._keyword_search_to_sql(query_text)
        
        # Prepare the database schema information for context
        schema_info = """
        Table: invoices
        Columns:
        - invoice_number (TEXT or VARCHAR): The unique identifier for each invoice
        - vendor (TEXT or VARCHAR): The company or individual who issued the invoice
        - invoice_date (DATE): The date the invoice was issued
        - due_date (DATE): The date payment is due
        - amount (DECIMAL): The total amount of the invoice
        - payment_status (TEXT or VARCHAR): Current status ('Paid', 'Unpaid', etc.)
        - fund_paid_by (TEXT or VARCHAR): The fund used to pay the invoice
        """
        
        # Create a prompt for the LLM
        prompt = f"""
        You are an AI assistant that translates natural language queries into PostgreSQL queries.
        
        {schema_info}
        
        Convert this natural language query to a valid PostgreSQL query:
        "{query_text}"
        
        Important:
        1. Only return the SQL query, nothing else.
        2. Format dates as YYYY-MM-DD in the query.
        3. Use CAST or :: for date conversions when comparing dates.
        4. Add proper error handling for text-to-date conversions.
        5. Handle potential case sensitivity in text comparisons using LOWER() function.
        
        Example: For "show unpaid invoices due last month", you might return:
        SELECT * FROM invoices 
        WHERE LOWER(payment_status) = 'unpaid' 
        AND due_date::DATE BETWEEN 
            (DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month')::DATE 
            AND (DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 day')::DATE
        """
        
        try:
            # Call the LLM API
            response = self.llm_client.generate_text(prompt)
            
            # Extract SQL from response and clean it up
            sql_query = response.strip()
            
            # Remove any markdown code blocks
            if sql_query.startswith("```") and sql_query.endswith("```"):
                sql_query = sql_query[3:-3].strip()
            
            # Remove SQL/PostgreSQL prefix if present
            for prefix in ["sql", "SQL", "postgresql", "PostgreSQL"]:
                if sql_query.startswith(prefix + "\n"):
                    sql_query = sql_query[len(prefix) + 1:].strip()
            
            # Safety validation - ensure it only accesses our tables
            allowed_tables = ['invoices', 'vendors', 'funds']
            table_found = False
            
            for table in allowed_tables:
                if table in sql_query.lower():
                    table_found = True
                    break
                    
            if not table_found:
                raise ValueError("Generated SQL does not reference any valid tables")
                
            # Basic SQL injection prevention
            if ";" in sql_query and not sql_query.strip().endswith(";"):
                # Multiple statements detected
                raise ValueError("Multiple SQL statements are not allowed")
                
            logger.info(f"Generated SQL query: {sql_query}")
            
            # Ensure there's a LIMIT clause
            if "LIMIT" not in sql_query.upper():
                sql_query = sql_query.rstrip(";") + " LIMIT 100;"
            
            return sql_query
            
        except Exception as e:
            logger.error(f"LLM API error: {str(e)}")
            raise Exception(f"LLM API error: {str(e)}")
    
    def _keyword_search_to_sql(self, query_text):
        """Fallback method to convert keywords to SQL without using LLM"""
        # A simple keyword-based approach when LLM is not available
        query_lower = query_text.lower()
        
        # Basic pattern matching
        if "unpaid" in query_lower:
            return "SELECT * FROM invoices WHERE LOWER(payment_status) = 'unpaid' LIMIT 100"
        elif "paid" in query_lower:
            return "SELECT * FROM invoices WHERE LOWER(payment_status) = 'paid' LIMIT 100"
        elif "overdue" in query_lower:
            return "SELECT * FROM invoices WHERE LOWER(payment_status) = 'unpaid' AND due_date::DATE < CURRENT_DATE LIMIT 100"
        elif "this month" in query_lower:
            return """
            SELECT * FROM invoices 
            WHERE EXTRACT(MONTH FROM invoice_date::DATE) = EXTRACT(MONTH FROM CURRENT_DATE)
            AND EXTRACT(YEAR FROM invoice_date::DATE) = EXTRACT(YEAR FROM CURRENT_DATE)
            LIMIT 100
            """
        else:
            # Default search - look for match in vendor or invoice number
            return f"""
            SELECT * FROM invoices 
            WHERE LOWER(vendor) LIKE LOWER('%{query_text}%')
            OR LOWER(invoice_number) LIKE LOWER('%{query_text}%')
            LIMIT 100
            """
    
    def _execute_query(self, sql_query):
        """Execute an SQL query and display the results
        
        Args:
            sql_query: The SQL query to execute
        """
        try:
            # Clear existing results
            for row in self.results_tree.get_children():
                self.results_tree.delete(row)
            
            # Execute the query
            result = self.db_manager.execute_query(sql_query)
            
            if 'error' in result and result['error']:
                raise Exception(result['error'])
            
            # No rows
            if 'rows' not in result or not result['rows']:
                self.status_var.set("No results found")
                return
            
            # Get column names
            columns = [col.lower() for col in result['columns']]
            
            # Add rows to treeview
            row_count = 0
            for row in result['rows']:
                values = []
                
                # Process each column
                for idx, value in enumerate(row):
                    # Format dates
                    if isinstance(value, datetime.date):
                        value = value.strftime('%Y-%m-%d')
                    
                    # Format amounts
                    if columns[idx] == 'amount' and isinstance(value, (int, float)):
                        value = f"${value:,.2f}"
                    
                    values.append(value if value is not None else "")
                
                # Add to treeview with alternating row colors
                tag = "even" if row_count % 2 == 0 else "odd"
                item_id = self.results_tree.insert("", tk.END, values=values, tags=(tag,))
                row_count += 1
            
            # Configure row tags for alternating colors
            self.results_tree.tag_configure("odd", background=self.bg_medium)
            self.results_tree.tag_configure("even", background=self.bg_light)
            
            # Update status
            self.status_var.set(f"Found {row_count} results")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Query execution error: {error_msg}")
            self.status_var.set(f"Error: {error_msg}")
            raise Exception(f"Failed to execute query: {error_msg}")
    
    def _show_search_suggestions(self):
        """Show a dialog with search query suggestions"""
        suggestions = [
            "Show all unpaid invoices",
            "Find invoices due this month",
            "Show invoices from vendor 'Acme Corp'",
            "List all invoices over $5000",
            "Show overdue invoices",
            "How many invoices were paid last month?",
            "What's the total amount of unpaid invoices?",
            "Show invoices paid from the General Fund",
            "Find invoices due in the next 7 days",
            "Which vendor has the most unpaid invoices?"
        ]
        
        # Create dialog with dark theme
        dialog = tk.Toplevel(self.window)
        dialog.title("Search Suggestions")
        dialog.geometry("500x400")
        dialog.transient(self.window)
        dialog.grab_set()
        dialog.configure(background=self.bg_dark)
        
        # Create frame
        frame = ttk.Frame(dialog, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Add heading
        ttk.Label(frame, text="Try these example searches:", 
                font=(self.font_family, 12, 'bold')).pack(pady=(0, 10))
        
        # Create listbox with suggestions
        listbox = tk.Listbox(frame, height=15, font=(self.font_family, 11),
                           background=self.bg_light, foreground=self.text_color,
                           selectbackground=self.accent_color, selectforeground="white",
                           borderwidth=0, highlightthickness=1,
                           highlightbackground=self.bg_medium, highlightcolor=self.accent_color)
        listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Add suggestions to listbox
        for suggestion in suggestions:
            listbox.insert(tk.END, suggestion)
        
        # Function to use selected suggestion
        def use_suggestion():
            selection = listbox.curselection()
            if selection:
                # Get selected suggestion
                suggestion = listbox.get(selection[0])
                
                # Close dialog
                dialog.destroy()
                
                # Set search text and execute
                self.search_var.set(suggestion)
                self._execute_llm_search()
        
        # Add buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(btn_frame, text="Use Selected", style='Accent.TButton',
                 command=use_suggestion).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Close", command=dialog.destroy).pack(side=tk.RIGHT)
        
        # Double-click to select
        listbox.bind("<Double-1>", lambda e: use_suggestion())
        
        # Select first item by default
        if listbox.size() > 0:
            listbox.selection_set(0)
    
    def show(self):
        """Show the dashboard"""
        if not self.window:
            return
            
        # Update UI
        self._update_summary_cards()
        
        # Show window
        self.window.lift()
        self.window.focus_force()

    def show_schema_inspector(self):
        """Show database schema inspector dialog with dark theme styling"""
        # Create inspector window
        inspector = tk.Toplevel(self.window)
        inspector.title("Database Schema Inspector")
        inspector.geometry("600x450")
        inspector.configure(background=self.bg_dark)
        inspector.transient(self.window)
        
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
        
        # Create a tab for each table
        for table_row in result['rows']:
            table_name = table_row[0]
            
            # Create tab
            tab = ttk.Frame(notebook)
            notebook.add(tab, text=table_name)
            
            # Get table columns
            columns_query = """
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = %s
            ORDER BY ordinal_position
            """
            result = self.db_manager.db.execute_query(columns_query, (table_name,))
            
            if 'error' in result and result['error']:
                ttk.Label(tab, text=f"Error: {result['error']}").pack()
                continue
            
            # Create treeview for columns
            columns_tree = ttk.Treeview(tab, columns=("name", "type", "nullable"), show="headings")
            columns_tree.heading("name", text="Column Name")
            columns_tree.heading("type", text="Data Type")
            columns_tree.heading("nullable", text="Nullable")
            
            columns_tree.column("name", width=150)
            columns_tree.column("type", width=150)
            columns_tree.column("nullable", width=100)
            
            columns_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Add scrollbar
            scrollbar = ttk.Scrollbar(columns_tree, orient=tk.VERTICAL, command=columns_tree.yview)
            columns_tree.configure(yscrollcommand=scrollbar.set)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Add columns data
            for i, col_row in enumerate(result['rows']):
                # Alternate row colors
                tag = "even" if i % 2 == 0 else "odd"
                columns_tree.insert('', tk.END, values=(col_row[0], col_row[1], col_row[2]), tags=(tag,))
            
            # Configure row colors
            columns_tree.tag_configure("odd", background=self.bg_medium)
            columns_tree.tag_configure("even", background=self.bg_light)
            
            # Add fix schema button
            button_frame = ttk.Frame(tab)
            button_frame.pack(fill=tk.X, pady=10)
            
            fix_button = ttk.Button(button_frame, text="Fix Schema Types", style="Accent.TButton",
                                  command=lambda t=table_name: self._fix_table_schema(t, inspector))
            fix_button.pack(side=tk.RIGHT, padx=5)
            
            analyze_button = ttk.Button(button_frame, text="Analyze Data", 
                                     command=lambda t=table_name: self._analyze_table_data(t, inspector))
            analyze_button.pack(side=tk.RIGHT, padx=5)
        
        # Center the window
        inspector.update_idletasks()
        width = inspector.winfo_width()
        height = inspector.winfo_height()
        x = (inspector.winfo_screenwidth() // 2) - (width // 2)
        y = (inspector.winfo_screenheight() // 2) - (height // 2)
        inspector.geometry('{}x{}+{}+{}'.format(width, height, x, y))
    
    def _fix_table_schema(self, table_name, parent_window):
        """Fix schema issues for a specific table
        
        Args:
            table_name: The name of the table to fix
            parent_window: The parent window for message boxes
        """
        try:
            # Ensure schema validator is available
            if not hasattr(self.db_manager, 'schema_validator') or self.db_manager.schema_validator is None:
                from finance_assistant.schema_validator import SchemaValidator
                self.db_manager.schema_validator = SchemaValidator(self.db_manager)
            
            # Start with a loading indicator
            self.status_var.set(f"Fixing schema for {table_name}...")
            parent_window.update()
            
            # Check and fix table schema
            result = self.db_manager.schema_validator.validate_table_schema(table_name, auto_fix=True)
            
            # Show result message
            if result['valid']:
                messagebox.showinfo("Schema Fix", f"Schema for {table_name} is now valid", parent=parent_window)
            else:
                messagebox.showwarning("Schema Fix", 
                                     f"Could not fix all issues with {table_name}. See logs for details.", 
                                     parent=parent_window)
                
            # Update status
            self.status_var.set("Ready")
                
        except Exception as e:
            messagebox.showerror("Error", f"Error fixing schema: {str(e)}", parent=parent_window)
            self.status_var.set("Error fixing schema")
    
    def _analyze_table_data(self, table_name, parent_window):
        """Analyze data in a table for potential issues
        
        Args:
            table_name: The name of the table to analyze
            parent_window: The parent window for message boxes
        """
        try:
            # Show analysis window
            analysis_window = tk.Toplevel(parent_window)
            analysis_window.title(f"Data Analysis: {table_name}")
            analysis_window.geometry("600x400")
            analysis_window.configure(background=self.bg_dark)
            analysis_window.transient(parent_window)
            
            # Create frame
            frame = ttk.Frame(analysis_window, padding="10")
            frame.pack(fill=tk.BOTH, expand=True)
            
            # Add header
            ttk.Label(frame, text=f"Data Analysis for {table_name}", 
                    font=(self.font_family, 14, 'bold')).pack(pady=(0, 15))
            
            # Create text widget for results
            results_text = tk.Text(frame, height=20, width=70, 
                                 bg=self.bg_light, fg=self.text_color,
                                 font=(self.font_family, 10))
            results_text.pack(fill=tk.BOTH, expand=True, pady=5)
            
            # Add scrollbar
            scrollbar = ttk.Scrollbar(results_text, orient=tk.VERTICAL, command=results_text.yview)
            results_text.configure(yscrollcommand=scrollbar.set)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Function to add text
            def add_text(text):
                results_text.insert(tk.END, text + "\n")
            
            # Get column info
            add_text(f"Analyzing table: {table_name}\n")
            
            columns_query = """
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = %s
            ORDER BY ordinal_position
            """
            columns_result = self.db_manager.db.execute_query(columns_query, (table_name,))
            
            if 'error' in columns_result and columns_result['error']:
                add_text(f"Error getting columns: {columns_result['error']}")
                return
            
            # Analyze each column
            for col_row in columns_result['rows']:
                col_name = col_row[0]
                data_type = col_row[1]
                
                add_text(f"\nColumn: {col_name} ({data_type})")
                
                # Count nulls
                null_query = f"SELECT COUNT(*) FROM {table_name} WHERE {col_name} IS NULL"
                null_result = self.db_manager.db.execute_query(null_query)
                
                if 'error' not in null_result or not null_result.get('error'):
                    null_count = null_result['rows'][0][0]
                    add_text(f"  - NULL values: {null_count}")
                
                # For text columns that should be dates
                if data_type.lower() in ('text', 'varchar', 'character varying') and 'date' in col_name.lower():
                    date_format_query = f"""
                    SELECT COUNT(*) FROM {table_name} 
                    WHERE {col_name} IS NOT NULL AND {col_name} !~ '^\d{{4}}-\d{{2}}-\d{{2}}$'
                    """
                    format_result = self.db_manager.db.execute_query(date_format_query)
                    
                    if 'error' not in format_result or not format_result.get('error'):
                        invalid_date_count = format_result['rows'][0][0]
                        if invalid_date_count > 0:
                            add_text(f"  - WARNING: {invalid_date_count} rows have invalid date formats")
                            add_text(f"  - Suggested fix: Convert {col_name} to DATE type")
                
                # For numeric columns
                if data_type.lower() in ('text', 'varchar', 'character varying') and ('amount' in col_name.lower() or 'price' in col_name.lower()):
                    numeric_query = f"""
                    SELECT COUNT(*) FROM {table_name} 
                    WHERE {col_name} IS NOT NULL AND {col_name} !~ '^[0-9.]+$'
                    """
                    numeric_result = self.db_manager.db.execute_query(numeric_query)
                    
                    if 'error' not in numeric_result or not numeric_result.get('error'):
                        invalid_numeric_count = numeric_result['rows'][0][0]
                        if invalid_numeric_count > 0:
                            add_text(f"  - WARNING: {invalid_numeric_count} rows have non-numeric values")
                            add_text(f"  - Suggested fix: Convert {col_name} to NUMERIC type")
            
            # Add close button
            ttk.Button(frame, text="Close", command=analysis_window.destroy, 
                     style="Accent.TButton").pack(pady=10)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error analyzing table data: {str(e)}", parent=parent_window)
    
    def _show_schema_tools_menu(self, event=None):
        """Show popup menu with schema tools"""
        menu = tk.Menu(self.window, tearoff=0, bg=self.bg_medium, fg=self.text_color,
                     activebackground=self.accent_color, activeforeground='white')
        
        menu.add_command(label="Schema Inspector", command=self.show_schema_inspector)
        menu.add_command(label="Fix Schema Issues", command=self._fix_all_schemas)
        menu.add_command(label="Analyze Data Types", command=self._analyze_all_tables)
        menu.add_separator()
        menu.add_command(label="Refresh Dashboard", command=self._refresh_dashboard)
        
        # Get the widget that triggered this
        if event:
            x, y = event.x_root, event.y_root
        else:
            # Position near the tools button if no event
            x = self.window.winfo_rootx() + 400
            y = self.window.winfo_rooty() + 150
        
        menu.tk_popup(x, y)
    
    def _fix_all_schemas(self):
        """Fix schema issues in all tables"""
        try:
            # Ensure schema validator is available
            if not hasattr(self.db_manager, 'schema_validator') or self.db_manager.schema_validator is None:
                from finance_assistant.schema_validator import SchemaValidator
                self.db_manager.schema_validator = SchemaValidator(self.db_manager)
            
            # Get list of tables
            tables_query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            result = self.db_manager.db.execute_query(tables_query)
            
            if 'error' in result and result['error']:
                messagebox.showerror("Error", f"Error getting tables: {result['error']}")
                return
            
            # Show progress dialog
            progress_window = tk.Toplevel(self.window)
            progress_window.title("Schema Fix Progress")
            progress_window.geometry("450x300")
            progress_window.configure(background=self.bg_dark)
            progress_window.transient(self.window)
            progress_window.grab_set()
            
            # Create frame
            frame = ttk.Frame(progress_window, padding="15")
            frame.pack(fill=tk.BOTH, expand=True)
            
            # Add header
            ttk.Label(frame, text="Schema Correction Progress", 
                    font=(self.font_family, 14, 'bold')).pack(pady=(0, 15))
            
            # Create text widget for progress
            progress_text = tk.Text(frame, height=10, width=50, 
                                  bg=self.bg_light, fg=self.text_color,
                                  font=(self.font_family, 10))
            progress_text.pack(fill=tk.BOTH, expand=True, pady=5)
            
            # Add scrollbar
            scrollbar = ttk.Scrollbar(progress_text, orient=tk.VERTICAL, command=progress_text.yview)
            progress_text.configure(yscrollcommand=scrollbar.set)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Function to add text
            def add_text(text):
                progress_text.insert(tk.END, text + "\n")
                progress_text.see(tk.END)
                progress_window.update()
            
            # Fix schemas
            add_text("Starting schema validation and correction...")
            tables_fixed = 0
            issues_found = 0
            
            for table_row in result['rows']:
                table_name = table_row[0]
                add_text(f"\nChecking table: {table_name}")
                
                # Validate table schema
                schema_result = self.db_manager.schema_validator.validate_table_schema(table_name, auto_fix=True)
                
                if schema_result['valid']:
                    add_text(f"✓ {table_name}: Schema is valid")
                else:
                    add_text(f"⚠ {table_name}: Schema issues found and fixed")
                    issues_found += 1
                
                tables_fixed += 1
                progress_window.update()
            
            # Add close button
            ttk.Button(frame, text="Close", command=progress_window.destroy,
                     style="Accent.TButton").pack(pady=(15, 0))
            
            # Show summary
            add_text(f"\nValidation complete. Checked {tables_fixed} tables, found and fixed issues in {issues_found} tables.")
            
            # Update dashboard data
            self._refresh_dashboard()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error fixing schemas: {str(e)}")
    
    def _analyze_all_tables(self):
        """Analyze all tables for data type issues"""
        # Similar to _fix_all_schemas but just analyzes and reports
        try:
            # Get list of tables
            tables_query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            result = self.db_manager.db.execute_query(tables_query)
            
            if 'error' in result and result['error']:
                messagebox.showerror("Error", f"Error getting tables: {result['error']}")
                return
            
            # Show analysis window
            analysis_window = tk.Toplevel(self.window)
            analysis_window.title("Data Type Analysis")
            analysis_window.geometry("600x400")
            analysis_window.configure(background=self.bg_dark)
            analysis_window.transient(self.window)
            
            # Create frame
            frame = ttk.Frame(analysis_window, padding="15")
            frame.pack(fill=tk.BOTH, expand=True)
            
            # Add header
            ttk.Label(frame, text="Database Type Analysis", 
                    font=(self.font_family, 14, 'bold')).pack(pady=(0, 15))
            
            # Create text widget for results
            results_text = tk.Text(frame, height=20, width=70, 
                                 bg=self.bg_light, fg=self.text_color,
                                 font=(self.font_family, 10))
            results_text.pack(fill=tk.BOTH, expand=True, pady=5)
            
            # Add scrollbar
            scrollbar = ttk.Scrollbar(results_text, orient=tk.VERTICAL, command=results_text.yview)
            results_text.configure(yscrollcommand=scrollbar.set)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Function to add text
            def add_text(text):
                results_text.insert(tk.END, text + "\n")
                results_text.see(tk.END)
                analysis_window.update()
            
            add_text("Analyzing database schema and types...\n")
            issues_found = 0
            
            for table_row in result['rows']:
                table_name = table_row[0]
                add_text(f"Table: {table_name}")
                
                # Get columns
                columns_query = """
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = %s
                AND (data_type LIKE 'character%' OR data_type = 'text')
                AND (column_name LIKE '%date%' OR column_name LIKE '%amount%')
                """
                columns_result = self.db_manager.db.execute_query(columns_query, (table_name,))
                
                table_issues = 0
                if 'rows' in columns_result and columns_result['rows']:
                    for col_row in columns_result['rows']:
                        col_name = col_row[0]
                        data_type = col_row[1]
                        
                        # Check for date columns as text
                        if 'date' in col_name.lower():
                            add_text(f"  - Column '{col_name}' has type {data_type} but might be a DATE")
                            table_issues += 1
                            issues_found += 1
                        
                        # Check for amount columns as text
                        if 'amount' in col_name.lower() or 'price' in col_name.lower():
                            add_text(f"  - Column '{col_name}' has type {data_type} but might be NUMERIC")
                            table_issues += 1
                            issues_found += 1
                
                if table_issues == 0:
                    add_text("  ✓ No obvious type issues detected")
                add_text("")
            
            # Add summary
            if issues_found > 0:
                add_text(f"\nFound {issues_found} potential data type issues across all tables.")
                add_text("Use 'Fix Schema Issues' to automatically correct these issues.")
            else:
                add_text("\nNo obvious data type issues found. Database schema appears to be consistent.")
            
            # Add buttons
            button_frame = ttk.Frame(frame)
            button_frame.pack(fill=tk.X, pady=(15, 0))
            
            ttk.Button(button_frame, text="Fix All Issues", style="Accent.TButton",
                     command=lambda: (analysis_window.destroy(), self._fix_all_schemas())).pack(side=tk.LEFT, padx=5)
            
            ttk.Button(button_frame, text="Close", 
                     command=analysis_window.destroy).pack(side=tk.RIGHT, padx=5)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error analyzing tables: {str(e)}")
    
    def _refresh_dashboard(self):
        """Refresh all dashboard data"""
        try:
            # Update summary cards
            self._update_summary_cards()
            
            # Refresh invoice data
            self._execute_query("SELECT * FROM invoices LIMIT 100")
            
            # Update status
            self.status_var.set("Dashboard refreshed")
            
        except Exception as e:
            logger.error(f"Error refreshing dashboard: {str(e)}")
            self.status_var.set(f"Error: {str(e)}")
    
    def _fix_data_types(self):
        """Fix data types in the database tables"""
        # Show confirmation dialog
        if not messagebox.askyesno(
            "Confirm", 
            "This will check and fix data type issues in all tables.\n\n"
            "The process will attempt to preserve all data, but backup is recommended.\n\n"
            "Do you want to continue?"
        ):
            return
        
        # Show the loading animation
        loading_window = self._show_loading_animation()
        self.window.update()
        
        try:
            # Create progress indicator
            progress_var = tk.StringVar(value="Starting...")
            progress_label = ttk.Label(loading_window, textvariable=progress_var)
            progress_label.pack(pady=10)
            
            # Run the operation in a separate thread
            def process_tables():
                try:
                    # Key tables to check
                    tables = ['invoices', 'vendors', 'funds']
                    fixed_tables = []
                    fixed_columns = []
                    
                    for table in tables:
                        # Update progress
                        progress_var.set(f"Checking {table} table...")
                        self.window.update_idletasks()
                        
                        # Run the type validation and fixing
                        result = self.db_manager.schema_validator.validate_and_fix_column_types(table)
                        
                        if result.get('fixed', False):
                            fixed_tables.append(table)
                            if 'fixed_columns' in result and result['fixed_columns']:
                                for col in result['fixed_columns']:
                                    fixed_columns.append(f"{table}.{col}")
                    
                    # Update UI with results
                    if fixed_tables:
                        message = f"Fixed data types in tables: {', '.join(fixed_tables)}"
                        if fixed_columns:
                            message += f"\n\nFixed columns: {', '.join(fixed_columns)}"
                        
                        self.window.after(0, lambda: self.status_var.set(message))
                        self.window.after(0, self._refresh_dashboard)
                        self.window.after(0, lambda: messagebox.showinfo("Success", message))
                    else:
                        self.window.after(0, lambda: self.status_var.set("All data types are correct, no fixes needed"))
                        self.window.after(0, lambda: messagebox.showinfo("Schema Check", "All data types are correct, no fixes needed"))
                    
                    # Close loading window
                    self.window.after(0, loading_window.destroy)
                    
                except Exception as e:
                    error_msg = str(e)
                    self.window.after(0, lambda: self.status_var.set(f"Error: {error_msg}"))
                    self.window.after(0, lambda: messagebox.showerror("Error", f"Error fixing data types: {error_msg}"))
                    self.window.after(0, loading_window.destroy)
            
            # Start thread
            threading.Thread(target=process_tables, daemon=True).start()
            
        except Exception as e:
            loading_window.destroy()
            self.status_var.set(f"Error fixing data types: {str(e)}")
            messagebox.showerror("Error", f"Error fixing data types: {str(e)}") 