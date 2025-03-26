"""
Repository classes for data access.

This module provides repository classes for accessing and manipulating
data in the database.
"""

import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Any, Union

from .models import (
    InvoiceRecord, VendorRecord, FundRecord, 
    DealRecord, ExpenseAllocationRecord,
    InvoiceStatus
)

logger = logging.getLogger(__name__)


class BaseRepository:
    """Base repository class with common methods."""
    
    def __init__(self, session):
        """Initialize the repository.
        
        Args:
            session: Database session
        """
        self.session = session


class InvoiceRepository(BaseRepository):
    """Repository for invoice data."""
    
    def get_all(self, limit=100, offset=0) -> List[InvoiceRecord]:
        """Get all invoices.
        
        Args:
            limit: Maximum number of records to return
            offset: Offset for pagination
            
        Returns:
            List[InvoiceRecord]: List of invoice records
        """
        try:
            query = """
            SELECT 
                id, invoice_number, vendor, invoice_date, due_date, 
                amount, payment_status, payment_date, payment_reference,
                fund_paid_by, impact, description, created_at
            FROM invoices
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
            """
            
            cursor = self.session.cursor()
            cursor.execute(query, (limit, offset))
            
            results = []
            for row in cursor.fetchall():
                results.append(InvoiceRecord(
                    id=row[0],
                    invoice_number=row[1],
                    vendor_name=row[2],
                    invoice_date=row[3],
                    due_date=row[4],
                    total_amount=row[5],
                    status=row[6],
                    payment_date=row[7],
                    payment_reference=row[8],
                    fund_name=row[9],
                    deal_name=row[10],
                    description=row[11],
                    created_at=row[12]
                ))
            
            return results
        except Exception as e:
            logger.error(f"Error getting all invoices: {str(e)}", exc_info=True)
            return []
    
    def get_by_id(self, invoice_id: int) -> Optional[InvoiceRecord]:
        """Get invoice by ID.
        
        Args:
            invoice_id: Invoice ID
            
        Returns:
            Optional[InvoiceRecord]: Invoice record if found, None otherwise
        """
        try:
            query = """
            SELECT 
                id, invoice_number, vendor, invoice_date, due_date, 
                amount, payment_status, payment_date, payment_reference,
                fund_paid_by, impact, description, created_at
            FROM invoices
            WHERE id = %s
            """
            
            cursor = self.session.cursor()
            cursor.execute(query, (invoice_id,))
            
            row = cursor.fetchone()
            if row:
                return InvoiceRecord(
                    id=row[0],
                    invoice_number=row[1],
                    vendor_name=row[2],
                    invoice_date=row[3],
                    due_date=row[4],
                    total_amount=row[5],
                    status=row[6],
                    payment_date=row[7],
                    payment_reference=row[8],
                    fund_name=row[9],
                    deal_name=row[10],
                    description=row[11],
                    created_at=row[12]
                )
            
            return None
        except Exception as e:
            logger.error(f"Error getting invoice by ID: {str(e)}", exc_info=True)
            return None
    
    def filter_invoices(self, 
                       start_date: Optional[date] = None,
                       end_date: Optional[date] = None,
                       fund_id: Optional[int] = None,
                       status: Optional[Union[str, InvoiceStatus]] = None,
                       limit: int = 100,
                       offset: int = 0) -> List[InvoiceRecord]:
        """Filter invoices by criteria.
        
        Args:
            start_date: Start date for invoice_date filter
            end_date: End date for invoice_date filter
            fund_id: Fund ID to filter by
            status: Status to filter by
            limit: Maximum number of records to return
            offset: Offset for pagination
            
        Returns:
            List[InvoiceRecord]: List of invoice records
        """
        try:
            query = """
            SELECT 
                i.id, i.invoice_number, i.vendor, i.invoice_date, i.due_date, 
                i.amount, i.payment_status, i.payment_date, i.payment_reference,
                i.fund_paid_by, i.impact, i.description, i.created_at
            FROM invoices i
            """
            
            conditions = []
            params = []
            
            # Join with funds table if fund_id is provided
            if fund_id and fund_id != -1:
                query += " JOIN funds f ON i.fund_paid_by = f.name"
                conditions.append("f.id = %s")
                params.append(fund_id)
            
            # Add date filters if provided
            if start_date:
                conditions.append("i.invoice_date >= %s")
                params.append(start_date)
            
            if end_date:
                conditions.append("i.invoice_date <= %s")
                params.append(end_date)
            
            # Add status filter if provided
            if status and status != "all":
                if isinstance(status, InvoiceStatus):
                    status_val = status.value
                else:
                    status_val = status
                
                conditions.append("i.payment_status = %s")
                params.append(status_val)
            
            # Add WHERE clause if there are conditions
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            # Add ORDER BY, LIMIT, and OFFSET
            query += " ORDER BY i.created_at DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            cursor = self.session.cursor()
            cursor.execute(query, params)
            
            results = []
            for row in cursor.fetchall():
                results.append(InvoiceRecord(
                    id=row[0],
                    invoice_number=row[1],
                    vendor_name=row[2],
                    invoice_date=row[3],
                    due_date=row[4],
                    total_amount=row[5],
                    status=row[6],
                    payment_date=row[7],
                    payment_reference=row[8],
                    fund_name=row[9],
                    deal_name=row[10],
                    description=row[11],
                    created_at=row[12]
                ))
            
            return results
        except Exception as e:
            logger.error(f"Error filtering invoices: {str(e)}", exc_info=True)
            return []
            
    def get_total_outstanding(self, fund_id=None):
        """Get the total amount of outstanding invoices.
        
        Args:
            fund_id: Optional fund ID to filter by
            
        Returns:
            float: Total outstanding amount
        """
        try:
            query = "SELECT SUM(amount) FROM invoices WHERE payment_status = 'Unpaid'"
            params = []
            
            if fund_id and fund_id != -1:
                # Join with funds table to filter by fund ID
                query = """
                SELECT SUM(i.amount) 
                FROM invoices i
                JOIN funds f ON i.fund_paid_by = f.name
                WHERE i.payment_status = 'Unpaid' AND f.id = %s
                """
                params.append(fund_id)
            
            cursor = self.session.cursor()
            cursor.execute(query, params)
            
            result = cursor.fetchone()
            return result[0] or 0.0
        except Exception as e:
            logger.error(f"Error getting total outstanding: {str(e)}", exc_info=True)
            return 0.0

    def get_ytd_expenses(self, fund_id=None):
        """Get the year-to-date expenses.
        
        Args:
            fund_id: Optional fund ID to filter by
            
        Returns:
            float: Total YTD expenses
        """
        try:
            year_start = date(date.today().year, 1, 1)
            
            query = """
            SELECT SUM(amount) 
            FROM invoices 
            WHERE invoice_date >= %s
            """
            params = [year_start]
            
            if fund_id and fund_id != -1:
                # Join with funds table to filter by fund ID
                query = """
                SELECT SUM(i.amount) 
                FROM invoices i
                JOIN funds f ON i.fund_paid_by = f.name
                WHERE i.invoice_date >= %s AND f.id = %s
                """
                params.append(fund_id)
            
            cursor = self.session.cursor()
            cursor.execute(query, params)
            
            result = cursor.fetchone()
            return result[0] or 0.0
        except Exception as e:
            logger.error(f"Error getting YTD expenses: {str(e)}", exc_info=True)
            return 0.0

    def get_upcoming_payments(self, days=30, fund_id=None):
        """Get the total amount of upcoming payments due within specified days.
        
        Args:
            days: Number of days to look ahead
            fund_id: Optional fund ID to filter by
            
        Returns:
            float: Total upcoming payments
        """
        try:
            today = date.today()
            future_date = today + timedelta(days=days)
            
            query = """
            SELECT SUM(amount) 
            FROM invoices 
            WHERE payment_status = 'Unpaid' AND due_date BETWEEN %s AND %s
            """
            params = [today, future_date]
            
            if fund_id and fund_id != -1:
                # Join with funds table to filter by fund ID
                query = """
                SELECT SUM(i.amount) 
                FROM invoices i
                JOIN funds f ON i.fund_paid_by = f.name
                WHERE i.payment_status = 'Unpaid' 
                AND i.due_date BETWEEN %s AND %s 
                AND f.id = %s
                """
                params.append(fund_id)
            
            cursor = self.session.cursor()
            cursor.execute(query, params)
            
            result = cursor.fetchone()
            return result[0] or 0.0
        except Exception as e:
            logger.error(f"Error getting upcoming payments: {str(e)}", exc_info=True)
            return 0.0

    def get_fund_allocation(self, fund_id=None):
        """Get the fund allocation distribution.
        
        Args:
            fund_id: Optional fund ID to filter by
            
        Returns:
            dict: Fund allocation by impact/category
        """
        try:
            if fund_id and fund_id != -1:
                query = """
                SELECT impact, SUM(amount) as total 
                FROM invoices i
                JOIN funds f ON i.fund_paid_by = f.name
                WHERE f.id = %s
                GROUP BY impact
                ORDER BY total DESC
                """
                params = [fund_id]
            else:
                query = """
                SELECT impact, SUM(amount) as total 
                FROM invoices
                GROUP BY impact
                ORDER BY total DESC
                """
                params = []
            
            cursor = self.session.cursor()
            cursor.execute(query, params)
            
            results = cursor.fetchall()
            return {row[0]: row[1] for row in results}
        except Exception as e:
            logger.error(f"Error getting fund allocation: {str(e)}", exc_info=True)
            return {}


