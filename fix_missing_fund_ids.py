#!/usr/bin/env python
"""
Fix Missing Fund IDs Script

This script identifies and fixes missing fund_id values in invoices and vendor allocations:
1. Detects 'nan' or null fund_id values
2. Assigns appropriate fund_id values based on configurable rules
3. Updates the CSV files with fixed foreign keys
"""

import os
import sys
import pandas as pd
import logging
import numpy as np
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager

# Add project directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
from finance_assistant.tables_manager import TablesManager
    from finance_assistant.logging_config import configure_logging, log_table_operation, get_audit_logger
    from finance_assistant.logging_utils import log_csv_operation, log_duration, csv_audit_logger
except ImportError as e:
    print(f"Error importing required modules: {e}")
    sys.exit(1)

# Configure CSV-focused logging
logger = configure_logging('fund_id_fixer')

# Default fund ID to use when no other option is available
DEFAULT_FUND_ID = None  # Will be set after loading funds

class FundAssigner:
    """Class to handle fund ID assignment strategies"""
    
    def __init__(self, tables_manager):
        """Initialize with the tables manager"""
        self.tables_manager = tables_manager
        self.vendors_df = None
        self.funds_df = None
        self.default_fund_id = None
        self._load_data()
    
    @log_csv_operation(logger)
    def _load_data(self):
        """Load required data tables"""
        logger.info("Loading vendor and fund data for assignment")
        try:
        self.vendors_df = self.tables_manager.get_table("vendors")
        self.funds_df = self.tables_manager.get_table("Funds")
        
        # Set default fund ID (first fund or general fund if available)
        if not isinstance(self.funds_df, dict) and not self.funds_df.empty:
            # Try to find a general fund first
            general_funds = self.funds_df[
                    self.funds_df['name'].str.lower().str.contains('general|main|default|corporate', 
                                                                   na=False)
            ]
            
            if not general_funds.empty:
                self.default_fund_id = general_funds.iloc[0]['fund_id']
                    logger.info(f"Using general fund as default: {self.default_fund_id}")
            else:
                self.default_fund_id = self.funds_df.iloc[0]['fund_id']
                    logger.info(f"Using first fund as default: {self.default_fund_id}")
        else:
            logger.warning("Could not load funds table or table is empty")
            self.default_fund_id = '1'  # Fallback
                logger.info(f"Using fallback fund ID: {self.default_fund_id}")
        except Exception as e:
            logger.error(f"Error loading data: {str(e)}", exc_info=True)
            self.default_fund_id = '1'  # Fallback on error
    
    @log_csv_operation(logger)
    def get_fund_for_vendor(self, vendor_id):
        """Get the most commonly used fund for a vendor"""
        if isinstance(self.vendors_df, dict) or self.vendors_df.empty:
            logger.debug(f"No vendors data, using default fund for vendor {vendor_id}")
            return self.default_fund_id
            
        # Get vendor allocations
        try:
        vendor_allocations = self.tables_manager.get_table("Vendor allocation")
        
        if isinstance(vendor_allocations, dict) or vendor_allocations.empty:
                logger.debug(f"No vendor allocations, using default fund for vendor {vendor_id}")
            return self.default_fund_id
        
        # Filter to this vendor
        if 'vendor_id' not in vendor_allocations.columns:
                logger.warning(f"vendor_id column not found in Vendor allocation table")
            return self.default_fund_id
            
        vendor_allocs = vendor_allocations[vendor_allocations['vendor_id'] == vendor_id]
        
        if vendor_allocs.empty or 'fund_id' not in vendor_allocs.columns:
                logger.debug(f"No allocations found for vendor {vendor_id}")
            return self.default_fund_id
        
        # Get the most common fund
        # Filter out NaN values
        valid_funds = vendor_allocs['fund_id'].dropna()
        if valid_funds.empty:
                logger.debug(f"No valid fund allocations for vendor {vendor_id}")
            return self.default_fund_id
            
        # Get the most common fund
            most_common_fund = valid_funds.mode().iloc[0]
            # Check if it's NaN
            if pd.isna(most_common_fund) or most_common_fund == 'nan':
                logger.debug(f"Most common fund for vendor {vendor_id} is NaN")
                return self.default_fund_id
                
            logger.debug(f"Found most common fund for vendor {vendor_id}: {most_common_fund}")
            return most_common_fund
        except Exception as e:
            logger.error(f"Error getting fund for vendor {vendor_id}: {str(e)}")
            return self.default_fund_id
    
    @log_csv_operation(logger)
    def get_fund_suggestions(self, record):
        """Get fund suggestions for a record"""
        suggestions = []
        record_id = record.get('invoice_id', record.get('id', 'unknown'))
        logger.debug(f"Getting fund suggestions for record {record_id}")
        
        # Strategy 1: Use vendor's primary fund
        if 'vendor_id' in record and record['vendor_id'] is not None:
            try:
                vendor_id = record['vendor_id']
                # Check if vendor_id is NaN or 'nan'
                if not (pd.isna(vendor_id) or vendor_id == 'nan' or vendor_id == ''):
                    vendor_fund = self.get_fund_for_vendor(vendor_id)
                    if vendor_fund != self.default_fund_id:
                        suggestions.append(('Vendor primary fund', vendor_fund))
                        logger.debug(f"Added vendor primary fund suggestion: {vendor_fund}")
            except Exception as e:
                logger.warning(f"Error getting fund for vendor {record.get('vendor_id', 'unknown')}: {str(e)}")
        
        # Strategy 2: Based on amount ranges
        if 'amount' in record and record['amount'] is not None:
            try:
                amount = float(record['amount'])
                # Example: Small amounts to operational fund, large to capital fund
                # This is just an example - customize based on your business rules
                small_funds = self.funds_df[
                    self.funds_df['name'].str.lower().str.contains('operational|expense|small', 
                                                                       na=False)
                ]
                
                large_funds = self.funds_df[
                    self.funds_df['name'].str.lower().str.contains('capital|investment|large', 
                                                                      na=False)
                ]
                
                if amount < 1000 and not small_funds.empty:
                    suggestions.append(('Small expense fund', small_funds.iloc[0]['fund_id']))
                    logger.debug(f"Added small expense fund suggestion: {small_funds.iloc[0]['fund_id']}")
                elif amount >= 1000 and not large_funds.empty:
                    suggestions.append(('Capital expense fund', large_funds.iloc[0]['fund_id']))
                    logger.debug(f"Added capital expense fund suggestion: {large_funds.iloc[0]['fund_id']}")
            except Exception as e:
                logger.warning(f"Error getting fund based on amount {record.get('amount', 'unknown')}: {str(e)}")
        
        # Always add default fund as last option
        suggestions.append(('Default fund', self.default_fund_id))
        logger.debug(f"Added default fund suggestion: {self.default_fund_id}")
        
        return suggestions

