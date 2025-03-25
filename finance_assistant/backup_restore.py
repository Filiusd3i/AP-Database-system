#!/usr/bin/env python3
"""
Backup and Restore Tools Module

Provides tools for backing up and restoring the database.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Dict, List, Optional
import os
import json
import shutil
from datetime import datetime
import subprocess

class BackupRestore:
    """Backup and restore tools for database management"""
    
    def __init__(self, parent: tk.Tk, db_manager):
        """Initialize the backup and restore tools
        
        Args:
            parent: Parent window
            db_manager: Database manager instance
        """
        self.parent = parent
        self.db_manager = db_manager
        self.backups_dir = "backups"
        
        # Create backups directory if it doesn't exist
        if not os.path.exists(self.backups_dir):
            os.makedirs(self.backups_dir)
            
        # Create main window
        self.window = tk.Toplevel(parent)
        self.window.title("Backup and Restore Tools")
        self.window.geometry("800x600")
        
        # Create main layout
        self._create_layout()
        
    def _create_layout(self):
        """Create the main layout"""
        # Create main frame
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create toolbar
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="Create Backup", command=self._create_backup).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Restore Backup", command=self._restore_backup).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Delete Backup", command=self._delete_backup).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Refresh", command=self._refresh_backups).pack(side=tk.LEFT, padx=2)
        
        # Create backup list
        list_frame = ttk.LabelFrame(main_frame, text="Backups")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.backup_tree = ttk.Treeview(list_frame, columns=("name", "date", "size"),
                                      show="headings")
        self.backup_tree.heading("name", text="Name")
        self.backup_tree.heading("date", text="Date")
        self.backup_tree.heading("size", text="Size")
        self.backup_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.backup_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.backup_tree.configure(yscrollcommand=scrollbar.set)
        
        # Create details panel
        details_frame = ttk.LabelFrame(main_frame, text="Backup Details")
        details_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.details_text = tk.Text(details_frame, height=10)
        self.details_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Bind selection event
        self.backup_tree.bind('<<TreeviewSelect>>', self._on_backup_select)
        
        # Refresh backup list
        self._refresh_backups()
        
    def _refresh_backups(self):
        """Refresh the backup list"""
        try:
            # Clear existing items
            for item in self.backup_tree.get_children():
                self.backup_tree.delete(item)
                
            # Get backup files
            backup_files = []
            for filename in os.listdir(self.backups_dir):
                if filename.endswith('.json'):
                    backup_files.append(filename)
                    
            # Sort by date (newest first)
            backup_files.sort(reverse=True)
            
            # Add to tree
            for filename in backup_files:
                # Get backup info
                with open(os.path.join(self.backups_dir, filename), 'r') as f:
                    backup = json.load(f)
                    
                # Get file size
                size = os.path.getsize(os.path.join(self.backups_dir, filename))
                size_str = f"{size / 1024:.1f} KB"
                
                self.backup_tree.insert("", "end", values=(
                    backup['name'],
                    backup['created_at'],
                    size_str
                ))
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh backups: {str(e)}")
            
    def _on_backup_select(self, event):
        """Handle backup selection"""
        selection = self.backup_tree.selection()
        if not selection:
            return
            
        try:
            # Get backup file
            name = self.backup_tree.item(selection[0])['values'][0]
            filename = f"{name}.json"
            
            with open(os.path.join(self.backups_dir, filename), 'r') as f:
                backup = json.load(f)
                
            # Update details text
            self.details_text.delete('1.0', tk.END)
            self.details_text.insert('1.0', f"Name: {backup['name']}\n")
            self.details_text.insert('end', f"Created: {backup['created_at']}\n")
            self.details_text.insert('end', f"Description: {backup['description']}\n")
            self.details_text.insert('end', f"Tables: {', '.join(backup['tables'])}\n")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load backup details: {str(e)}")
            
    def _create_backup(self):
        """Create a new backup"""
        dialog = tk.Toplevel(self.window)
        dialog.title("Create Backup")
        dialog.geometry("400x300")
        
        frame = ttk.Frame(dialog, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Backup name
        ttk.Label(frame, text="Backup Name:").pack(anchor=tk.W)
        name_entry = ttk.Entry(frame)
        name_entry.pack(fill=tk.X, pady=(0, 10))
        
        # Description
        ttk.Label(frame, text="Description:").pack(anchor=tk.W)
        desc_text = tk.Text(frame, height=3)
        desc_text.pack(fill=tk.X, pady=(0, 10))
        
        # Tables to backup
        ttk.Label(frame, text="Tables to Backup:").pack(anchor=tk.W)
        tables_frame = ttk.Frame(frame)
        tables_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        table_vars = {}
        for table in self.db_manager.tables:
            var = tk.BooleanVar(value=True)
            table_vars[table] = var
            ttk.Checkbutton(tables_frame, text=table, variable=var).pack(anchor=tk.W)
            
        def save_backup():
            """Save the backup"""
            try:
                name = name_entry.get().strip()
                if not name:
                    messagebox.showerror("Error", "Please enter a backup name")
                    return
                    
                # Get selected tables
                selected_tables = [table for table, var in table_vars.items() if var.get()]
                if not selected_tables:
                    messagebox.showerror("Error", "Please select at least one table")
                    return
                    
                # Create backup object
                backup = {
                    'name': name,
                    'description': desc_text.get('1.0', tk.END).strip(),
                    'tables': selected_tables,
                    'created_at': datetime.now().isoformat()
                }
                
                # Save backup info
                filename = f"{name}.json"
                with open(os.path.join(self.backups_dir, filename), 'w') as f:
                    json.dump(backup, f, indent=2)
                    
                # Export data for each table
                for table in selected_tables:
                    # Get table data
                    result = self.db_manager.execute_query(f"SELECT * FROM {table}")
                    
                    if "error" in result:
                        messagebox.showerror("Error", f"Failed to get data for {table}: {result['error']}")
                        continue
                        
                    # Save table data
                    data_filename = f"{name}_{table}.csv"
                    with open(os.path.join(self.backups_dir, data_filename), 'w') as f:
                        # Write header
                        f.write(','.join(result['columns']) + '\n')
                        
                        # Write data
                        for row in result['rows']:
                            f.write(','.join(str(val) for val in row) + '\n')
                            
                self._refresh_backups()
                dialog.destroy()
                messagebox.showinfo("Success", "Backup created successfully")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create backup: {str(e)}")
                
        ttk.Button(frame, text="Save", command=save_backup).pack(fill=tk.X)
        
    def _restore_backup(self):
        """Restore the selected backup"""
        selection = self.backup_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a backup to restore")
            return
            
        if not messagebox.askyesno("Confirm", "Are you sure you want to restore this backup? This will overwrite existing data."):
            return
            
        try:
            # Get backup file
            name = self.backup_tree.item(selection[0])['values'][0]
            filename = f"{name}.json"
            
            with open(os.path.join(self.backups_dir, filename), 'r') as f:
                backup = json.load(f)
                
            # Restore each table
            for table in backup['tables']:
                # Clear existing data
                self.db_manager.execute_query(f"TRUNCATE TABLE {table}")
                
                # Read backup data
                data_filename = f"{name}_{table}.csv"
                with open(os.path.join(self.backups_dir, data_filename), 'r') as f:
                    # Skip header
                    columns = f.readline().strip().split(',')
                    
                    # Read and insert data
                    for line in f:
                        values = line.strip().split(',')
                        sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(repr(val) for val in values)})"
                        self.db_manager.execute_query(sql)
                        
            self._refresh_backups()
            messagebox.showinfo("Success", "Backup restored successfully")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to restore backup: {str(e)}")
            
    def _delete_backup(self):
        """Delete the selected backup"""
        selection = self.backup_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a backup to delete")
            return
            
        if not messagebox.askyesno("Confirm", "Are you sure you want to delete this backup?"):
            return
            
        try:
            # Get backup file
            name = self.backup_tree.item(selection[0])['values'][0]
            filename = f"{name}.json"
            
            with open(os.path.join(self.backups_dir, filename), 'r') as f:
                backup = json.load(f)
                
            # Delete backup files
            os.remove(os.path.join(self.backups_dir, filename))
            for table in backup['tables']:
                data_filename = f"{name}_{table}.csv"
                os.remove(os.path.join(self.backups_dir, data_filename))
                
            self._refresh_backups()
            messagebox.showinfo("Success", "Backup deleted successfully")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete backup: {str(e)}")
            
    def show(self):
        """Show the backup and restore window"""
        self.window.deiconify()
        self.window.lift() 