class VendorRepository(BaseRepository):
    """Repository for vendor data."""
    
    def get_all(self) -> List[VendorRecord]:
        """Get all vendors.
        
        Returns:
            List[VendorRecord]: List of vendor records
        """
        try:
            query = """
            SELECT id, name, contact_name, email, phone, address, created_at
            FROM vendors
            ORDER BY name
            """
            
            cursor = self.session.cursor()
            cursor.execute(query)
            
            results = []
            for row in cursor.fetchall():
                results.append(VendorRecord(
                    id=row[0],
                    name=row[1],
                    contact_name=row[2],
                    email=row[3],
                    phone=row[4],
                    address=row[5],
                    created_at=row[6]
                ))
            
            return results
        except Exception as e:
            logger.error(f"Error getting all vendors: {str(e)}", exc_info=True)
            return []
    
    def get_by_id(self, vendor_id: int) -> Optional[VendorRecord]:
        """Get vendor by ID.
        
        Args:
            vendor_id: Vendor ID
            
        Returns:
            Optional[VendorRecord]: Vendor record if found, None otherwise
        """
        try:
            query = """
            SELECT id, name, contact_name, email, phone, address, created_at
            FROM vendors
            WHERE id = %s
            """
            
            cursor = self.session.cursor()
            cursor.execute(query, (vendor_id,))
            
            row = cursor.fetchone()
            if row:
                return VendorRecord(
                    id=row[0],
                    name=row[1],
                    contact_name=row[2],
                    email=row[3],
                    phone=row[4],
                    address=row[5],
                    created_at=row[6]
                )
            
            return None
        except Exception as e:
            logger.error(f"Error getting vendor by ID: {str(e)}", exc_info=True)
            return None
    
    def get_all_types(self) -> List[Dict[str, Any]]:
        """Get all vendor types.
        
        Returns:
            List[Dict[str, Any]]: List of vendor types
        """
        # This is a placeholder - in a real system, vendor types would be stored in a separate table
        return [
            {"id": 1, "name": "Legal"},
            {"id": 2, "name": "Administrative"},
            {"id": 3, "name": "Technology"},
            {"id": 4, "name": "Consulting"},
            {"id": 5, "name": "Marketing"},
            {"id": 6, "name": "Operations"}
        ]


