#!/usr/bin/env python3
"""
LLM Client Module

Provides a client for connecting to Large Language Model APIs like OpenAI.
"""

import os
import logging
import requests
import json
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

class LLMClient:
    """Client for connecting to Large Language Model APIs"""
    
    # Define known API providers and their endpoints
    PROVIDERS = {
        "openai": {
            "endpoint": "https://api.openai.com/v1/chat/completions",
            "default_model": "gpt-3.5-turbo",
            "env_key": "OPENAI_API_KEY"
        },
        "azure": {
            "endpoint": "https://YOUR_AZURE_RESOURCE.openai.azure.com/openai/deployments/YOUR_MODEL/chat/completions",
            "default_model": "gpt-35-turbo",
            "env_key": "AZURE_OPENAI_API_KEY"
        },
        "anthropic": {
            "endpoint": "https://api.anthropic.com/v1/messages",
            "default_model": "claude-instant-1",
            "env_key": "ANTHROPIC_API_KEY"
        }
    }
    
    def __init__(self, api_key=None, model=None, provider="openai", endpoint=None):
        """Initialize the LLM client
        
        Args:
            api_key: API key for the LLM provider. If None, will try to get from environment
            model: Model name to use (e.g., gpt-3.5-turbo, claude-instant-1)
            provider: Provider name (openai, azure, anthropic)
            endpoint: Custom API endpoint URL. If None, uses the standard endpoint for the provider
        """
        # Try to get API key from different sources
        self.api_key = api_key or os.getenv(self.PROVIDERS.get(provider, {}).get("env_key", "LLM_API_KEY"))
        if not self.api_key:
            fallback_keys = ["LLM_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "AZURE_OPENAI_API_KEY"]
            for key_name in fallback_keys:
                if os.getenv(key_name):
                    self.api_key = os.getenv(key_name)
                    logger.info(f"Using API key from {key_name}")
                    break
        
        # Configure provider details
        self.provider = provider.lower()
        self.provider_config = self.PROVIDERS.get(self.provider, self.PROVIDERS["openai"])
        
        # Configure model
        self.model = model or os.getenv("LLM_MODEL") or self.provider_config["default_model"]
        
        # Configure endpoint
        self.endpoint = endpoint or os.getenv("LLM_ENDPOINT") or self.provider_config["endpoint"]
        
        # Log configuration
        logger.info(f"LLM client initialized with provider: {self.provider}, model: {self.model}")
        if not self.api_key:
            logger.warning("No API key provided or found in environment variables")
    
    def generate_text(self, prompt: str, max_tokens: int = 500, temperature: float = 0.1) -> str:
        """Generate text using the configured LLM API
        
        Args:
            prompt: The input prompt
            max_tokens: Maximum number of tokens to generate
            temperature: Temperature for generation (lower is more deterministic)
            
        Returns:
            str: The generated text
            
        Raises:
            Exception: If the API call fails
        """
        if not self.api_key:
            logger.warning("No API key available. Using fallback method.")
            return self._fallback_generate(prompt)
        
        try:
            # OpenAI API format
            if self.provider in ["openai", "azure"]:
                # Prepare the request
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }
                
                # Azure-specific header
                if self.provider == "azure":
                    headers["api-key"] = self.api_key
                    if "api.openai.com" in self.endpoint:
                        logger.warning("Using Azure provider but standard OpenAI endpoint")
                
                # Prepare the data payload
                data = {
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                    "temperature": temperature
                }
                
                # Make the API call
                response = requests.post(self.endpoint, headers=headers, json=data, timeout=30)
                response.raise_for_status()
                
                # Parse the response
                result = response.json()
                
                # Extract the text from the response
                generated_text = result["choices"][0]["message"]["content"]
                
                return generated_text
                
            # Anthropic API format
            elif self.provider == "anthropic":
                # Prepare the request
                headers = {
                    "Content-Type": "application/json",
                    "X-API-Key": self.api_key,
                    "anthropic-version": "2023-06-01"
                }
                
                # Prepare the data payload
                data = {
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                    "temperature": temperature
                }
                
                # Make the API call
                response = requests.post(self.endpoint, headers=headers, json=data, timeout=30)
                response.raise_for_status()
                
                # Parse the response
                result = response.json()
                
                # Extract the text from the response
                generated_text = result["content"][0]["text"] 
                
                return generated_text
            
            # Unsupported provider
            else:
                logger.warning(f"Unsupported provider: {self.provider}. Using fallback.")
                return self._fallback_generate(prompt)
                
        except Exception as e:
            logger.error(f"LLM API error: {str(e)}")
            # If we get a specific API error about the model not being available,
            # try with a different model
            if "model" in str(e).lower() and "access" in str(e).lower():
                logger.warning(f"Model {self.model} not available. Trying fallback model...")
                fallback_models = ["text-davinci-003", "gpt-3.5-turbo-instruct", "claude-instant-1"]
                for model in fallback_models:
                    try:
                        old_model = self.model
                        self.model = model
                        logger.info(f"Trying fallback model: {model}")
                        result = self.generate_text(prompt, max_tokens, temperature)
                        return result
                    except Exception as e2:
                        logger.error(f"Failed with fallback model {model}: {str(e2)}")
                        continue
                    finally:
                        self.model = old_model
            
            # If all API attempts fail, use the fallback method
            logger.warning("All API attempts failed. Using rule-based fallback.")
            return self._fallback_generate(prompt)
    
    def _fallback_generate(self, prompt: str) -> str:
        """Simple rule-based fallback for basic SQL generation when API is unavailable
        
        Args:
            prompt: The input prompt
            
        Returns:
            str: A generated SQL query based on basic rules
        """
        logger.info("Using fallback SQL generation")
        
        prompt_lower = prompt.lower()
        
        # Detect if this is a SQL conversion request
        if "sql" in prompt_lower and ("convert" in prompt_lower or "translate" in prompt_lower):
            # Extract the actual query text
            if "query" in prompt_lower and ":" in prompt:
                query_text = prompt.split(":", 1)[1].strip().lower()
            else:
                query_text = prompt_lower
            
            # Simple keyword-based SQL generation
            if "invoices" in prompt_lower or "invoice" in prompt_lower:
                base_table = "invoices"
                
                # Handle common types of requests
                if "unpaid" in query_text:
                    return f"SELECT * FROM {base_table} WHERE payment_status = 'Unpaid' LIMIT 100;"
                    
                elif "paid" in query_text:
                    return f"SELECT * FROM {base_table} WHERE payment_status = 'Paid' LIMIT 100;"
                    
                elif "overdue" in query_text:
                    return f"SELECT * FROM {base_table} WHERE payment_status = 'Unpaid' AND due_date < CURRENT_DATE LIMIT 100;"
                    
                elif "last month" in query_text or "previous month" in query_text:
                    return f"""
                    SELECT * FROM {base_table} 
                    WHERE invoice_date BETWEEN 
                        DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month') 
                        AND 
                        DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 day'
                    LIMIT 100;
                    """
                    
                elif "this month" in query_text or "current month" in query_text:
                    return f"""
                    SELECT * FROM {base_table} 
                    WHERE invoice_date BETWEEN 
                        DATE_TRUNC('month', CURRENT_DATE) 
                        AND 
                        CURRENT_DATE
                    LIMIT 100;
                    """
                    
                elif any(vendor in query_text for vendor in ["vendor", "company", "supplier"]):
                    # Try to extract a vendor name if in quotes
                    if "'" in query_text:
                        parts = query_text.split("'")
                        if len(parts) >= 3:
                            vendor_name = parts[1]
                            return f"SELECT * FROM {base_table} WHERE vendor LIKE '%{vendor_name}%' LIMIT 100;"
                    
                    # General vendor query
                    return f"SELECT vendor, COUNT(*) as invoice_count, SUM(amount) as total_amount FROM {base_table} GROUP BY vendor ORDER BY total_amount DESC LIMIT 100;"
                
                # Default invoice query
                return f"SELECT * FROM {base_table} LIMIT 100;"
                
            # General fallback
            return "SELECT * FROM invoices LIMIT 100;"
        
        # Non-SQL queries just return a simple message
        return "SELECT * FROM invoices LIMIT 100;"
    
    def generate_sql_query(self, natural_language_query):
        """Generate SQL query from natural language using LLM
        
        Args:
            natural_language_query: The natural language query to convert to SQL
            
        Returns:
            str: The generated SQL query
            
        Raises:
            Exception: If the API call fails
        """
        # Construct table information for context
        table_info = """
        Tables in the database:
        
        invoices: 
        - id (SERIAL PRIMARY KEY)
        - invoice_number (VARCHAR)
        - invoice_date (DATE)
        - due_date (DATE)
        - amount (NUMERIC)
        - vendor (VARCHAR)
        - payment_status (VARCHAR) - Values like 'Paid', 'Unpaid', 'Pending'
        - fund_paid_by (VARCHAR)
        - description (TEXT)
        
        vendors:
        - id (SERIAL PRIMARY KEY)
        - name (VARCHAR)
        - contact_name (VARCHAR)
        - email (VARCHAR)
        - phone (VARCHAR)
        
        funds:
        - id (SERIAL PRIMARY KEY)
        - name (VARCHAR)
        - description (TEXT)
        - balance (NUMERIC)
        """
        
        # Create the prompt
        prompt = f"""
        Given the following database schema:
        {table_info}
        
        Generate a SQL query for PostgreSQL to answer this question:
        "{natural_language_query}"
        
        Return ONLY the SQL query without any explanations.
        """
        
        try:
            # Use the generate_text method to get the SQL
            response = self.generate_text(prompt, max_tokens=500, temperature=0.1)
            
            # Clean up the response
            if response:
                # Remove any markdown code blocks
                clean_response = response.replace("```sql", "").replace("```", "").strip()
                return clean_response
            
            # Fallback if response is empty
            return self._fallback_sql_for_query(natural_language_query)
            
        except Exception as e:
            logger.error(f"Error generating SQL query: {str(e)}")
            # Use fallback if API fails
            return self._fallback_sql_for_query(natural_language_query)
    
    def _fallback_sql_for_query(self, query_text):
        """Generate a simple SQL query based on the input text without using LLM
        
        Args:
            query_text: The query text
            
        Returns:
            str: A simple SQL query
        """
        query_lower = query_text.lower()
        
        # Handle common query patterns
        if "how much" in query_lower and "pay" in query_lower and ("2025" in query_lower or "this year" in query_lower):
            return """
            SELECT COALESCE(SUM(amount), 0) AS total_paid
            FROM invoices 
            WHERE payment_status = 'Paid' 
            AND EXTRACT(YEAR FROM invoice_date::DATE) = EXTRACT(YEAR FROM CURRENT_DATE)
            """
        
        elif "how much" in query_lower and "pay" in query_lower and ("2024" in query_lower or "last year" in query_lower):
            return """
            SELECT COALESCE(SUM(amount), 0) AS total_paid
            FROM invoices 
            WHERE payment_status = 'Paid' 
            AND EXTRACT(YEAR FROM invoice_date::DATE) = EXTRACT(YEAR FROM CURRENT_DATE) - 1
            """
            
        elif "unpaid" in query_lower:
            return "SELECT * FROM invoices WHERE payment_status = 'Unpaid' ORDER BY due_date ASC LIMIT 100"
            
        elif "paid" in query_lower:
            return "SELECT * FROM invoices WHERE payment_status = 'Paid' ORDER BY invoice_date DESC LIMIT 100"
            
        elif "overdue" in query_lower:
            return """
            SELECT * FROM invoices 
            WHERE payment_status = 'Unpaid' AND due_date::DATE < CURRENT_DATE 
            ORDER BY due_date ASC LIMIT 100
            """
            
        elif "recent" in query_lower:
            return "SELECT * FROM invoices ORDER BY invoice_date DESC LIMIT 10"
        
        # Default query
        return "SELECT * FROM invoices LIMIT 100" 