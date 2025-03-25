import os
import csv
import re
from tkinter import filedialog

class ExportManager:
    def __init__(self, app):
        self.app = app
    
    def is_export_request(self, text):
        """Check if the user is requesting to export data"""
        export_patterns = [
            r'(export|save|download|convert).*(csv|excel|file)',
            r'(save|export).*results',
            r'(create|make|generate).*(csv|excel|file)'
        ]
        
        return any(re.search(pattern, text.lower()) for pattern in export_patterns)
    
    def export_to_csv(self, results):
        """Export the query result to a CSV file"""
        if not results or 'rows' not in results or not results['rows']:
            self.app.ui_manager.display_message("Assistant", "There's no data to export. Please run a query first.")
            return
            
        # Ask user for save location
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Save Data As CSV"
        )
        
        if not file_path:
            return  # User cancelled
            
        try:
            with open(file_path, 'w', newline='') as csvfile:
                csv_writer = csv.writer(csvfile)
                
                # Write headers
                csv_writer.writerow(results['columns'])
                
                # Write data rows
                for row in results['rows']:
                    csv_writer.writerow(row)
                    
            self.app.ui_manager.display_message("Assistant", f"Data successfully exported to {os.path.basename(file_path)}")
        except Exception as e:
            self.app.ui_manager.display_message("Assistant", f"Error exporting data: {str(e)}") 