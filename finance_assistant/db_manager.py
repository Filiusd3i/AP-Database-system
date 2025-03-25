def get_table_names(self):
    """Get list of table names in the database"""
    query = """
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema='public'
    ORDER BY table_name
    """
    result = self.execute_query(query)
    
    if result.get('error') or not result.get('rows'):
        return []
    
    return [row[0] for row in result['rows']]

def get_table_schema(self, table_name):
    """Get schema information for the specified table"""
    query = """
    SELECT column_name, data_type, character_maximum_length,
           is_nullable, column_default
    FROM information_schema.columns
    WHERE table_name = %s
    ORDER BY ordinal_position
    """
    result = self.execute_query(query, [table_name])
    
    if result.get('error'):
        return f"Error getting schema: {result['error']}"
    
    if not result.get('rows'):
        return f"No schema information found for table: {table_name}"
    
    # Format schema information as text
    schema_text = f"Schema for table: {table_name}\n\n"
    schema_text += "-" * 80 + "\n"
    schema_text += f"{'Column Name':<30}{'Data Type':<20}{'Length':<10}{'Nullable':<10}{'Default':<20}\n"
    schema_text += "-" * 80 + "\n"
    
    for row in result['rows']:
        column_name, data_type, max_length, nullable, default = row
        length_str = str(max_length) if max_length is not None else ""
        nullable_str = "YES" if nullable == "YES" else "NO"
        default_str = str(default) if default is not None else ""
        
        schema_text += f"{column_name:<30}{data_type:<20}{length_str:<10}{nullable_str:<10}{default_str:<20}\n"
    
    return schema_text 