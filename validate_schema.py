#!/usr/bin/env python
"""
Schema Validation Tool

This script validates the relationship schema against the actual table structures:
1. Checks that all tables referenced in the schema exist
2. Verifies that all columns referenced in relationships exist in their tables
3. Identifies potential column name discrepancies
4. Generates warning and error reports
"""

import os
import sys
import json
import pandas as pd
import logging
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager

# Add project directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from finance_assistant.tables_manager import TablesManager
    from finance_assistant.logging_config import configure_logging, log_table_operation
    from finance_assistant.logging_utils import log_csv_operation, log_duration, csv_audit_logger
except ImportError as e:
    print(f"Error importing required modules: {e}")
    # Configure basic logging as fallback
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    
# Configure CSV-focused logging
logger = configure_logging('schema_validator')

class SchemaValidator:
    """Validates the relationship schema against actual tables"""
    
    def __init__(self, tables_dir="Tables", schema_path="relationship_schema.json"):
        """Initialize with tables directory and schema path"""
        self.tables_dir = tables_dir
        self.schema_path = schema_path
        self.tables_manager = TablesManager(tables_dir)
        self.schema = None
        self.errors = []
        self.warnings = []
        self.suggestions = []
        
        self._load_schema()
    
    @log_csv_operation(logger)
    def _load_schema(self):
        """Load the relationship schema"""
        try:
            if os.path.exists(self.schema_path):
                with open(self.schema_path, 'r') as f:
                    self.schema = json.load(f)
                logger.info(f"Loaded schema from {self.schema_path}")
                
                # Basic schema validation
                if not isinstance(self.schema, dict) or 'relationships' not in self.schema:
                    self.errors.append("Schema is invalid: missing 'relationships' array")
                    self.schema = {"relationships": []}
            else:
                self.errors.append(f"Schema file not found: {self.schema_path}")
                self.schema = {"relationships": []}
        except json.JSONDecodeError as e:
            self.errors.append(f"Invalid JSON in schema file: {str(e)}")
            self.schema = {"relationships": []}
        except Exception as e:
            self.errors.append(f"Error loading schema: {str(e)}")
            self.schema = {"relationships": []}
    
    @log_csv_operation(logger)
    def get_table_columns(self, table_name):
        """Get the columns for a table"""
        try:
            with log_duration(logger, f"Loading table {table_name}"):
                df = self.tables_manager.get_table(table_name)
                
            if isinstance(df, dict) and 'error' in df:
                error_msg = f"Error loading table {table_name}: {df['error']}"
                self.errors.append(error_msg)
                logger.error(error_msg)
                return []
                
            logger.info(f"Loaded table {table_name} with {len(df.columns)} columns")
            return list(df.columns)
        except Exception as e:
            error_msg = f"Error loading table {table_name}: {str(e)}"
            self.errors.append(error_msg)
            logger.error(error_msg, exc_info=True)
            return []
    
    @log_csv_operation(logger)
    def find_similar_column(self, table_name, column_name):
        """Find a column with a similar name"""
        columns = self.get_table_columns(table_name)
        logger.debug(f"Searching for column similar to '{column_name}' in table '{table_name}'")
        
        # Check for case insensitive match
        for col in columns:
            if col.lower() == column_name.lower():
                logger.info(f"Found case-insensitive match for '{column_name}': '{col}' in table '{table_name}'")
                return col
        
        # Check for partial matches
        matches = []
        for col in columns:
            # If column_name is a prefix of col or vice versa
            if col.lower().startswith(column_name.lower()) or column_name.lower().startswith(col.lower()):
                matches.append(col)
            # If column_name without '_id' matches col or vice versa
            elif column_name.lower().endswith('_id') and col.lower() == column_name.lower()[:-3]:
                matches.append(col)
            elif col.lower().endswith('_id') and column_name.lower() == col.lower()[:-3]:
                matches.append(col)
        
        if matches:
            logger.info(f"Found similar column for '{column_name}': '{matches[0]}' in table '{table_name}'")
            return matches[0]  # Return the first match
        
        logger.debug(f"No similar column found for '{column_name}' in table '{table_name}'")
        return None
    
    @log_csv_operation(logger)
    def validate_tables_exist(self):
        """Validate that all tables referenced in the schema exist"""
        logger.info("Validating table existence")
        relationship_count = len(self.schema.get('relationships', []))
        logger.info(f"Checking {relationship_count} relationships")
        
        for rel in self.schema.get('relationships', []):
            main_table = rel.get('table')
            related_table = rel.get('related_table')
            rel_name = rel.get('name', 'unnamed')
            
            logger.debug(f"Checking tables for relationship: {rel_name}")
            
            # Check main table
            try:
                with log_duration(logger, f"Checking table existence: {main_table}"):
                    df = self.tables_manager.get_table(main_table)
                    
                if isinstance(df, dict) and 'error' in df:
                    error_msg = f"Table {main_table} not found (referenced in relationship {rel_name})"
                    self.errors.append(error_msg)
                    logger.error(error_msg)
                else:
                    logger.debug(f"Table {main_table} exists")
            except Exception as e:
                error_msg = f"Error loading table {main_table} (referenced in relationship {rel_name}): {str(e)}"
                self.errors.append(error_msg)
                logger.error(error_msg, exc_info=True)
            
            # Check related table
            try:
                with log_duration(logger, f"Checking table existence: {related_table}"):
                    df = self.tables_manager.get_table(related_table)
                    
                if isinstance(df, dict) and 'error' in df:
                    error_msg = f"Table {related_table} not found (referenced in relationship {rel_name})"
                    self.errors.append(error_msg)
                    logger.error(error_msg)
                else:
                    logger.debug(f"Table {related_table} exists")
            except Exception as e:
                error_msg = f"Error loading table {related_table} (referenced in relationship {rel_name}): {str(e)}"
                self.errors.append(error_msg)
                logger.error(error_msg, exc_info=True)
    
    @log_csv_operation(logger)
    def validate_columns_exist(self):
        """Validate that all columns referenced in the schema exist in their tables"""
        logger.info("Validating column existence")
        
        for rel in self.schema.get('relationships', []):
            main_table = rel.get('table')
            related_table = rel.get('related_table')
            main_column = rel.get('pk_column')
            related_column = rel.get('related_column')
            rel_name = rel.get('name', 'unnamed')
            
            logger.debug(f"Checking columns for relationship: {rel_name}")
            
            # Check main column
            main_columns = self.get_table_columns(main_table)
            if main_column not in main_columns:
                error_msg = f"Column {main_column} not found in table {main_table} (referenced in relationship {rel_name})"
                self.errors.append(error_msg)
                logger.error(error_msg)
                
                # Suggest a similar column
                similar = self.find_similar_column(main_table, main_column)
                if similar:
                    suggestion = f"Consider using '{similar}' instead of '{main_column}' in table {main_table}"
                    self.suggestions.append(suggestion)
                    logger.info(suggestion)
            else:
                logger.debug(f"Column {main_column} exists in table {main_table}")
            
            # Check related column
            related_columns = self.get_table_columns(related_table)
            if related_column not in related_columns:
                error_msg = f"Column {related_column} not found in table {related_table} (referenced in relationship {rel_name})"
                self.errors.append(error_msg)
                logger.error(error_msg)
                
                # Suggest a similar column
                similar = self.find_similar_column(related_table, related_column)
                if similar:
                    suggestion = f"Consider using '{similar}' instead of '{related_column}' in table {related_table}"
                    self.suggestions.append(suggestion)
                    logger.info(suggestion)
            else:
                logger.debug(f"Column {related_column} exists in table {related_table}")
    
    @log_csv_operation(logger)
    def check_data_types(self):
        """Check that the data types of related columns are compatible"""
        logger.info("Checking data type compatibility")
        
        for rel in self.schema.get('relationships', []):
            main_table = rel.get('table')
            related_table = rel.get('related_table')
            main_column = rel.get('pk_column')
            related_column = rel.get('related_column')
            rel_name = rel.get('name', 'unnamed')
            
            logger.debug(f"Checking data types for relationship: {rel_name}")
            
            # Get the tables
            with log_duration(logger, f"Loading tables for data type check: {main_table}, {related_table}"):
                main_df = self.tables_manager.get_table(main_table)
                related_df = self.tables_manager.get_table(related_table)
            
            if isinstance(main_df, dict) or isinstance(related_df, dict):
                logger.warning(f"Skipping data type check for relationship {rel_name} - tables could not be loaded")
                continue  # Skip if tables couldn't be loaded
            
            # Check if columns exist
            if main_column not in main_df.columns:
                logger.warning(f"Skipping data type check - column {main_column} not found in {main_table}")
                continue
                
            if related_column not in related_df.columns:
                logger.warning(f"Skipping data type check - column {related_column} not found in {related_table}")
                continue
            
            # Get the data types
            main_type = main_df[main_column].dtype
            related_type = related_df[related_column].dtype
            
            logger.debug(f"Data types: {main_table}.{main_column} is {main_type}, {related_table}.{related_column} is {related_type}")
            
            # Check for common type issues
            if main_type != related_type:
                warning_msg = f"Data type mismatch: {main_table}.{main_column} is {main_type} but {related_table}.{related_column} is {related_type}"
                self.warnings.append(warning_msg)
                logger.warning(warning_msg)
                
                # Provide more specific guidance
                if 'int' in str(main_type) and 'float' in str(related_type):
                    self.suggestions.append(f"Consider converting {related_table}.{related_column} to integer type")
                elif 'int' in str(related_type) and 'float' in str(main_type):
                    self.suggestions.append(f"Consider converting {main_table}.{main_column} to integer type")
                elif 'object' in str(main_type) and 'int' in str(related_type):
                    self.suggestions.append(f"Consider converting {main_table}.{main_column} from string to numeric type")
                elif 'object' in str(related_type) and 'int' in str(main_type):
                    self.suggestions.append(f"Consider converting {related_table}.{related_column} from string to numeric type")
            else:
                logger.debug(f"Data types match for {main_table}.{main_column} and {related_table}.{related_column}")
    
    @log_csv_operation(logger)
    def validate_schema(self):
        """Run all validation checks"""
        logger.info("Starting schema validation")
        
        # Clear previous results
        self.errors = []
        self.warnings = []
        self.suggestions = []
        
        # Run validation checks
        with log_duration(logger, "Validating table existence"):
            self.validate_tables_exist()
            
        with log_duration(logger, "Validating column existence"):
            self.validate_columns_exist()
            
        with log_duration(logger, "Checking data types"):
            self.check_data_types()
        
        # Log summary
        logger.info(f"Validation complete: {len(self.errors)} errors, {len(self.warnings)} warnings, {len(self.suggestions)} suggestions")
        
        # Return results
        return {
            "valid": len(self.errors) == 0,
            "errors": self.errors,
            "warnings": self.warnings,
            "suggestions": self.suggestions
        }
    
    @log_csv_operation(logger)
    def generate_updated_schema(self):
        """Generate an updated schema based on validation results"""
        logger.info("Generating updated schema")
        
        # Start with a deep copy of the original schema
        import copy
        updated_schema = copy.deepcopy(self.schema)
        
        # Make sure we have relationships
        if 'relationships' not in updated_schema:
            updated_schema['relationships'] = []
        
        # Track changes
        changes_made = False
        
        # Fix relationship entries
        for i, rel in enumerate(updated_schema['relationships']):
            rel_name = rel.get('name', f'relationship_{i}')
            
            # Fix table names if needed
            main_table = rel.get('table')
            related_table = rel.get('related_table')
            
            # Fix main table column if needed
            main_column = rel.get('pk_column')
            main_columns = self.get_table_columns(main_table)
            
            if main_column not in main_columns:
                similar = self.find_similar_column(main_table, main_column)
                if similar:
                    logger.info(f"Fixing column name in relationship {rel_name}: {main_column} -> {similar} in table {main_table}")
                    rel['pk_column'] = similar
                    changes_made = True
            
            # Fix related table column if needed
            related_column = rel.get('related_column')
            related_columns = self.get_table_columns(related_table)
            
            if related_column not in related_columns:
                similar = self.find_similar_column(related_table, related_column)
                if similar:
                    logger.info(f"Fixing column name in relationship {rel_name}: {related_column} -> {similar} in table {related_table}")
                    rel['related_column'] = similar
                    changes_made = True
        
        if changes_made:
            logger.info("Updated schema generated with fixes")
        else:
            logger.info("No changes needed in schema")
            
        return updated_schema, changes_made
    
    @log_csv_operation(logger)
    def save_updated_schema(self, output_path=None, username="system"):
        """Save the updated schema to a file"""
        updated_schema, changes_made = self.generate_updated_schema()
        
        if not changes_made:
            logger.info("No changes to save in schema")
            return False
        
        output_path = output_path or self.schema_path
        
        try:
            # Create backup of original schema
            if os.path.exists(self.schema_path):
                backup_path = f"{self.schema_path}.bak"
                import shutil
                shutil.copy2(self.schema_path, backup_path)
                logger.info(f"Created backup of original schema at {backup_path}")
            
            # Save updated schema
            with open(output_path, 'w') as f:
                json.dump(updated_schema, f, indent=2)
                
            logger.info(f"Saved updated schema to {output_path}")
            
            # Log the action
            csv_audit_logger.log_action(
                username, 
                "update_schema", 
                "relationship_schema", 
                None, 
                f"Fixed schema issues automatically"
            )
            
            return True
        except Exception as e:
            logger.error(f"Error saving updated schema: {str(e)}", exc_info=True)
            return False

