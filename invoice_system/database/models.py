"""
Database models for the invoice system.

This module defines the data models used in the invoice system,
including enums and data classes.
"""

import enum
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional, List


class InvoiceStatus(enum.Enum):
    """Invoice status enum."""
    PENDING = "pending"
    APPROVED = "approved"
    PAID = "paid"
    DISPUTED = "disputed"
    OVERDUE = "overdue"
    CANCELED = "canceled"


class PaymentMethod(enum.Enum):
    """Payment method enum."""
    CHECK = "check"
    WIRE = "wire"
    ACH = "ach"
    CREDIT_CARD = "credit_card"
    CASH = "cash"
    OTHER = "other"


@dataclass
class InvoiceRecord:
    """Invoice record data class."""
    id: int
    invoice_number: str
    vendor_name: str
    invoice_date: date
    due_date: Optional[date] = None
    total_amount: float = 0.0
    status: InvoiceStatus = InvoiceStatus.PENDING
    payment_date: Optional[date] = None
    payment_reference: Optional[str] = None
    payment_method: Optional[PaymentMethod] = None
    fund_name: Optional[str] = None
    deal_name: Optional[str] = None
    description: Optional[str] = None
    approved_by: Optional[str] = None
    approval_date: Optional[date] = None
    created_at: datetime = None
    
    def __post_init__(self):
        """Convert string values to proper types."""
        # Convert string status to enum if needed
        if isinstance(self.status, str):
            try:
                self.status = InvoiceStatus(self.status.lower())
            except ValueError:
                self.status = InvoiceStatus.PENDING
        
        # Convert string dates to date objects if needed
        if isinstance(self.invoice_date, str):
            self.invoice_date = date.fromisoformat(self.invoice_date)
        
        if isinstance(self.due_date, str) and self.due_date:
            self.due_date = date.fromisoformat(self.due_date)
        
        if isinstance(self.payment_date, str) and self.payment_date:
            self.payment_date = date.fromisoformat(self.payment_date)
        
        if isinstance(self.approval_date, str) and self.approval_date:
            self.approval_date = date.fromisoformat(self.approval_date)
        
        # Convert payment method string to enum if needed
        if isinstance(self.payment_method, str) and self.payment_method:
            try:
                self.payment_method = PaymentMethod(self.payment_method.lower())
            except ValueError:
                self.payment_method = None


@dataclass
class VendorRecord:
    """Vendor record data class."""
    id: int
    name: str
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    vendor_type: Optional[str] = None
    created_at: datetime = None


@dataclass
class FundRecord:
    """Fund record data class."""
    id: int
    name: str
    description: Optional[str] = None
    created_at: datetime = None


@dataclass
class DealRecord:
    """Deal record data class."""
    id: int
    deal_name: str
    fund_id: int
    fund_name: Optional[str] = None
    allocation_percentage: float = 100.0
    created_at: datetime = None


@dataclass
class ExpenseAllocationRecord:
    """Expense allocation record data class."""
    id: int
    invoice_id: int
    deal_allocation_id: int
    deal_name: Optional[str] = None
    allocation_percentage: float = 100.0
    created_at: datetime = None


@dataclass
class FundAllocationSummary:
    """Fund allocation summary data class for dashboard visualizations."""
    fund_name: str
    fund_id: int
    total_amount: float
    deal_allocations: List[dict]


@dataclass
class VendorAnalytics:
    """Vendor analytics data class for dashboard visualizations."""
    vendor_name: str
    vendor_id: int
    invoice_count: int
    total_amount: float
    avg_amount: float 