class FundRepository(BaseRepository):
    """Repository for fund data."""
    
    def get_all(self) -> List[FundRecord]:
        """Get all funds.
        
        Returns:
            List[FundRecord]: List of fund records
        """
        try:
            query = """
            SELECT id, name, description, created_at
            FROM funds
            ORDER BY name
            """
            
            cursor = self.session.cursor()
            cursor.execute(query)
            
            results = []
            for row in cursor.fetchall():
                results.append(FundRecord(
                    id=row[0],
                    name=row[1],
                    description=row[2],
                    created_at=row[3]
                ))
            
            return results
        except Exception as e:
            logger.error(f"Error getting all funds: {str(e)}", exc_info=True)
            return []
    
    def get_by_id(self, fund_id: int) -> Optional[FundRecord]:
        """Get fund by ID.
        
        Args:
            fund_id: Fund ID
            
        Returns:
            Optional[FundRecord]: Fund record if found, None otherwise
        """
        try:
            query = """
            SELECT id, name, description, created_at
            FROM funds
            WHERE id = %s
            """
            
            cursor = self.session.cursor()
            cursor.execute(query, (fund_id,))
            
            row = cursor.fetchone()
            if row:
                return FundRecord(
                    id=row[0],
                    name=row[1],
                    description=row[2],
                    created_at=row[3]
                )
            
            return None
        except Exception as e:
            logger.error(f"Error getting fund by ID: {str(e)}", exc_info=True)
            return None


