import os
import json
import logging
import traceback
from datetime import datetime
import re
from typing import Dict, List, Optional, Tuple, Any

# Add dotenv import
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

# Set up logger
logger = logging.getLogger("demo_manager")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler("demo_manager.log")
    fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(fh)

# Try to import OpenAI - this is optional and only used in demo mode
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    logger.warning("OpenAI package not available. Install with: pip install openai")
    OPENAI_AVAILABLE = False

from finance_assistant.template_manager import TemplateManager, QueryTemplate
from finance_assistant.database.connection import DatabaseConnection
from finance_assistant.demo.in_memory_db import DemoDatabase

class DemoManager:
    """Manages demo mode operation with OpenAI integration for template generation"""
    
    def __init__(self, app, app_state, template_db_path="query_templates.db"):
        """
        Initialize the demo manager.
        
        Args:
            app: The main application instance
            app_state: The ApplicationState instance for state management
            template_db_path: Path to the query templates database
        """
        self.app = app
        self.app_state = app_state
        self.ready = False
        self._initialization_steps = {
            "state_received": False,
            "templates_loaded": False,
            "openai_checked": False
        }
        
        # Register as an observer for state changes
        self.app_state.register_observer(self)
        
        # Template manager initialization
        self.template_db_path = template_db_path
        self.template_manager = TemplateManager(db_path=template_db_path)
        
        # Database connection
        self.db_connection = None
        
        # OpenAI client
        self.openai_client = None
        self.openai_model = "gpt-3.5-turbo"  # Default model, can use gpt-4 if available
        
        # Load environment variables if dotenv is available
        if DOTENV_AVAILABLE:
            # Load from .env file
            load_dotenv()
            # Check if a specific model is specified
            env_model = os.environ.get("OPENAI_MODEL")
            if env_model:
                self.openai_model = env_model
        
        # Load or import default templates
        self._load_templates()
        
        # Initialize OpenAI
        self._init_openai()
        
        # Mark OpenAI initialization as complete
        self._initialization_steps["openai_checked"] = True
        self._check_readiness()
    
    def on_demo_mode_changed(self, is_active):
        """
        Handle demo mode state change notification.
        Called when the application state changes.
        """
        logger.info(f"DemoManager received demo mode change: {is_active}")
        
        # Mark state as received
        self._initialization_steps["state_received"] = True
        
        if is_active:
            logger.info("Demo mode activated, initializing in-memory database")
            # Initialize in-memory database
            try:
                if not self.db_connection:
                    self.db_connection = DemoDatabase()
                    self.db_connection.connect()
                    logger.info("Demo database initialized")
            except Exception as e:
                logger.error(f"Failed to initialize demo database: {str(e)}")
                logger.error(traceback.format_exc())
        else:
            logger.info("Demo mode deactivated")
            # Close database connection if exists
            if self.db_connection:
                try:
                    self.db_connection.close()
                    logger.info("Demo database connection closed")
                except Exception as e:
                    logger.error(f"Error closing demo database connection: {str(e)}")
        
        self._check_readiness()
    
    def _check_readiness(self):
        """Check if all initialization steps are complete"""
        self.ready = all(self._initialization_steps.values())
        readiness_status = {k: v for k, v in self._initialization_steps.items()}
        logger.info(f"DemoManager readiness check: {readiness_status}")
        
        if self.ready:
            logger.info("DemoManager is now fully initialized and ready")
        return self.ready
    
    def _load_templates(self):
        """Load or import default templates"""
        try:
            if not self.template_manager.templates:
                logger.info("No templates found, importing defaults")
                self.template_manager.import_defaults()
            else:
                logger.info(f"Loaded {len(self.template_manager.templates)} templates")
                
            self._initialization_steps["templates_loaded"] = True
            self._check_readiness()
        except Exception as e:
            logger.error(f"Error loading templates: {str(e)}")
            logger.error(traceback.format_exc())
    
    def _init_openai(self):
        """Initialize OpenAI client if API key is available"""
        if not OPENAI_AVAILABLE:
            logger.warning("OpenAI integration not available. Demo mode will use templates only.")
            return False
            
        # Try to get API key from environment variable
        api_key = os.environ.get("OPENAI_API_KEY")
        
        # If not available, check for a key file
        if not api_key:
            try:
                if os.path.exists("openai_key.txt"):
                    with open("openai_key.txt", "r") as f:
                        api_key = f.read().strip()
            except Exception as e:
                logger.error(f"Error reading API key file: {str(e)}")
        
        # Initialize client if we have a key
        if api_key:
            try:
                self.openai_client = OpenAI(api_key=api_key)
                logger.info("OpenAI client initialized successfully")
                return True
            except Exception as e:
                logger.error(f"Error initializing OpenAI client: {str(e)}")
                self.openai_client = None
        else:
            logger.warning("No OpenAI API key found. Please set OPENAI_API_KEY in your .env file, as an environment variable, or create openai_key.txt")
        
        return False
    
    def process_query(self, user_query):
        """Process a user query using the demo system"""
        logger.info(f"Processing demo query: {user_query}")
        
        # Check if demo mode is active
        if not self.app_state.is_demo_mode():
            logger.warning("Attempted to process query with demo mode inactive")
            return {"error": "Demo mode is not active. Please activate demo mode first."}
        
        # Check if we're ready
        if not self.ready:
            logger.warning("DemoManager is not ready yet")
            return {"error": "Demo system is initializing. Please try again in a moment."}
        
        # Try to find matching template
        template_match = self.template_manager.find_matching_template(user_query)
        
        if template_match:
            logger.info(f"Found matching template with confidence {template_match.confidence}")
            return self._process_with_template(template_match, user_query)
        elif self.openai_client:
            logger.info("No matching template found, using OpenAI to generate response")
            return self._process_with_openai(user_query)
        else:
            logger.warning("No matching template and OpenAI not available")
            return {"error": "I don't understand that query and OpenAI integration is not available."}
    
    def _process_with_template(self, template_match, user_query):
        """Process a query using a matching template"""
        try:
            logger.info(f"Processing with template: {template_match.template_id}")
            
            # Extract parameters from the query
            parameters = self.template_manager.extract_parameters(template_match.template, user_query)
            logger.info(f"Extracted parameters: {parameters}")
            
            # Handle different types of templates
            if template_match.query_type == "SELECT":
                # Execute the SQL query
                if not self.db_connection:
                    return {"error": "Database connection not available"}
                
                # Replace parameter placeholders in the SQL
                sql = template_match.sql
                for param_name, param_value in parameters.items():
                    # Format parameters appropriately
                    if isinstance(param_value, str):
                        formatted_value = f"'{param_value}'"
                    else:
                        formatted_value = str(param_value)
                    
                    # Replace in SQL
                    sql = sql.replace(f":{param_name}", formatted_value)
                
                logger.info(f"Executing SQL: {sql}")
                results = self.db_connection.execute_query(sql)
                
                # Create response
                response = {
                    "type": "data",
                    "data": results,
                    "message": template_match.response_template
                }
                
                # Format message with parameter values
                if parameters and template_match.response_template:
                    response["message"] = template_match.response_template.format(**parameters)
                
                return response
            
            elif template_match.query_type == "AGGREGATE":
                # Execute aggregate query
                if not self.db_connection:
                    return {"error": "Database connection not available"}
                
                # Replace parameter placeholders in the SQL
                sql = template_match.sql
                for param_name, param_value in parameters.items():
                    # Format parameters appropriately
                    if isinstance(param_value, str):
                        formatted_value = f"'{param_value}'"
                    else:
                        formatted_value = str(param_value)
                    
                    # Replace in SQL
                    sql = sql.replace(f":{param_name}", formatted_value)
                
                logger.info(f"Executing aggregate SQL: {sql}")
                results = self.db_connection.execute_query(sql)
                
                # For aggregate queries, format the result
                if results and len(results) > 0:
                    # Get the first result (should only be one for aggregates)
                    result = results[0]
                    
                    # Create response with the aggregate value
                    response = {
                        "type": "aggregate",
                        "data": result,
                        "message": template_match.response_template
                    }
                    
                    # Add parameters to use in formatting
                    format_dict = {**parameters, **result}
                    
                    # Format message with parameter values and result
                    if template_match.response_template:
                        response["message"] = template_match.response_template.format(**format_dict)
                    
                    return response
                else:
                    return {"error": "No results found for this query"}
            
            else:
                logger.warning(f"Unsupported query type: {template_match.query_type}")
                return {"error": "This query type is not supported"}
                
        except Exception as e:
            logger.error(f"Error processing template: {str(e)}")
            logger.error(traceback.format_exc())
            return {"error": f"Error processing your query: {str(e)}"}
    
    def _process_with_openai(self, user_query):
        """Process a query using OpenAI to generate a response"""
        try:
            logger.info("Processing with OpenAI")
            
            # Prepare system message with information about available tables and schema
            system_message = self._generate_system_prompt()
            
            # Create chat completion request
            logger.info(f"Sending request to OpenAI model: {self.openai_model}")
            response = self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_query}
                ],
                temperature=0.7,
                max_tokens=1500
            )
            
            # Get the response text
            response_text = response.choices[0].message.content
            logger.info(f"Received response from OpenAI: {response_text[:100]}...")
            
            # Try to detect if this contains SQL
            if "SELECT" in response_text.upper() and "FROM" in response_text.upper():
                # Try to extract SQL from the response
                sql = self._extract_sql(response_text)
                if sql:
                    logger.info(f"Extracted SQL from response: {sql}")
                    
                    # Execute the extracted SQL
                    try:
                        results = self.db_connection.execute_query(sql)
                        
                        # Create a new template from this successful query
                        self._create_template_from_query(user_query, sql)
                        
                        return {
                            "type": "data",
                            "data": results,
                            "message": response_text
                        }
                    except Exception as e:
                        logger.error(f"Error executing extracted SQL: {str(e)}")
                        return {
                            "type": "text",
                            "message": f"I understood your question, but there was an error in the SQL: {str(e)}"
                        }
            
            # If no SQL detected or extraction failed, return text response
            return {
                "type": "text",
                "message": response_text
            }
            
        except Exception as e:
            logger.error(f"Error processing with OpenAI: {str(e)}")
            logger.error(traceback.format_exc())
            return {"error": f"Error processing your query with AI: {str(e)}"}
    
    def _generate_system_prompt(self):
        """Generate a system prompt with database schema information"""
        prompt = "You are a helpful financial database assistant. "
        
        # Add schema information if available
        if self.db_connection and hasattr(self.db_connection, 'schema_cache'):
            prompt += "The database contains the following tables:\n\n"
            
            for table_name, columns in self.db_connection.schema_cache.items():
                prompt += f"Table: {table_name}\n"
                prompt += f"Columns: {', '.join(columns)}\n\n"
            
            prompt += "When answering questions, generate SQL queries when appropriate. "
            prompt += "Format SQL inside triple backticks like ```sql SELECT * FROM table ```.\n\n"
            prompt += "Always use proper column names and be careful with date formats.\n"
            prompt += "For financial values, format them with proper currency symbols and decimal places.\n"
        else:
            prompt += "I help answer questions about financial data.\n"
        
        return prompt
    
    def _extract_sql(self, text):
        """Extract SQL query from a text response"""
        # Look for SQL in code blocks first
        sql_pattern = r"```sql(.*?)```"
        matches = re.findall(sql_pattern, text, re.DOTALL)
        
        if matches:
            return matches[0].strip()
        
        # Try alternate pattern with just sql keyword
        sql_pattern = r"```(.*?)```"
        matches = re.findall(sql_pattern, text, re.DOTALL)
        
        if matches:
            for match in matches:
                if "SELECT" in match.upper() and "FROM" in match.upper():
                    return match.strip()
        
        # Try to find SQL without code blocks
        sql_pattern = r"SELECT\s+.*?FROM\s+.*?(?:WHERE|GROUP BY|ORDER BY|LIMIT|;|$)"
        matches = re.findall(sql_pattern, text, re.DOTALL | re.IGNORECASE)
        
        if matches:
            return matches[0].strip()
        
        return None
    
    def _create_template_from_query(self, user_query, sql):
        """Create a new template from a successful query"""
        try:
            # Determine query type
            query_type = "SELECT"
            if "COUNT(" in sql.upper() or "SUM(" in sql.upper() or "AVG(" in sql.upper():
                query_type = "AGGREGATE"
            
            # Create a response template
            response_template = "Here are the results of your query."
            
            # Create a new template
            template = QueryTemplate(
                template_id=None,  # Will be assigned when saved
                template=user_query,
                sql=sql,
                query_type=query_type,
                response_template=response_template,
                parameters={},
                success_count=1,
                created_date=datetime.now().isoformat()
            )
            
            # Save the template
            template_id = self.template_manager.add_template(template)
            logger.info(f"Created new template: {template_id}")
            
            return template_id
        except Exception as e:
            logger.error(f"Error creating template from query: {str(e)}")
            return None
    
    def health_status(self):
        """Return health status of the DemoManager"""
        status = {
            "status": "healthy" if self.ready else "initializing",
            "openai_available": self.openai_client is not None,
            "template_count": len(self.template_manager.templates) if hasattr(self.template_manager, 'templates') else 0,
            "database_connection": "active" if self.db_connection else "inactive",
            "initialization_steps": self._initialization_steps
        }
        
        # Add database status if available
        if self.db_connection:
            # Check if attributes exist, otherwise provide defaults
            status["database_type"] = "in_memory_sqlite"
            if hasattr(self.db_connection, 'db_path'):
                status["database_path"] = self.db_connection.db_path
            elif hasattr(self.db_connection, 'connection'):
                status["database_path"] = ":memory:"
        
        return status 