def colorize(text, color):
    """Add color to console output"""
    colors = {
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'purple': '\033[95m',
        'end': '\033[0m'
    }
    
    # Only colorize if stdout is a terminal
    if sys.stdout.isatty():
        return f"{colors.get(color, '')}{text}{colors['end']}"
    else:
        return text

def main():
    """Main function to run validation as a script"""
    # Set up logging to file
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"schema_fix_{timestamp}.log"
    
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    logger.addHandler(file_handler)
    
    logger.info("="*60)
    logger.info("Starting schema validation")
    logger.info(f"Log file: {log_file}")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Platform: {sys.platform}")
    logger.info(f"Current directory: {os.getcwd()}")
    logger.info("="*60)
    
    try:
        # Parse command line arguments
        import argparse
        parser = argparse.ArgumentParser(description="Validate and fix schema relationships")
        parser.add_argument("--tables-dir", default="Tables", help="Directory containing CSV tables")
        parser.add_argument("--schema-path", default="relationship_schema.json", help="Path to relationship schema file")
        parser.add_argument("--auto-fix", action="store_true", help="Automatically fix schema issues")
        parser.add_argument("--username", default="system", help="Username for audit logging")
        args = parser.parse_args()
        
        # Initialize validator
        validator = SchemaValidator(args.tables_dir, args.schema_path)
        
        # Run validation
        results = validator.validate_schema()
        
        # Print results
        print("\n" + "="*60)
        print(colorize("SCHEMA VALIDATION RESULTS", "blue"))
        print("="*60)
        
        if results["valid"]:
            print(colorize("✓ Schema is valid!", "green"))
        else:
            print(colorize(f"✗ Schema has {len(results['errors'])} errors", "red"))
        
        if results["warnings"]:
            print(colorize(f"⚠ Found {len(results['warnings'])} warnings", "yellow"))
        
        if results["suggestions"]:
            print(colorize(f"ℹ Have {len(results['suggestions'])} improvement suggestions", "purple"))
        
        # Print errors
        if results["errors"]:
            print("\n" + colorize("ERRORS:", "red"))
            for i, error in enumerate(results["errors"]):
                print(f"{i+1}. {error}")
        
        # Print warnings
        if results["warnings"]:
            print("\n" + colorize("WARNINGS:", "yellow"))
            for i, warning in enumerate(results["warnings"]):
                print(f"{i+1}. {warning}")
        
        # Print suggestions
        if results["suggestions"]:
            print("\n" + colorize("SUGGESTIONS:", "purple"))
            for i, suggestion in enumerate(results["suggestions"]):
                print(f"{i+1}. {suggestion}")
        
        # Auto-fix if requested
        if args.auto_fix and (not results["valid"] or results["warnings"] or results["suggestions"]):
            print("\n" + colorize("AUTO-FIXING SCHEMA...", "blue"))
            if validator.save_updated_schema(username=args.username):
                print(colorize("✓ Schema updated successfully!", "green"))
            else:
                print(colorize("ℹ No changes made to schema", "blue"))
        
        print("\n" + "="*60)
        
        # Return appropriate exit code
        if not results["valid"]:
            return 1
        return 0
        
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
        print(colorize(f"ERROR: {str(e)}", "red"))
        return 1

if __name__ == "__main__":
    sys.exit(main())
