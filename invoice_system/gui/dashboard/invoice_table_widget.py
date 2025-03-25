"""
Invoice table widget for displaying invoice data with sorting and filtering.

This module provides a table widget that displays invoice data with support for
sorting, filtering, and selection.
"""

import logging
from datetime import datetime, date
from typing import List, Dict, Any, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableView, 
    QAbstractItemView, QHeaderView, QLabel
)
from PySide6.QtCore import Qt, Signal, QSortFilterProxyModel, QDate, QModelIndex
from PySide6.QtGui import QStandardItemModel, QStandardItem, QColor, QBrush

from invoice_system.database.connection import DatabaseConnection
from invoice_system.database.models import InvoiceStatus
from invoice_system.database.repositories import InvoiceRepository

logger = logging.getLogger(__name__)


class InvoiceTableWidget(QWidget):
    """Widget for displaying invoice data in a table with sorting/filtering."""
    
    # Signal emitted when the selection changes
    selectionChanged = Signal()
    
    def __init__(self, db_connection: DatabaseConnection, parent=None):
        """Initialize the invoice table widget.
        
        Args:
            db_connection: Database connection manager
            parent: Parent widget
        """
        super().__init__(parent)
        self.db_connection = db_connection
        
        # Column definitions
        self.columns = [
            {'name': 'ID', 'key': 'id', 'visible': False, 'width': None},
            {'name': 'Invoice #', 'key': 'invoice_number', 'visible': True, 'width': 100},
            {'name': 'Vendor', 'key': 'vendor_name', 'visible': True, 'width': 150},
            {'name': 'Fund', 'key': 'fund_name', 'visible': True, 'width': 120},
            {'name': 'Date', 'key': 'invoice_date', 'visible': True, 'width': 100},
            {'name': 'Due Date', 'key': 'due_date', 'visible': True, 'width': 100},
            {'name': 'Amount', 'key': 'total_amount', 'visible': True, 'width': 100},
            {'name': 'Status', 'key': 'status', 'visible': True, 'width': 100},
            {'name': 'Approved By', 'key': 'approved_by', 'visible': True, 'width': 120},
            {'name': 'Approval Date', 'key': 'approval_date', 'visible': True, 'width': 100},
        ]
        
        # Create model
        self.model = QStandardItemModel(0, len(self.columns))
        
        # Set header data
        for i, col in enumerate(self.columns):
            self.model.setHeaderData(i, Qt.Orientation.Horizontal, col['name'])
        
        # Create proxy model for sorting/filtering
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        
        # Current data
        self.current_data = []
        
        # Create UI
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the UI components."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create table view
        self.table_view = QTableView()
        self.table_view.setModel(self.proxy_model)
        
        # Set selection behavior
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        
        # Set sorting
        self.table_view.setSortingEnabled(True)
        
        # Set column widths and visibility
        header = self.table_view.horizontalHeader()
        for i, col in enumerate(self.columns):
            if not col.get('visible', True):
                self.table_view.setColumnHidden(i, True)
            elif col.get('width'):
                self.table_view.setColumnWidth(i, col['width'])
        
        # Set header properties
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        
        # Set alternating row colors
        self.table_view.setAlternatingRowColors(True)
        
        # Connect selection changed signal
        self.table_view.selectionModel().selectionChanged.connect(
            lambda: self.selectionChanged.emit()
        )
        
        # Add to layout
        layout.addWidget(self.table_view)
    
    def apply_filters(self, start_date: date, end_date: date, 
                     fund_id: Optional[int] = None, 
                     status: Optional[str] = None):
        """Apply filters to the table data.
        
        Args:
            start_date: Start date for filtering
            end_date: End date for filtering
            fund_id: Optional fund ID to filter by (-1 for all funds)
            status: Optional status to filter by ('all' for all statuses)
        """
        try:
            with self.db_connection.session() as session:
                # Create repository
                invoice_repo = InvoiceRepository(session)
                
                # Get invoices based on filters
                if status and status != 'all':
                    # Convert string status to enum
                    status_enum = next(
                        (s for s in InvoiceStatus if s.value == status),
                        None
                    )
                    if status_enum:
                        invoices = invoice_repo.get_by_status_and_date_range(
                            status_enum, start_date, end_date, fund_id if fund_id != -1 else None
                        )
                    else:
                        # Fallback if status not found
                        invoices = invoice_repo.get_by_date_range(
                            start_date, end_date, fund_id if fund_id != -1 else None
                        )
                else:
                    # Get all invoices in date range
                    invoices = invoice_repo.get_by_date_range(
                        start_date, end_date, fund_id if fund_id != -1 else None
                    )
                
                # Update the table with the filtered data
                self._update_table_data(invoices)
        
        except Exception as e:
            logger.error(f"Error applying filters: {str(e)}", exc_info=True)
            raise
    
    def _update_table_data(self, invoices: List[Any]):
        """Update the table data with the given invoices.
        
        Args:
            invoices: List of invoice records
        """
        # Clear current data
        self.model.removeRows(0, self.model.rowCount())
        self.current_data = []
        
        # Add each invoice to the model
        for invoice in invoices:
            # Extract data for display
            row_data = {
                'id': invoice.id,
                'invoice_number': invoice.invoice_number,
                'vendor_name': invoice.vendor.name if invoice.vendor else '',
                'fund_name': invoice.fund.name if invoice.fund else '',
                'invoice_date': invoice.invoice_date.strftime('%Y-%m-%d') if invoice.invoice_date else '',
                'due_date': invoice.due_date.strftime('%Y-%m-%d') if invoice.due_date else '',
                'total_amount': f"${float(invoice.total_amount):,.2f}",
                'status': invoice.status.value.capitalize(),
                'approved_by': invoice.approved_by or '',
                'approval_date': invoice.approval_date.strftime('%Y-%m-%d') if invoice.approval_date else '',
                'invoice': invoice  # Store the original invoice object for reference
            }
            
            # Add to current data
            self.current_data.append(row_data)
            
            # Create row items
            row_items = []
            for col in self.columns:
                item = QStandardItem(str(row_data.get(col['key'], '')))
                
                # Set raw invoice ID as user data for the ID column
                if col['key'] == 'id':
                    item.setData(invoice.id, Qt.ItemDataRole.UserRole)
                
                # Set alignment for numeric columns
                if col['key'] in ['total_amount']:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                
                # Set background color based on status
                if col['key'] == 'status':
                    if invoice.status == InvoiceStatus.PENDING:
                        item.setBackground(QBrush(QColor("#fff3cd")))  # Light yellow
                    elif invoice.status == InvoiceStatus.APPROVED:
                        item.setBackground(QBrush(QColor("#d1e7dd")))  # Light green
                    elif invoice.status == InvoiceStatus.PAID:
                        item.setBackground(QBrush(QColor("#cfe2ff")))  # Light blue
                    elif invoice.status == InvoiceStatus.DISPUTED:
                        item.setBackground(QBrush(QColor("#f8d7da")))  # Light red
                
                row_items.append(item)
            
            # Add row to model
            self.model.appendRow(row_items)
            
        # Force layout update
        self.table_view.resizeColumnsToContents()
    
    def has_selection(self) -> bool:
        """Check if a row is selected.
        
        Returns:
            True if a row is selected, False otherwise
        """
        return len(self.table_view.selectionModel().selectedRows()) > 0
    
    def get_selected_invoice_id(self) -> Optional[int]:
        """Get the ID of the selected invoice.
        
        Returns:
            Invoice ID if a row is selected, None otherwise
        """
        if not self.has_selection():
            return None
        
        # Get selected row
        selected_rows = self.table_view.selectionModel().selectedRows()
        if not selected_rows:
            return None
        
        # Get the proxy model index
        proxy_index = selected_rows[0]
        
        # Convert to source model index
        source_index = self.proxy_model.mapToSource(proxy_index)
        
        # Get the ID from the ID column
        id_index = self.model.index(source_index.row(), 0)  # 0 is the ID column
        invoice_id = self.model.data(id_index, Qt.ItemDataRole.UserRole)
        
        return invoice_id
    
    def get_selected_invoice(self) -> Optional[Dict[str, Any]]:
        """Get the selected invoice data.
        
        Returns:
            Dictionary with invoice data if a row is selected, None otherwise
        """
        if not self.has_selection():
            return None
        
        invoice_id = self.get_selected_invoice_id()
        if invoice_id is None:
            return None
        
        # Find the invoice data in current_data
        for invoice in self.current_data:
            if invoice.get('id') == invoice_id:
                return invoice
        
        return None
    
    def get_current_data(self) -> List[Dict[str, Any]]:
        """Get the current data displayed in the table.
        
        Returns:
            List of dictionaries with invoice data
        """
        return self.current_data
