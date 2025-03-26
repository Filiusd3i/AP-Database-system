#!/usr/bin/env python3
"""
Schema Validator Module

Provides functionality to validate database schema and ensure required columns exist.
"""

import logging
import os
from typing import Dict, List, Any, Optional
from tkinter import messagebox
import tkinter as tk
from tkinter import ttk
import re

logger = logging.getLogger(__name__)

class SchemaValidator:
    """Validates database schema and ensures required columns exist"""
    
    def __init__(self, db_manager):
        """Initialize the schema validator
        
        Args:
            db_manager: DatabaseManager instance
        """
        self.db_manager = db_manager
        self.fixed_tables = set()  # Keep track of tables we've already fixed
        self.expected_schemas = self._initialize_expected_schemas()
        self.type_conversions_performed = []  # Track column type conversions
    
    def _initialize_expected_schemas(self) -> Dict[str, Dict[str, Any]]:
        """Initialize the expected schemas for known tables
        
        Returns:
            Dict: A dictionary mapping table names to their expected schemas
        """
        schemas = {}
        
        # Define the expected schema for the invoices table
        schemas['invoices'] = {
            'required_columns': {
                'invoice_number': 'VARCHAR(50)',
                'vendor_name': 'VARCHAR(100)',  # Use vendor_name instead of vendor
                'invoice_date': 'DATE',
                'due_date': 'DATE', 
                'amount': 'DECIMAL(10,2)',
                'payment_status': 'VARCHAR(20)',
                'fund_paid_by': 'VARCHAR(100)'
            },
            'optional_columns': {
                'description': 'TEXT',
                'payment_date': 'DATE',
                'payment_reference': 'VARCHAR(50)',
                'impact': 'VARCHAR(100)'
            }
        }
        
        # Define the expected schema for the vendors table
        schemas['vendors'] = {
            'required_columns': {
                'name': 'VARCHAR(100)',
                'contact_name': 'VARCHAR(100)',
                'email': 'VARCHAR(100)',
                'phone': 'VARCHAR(20)'
            },
            'optional_columns': {
                'address': 'TEXT',
                'notes': 'TEXT'
            }
        }
        
        # Define the expected schema for the funds table
        schemas['funds'] = {
            'required_columns': {
                'name': 'VARCHAR(100)',
                'description': 'TEXT'
            },
            'optional_columns': {}
        }
        
        return schemas
    
    def validate_table(self, table_name: str, auto_fix: bool = False) -> Dict[str, Any]:
        """Validate that a table has the required columns
        
        Args:
            table_name: The name of the table to validate
            auto_fix: Whether to automatically add missing columns
            
        Returns:
            Dict: A dictionary with validation results
        """
        logger.info(f"Validating schema for table '{table_name}'")
        
        # Skip if we don't have an expected schema for this table
        if table_name.lower() not in self.expected_schemas:
            logger.info(f"No expected schema defined for table '{table_name}'")
            return {'valid': True, 'table': table_name, 'missing_columns': []}
        
        # Get actual columns from the database
        db = self.db_manager.db
        if not db.connected:
            logger.error("Not connected to database")
            return {'valid': False, 'table': table_name, 'error': 'Not connected to database'}
        
        # Get columns with exact case preserved
        columns_query = """
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns 
            WHERE table_name = %s
        """
        result = db.execute_query(columns_query, [table_name])
        
        if 'error' in result and result['error']:
            logger.error(f"Error getting columns for table '{table_name}': {result['error']}")
            return {'valid': False, 'table': table_name, 'error': result['error']}
        
        # Create case-insensitive mapping of actual columns
        actual_columns = {}
        for row in result['rows']:
            col_name = row[0]  # Original case preserved
            col_type = row[1]
            
            # Store with lowercase key for case-insensitive lookup
            actual_columns[col_name.lower()] = {
                'name': col_name,  # Original case
                'type': col_type
            }
        
        expected_schema = self.expected_schemas[table_name.lower()]
        
        # Check for missing required columns using case-insensitive comparison
        missing_columns = []
        for col_name, col_type in expected_schema['required_columns'].items():
            if col_name.lower() not in actual_columns:
                missing_columns.append({
                    'name': col_name,
                    'type': col_type,
                    'required': True
                })
        
        # If the table is valid (has all required columns), return success
        if not missing_columns:
            logger.info(f"Table '{table_name}' has all required columns")
            return {'valid': True, 'table': table_name, 'missing_columns': []}
        
        # If auto-fix is enabled, add missing columns
        if auto_fix and table_name.lower() not in self.fixed_tables:
            success = self._add_missing_columns_safely(table_name, missing_columns, actual_columns)
            if success:
                self.fixed_tables.add(table_name.lower())
                # Validate again to confirm the fix worked, but without auto-fix to prevent loops
                return self.validate_table(table_name, auto_fix=False)
        
        # Return validation result
        logger.warning(f"Table '{table_name}' is missing required columns: {[col['name'] for col in missing_columns]}")
        return {'valid': False, 'table': table_name, 'missing_columns': missing_columns}
    
    def _add_missing_columns_safely(self, table_name: str, missing_columns: List[Dict[str, Any]], 
                                   actual_columns: Dict[str, Dict[str, Any]]) -> bool:
        """Add missing columns to a table with case-sensitivity awareness
        
        Args:
            table_name: The name of the table
            missing_columns: List of missing columns with their types
            actual_columns: Dictionary of existing columns (lowercase names as keys)
            
        Returns:
            bool: True if successful, False otherwise
        """
        db = self.db_manager.db
        success = True
        
        for column in missing_columns:
            col_name = column['name']
            col_type = column['type']
            col_name_lower = col_name.lower()
            
            # Check if the column already exists in a different case
            if col_name_lower in actual_columns:
                actual_col_name = actual_columns[col_name_lower]['name']
                logger.info(f"Column '{col_name}' already exists as '{actual_col_name}' in table '{table_name}'")
                continue
            
            # Add the column
            try:
                # Try with IF NOT EXISTS for PostgreSQL 12+
                try:
                    query = f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {col_name} {col_type}"
                    result = db.execute_update(query)
                    
                    if 'error' in result and result['error'] and "syntax error" in str(result['error']):
                        # IF NOT EXISTS not supported, fall back to normal ADD COLUMN
                        query = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}"
                        result = db.execute_update(query)
                except Exception:
                    # Fall back to normal ADD COLUMN
                    query = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}"
                    result = db.execute_update(query)
                
                if 'error' in result and result['error']:
                    error_msg = str(result['error'])
                    # Check if the error indicates column already exists
                    if "already exists" in error_msg:
                        logger.warning(f"Column '{col_name}' already exists in table '{table_name}' (with different case)")
                    else:
                        logger.error(f"Error adding column '{col_name}': {error_msg}")
                        success = False
                else:
                    logger.info(f"Successfully added column '{col_name}' to table '{table_name}'")
                    
            except Exception as e:
                logger.error(f"Exception adding column '{col_name}': {str(e)}")
                success = False
        
        return success
    
    def check_table_exists(self, table_name: str, create_if_missing: bool = False) -> bool:
        """Check if a table exists in the database
        
        Args:
            table_name: The name of the table to check
            create_if_missing: Whether to create the table if it doesn't exist
            
        Returns:
            bool: True if the table exists or was created, False otherwise
        """
        # Get list of tables from the database
        db = self.db_manager.db
        result = db.get_tables()
        
        if 'error' in result and result['error']:
            logger.error(f"Error getting tables: {result['error']}")
            return False
        
        existing_tables = [t.lower() for t in result['tables']]
        
        # If the table exists, return True
        if table_name.lower() in existing_tables:
            return True
        
        # If create_if_missing is True and we have a schema for this table, create it
        if create_if_missing and table_name.lower() in self.expected_schemas:
            success = self._create_table(table_name)
            return success
        
        return False
    
    def _create_table(self, table_name: str) -> bool:
        """Create a table with the expected schema
        
        Args:
            table_name: The name of the table to create
            
        Returns:
            bool: True if successful, False otherwise
        """
        if table_name.lower() not in self.expected_schemas:
            logger.error(f"No schema defined for table '{table_name}'")
            return False
        
        schema = self.expected_schemas[table_name.lower()]
        db = self.db_manager.db
        
        # Build the CREATE TABLE query
        query = f"CREATE TABLE {table_name} (\n"
        query += "    id SERIAL PRIMARY KEY,\n"
        
        # Add required columns
        for col_name, col_type in schema['required_columns'].items():
            query += f"    {col_name} {col_type} NOT NULL,\n"
        
        # Add optional columns
        for col_name, col_type in schema['optional_columns'].items():
            query += f"    {col_name} {col_type},\n"
        
        # Add created_at timestamp
        query += "    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n"
        query += ");"
        
        try:
            # Execute the CREATE TABLE query
            logger.info(f"Creating table '{table_name}' with schema: {schema}")
            result = db.execute_update(query)
            
            if 'error' in result and result['error']:
                logger.error(f"Error creating table '{table_name}': {result['error']}")
                return False
            
            logger.info(f"Successfully created table '{table_name}'")
            return True
            
        except Exception as e:
            logger.error(f"Exception creating table '{table_name}': {str(e)}")
            return False
    
    def validate_table_schema(self, table_name: str, auto_fix: bool = True):
        """Validate and fix table schema including column types
        
        Args:
            table_name: The name of the table to validate
            auto_fix: Whether to automatically fix issues
            
        Returns:
            Dict: Validation results
        """
        logger.info(f"Validating schema for table '{table_name}'")
        
        # Get actual columns and their types from database
        columns_query = """
            SELECT column_name, data_type, udt_name
            FROM information_schema.columns 
            WHERE table_name = %s
            ORDER BY ordinal_position
        """
        
        result = self.db_manager.db.execute_query(columns_query, (table_name,))
        
        # Create mapping of actual columns with their types
        actual_columns = {}
        for row in result['rows']:
            col_name = row[0].lower()  # Case-insensitive
            data_type = row[1]
            udt_name = row[2]  # Underlying type name (helpful for custom types)
            
            actual_columns[col_name] = {
                'name': row[0],  # Original case preserved
                'type': data_type,
                'udt_name': udt_name
            }
        
        # Get expected schema
        if table_name.lower() not in self.expected_schemas:
            logger.info(f"No expected schema defined for table '{table_name}'")
            return {'valid': True, 'table': table_name, 'missing_columns': [], 'type_mismatches': []}
        
        expected_schema = self.expected_schemas[table_name.lower()]
        
        # Check for missing columns and type mismatches
        missing_columns = []
        type_mismatches = []
        
        # Check required columns
        for col_name, col_type in expected_schema['required_columns'].items():
            expected_name = col_name.lower()
            expected_type = self._get_base_type(col_type).lower()
            
            if expected_name not in actual_columns:
                missing_columns.append({
                    'name': col_name,
                    'type': col_type,
                    'required': True
                })
            else:
                actual_type = actual_columns[expected_name]['type'].lower()
                
                # Check for type mismatches that need fixing
                if self._needs_type_conversion(actual_type, expected_type):
                    type_mismatches.append({
                        'name': actual_columns[expected_name]['name'],  # Use actual case
                        'actual_type': actual_type,
                        'expected_type': expected_type
                    })
        
        # Fix issues if auto_fix is enabled
        if auto_fix:
            # Fix missing columns first
            if missing_columns:
                logger.info(f"Auto-fixing table '{table_name}' by adding missing columns")
                self._add_missing_columns_safely(table_name, missing_columns, actual_columns)
            
            # Fix type mismatches second
            if type_mismatches:
                logger.info(f"Auto-fixing table '{table_name}' column types")
                for mismatch in type_mismatches:
                    self.fix_column_type(table_name, mismatch['name'], 
                                      mismatch['actual_type'], mismatch['expected_type'])
            
            # Re-validate after fixing (but don't auto-fix again to avoid loops)
            if missing_columns or type_mismatches:
                return self.validate_table_schema(table_name, auto_fix=False)
        
        return {
            'valid': len(missing_columns) == 0 and len(type_mismatches) == 0,
            'table': table_name,
            'missing_columns': missing_columns,
            'type_mismatches': type_mismatches
        }
    
    def _get_base_type(self, type_def):
        """Extract the base type from a type definition
        
        Args:
            type_def: Type definition (e.g., "NUMERIC(10,2)")
            
        Returns:
            str: Base type (e.g., "numeric")
        """
        # Split on first parenthesis or space
        match = re.match(r'^([a-z_]+)(\s*\(|$|\s)', type_def.lower())
        if match:
            return match.group(1)
        return type_def.lower()
    
    def _needs_type_conversion(self, actual_type, expected_type):
        """Determine if a type conversion is needed
        
        Args:
            actual_type: Current data type
            expected_type: Expected data type
            
        Returns:
            bool: True if conversion is needed, False otherwise
        """
        # Common type mappings that should be considered equivalent
        type_equivalents = {
            'character varying': 'varchar',
            'double precision': 'float8',
            'integer': 'int4',
            'bigint': 'int8',
            'numeric': 'decimal'
        }
        
        # Normalize types for comparison
        actual = type_equivalents.get(actual_type, actual_type)
        expected = type_equivalents.get(expected_type, expected_type)
        
        # Critical mismatches that need fixing
        critical_mismatches = [
            # (actual, expected)
            ('text', 'date'),
            ('varchar', 'date'),
            ('character varying', 'date'),
            ('text', 'decimal'),
            ('varchar', 'decimal'),
            ('character varying', 'decimal'),
            ('text', 'integer'),
            ('varchar', 'integer'),
            ('character varying', 'integer'),
            ('text', 'timestamp'),
            ('varchar', 'timestamp'),
            ('character varying', 'timestamp')
        ]
        
        # Check if we have a critical mismatch
        return (actual != expected) and ((actual, expected) in critical_mismatches)
    
    def fix_column_type(self, table_name, column_name, actual_type, expected_type):
        """Fix column type mismatches
        
        Args:
            table_name: The table name
            column_name: The column name
            actual_type: The current data type
            expected_type: The expected data type
            
        Returns:
            bool: True if successful, False otherwise
        """
        logger.info(f"Converting column '{column_name}' from {actual_type} to {expected_type}")
        
        # Special handling for common conversions
        if actual_type in ('text', 'varchar', 'character varying') and expected_type == 'date':
            # Text to date conversion
            try:
                # Clean the data first (remove any invalid values)
                clean_query = f"""
                UPDATE {table_name}
                SET {column_name} = NULL
                WHERE {column_name} IS NOT NULL AND {column_name} !~ E'^\\d{4}-\\d{2}-\\d{2}$'
                """
                
                clean_result = self.db_manager.execute_query(clean_query)
                if 'error' in clean_result and clean_result['error']:
                    logger.warning(f"Error cleaning {column_name} values: {clean_result['error']}")
                
                # Try direct conversion with validation
                query = f"""
                ALTER TABLE {table_name} 
                ALTER COLUMN {column_name} TYPE DATE 
                USING CASE 
                    WHEN {column_name} ~ E'^\\d{4}-\\d{2}-\\d{2}$' THEN {column_name}::DATE
                    ELSE NULL 
                END
                """
                
                result = self.db_manager.execute_query(query)
                
                if 'error' in result and result['error']:
                    # Fallback: Create new column approach
                    logger.warning(f"Direct conversion failed, trying alternate approach: {result['error']}")
                    success = self._column_type_fix_with_temp(table_name, column_name, expected_type)
                    if success:
                        self.type_conversions_performed.append({
                            'table': table_name,
                            'column': column_name,
                            'from_type': actual_type,
                            'to_type': expected_type,
                            'method': 'temp_column'
                        })
                        return True
                    else:
                        return False
                else:
                    logger.info(f"Successfully converted '{column_name}' to {expected_type}")
                    self.type_conversions_performed.append({
                        'table': table_name,
                        'column': column_name,
                        'from_type': actual_type,
                        'to_type': expected_type,
                        'method': 'direct'
                    })
                    return True
                    
            except Exception as e:
                logger.error(f"Error fixing column type: {str(e)}")
                return False
                
        elif actual_type in ('text', 'varchar', 'character varying') and expected_type in ('decimal', 'numeric'):
            # Text to numeric conversion
            success = self._column_type_fix_with_temp(table_name, column_name, expected_type)
            if success:
                self.type_conversions_performed.append({
                    'table': table_name,
                    'column': column_name,
                    'from_type': actual_type,
                    'to_type': expected_type,
                    'method': 'temp_column'
                })
            return success
            
        elif actual_type in ('text', 'varchar', 'character varying') and expected_type in ('integer', 'int', 'int4'):
            # Text to integer conversion
            try:
                # Clean the data first (remove any invalid values)
                clean_query = f"""
                UPDATE {table_name}
                SET {column_name} = NULL
                WHERE {column_name} IS NOT NULL AND {column_name} !~ E'^\\d+$'
                """
                
                clean_result = self.db_manager.execute_query(clean_query)
                
                # Try direct conversion with validation
                query = f"""
                ALTER TABLE {table_name} 
                ALTER COLUMN {column_name} TYPE INTEGER 
                USING CASE 
                    WHEN {column_name} ~ E'^\\d+$' THEN {column_name}::INTEGER
                    ELSE NULL 
                END
                """
                
                result = self.db_manager.execute_query(query)
                
                if 'error' in result and result['error']:
                    # Fallback: Create new column approach
                    logger.warning(f"Direct conversion failed, trying alternate approach: {result['error']}")
                    success = self._column_type_fix_with_temp(table_name, column_name, expected_type)
                    if success:
                        self.type_conversions_performed.append({
                            'table': table_name,
                            'column': column_name,
                            'from_type': actual_type,
                            'to_type': expected_type,
                            'method': 'temp_column'
                        })
                    return success
                else:
                    logger.info(f"Successfully converted '{column_name}' to {expected_type}")
                    self.type_conversions_performed.append({
                        'table': table_name,
                        'column': column_name,
                        'from_type': actual_type,
                        'to_type': expected_type,
                        'method': 'direct'
                    })
                    return True
                    
            except Exception as e:
                logger.error(f"Error fixing column type: {str(e)}")
                return False
                
        else:
            # Generic type conversion attempt
            try:
                query = f"""
                ALTER TABLE {table_name}
                ALTER COLUMN {column_name} TYPE {expected_type}
                USING {column_name}::{expected_type}
                """
                
                result = self.db_manager.execute_query(query)
                if 'error' in result and result['error']:
                    logger.error(f"Error converting column type: {result['error']}")
                    return False
                else:
                    logger.info(f"Successfully converted '{column_name}' to {expected_type}")
                    self.type_conversions_performed.append({
                        'table': table_name,
                        'column': column_name,
                        'from_type': actual_type,
                        'to_type': expected_type,
                        'method': 'direct'
                    })
                    return True
                    
            except Exception as e:
                logger.error(f"Error fixing column type: {str(e)}")
                return False
    
    def _column_type_fix_with_temp(self, table_name, column_name, expected_type):
        """Fix column type using a temporary column approach
        
        Args:
            table_name: The table name
            column_name: The column name
            expected_type: The expected data type
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Create temp column with correct type
        temp_name = f"temp_{column_name}"
        
        steps = [
            f"ALTER TABLE {table_name} ADD COLUMN {temp_name} {expected_type}",
            f"UPDATE {table_name} SET {temp_name} = {column_name}::{expected_type} WHERE {column_name} ~ r'^[0-9.]+$'",
            f"ALTER TABLE {table_name} DROP COLUMN {column_name}",
            f"ALTER TABLE {table_name} RENAME COLUMN {temp_name} TO {column_name}"
        ]
        
        for i, step in enumerate(steps):
            try:
                result = self.db_manager.execute_query(step)
                if 'error' in result and result['error']:
                    logger.error(f"Error in column type fix step {i+1}: {result['error']}")
                    
                    # Try to clean up if we failed after adding the temp column
                    if i > 0 and i < 3:
                        try:
                            self.db_manager.execute_query(f"ALTER TABLE {table_name} DROP COLUMN {temp_name}")
                        except:
                            pass
                            
                    return False
            except Exception as e:
                logger.error(f"Exception in column type fix step {i+1}: {str(e)}")
                return False
        
        logger.info(f"Successfully converted '{column_name}' to {expected_type} using temp column")
        return True
    
    def ensure_valid_schema(self, table_name: str) -> bool:
        """Ensure that a table exists and has the required columns with correct types
        
        This will create the table if it doesn't exist, add any missing columns,
        and correct column types as needed.
        
        Args:
            table_name: The name of the table to validate
            
        Returns:
            bool: True if the table exists and has all required columns with correct types
        """
        # Check if the table exists, create it if not
        if not self.check_table_exists(table_name, create_if_missing=True):
            return False
        
        # First, validate and fix columns using the original method
        result = self.validate_table(table_name, auto_fix=True)
        
        # Then, validate and fix column types using the new method
        type_result = self.validate_table_schema(table_name, auto_fix=True)
        
        return result['valid'] and type_result['valid']
    
    def validate_invoices_table(self, auto_fix: bool = True) -> Dict[str, Any]:
        """Validate the invoices table
        
        This is a convenience method that validates the invoices table
        and shows a message box with the results.
        
        Args:
            auto_fix: Whether to automatically add missing columns
            
        Returns:
            Dict: Validation results
        """
        result = self.validate_table('invoices', auto_fix=auto_fix)
        
        if not result['valid'] and not auto_fix:
            missing_cols = [col['name'] for col in result['missing_columns']]
            messagebox.showwarning(
                "Invoice Table Schema Issue",
                f"The invoices table is missing these required columns: {', '.join(missing_cols)}\n\n"
                "This may cause errors in the dashboard and reports."
            )
        
        return result
    
    def get_csv_import_mapping(self, table_name: str, csv_headers: List[str]) -> Dict[str, str]:
        """Generate a mapping from CSV headers to database columns
        
        Args:
            table_name: The name of the table to map to
            csv_headers: The headers from the CSV file
            
        Returns:
            Dict: A mapping from CSV headers to database columns
        """
        if table_name.lower() not in self.expected_schemas:
            return {}
        
        schema = self.expected_schemas[table_name.lower()]
        mapping = {}
        
        # Combine required and optional columns
        all_columns = {}
        all_columns.update(schema['required_columns'])
        all_columns.update(schema['optional_columns'])
        
        # Create potential mappings list with variations
        potential_mappings = {}
        for db_col in all_columns.keys():
            # Add original column name
            potential_mappings[db_col] = db_col
            
            # Add variations
            potential_mappings[db_col.replace('_', ' ')] = db_col
            potential_mappings[db_col.replace('_', '')] = db_col
            potential_mappings[db_col.title()] = db_col
            potential_mappings[db_col.title().replace('_', ' ')] = db_col
            potential_mappings[db_col.title().replace('_', '')] = db_col
            
            # Special cases for common variations
            if db_col == 'invoice_number':
                potential_mappings['invoice #'] = db_col
                potential_mappings['invoice#'] = db_col
                potential_mappings['Invoice #'] = db_col
                potential_mappings['Invoice#'] = db_col
            elif db_col == 'payment_status':
                potential_mappings['status'] = db_col
                potential_mappings['Status'] = db_col
            elif db_col == 'fund_paid_by':
                potential_mappings['fund'] = db_col
                potential_mappings['Fund'] = db_col
        
        # Try to match CSV headers to database columns
        for header in csv_headers:
            # Try exact match
            if header.lower() in potential_mappings:
                mapping[header] = potential_mappings[header.lower()]
                continue
                
            # Try normalizing the header
            normalized = header.lower().replace(' ', '_').replace('#', 'number')
            if normalized in all_columns:
                mapping[header] = normalized
        
        return mapping 
    
    def diagnose_table_schema(self, table_name: str) -> Dict:
        """Diagnose issues with a table schema by showing actual vs expected columns
        
        Args:
            table_name: The name of the table to diagnose
            
        Returns:
            Dict: Diagnostic information
        """
        if not self.db_manager.db.connected:
            return {'error': 'Not connected to database'}
        
        # Get actual columns from database
        result = self.db_manager.db.execute_query("""
            SELECT column_name, data_type, character_maximum_length 
            FROM information_schema.columns 
            WHERE table_name = %s
            ORDER BY ordinal_position
        """, [table_name])
        
        if 'error' in result and result['error']:
            return {'error': result['error']}
        
        # Get expected schema
        expected_schema = {}
        if table_name.lower() in self.expected_schemas:
            expected_schema = self.expected_schemas[table_name.lower()]
        
        # Compare actual vs expected
        actual_columns = []
        for row in result['rows']:
            col_name = row[0]
            data_type = row[1]
            max_length = row[2]
            
            type_with_length = data_type
            if max_length:
                type_with_length = f"{data_type}({max_length})"
            
            actual_columns.append({
                'name': col_name,
                'type': type_with_length,
                'lower_name': col_name.lower()
            })
        
        # Check for case mismatches
        case_mismatches = []
        if table_name.lower() in self.expected_schemas:
            required_cols = self.expected_schemas[table_name.lower()]['required_columns']
            for col_name in required_cols:
                for actual in actual_columns:
                    if col_name.lower() == actual['lower_name'] and col_name != actual['name']:
                        case_mismatches.append({
                            'expected': col_name,
                            'actual': actual['name']
                        })
        
        return {
            'table': table_name,
            'actual_columns': actual_columns,
            'expected_schema': expected_schema,
            'case_mismatches': case_mismatches
        }
    
    def get_schema_report(self, table_name: str) -> Dict:
        """Generate a comprehensive report on the table schema
        
        Args:
            table_name: The name of the table to check
            
        Returns:
            Dict: A report containing detailed schema information
        """
        diagnosis = self.diagnose_table_schema(table_name)
        
        # Add recommendations based on the diagnosis
        recommendations = []
        
        if 'case_mismatches' in diagnosis and diagnosis['case_mismatches']:
            recommendations.append({
                'issue': 'Case Mismatches',
                'description': 'Some columns exist with different case than expected',
                'actions': [
                    f"ALTER TABLE {table_name} RENAME COLUMN \"{mismatch['actual']}\" TO {mismatch['expected']};"
                    for mismatch in diagnosis['case_mismatches']
                ]
            })
        
        if 'missing_columns' in diagnosis and diagnosis['missing_columns']:
            recommendations.append({
                'issue': 'Missing Columns',
                'description': 'Required columns are missing from the table',
                'actions': [
                    f"ALTER TABLE {table_name} ADD COLUMN {col['name']} {col['type']};"
                    for col in diagnosis['missing_columns']
                ]
            })
        
        diagnosis['recommendations'] = recommendations
        diagnosis['fix_script'] = "\n".join([
            action
            for rec in recommendations
            for action in rec['actions']
        ])
        
        return diagnosis
    
    def initialize_database(self) -> Dict:
        """Initialize the database with all expected tables and schemas
        
        Returns:
            Dict: A report of the initialization process
        """
        if not self.db_manager.db.connected:
            return {'success': False, 'error': 'Not connected to database'}
        
        results = {
            'success': True,
            'created_tables': [],
            'errors': []
        }
        
        # Create each expected table
        for table_name, schema in self.expected_schemas.items():
            try:
                # Check if table exists
                table_exists = self.check_table_exists(table_name)
                
                if not table_exists:
                    # Create the table
                    success = self._create_table(table_name)
                    if success:
                        results['created_tables'].append(table_name)
                    else:
                        results['errors'].append({
                            'table': table_name,
                            'error': f"Failed to create table '{table_name}'"
                        })
                        results['success'] = False
                else:
                    # Validate and fix existing table
                    result = self.validate_table(table_name, auto_fix=True)
                    if not result['valid']:
                        results['errors'].append({
                            'table': table_name,
                            'error': f"Failed to validate table '{table_name}'",
                            'details': result
                        })
                        results['success'] = False
            except Exception as e:
                results['errors'].append({
                    'table': table_name,
                    'error': str(e)
                })
                results['success'] = False
        
        return results 

    def _analyze_table_data(self, table_name, parent_window):
        """Analyze data in a table for potential issues
        
        Args:
            table_name: The name of the table to analyze
            parent_window: The parent window for message boxes
        """
        try:
            # Show analysis window
            analysis_window = tk.Toplevel(parent_window)
            analysis_window.title(f"Data Analysis: {table_name}")
            analysis_window.geometry("600x400")
            
            # Create frame
            frame = ttk.Frame(analysis_window, padding="10")
            frame.pack(fill=tk.BOTH, expand=True)
            
            # Add header
            ttk.Label(frame, text=f"Data Analysis for {table_name}", 
                    font=("", 14, "bold")).pack(pady=(0, 15))
            
            # Create text widget for results
            results_text = tk.Text(frame, height=20, width=70)
            results_text.pack(fill=tk.BOTH, expand=True, pady=5)
            
            # Add scrollbar
            scrollbar = ttk.Scrollbar(results_text, orient=tk.VERTICAL, command=results_text.yview)
            results_text.configure(yscrollcommand=scrollbar.set)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Function to add text
            def add_text(text):
                results_text.insert(tk.END, text + "\n")
            
            # Get column info
            add_text(f"Analyzing table: {table_name}\n")
            
            columns_query = """
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = %s
            ORDER BY ordinal_position
            """
            columns_result = self.db_manager.db.execute_query(columns_query, (table_name,))
            
            if 'error' in columns_result and columns_result['error']:
                add_text(f"Error getting columns: {columns_result['error']}")
                return
            
            # Analyze each column
            for col_row in columns_result['rows']:
                col_name = col_row[0]
                data_type = col_row[1]
                
                add_text(f"\nColumn: {col_name} ({data_type})")
                
                # Count nulls
                null_query = f"SELECT COUNT(*) FROM {table_name} WHERE {col_name} IS NULL"
                null_result = self.db_manager.db.execute_query(null_query)
                
                if 'error' not in null_result or not null_result.get('error'):
                    null_count = null_result['rows'][0][0]
                    add_text(f"  - NULL values: {null_count}")
                
                # For text columns that should be dates
                if data_type.lower() in ('text', 'varchar', 'character varying') and 'date' in col_name.lower():
                    date_format_query = f"""
                    SELECT COUNT(*) FROM {table_name} 
                    WHERE {col_name} IS NOT NULL AND {col_name} !~ E'^\\d{4}-\\d{2}-\\d{2}$'
                    """
                    format_result = self.db_manager.db.execute_query(date_format_query)
                    
                    if 'error' not in format_result or not format_result.get('error'):
                        invalid_date_count = format_result['rows'][0][0]
                        if invalid_date_count > 0:
                            add_text(f"  - WARNING: {invalid_date_count} rows have invalid date formats")
                            add_text(f"  - Suggested fix: Convert {col_name} to DATE type")
                
                # For numeric columns
                if data_type.lower() in ('text', 'varchar', 'character varying') and ('amount' in col_name.lower() or 'price' in col_name.lower()):
                    numeric_query = f"""
                    SELECT COUNT(*) FROM {table_name} 
                    WHERE {col_name} IS NOT NULL AND {col_name} !~ E'^[0-9.]+$'
                    """
                    numeric_result = self.db_manager.db.execute_query(numeric_query)
                    
                    if 'error' not in numeric_result or not numeric_result.get('error'):
                        invalid_numeric_count = numeric_result['rows'][0][0]
                        if invalid_numeric_count > 0:
                            add_text(f"  - WARNING: {invalid_numeric_count} rows have non-numeric values")
                            add_text(f"  - Suggested fix: Convert {col_name} to NUMERIC type")
            
            # Add close button
            ttk.Button(frame, text="Close", command=analysis_window.destroy).pack(pady=10)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error analyzing table data: {str(e)}", parent=parent_window) 

    def _types_are_compatible(self, actual_type, udt_name, expected_type):
        """Check if actual and expected types are compatible
        
        Args:
            actual_type: The current data type
            udt_name: Underlying type name from PostgreSQL
            expected_type: The expected data type
            
        Returns:
            bool: True if types are compatible, False otherwise
        """
        # Type mappings to normalize PostgreSQL type names
        type_equivalents = {
            'character varying': 'varchar',
            'varchar': 'character varying',
            'int4': 'integer',
            'integer': 'int4',
            'int8': 'bigint',
            'bigint': 'int8',
            'float8': 'double precision',
            'double precision': 'float8',
            'numeric': 'decimal',
            'decimal': 'numeric',
            'bool': 'boolean',
            'boolean': 'bool',
            'timestamptz': 'timestamp with time zone',
            'timestamp with time zone': 'timestamptz'
        }
        
        # Normalize types for comparison
        normalized_actual = type_equivalents.get(actual_type, actual_type)
        normalized_expected = type_equivalents.get(expected_type, expected_type)
        
        # Direct match
        if normalized_actual == normalized_expected:
            return True
        
        # Check for special compatibility cases
        if normalized_expected == 'date':
            # These types can be converted to date
            compatible_with_date = ['date', 'timestamp', 'timestamptz']
            return normalized_actual in compatible_with_date
        
        # For numeric types, check if actual type has enough precision
        if normalized_expected in ['decimal', 'numeric']:
            # Numeric types can be converted to decimal
            return normalized_actual in ['decimal', 'numeric', 'integer', 'bigint', 'real', 'double precision']
        
        return False

    def validate_and_fix_column_types(self, table_name):
        """Check and automatically fix column data types in a table
        
        Args:
            table_name: The name of the table to check
            
        Returns:
            dict: Results of the validation and fixing process
        """
        logger.info(f"Checking and fixing column types for '{table_name}'")
        
        if table_name.lower() not in self.expected_schemas:
            logger.info(f"No expected schema defined for '{table_name}', skipping type check")
            return {'valid': True, 'fixed': False}
        
        # Get expected column types
        expected_schema = self.expected_schemas[table_name.lower()]
        
        # Merge required and optional columns
        expected_types = {}
        for col_name, col_type in expected_schema['required_columns'].items():
            expected_types[col_name.lower()] = col_type.lower()
        
        for col_name, col_type in expected_schema['optional_columns'].items():
            expected_types[col_name.lower()] = col_type.lower()
        
        # Get actual column information from database
        column_query = """
            SELECT column_name, data_type, udt_name
            FROM information_schema.columns
            WHERE table_name = %s
        """
        
        result = self.db_manager.db.execute_query(column_query, (table_name,))
        if 'error' in result and result['error']:
            logger.error(f"Error getting column info: {result['error']}")
            return {'valid': False, 'fixed': False, 'error': result['error']}
        
        # Find columns with incorrect types
        type_mismatches = []
        for row in result['rows']:
            col_name = row[0].lower()
            actual_type = row[1].lower()
            udt_name = row[2].lower()  # Underlying type name
            
            if col_name in expected_types:
                expected_type = self._get_base_type(expected_types[col_name])
                
                # Check if types don't match (considering equivalent types)
                if not self._types_are_compatible(actual_type, udt_name, expected_type):
                    type_mismatches.append({
                        'column': col_name,
                        'actual_type': actual_type,
                        'expected_type': expected_type
                    })
        
        # Fix type mismatches if any
        fixed_columns = []
        if type_mismatches:
            logger.info(f"Found {len(type_mismatches)} column type mismatches in '{table_name}'")
            
            for mismatch in type_mismatches:
                col_name = mismatch['column']
                from_type = mismatch['actual_type']
                to_type = mismatch['expected_type']
                
                logger.info(f"Fixing column '{col_name}' from {from_type} to {to_type}")
                success = self._convert_column_type_safely(table_name, col_name, from_type, to_type)
                
                if success:
                    fixed_columns.append(col_name)
                    logger.info(f"Successfully fixed column '{col_name}' type")
                    # Track the conversion
                    self.type_conversions_performed.append({
                        'table': table_name,
                        'column': col_name,
                        'from_type': from_type,
                        'to_type': to_type,
                        'method': 'robust_conversion'
                    })
                else:
                    logger.error(f"Failed to fix column '{col_name}' type")
        
        return {
            'valid': len(type_mismatches) == 0 or len(fixed_columns) == len(type_mismatches),
            'fixed': len(fixed_columns) > 0,
            'mismatches': type_mismatches,
            'fixed_columns': fixed_columns
        }

    def _convert_column_type_safely(self, table_name, column_name, from_type, to_type):
        """Convert a column from one type to another using safe methods
        
        Args:
            table_name: The table name
            column_name: The column name
            from_type: Current data type
            to_type: Target data type
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Special case for text to date conversion (most common issue)
            if from_type in ['text', 'character varying'] and to_type == 'date':
                return self._convert_text_to_date(table_name, column_name)
            
            # Special case for text to numeric conversion
            if from_type in ['text', 'character varying'] and to_type in ['numeric', 'decimal']:
                return self._convert_text_to_numeric(table_name, column_name)
            
            # Special case for text to integer conversion
            if from_type in ['text', 'character varying'] and to_type in ['integer', 'int4']:
                return self._convert_text_to_integer(table_name, column_name)
            
            # Generic conversion with explicit casting
            # Create a temporary column with the right type
            temp_col = f"temp_{column_name}"
            
            # Use transaction for safety
            self.db_manager.db.begin_transaction()
            
            # Create temp column with correct type
            add_query = f"ALTER TABLE {table_name} ADD COLUMN {temp_col} {to_type}"
            result = self.db_manager.db.execute_update(add_query)
            if 'error' in result and result['error']:
                logger.error(f"Error adding temp column: {result['error']}")
                self.db_manager.db.rollback_transaction()
                return False
            
            # Copy data with explicit casting
            update_query = f"UPDATE {table_name} SET {temp_col} = {column_name}::{to_type}"
            result = self.db_manager.db.execute_update(update_query)
            if 'error' in result and result['error']:
                logger.error(f"Error copying data: {result['error']}")
                self.db_manager.db.rollback_transaction()
                return False
            
            # Drop the original column
            drop_query = f"ALTER TABLE {table_name} DROP COLUMN {column_name}"
            result = self.db_manager.db.execute_update(drop_query)
            if 'error' in result and result['error']:
                logger.error(f"Error dropping column: {result['error']}")
                self.db_manager.db.rollback_transaction()
                return False
            
            # Rename temp column to original name
            rename_query = f"ALTER TABLE {table_name} RENAME COLUMN {temp_col} TO {column_name}"
            result = self.db_manager.db.execute_update(rename_query)
            if 'error' in result and result['error']:
                logger.error(f"Error renaming column: {result['error']}")
                self.db_manager.db.rollback_transaction()
                return False
            
            # Commit all changes
            self.db_manager.db.commit_transaction()
            return True
            
        except Exception as e:
            logger.error(f"Error converting column type: {str(e)}")
            try:
                self.db_manager.db.rollback_transaction()
            except:
                pass
            return False

    def _convert_text_to_date(self, table_name, column_name):
        """Special handling for text to date conversion with multiple format support
        
        Args:
            table_name: The table name
            column_name: The column name to convert
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create a temporary column with DATE type
            temp_col = f"temp_{column_name}"
            
            # Begin transaction
            self.db_manager.db.begin_transaction()
            
            # Add temp column
            add_query = f"ALTER TABLE {table_name} ADD COLUMN {temp_col} DATE"
            result = self.db_manager.db.execute_update(add_query)
            if 'error' in result and result['error']:
                logger.error(f"Error adding temp column: {result['error']}")
                self.db_manager.db.rollback_transaction()
                return False
            
            # Copy data with validation to handle multiple date formats
            update_query = f"""
            UPDATE {table_name} 
            SET {temp_col} = 
                CASE 
                    WHEN {column_name} ~ E'^\\d{{4}}-\\d{{2}}-\\d{{2}}$' THEN {column_name}::DATE
                    WHEN {column_name} ~ E'^\\d{{2}}/\\d{{2}}/\\d{{4}}$' THEN to_date({column_name}, 'MM/DD/YYYY')
                    WHEN {column_name} ~ E'^\\d{{2}}-\\d{{2}}-\\d{{4}}$' THEN to_date({column_name}, 'MM-DD-YYYY')
                    ELSE NULL 
                END
            """
            
            result = self.db_manager.db.execute_update(update_query)
            if 'error' in result and result['error']:
                logger.error(f"Error copying data: {result['error']}")
                self.db_manager.db.rollback_transaction()
                return False
            
            # Drop original column
            drop_query = f"ALTER TABLE {table_name} DROP COLUMN {column_name}"
            result = self.db_manager.db.execute_update(drop_query)
            if 'error' in result and result['error']:
                logger.error(f"Error dropping column: {result['error']}")
                self.db_manager.db.rollback_transaction()
                return False
            
            # Rename temp column
            rename_query = f"ALTER TABLE {table_name} RENAME COLUMN {temp_col} TO {column_name}"
            result = self.db_manager.db.execute_update(rename_query)
            if 'error' in result and result['error']:
                logger.error(f"Error renaming column: {result['error']}")
                self.db_manager.db.rollback_transaction()
                return False
            
            # Commit changes
            self.db_manager.db.commit_transaction()
            return True
            
        except Exception as e:
            logger.error(f"Error converting text to date: {str(e)}")
            try:
                self.db_manager.db.rollback_transaction()
            except:
                pass
            return False

    def _convert_text_to_numeric(self, table_name, column_name):
        """Special handling for text to numeric conversion with validation
        
        Args:
            table_name: The table name
            column_name: The column name to convert
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create a temporary column with NUMERIC type
            temp_col = f"temp_{column_name}"
            
            # Begin transaction
            self.db_manager.db.begin_transaction()
            
            # Add temp column
            add_query = f"ALTER TABLE {table_name} ADD COLUMN {temp_col} NUMERIC(12,2)"
            result = self.db_manager.db.execute_update(add_query)
            if 'error' in result and result['error']:
                logger.error(f"Error adding temp column: {result['error']}")
                self.db_manager.db.rollback_transaction()
                return False
            
            # Copy data with validation for numeric values
            update_query = f"""
            UPDATE {table_name} 
            SET {temp_col} = 
                CASE 
                    WHEN {column_name} ~ E'^[0-9]+(\\.[0-9]+)?$' THEN {column_name}::NUMERIC
                    WHEN {column_name} ~ E'^\\$[0-9]+(\\.[0-9]+)?$' THEN replace({column_name}, '$', '')::NUMERIC
                    ELSE NULL 
                END
            """
            
            result = self.db_manager.db.execute_update(update_query)
            if 'error' in result and result['error']:
                logger.error(f"Error copying data: {result['error']}")
                self.db_manager.db.rollback_transaction()
                return False
            
            # Drop original column
            drop_query = f"ALTER TABLE {table_name} DROP COLUMN {column_name}"
            result = self.db_manager.db.execute_update(drop_query)
            if 'error' in result and result['error']:
                logger.error(f"Error dropping column: {result['error']}")
                self.db_manager.db.rollback_transaction()
                return False
            
            # Rename temp column
            rename_query = f"ALTER TABLE {table_name} RENAME COLUMN {temp_col} TO {column_name}"
            result = self.db_manager.db.execute_update(rename_query)
            if 'error' in result and result['error']:
                logger.error(f"Error renaming column: {result['error']}")
                self.db_manager.db.rollback_transaction()
                return False
            
            # Commit changes
            self.db_manager.db.commit_transaction()
            return True
            
        except Exception as e:
            logger.error(f"Error converting text to numeric: {str(e)}")
            try:
                self.db_manager.db.rollback_transaction()
            except:
                pass
            return False

    def _convert_text_to_integer(self, table_name, column_name):
        """Special handling for text to integer conversion with validation
        
        Args:
            table_name: The table name
            column_name: The column name to convert
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create a temporary column with INTEGER type
            temp_col = f"temp_{column_name}"
            
            # Begin transaction
            self.db_manager.db.begin_transaction()
            
            # Add temp column
            add_query = f"ALTER TABLE {table_name} ADD COLUMN {temp_col} INTEGER"
            result = self.db_manager.db.execute_update(add_query)
            if 'error' in result and result['error']:
                logger.error(f"Error adding temp column: {result['error']}")
                self.db_manager.db.rollback_transaction()
                return False
            
            # Copy data with validation for integer values
            update_query = f"""
            UPDATE {table_name} 
            SET {temp_col} = 
                CASE 
                    WHEN {column_name} ~ E'^[0-9]+$' THEN {column_name}::INTEGER
                    ELSE NULL 
                END
            """
            
            result = self.db_manager.db.execute_update(update_query)
            if 'error' in result and result['error']:
                logger.error(f"Error copying data: {result['error']}")
                self.db_manager.db.rollback_transaction()
                return False
            
            # Drop original column
            drop_query = f"ALTER TABLE {table_name} DROP COLUMN {column_name}"
            result = self.db_manager.db.execute_update(drop_query)
            if 'error' in result and result['error']:
                logger.error(f"Error dropping column: {result['error']}")
                self.db_manager.db.rollback_transaction()
                return False
            
            # Rename temp column
            rename_query = f"ALTER TABLE {table_name} RENAME COLUMN {temp_col} TO {column_name}"
            result = self.db_manager.db.execute_update(rename_query)
            if 'error' in result and result['error']:
                logger.error(f"Error renaming column: {result['error']}")
                self.db_manager.db.rollback_transaction()
                return False
            
            # Commit changes
            self.db_manager.db.commit_transaction()
            return True
            
        except Exception as e:
            logger.error(f"Error converting text to integer: {str(e)}")
            try:
                self.db_manager.db.rollback_transaction()
            except:
                pass
            return False
