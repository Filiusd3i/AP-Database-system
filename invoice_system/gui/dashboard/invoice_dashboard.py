"""
Main dashboard widget for the private equity invoice management system.

This module provides the primary dashboard interface for managing invoices,
viewing analytics, and performing invoice-related operations with focus on
private equity fund management.
"""

import logging
from datetime import datetime, timedelta, date
from typing import Optional, Dict, List, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, 
    QPushButton, QTabWidget, QLabel, QComboBox,
    QDateEdit, QMessageBox, QHeaderView, QFileDialog,
    QFrame, QGridLayout, QScrollArea, QGroupBox
)
from PySide6.QtCore import Qt, Signal, Slot, QDate, QSize
from PySide6.QtGui import QIcon, QColor, QPalette, QFont
from PySide6.QtCharts import QChartView, QChart, QPieSeries, QBarSeries, QBarSet
from PySide6.QtCharts import QBarCategoryAxis, QValueAxis

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
        
        # 1. TOP NAVIGATION BAR
        top_nav_layout = self._create_top_nav_bar()
        main_layout.addLayout(top_nav_layout)
        
        # 2-3-4. MAIN CONTENT AREA (Left sidebar, Central visualization, Detail panel)
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 2. LEFT SIDEBAR - Navigation & Filtering
        left_sidebar = self._create_left_sidebar()
        content_splitter.addWidget(left_sidebar)
        
        # 3. CENTRAL VISUALIZATION AREA
        central_area = self._create_central_visualization_area()
        content_splitter.addWidget(central_area)
        
        # 4. DETAIL PANEL (Right Side)
        detail_panel = self._create_detail_panel()
        content_splitter.addWidget(detail_panel)
        
        # Set initial sizes (20% sidebar, 50% central, 30% details)
        content_splitter.setSizes([200, 500, 300])
        main_layout.addWidget(content_splitter, 1)  # Give the splitter a stretch factor
        
        # 5. BOTTOM ACTION BAR
        action_bar = self._create_bottom_action_bar()
        main_layout.addLayout(action_bar)
        
        # Connect signals and slots
        self._connect_signals()
    
    def _create_top_nav_bar(self):
        """Create the top navigation bar with fund selector and KPI cards."""
        top_nav_layout = QVBoxLayout()
        top_nav_layout.setSpacing(10)
        
        # Top controls
        controls_layout = QHBoxLayout()
        
        # Fund Selector
        fund_layout = QHBoxLayout()
        fund_layout.addWidget(QLabel("Fund:"))
        self.fund_selector = QComboBox()
        self.fund_selector.addItem("All Funds", -1)
        self.fund_selector.setMinimumWidth(200)
        fund_layout.addWidget(self.fund_selector)
        controls_layout.addLayout(fund_layout)
        
        # Date Range Selector
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("Date Range:"))
        self.date_range_selector = QComboBox()
        self.date_range_selector.addItems(["YTD", "QTD", "Last 12 Months", "Custom"])
        self.date_range_selector.setCurrentText("YTD")
        date_layout.addWidget(self.date_range_selector)
        
        # Custom date range (initially hidden, shown when "Custom" is selected)
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addMonths(-1))
        self.start_date.setCalendarPopup(True)
        date_layout.addWidget(QLabel("From:"))
        date_layout.addWidget(self.start_date)
        
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        date_layout.addWidget(QLabel("To:"))
        date_layout.addWidget(self.end_date)
        
        # Hide custom date fields initially
        self.start_date.hide()
        self.end_date.hide()
        controls_layout.addLayout(date_layout)
        
        # Add stretch to push controls to the left
        controls_layout.addStretch(1)
        
        # Apply filters button
        self.apply_filters_btn = QPushButton("Apply Filters")
        controls_layout.addWidget(self.apply_filters_btn)
        
        # Refresh button
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setToolTip("Refresh data from database")
        controls_layout.addWidget(self.refresh_btn)
        
        top_nav_layout.addLayout(controls_layout)
        
        # Quick Metrics - KPI cards
        metrics_layout = QHBoxLayout()
        
        # Create 4 KPI cards for the top metrics
        self.kpi_cards = []
        kpi_titles = [
            "Total Outstanding Invoices",
            "YTD Expenses by Category",
            "Upcoming Payment Obligations",
            "Fund Allocation Distribution"
        ]
        
        for title in kpi_titles:
            card = self._create_kpi_card(title, "$0.00")
            metrics_layout.addWidget(card)
            self.kpi_cards.append(card)
        
        top_nav_layout.addLayout(metrics_layout)
        
        return top_nav_layout
    
    def _create_kpi_card(self, title, value):
        """Create a KPI card with title and value."""
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setFrameShadow(QFrame.Shadow.Raised)
        card.setLineWidth(1)
        
        # Set minimum size
        card.setMinimumSize(QSize(200, 100))
        
        # Layout for the card
        card_layout = QVBoxLayout(card)
        
        # Title label
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title_label)
        
        # Value label
        value_label = QLabel(value)
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = value_label.font()
        font.setPointSize(16)
        font.setBold(True)
        value_label.setFont(font)
        card_layout.addWidget(value_label)
        
        # Store value label as property for easy updates
        card.value_label = value_label
        
        return card
    
    def _create_left_sidebar(self):
        """Create the left sidebar with navigation and advanced filters."""
        sidebar_widget = QWidget()
        sidebar_layout = QVBoxLayout(sidebar_widget)
        
        # Main Navigation - Tabs
        nav_group = QGroupBox("Navigation")
        nav_layout = QVBoxLayout(nav_group)
        
        nav_buttons = [
            ("Overview", True),
            ("Vendors", False),
            ("Invoices", False),
            ("Funds", False),
            ("Reports", False)
        ]
        
        self.nav_button_group = []
        for label, is_active in nav_buttons:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setChecked(is_active)
            nav_layout.addWidget(btn)
            self.nav_button_group.append(btn)
        
        sidebar_layout.addWidget(nav_group)
        
        # Advanced Filters
        filter_group = QGroupBox("Advanced Filters")
        filter_layout = QVBoxLayout(filter_group)
        
        # Vendor type filter
        vendor_layout = QVBoxLayout()
        vendor_layout.addWidget(QLabel("Vendor Type:"))
        self.vendor_type_selector = QComboBox()
        self.vendor_type_selector.addItem("All Types", -1)
        vendor_layout.addWidget(self.vendor_type_selector)
        filter_layout.addLayout(vendor_layout)
        
        # Expense categories filter
        expense_layout = QVBoxLayout()
        expense_layout.addWidget(QLabel("Expense Category:"))
        self.expense_category_selector = QComboBox()
        self.expense_category_selector.addItem("All Categories", -1)
        expense_layout.addWidget(self.expense_category_selector)
        filter_layout.addLayout(expense_layout)
        
        # Approval status filter
        approval_layout = QVBoxLayout()
        approval_layout.addWidget(QLabel("Approval Status:"))
        self.status_selector = QComboBox()
        self.status_selector.addItem("All Statuses", "all")
        for status in InvoiceStatus:
            self.status_selector.addItem(status.value.capitalize(), status.value)
        approval_layout.addWidget(self.status_selector)
        filter_layout.addLayout(approval_layout)
        
        # Deal name filter
        deal_layout = QVBoxLayout()
        deal_layout.addWidget(QLabel("Deal Name:"))
        self.deal_selector = QComboBox()
        self.deal_selector.addItem("All Deals", -1)
        deal_layout.addWidget(self.deal_selector)
        filter_layout.addLayout(deal_layout)
        
        # Payment status filter
        payment_layout = QVBoxLayout()
        payment_layout.addWidget(QLabel("Payment Status:"))
        self.payment_status_selector = QComboBox()
        self.payment_status_selector.addItems(["All", "Paid", "Unpaid", "Partial"])
        payment_layout.addWidget(self.payment_status_selector)
        filter_layout.addLayout(payment_layout)
        
        sidebar_layout.addWidget(filter_group)
        
        # Saved Views
        saved_group = QGroupBox("Saved Views")
        saved_layout = QVBoxLayout(saved_group)
        
        # Sample saved views
        saved_views = ["Last Quarter Expenses", "Overdue Payments", "Top Vendors"]
        for view in saved_views:
            saved_layout.addWidget(QPushButton(view))
        
        sidebar_layout.addWidget(saved_group)
        
        # Add stretch to push everything to the top
        sidebar_layout.addStretch(1)
        
        return sidebar_widget
    
    def _create_central_visualization_area(self):
        """Create the central visualization area with charts and tables."""
        central_widget = QWidget()
        central_layout = QVBoxLayout(central_widget)
        
        # Create visualization tabs
        viz_tabs = QTabWidget()
        viz_tabs.setDocumentMode(True)
        
        # Overview tab with visualizations
        overview_tab = QWidget()
        overview_layout = QVBoxLayout(overview_tab)
        
        # Relationship Flow Diagram (Placeholder for Sankey chart)
        flow_group = QGroupBox("Fund-Deal-Vendor Relationship Flow")
        flow_layout = QVBoxLayout(flow_group)
        flow_layout.addWidget(QLabel("Interactive Sankey diagram showing money flow"))
        # This would be replaced with an actual Sankey visualization
        
        overview_layout.addWidget(flow_group)
        
        # Fund Allocation Treemap and Vendor Concentration
        charts_layout = QHBoxLayout()
        
        # Fund Allocation chart (placeholder for treemap)
        allocation_group = QGroupBox("Fund Allocation")
        allocation_layout = QVBoxLayout(allocation_group)
        
        # Create a simple pie chart as placeholder
        allocation_chart = QChart()
        allocation_chart.setTitle("Fund Allocation by Category")
        allocation_chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        
        allocation_series = QPieSeries()
        allocation_series.append("Legal", 15.0)
        allocation_series.append("Admin", 25.0)
        allocation_series.append("Operations", 35.0)
        allocation_series.append("Marketing", 10.0)
        allocation_series.append("Travel", 15.0)
        
        # Make first slice exploded
        slice_ = allocation_series.slices()[0]
        slice_.setExploded(True)
        slice_.setLabelVisible(True)
        
        allocation_chart.addSeries(allocation_series)
        allocation_chart.legend().setAlignment(Qt.AlignmentFlag.AlignRight)
        
        allocation_chart_view = QChartView(allocation_chart)
        allocation_chart_view.setRenderHint(allocation_chart_view.renderHint())
        allocation_chart_view.setMinimumHeight(250)
        
        allocation_layout.addWidget(allocation_chart_view)
        charts_layout.addWidget(allocation_group)
        
        # Vendor Concentration chart
        vendor_group = QGroupBox("Vendor Concentration")
        vendor_layout = QVBoxLayout(vendor_group)
        
        # Create a simple bar chart as placeholder
        vendor_chart = QChart()
        vendor_chart.setTitle("Top Vendors by Spend")
        vendor_chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        
        vendor_set = QBarSet("Amount")
        vendor_set.append([45000, 37500, 25000, 15000, 10000])
        
        series = QBarSeries()
        series.append(vendor_set)
        
        vendor_chart.addSeries(series)
        
        vendors = ["Acme Corp", "Tech Solutions", "Legal LLC", "Consulting Inc", "Office Supplies"]
        axis_x = QBarCategoryAxis()
        axis_x.append(vendors)
        vendor_chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axis_x)
        
        axis_y = QValueAxis()
        axis_y.setRange(0, 50000)
        vendor_chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_y)
        
        vendor_chart.legend().setVisible(False)
        
        vendor_chart_view = QChartView(vendor_chart)
        vendor_chart_view.setRenderHint(vendor_chart_view.renderHint())
        vendor_chart_view.setMinimumHeight(250)
        
        vendor_layout.addWidget(vendor_chart_view)
        charts_layout.addWidget(vendor_group)
        
        overview_layout.addLayout(charts_layout)
        
        # Invoice Timeline
        timeline_group = QGroupBox("Invoice Timeline")
        timeline_layout = QVBoxLayout(timeline_group)
        timeline_layout.addWidget(QLabel("Gantt-style chart showing invoice due dates and payment status"))
        # This would be replaced with an actual Gantt visualization
        
        overview_layout.addWidget(timeline_group)
        
        viz_tabs.addTab(overview_tab, "Overview")
        
        # Invoice table tab
        table_tab = QWidget()
        table_layout = QVBoxLayout(table_tab)
        self.invoice_table = InvoiceTableWidget(self.db_connection)
        table_layout.addWidget(self.invoice_table)
        viz_tabs.addTab(table_tab, "Invoices")
        
        # Fund Analysis tab (placeholder)
        fund_tab = QWidget()
        fund_layout = QVBoxLayout(fund_tab)
        fund_layout.addWidget(QLabel("Fund performance analytics will be displayed here"))
        viz_tabs.addTab(fund_tab, "Fund Analysis")
        
        # Vendor Analysis tab (placeholder)
        vendor_tab = QWidget()
        vendor_layout = QVBoxLayout(vendor_tab)
        vendor_layout.addWidget(QLabel("Vendor analytics will be displayed here"))
        viz_tabs.addTab(vendor_tab, "Vendor Analysis")
        
        central_layout.addWidget(viz_tabs)
        
        return central_widget
    
    def _create_detail_panel(self):
        """Create the detail panel for showing contextual information."""
        detail_widget = QWidget()
        detail_layout = QVBoxLayout(detail_widget)
        
        # Header
        detail_header = QLabel("Detail Panel")
        font = detail_header.font()
        font.setPointSize(14)
        font.setBold(True)
        detail_header.setFont(font)
        detail_layout.addWidget(detail_header)
        
        # Content will change based on selection
        self.detail_content = QTabWidget()
        
        # Placeholder tabs for different entity details
        self.invoice_details = QWidget()
        invoice_layout = QVBoxLayout(self.invoice_details)
        invoice_layout.addWidget(QLabel("Select an invoice to view details"))
        self.detail_content.addTab(self.invoice_details, "Invoice Details")
        
        self.vendor_details = QWidget()
        vendor_layout = QVBoxLayout(self.vendor_details)
        vendor_layout.addWidget(QLabel("Select a vendor to view details"))
        self.detail_content.addTab(self.vendor_details, "Vendor Details")
        
        self.fund_details = QWidget()
        fund_layout = QVBoxLayout(self.fund_details)
        fund_layout.addWidget(QLabel("Select a fund to view details"))
        self.detail_content.addTab(self.fund_details, "Fund Details")
        
        detail_layout.addWidget(self.detail_content, 1)
        
        return detail_widget
    
    def _create_bottom_action_bar(self):
        """Create the bottom action bar with quick action buttons."""
        actions_layout = QHBoxLayout()
        
        # Quick action buttons
        self.export_btn = QPushButton("Export Data")
        self.export_btn.setIcon(QIcon.fromTheme("document-save"))
        
        self.report_btn = QPushButton("Generate Report")
        self.report_btn.setIcon(QIcon.fromTheme("document-print"))
        
        self.payment_btn = QPushButton("Schedule Payments")
        self.payment_btn.setIcon(QIcon.fromTheme("appointment-soon"))
        
        self.add_vendor_btn = QPushButton("Add Vendor/Invoice")
        self.add_vendor_btn.setIcon(QIcon.fromTheme("list-add"))
        
        actions_layout.addWidget(self.export_btn)
        actions_layout.addWidget(self.report_btn)
        actions_layout.addWidget(self.payment_btn)
        actions_layout.addStretch(1)
        actions_layout.addWidget(self.add_vendor_btn)
        
        return actions_layout
    
    def _connect_signals(self):
        """Connect signals and slots."""
        # Filter and refresh connections
        self.apply_filters_btn.clicked.connect(self._apply_filters)
        self.refresh_btn.clicked.connect(self.refresh_data)
        
        # Date range selector connections
        self.date_range_selector.currentTextChanged.connect(self._handle_date_range_change)
        
        # Navigation button connections
        for i, btn in enumerate(self.nav_button_group):
            btn.clicked.connect(lambda checked, idx=i: self._handle_nav_button_click(idx))
        
        # Table selection changed
        self.invoice_table.selectionChanged.connect(self._handle_selection_changed)
        
        # Bottom action bar connections
        self.export_btn.clicked.connect(self._export_data)
        self.report_btn.clicked.connect(self._generate_report)
        self.payment_btn.clicked.connect(self._schedule_payments)
        self.add_vendor_btn.clicked.connect(self._add_vendor_invoice)
    
    def _handle_date_range_change(self, text):
        """Handle date range selector change."""
        # Show/hide custom date fields based on selection
        show_custom = (text == "Custom")
        self.start_date.setVisible(show_custom)
        self.end_date.setVisible(show_custom)
        
        # Set appropriate date range based on selection
        if not show_custom:
            today = QDate.currentDate()
            if text == "YTD":
                # Year to date - Jan 1 to today
                self.start_date.setDate(QDate(today.year(), 1, 1))
                self.end_date.setDate(today)
            elif text == "QTD":
                # Quarter to date
                quarter_start_month = ((today.month() - 1) // 3) * 3 + 1
                self.start_date.setDate(QDate(today.year(), quarter_start_month, 1))
                self.end_date.setDate(today)
            elif text == "Last 12 Months":
                # Last 12 months
                self.start_date.setDate(today.addMonths(-12))
                self.end_date.setDate(today)
    
    def _handle_nav_button_click(self, index):
        """Handle navigation button click."""
        # Update button states
        for i, btn in enumerate(self.nav_button_group):
            btn.setChecked(i == index)
        
        # TODO: Switch content based on selected navigation item
        # This would change the central visualization area content
        pass
    
    def _update_details_view(self):
        """Update the details view with the selected entity."""
        has_selection = self.invoice_table.has_selection()
        
        if has_selection:
            invoice_id = self.invoice_table.get_selected_invoice_id()
            if invoice_id:
                # Switch to invoice details tab
                self.detail_content.setCurrentWidget(self.invoice_details)
                
                # Clear previous content
                while self.invoice_details.layout().count():
                    item = self.invoice_details.layout().takeAt(0)
                    widget = item.widget()
                    if widget:
                        widget.deleteLater()
                
                try:
                    # Fetch invoice details
                    with self.db_connection.session() as session:
                        invoice_repo = InvoiceRepository(session)
                        vendor_repo = VendorRepository(session)
                        fund_repo = FundRepository(session)
                        
                        invoice = invoice_repo.get_by_id(invoice_id)
                        
                        if invoice:
                            # Create a form-like layout for invoice details
                            form_layout = QGridLayout()
                            row = 0
                            
                            # Helper function to add a field
                            def add_field(label_text, value_text):
                                nonlocal row
                                label = QLabel(f"{label_text}:")
                                font = label.font()
                                font.setBold(True)
                                label.setFont(font)
                                
                                value = QLabel(str(value_text) if value_text is not None else "")
                                
                                form_layout.addWidget(label, row, 0)
                                form_layout.addWidget(value, row, 1)
                                row += 1
                            
                            # Add invoice fields
                            add_field("Invoice Number", invoice.invoice_number)
                            add_field("Vendor", invoice.vendor_name)
                            add_field("Invoice Date", invoice.invoice_date.strftime("%Y-%m-%d") if invoice.invoice_date else "")
                            add_field("Due Date", invoice.due_date.strftime("%Y-%m-%d") if invoice.due_date else "")
                            add_field("Amount", f"${invoice.total_amount:.2f}")
                            add_field("Status", invoice.status.value.capitalize() if hasattr(invoice.status, 'value') else invoice.status)
                            
                            # Additional fields
                            if hasattr(invoice, 'fund_name'):
                                add_field("Fund", invoice.fund_name)
                            if hasattr(invoice, 'approved_by'):
                                add_field("Approved By", invoice.approved_by)
                            if hasattr(invoice, 'approval_date'):
                                add_field("Approval Date", invoice.approval_date.strftime("%Y-%m-%d") if invoice.approval_date else "")
                            
                            # Add description if available
                            if hasattr(invoice, 'description') and invoice.description:
                                form_layout.addWidget(QLabel("Description:"), row, 0, alignment=Qt.AlignmentFlag.AlignTop)
                                description = QLabel(invoice.description)
                                description.setWordWrap(True)
                                form_layout.addWidget(description, row, 1)
                                row += 1
                            
                            self.invoice_details.layout().addLayout(form_layout)
                            self.invoice_details.layout().addStretch(1)
                except Exception as e:
                    logger.error(f"Error updating detail view: {str(e)}", exc_info=True)
                    error_label = QLabel(f"Error loading details: {str(e)}")
                    error_label.setWordWrap(True)
                    self.invoice_details.layout().addWidget(error_label)
                    self.invoice_details.layout().addStretch(1)
        
    @Slot()
    def _generate_report(self):
        """Generate a report based on current data."""
        QMessageBox.information(
            self, "Generate Report", 
            "Report generation feature will be implemented in a future update."
        )
    
    @Slot()
    def _schedule_payments(self):
        """Open payment scheduling dialog."""
        QMessageBox.information(
            self, "Schedule Payments", 
            "Payment scheduling feature will be implemented in a future update."
        )
    
    @Slot()
    def _add_vendor_invoice(self):
        """Open dialog to add new vendor or invoice."""
        QMessageBox.information(
            self, "Add Vendor/Invoice", 
            "Add vendor/invoice feature will be implemented in a future update."
        )
    
    @Slot()
    def _apply_filters(self):
        """Apply dashboard filters."""
        try:
            # Get date range from UI
            start_date = self.start_date.date().toPython()
            end_date = self.end_date.date().toPython()
            
            # Get filter values
            fund_id = self.fund_selector.currentData()
            status = self.status_selector.currentData()
            vendor_type = self.vendor_type_selector.currentData()
            expense_category = self.expense_category_selector.currentData()
            deal_id = self.deal_selector.currentData()
            payment_status = self.payment_status_selector.currentText()
            if payment_status == "All":
                payment_status = None
            
            # Apply filters to invoice table
            self.invoice_table.apply_filters(start_date, end_date, fund_id, status)
            
            # Update visualizations and KPIs
            self._update_kpi_cards(start_date, end_date, fund_id)
            self._update_visualizations(start_date, end_date, fund_id, vendor_type, expense_category, deal_id, payment_status)
            
        except Exception as e:
            logger.error(f"Error applying filters: {str(e)}", exc_info=True)
            QMessageBox.warning(
                self, "Filter Error", 
                f"Error applying filters: {str(e)}"
            )
    
    def _update_kpi_cards(self, start_date, end_date, fund_id):
        """Update KPI cards with current data."""
        try:
            with self.db_connection.session() as session:
                invoice_repo = InvoiceRepository(session)
                
                # Get total outstanding invoices
                outstanding = invoice_repo.get_total_outstanding(fund_id)
                self.kpi_cards[0].value_label.setText(f"${outstanding:,.2f}")
                
                # Get YTD expenses by category
                ytd_expenses = invoice_repo.get_ytd_expenses(fund_id)
                self.kpi_cards[1].value_label.setText(f"${ytd_expenses:,.2f}")
                
                # Get upcoming payment obligations (next 30 days)
                upcoming = invoice_repo.get_upcoming_payments(30, fund_id)
                self.kpi_cards[2].value_label.setText(f"${upcoming:,.2f}")
                
                # Get fund allocation distribution
                allocation = invoice_repo.get_fund_allocation(fund_id)
                if fund_id == -1:
                    self.kpi_cards[3].value_label.setText("All Funds")
                else:
                    fund_repo = FundRepository(session)
                    fund = fund_repo.get_by_id(fund_id)
                    if fund:
                        self.kpi_cards[3].value_label.setText(fund.name)
                    else:
                        self.kpi_cards[3].value_label.setText("Unknown Fund")
                
        except Exception as e:
            logger.error(f"Error updating KPI cards: {str(e)}", exc_info=True)
    
    def _update_visualizations(self, start_date, end_date, fund_id, vendor_type, expense_category, deal_id, payment_status):
        """Update all visualizations with current filtered data."""
        # This would be implemented to update all the charts and visualizations
        # For now, this is a placeholder as implementation depends on the specific visualization libraries
        pass
    
    @Slot()
    def refresh_data(self):
        """Refresh all dashboard data."""
        try:
            # Load reference data
            self._load_reference_data()
            
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
    
    def _load_reference_data(self):
        """Load reference data for all selectors."""
        try:
            with self.db_connection.session() as session:
                # Load funds for fund selector
                fund_repo = FundRepository(session)
                funds = fund_repo.get_all()
                
                # Clear current items except "All Funds"
                while self.fund_selector.count() > 1:
                    self.fund_selector.removeItem(1)
                
                # Add funds to selector
                for fund in funds:
                    self.fund_selector.addItem(fund.name, fund.id)
                
                # Load vendor types
                vendor_repo = VendorRepository(session)
                vendor_types = vendor_repo.get_all_types()
                
                # Clear current items except "All Types"
                while self.vendor_type_selector.count() > 1:
                    self.vendor_type_selector.removeItem(1)
                
                # Add vendor types to selector
                for v_type in vendor_types:
                    self.vendor_type_selector.addItem(v_type.name, v_type.id)
                
                # Load expense categories
                expense_repo = ExpenseCategoryRepository(session)
                categories = expense_repo.get_all()
                
                # Clear current items except "All Categories"
                while self.expense_category_selector.count() > 1:
                    self.expense_category_selector.removeItem(1)
                
                # Add categories to selector
                for category in categories:
                    self.expense_category_selector.addItem(category.name, category.id)
                
                # TODO: Load deals for deal selector
                # This would require a DealRepository
                
        except Exception as e:
            logger.error(f"Error loading reference data: {str(e)}", exc_info=True)
            QMessageBox.warning(
                self, "Data Loading Error", 
                f"Error loading reference data: {str(e)}"
            )
    
    def _update_button_states(self):
        """Update action button states based on selection."""
        has_selection = self.invoice_table.has_selection()
        
        self.export_btn.setEnabled(has_selection)
    
    @Slot()
    def _handle_selection_changed(self):
        """Handle table selection change."""
        self._update_button_states()
        self._update_details_view()
    
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
