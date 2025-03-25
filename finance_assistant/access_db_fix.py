"""
Compatibility module for access_db_fix.

This module is provided for backward compatibility. New code should use
the finance_assistant.database.connection module directly.
"""

import warnings

# Show deprecation warning
warnings.warn(
    "The finance_assistant.access_db_fix module is deprecated. "
    "Please use finance_assistant.database.connection instead.",
    DeprecationWarning,
    stacklevel=2
)

# Import from the new module for compatibility
from finance_assistant.database.connection import AccessDatabaseFix, QueryBuilder

# Export the names for backward compatibility
__all__ = ['AccessDatabaseFix', 'QueryBuilder'] 