#!/usr/bin/env python3
"""
Visual Query Builder Module

Provides a drag-and-drop interface for building SQL queries
without writing raw SQL code.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List, Optional, Set

class QueryNode:
    """Represents a table or join in the query builder"""
    def __init__(self, name: str, x: int, y: int, is_table: bool = True):
        self.name = name
        self.x = x
        self.y = y
        self.is_table = is_table
        self.columns: List[str] = []
        self.selected_columns: Set[str] = set()
        self.join_conditions: List[Dict] = []
        
class QueryBuilder:
    """Visual query builder with drag-and-drop functionality"""
    
    def __init__(self, parent: tk.Tk, db_manager):
        """Initialize the query builder
        
        Args:
            parent: Parent window
            db_manager: Database manager instance
        """
        self.parent = parent
        self.db_manager = db_manager
        self.nodes: Dict[str, QueryNode] = {}
        self.selected_node: Optional[QueryNode] = None
        self.dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        
        # Create main window
        self.window = tk.Toplevel(parent)
        self.window.title("Query Builder")
        self.window.geometry("1200x800")
        
        # Create main layout
        self._create_layout()
        
        # Bind events
        self._bind_events()
        
    def _create_layout(self):
        """Create the main layout"""
        # Create main frame
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create toolbar
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="Add Table", command=self._add_table).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Add Join", command=self._add_join).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Add Filter", command=self._add_filter).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Generate SQL", command=self._generate_sql).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Execute Query", command=self._execute_query).pack(side=tk.LEFT, padx=2)
        
        # Create canvas for drawing
        self.canvas = tk.Canvas(main_frame, bg='white')
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create SQL preview
        sql_frame = ttk.LabelFrame(main_frame, text="SQL Preview")
        sql_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.sql_text = tk.Text(sql_frame, height=5)
        self.sql_text.pack(fill=tk.X, padx=5, pady=5)
        
    def _bind_events(self):
        """Bind canvas events"""
        self.canvas.bind('<Button-1>', self._on_canvas_click)
        self.canvas.bind('<B1-Motion>', self._on_canvas_drag)
        self.canvas.bind('<ButtonRelease-1>', self._on_canvas_release)
        
    def _add_table(self):
        """Add a table to the query"""
        dialog = tk.Toplevel(self.window)
        dialog.title("Add Table")
        dialog.geometry("300x400")
        
        frame = ttk.Frame(dialog, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Table selection
        ttk.Label(frame, text="Select Table:").pack(anchor=tk.W)
        table_var = tk.StringVar()
        table_combo = ttk.Combobox(frame, textvariable=table_var,
                                 values=self.db_manager.tables)
        table_combo.pack(fill=tk.X, pady=(0, 10))
        
        # Column selection
        ttk.Label(frame, text="Select Columns:").pack(anchor=tk.W)
        columns_frame = ttk.Frame(frame)
        columns_frame.pack(fill=tk.BOTH, expand=True)
        
        columns_list = ttk.Treeview(columns_frame, columns=("name",), show="headings")
        columns_list.heading("name", text="Column Name")
        columns_list.pack(fill=tk.BOTH, expand=True)
        
        def update_columns(*args):
            """Update column list when table is selected"""
            table = table_var.get()
            if not table:
                return
                
            # Clear existing columns
            for item in columns_list.get_children():
                columns_list.delete(item)
                
            # Get columns for selected table
            result = self.db_manager.execute_query(
                f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}'"
            )
            
            if "error" in result:
                messagebox.showerror("Error", f"Failed to get columns: {result['error']}")
                return
                
            # Add columns to list
            for row in result["rows"]:
                columns_list.insert("", "end", values=(row[0],))
                
        table_combo.bind('<<ComboboxSelected>>', update_columns)
        
        def save_table():
            """Save selected table and columns"""
            table = table_var.get()
            if not table:
                messagebox.showerror("Error", "Please select a table")
                return
                
            if table in self.nodes:
                messagebox.showerror("Error", "Table already added")
                return
                
            # Create new table node
            node = QueryNode(table, 100, 100)
            node.columns = [row[0] for row in columns_list.get_children()]
            node.selected_columns = {row[0] for row in columns_list.selection()}
            
            self.nodes[table] = node
            
            # Draw node on canvas
            self._draw_node(node)
            
            dialog.destroy()
        
        ttk.Button(frame, text="Add", command=save_table).pack(fill=tk.X, pady=(10, 0))
        
    def _draw_node(self, node: QueryNode):
        """Draw a node on the canvas"""
        # Draw node box
        x, y = node.x, node.y
        width, height = 200, 100
        
        # Draw main box
        color = 'lightblue' if node.is_table else 'lightgreen'
        self.canvas.create_rectangle(x, y, x + width, y + height, fill=color)
        
        # Draw node name
        self.canvas.create_text(x + width/2, y + 20, text=node.name, font=('Arial', 12, 'bold'))
        
        # Draw selected columns
        for i, col in enumerate(node.selected_columns):
            y_pos = y + 40 + i * 20
            self.canvas.create_text(x + 10, y_pos, text=col, anchor=tk.W)
            
        # Draw join conditions
        for i, join in enumerate(node.join_conditions):
            y_pos = y + 40 + (i + len(node.selected_columns)) * 20
            self.canvas.create_text(x + 10, y_pos, text=f"JOIN {join['condition']}", anchor=tk.W)
            
    def _on_canvas_click(self, event):
        """Handle canvas click event"""
        # Check if clicked on a node
        for node in self.nodes.values():
            if (node.x <= event.x <= node.x + 200 and 
                node.y <= event.y <= node.y + 100):
                self.selected_node = node
                self.dragging = True
                self.drag_start_x = event.x - node.x
                self.drag_start_y = event.y - node.y
                return
                
        self.selected_node = None
        
    def _on_canvas_drag(self, event):
        """Handle canvas drag event"""
        if self.dragging and self.selected_node:
            # Update node position
            self.selected_node.x = event.x - self.drag_start_x
            self.selected_node.y = event.y - self.drag_start_y
            
            # Redraw canvas
            self.canvas.delete('all')
            for node in self.nodes.values():
                self._draw_node(node)
                
    def _on_canvas_release(self, event):
        """Handle canvas release event"""
        self.dragging = False
        self.selected_node = None
        
    def _add_join(self):
        """Add a join between tables"""
        if not self.selected_node:
            messagebox.showwarning("Warning", "Please select a source table first")
            return
            
        dialog = tk.Toplevel(self.window)
        dialog.title("Add Join")
        dialog.geometry("400x300")
        
        frame = ttk.Frame(dialog, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Target table selection
        ttk.Label(frame, text="Target Table:").pack(anchor=tk.W)
        target_var = tk.StringVar()
        target_combo = ttk.Combobox(frame, textvariable=target_var,
                                  values=list(self.nodes.keys()))
        target_combo.pack(fill=tk.X, pady=(0, 10))
        
        # Join type
        ttk.Label(frame, text="Join Type:").pack(anchor=tk.W)
        type_var = tk.StringVar(value="INNER")
        type_combo = ttk.Combobox(frame, textvariable=type_var,
                                values=["INNER", "LEFT", "RIGHT", "FULL"])
        type_combo.pack(fill=tk.X, pady=(0, 10))
        
        # Join condition
        ttk.Label(frame, text="Join Condition:").pack(anchor=tk.W)
        condition_frame = ttk.Frame(frame)
        condition_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Source column
        source_col_var = tk.StringVar()
        source_col_combo = ttk.Combobox(condition_frame, textvariable=source_col_var,
                                      values=list(self.selected_node.selected_columns))
        source_col_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        ttk.Label(condition_frame, text="=").pack(side=tk.LEFT)
        
        # Target column
        target_col_var = tk.StringVar()
        target_col_combo = ttk.Combobox(condition_frame, textvariable=target_col_var)
        target_col_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        def update_target_columns(*args):
            """Update target column list when table is selected"""
            target = target_var.get()
            if not target:
                return
                
            # Get columns for target table
            result = self.db_manager.execute_query(
                f"SELECT column_name FROM information_schema.columns WHERE table_name = '{target}'"
            )
            
            if "error" in result:
                messagebox.showerror("Error", f"Failed to get columns: {result['error']}")
                return
                
            # Update target column combo
            target_col_combo['values'] = [row[0] for row in result["rows"]]
            
        target_combo.bind('<<ComboboxSelected>>', update_target_columns)
        
        def save_join():
            """Save join condition"""
            target = target_var.get()
            if not target:
                messagebox.showerror("Error", "Please select a target table")
                return
                
            source_col = source_col_var.get()
            target_col = target_col_var.get()
            
            if not source_col or not target_col:
                messagebox.showerror("Error", "Please select join columns")
                return
                
            # Add join condition
            self.selected_node.join_conditions.append({
                'target_table': target,
                'type': type_var.get(),
                'source_column': source_col,
                'target_column': target_col
            })
            
            # Redraw canvas
            self.canvas.delete('all')
            for node in self.nodes.values():
                self._draw_node(node)
                
            dialog.destroy()
        
        ttk.Button(frame, text="Add", command=save_join).pack(fill=tk.X)
        
    def _add_filter(self):
        """Add a filter condition"""
        if not self.selected_node:
            messagebox.showwarning("Warning", "Please select a table first")
            return
            
        dialog = tk.Toplevel(self.window)
        dialog.title("Add Filter")
        dialog.geometry("400x200")
        
        frame = ttk.Frame(dialog, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Column selection
        ttk.Label(frame, text="Column:").pack(anchor=tk.W)
        col_var = tk.StringVar()
        col_combo = ttk.Combobox(frame, textvariable=col_var,
                               values=list(self.selected_node.selected_columns))
        col_combo.pack(fill=tk.X, pady=(0, 10))
        
        # Operator selection
        ttk.Label(frame, text="Operator:").pack(anchor=tk.W)
        op_var = tk.StringVar(value="=")
        op_combo = ttk.Combobox(frame, textvariable=op_var,
                              values=["=", "!=", ">", "<", ">=", "<=", "LIKE", "IN"])
        op_combo.pack(fill=tk.X, pady=(0, 10))
        
        # Value input
        ttk.Label(frame, text="Value:").pack(anchor=tk.W)
        value_entry = ttk.Entry(frame)
        value_entry.pack(fill=tk.X, pady=(0, 10))
        
        def save_filter():
            """Save filter condition"""
            column = col_var.get()
            operator = op_var.get()
            value = value_entry.get()
            
            if not column or not value:
                messagebox.showerror("Error", "Please fill in all fields")
                return
                
            # Add filter condition
            if not hasattr(self.selected_node, 'filters'):
                self.selected_node.filters = []
                
            self.selected_node.filters.append({
                'column': column,
                'operator': operator,
                'value': value
            })
            
            # Redraw canvas
            self.canvas.delete('all')
            for node in self.nodes.values():
                self._draw_node(node)
                
            dialog.destroy()
        
        ttk.Button(frame, text="Add", command=save_filter).pack(fill=tk.X)
        
    def _generate_sql(self):
        """Generate SQL from the visual query"""
        try:
            # Start with SELECT clause
            select_columns = []
            for node in self.nodes.values():
                for col in node.selected_columns:
                    select_columns.append(f"{node.name}.{col}")
                    
            sql = f"SELECT {', '.join(select_columns)}\n"
            
            # Add FROM clause
            sql += f"FROM {list(self.nodes.keys())[0]}\n"
            
            # Add JOIN clauses
            for node in self.nodes.values():
                for join in node.join_conditions:
                    sql += f"{join['type']} JOIN {join['target_table']} "
                    sql += f"ON {node.name}.{join['source_column']} = "
                    sql += f"{join['target_table']}.{join['target_column']}\n"
                    
            # Add WHERE clause
            where_conditions = []
            for node in self.nodes.values():
                if hasattr(node, 'filters'):
                    for filter_cond in node.filters:
                        where_conditions.append(
                            f"{node.name}.{filter_cond['column']} "
                            f"{filter_cond['operator']} '{filter_cond['value']}'"
                        )
                        
            if where_conditions:
                sql += f"WHERE {' AND '.join(where_conditions)}\n"
                
            # Update SQL preview
            self.sql_text.delete('1.0', tk.END)
            self.sql_text.insert('1.0', sql)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate SQL: {str(e)}")
            
    def _execute_query(self):
        """Execute the generated SQL query"""
        sql = self.sql_text.get('1.0', tk.END).strip()
        if not sql:
            messagebox.showwarning("Warning", "No SQL query to execute")
            return
            
        try:
            result = self.db_manager.execute_query(sql)
            
            if "error" in result:
                messagebox.showerror("Error", f"Query failed: {result['error']}")
                return
                
            # Show results in a new window
            self._show_results(result)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to execute query: {str(e)}")
            
    def _show_results(self, result: Dict):
        """Show query results in a new window"""
        dialog = tk.Toplevel(self.window)
        dialog.title("Query Results")
        dialog.geometry("800x600")
        
        # Create treeview
        tree = ttk.Treeview(dialog, columns=result['columns'], show='headings')
        
        # Set column headings
        for col in result['columns']:
            tree.heading(col, text=col)
            tree.column(col, width=100)
            
        # Add data
        for row in result['rows']:
            tree.insert('', 'end', values=row)
            
        # Add scrollbars
        y_scroll = ttk.Scrollbar(dialog, orient=tk.VERTICAL, command=tree.yview)
        x_scroll = ttk.Scrollbar(dialog, orient=tk.HORIZONTAL, command=tree.xview)
        tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        
        # Layout
        tree.grid(row=0, column=0, sticky='nsew')
        y_scroll.grid(row=0, column=1, sticky='ns')
        x_scroll.grid(row=1, column=0, sticky='ew')
        
        dialog.grid_rowconfigure(0, weight=1)
        dialog.grid_columnconfigure(0, weight=1)
        
    def show(self):
        """Show the query builder window"""
        self.window.deiconify()
        self.window.lift() 