def is_missing_fund_id(value):
    """Check if a fund_id value is missing or invalid"""
    if pd.isna(value):
        return True
    if isinstance(value, str) and (value.lower() == 'nan' or value.strip() == ''):
        return True
    return False

@log_csv_operation(logger)
def fix_invoices_fund_ids(tables_manager, fund_assigner, interactive=True, username="system"):
    """Fix missing fund_id values in invoices table"""
    # Log operation start
    logger.info("Starting fix_invoices_fund_ids operation")
    
    # Load the invoices data
    with log_duration(logger, "Loading invoices table"):
    invoices_df = tables_manager.get_table("Invoices")
    
    if isinstance(invoices_df, dict) and 'error' in invoices_df:
        logger.error(f"Error loading invoices: {invoices_df['error']}")
        return {"error": invoices_df['error']}
    
    # Check if fund_id column exists
    if 'fund_id' not in invoices_df.columns:
        logger.error("fund_id column not found in Invoices table")
        return {"error": "fund_id column not found in Invoices table"}
    
    # Identify records with missing fund_id
    missing_fund_ids = invoices_df['fund_id'].apply(is_missing_fund_id)
    missing_count = missing_fund_ids.sum()
    
    if missing_count == 0:
        logger.info("No missing fund_id values found in Invoices")
        return {"updated_count": 0}
    
    logger.info(f"Found {missing_count} invoices with missing fund_id values")
    
    # Make a copy to avoid modifying the original
    updated_df = invoices_df.copy()
    
    if interactive:
        # Try to use UI for fixing
        try:
            show_fund_assignment_ui(updated_df, missing_fund_ids, fund_assigner, tables_manager, "Invoices", username)
            # UI will handle saving
            return {"updated_count": missing_count}
        except Exception as e:
            logger.error(f"Error showing UI: {str(e)}", exc_info=True)
            logger.info("Falling back to automatic assignment")
    
    # Automatic assignment
    logger.info("Performing automatic fund assignment for invoices")
    update_count = 0
    
    # For each invoice with missing fund_id, assign the most appropriate fund
    for idx in updated_df[missing_fund_ids].index:
        record = updated_df.loc[idx]
        suggestions = fund_assigner.get_fund_suggestions(record)
        
        # Use the first suggestion (highest priority)
        if suggestions:
            updated_df.loc[idx, 'fund_id'] = suggestions[0][1]
            logger.info(f"Assigned fund {suggestions[0][1]} to invoice {record.get('invoice_id', idx)} (reason: {suggestions[0][0]})")
            update_count += 1
    
    # Save the updated dataframe
    with log_duration(logger, "Saving updated invoices"):
        try:
    result = tables_manager.save_table("Invoices", updated_df)
            logger.info(f"Successfully saved {update_count} fund ID updates to Invoices")
            # Log to audit log
            csv_audit_logger.log_action(
                username, 
                "fix_missing_fund_ids", 
                "Invoices", 
                None, 
                f"Fixed {update_count} missing fund IDs automatically"
            )
        except Exception as e:
            logger.error(f"Error saving updated invoices: {str(e)}", exc_info=True)
            return {"error": str(e), "updated_count": 0}
    
    return {"updated_count": update_count, "result": result}

