import tkinter as tk
from tkinter import scrolledtext, ttk, Frame, Label, Button, Entry, messagebox
import re
from datetime import datetime

class UIManager:
    def __init__(self, app):
        self.app = app
        self.root = app.root
        
        # UI elements that need to be accessed by other components
        self.chat_area = None
        self.entry = None
        self.status_var = None
        self.connect_button = None
        self.demo_button = None
        self.export_button = None
        self.notebook = None
        self.chat_frame = None
        self.dashboard_frame = None
        self.visualization_frame = None
        self.ocr_frame = None
    
    def setup_ui(self):
        """Setup the user interface components"""
        # Create a frame for the header
        header_frame = tk.Frame(self.root, bg="#3a7ff6", height=50)
        header_frame.pack(fill=tk.X)
        
        # App title
        title_label = tk.Label(header_frame, text="Finance Database Assistant", 
                               font=("Arial", 16, "bold"), bg="#3a7ff6", fg="white")
        title_label.pack(side=tk.LEFT, padx=10, pady=10)
        
        # Database connection status
        self.status_var = tk.StringVar(value="Not Connected")
        self.status_label = tk.Label(header_frame, textvariable=self.status_var, 
                                     bg="#3a7ff6", fg="white", font=("Arial", 10))
        self.status_label.pack(side=tk.RIGHT, padx=10, pady=10)
        
        # Connect button
        self.connect_button = tk.Button(header_frame, text="Connect Database", 
                                       command=self.app.connect_database, bg="#2a5db0", fg="white",
                                       font=("Arial", 10), relief=tk.FLAT)
        self.connect_button.pack(side=tk.RIGHT, padx=10, pady=10)
        
        # Demo mode button
        self.demo_button = tk.Button(header_frame, text="Demo Mode", 
                                    command=self.app.enable_demo_mode, bg="#5a9f7a", fg="white",
                                    font=("Arial", 10), relief=tk.FLAT)
        self.demo_button.pack(side=tk.RIGHT, padx=10, pady=10)
        
        # CSV Import button
        self.import_button = tk.Button(header_frame, text="Import CSV", 
                                     command=self.show_import_dialog, bg="#ff9800", fg="white",
                                     font=("Arial", 10), relief=tk.FLAT)
        self.import_button.pack(side=tk.RIGHT, padx=10, pady=10)
        
        # Export button
        self.export_button = tk.Button(header_frame, text="Export to CSV", 
                                    command=self.app.export_to_csv, bg="#ff9800", fg="white",
                                    font=("Arial", 10), relief=tk.FLAT, state=tk.DISABLED)
        self.export_button.pack(side=tk.RIGHT, padx=10, pady=10)
        
        # Create a notebook with tabs for Chat, Dashboard, Visualization, and OCR
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Chat tab
        self.chat_frame = tk.Frame(self.notebook, bg="#f0f0f0")
        self.notebook.add(self.chat_frame, text="Chat")
        
        # Dashboard tab - Always visible
        self.dashboard_frame = tk.Frame(self.notebook, bg="#f0f0f0")
        self.notebook.add(self.dashboard_frame, text="Dashboard")
        
        # Visualization tab for query results
        self.visualization_frame = tk.Frame(self.notebook, bg="#f0f0f0")
        self.notebook.add(self.visualization_frame, text="Visualization")
        
        # OCR Integration tab
        self.ocr_frame = tk.Frame(self.notebook, bg="#f0f0f0")
        self.notebook.add(self.ocr_frame, text="OCR Scanner")
        
        # Only hide the visualization tab initially
        self.notebook.hide(2)
        
        # Setup UI in tabs
        self.setup_chat_ui()
        self.setup_ocr_tab()
        
        # Add a welcome message
        self.entry.focus_set()
        self.root.after(100, self.app.display_welcome_message)
        
        # Setup empty dashboard frame - will be populated by visualization manager
        empty_label = tk.Label(self.dashboard_frame, text="Connect to a database or enable Demo Mode to view dashboard", 
                             font=("Arial", 14), bg="#f0f0f0")
        empty_label.pack(expand=True)
    
    def setup_ocr_tab(self):
        """Setup the OCR scanner integration tab"""
        # Main frame with padding
        ocr_main_frame = tk.Frame(self.ocr_frame, bg="#f0f0f0", padx=20, pady=20)
        ocr_main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = tk.Label(ocr_main_frame, text="OCR Scanner Integration", 
                              font=("Arial", 16, "bold"), bg="#f0f0f0")
        title_label.pack(pady=(0, 20))
        
        # Description
        description = (
            "This tab integrates with the Invoice Viewer System to process scanned invoices.\n"
            "You can scan invoices and the system will extract data from them and add it to your database."
        )
        desc_label = tk.Label(ocr_main_frame, text=description, 
                             font=("Arial", 11), bg="#f0f0f0", justify=tk.LEFT)
        desc_label.pack(pady=(0, 20), anchor=tk.W)
        
        # Buttons frame
        buttons_frame = tk.Frame(ocr_main_frame, bg="#f0f0f0")
        buttons_frame.pack(pady=20)
        
        # Launch OCR Scanner button
        self.launch_ocr_btn = tk.Button(buttons_frame, text="Launch OCR Scanner", 
                                      command=self.app.launch_ocr_scanner,
                                      bg="#2a5db0", fg="white", font=("Arial", 12, "bold"),
                                      width=20, height=2, relief=tk.FLAT)
        self.launch_ocr_btn.pack(side=tk.LEFT, padx=10)
        
        # Import from OCR button
        self.import_ocr_btn = tk.Button(buttons_frame, text="Import OCR Data", 
                                       command=self.app.import_ocr_data,
                                       bg="#5a9f7a", fg="white", font=("Arial", 12, "bold"),
                                       width=20, height=2, relief=tk.FLAT)
        self.import_ocr_btn.pack(side=tk.LEFT, padx=10)
        
        # Status label for OCR operations
        self.ocr_status_var = tk.StringVar(value="Ready to scan invoices")
        self.ocr_status_label = tk.Label(ocr_main_frame, textvariable=self.ocr_status_var,
                                        font=("Arial", 11, "italic"), bg="#f0f0f0", fg="#666666")
        self.ocr_status_label.pack(pady=20)
    
    def setup_chat_ui(self):
        """Setup the chat interface components"""
        # Chat area
        self.chat_area = scrolledtext.ScrolledText(self.chat_frame, wrap=tk.WORD, 
                                                  state='disabled', 
                                                  font=("Arial", 11),
                                                  bg="white", fg="#333333",
                                                  height=20)
        self.chat_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Entry frame
        entry_frame = tk.Frame(self.chat_frame, bg="#f0f0f0")
        entry_frame.pack(fill=tk.X, pady=10)
        
        # Entry with larger font and nicer look
        self.entry = tk.Entry(entry_frame, font=("Arial", 12), bd=2, relief=tk.GROOVE)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.entry.bind("<Return>", self.app.send_message)
        
        # Send button with better styling
        self.send_button = tk.Button(entry_frame, text="Send", command=self.app.send_message,
                                    bg="#3a7ff6", fg="white", font=("Arial", 11, "bold"),
                                    width=10, relief=tk.FLAT)
        self.send_button.pack(side=tk.RIGHT, padx=5)
        
        # Dashboard button
        self.dashboard_button = tk.Button(entry_frame, text="Dashboard", 
                                     command=self.app.show_dashboard,
                                     bg="#5a9f7a", fg="white", font=("Arial", 11),
                                     width=10, relief=tk.FLAT)
        self.dashboard_button.pack(side=tk.RIGHT, padx=5)
        
        # Help button
        self.help_button = tk.Button(entry_frame, text="Help", command=self.app.show_help,
                                   bg="#5a9f7a", fg="white", font=("Arial", 11),
                                   width=10, relief=tk.FLAT)
        self.help_button.pack(side=tk.RIGHT, padx=5)
    
    def is_dashboard_request(self, text):
        """Check if the user is requesting the dashboard"""
        dashboard_patterns = [
            r'(show|display|visualize).*dashboard',
            r'(show|see).*overview',
            r'(go to|switch to|open).*dashboard'
        ]
        
        return any(re.search(pattern, text.lower()) for pattern in dashboard_patterns)
    
    def is_visualization_request(self, text):
        """Check if the user is requesting visualization"""
        viz_patterns = [
            r'(show|display|visualize|plot|graph|chart).*',
            r'(show|make|create).*graph.*',
            r'.*visual(ly|ize).*'
        ]
        
        return any(re.search(pattern, text.lower()) for pattern in viz_patterns)
        
    def is_ocr_request(self, text):
        """Check if the user is requesting OCR functionality"""
        ocr_patterns = [
            r'(scan|ocr).*invoice',
            r'(process|read).*document',
            r'(extract|get).*from.*invoice',
            r'(open|launch|run).*scanner'
        ]
        
        return any(re.search(pattern, text.lower()) for pattern in ocr_patterns)
    
    def display_message(self, sender, message):
        """Display a message in the chat area"""
        self.chat_area.configure(state='normal')
        
        # Add a bit of space between messages
        if self.chat_area.get("1.0", "end-1c"):
            self.chat_area.insert(tk.END, "\n\n")
            
        # Format sender with timestamp
        timestamp = datetime.now().strftime("%H:%M")
        
        if sender == "You":
            sender_text = f"You [{timestamp}]:"
            self.chat_area.insert(tk.END, sender_text + "\n", "user")
        elif sender == "Assistant":
            sender_text = f"Assistant [{timestamp}]:"
            self.chat_area.insert(tk.END, sender_text + "\n", "assistant")
        elif sender == "System":
            sender_text = f"System [{timestamp}]:"
            self.chat_area.insert(tk.END, sender_text + "\n", "system")
        elif sender == "Help":
            sender_text = f"Help [{timestamp}]:"
            self.chat_area.insert(tk.END, sender_text + "\n", "help")
        
        # Message content with indentation
        message_lines = message.split('\n')
        for i, line in enumerate(message_lines):
            if i > 0:
                self.chat_area.insert(tk.END, "\n")
            self.chat_area.insert(tk.END, f"  {line}")
            
        self.chat_area.configure(state='disabled')
        self.chat_area.yview(tk.END)
        
        # Configure tags for different senders
        self.chat_area.tag_configure("user", foreground="#0066cc", font=("Arial", 11, "bold"))
        self.chat_area.tag_configure("assistant", foreground="#006633", font=("Arial", 11, "bold"))
        self.chat_area.tag_configure("system", foreground="#cc3300", font=("Arial", 11, "bold"))
        self.chat_area.tag_configure("help", foreground="#9900cc", font=("Arial", 11, "bold"))
    
    def display_query_results(self, results, sql):
        """Format and display the query results in the chat area"""
        if 'error' in results:
            error_msg = results['error']
            if "Driver" in error_msg:
                self.display_message("Assistant", 
                    "Database connection lost. Please reconnect to the database.")
            else:
                self.display_message("Assistant", 
                    f"Error executing query: {error_msg}\n\nQuery was: {sql}")
            return
            
        columns = results['columns']
        rows = results['rows']
        
        if not rows:
            self.display_message("Assistant", "No results found for your query.")
            return
            
        # Format as ASCII table for simplicity
        # For large result sets, just show the count
        if len(rows) > 10:
            preview_rows = rows[:10]
            result_text = f"Found {len(rows)} results. Showing first 10:\n\n"
        else:
            preview_rows = rows
            result_text = f"Found {len(rows)} result(s):\n\n"
        
        # Get max width for each column for nice formatting
        col_widths = [len(str(col)) for col in columns]
        for row in preview_rows:
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(str(cell)))
        
        # Header
        header = " | ".join(str(col).ljust(col_widths[i]) for i, col in enumerate(columns))
        separator = "-" * len(header)
        result_text += header + "\n" + separator + "\n"
        
        # Rows
        for row in preview_rows:
            result_text += " | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row)) + "\n"
        
        self.display_message("Assistant", result_text)
    
    def show_help(self):
        """Display help information to the user"""
        help_text = (
            "Here are some examples of questions you can ask:\n\n"
            "Expenses:\n"
            "• 'Show expenses from January'\n"
            "• 'What are the expenses for last month?'\n"
            "• 'Total expenses this year'\n"
            "• 'How much did we spend last quarter?'\n\n"
            
            "Invoices:\n"
            "• 'Show unpaid invoices'\n"
            "• 'List outstanding bills'\n"
            "• 'Show invoices from March'\n\n"
            
            "Vendors:\n"
            "• 'Show all vendors'\n"
            "• 'List suppliers'\n\n"
            
            "Tables:\n"
            "• 'Show [table name]'\n"
            "• 'List contents of [table name]'\n\n"
            
            "Visualization:\n"
            "• 'Visualize expenses by category'\n"
            "• 'Show a chart of revenue by month'\n"
            "• 'Display unpaid invoices as a pie chart'\n\n"
            
            "Export:\n"
            "• 'Export this to CSV'\n"
            "• 'Save the results to a file'\n\n"
            
            "Import:\n"
            "• Click the 'Import CSV' button to import data from CSV files\n"
            "• You can map CSV columns to database columns\n"
            "• Data import handles NaN/NULL values automatically\n\n"
            
            "Dashboard:\n"
            "• 'Show me the dashboard'\n"
            "• 'Open financial overview'\n\n"
            
            "You can also try asking about specific columns or values."
        )
        self.display_message("Help", help_text)
    
    def show_dashboard(self):
        """Switch to the dashboard tab"""
        self.notebook.select(1)  # Switch to dashboard tab
        
    def show_ocr_tab(self):
        """Switch to the OCR scanner tab"""
        self.notebook.select(3)  # Switch to OCR tab
    
    def update_ocr_status(self, status_message):
        """Update the OCR status message"""
        self.ocr_status_var.set(status_message)
    
    def get_user_message(self):
        """Get the message text from the input field"""
        return self.entry.get()
    
    def clear_input(self):
        """Clear the input field"""
        self.entry.delete(0, tk.END)
    
    def show_dashboard_tab(self):
        """Switch to the dashboard tab"""
        self.notebook.select(1)  # Switch to dashboard tab
    
    def update_status(self, status_text):
        """Update the status bar text"""
        self.status_var.set(status_text)
        self.root.update_idletasks()
    
    def add_export_suggestion(self):
        """Add a button to export the current query results to CSV"""
        try:
            # Create a frame for the button
            button_frame = tk.Frame(self.chat_frame, bg="#f0f0f0")
            button_frame.pack(fill=tk.X, pady=5)
            
            # Add a label
            suggestion_label = tk.Label(
                button_frame,
                text="Want to save these results?",
                bg="#f0f0f0",
                fg="#555555",
                font=("Arial", 9, "italic")
            )
            suggestion_label.pack(side=tk.LEFT, padx=10)
            
            # Add the export button
            export_button = tk.Button(
                button_frame,
                text="Export to CSV",
                command=self.app.export_to_csv,
                bg="#5a9f7a",
                fg="white",
                relief=tk.GROOVE,
                padx=10
            )
            export_button.pack(side=tk.LEFT, padx=5)
            
            # Scroll to see the button
            self.chat_area.see(tk.END)
        except Exception as e:
            print(f"Error adding export suggestion: {str(e)}")
    
    def add_visualization_suggestion(self):
        """Add a button to visualize the current query results"""
        try:
            # Create a frame for the button
            button_frame = tk.Frame(self.chat_frame, bg="#f0f0f0")
            button_frame.pack(fill=tk.X, pady=5)
            
            # Add a label
            suggestion_label = tk.Label(
                button_frame,
                text="Want to visualize these results?",
                bg="#f0f0f0",
                fg="#555555",
                font=("Arial", 9, "italic")
            )
            suggestion_label.pack(side=tk.LEFT, padx=10)
            
            # Add the visualization button
            viz_button = tk.Button(
                button_frame,
                text="Show Visualization",
                command=self.app.show_dashboard,
                bg="#2a5db0",
                fg="white",
                relief=tk.GROOVE,
                padx=10
            )
            viz_button.pack(side=tk.LEFT, padx=5)
            
            # Scroll to see the button
            self.chat_area.see(tk.END)
        except Exception as e:
            print(f"Error adding visualization suggestion: {str(e)}")

    def show_import_dialog(self):
        """Show the import CSV dialog"""
        try:
            # Check if connected to database first
            if not self.app.database_manager.is_connected():
                messagebox.showwarning(
                    "Not Connected", 
                    "Please connect to a database before importing data."
                )
                return
                
            # Open the import dialog using the import manager
            self.app.import_manager.show_import_dialog()
        except Exception as e:
            print(f"Error showing import dialog: {str(e)}")
            messagebox.showerror("Error", f"Failed to open import dialog: {str(e)}")

    def display_thinking(self):
        """Display a thinking indicator in the chat area"""
        self.chat_area.configure(state='normal')
        
        # Add a bit of space between messages
        if self.chat_area.get("1.0", "end-1c"):
            self.chat_area.insert(tk.END, "\n\n")
            
        # Format sender with timestamp
        timestamp = datetime.now().strftime("%H:%M")
        sender_text = f"Assistant [{timestamp}]:"
        self.chat_area.insert(tk.END, sender_text + "\n", "assistant")
        
        # Add thinking indicator
        self.chat_area.insert(tk.END, "  Thinking...", "thinking")
        
        # Store the position for later removal
        self._thinking_position = self.chat_area.index(tk.INSERT)
        
        self.chat_area.configure(state='disabled')
        self.chat_area.yview(tk.END)
        
        # Configure thinking tag
        self.chat_area.tag_configure("thinking", foreground="#999999", font=("Arial", 11, "italic"))
        
        # Update UI immediately
        self.app.root.update()

    def remove_thinking(self):
        """Remove the thinking indicator"""
        if hasattr(self, '_thinking_position'):
            self.chat_area.configure(state='normal')
            
            # Delete from the start of "Thinking..." to the end of that line
            self.chat_area.delete(f"{self._thinking_position} linestart", f"{self._thinking_position} lineend")
            
            self.chat_area.configure(state='disabled')
            self.chat_area.yview(tk.END)
            
            # Update UI immediately
            self.app.root.update()

    def clear_chat(self):
        """Clear the chat area"""
        self.chat_area.configure(state='normal')
        self.chat_area.delete(1.0, tk.END)
        self.chat_area.configure(state='disabled')
        
        # Display welcome message
        self.app.display_welcome_message() 