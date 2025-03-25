#!/usr/bin/env python3
"""
Schema Migration Tools Module

Provides tools for tracking and applying database schema changes.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List, Optional
import json
import os
from datetime import datetime

class SchemaMigration:
    """Schema migration tools for tracking and applying changes"""
    
    def __init__(self, parent: tk.Tk, db_manager):
        """Initialize the schema migration tools
        
        Args:
            parent: Parent window
            db_manager: Database manager instance
        """
        self.parent = parent
        self.db_manager = db_manager
        self.migrations_dir = "migrations"
        self.current_version = 0
        
        # Create migrations directory if it doesn't exist
        if not os.path.exists(self.migrations_dir):
            os.makedirs(self.migrations_dir)
            
        # Create main window
        self.window = tk.Toplevel(parent)
        self.window.title("Schema Migration Tools")
        self.window.geometry("800x600")
        
        # Create main layout
        self._create_layout()
        
        # Load current version
        self._load_current_version()
        
    def _create_layout(self):
        """Create the main layout"""
        # Create main frame
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create toolbar
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="Create Migration", command=self._create_migration).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Apply Migration", command=self._apply_migration).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Rollback Migration", command=self._rollback_migration).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Refresh", command=self._refresh_migrations).pack(side=tk.LEFT, padx=2)
        
        # Create migration list
        list_frame = ttk.LabelFrame(main_frame, text="Migrations")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.migration_tree = ttk.Treeview(list_frame, columns=("version", "name", "status"),
                                         show="headings")
        self.migration_tree.heading("version", text="Version")
        self.migration_tree.heading("name", text="Name")
        self.migration_tree.heading("status", text="Status")
        self.migration_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.migration_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.migration_tree.configure(yscrollcommand=scrollbar.set)
        
        # Create details panel
        details_frame = ttk.LabelFrame(main_frame, text="Migration Details")
        details_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.details_text = tk.Text(details_frame, height=10)
        self.details_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Bind selection event
        self.migration_tree.bind('<<TreeviewSelect>>', self._on_migration_select)
        
    def _load_current_version(self):
        """Load the current schema version"""
        try:
            # Create version table if it doesn't exist
            self.db_manager.execute_query("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Get current version
            result = self.db_manager.execute_query("SELECT MAX(version) FROM schema_version")
            
            if "error" in result:
                messagebox.showerror("Error", f"Failed to get current version: {result['error']}")
                return
                
            self.current_version = result["rows"][0][0] or 0
            
            # Refresh migration list
            self._refresh_migrations()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load current version: {str(e)}")
            
    def _refresh_migrations(self):
        """Refresh the migration list"""
        try:
            # Clear existing items
            for item in self.migration_tree.get_children():
                self.migration_tree.delete(item)
                
            # Get migration files
            migration_files = []
            for filename in os.listdir(self.migrations_dir):
                if filename.endswith('.json'):
                    migration_files.append(filename)
                    
            # Sort by version number
            migration_files.sort(key=lambda x: int(x.split('_')[0]))
            
            # Add to tree
            for filename in migration_files:
                version = int(filename.split('_')[0])
                name = filename[filename.index('_') + 1:filename.index('.')]
                status = "Applied" if version <= self.current_version else "Pending"
                
                self.migration_tree.insert("", "end", values=(version, name, status))
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh migrations: {str(e)}")
            
    def _on_migration_select(self, event):
        """Handle migration selection"""
        selection = self.migration_tree.selection()
        if not selection:
            return
            
        try:
            # Get migration file
            version = self.migration_tree.item(selection[0])['values'][0]
            name = self.migration_tree.item(selection[0])['values'][1]
            filename = f"{version:04d}_{name}.json"
            
            with open(os.path.join(self.migrations_dir, filename), 'r') as f:
                migration = json.load(f)
                
            # Update details text
            self.details_text.delete('1.0', tk.END)
            self.details_text.insert('1.0', f"Version: {version}\n")
            self.details_text.insert('end', f"Name: {name}\n")
            self.details_text.insert('end', f"Description: {migration['description']}\n\n")
            self.details_text.insert('end', "Up SQL:\n")
            self.details_text.insert('end', migration['up_sql'])
            self.details_text.insert('end', "\n\nDown SQL:\n")
            self.details_text.insert('end', migration['down_sql'])
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load migration details: {str(e)}")
            
    def _create_migration(self):
        """Create a new migration"""
        dialog = tk.Toplevel(self.window)
        dialog.title("Create Migration")
        dialog.geometry("600x400")
        
        frame = ttk.Frame(dialog, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Migration name
        ttk.Label(frame, text="Migration Name:").pack(anchor=tk.W)
        name_entry = ttk.Entry(frame)
        name_entry.pack(fill=tk.X, pady=(0, 10))
        
        # Description
        ttk.Label(frame, text="Description:").pack(anchor=tk.W)
        desc_text = tk.Text(frame, height=3)
        desc_text.pack(fill=tk.X, pady=(0, 10))
        
        # Up SQL
        ttk.Label(frame, text="Up SQL:").pack(anchor=tk.W)
        up_text = tk.Text(frame, height=5)
        up_text.pack(fill=tk.X, pady=(0, 10))
        
        # Down SQL
        ttk.Label(frame, text="Down SQL:").pack(anchor=tk.W)
        down_text = tk.Text(frame, height=5)
        down_text.pack(fill=tk.X, pady=(0, 10))
        
        def save_migration():
            """Save the migration"""
            try:
                name = name_entry.get().strip()
                if not name:
                    messagebox.showerror("Error", "Please enter a migration name")
                    return
                    
                # Create migration object
                migration = {
                    'version': self.current_version + 1,
                    'name': name,
                    'description': desc_text.get('1.0', tk.END).strip(),
                    'up_sql': up_text.get('1.0', tk.END).strip(),
                    'down_sql': down_text.get('1.0', tk.END).strip(),
                    'created_at': datetime.now().isoformat()
                }
                
                # Save to file
                filename = f"{migration['version']:04d}_{name}.json"
                with open(os.path.join(self.migrations_dir, filename), 'w') as f:
                    json.dump(migration, f, indent=2)
                    
                self._refresh_migrations()
                dialog.destroy()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save migration: {str(e)}")
                
        ttk.Button(frame, text="Save", command=save_migration).pack(fill=tk.X)
        
    def _apply_migration(self):
        """Apply the selected migration"""
        selection = self.migration_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a migration to apply")
            return
            
        try:
            # Get migration file
            version = self.migration_tree.item(selection[0])['values'][0]
            name = self.migration_tree.item(selection[0])['values'][1]
            filename = f"{version:04d}_{name}.json"
            
            with open(os.path.join(self.migrations_dir, filename), 'r') as f:
                migration = json.load(f)
                
            # Execute up SQL
            result = self.db_manager.execute_query(migration['up_sql'])
            
            if "error" in result:
                messagebox.showerror("Error", f"Failed to apply migration: {result['error']}")
                return
                
            # Update version
            self.db_manager.execute_query(
                f"INSERT INTO schema_version (version) VALUES ({version})"
            )
            
            self.current_version = version
            self._refresh_migrations()
            messagebox.showinfo("Success", "Migration applied successfully")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to apply migration: {str(e)}")
            
    def _rollback_migration(self):
        """Rollback the selected migration"""
        selection = self.migration_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a migration to rollback")
            return
            
        try:
            # Get migration file
            version = self.migration_tree.item(selection[0])['values'][0]
            name = self.migration_tree.item(selection[0])['values'][1]
            filename = f"{version:04d}_{name}.json"
            
            with open(os.path.join(self.migrations_dir, filename), 'r') as f:
                migration = json.load(f)
                
            # Execute down SQL
            result = self.db_manager.execute_query(migration['down_sql'])
            
            if "error" in result:
                messagebox.showerror("Error", f"Failed to rollback migration: {result['error']}")
                return
                
            # Update version
            self.db_manager.execute_query(
                f"DELETE FROM schema_version WHERE version = {version}"
            )
            
            self.current_version = max(0, version - 1)
            self._refresh_migrations()
            messagebox.showinfo("Success", "Migration rolled back successfully")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to rollback migration: {str(e)}")
            
    def show(self):
        """Show the migration tools window"""
        self.window.deiconify()
        self.window.lift() 