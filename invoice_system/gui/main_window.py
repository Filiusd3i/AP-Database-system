"""
Main application window for the invoice processing system.

This module provides the main application window with navigation, menus,
and integration of the various components of the invoice processing system.
"""

import os
import logging
import sys
from PySide6.QtWidgets import (
    QMainWindow, QApplication, QTabWidget, QFileDialog,
    QMessageBox, QToolBar, QStatusBar, QWidget, QVBoxLayout,
    QLabel
)
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import Qt, QSize

from .invoice_viewer import InvoiceViewerWidget
from .dashboard.invoice_dashboard import InvoiceDashboardWidget
from ..document_processing import PatternLearningSystem
from ..database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class InvoiceAppMainWindow(QMainWindow):
    """Main window for the invoice processing application."""
    
    def __init__(self, parent=None):
        """Initialize the main application window.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Initialize UI properties
        self.setWindowTitle("Invoice Processing System")
        self.resize(1280, 900)
        
        # Initialize components
        self.pattern_learning_system = PatternLearningSystem()
        
        # Set up the UI
        self._create_actions()
        self._create_menus()
        self._create_toolbars()
        self._create_status_bar()
        self._create_central_widget()
        
        # Show status message
        self.status_bar.showMessage("Ready", 3000)
    
    def _create_actions(self):
        """Create actions for menus and toolbars."""
        # File menu actions
        self.open_action = QAction("Open Invoice", self)
        self.open_action.setShortcut("Ctrl+O")
        self.open_action.triggered.connect(self.open_invoice)
        
        self.exit_action = QAction("Exit", self)
        self.exit_action.setShortcut("Ctrl+Q")
        self.exit_action.triggered.connect(self.close)
        
        # Process menu actions
        self.process_action = QAction("Process Current Invoice", self)
        self.process_action.setShortcut("Ctrl+P")
        self.process_action.triggered.connect(self.process_current_invoice)
        self.process_action.setEnabled(False)
        
        self.batch_process_action = QAction("Batch Process Folder", self)
        self.batch_process_action.setShortcut("Ctrl+B")
        self.batch_process_action.triggered.connect(self.batch_process_folder)
        
        # View menu actions
        self.toggle_toolbar_action = QAction("Show Toolbar", self)
        self.toggle_toolbar_action.setCheckable(True)
        self.toggle_toolbar_action.setChecked(True)
        self.toggle_toolbar_action.triggered.connect(self.toggle_toolbar)
        
        # Help menu actions
        self.about_action = QAction("About", self)
        self.about_action.triggered.connect(self.show_about_dialog)
    
    def _create_menus(self):
        """Create the application menus."""
        # Main menu bar
        menu_bar = self.menuBar()
        
        # File menu
        file_menu = menu_bar.addMenu("File")
        file_menu.addAction(self.open_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)
        
        # Process menu
        process_menu = menu_bar.addMenu("Process")
        process_menu.addAction(self.process_action)
        process_menu.addAction(self.batch_process_action)
        
        # View menu
        view_menu = menu_bar.addMenu("View")
        view_menu.addAction(self.toggle_toolbar_action)
        
        # Help menu
        help_menu = menu_bar.addMenu("Help")
        help_menu.addAction(self.about_action)
    
    def _create_toolbars(self):
        """Create the application toolbars."""
        # Main toolbar
        self.toolbar = QToolBar("Main Toolbar", self)
        self.toolbar.setMovable(False)
        self.toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(self.toolbar)
        
        # Add actions to the toolbar
        self.toolbar.addAction(self.open_action)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.process_action)
        self.toolbar.addAction(self.batch_process_action)
    
    def _create_status_bar(self):
        """Create the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
    
    def _create_central_widget(self):
        """Create the central widget with tabs."""
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.TabPosition.North)
        self.tab_widget.setDocumentMode(True)
        
        # Initialize the database connection
        try:
            self.db_connection = DatabaseConnection()
            db_initialized = self.db_connection.initialize_database()
            if db_initialized:
                logger.info("Database initialized successfully")
            else:
                logger.info("Using existing database")
                
            # Ensure the database has the required structure for private equity fund management
            from finance_assistant.database.manager import DatabaseManager
            db_manager = DatabaseManager()
            if db_manager.is_connected:
                db_manager.ensure_private_equity_schema()
                logger.info("Private equity schema ensured")
            else:
                logger.warning("Could not ensure private equity schema - database not connected")
                
        except Exception as e:
            logger.error(f"Database initialization error: {str(e)}", exc_info=True)
            QMessageBox.critical(
                self, "Database Error",
                f"Could not initialize database: {str(e)}\n\n"
                f"Application may not function properly."
            )
            self.db_connection = None
        
        # Create tabs
        self._create_invoice_viewer_tab()
        self._create_dashboard_tab()
        
        # Set as central widget
        self.setCentralWidget(self.tab_widget)
    
    def _create_invoice_viewer_tab(self):
        """Create the invoice viewer tab."""
        self.invoice_viewer = InvoiceViewerWidget(self.pattern_learning_system)
        self.invoice_viewer.correctionSubmitted.connect(self.handle_correction_submitted)
        
        self.tab_widget.addTab(self.invoice_viewer, "Invoice Viewer")
    
    def _create_dashboard_tab(self):
        """Create the invoice dashboard tab."""
        if self.db_connection:
            self.invoice_dashboard = InvoiceDashboardWidget(self.db_connection)
            self.tab_widget.addTab(self.invoice_dashboard, "Invoice Dashboard")
            
            # Connect signals
            self.invoice_viewer.correctionSubmitted.connect(self._handle_extraction_saved)
        else:
            # If database connection failed, create an empty widget with a message
            error_widget = QWidget()
            error_layout = QVBoxLayout(error_widget)
            error_label = QLabel("Dashboard unavailable: Database connection failed.")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            error_layout.addWidget(error_label)
            
            self.tab_widget.addTab(error_widget, "Invoice Dashboard")
    
    def open_invoice(self):
        """Open an invoice file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Invoice File", "", "PDF Files (*.pdf)"
        )
        
        if file_path:
            # Attempt to load the invoice
            success = self.invoice_viewer.load_invoice(file_path)
            
            if success:
                self.status_bar.showMessage(f"Loaded: {os.path.basename(file_path)}", 5000)
                self.process_action.setEnabled(True)
                # Ensure the invoice viewer tab is selected
                self.tab_widget.setCurrentWidget(self.invoice_viewer)
    
    def process_current_invoice(self):
        """Process the current invoice."""
        self.invoice_viewer.process_current_invoice()
        self.status_bar.showMessage("Processing complete", 5000)
    
    def batch_process_folder(self):
        """Batch process a folder of invoices."""
        # This will be implemented in a future version
        QMessageBox.information(
            self,
            "Batch Processing",
            "Batch processing will be available in a future update."
        )
    
    def toggle_toolbar(self, checked):
        """Toggle the visibility of the toolbar.
        
        Args:
            checked: Whether the toolbar should be visible
        """
        self.toolbar.setVisible(checked)
    
    def handle_correction_submitted(self, corrected_data, file_path):
        """Handle when a correction is submitted in the invoice viewer.
        
        Args:
            corrected_data: Dictionary of corrected invoice data
            file_path: Path to the invoice file
        """
        self.status_bar.showMessage(
            f"Corrections saved for: {os.path.basename(file_path)}", 
            5000
        )
        
        # If we have a dashboard, pass the data there as well
        if hasattr(self, 'db_connection') and self.db_connection:
            self._handle_extraction_saved(corrected_data, file_path)
    
    def _handle_extraction_saved(self, data, file_path):
        """Handle saving extracted invoice data to the database.
        
        Args:
            data: Dictionary of invoice data
            file_path: Path to the invoice file
        """
        try:
            with self.db_connection.session() as session:
                from invoice_system.database.repositories import InvoiceRepository, VendorRepository, FundRepository
                from invoice_system.database.models import InvoiceRecord
                
                # Get or create vendor
                vendor_repo = VendorRepository(session)
                vendor = vendor_repo.get_by_name(data.get('vendor_name', ''))
                if not vendor and data.get('vendor_name'):
                    vendor = vendor_repo.create({'name': data.get('vendor_name')})
                
                # Get or create fund
                fund_repo = FundRepository(session)
                fund = fund_repo.get_by_name(data.get('fund_name', ''))
                if not fund and data.get('fund_name'):
                    fund = fund_repo.create({'name': data.get('fund_name')})
                
                # Get or create invoice
                invoice_repo = InvoiceRepository(session)
                invoice_number = data.get('invoice_number', '')
                invoice = invoice_repo.get_by_invoice_number(invoice_number) if invoice_number else None
                
                # Create or update invoice
                import datetime
                
                # Prepare invoice data
                invoice_data = {
                    'invoice_number': invoice_number,
                    'vendor_id': vendor.id if vendor else None,
                    'fund_id': fund.id if fund else None,
                    'invoice_date': datetime.datetime.strptime(data.get('invoice_date', ''), '%Y-%m-%d') 
                                   if data.get('invoice_date') else datetime.datetime.now(),
                    'total_amount': float(data.get('total_amount', 0)),
                    'file_path': file_path,
                    'extraction_confidence': data.get('overall_confidence', 0)
                }
                
                # Create or update invoice
                if invoice:
                    invoice_repo.update(invoice.id, invoice_data)
                    logger.info(f"Updated invoice {invoice_number} in database")
                else:
                    invoice = invoice_repo.create(invoice_data)
                    logger.info(f"Created new invoice {invoice_number} in database")
                
                # Refresh dashboard if available
                if hasattr(self, 'invoice_dashboard'):
                    self.invoice_dashboard.refresh_data()
                
        except Exception as e:
            logger.error(f"Error saving invoice to database: {str(e)}", exc_info=True)
            # Don't show error to user since this is a background operation
    
    def show_about_dialog(self):
        """Show the about dialog."""
        QMessageBox.about(
            self,
            "About Invoice Processing System",
            "<h3>Invoice Processing System</h3>"
            "<p>A system for processing and managing invoices with "
            "OCR, data extraction, and pattern learning capabilities.</p>"
            "<p>Version 1.0</p>"
        )


def main():
    """Run the invoice system application."""
    import sys
    from PySide6.QtWidgets import QApplication
    from invoice_system.logging_config import configure_logging
    
    # Configure logging
    logger = configure_logging()
    
    # Create and run application
    app = QApplication(sys.argv)
    window = InvoiceAppMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
