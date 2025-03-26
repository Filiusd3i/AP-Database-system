# Changelog

All notable changes to this project will be documented in this file.

## [1.2.0] - 2025-03-26
### Added
- New Modern Dashboard interface with three-panel layout
  - Left sidebar navigation panel
  - Center invoice list panel
  - Right detail panel showing relationships
  - Interactive visualization of fund allocations
  - Modern styling with improved card components
- Updated application launch options
  - Added command line argument `--modern-ui` to launch with new UI by default
  - Added menu options to switch between dashboard styles
  - Enhanced toolbar with buttons for both dashboard types

### Changed
- Refactored main.py to support both classic and modern UI options
- Improved dashboard UI component initialization sequence to prevent errors
- Enhanced relationship visualization between invoices, vendors, and funds

## [1.1.0] - 2025-03-26
### Added
- New Accounts Payable Aging Report feature
  - Generate detailed aging reports for unpaid invoices
  - Export aging reports to CSV
  - Categorize invoices by aging buckets (Current, 1-30 days, 31-60 days, 61-90 days, Over 90 days)

### Added 
- Enhanced logging system with ELK Stack integration
  - Added structured JSON logging for better analysis
  - Implemented performance tracking tools for operations
  - Added method call tracing with parameters
  - Created comprehensive logging documentation
- Updated date format in dashboard UI to use MM/DD/YYYY format for better readability
- Added support for automatic logging to local files when ELK Stack is unavailable

### Changed
- Refactored logging configuration to use a more robust approach
- Improved error handling for database connections to include detailed logging
- Enhanced dashboard datetime display formats for consistency

### Fixed
- Fixed database schema issue with vendor name column
- Fixed Current Invoices calculation to properly filter unpaid invoices that are not yet overdue
- Fixed dashboard initialization error related to missing `update_invoice_table` method call
- Fixed error in logging system where standard LogRecord objects were missing expected `iso_timestamp` attribute
- Fixed missing `execute_search` method in UnifiedDashboard class causing application startup failures

## [1.0.0] - 2025-03-25

### Added
- Initial release
- Basic invoice database management
- Dashboard visualization for financial data
- CSV import and export functionality
- Database schema validation and automatic fixes
- Dark theme UI with responsive design
