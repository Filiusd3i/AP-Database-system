#!/usr/bin/env python3
"""
Data Management Dashboard Module

Provides a dashboard for viewing table details, statistics, and data management.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List, Optional
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np

class DataDashboard:
    """Data management dashboard with table details and statistics"""
    
    def __init__(self, parent: tk.Tk, db_manager):
        """Initialize the data dashboard
        
        Args:
            parent: Parent window
            db_manager: Database manager instance
        """
        self.parent = parent
        self.db_manager = db_manager
        self.current_table: Optional[str] = None
        
        # Create main window
        self.window = tk.Toplevel(parent)
        self.window.title("Data Management Dashboard")
        self.window.geometry("1200x800")
        
        # Create main layout
        self._create_layout()
        
    def _create_layout(self):
        """Create the main layout"""
        # Create main frame
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create left panel for table selection
        left_panel = ttk.Frame(main_frame)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        
        # Create header with label and refresh button
        header_frame = ttk.Frame(left_panel)
        header_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(header_frame, text="Tables").pack(side=tk.LEFT, anchor=tk.W)
        ttk.Button(header_frame, text="Refresh", command=self._refresh_tables).pack(side=tk.RIGHT)
        
        self.table_list = ttk.Treeview(left_panel, columns=("name",), show="headings")
        self.table_list.heading("name", text="Table Name")
        self.table_list.pack(fill=tk.BOTH, expand=True)
        
        # Add tables to list
        self._populate_tables()
            
        # Bind selection event
        self.table_list.bind('<<TreeviewSelect>>', self._on_table_select)
        
        # Create right panel for details
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create notebook for different views
        self.notebook = ttk.Notebook(right_panel)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create tabs
        self._create_overview_tab()
        self._create_data_tab()
        self._create_statistics_tab()
        
    def _populate_tables(self):
        """Populate the table list with tables from the database"""
        # Clear existing items
        for item in self.table_list.get_children():
            self.table_list.delete(item)
            
        # Add tables to list
        if hasattr(self.db_manager, 'tables') and self.db_manager.tables:
            for table in self.db_manager.tables:
                self.table_list.insert("", "end", values=(table,))
        else:
            messagebox.showinfo("No Tables", "No tables found in the database. If you've just connected, try clicking Refresh.")
            
    def _refresh_tables(self):
        """Refresh the table list"""
        # Fetch tables again
        if hasattr(self.db_manager, '_fetch_tables'):
            self.db_manager._fetch_tables()
            self._populate_tables()
        else:
            messagebox.showwarning("Not Supported", "The database manager doesn't support refreshing tables.")
            
    def _create_overview_tab(self):
        """Create the overview tab"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Overview")
        
        # Table information
        info_frame = ttk.LabelFrame(frame, text="Table Information")
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.info_text = tk.Text(info_frame, height=10)
        self.info_text.pack(fill=tk.X, padx=5, pady=5)
        
        # Column information
        col_frame = ttk.LabelFrame(frame, text="Columns")
        col_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.col_tree = ttk.Treeview(col_frame, columns=("name", "type", "nullable", "key"),
                                   show="headings")
        self.col_tree.heading("name", text="Name")
        self.col_tree.heading("type", text="Type")
        self.col_tree.heading("nullable", text="Nullable")
        self.col_tree.heading("key", text="Key")
        self.col_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
    def _create_data_tab(self):
        """Create the data tab"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Data")
        
        # Toolbar
        toolbar = ttk.Frame(frame)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="Refresh", command=self._refresh_data).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Add Row", command=self._add_row).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Edit Row", command=self._edit_row).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Delete Row", command=self._delete_row).pack(side=tk.LEFT, padx=2)
        
        # Data grid
        self.data_tree = ttk.Treeview(frame)
        self.data_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scrollbars
        y_scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.data_tree.yview)
        x_scroll = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=self.data_tree.xview)
        self.data_tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        
        y_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        x_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        
    def _create_statistics_tab(self):
        """Create the statistics tab"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Statistics")
        
        # Create matplotlib figure
        self.fig, self.ax = plt.subplots(figsize=(8, 6))
        self.canvas = FigureCanvasTkAgg(self.fig, master=frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
    def _on_table_select(self, event):
        """Handle table selection"""
        selection = self.table_list.selection()
        if not selection:
            return
            
        self.current_table = self.table_list.item(selection[0])['values'][0]
        self._update_overview()
        self._update_data()
        self._update_statistics()
        
    def _update_overview(self):
        """Update the overview tab"""
        if not self.current_table:
            return
            
        try:
            # Get table information
            result = self.db_manager.execute_query(
                f"SELECT COUNT(*) FROM {self.current_table}"
            )
            
            if "error" in result:
                messagebox.showerror("Error", f"Failed to get table info: {result['error']}")
                return
                
            row_count = result["rows"][0][0]
            
            # Update info text
            self.info_text.delete('1.0', tk.END)
            self.info_text.insert('1.0', f"Table: {self.current_table}\n")
            self.info_text.insert('end', f"Total Rows: {row_count}\n")
            
            # Get column information
            result = self.db_manager.execute_query(
                f"""
                SELECT column_name, data_type, is_nullable, 
                       CASE WHEN column_name IN (
                           SELECT column_name FROM information_schema.key_column_usage 
                           WHERE table_name = '{self.current_table}' 
                             AND constraint_name LIKE '%_pkey'
                       ) THEN 'PRI' ELSE '' END AS column_key
                FROM information_schema.columns
                WHERE table_name = '{self.current_table}'
                ORDER BY ordinal_position
                """
            )
            
            if "error" in result:
                messagebox.showerror("Error", f"Failed to get column info: {result['error']}")
                return
                
            # Clear existing columns
            for item in self.col_tree.get_children():
                self.col_tree.delete(item)
                
            # Add columns to tree
            for row in result["rows"]:
                self.col_tree.insert("", "end", values=row)
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update overview: {str(e)}")
            
    def _update_data(self):
        """Update the data tab"""
        if not self.current_table:
            return
            
        try:
            # Get column names
            result = self.db_manager.execute_query(
                f"""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = '{self.current_table}'
                ORDER BY ordinal_position
                """
            )
            
            if "error" in result:
                messagebox.showerror("Error", f"Failed to get column names: {result['error']}")
                return
                
            columns = [row[0] for row in result["rows"]]
            
            # Configure tree columns
            self.data_tree["columns"] = columns
            for col in columns:
                self.data_tree.heading(col, text=col)
                self.data_tree.column(col, width=100)
                
            # Get data
            result = self.db_manager.execute_query(
                f"SELECT * FROM {self.current_table} LIMIT 1000"
            )
            
            if "error" in result:
                messagebox.showerror("Error", f"Failed to get data: {result['error']}")
                return
                
            # Clear existing data
            for item in self.data_tree.get_children():
                self.data_tree.delete(item)
                
            # Add data to tree
            for row in result["rows"]:
                self.data_tree.insert("", "end", values=row)
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update data: {str(e)}")
            
    def _update_statistics(self):
        """Update the statistics tab"""
        if not self.current_table:
            return
            
        try:
            # Get numeric columns
            result = self.db_manager.execute_query(
                f"""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = '{self.current_table}'
                AND data_type IN ('integer', 'numeric', 'decimal', 'real', 'double precision')
                """
            )
            
            if "error" in result:
                messagebox.showerror("Error", f"Failed to get numeric columns: {result['error']}")
                return
                
            numeric_columns = [row[0] for row in result["rows"]]
            
            if not numeric_columns:
                self.ax.clear()
                self.ax.text(0.5, 0.5, "No numeric columns available",
                           ha='center', va='center')
                self.canvas.draw()
                return
                
            # Get statistics for first numeric column
            column = numeric_columns[0]
            result = self.db_manager.execute_query(
                f"""
                SELECT MIN({column}), MAX({column}), AVG({column})
                FROM {self.current_table}
                """
            )
            
            if "error" in result:
                messagebox.showerror("Error", f"Failed to get statistics: {result['error']}")
                return
                
            min_val, max_val, avg_val = result["rows"][0]
            
            # Create histogram
            result = self.db_manager.execute_query(
                f"SELECT {column} FROM {self.current_table}"
            )
            
            if "error" in result:
                messagebox.showerror("Error", f"Failed to get histogram data: {result['error']}")
                return
                
            values = [row[0] for row in result["rows"]]
            
            self.ax.clear()
            self.ax.hist(values, bins=50)
            self.ax.set_title(f"Distribution of {column}")
            self.ax.set_xlabel(column)
            self.ax.set_ylabel("Count")
            
            # Add statistics text
            stats_text = f"Min: {min_val:.2f}\nMax: {max_val:.2f}\nAvg: {avg_val:.2f}"
            self.ax.text(0.02, 0.98, stats_text,
                        transform=self.ax.transAxes,
                        verticalalignment='top',
                        bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
            
            self.canvas.draw()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update statistics: {str(e)}")
            
    def _refresh_data(self):
        """Refresh the data view"""
        self._update_data()
        
    def _add_row(self):
        """Add a new row to the table"""
        if not self.current_table:
            messagebox.showwarning("Warning", "Please select a table first")
            return
            
        dialog = tk.Toplevel(self.window)
        dialog.title("Add Row")
        dialog.geometry("400x600")
        
        frame = ttk.Frame(dialog, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Get column information
        result = self.db_manager.execute_query(
            f"""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = '{self.current_table}'
            ORDER BY ordinal_position
            """
        )
        
        if "error" in result:
            messagebox.showerror("Error", f"Failed to get column info: {result['error']}")
            dialog.destroy()
            return
            
        # Create entry fields
        entries = {}
        for col_name, data_type, is_nullable in result["rows"]:
            field_frame = ttk.Frame(frame)
            field_frame.pack(fill=tk.X, pady=2)
            
            ttk.Label(field_frame, text=f"{col_name}:").pack(side=tk.LEFT)
            
            if data_type in ('integer', 'numeric', 'decimal', 'real', 'double precision'):
                entry = ttk.Entry(field_frame)
            elif data_type == 'date':
                entry = ttk.Entry(field_frame)
            elif data_type == 'boolean':
                entry = ttk.Checkbutton(field_frame)
            else:
                entry = ttk.Entry(field_frame)
                
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            entries[col_name] = entry
            
        def save_row():
            """Save the new row"""
            try:
                # Build INSERT statement
                columns = []
                values = []
                
                for col_name, entry in entries.items():
                    if isinstance(entry, ttk.Entry):
                        value = entry.get()
                    elif isinstance(entry, ttk.Checkbutton):
                        value = entry.instate(['selected'])
                    else:
                        value = entry.get()
                        
                    if value or not is_nullable:
                        columns.append(col_name)
                        values.append(f"'{value}'" if isinstance(value, str) else str(value))
                        
                if not columns:
                    messagebox.showerror("Error", "No values provided")
                    return
                    
                sql = f"INSERT INTO {self.current_table} ({', '.join(columns)}) "
                sql += f"VALUES ({', '.join(values)})"
                
                result = self.db_manager.execute_query(sql)
                
                if "error" in result:
                    messagebox.showerror("Error", f"Failed to insert row: {result['error']}")
                    return
                    
                self._update_data()
                dialog.destroy()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save row: {str(e)}")
                
        ttk.Button(frame, text="Save", command=save_row).pack(fill=tk.X, pady=(10, 0))
        
    def _edit_row(self):
        """Edit the selected row"""
        if not self.current_table:
            messagebox.showwarning("Warning", "Please select a table first")
            return
            
        selection = self.data_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a row to edit")
            return
            
        dialog = tk.Toplevel(self.window)
        dialog.title("Edit Row")
        dialog.geometry("400x600")
        
        frame = ttk.Frame(dialog, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Get selected row values
        row_values = self.data_tree.item(selection[0])['values']
        
        # Get column information
        result = self.db_manager.execute_query(
            f"""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = '{self.current_table}'
            ORDER BY ordinal_position
            """
        )
        
        if "error" in result:
            messagebox.showerror("Error", f"Failed to get column info: {result['error']}")
            dialog.destroy()
            return
            
        # Create entry fields
        entries = {}
        for i, (col_name, data_type, is_nullable) in enumerate(result["rows"]):
            field_frame = ttk.Frame(frame)
            field_frame.pack(fill=tk.X, pady=2)
            
            ttk.Label(field_frame, text=f"{col_name}:").pack(side=tk.LEFT)
            
            if data_type in ('integer', 'numeric', 'decimal', 'real', 'double precision'):
                entry = ttk.Entry(field_frame)
                entry.insert(0, str(row_values[i]))
            elif data_type == 'date':
                entry = ttk.Entry(field_frame)
                entry.insert(0, str(row_values[i]))
            elif data_type == 'boolean':
                entry = ttk.Checkbutton(field_frame)
                entry.state(['selected'] if row_values[i] else [])
            else:
                entry = ttk.Entry(field_frame)
                entry.insert(0, str(row_values[i]))
                
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            entries[col_name] = entry
            
        def save_changes():
            """Save the changes"""
            try:
                # Build UPDATE statement
                set_clauses = []
                where_clauses = []
                
                for col_name, entry in entries.items():
                    if isinstance(entry, ttk.Entry):
                        value = entry.get()
                    elif isinstance(entry, ttk.Checkbutton):
                        value = entry.instate(['selected'])
                    else:
                        value = entry.get()
                        
                    if value or not is_nullable:
                        set_clauses.append(f"{col_name} = '{value}'" if isinstance(value, str)
                                         else f"{col_name} = {value}")
                        
                if not set_clauses:
                    messagebox.showerror("Error", "No changes made")
                    return
                    
                sql = f"UPDATE {self.current_table} SET {', '.join(set_clauses)}"
                
                result = self.db_manager.execute_query(sql)
                
                if "error" in result:
                    messagebox.showerror("Error", f"Failed to update row: {result['error']}")
                    return
                    
                self._update_data()
                dialog.destroy()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save changes: {str(e)}")
                
        ttk.Button(frame, text="Save", command=save_changes).pack(fill=tk.X, pady=(10, 0))
        
    def _delete_row(self):
        """Delete the selected row"""
        if not self.current_table:
            messagebox.showwarning("Warning", "Please select a table first")
            return
            
        selection = self.data_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a row to delete")
            return
            
        if not messagebox.askyesno("Confirm", "Are you sure you want to delete this row?"):
            return
            
        try:
            # Get primary key columns
            result = self.db_manager.execute_query(
                f"""
                SELECT column_name
                FROM information_schema.key_column_usage
                WHERE table_name = '{self.current_table}'
                AND constraint_name = 'PRIMARY'
                """
            )
            
            if "error" in result:
                messagebox.showerror("Error", f"Failed to get primary key: {result['error']}")
                return
                
            pk_columns = [row[0] for row in result["rows"]]
            
            if not pk_columns:
                messagebox.showerror("Error", "No primary key found")
                return
                
            # Get row values
            row_values = self.data_tree.item(selection[0])['values']
            
            # Build WHERE clause
            where_clauses = []
            for col_name in pk_columns:
                col_index = self.data_tree["columns"].index(col_name)
                value = row_values[col_index]
                where_clauses.append(f"{col_name} = '{value}'" if isinstance(value, str)
                                   else f"{col_name} = {value}")
                
            sql = f"DELETE FROM {self.current_table} WHERE {' AND '.join(where_clauses)}"
            
            result = self.db_manager.execute_query(sql)
            
            if "error" in result:
                messagebox.showerror("Error", f"Failed to delete row: {result['error']}")
                return
                
            self._update_data()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete row: {str(e)}")
            
    def show(self):
        """Show the dashboard window"""
        self.window.deiconify()
        self.window.lift()
        
        # If no tables are visible, try fetching them again
        if hasattr(self.db_manager, 'tables') and not self.db_manager.tables:
            self._refresh_tables() 