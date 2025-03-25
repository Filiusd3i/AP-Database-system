import re
import json
import os
from datetime import datetime, timedelta

class QueryManager:
    def __init__(self, app):
        self.app = app
        self.patterns = []
        self.schema = {}
        self.common_query_templates = []
        self.db_relationships = []
    
    def load_query_patterns(self):
        """Load query patterns from configuration file or create default patterns"""
        try:
            # Try to load schema first
            self._load_schema()
            
            # Try to load patterns
            if os.path.exists('query_patterns.json'):
                with open('query_patterns.json', 'r') as f:
                    self.patterns = json.load(f)
            else:
                # Create default patterns
                self._create_default_patterns()
                
                # Save the default patterns
                with open('query_patterns.json', 'w') as f:
                    json.dump(self.patterns, f, indent=2)
        except Exception as e:
            print(f"Error loading query patterns: {str(e)}")
            # Create default patterns without saving
            self._create_default_patterns()
    
    def _load_schema(self):
        """Load database schema from file if available"""
        try:
            if os.path.exists('db_schema.json'):
                with open('db_schema.json', 'r') as f:
                    schema_data = json.load(f)
                    # Update schema and relationships
                    self.schema = schema_data.get('schema', {})
                    self.db_relationships = schema_data.get('relationships', [])
        except Exception as e:
            print(f"Error loading schema: {str(e)}")
    
    def _create_default_patterns(self):
        """Create default query patterns"""
        self.patterns = [
            {
                "pattern": r"(?:show|list|get|display|what are)(?: the)? (?:all )?(?:of )?(?:my )?(.*?)(?:from|in|during|between|after|before|>|<)? ?(.*)?",
                "sql_template": "SELECT * FROM {table} {where_clause}",
                "example": "Show all expenses from January",
                "description": "This pattern is for basic queries to show all records from a table, optionally with a date filter."
            },
            {
                "pattern": r"(?:count|how many|total number of) (.*?) (?:are there|do I have|do we have|exists?|we have|are active|is active)(?:.*?(?:from|in|during|between|after|before|>|<)? ?(.*)?)?",
                "sql_template": "SELECT COUNT(*) FROM {table} {where_clause}",
                "example": "How many invoices do I have from last month",
                "description": "This pattern counts records in a table, optionally with a filter."
            },
            {
                "pattern": r"(?:what is|show|get|calculate) (?:the )?(?:total|sum of|sum)(?: the)? (.*?)(?:.*?(?:from|in|during|between|after|before|>|<)? ?(.*)?)?",
                "sql_template": "SELECT SUM({column}) FROM {table} {where_clause}",
                "example": "What is the total revenue in March",
                "description": "This pattern sums a column, optionally with a filter."
            },
            {
                "pattern": r"(?:what is|show|get|calculate) (?:the )?(?:average|avg|mean)(?: of)?(?: the)? (.*?)(?:.*?(?:from|in|during|between|after|before|>|<)? ?(.*)?)?",
                "sql_template": "SELECT AVG({column}) FROM {table} {where_clause}",
                "example": "What is the average expense amount",
                "description": "This pattern calculates the average of a column, optionally with a filter."
            },
            {
                "pattern": r"(?:what is|show|get|find) (?:the )?(?:largest|highest|maximum|max|biggest|most expensive)(?: of)?(?: the)? (.*?)(?:.*?(?:from|in|during|between|after|before|>|<)? ?(.*)?)?",
                "sql_template": "SELECT MAX({column}) FROM {table} {where_clause}",
                "example": "What is the largest expense in February",
                "description": "This pattern finds the maximum value in a column, optionally with a filter."
            },
            {
                "pattern": r"(?:what is|show|get|find) (?:the )?(?:smallest|lowest|minimum|min|cheapest|least expensive)(?: of)?(?: the)? (.*?)(?:.*?(?:from|in|during|between|after|before|>|<)? ?(.*)?)?",
                "sql_template": "SELECT MIN({column}) FROM {table} {where_clause}",
                "example": "What is the smallest payment received",
                "description": "This pattern finds the minimum value in a column, optionally with a filter."
            },
            {
                "pattern": r"(?:show|display|get|list) (.*?) (?:for|by|related to|associated with|joined with|connected to|from) (.*?)(?: where| with| having)? ?(.*)?",
                "sql_template": "SELECT {columns} FROM {primary_table} JOIN {related_table} ON {join_condition} {where_clause}",
                "example": "Show invoices for customer XYZ Corp",
                "description": "This pattern handles queries spanning multiple tables with relationships."
            }
        ]
        
        # Create common query templates
        self.common_query_templates = [
            "Show all {table}",
            "Show {table} from {date}",
            "What is the total {column} in {table}",
            "How many {table} do I have",
            "Show all unpaid invoices",
            "What is the average amount of {table}",
            "Show expenses by category",
            "Show revenue by month"
        ]
    
    def parse_natural_language(self, text):
        """Parse natural language query into SQL"""
        try:
            # Store the current query text for context
            self.current_query_text = text
            
            # Try the intent-based query generation first (new approach)
            result, explanation = self._parse_query_intent(text)
            if result is not None:
                return result, explanation
            
            # Try the specialized financial parser next
            sql, explanation = self._parse_financial_rules(text)
            if sql:
                return sql, explanation
            
            # Special handling for relationship queries
            if self._is_relationship_query(text):
                return self._handle_relationship_query(text)
            
            sql, explanation = self._try_match_patterns(text)
            if sql:
                return sql, explanation
                
            return None, None
        except Exception as e:
            print(f"Error parsing query: {str(e)}")
            return None, None
    
    def _parse_query_intent(self, text):
        """New intent-based approach that uses specialized methods instead of raw SQL"""
        text_lower = text.lower()
        
        # Check if we have access to the database_manager with the new AccessDatabaseFix
        if not hasattr(self.app, 'database_manager') or not hasattr(self.app.database_manager, 'access_db'):
            return None, None
        
        access_db = self.app.database_manager.access_db
        if not access_db or not access_db.connected:
            return None, None
        
        # Map common intents to specialized methods
        
        # 1. INTENT: Get invoice totals (sum of amounts)
        if any(phrase in text_lower for phrase in [
            "total invoice", "total amount", "sum of invoice", "sum of all invoice", 
            "total of all invoice", "invoice total", "total value of invoice"
        ]):
            try:
                # Use the specialized method instead of generating SQL
                invoice_totals = access_db.get_invoice_totals()
                if invoice_totals and 'total_amount' in invoice_totals:
                    # Create a result in the format expected by the app
                    result = {
                        'columns': ['Total Amount'],
                        'rows': [[invoice_totals['total_amount']]],
                        'row_count': 1,
                        'intent_based': True  # Mark this as an intent-based result
                    }
                    explanation = "I calculated the total amount of all invoices using a specialized method."
                    return result, explanation
            except Exception as e:
                print(f"Error with invoice totals intent: {e}")
        
        # 2. INTENT: Count invoices
        if any(phrase in text_lower for phrase in [
            "how many invoice", "count of invoice", "number of invoice", 
            "total number of invoice", "invoice count"
        ]):
            try:
                invoice_totals = access_db.get_invoice_totals()
                if invoice_totals and 'total_invoices' in invoice_totals:
                    result = {
                        'columns': ['Invoice Count'],
                        'rows': [[invoice_totals['total_invoices']]],
                        'row_count': 1,
                        'intent_based': True
                    }
                    explanation = "I counted the total number of invoices using a specialized method."
                    return result, explanation
            except Exception as e:
                print(f"Error with invoice count intent: {e}")
        
        # 3. INTENT: List all invoices
        if any(phrase in text_lower for phrase in [
            "list all invoice", "show all invoice", "get all invoice", 
            "display all invoice", "all invoice"
        ]):
            try:
                # Use the safe invoice data method instead of raw SQL
                invoices = access_db.get_invoice_data()
                if invoices:
                    # Convert to the format expected by the app
                    columns = list(invoices[0].keys())
                    rows = []
                    for invoice in invoices:
                        row = [invoice[col] for col in columns]
                        rows.append(row)
                    
                    result = {
                        'columns': columns,
                        'rows': rows,
                        'row_count': len(rows),
                        'intent_based': True
                    }
                    explanation = "I retrieved all invoices using a specialized method that avoids problematic columns."
                    return result, explanation
            except Exception as e:
                print(f"Error with list invoices intent: {e}")
        
        # 4. INTENT: List all vendors
        if any(phrase in text_lower for phrase in [
            "list all vendor", "show all vendor", "get all vendor", 
            "display all vendor", "all vendor"
        ]):
            try:
                vendors = access_db.get_vendor_data()
                if vendors:
                    columns = list(vendors[0].keys())
                    rows = []
                    for vendor in vendors:
                        row = [vendor[col] for col in columns]
                        rows.append(row)
                    
                    result = {
                        'columns': columns,
                        'rows': rows,
                        'row_count': len(rows),
                        'intent_based': True
                    }
                    explanation = "I retrieved all vendors using a specialized method."
                    return result, explanation
            except Exception as e:
                print(f"Error with list vendors intent: {e}")
        
        # 5. INTENT: Execute a safe query for any table
        for table in access_db.tables:
            table_phrases = [
                f"list all {table}", f"show all {table}", f"get all {table}",
                f"display all {table}", f"all {table}"
            ]
            
            # Convert table name to singular for natural language
            singular = table[:-1] if table.endswith('s') else table
            singular_phrases = [
                f"list all {singular}", f"show all {singular}", f"get all {singular}",
                f"display all {singular}", f"all {singular}"
            ]
            
            all_phrases = table_phrases + singular_phrases
            
            if any(phrase in text_lower for phrase in all_phrases):
                try:
                    # Use the safe query execution with brackets around column names
                    results = access_db.execute_safe_query(table)
                    if results:
                        columns = list(results[0].keys())
                        rows = []
                        for item in results:
                            row = [item[col] for col in columns]
                            rows.append(row)
                        
                        result = {
                            'columns': columns,
                            'rows': rows,
                            'row_count': len(rows),
                            'intent_based': True
                        }
                        explanation = f"I retrieved all {table} using a specialized method that brackets column names."
                        return result, explanation
                except Exception as e:
                    print(f"Error with list {table} intent: {e}")
        
        # No matching intent found
        return None, None
    
    def _parse_financial_rules(self, text):
        """Specialized rule-based parser for financial queries"""
        text_lower = text.lower()
        
        try:
            # 1. Unpaid vendors this month/period
            if any(term in text_lower for term in ["unpaid vendors", "vendors not paid", "which vendors haven't been paid"]):
                time_period = self._extract_time_period(text_lower)
                where_clause = ""
                
                if time_period:
                    where_clause = f" AND {time_period}"
                    
                sql = f"SELECT DISTINCT Vendor FROM Invoices WHERE Check = ''{where_clause} ORDER BY Vendor"
                explanation = "I'm showing vendors who have unpaid invoices for the specified time period."
                return sql, explanation
                
            # 2. Invoices over specific amount
            if any(phrase in text_lower for phrase in ["invoices over", "bills over", "invoices more than", "invoices greater than"]):
                amount = self._extract_amount(text_lower)
                if amount:
                    sql = f"SELECT * FROM Invoices WHERE Amount > {amount} ORDER BY Amount DESC"
                    explanation = f"I'm showing invoices with amounts greater than ${amount:,.2f}."
                    return sql, explanation
                
            # 3. Most unpaid invoices by vendor
            if any(phrase in text_lower for phrase in ["most unpaid", "highest number of unpaid", "who has the most unpaid"]):
                sql = """
                    SELECT Vendor, COUNT(*) as UnpaidCount 
                    FROM Invoices 
                    WHERE Check = '' 
                    GROUP BY Vendor 
                    ORDER BY UnpaidCount DESC
                """
                explanation = "I'm showing vendors ranked by the number of unpaid invoices they have."
                return sql, explanation
                
            # 4. Total spend by category/vendor/fund
            if "total spend" in text_lower or "total amount" in text_lower:
                # Determine what to group by
                group_by = "Vendor"  # Default
                
                if "category" in text_lower:
                    group_by = "Category"
                elif "fund" in text_lower:
                    group_by = "[Fund Paid By]"
                    
                # Determine time period
                time_period = self._extract_time_period(text_lower)
                where_clause = ""
                
                if time_period:
                    where_clause = f" WHERE {time_period}"
                    
                sql = f"""
                    SELECT {group_by}, SUM(Amount) as TotalSpend 
                    FROM Invoices{where_clause}
                    GROUP BY {group_by} 
                    ORDER BY TotalSpend DESC
                """
                explanation = f"I'm showing total spend grouped by {group_by.lower()}."
                return sql, explanation
                
            # 5. Largest/highest invoices 
            if any(term in text_lower for term in ["largest invoice", "biggest invoice", "highest amount", "largest payment"]):
                limit = 1
                # Check if they want top N
                top_match = re.search(r'(?:top|highest|largest) ([0-9]+)', text_lower)
                if top_match:
                    limit = int(top_match.group(1))
                    
                sql = f"SELECT TOP {limit} * FROM Invoices ORDER BY Amount DESC"
                explanation = f"I'm showing the {limit} largest invoice(s) by amount."
                return sql, explanation
                
            # 6. Recent/latest invoices
            if any(term in text_lower for term in ["recent invoice", "latest invoice", "newest invoice", "last invoice"]):
                limit = 5  # Default to showing 5
                # Check if they want top N
                top_match = re.search(r'(?:last|recent|latest) ([0-9]+)', text_lower)
                if top_match:
                    limit = int(top_match.group(1))
                    
                sql = f"SELECT TOP {limit} * FROM Invoices ORDER BY [Invoice Date] DESC"
                explanation = f"I'm showing the {limit} most recent invoice(s)."
                return sql, explanation
                
            # 7. Overdue invoices
            if "overdue" in text_lower:
                sql = "SELECT * FROM Invoices WHERE [Days Overdue] > 0 ORDER BY [Days Overdue] DESC"
                explanation = "I'm showing overdue invoices, ordered by the most overdue first."
                return sql, explanation
                
            # 8. Active/inactive vendors or employees
            if "active" in text_lower:
                table = "vendor list" if "vendor" in text_lower else "Employees"
                sql = f"SELECT * FROM [{table}] WHERE is_active = True"
                explanation = f"I'm showing active records from the {table} table."
                return sql, explanation
                
            if "inactive" in text_lower:
                table = "vendor list" if "vendor" in text_lower else "Employees"
                sql = f"SELECT * FROM [{table}] WHERE is_active = False"
                explanation = f"I'm showing inactive records from the {table} table."
                return sql, explanation
                
            # 9. Top vendors by amount
            if any(phrase in text_lower for phrase in ["top vendors", "biggest vendors", "highest spending vendors"]):
                limit = 5  # Default to top 5
                top_match = re.search(r'top ([0-9]+)', text_lower)
                if top_match:
                    limit = int(top_match.group(1))
                    
                sql = f"""
                    SELECT TOP {limit} Vendor, SUM(Amount) as TotalAmount
                    FROM Invoices
                    GROUP BY Vendor
                    ORDER BY TotalAmount DESC
                """
                explanation = f"I'm showing the top {limit} vendors by total invoice amount."
                return sql, explanation
                
            # 10. Payment status summary
            if any(phrase in text_lower for phrase in ["payment summary", "payment status", "paid vs unpaid"]):
                sql = """
                    SELECT 
                        CASE WHEN Check = '' THEN 'Unpaid' ELSE 'Paid' END as PaymentStatus,
                        COUNT(*) as InvoiceCount,
                        SUM(Amount) as TotalAmount
                    FROM Invoices
                    GROUP BY CASE WHEN Check = '' THEN 'Unpaid' ELSE 'Paid' END
                """
                explanation = "I'm showing a summary of paid versus unpaid invoices."
                return sql, explanation
            
            # 11. Payment summary by vendor
            if any(phrase in text_lower for phrase in ["payment summary by vendor", "which vendors are paid"]):
                sql = """
                    SELECT 
                        Vendor,
                        SUM(CASE WHEN Check = '' THEN 0 ELSE Amount END) as PaidAmount,
                        SUM(CASE WHEN Check = '' THEN Amount ELSE 0 END) as UnpaidAmount,
                        COUNT(CASE WHEN Check = '' THEN NULL ELSE 1 END) as PaidCount,
                        COUNT(CASE WHEN Check = '' THEN 1 ELSE NULL END) as UnpaidCount
                    FROM Invoices
                    GROUP BY Vendor
                    ORDER BY SUM(Amount) DESC
                """
                explanation = "I'm showing a payment summary for each vendor, with paid and unpaid amounts."
                return sql, explanation
                
            # No specialized rule matched
            return None, None
            
        except Exception as e:
            print(f"Error in financial rules parser: {str(e)}")
            return None, None
    
    def _extract_time_period(self, text):
        """Extract time period from text and return appropriate SQL condition"""
        # Current month/year
        if "this month" in text:
            return "MONTH([Invoice Date]) = MONTH(Date())"
        elif "this year" in text:
            return "YEAR([Invoice Date]) = YEAR(Date())"
            
        # Previous periods
        elif "last month" in text:
            return "MONTH([Invoice Date]) = MONTH(DateAdd('m', -1, Date())) AND YEAR([Invoice Date]) = YEAR(DateAdd('m', -1, Date()))"
        elif "last year" in text:
            return "YEAR([Invoice Date]) = YEAR(DateAdd('yyyy', -1, Date()))"
            
        # Specific months
        for month_name, month_num in {
            'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
            'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12,
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }.items():
            if month_name in text:
                return f"MONTH([Invoice Date]) = {month_num}"
                
        # Specific years
        year_match = re.search(r'\b(20\d{2})\b', text)
        if year_match:
            return f"YEAR([Invoice Date]) = {year_match.group(1)}"
            
        # Quarters
        if "q1" in text or "first quarter" in text:
            return "MONTH([Invoice Date]) BETWEEN 1 AND 3"
        elif "q2" in text or "second quarter" in text:
            return "MONTH([Invoice Date]) BETWEEN 4 AND 6"
        elif "q3" in text or "third quarter" in text:
            return "MONTH([Invoice Date]) BETWEEN 7 AND 9"
        elif "q4" in text or "fourth quarter" in text:
            return "MONTH([Invoice Date]) BETWEEN 10 AND 12"
            
        # Default to no time period constraint
        return None
    
    def _is_relationship_query(self, text):
        """Check if this query involves multiple tables/relationships"""
        relationship_keywords = [
            'join', 'related to', 'associated with', 'connected to', 
            'along with', 'including', 'together with', 'with their',
            'for vendor', 'by vendor', 'from vendor', 'for fund', 'by fund'
        ]
        
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in relationship_keywords)
    
    def _handle_relationship_query(self, text):
        """Handle queries that involve table relationships"""
        text_lower = text.lower()
        
        # Check for common relationship queries
        if 'invoice' in text_lower and 'vendor' in text_lower:
            # Query invoices with vendor information
            sql = self._build_invoice_vendor_query(text)
            explanation = "I'm showing invoice data with vendor information joined from the related tables."
            return sql, explanation
            
        elif 'invoice' in text_lower and 'fund' in text_lower:
            # Query invoices with fund information
            sql = self._build_invoice_fund_query(text)
            explanation = "I'm showing invoice data grouped by fund from the related tables."
            return sql, explanation
        
        elif any(quarter in text_lower for quarter in ['qz 2019', 'qz 2020', 'qz 2022', 'qz 2024']):
            # Query invoices by quarter
            sql = self._build_quarter_query(text)
            explanation = "I'm showing invoice data for the specified quarter."
            return sql, explanation
            
        # Try to detect the tables and relationships from the query
        return self._build_dynamic_join_query(text)
    
    def _build_invoice_vendor_query(self, text):
        """Build a query joining invoices and vendors"""
        # Check for filtering conditions
        where_clause = ""
        if 'unpaid' in text.lower() or 'pending' in text.lower():
            where_clause = " WHERE Check = ''"
        elif 'paid' in text.lower():
            where_clause = " WHERE Check <> ''"
        
        # Build the core query
        sql = f"SELECT Vendor, COUNT(*) as InvoiceCount, SUM(Amount) as TotalAmount FROM Invoices{where_clause} GROUP BY Vendor ORDER BY TotalAmount DESC"
        
        return sql
    
    def _build_invoice_fund_query(self, text):
        """Build a query showing invoices by fund"""
        # Check for filtering conditions
        where_clause = ""
        if 'unpaid' in text.lower() or 'pending' in text.lower():
            where_clause = " WHERE Check = ''"
        elif 'paid' in text.lower():
            where_clause = " WHERE Check <> ''"
        
        # Build the core query
        sql = f"SELECT [Fund Paid By], COUNT(*) as InvoiceCount, SUM(Amount) as TotalAmount FROM Invoices{where_clause} GROUP BY [Fund Paid By] ORDER BY TotalAmount DESC"
        
        return sql
    
    def _build_quarter_query(self, text):
        """Build a query filtering by quarter"""
        # Determine which quarter is requested
        text_lower = text.lower()
        quarter = None
        
        for q in ['qz 2019', 'qz 2020', 'qz 2022', 'qz 2024']:
            if q in text_lower:
                quarter = q.upper()
                break
        
        if not quarter:
            return None
            
        # Build the query with the quarter filter
        sql = f"SELECT * FROM Invoices WHERE [{quarter}] <> ''"
        
        return sql
    
    def _build_dynamic_join_query(self, text):
        """Attempt to build a join query based on detected tables and relationships"""
        # This is a more complex implementation that would analyze the query
        # and database relationships to build appropriate JOIN statements
        
        # Simplified implementation for now
        text_lower = text.lower()
        
        # First, identify mentioned tables
        mentioned_tables = []
        for table in self.app.database_manager.tables:
            # Check for table name or a likely plural form
            if table.lower() in text_lower or (table.lower()[:-1] + 's') in text_lower or (table.lower()[:-1] + 'es') in text_lower:
                mentioned_tables.append(table)
        
        if len(mentioned_tables) <= 1:
            # Not enough tables mentioned for a join query
            return None, None
        
        # Identify potential join relationships between mentioned tables
        join_possibilities = []
        for rel in self.db_relationships:
            if rel['parent_table'] in mentioned_tables and rel['child_table'] in mentioned_tables:
                join_possibilities.append(rel)
        
        if not join_possibilities and len(mentioned_tables) >= 2:
            # No explicit relationships but two tables mentioned
            # Try to infer a join condition based on common column patterns
            primary_table = mentioned_tables[0]
            secondary_table = mentioned_tables[1]
            
            # Look for ID columns to join on
            primary_id = f"{primary_table}ID"
            secondary_id = f"{secondary_table}ID"
            
            # Check if these columns exist in the respective tables
            primary_columns = [col['name'] for col in self.schema.get(primary_table, [])]
            secondary_columns = [col['name'] for col in self.schema.get(secondary_table, [])]
            
            if primary_id in secondary_columns:
                join_condition = f"{secondary_table}.{primary_id} = {primary_table}.ID"
                sql = f"SELECT * FROM {primary_table} JOIN {secondary_table} ON {join_condition}"
                explanation = f"I've joined {primary_table} and {secondary_table} based on their relationship."
                return sql, explanation
                
            elif secondary_id in primary_columns:
                join_condition = f"{primary_table}.{secondary_id} = {secondary_table}.ID"
                sql = f"SELECT * FROM {primary_table} JOIN {secondary_table} ON {join_condition}"
                explanation = f"I've joined {primary_table} and {secondary_table} based on their relationship."
                return sql, explanation
        
        # If we found relationships, build a join query
        if join_possibilities:
            rel = join_possibilities[0]  # Just use the first relationship for now
            join_condition = f"{rel['child_table']}.{rel['child_column']} = {rel['parent_table']}.{rel['parent_column']}"
            sql = f"SELECT * FROM {rel['parent_table']} JOIN {rel['child_table']} ON {join_condition}"
            explanation = f"I've joined {rel['parent_table']} and {rel['child_table']} based on their relationship."
            return sql, explanation
        
        # Fallback: no relationships found
        return None, None
    
    def _try_match_patterns(self, text):
        """Try to match the text against query patterns"""
        text_lower = text.lower()
        
        for pattern in self.patterns:
            match = re.search(pattern['pattern'], text_lower)
            if match:
                sql = self._build_sql_from_pattern(pattern, match, text)
                if sql:
                    explanation = f"I interpreted your question as a request to {pattern['description']}."
                    return sql, explanation
        
        return None, None
    
    def _build_sql_from_pattern(self, pattern, match, original_text):
        """Build an SQL query from a matched pattern"""
        sql_template = pattern['sql_template']
        
        # Extract groups from the match
        groups = match.groups()
        
        if 'JOIN' in sql_template:
            # This is a join query - needs special handling
            return self._build_join_query(pattern, groups, original_text)
        
        # Map the extracted text to table and column names
        table_name = self._map_to_table(groups[0])
        if not table_name:
            return None
            
        # For patterns that need a column name (SUM, AVG, etc.)
        if '{column}' in sql_template:
            column_name = self._map_to_column(groups[0], table_name)
            if not column_name:
                return None
            sql_template = sql_template.replace('{column}', column_name)
        
        # Replace the table placeholder
        sql_template = sql_template.replace('{table}', table_name)
        
        # Build where clause if there's a filter group
        where_clause = ""
        if len(groups) > 1 and groups[1]:
            where_clause = self._build_where_clause(groups[1], table_name)
        
        # Replace the where_clause placeholder
        sql_template = sql_template.replace('{where_clause}', where_clause)
        
        return sql_template
    
    def _build_join_query(self, pattern, groups, original_text):
        """Build a query with JOIN clauses based on relationships"""
        # This would be a more complex implementation using table relationships
        # For simplicity, we're returning None for now
        return None
    
    def _map_to_table(self, text):
        """Map natural language text to a database table name more flexibly"""
        if not text:
            return None
            
        text_lower = text.lower().strip()
        
        # Get available tables from the database
        available_tables = self.app.database_manager.tables
        
        # First, check for exact matches to quickly resolve direct table references
        for table in available_tables:
            if text_lower == table.lower():
                return table
        
        # Direct mappings for common entities - handles plurals and variations
        direct_mappings = {
            'vendor': 'vendor list',
            'vendors': 'vendor list',
            'invoice': 'Invoices',
            'invoices': 'Invoices',
            'fund': 'Funds',
            'funds': 'Funds',
            'employee': 'Employees',
            'employees': 'Employees',
            'deal allocation': 'Deal Allocations',
            'deal allocations': 'Deal Allocations',
            'vendor allocation': 'Vendor allocation',
            'vendor allocations': 'Vendor allocation',
        }
        
        # Check direct mappings
        for key, value in direct_mappings.items():
            if key in text_lower:
                # Ensure the mapped table actually exists in the database
                if value in available_tables or value.lower() in [t.lower() for t in available_tables]:
                    # Find the actual case-sensitive table name
                    for table in available_tables:
                        if table.lower() == value.lower():
                            return table
        
        # Handle more complex cases with fuzzy matching
        
        # 1. Check for singular/plural variations
        for table in available_tables:
            table_lower = table.lower()
            singular = table_lower.rstrip('s')
            
            # Check if the singular form or exact table name is in the text
            if singular in text_lower or table_lower in text_lower:
                return table
        
        # 2. Check for multi-word table names (split by underscore or camelCase)
        for table in available_tables:
            table_parts = []
            
            # Split by spaces
            if ' ' in table:
                table_parts = table.lower().split(' ')
            # Split by underscores
            elif '_' in table:
                table_parts = table.lower().split('_')
            # Split camelCase
            else:
                # Simple camelCase splitter
                last_cap = 0
                parts = []
                for i, char in enumerate(table):
                    if char.isupper() and i > 0:
                        parts.append(table[last_cap:i].lower())
                        last_cap = i
                if last_cap < len(table):
                    parts.append(table[last_cap:].lower())
                table_parts = parts
            
            # Check if all parts are in the text
            if table_parts and all(part.lower() in text_lower for part in table_parts):
                return table
        
        # 3. Handle special cases in financial contexts
        financial_mappings = {
            'expense': 'Expenses',
            'expenses': 'Expenses',
            'costs': 'Expenses',
            'bills': 'Invoices',
            'payments': 'Invoices',
            'clients': 'vendor list',
            'customers': 'vendor list',
            'sales': 'Revenue',
            'revenue': 'Revenue',
            'income': 'Revenue',
            'staff': 'Employees',
            'personnel': 'Employees',
            'team': 'Employees',
            'transactions': 'Invoices',
            'investment': 'Deal Allocations',
            'investments': 'Deal Allocations',
            'deals': 'Deal Allocations',
            'projects': 'Deal Allocations',
            'allocations': 'Deal Allocations',
        }
        
        for key, value in financial_mappings.items():
            if key in text_lower:
                # Verify the mapped table exists
                if value in available_tables or value.lower() in [t.lower() for t in available_tables]:
                    # Find the actual case-sensitive table name
                    for table in available_tables:
                        if table.lower() == value.lower():
                            return table
        
        # If we still don't have a match, try to make an educated guess based on context
        context_clues = {
            'amount': 'Invoices',  # Money amounts are likely in Invoices
            'paid': 'Invoices',    # Payment status is in Invoices
            'check': 'Invoices',   # Check numbers are in Invoices
            'date': 'Invoices',    # Dates often refer to Invoices
            'total': 'Invoices',   # Totals often refer to Invoices
            'due': 'Invoices',     # Due dates are in Invoices
            'name': 'vendor list', # Names often refer to Vendors
            'contact': 'vendor list', # Contacts are in Vendors table
            'email': 'vendor list', # Emails are in Vendors table
            'address': 'vendor list', # Addresses are in Vendors table
            'company': 'vendor list', # Companies are in Vendors table
            'fund': 'Funds',      # Fund references go to Funds table
            'salary': 'Employees', # Salary info is in Employees table
            'hire': 'Employees',   # Hire dates are in Employees table
            'manager': 'Employees', # Managers are in Employees table
            'project': 'Deal Allocations', # Projects are in Deal Allocations
            'deal': 'Deal Allocations',    # Deals are in Deal Allocations
            'invest': 'Deal Allocations',  # Investments are in Deal Allocations
        }
        
        for clue, table in context_clues.items():
            if clue in text_lower:
                # Verify the table exists
                if table in available_tables or table.lower() in [t.lower() for t in available_tables]:
                    # Find the actual case-sensitive table name
                    for actual_table in available_tables:
                        if actual_table.lower() == table.lower():
                            return actual_table
        
        # If we still can't determine, return the first table as a fallback
        if available_tables:
            # Log this for debugging
            print(f"Could not map '{text}' to a table name. Using {available_tables[0]} as fallback.")
            return available_tables[0]
            
        return None
    
    def _map_to_column(self, text, table_name):
        """Map extracted text to a column in the specified table"""
        text = text.lower().strip()
        
        # Common mappings for specific tables
        table_column_mappings = {
            'Expenses': {
                'amount': 'Amount',
                'total': 'Amount',
                'cost': 'Amount',
                'money': 'Amount',
                'price': 'Amount',
                'expense': 'Amount',
                'date': 'Date',
                'when': 'Date',
                'time': 'Date',
                'category': 'Category',
                'type': 'Category',
                'description': 'Description',
                'details': 'Description',
                'desc': 'Description',
                'notes': 'Description',
                'vendor': 'Vendor',
                'supplier': 'Vendor',
                'company': 'Vendor',
                'who': 'Vendor'
            },
            'Invoices': {
                'amount': 'Amount',
                'total': 'Amount',
                'cost': 'Amount',
                'money': 'Amount',
                'price': 'Amount',
                'invoice': 'Invoice#',
                'number': 'Invoice#',
                'invoice number': 'Invoice#',
                'date': 'Invoice Date',
                'invoice date': 'Invoice Date',
                'due date': 'Due Date',
                'deadline': 'Due Date',
                'status': 'Status',
                'state': 'Status',
                'fund': 'Fund Paid By',
                'client': 'Vendor',
                'customer': 'Vendor',
                'vendor': 'Vendor',
                'supplier': 'Vendor',
                'company': 'Vendor',
                'overdue': 'Days Overdue',
                'late': 'Days Overdue',
                'past due': 'Days Overdue',
                'check': 'Check',
                'payment': 'Check'
            },
            'Vendors': {
                'name': 'Name',
                'vendor': 'Name',
                'supplier': 'Name',
                'company': 'Name',
                'contact': 'Contact',
                'person': 'Contact',
                'phone': 'Phone',
                'telephone': 'Phone',
                'number': 'Phone',
                'email': 'Email',
                'mail': 'Email',
                'address': 'Address',
                'location': 'Address'
            },
            'Revenue': {
                'amount': 'Amount',
                'total': 'Amount',
                'revenue': 'Amount',
                'income': 'Amount',
                'money': 'Amount',
                'date': 'Date',
                'when': 'Date',
                'time': 'Date',
                'category': 'Category',
                'type': 'Category',
                'description': 'Description',
                'details': 'Description',
                'desc': 'Description',
                'notes': 'Description',
                'client': 'Client',
                'customer': 'Client',
                'company': 'Client',
                'who': 'Client'
            }
        }
        
        # Check if we have mappings for this table
        if table_name in table_column_mappings:
            mappings = table_column_mappings[table_name]
            
            # Try direct mapping
            if text in mappings:
                return mappings[text]
                
            # Try partial matches
            for key, value in mappings.items():
                if key in text or text in key:
                    return value
        
        # For Amount keyword, default to Amount column for any table
        if 'amount' in text or 'money' in text or 'total' in text or 'sum' in text:
            return 'Amount'
        
        # Check for actual column names in the table schema
        if table_name in self.schema:
            for column in self.schema[table_name]:
                col_name = column['name']
                if col_name.lower() in text or text in col_name.lower():
                    return col_name
        
        # Default to first column or ID
        if table_name in self.schema and self.schema[table_name]:
            return self.schema[table_name][0]['name']
        
        return 'Amount'  # Default to Amount if all else fails
    
    def _build_where_clause(self, filter_text, table_name):
        """Build a WHERE clause from the filter text"""
        filter_text = filter_text.lower().strip()
        
        # Empty filter means no WHERE clause
        if not filter_text:
            # Check if the main query text contains status filters
            main_query = self.current_query_text.lower() if hasattr(self, 'current_query_text') else ""
            
            # Handle specific status filters in the main query
            if "active" in main_query and table_name in ["Employees", "vendor list", "Vendors"]:
                return "WHERE is_active = True"
            elif "inactive" in main_query and table_name in ["Employees", "vendor list", "Vendors"]:
                return "WHERE is_active = False"
            
            return ""
            
        # Check for date filters
        months = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12,
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'jun': 6, 'jul': 7,
            'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }
        
        # Determine appropriate date column for the table
        date_column = self._get_date_column(table_name)
        
        # Status filters
        if "active" in filter_text and table_name in ["Employees", "vendor list", "Vendors"]:
            return "WHERE is_active = True"
        elif "inactive" in filter_text and table_name in ["Employees", "vendor list", "Vendors"]:
            return "WHERE is_active = False"
        
        # Month filter
        for month_name, month_num in months.items():
            if month_name in filter_text:
                return f"WHERE MONTH({date_column}) = {month_num}"
        
        # Quarter filter
        if "q1" in filter_text or "first quarter" in filter_text:
            return f"WHERE MONTH({date_column}) BETWEEN 1 AND 3"
        elif "q2" in filter_text or "second quarter" in filter_text:
            return f"WHERE MONTH({date_column}) BETWEEN 4 AND 6"
        elif "q3" in filter_text or "third quarter" in filter_text:
            return f"WHERE MONTH({date_column}) BETWEEN 7 AND 9"
        elif "q4" in filter_text or "fourth quarter" in filter_text:
            return f"WHERE MONTH({date_column}) BETWEEN 10 AND 12"
            
        # Year filter
        year_match = re.search(r'\b(20\d{2})\b', filter_text)
        if year_match:
            year = year_match.group(1)
            return f"WHERE YEAR({date_column}) = {year}"
            
        # Time periods
        if "last month" in filter_text:
            return f"WHERE MONTH({date_column}) = MONTH(DATEADD(month, -1, GETDATE()))"
        elif "this month" in filter_text:
            return f"WHERE MONTH({date_column}) = MONTH(GETDATE())"
        elif "last year" in filter_text:
            return f"WHERE YEAR({date_column}) = YEAR(DATEADD(year, -1, GETDATE()))"
        elif "this year" in filter_text:
            return f"WHERE YEAR({date_column}) = YEAR(GETDATE())"
        elif "ytd" in filter_text or "year to date" in filter_text:
            return f"WHERE YEAR({date_column}) = YEAR(GETDATE())"
            
        # Status filters for invoices
        if table_name == 'Invoices':
            if "unpaid" in filter_text or "pending" in filter_text:
                return "WHERE Check = ''"
            elif "paid" in filter_text:
                return "WHERE Check <> ''"
            elif "overdue" in filter_text:
                return "WHERE [Days Overdue] > 0"
        
        # Amount filters
        amount_match = re.search(r'(greater than|over|more than|above|>)\s*\$?(\d+)', filter_text)
        if amount_match:
            amount = amount_match.group(2)
            return f"WHERE Amount > {amount}"
            
        amount_match = re.search(r'(less than|under|below|<)\s*\$?(\d+)', filter_text)
        if amount_match:
            amount = amount_match.group(2)
            return f"WHERE Amount < {amount}"
            
        # Vendor filters
        vendor_match = re.search(r'from\s+(?:vendor|supplier)?s?\s+([A-Za-z0-9\s&]+)', filter_text)
        if vendor_match:
            vendor_name = vendor_match.group(1).strip()
            return f"WHERE Vendor LIKE '%{vendor_name}%'"
            
        # Category filters (for Expenses or Revenue)
        if table_name in ('Expenses', 'Revenue'):
            category_match = re.search(r'(category|type)\s+([A-Za-z0-9\s&]+)', filter_text)
            if category_match:
                category_name = category_match.group(2).strip()
                return f"WHERE Category LIKE '%{category_name}%'"
        
        # If we can't determine a specific filter, return empty WHERE clause
        return ""
    
    def _get_date_column(self, table_name):
        """Get the appropriate date column for a table"""
        date_columns = {
            'Expenses': 'Date',
            'Revenue': 'Date',
            'Invoices': 'Invoice Date',
            'Vendors': 'ID'  # No date column, use ID as fallback
        }
        
        return date_columns.get(table_name, 'Date')
    
    def get_query_suggestions(self, text):
        """Generate query suggestions based on the input text"""
        # Generate some relevant suggestions based on the tables in the database
        suggestions = []
        
        for template in self.common_query_templates:
            for table in self.app.database_manager.tables:
                # Skip suggestions that don't make sense
                if '{table}' in template and table in ('MSysAccessObjects', 'MSysObjects'):
                    continue
                    
                suggestion = template.replace('{table}', table.lower())
                
                # Replace {column} with a reasonable column if needed
                if '{column}' in suggestion:
                    # Get a suitable numeric column from the table
                    column = self._get_suitable_column(table)
                    if column:
                        suggestion = suggestion.replace('{column}', column.lower())
                    else:
                        continue  # Skip this suggestion if no suitable column
                
                # Replace {date} with current month
                if '{date}' in suggestion:
                    current_month = datetime.now().strftime('%B')
                    suggestion = suggestion.replace('{date}', current_month)
                
                suggestions.append(suggestion)
                
                # Limit to avoid too many suggestions
                if len(suggestions) >= 5:
                    break
            
            if len(suggestions) >= 5:
                break
        
        # Add relationship query suggestions
        if self.db_relationships:
            suggestions.append("Show invoices with vendor information")
            suggestions.append("Show expenses by vendor")
            
        # Format the suggestions
        if suggestions:
            suggestion_text = "You could try asking questions like:\n• " + "\n• ".join(suggestions[:5])
            return suggestion_text
        else:
            return "You can ask questions about your financial data."
    
    def _get_suitable_column(self, table_name):
        """Get a suitable numeric column from a table for suggestions"""
        # Default numeric columns by table
        default_columns = {
            'Expenses': 'Amount',
            'Revenue': 'Amount',
            'Invoices': 'Amount',
            'Vendors': 'ID'
        }
        
        if table_name in default_columns:
            return default_columns[table_name]
            
        # Try to find a numeric column in the schema
        if table_name in self.schema:
            for column in self.schema[table_name]:
                col_type = column['type'].lower()
                if 'int' in col_type or 'float' in col_type or 'double' in col_type or 'decimal' in col_type:
                    return column['name']
        
        return None
    
    def _extract_amount(self, text):
        """Extract monetary amount from text with support for different formats"""
        # Look for currency patterns with $ symbol
        currency_match = re.search(r'(?:\$\s*)([0-9,.]+)(?:k|K|M|thousand|million|)', text)
        if currency_match:
            amount_str = currency_match.group(1).replace(',', '')
            amount = float(amount_str)
            
            # Handle suffixes
            suffix = currency_match.group(0).lower()
            if 'k' in suffix or 'thousand' in suffix:
                amount *= 1000
            elif 'm' in suffix or 'million' in suffix:
                amount *= 1000000
                
            return amount
        
        # Look for patterns like "5000 dollars" or "10k"
        amount_match = re.search(r'([0-9,.]+)\s*(?:k|K|M|thousand|million|dollars|usd)', text)
        if amount_match:
            amount_str = amount_match.group(1).replace(',', '')
            amount = float(amount_str)
            
            # Handle suffixes
            suffix = amount_match.group(0).lower()
            if 'k' in suffix or 'thousand' in suffix:
                amount *= 1000
            elif 'm' in suffix or 'million' in suffix:
                amount *= 1000000
                
            return amount
            
        # Look for numbers following key phrases
        phrase_match = re.search(r'(over|above|more than|greater than|exceeding|at least)\s*([0-9,.]+)(?:k|K|M|thousand|million|)', text)
        if phrase_match:
            amount_str = phrase_match.group(2).replace(',', '')
            amount = float(amount_str)
            
            # Handle suffixes
            suffix = phrase_match.group(0).lower()
            if 'k' in suffix or 'thousand' in suffix:
                amount *= 1000
            elif 'm' in suffix or 'million' in suffix:
                amount *= 1000000
                
            return amount
            
        return None
    
    def get_fallback_suggestions(self, text):
        """Generate targeted fallback suggestions based on what the user might be trying to ask"""
        text_lower = text.lower()
        
        # Initialize with empty suggestions
        suggestions = []
        
        # Check for keywords and provide relevant suggestions
        if any(word in text_lower for word in ['vendor', 'suppliers', 'companies']):
            suggestions.append("Show me all vendors")
            suggestions.append("Which vendors are active?")
            suggestions.append("Who are our top 5 vendors by invoice amount?")
            
        if any(word in text_lower for word in ['invoice', 'bill', 'payment']):
            suggestions.append("Show me unpaid invoices")
            suggestions.append("Show me invoices over $5,000")
            suggestions.append("What's our largest invoice this year?")
            
        if any(word in text_lower for word in ['employee', 'staff', 'team']):
            suggestions.append("Show me all active employees")
            suggestions.append("How many employees do we have?")
            
        if any(word in text_lower for word in ['fund', 'allocation', 'investment']):
            suggestions.append("Show me all funds")
            suggestions.append("What deals are allocated to OZ 2019?")
            
        if any(word in text_lower for word in ['money', 'amount', 'total', 'spend', 'paid']):
            suggestions.append("What's our total spend this year?")
            suggestions.append("Show me total spend by vendor")
            suggestions.append("What's our largest payment?")
            
        # General suggestions if nothing specific is detected or not enough suggestions
        if len(suggestions) < 3:
            general_suggestions = [
                "Show me all unpaid invoices",
                "Which vendors haven't been paid this month?",
                "Show me invoices over $5,000",
                "Who has the most unpaid invoices?",
                "What's our total spend by category this year?",
                "Show me our active vendors",
                "What are our most recent invoices?"
            ]
            
            # Add general suggestions until we have at least 3
            for suggestion in general_suggestions:
                if suggestion not in suggestions:
                    suggestions.append(suggestion)
                    if len(suggestions) >= 5:  # Limit to 5 suggestions
                        break
        
        # Format the suggestions string
        formatted_suggestions = "I don't understand that query. Here are some suggestions:\n\n"
        formatted_suggestions += "\n".join(f"• {suggestion}" for suggestion in suggestions[:5])
        formatted_suggestions += "\n\nYou can also try more specific financial queries like counting items or filtering by dates."
        
        return formatted_suggestions 