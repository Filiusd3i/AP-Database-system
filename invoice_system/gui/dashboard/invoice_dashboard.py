"""
Main dashboard widget for the invoice management system.

This module provides the primary dashboard interface for managing invoices,
viewing analytics, and performing invoice-related operations.
"""

import logging
from datetime import datetime, timedelta, date
from typing import Optional, Dict, List, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, 
    QPushButton, QTabWidget, QLabel, QComboBox,
    QDateEdit, QMessageBox, QHeaderView, QFileDialog
)
from PySide6.QtCore import Qt, Signal, Slot, QDate, QSize
from PySide6.QtGui import QIcon

from invoice_system.database.connection import DatabaseConnection
from invoice_system.database.models import InvoiceStatus
from invoice_system.database.repositories import (
    InvoiceRepository, FundRepository, VendorRepository, 
    PaymentRepository, ExpenseCategoryRepository
)

from .invoice_table_widget import InvoiceTableWidget
from .status_summary_widget import StatusSummaryWidget

logger = logging.getLogger(__name__)


class InvoiceDashboardWidget(QWidget):
    """Main dashboard widget for invoice management."""
    
    # Signals
    invoice_updated = Signal(int)  # Emitted when an invoice is updated
    
    def __init__(self, db_connection: DatabaseConnection, parent=None):
        """Initialize the invoice dashboard.
        
        Args:
            db_connection: Database connection manager
            parent: Parent widget
        """
        super().__init__(parent)
        self.db_connection = db_connection
        
        # Initialize UI components
        self._setup_ui()
        
        # Load initial data
        self.refresh_data()
    
    def _setup_ui(self):
        """Set up the dashboard UI."""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Header section with filter controls
        header_layout = QHBoxLayout()
        
        # Date range selector
        date_layout = QVBoxLayout()
        date_layout.addWidget(QLabel("Date Range:"))
        date_selector = QHBoxLayout()
        
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addMonths(-1))
        self.start_date.setCalendarPopup(True)
        date_selector.addWidget(QLabel("From:"))
        date_selector.addWidget(self.start_date)
        
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        date_selector.addWidget(QLabel("To:"))
        date_selector.addWidget(self.end_date)
        
        date_layout.addLayout(date_selector)
        header_layout.addLayout(date_layout)
        
        # Fund selector
        fund_layout = QVBoxLayout()
        fund_layout.addWidget(QLabel("Fund:"))
        self.fund_selector = QComboBox()
        self.fund_selector.addItem("All Funds", -1)
        fund_layout.addWidget(self.fund_selector)
        header_layout.addLayout(fund_layout)
        
        # Status selector
        status_layout = QVBoxLayout()
        status_layout.addWidget(QLabel("Status:"))
        self.status_selector = QComboBox()
        self.status_selector.addItem("All Statuses", "all")
        for status in InvoiceStatus:
            self.status_selector.addItem(status.value.capitalize(), status.value)
        status_layout.addWidget(self.status_selector)
        header_layout.addLayout(status_layout)
        
        # Apply filters button
        self.apply_filters_btn = QPushButton("Apply Filters")
        header_layout.addWidget(self.apply_filters_btn)
        
        # Add stretch to push controls to the left
        header_layout.addStretch(1)
        
        # Refresh button
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setToolTip("Refresh data from database")
        header_layout.addWidget(self.refresh_btn)
        
        main_layout.addLayout(header_layout)
        
        # Status summary cards
        self.status_summary = StatusSummaryWidget(self.db_connection)
        main_layout.addWidget(self.status_summary)
        
        # Split view with table and details
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Invoice table
        self.invoice_table = InvoiceTableWidget(self.db_connection)
        splitter.addWidget(self.invoice_table)
        
        # Details tab widget
        self.details_tab = QTabWidget()
        
        # Invoice details tab
        self.invoice_details = QWidget()
        self.details_tab.addTab(self.invoice_details, "Invoice Details")
        
        # Analytics tabs will be added in future implementation
        
        splitter.addWidget(self.details_tab)
        
        # Set initial sizes (60% table, 40% details)
        splitter.setSizes([600, 400])
        main_layout.addWidget(splitter, 1)  # Give the splitter a stretch factor
        
        # Action buttons
        actions_layout = QHBoxLayout()
        
        self.view_details_btn = QPushButton("View Details")
        self.view_details_btn.setEnabled(False)
        
        self.approve_btn = QPushButton("Approve Invoice")
        self.approve_btn.setEnabled(False)
        
        self.payment_btn = QPushButton("Record Payment")
        self.payment_btn.setEnabled(False)
        
        self.dispute_btn = QPushButton("Mark Disputed")
        self.dispute_btn.setEnabled(False)
        
        self.export_btn = QPushButton("Export Data")
        
        actions_layout.addWidget(self.view_details_btn)
        actions_layout.addWidget(self.approve_btn)
        actions_layout.addWidget(self.payment_btn)
        actions_layout.addWidget(self.dispute_btn)
        actions_layout.addStretch(1)
        actions_layout.addWidget(self.export_btn)
        
        main_layout.addLayout(actions_layout)
        
        # Connect signals and slots
        self._connect_signals()
    
    def _connect_signals(self):
        """Connect signals and slots."""
        # Filter and refresh connections
        self.apply_filters_btn.clicked.connect(self._apply_filters)
        self.refresh_btn.clicked.connect(self.refresh_data)
        
        # Table selection changed
        self.invoice_table.selectionChanged.connect(self._handle_selection_changed)
        
        # Action button connections
        self.view_details_btn.clicked.connect(self._view_invoice_details)
        self.approve_btn.clicked.connect(self._approve_invoice)
        self.payment_btn.clicked.connect(self._record_payment)
        self.dispute_btn.clicked.connect(self._mark_disputed)
        self.export_btn.clicked.connect(self._export_data)
    
    def _update_button_states(self):
        """Update action button states based on selection."""
        has_selection = self.invoice_table.has_selection()
        
        self.view_details_btn.setEnabled(has_selection)
        
        # Get selected invoice status if there's a selection
        selected_status = None
        if has_selection:
            invoice_id = self.invoice_table.get_selected_invoice_id()
            if invoice_id:
                with self.db_connection.session() as session:
                    repo = InvoiceRepository(session)
                    invoice = repo.get_by_id(invoice_id)
                    if invoice:
                        selected_status = invoice.status
        
        # Enable/disable action buttons based on status
        if selected_status:
            self.approve_btn.setEnabled(selected_status == InvoiceStatus.PENDING)
            self.payment_btn.setEnabled(selected_status in [
                InvoiceStatus.APPROVED, 
                InvoiceStatus.PENDING
            ])
            self.dispute_btn.setEnabled(selected_status != InvoiceStatus.DISPUTED)
        else:
            self.approve_btn.setEnabled(False)
            self.payment_btn.setEnabled(False)
            self.dispute_btn.setEnabled(False)
    
    @Slot()
    def _apply_filters(self):
        """Apply dashboard filters."""
        try:
            start_date = self.start_date.date().toPython()
            end_date = self.end_date.date().toPython()
            fund_id = self.fund_selector.currentData()
            status = self.status_selector.currentData()
            
            # Apply filters to invoice table
            self.invoice_table.apply_filters(start_date, end_date, fund_id, status)
            
            # Update summary
            self.status_summary.update_summary(start_date, end_date, fund_id)
            
        except Exception as e:
            logger.error(f"Error applying filters: {str(e)}", exc_info=True)
            QMessageBox.warning(
                self, "Filter Error", 
                f"Error applying filters: {str(e)}"
            )
    
    @Slot()
    def _handle_selection_changed(self):
        """Handle table selection change."""
        self._update_button_states()
        self._update_details_view()
    
    def _update_details_view(self):
        """Update the details view with the selected invoice."""
        # This will be implemented in future to show invoice details
        pass
    
    @Slot()
    def _view_invoice_details(self):
        """Show invoice details dialog."""
        invoice_id = self.invoice_table.get_selected_invoice_id()
        if invoice_id:
            # This will be implemented in future to show a detailed view
            QMessageBox.information(
                self, "Invoice Details", 
                f"Showing details for invoice #{invoice_id}\n\n"
                f"This functionality will be fully implemented in a future update."
            )
    
    @Slot()
    def _approve_invoice(self):
        """Approve the selected invoice."""
        invoice_id = self.invoice_table.get_selected_invoice_id()
        if not invoice_id:
            return
            
        reply = QMessageBox.question(
            self, "Approve Invoice",
            "Do you want to approve this invoice?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                with self.db_connection.session() as session:
                    repo = InvoiceRepository(session)
                    approved_by = "Current User"  # This would be the actual logged-in user
                    invoice = repo.approve(invoice_id, approved_by)
                    
                    if invoice:
                        QMessageBox.information(
                            self, "Invoice Approved",
                            f"Invoice #{invoice.invoice_number} has been approved."
                        )
                        self.refresh_data()
                        self.invoice_updated.emit(invoice_id)
                    else:
                        QMessageBox.warning(
                            self, "Approval Failed",
                            "Could not find the selected invoice."
                        )
            except Exception as e:
                logger.error(f"Error approving invoice: {str(e)}", exc_info=True)
                QMessageBox.critical(
                    self, "Approval Error",
                    f"Error approving invoice: {str(e)}"
                )
    
    @Slot()
    def _record_payment(self):
        """Record payment for the selected invoice."""
        invoice_id = self.invoice_table.get_selected_invoice_id()
        if not invoice_id:
            return
            
        # This will be implemented in future for payment recording
        QMessageBox.information(
            self, "Record Payment", 
            f"Payment recording for invoice #{invoice_id}\n\n"
            f"This functionality will be fully implemented in a future update."
        )
    
    @Slot()
    def _mark_disputed(self):
        """Mark selected invoice as disputed."""
        invoice_id = self.invoice_table.get_selected_invoice_id()
        if not invoice_id:
            return
            
        # This will be implemented in future for dispute handling
        QMessageBox.information(
            self, "Mark Disputed", 
            f"Marking invoice #{invoice_id} as disputed\n\n"
            f"This functionality will be fully implemented in a future update."
        )
    
    @Slot()
    def _export_data(self):
        """Export invoice data to CSV."""
        try:
            # Get file path from user
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Export Invoice Data", "", "CSV Files (*.csv)"
            )
            
            if not file_path:
                return
                
            # Add .csv extension if not present
            if not file_path.endswith('.csv'):
                file_path += '.csv'
                
            # Get invoice data
            invoices = self.invoice_table.get_current_data()
            
            # Export to CSV
            import csv
            
            with open(file_path, 'w', newline='') as csvfile:
                # Define fieldnames
                fieldnames = [
                    'invoice_number', 'vendor_name', 'fund_name', 
                    'invoice_date', 'due_date', 'total_amount', 
                    'status', 'approval_date', 'approved_by'
                ]
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for invoice in invoices:
                    writer.writerow({
                        'invoice_number': invoice.get('invoice_number', ''),
                        'vendor_name': invoice.get('vendor_name', ''),
                        'fund_name': invoice.get('fund_name', ''),
                        'invoice_date': invoice.get('invoice_date', ''),
                        'due_date': invoice.get('due_date', ''),
                        'total_amount': invoice.get('total_amount', ''),
                        'status': invoice.get('status', ''),
                        'approval_date': invoice.get('approval_date', ''),
                        'approved_by': invoice.get('approved_by', '')
                    })
                    
                QMessageBox.information(
                    self, "Export Successful", 
                    f"Invoice data exported successfully to {file_path}"
                )
        except Exception as e:
            logger.error(f"Error exporting data: {str(e)}", exc_info=True)
            QMessageBox.critical(
                self, "Export Error", 
                f"Error exporting data: {str(e)}"
            )
    
    @Slot()
    def refresh_data(self):
        """Refresh all dashboard data."""
        try:
            # Load funds for selector
            self._load_funds()
            
            # Apply filters to refresh data
            self._apply_filters()
            
            # Update button states
            self._update_button_states()
            
        except Exception as e:
            logger.error(f"Error refreshing data: {str(e)}", exc_info=True)
            QMessageBox.warning(
                self, "Refresh Error", 
                f"Error refreshing data: {str(e)}"
            )
    
    def _load_funds(self):
        """Load fund data for the fund selector."""
        try:
            with self.db_connection.session() as session:
                fund_repo = FundRepository(session)
                funds = fund_repo.get_all()
                
                # Clear current items except "All Funds"
                while self.fund_selector.count() > 1:
                    self.fund_selector.removeItem(1)
                
                # Add funds to selector
                for fund in funds:
                    self.fund_selector.addItem(fund.name, fund.id)
        except Exception as e:
            logger.error(f"Error loading funds: {str(e)}", exc_info=True)
            QMessageBox.warning(
                self, "Data Loading Error", 
                f"Error loading fund data: {str(e)}"
            )