class ExpenseCategoryRepository(BaseRepository):
    """Repository for expense category data."""
    
    def get_all(self) -> List[Dict[str, Any]]:
        """Get all expense categories.
        
        Returns:
            List[Dict[str, Any]]: List of expense categories
        """
        # This is a placeholder - in a real system, expense categories would be stored in a separate table
        return [
            {"id": 1, "name": "Legal Fees"},
            {"id": 2, "name": "Administrative"},
            {"id": 3, "name": "Technology"},
            {"id": 4, "name": "Consulting"},
            {"id": 5, "name": "Travel & Entertainment"},
            {"id": 6, "name": "Rent & Facilities"},
            {"id": 7, "name": "Marketing"},
            {"id": 8, "name": "Insurance"}
        ]


class PaymentRepository(BaseRepository):
    """Repository for payment data."""
    
    def record_payment(self, invoice_id: int, payment_date: date, 
                      payment_reference: str, payment_method: str) -> bool:
        """Record a payment for an invoice.
        
        Args:
            invoice_id: Invoice ID
            payment_date: Payment date
            payment_reference: Payment reference (e.g., check number)
            payment_method: Payment method
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            query = """
            UPDATE invoices
            SET payment_status = 'Paid', payment_date = %s, payment_reference = %s
            WHERE id = %s
            """
            
            cursor = self.session.cursor()
            cursor.execute(query, (payment_date, payment_reference, invoice_id))
            self.session.commit()
            
            return True
        except Exception as e:
            logger.error(f"Error recording payment: {str(e)}", exc_info=True)
            return False

def get_invoice_vendor_relationship(self, fund_id=None, start_date=None, end_date=None):
    """Get invoice-vendor relationship data for visualizations.
    
    Args:
        fund_id: Optional fund ID to filter by
        start_date: Optional start date for filtering
        end_date: Optional end date for filtering
        
    Returns:
        list: List of invoice-vendor relationship data
    """
    query = """
    SELECT 
        i.vendor as vendor_name,
        COUNT(i.id) as invoice_count,
        SUM(i.amount) as total_amount,
        AVG(i.amount) as avg_amount,
        v.id as vendor_id
    FROM 
        invoices i
    LEFT JOIN 
        vendors v ON i.vendor = v.name
    """
    
    conditions = []
    params = []
    
    if fund_id and fund_id != -1:
        conditions.append("i.fund_paid_by = (SELECT name FROM funds WHERE id = %s)")
        params.append(fund_id)
    
    if start_date:
        conditions.append("i.invoice_date >= %s")
        params.append(start_date)
    
    if end_date:
        conditions.append("i.invoice_date <= %s")
        params.append(end_date)
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += " GROUP BY i.vendor, v.id ORDER BY total_amount DESC"
    
    results = self.session.execute(query, params).fetchall()
    
    # Convert to list of dictionaries
    return [
        {
            'vendor_name': row[0],
            'invoice_count': row[1],
            'total_amount': row[2],
            'avg_amount': row[3],
            'vendor_id': row[4]
        }
        for row in results
    ]

def get_fund_deal_allocation(self, fund_id=None, start_date=None, end_date=None):
    """Get fund-deal allocation data for visualizations.
    
    Args:
        fund_id: Optional fund ID to filter by
        start_date: Optional start date for filtering
        end_date: Optional end date for filtering
        
    Returns:
        list: List of fund-deal allocation data
    """
    query = """
    SELECT 
        i.fund_paid_by as fund_name,
        i.impact as deal_name,
        SUM(i.amount) as total_amount,
        COUNT(i.id) as invoice_count,
        f.id as fund_id
    FROM 
        invoices i
    LEFT JOIN 
        funds f ON i.fund_paid_by = f.name
    """
    
    conditions = []
    params = []
    
    if fund_id and fund_id != -1:
        conditions.append("f.id = %s")
        params.append(fund_id)
    
    if start_date:
        conditions.append("i.invoice_date >= %s")
        params.append(start_date)
    
    if end_date:
        conditions.append("i.invoice_date <= %s")
        params.append(end_date)
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += " GROUP BY i.fund_paid_by, i.impact, f.id ORDER BY fund_name, total_amount DESC"
    
    results = self.session.execute(query, params).fetchall()
    
    # Convert to list of dictionaries
    return [
        {
            'fund_name': row[0],
            'deal_name': row[1],
            'total_amount': row[2],
            'invoice_count': row[3],
            'fund_id': row[4]
        }
        for row in results
    ] 