@log_csv_operation(logger)
def fix_vendor_allocation_fund_ids(tables_manager, fund_assigner, interactive=True, username="system"):
    """Fix missing fund_id values in Vendor allocation table"""
    # Log operation start
    logger.info("Starting fix_vendor_allocation_fund_ids operation")
    
    # Load the vendor allocation data
    with log_duration(logger, "Loading vendor allocation table"):
        alloc_df = tables_manager.get_table("Vendor allocation")
    
    if isinstance(alloc_df, dict) and 'error' in alloc_df:
        logger.error(f"Error loading Vendor allocation: {alloc_df['error']}")
        return {"error": alloc_df['error']}
    
    # Check if fund_id column exists
    if 'fund_id' not in alloc_df.columns:
        logger.error("fund_id column not found in Vendor allocation table")
        return {"error": "fund_id column not found in Vendor allocation table"}
    
    # Identify records with missing fund_id
    missing_fund_ids = alloc_df['fund_id'].apply(is_missing_fund_id)
    missing_count = missing_fund_ids.sum()
    
    if missing_count == 0:
        logger.info("No missing fund_id values found in Vendor allocation")
        return {"updated_count": 0}
    
    logger.info(f"Found {missing_count} allocations with missing fund_id values")
    
    # Make a copy to avoid modifying the original
    updated_df = alloc_df.copy()
    
    if interactive:
        # Try to use UI for fixing
        try:
            show_fund_assignment_ui(updated_df, missing_fund_ids, fund_assigner, tables_manager, "Vendor allocation")
            # UI will handle saving
            log_table_operation(username, "fix_missing_fund_ids", "Vendor allocation", None, f"Fixed {missing_count} missing fund IDs interactively")
            return {"updated_count": missing_count}
        except Exception as e:
            logger.error(f"Error showing UI: {str(e)}")
            logger.info("Falling back to automatic assignment")
    
    # Automatic assignment
    # For each allocation with missing fund_id, assign the most appropriate fund
    update_count = 0
    for idx in updated_df[missing_fund_ids].index:
        record = updated_df.loc[idx]
        suggestions = fund_assigner.get_fund_suggestions(record)
        
        # Use the first suggestion (highest priority)
        if suggestions:
            updated_df.loc[idx, 'fund_id'] = suggestions[0][1]
            logger.debug(f"Assigned fund {suggestions[0][1]} to vendor allocation (reason: {suggestions[0][0]})")
            update_count += 1
    
    # Save the updated dataframe
    with log_duration(logger, "Saving updated vendor allocations"):
    result = tables_manager.save_table("Vendor allocation", updated_df)
    
    logger.info(f"Fixed {update_count} missing fund IDs in Vendor allocation table")
    log_table_operation(username, "fix_missing_fund_ids", "Vendor allocation", None, f"Fixed {update_count} missing fund IDs automatically")
    
    return {"updated_count": update_count, "result": result}

