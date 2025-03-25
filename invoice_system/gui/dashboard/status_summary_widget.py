"""
Status summary widget for the invoice dashboard.

This module provides a widget that displays summary information about invoices,
including counts by status and due date metrics.
"""

import logging
from datetime import datetime, date
from typing import Dict, Optional

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
    QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QPalette

from invoice_system.database.connection import DatabaseConnection
from invoice_system.database.repositories import InvoiceRepository
from invoice_system.database.models import InvoiceStatus

logger = logging.getLogger(__name__)


class StatusCard(QFrame):
    """Card displaying a status count with label."""
    
    def __init__(self, title: str, count: int = 0, color: str = "#ffffff", parent=None):
        """Initialize the status card.
        
        Args:
            title: Title of the card
            count: Initial count value
            color: Background color (hex string)
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Set frame properties
        self.setFrameShape(QFrame.Shape.Box)
        self.setLineWidth(1)
        self.setMidLineWidth(0)
        
        # Set size policy
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(100)
        
        # Set background color
        self.setStyleSheet(f"""
            StatusCard {{
                background-color: {color};
                border-radius: 4px;
                border: 1px solid #cccccc;
            }}
            QLabel {{
                background-color: transparent;
            }}
        """)
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        # Create count label
        self.count_label = QLabel(str(count))
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.count_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        
        # Create title label
        self.title_label = QLabel(title)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("font-size: 14px;")
        
        # Add labels to layout
        layout.addWidget(self.count_label)
        layout.addWidget(self.title_label)
    
    def set_count(self, count: int):
        """Update the count value.
        
        Args:
            count: New count value
        """
        self.count_label.setText(str(count))
    
    def get_count(self) -> int:
        """Get the current count value.
        
        Returns:
            Current count value
        """
        return int(self.count_label.text())


class StatusSummaryWidget(QWidget):
    """Widget displaying summary of invoice statuses."""
    
    STATUS_COLORS = {
        'total': "#f8f9fa",
        'pending': "#fff3cd",
        'approved': "#d1e7dd",
        'paid': "#cfe2ff",
        'disputed': "#f8d7da",
        'overdue': "#ffe0e0"
    }
    
    def __init__(self, db_connection: DatabaseConnection, parent=None):
        """Initialize the status summary widget.
        
        Args:
            db_connection: Database connection manager
            parent: Parent widget
        """
        super().__init__(parent)
        self.db_connection = db_connection
        
        # Create UI components
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the UI components."""
        # Create layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Create status cards
        self.total_card = StatusCard(
            "Total Invoices", 0, self.STATUS_COLORS['total']
        )
        self.pending_card = StatusCard(
            "Pending", 0, self.STATUS_COLORS['pending']
        )
        self.approved_card = StatusCard(
            "Approved", 0, self.STATUS_COLORS['approved']
        )
        self.paid_card = StatusCard(
            "Paid", 0, self.STATUS_COLORS['paid']
        )
        self.disputed_card = StatusCard(
            "Disputed", 0, self.STATUS_COLORS['disputed']
        )
        self.overdue_card = StatusCard(
            "Overdue", 0, self.STATUS_COLORS['overdue']
        )
        
        # Add cards to layout
        layout.addWidget(self.total_card)
        layout.addWidget(self.pending_card)
        layout.addWidget(self.approved_card)
        layout.addWidget(self.paid_card)
        layout.addWidget(self.disputed_card)
        layout.addWidget(self.overdue_card)
    
    def update_summary(self, 
                     start_date: Optional[date] = None,
                     end_date: Optional[date] = None,
                     fund_id: Optional[int] = None):
        """Update the summary with current data.
        
        Args:
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            fund_id: Optional fund ID for filtering
        """
        try:
            # Set defaults if not provided
            if start_date is None:
                start_date = datetime.now().date().replace(day=1)  # First day of current month
            if end_date is None:
                end_date = datetime.now().date()
            
            with self.db_connection.session() as session:
                # Create repository
                invoice_repo = InvoiceRepository(session)
                
                # Get status summary
                status_summary = invoice_repo.get_status_summary(
                    start_date, end_date, fund_id
                )
                
                # Get overdue invoices
                overdue_invoices = invoice_repo.get_overdue()
                
                # Update status cards
                total = sum(status_summary.values())
                self.total_card.set_count(total)
                self.pending_card.set_count(status_summary.get('pending', 0))
                self.approved_card.set_count(status_summary.get('approved', 0))
                self.paid_card.set_count(status_summary.get('paid', 0))
                self.disputed_card.set_count(status_summary.get('disputed', 0))
                self.overdue_card.set_count(len(overdue_invoices))
                
        except Exception as e:
            logger.error(f"Error updating status summary: {str(e)}", exc_info=True)
