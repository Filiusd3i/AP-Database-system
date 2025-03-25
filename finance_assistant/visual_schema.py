#!/usr/bin/env python3
"""
Visual Schema Designer Module

Provides a drag-and-drop interface for designing database schemas,
including table creation, relationships, and constraints.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import json
from typing import Dict, List, Optional, Tuple

class TableNode:
    """Represents a table in the schema designer"""
    def __init__(self, name: str, x: int, y: int):
        self.name = name
        self.x = x
        self.y = y
        self.columns: List[Dict] = []
        self.relationships: List[Dict] = []
        
    def to_dict(self) -> Dict:
        """Convert table node to dictionary for saving"""
        return {
            'name': self.name,
            'x': self.x,
            'y': self.y,
            'columns': self.columns,
            'relationships': self.relationships
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TableNode':
        """Create table node from dictionary"""
        node = cls(data['name'], data['x'], data['y'])
        node.columns = data['columns']
        node.relationships = data['relationships']
        return node

class SchemaDesigner:
    """Visual schema designer with drag-and-drop functionality"""
    
    def __init__(self, parent: tk.Tk, db_manager):
        """Initialize the schema designer
        
        Args:
            parent: Parent window
            db_manager: Database manager instance
        """
        self.parent = parent
        self.db_manager = db_manager
        self.tables: Dict[str, TableNode] = {}
        self.selected_table: Optional[TableNode] = None
        self.dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        
        # Create main window
        self.window = tk.Toplevel(parent)
        self.window.title("Schema Designer")
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
        
        ttk.Button(toolbar, text="New Table", command=self._create_new_table).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Add Relationship", command=self._add_relationship).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Save Schema", command=self._save_schema).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Apply to Database", command=self._apply_schema).pack(side=tk.LEFT, padx=2)
        
        # Create canvas for drawing
        self.canvas = tk.Canvas(main_frame, bg='white')
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create properties panel
        self.properties_frame = ttk.LabelFrame(main_frame, text="Properties")
        self.properties_frame.pack(fill=tk.Y, padx=5, pady=5)
        
    def _bind_events(self):
        """Bind canvas events"""
        self.canvas.bind('<Button-1>', self._on_canvas_click)
        self.canvas.bind('<B1-Motion>', self._on_canvas_drag)
        self.canvas.bind('<ButtonRelease-1>', self._on_canvas_release)
        
    def _create_new_table(self):
        """Create a new table node"""
        dialog = tk.Toplevel(self.window)
        dialog.title("New Table")
        dialog.geometry("300x150")
        
        frame = ttk.Frame(dialog, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Table Name:").pack(anchor=tk.W)
        name_entry = ttk.Entry(frame)
        name_entry.pack(fill=tk.X, pady=(0, 10))
        
        def save_table():
            name = name_entry.get().strip()
            if not name:
                messagebox.showerror("Error", "Table name is required")
                return
                
            if name in self.tables:
                messagebox.showerror("Error", "Table name already exists")
                return
            
            # Create new table node
            table = TableNode(name, 100, 100)
            self.tables[name] = table
            
            # Draw table on canvas
            self._draw_table(table)
            
            dialog.destroy()
        
        ttk.Button(frame, text="Create", command=save_table).pack(fill=tk.X)
        
    def _draw_table(self, table: TableNode):
        """Draw a table node on the canvas"""
        # Draw table box
        x, y = table.x, table.y
        width, height = 200, 100
        
        # Draw main box
        self.canvas.create_rectangle(x, y, x + width, y + height, fill='lightblue')
        
        # Draw table name
        self.canvas.create_text(x + width/2, y + 20, text=table.name, font=('Arial', 12, 'bold'))
        
        # Draw columns
        for i, col in enumerate(table.columns):
            y_pos = y + 40 + i * 20
            col_text = f"{col['name']} ({col['type']})"
            if col.get('primary_key'):
                col_text = f"PK {col_text}"
            self.canvas.create_text(x + 10, y_pos, text=col_text, anchor=tk.W)
            
        # Draw relationships
        for rel in table.relationships:
            target = self.tables.get(rel['target_table'])
            if target:
                self._draw_relationship(table, target, rel)
                
    def _draw_relationship(self, source: TableNode, target: TableNode, relationship: Dict):
        """Draw a relationship line between tables"""
        # Calculate line points
        source_x = source.x + 100
        source_y = source.y + 50
        target_x = target.x + 100
        target_y = target.y + 50
        
        # Draw line
        self.canvas.create_line(source_x, source_y, target_x, target_y, arrow=tk.LAST)
        
        # Draw relationship type
        mid_x = (source_x + target_x) / 2
        mid_y = (source_y + target_y) / 2
        self.canvas.create_text(mid_x, mid_y - 10, text=relationship['type'])
        
    def _on_canvas_click(self, event):
        """Handle canvas click event"""
        # Check if clicked on a table
        for table in self.tables.values():
            if (table.x <= event.x <= table.x + 200 and 
                table.y <= event.y <= table.y + 100):
                self.selected_table = table
                self.dragging = True
                self.drag_start_x = event.x - table.x
                self.drag_start_y = event.y - table.y
                return
                
        self.selected_table = None
        
    def _on_canvas_drag(self, event):
        """Handle canvas drag event"""
        if self.dragging and self.selected_table:
            # Update table position
            self.selected_table.x = event.x - self.drag_start_x
            self.selected_table.y = event.y - self.drag_start_y
            
            # Redraw canvas
            self.canvas.delete('all')
            for table in self.tables.values():
                self._draw_table(table)
                
    def _on_canvas_release(self, event):
        """Handle canvas release event"""
        self.dragging = False
        self.selected_table = None
        
    def _add_relationship(self):
        """Add a relationship between tables"""
        if not self.selected_table:
            messagebox.showwarning("Warning", "Please select a source table first")
            return
            
        dialog = tk.Toplevel(self.window)
        dialog.title("Add Relationship")
        dialog.geometry("300x200")
        
        frame = ttk.Frame(dialog, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Target table selection
        ttk.Label(frame, text="Target Table:").pack(anchor=tk.W)
        target_var = tk.StringVar()
        target_combo = ttk.Combobox(frame, textvariable=target_var, 
                                  values=list(self.tables.keys()))
        target_combo.pack(fill=tk.X, pady=(0, 10))
        
        # Relationship type
        ttk.Label(frame, text="Relationship Type:").pack(anchor=tk.W)
        type_var = tk.StringVar(value="1:N")
        type_combo = ttk.Combobox(frame, textvariable=type_var,
                                values=["1:1", "1:N", "N:M"])
        type_combo.pack(fill=tk.X, pady=(0, 10))
        
        def save_relationship():
            target = target_var.get()
            if not target:
                messagebox.showerror("Error", "Please select a target table")
                return
                
            if target == self.selected_table.name:
                messagebox.showerror("Error", "Cannot create relationship to self")
                return
                
            # Add relationship
            self.selected_table.relationships.append({
                'target_table': target,
                'type': type_var.get()
            })
            
            # Redraw canvas
            self.canvas.delete('all')
            for table in self.tables.values():
                self._draw_table(table)
                
            dialog.destroy()
        
        ttk.Button(frame, text="Add", command=save_relationship).pack(fill=tk.X)
        
    def _save_schema(self):
        """Save the current schema to a file"""
        schema_data = {
            'tables': {name: table.to_dict() for name, table in self.tables.items()}
        }
        
        try:
            with open('schema.json', 'w') as f:
                json.dump(schema_data, f, indent=2)
            messagebox.showinfo("Success", "Schema saved successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save schema: {str(e)}")
            
    def _apply_schema(self):
        """Apply the current schema to the database"""
        try:
            # Create tables
            for table in self.tables.values():
                # Build CREATE TABLE statement
                columns = []
                for col in table.columns:
                    col_def = f"{col['name']} {col['type']}"
                    if col.get('primary_key'):
                        col_def += " PRIMARY KEY"
                    if not col.get('nullable', True):
                        col_def += " NOT NULL"
                    columns.append(col_def)
                
                create_sql = f"CREATE TABLE {table.name} (\n  " + ",\n  ".join(columns) + "\n)"
                
                # Execute query
                result = self.db_manager.execute_query(create_sql)
                if "error" in result:
                    raise Exception(result["error"])
            
            # Create relationships
            for table in self.tables.values():
                for rel in table.relationships:
                    target = self.tables[rel['target_table']]
                    
                    # Add foreign key
                    fk_sql = f"""
                    ALTER TABLE {table.name}
                    ADD CONSTRAINT fk_{table.name}_{target.name}
                    FOREIGN KEY ({rel['source_column']})
                    REFERENCES {target.name}({rel['target_column']})
                    """
                    
                    result = self.db_manager.execute_query(fk_sql)
                    if "error" in result:
                        raise Exception(result["error"])
            
            messagebox.showinfo("Success", "Schema applied successfully")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to apply schema: {str(e)}")
            
    def show(self):
        """Show the schema designer window"""
        self.window.deiconify()
        self.window.lift() 