def show_fund_assignment_ui(dataframe, missing_mask, fund_assigner, tables_manager, table_name):
    """Show UI for manually assigning fund IDs"""
    logger.info(f"Showing UI for {table_name} fund assignment")
    
    # Create a new Tkinter window
    root = tk.Tk()
    root.title(f"Fix Missing Fund IDs - {table_name}")
    root.geometry("1000x700")
    
    # Create a frame for the data table
    table_frame = ttk.LabelFrame(root, text=f"{table_name} with Missing Fund IDs")
    table_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
    
    # Create a treeview for the data
    tree = ttk.Treeview(table_frame)
    tree.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
    
    # Add scrollbars
    vsb = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    vsb.pack(side=tk.RIGHT, fill=tk.Y)
    tree.configure(yscrollcommand=vsb.set)
    
    hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=tree.xview)
    hsb.pack(side=tk.BOTTOM, fill=tk.X)
    tree.configure(xscrollcommand=hsb.set)
    
    # Get the subset of the dataframe with missing fund IDs
    subset_df = dataframe[missing_mask].copy()
    
    # Configure columns
    tree["columns"] = list(subset_df.columns)
    tree["show"] = "headings"
    
    for col in subset_df.columns:
        tree.heading(col, text=col)
        tree.column(col, width=100)
    
    # Add data to treeview
    for idx, row in subset_df.iterrows():
        values = [str(row[col]) for col in subset_df.columns]
        tree.insert("", "end", iid=str(idx), values=values)
    
    # Store selected indices and fund assignments
    assignments = {}
    
    # Create a frame for fund selection
    fund_frame = ttk.LabelFrame(root, text="Fund Assignment")
    fund_frame.pack(pady=10, padx=10, fill=tk.X)
    
    # Fund selection combobox
    ttk.Label(fund_frame, text="Select Fund:").grid(row=0, column=0, padx=5, pady=5)
    fund_combo = ttk.Combobox(fund_frame, width=40)
    fund_combo.grid(row=0, column=1, padx=5, pady=5)
    
    # Get all funds for the combobox
    funds_df = fund_assigner.funds_df
    fund_id_col = fund_assigner._get_fund_id_column() or 'fund_id'
    fund_name_col = fund_assigner._get_fund_name_column() or 'name'
    
    if not isinstance(funds_df, dict) and not funds_df.empty and fund_id_col in funds_df.columns:
        fund_options = []
        for idx, row in funds_df.iterrows():
            fund_id = row[fund_id_col]
            fund_name = row[fund_name_col] if fund_name_col in funds_df.columns else f"Fund {fund_id}"
            fund_options.append(f"{fund_id}: {fund_name}")
        fund_combo['values'] = fund_options
    
    # Function to get the fund ID from the selected option
    def get_selected_fund_id():
        selection = fund_combo.get()
        if selection:
            return selection.split(":", 1)[0].strip()
        return None
    
    # Action buttons
    button_frame = ttk.Frame(fund_frame)
    button_frame.grid(row=1, column=0, columnspan=2, pady=10)
    
    def assign_to_selected():
        selected_items = tree.selection()
        if not selected_items:
            messagebox.showwarning("No Selection", "Please select at least one row")
            return
            
        fund_id = get_selected_fund_id()
        if not fund_id:
            messagebox.showwarning("No Fund", "Please select a fund")
            return
            
        # Assign the fund to all selected items
        for item in selected_items:
            idx = int(item)
            assignments[idx] = fund_id
            # Update the tree item
            values = list(tree.item(item, "values"))
            fund_idx = subset_df.columns.get_loc("fund_id")
            values[fund_idx] = fund_id
            tree.item(item, values=values)
            
        logger.info(f"Assigned fund {fund_id} to {len(selected_items)} rows in {table_name}")
    
    def assign_all():
        fund_id = get_selected_fund_id()
        if not fund_id:
            messagebox.showwarning("No Fund", "Please select a fund")
            return
            
        # Assign the fund to all items
        for idx in subset_df.index:
            assignments[idx] = fund_id
            # Update the tree item
            item = str(idx)
            values = list(tree.item(item, "values"))
            fund_idx = subset_df.columns.get_loc("fund_id")
            values[fund_idx] = fund_id
            tree.item(item, values=values)
            
        logger.info(f"Assigned fund {fund_id} to all {len(subset_df)} rows in {table_name}")
    
    def auto_assign():
        """Auto-assign funds based on suggestions"""
        for idx in subset_df.index:
            record = subset_df.loc[idx]
            suggestions = fund_assigner.get_fund_suggestions(record)
            if suggestions:
                fund_id = suggestions[0][1]
                assignments[idx] = fund_id
                # Update the tree item
                item = str(idx)
                values = list(tree.item(item, "values"))
                fund_idx = subset_df.columns.get_loc("fund_id")
                values[fund_idx] = fund_id
                tree.item(item, values=values)
                
        logger.info(f"Auto-assigned funds to {len(subset_df)} rows in {table_name}")
    
    def save_changes():
        """Save all fund assignments to the original dataframe"""
        if not assignments:
            messagebox.showinfo("No Changes", "No fund assignments have been made")
            return
            
        # Apply assignments to the original dataframe
        for idx, fund_id in assignments.items():
            dataframe.loc[idx, "fund_id"] = fund_id
            
        # Save the updated dataframe
        with log_duration(logger, f"Saving {table_name} with fund assignments"):
            result = tables_manager.save_table(table_name, dataframe)
            
        logger.info(f"Saved {len(assignments)} fund assignments to {table_name}")
        messagebox.showinfo("Success", f"Successfully saved {len(assignments)} fund assignments")
        root.destroy()
    
    ttk.Button(button_frame, text="Assign to Selected", command=assign_to_selected).pack(side=tk.LEFT, padx=5)
    ttk.Button(button_frame, text="Assign to All", command=assign_all).pack(side=tk.LEFT, padx=5)
    ttk.Button(button_frame, text="Auto-Assign", command=auto_assign).pack(side=tk.LEFT, padx=5)
    ttk.Button(button_frame, text="Save Changes", command=save_changes).pack(side=tk.LEFT, padx=5)
    ttk.Button(button_frame, text="Cancel", command=root.destroy).pack(side=tk.LEFT, padx=5)
    
    # Instructions
    instructions_text = (
        "1. Select rows in the table above\n"
        "2. Choose a fund from the dropdown\n"
        "3. Click 'Assign to Selected' or 'Assign to All'\n"
        "4. Use 'Auto-Assign' to apply suggested funds based on rules\n"
        "5. Click 'Save Changes' when done"
    )
    instructions = ttk.Label(root, text=instructions_text, justify=tk.LEFT)
    instructions.pack(pady=10, padx=10, anchor=tk.W)
    
    # Start the UI
    root.mainloop()

def main():
    """Main function"""
    # Set up logging to file
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"fund_id_fix_{timestamp}.log"
    
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    logger.addHandler(file_handler)
    
    logger.info("Starting fund_id_fix script")
    
    try:
        # Initialize the tables manager
        tables_manager = TablesManager()
    
    # Initialize fund assigner
    fund_assigner = FundAssigner(tables_manager)
    
        # Create a backup before making changes
        logger.info("Creating tables backup")
        backup_result = tables_manager.create_backup()
        logger.info(f"Backup result: {backup_result}")
        
        # Determine if we should use interactive mode
        interactive = True
        if len(sys.argv) > 1 and sys.argv[1].lower() in ('--auto', '-a'):
            interactive = False
            logger.info("Running in automatic mode")
    else:
            logger.info("Running in interactive mode")
        
        # Get username if provided
        username = "system"
        if len(sys.argv) > 2:
            username = sys.argv[2]
        
        # Fix fund IDs in invoices
        logger.info("Fixing missing fund IDs in Invoices")
        invoices_result = fix_invoices_fund_ids(tables_manager, fund_assigner, interactive, username)
        if 'error' in invoices_result:
            logger.error(f"Error fixing invoices: {invoices_result['error']}")
        else:
            logger.info(f"Updated {invoices_result['updated_count']} invoices")
        
        # Fix fund IDs in vendor allocations
        logger.info("Fixing missing fund IDs in Vendor allocation")
        alloc_result = fix_vendor_allocation_fund_ids(tables_manager, fund_assigner, interactive, username)
        if 'error' in alloc_result:
            logger.error(f"Error fixing vendor allocations: {alloc_result['error']}")
    else:
            logger.info(f"Updated {alloc_result['updated_count']} vendor allocations")
        
        logger.info("Fund ID fix completed successfully")
        
        if not interactive:
            # In interactive mode, the UI will show a message box
            total_updates = invoices_result.get('updated_count', 0) + alloc_result.get('updated_count', 0)
            print(f"Successfully updated {total_updates} records with missing fund IDs")
            
    except Exception as e:
        logger.error(f"Error in main process: {str(e)}", exc_info=True)
        print(f"Error: {str(e)}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
