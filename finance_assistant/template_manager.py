import sqlite3
import json
import numpy as np
import os
from datetime import datetime
import logging
from typing import Dict, List, Optional, Tuple, Any

# Set up logger
logger = logging.getLogger("template_manager")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler("template_manager.log")
    fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(fh)

try:
    # Try to import sentence-transformers for embeddings
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    logger.warning("sentence-transformers not found. Install with: pip install sentence-transformers")
    logger.warning("Falling back to keyword-based matching.")
    EMBEDDINGS_AVAILABLE = False

class ParameterExtractor:
    """Extracts parameters from natural language queries"""
    
    def __init__(self, param_name: str, patterns: List[str]):
        self.param_name = param_name
        self.patterns = patterns
        
    def extract(self, query: str) -> Optional[str]:
        """Extract parameter value from query text"""
        import re
        
        for pattern in self.patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match and match.groups():
                return match.group(1).strip()
        
        return None

class QueryTemplate:
    """Template for matching and executing natural language queries"""
    
    def __init__(self, id: int, nl_pattern: str, query_pattern: str, 
                 parameter_extractors: Dict[str, ParameterExtractor] = None,
                 embedding: List[float] = None, 
                 success_count: int = 0, failure_count: int = 0,
                 query_type: str = "general"):
        self.id = id
        self.nl_pattern = nl_pattern
        self.query_pattern = query_pattern
        self.parameter_extractors = parameter_extractors or {}
        self.embedding = embedding
        self.success_count = success_count
        self.failure_count = failure_count
        self.query_type = query_type
        self.last_used = datetime.now()
        
    def apply(self, user_question: str, default_params: Dict[str, Any] = None) -> Tuple[str, Dict[str, Any]]:
        """Apply this template to a user question, returning the query and extracted parameters"""
        params = default_params or {}
        
        # Extract parameters from the question
        for param_name, extractor in self.parameter_extractors.items():
            extracted_value = extractor.extract(user_question)
            if extracted_value:
                params[param_name] = extracted_value
            
        # Build the final query by filling in the template
        try:
            final_query = self.query_pattern.format(**params)
            return final_query, params
        except KeyError as e:
            logger.warning(f"Missing parameter in template {self.id}: {str(e)}")
            return None, params
        
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'nl_pattern': self.nl_pattern,
            'query_pattern': self.query_pattern,
            'parameter_extractors': {
                name: {'param_name': extractor.param_name, 'patterns': extractor.patterns}
                for name, extractor in self.parameter_extractors.items()
            },
            'embedding': self.embedding.tolist() if isinstance(self.embedding, np.ndarray) else self.embedding,
            'success_count': self.success_count,
            'failure_count': self.failure_count,
            'query_type': self.query_type
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'QueryTemplate':
        """Create from dictionary"""
        # Create parameter extractors
        extractors = {}
        for name, extractor_data in data.get('parameter_extractors', {}).items():
            extractors[name] = ParameterExtractor(
                extractor_data['param_name'],
                extractor_data['patterns']
            )
            
        # Convert embedding if needed
        embedding = data.get('embedding')
        if embedding and isinstance(embedding, list):
            embedding = np.array(embedding)
            
        return cls(
            id=data['id'],
            nl_pattern=data['nl_pattern'],
            query_pattern=data['query_pattern'],
            parameter_extractors=extractors,
            embedding=embedding,
            success_count=data.get('success_count', 0),
            failure_count=data.get('failure_count', 0),
            query_type=data.get('query_type', 'general')
        )

class TemplateManager:
    """Manages query templates with semantic matching capabilities"""
    
    def __init__(self, db_path: str = "query_templates.db"):
        self.db_path = db_path
        self._init_db()
        self.templates = self._load_templates()
        
        # Initialize embedding model if available
        self.embedding_model = None
        if EMBEDDINGS_AVAILABLE:
            try:
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')  # Small, efficient model
                logger.info("Loaded embedding model for semantic matching")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {str(e)}")
        
    def _init_db(self):
        """Initialize the template database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create templates table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS query_templates (
                id INTEGER PRIMARY KEY,
                nl_pattern TEXT NOT NULL,
                query_pattern TEXT NOT NULL,
                parameter_extractors TEXT,
                embedding TEXT,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                query_type TEXT DEFAULT 'general',
                last_used TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create template variants table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS template_variants (
                id INTEGER PRIMARY KEY,
                parent_template_id INTEGER,
                nl_pattern TEXT NOT NULL,
                query_pattern TEXT NOT NULL,
                parameter_extractors TEXT,
                embedding TEXT,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_template_id) REFERENCES query_templates (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_templates(self) -> List[QueryTemplate]:
        """Load all templates from the database"""
        templates = []
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM query_templates')
        rows = cursor.fetchall()
        
        for row in cursor.description:
            print(row[0])
        
        for row in rows:
            try:
                template_data = {
                    'id': row[0],
                    'nl_pattern': row[1],
                    'query_pattern': row[2],
                    'parameter_extractors': json.loads(row[3]) if row[3] else {},
                    'embedding': json.loads(row[4]) if row[4] else None,
                    'success_count': row[5],
                    'failure_count': row[6],
                    'query_type': row[7]
                }
                templates.append(QueryTemplate.from_dict(template_data))
            except Exception as e:
                logger.error(f"Error loading template {row[0]}: {str(e)}")
        
        conn.close()
        logger.info(f"Loaded {len(templates)} templates from database")
        return templates
    
    def add_template(self, nl_pattern: str, query_pattern: str, 
                    parameter_extractors: Dict[str, ParameterExtractor] = None,
                    query_type: str = "general") -> int:
        """Add a new template to the library"""
        # Generate embedding if model is available
        embedding = None
        if self.embedding_model:
            try:
                embedding = self.embedding_model.encode(nl_pattern).tolist()
            except Exception as e:
                logger.error(f"Error generating embedding: {str(e)}")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Serialize parameter extractors
        param_extractors_json = json.dumps({
            name: {'param_name': extractor.param_name, 'patterns': extractor.patterns}
            for name, extractor in (parameter_extractors or {}).items()
        }) if parameter_extractors else None
        
        # Serialize embedding
        embedding_json = json.dumps(embedding) if embedding else None
        
        cursor.execute('''
            INSERT INTO query_templates 
            (nl_pattern, query_pattern, parameter_extractors, embedding, query_type, last_used)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            nl_pattern, 
            query_pattern, 
            param_extractors_json,
            embedding_json,
            query_type,
            datetime.now().isoformat()
        ))
        
        template_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Create and add template to in-memory list
        template = QueryTemplate(
            id=template_id,
            nl_pattern=nl_pattern,
            query_pattern=query_pattern,
            parameter_extractors=parameter_extractors,
            embedding=embedding,
            query_type=query_type
        )
        
        self.templates.append(template)
        logger.info(f"Added new template with ID {template_id}")
        
        return template_id
    
    def add_template_variant(self, parent_id: int, nl_pattern: str, query_pattern: str,
                            parameter_extractors: Dict[str, ParameterExtractor] = None) -> int:
        """Add a variant of an existing template"""
        # Generate embedding if model is available
        embedding = None
        if self.embedding_model:
            try:
                embedding = self.embedding_model.encode(nl_pattern).tolist()
            except Exception as e:
                logger.error(f"Error generating embedding: {str(e)}")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Serialize parameter extractors
        param_extractors_json = json.dumps({
            name: {'param_name': extractor.param_name, 'patterns': extractor.patterns}
            for name, extractor in (parameter_extractors or {}).items()
        }) if parameter_extractors else None
        
        # Serialize embedding
        embedding_json = json.dumps(embedding) if embedding else None
        
        cursor.execute('''
            INSERT INTO template_variants 
            (parent_template_id, nl_pattern, query_pattern, parameter_extractors, embedding)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            parent_id,
            nl_pattern, 
            query_pattern, 
            param_extractors_json,
            embedding_json
        ))
        
        variant_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"Added template variant {variant_id} for parent {parent_id}")
        return variant_id
    
    def find_matching_template(self, user_question: str, 
                              similarity_threshold: float = 0.70) -> Optional[QueryTemplate]:
        """Find the template that best matches the user's question"""
        if not self.templates:
            logger.warning("No templates available for matching")
            return None
            
        # Use embeddings for semantic matching if available
        if self.embedding_model and EMBEDDINGS_AVAILABLE:
            try:
                # Generate embedding for user question
                question_embedding = self.embedding_model.encode(user_question)
                
                # Find closest match
                best_match = None
                highest_similarity = similarity_threshold
                
                for template in self.templates:
                    # Skip templates without embeddings
                    if template.embedding is None:
                        continue
                        
                    # Convert to numpy array if needed
                    template_embedding = template.embedding
                    if isinstance(template_embedding, list):
                        template_embedding = np.array(template_embedding)
                    
                    # Calculate cosine similarity
                    similarity = self._cosine_similarity(question_embedding, template_embedding)
                    
                    if similarity > highest_similarity:
                        highest_similarity = similarity
                        best_match = template
                
                if best_match:
                    logger.info(f"Found semantic match with similarity {highest_similarity:.4f}")
                    return best_match
                    
            except Exception as e:
                logger.error(f"Error in semantic matching: {str(e)}")
                # Fall back to keyword matching
        
        # Fallback: keyword matching
        return self._keyword_matching(user_question)
    
    def _keyword_matching(self, user_question: str) -> Optional[QueryTemplate]:
        """Simple keyword-based matching as a fallback"""
        from collections import Counter
        import re
        
        # Tokenize user question
        user_tokens = set(re.findall(r'\b\w+\b', user_question.lower()))
        
        best_match = None
        highest_score = 0
        
        for template in self.templates:
            # Tokenize template pattern
            template_tokens = set(re.findall(r'\b\w+\b', template.nl_pattern.lower()))
            
            # Calculate overlap
            common_tokens = user_tokens.intersection(template_tokens)
            if not common_tokens:
                continue
                
            # Score based on number of matching tokens and their significance
            score = len(common_tokens) / max(len(user_tokens), len(template_tokens))
            
            if score > highest_score:
                highest_score = score
                best_match = template
        
        if best_match and highest_score > 0.4:  # Threshold for keyword matching
            logger.info(f"Found keyword match with score {highest_score:.4f}")
            return best_match
            
        return None
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    
    def increment_success(self, template_id: int):
        """Increment success count for a template"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE query_templates
            SET success_count = success_count + 1, last_used = ?
            WHERE id = ?
        ''', (datetime.now().isoformat(), template_id))
        
        conn.commit()
        conn.close()
        
        # Update in-memory template
        for template in self.templates:
            if template.id == template_id:
                template.success_count += 1
                template.last_used = datetime.now()
                break
    
    def increment_failure(self, template_id: int):
        """Increment failure count for a template"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE query_templates
            SET failure_count = failure_count + 1, last_used = ?
            WHERE id = ?
        ''', (datetime.now().isoformat(), template_id))
        
        conn.commit()
        conn.close()
        
        # Update in-memory template
        for template in self.templates:
            if template.id == template_id:
                template.failure_count += 1
                template.last_used = datetime.now()
                break
    
    def calculate_template_confidence(self, template: QueryTemplate, user_question: str) -> float:
        """Calculate confidence score for applying this template to the question"""
        # Calculate semantic similarity
        similarity_score = 0.5  # Default moderate similarity
        
        if self.embedding_model and template.embedding is not None:
            try:
                # Get question embedding
                question_embedding = self.embedding_model.encode(user_question)
                
                # Get template embedding
                template_embedding = template.embedding
                if isinstance(template_embedding, list):
                    template_embedding = np.array(template_embedding)
                
                # Calculate similarity
                similarity_score = self._cosine_similarity(question_embedding, template_embedding)
            except Exception as e:
                logger.error(f"Error calculating semantic similarity: {str(e)}")
        
        # Calculate historical success rate
        total_usage = template.success_count + template.failure_count
        historical_success = 0.5  # Default to neutral
        if total_usage > 0:
            historical_success = template.success_count / total_usage
        
        # Calculate parameter extraction confidence
        param_confidence = 0.0
        param_count = len(template.parameter_extractors)
        if param_count > 0:
            extracted_params = 0
            for extractor in template.parameter_extractors.values():
                if extractor.extract(user_question) is not None:
                    extracted_params += 1
            
            param_confidence = extracted_params / param_count
        else:
            # No parameters to extract is actually good
            param_confidence = 1.0
        
        # Combine factors with weighting
        confidence = (
            similarity_score * 0.5 + 
            historical_success * 0.3 + 
            param_confidence * 0.2
        )
        
        return min(1.0, max(0.0, confidence))  # Ensure result is between 0 and 1
    
    def import_defaults(self):
        """Import default templates to get started"""
        # Basic templates to handle common queries
        defaults = [
            {
                "nl_pattern": "Show all invoices",
                "query_pattern": "access_db.get_invoice_data()",
                "query_type": "list_all"
            },
            {
                "nl_pattern": "What is the total amount of all invoices",
                "query_pattern": "access_db.get_invoice_totals()",
                "query_type": "aggregate"
            },
            {
                "nl_pattern": "Show all vendors",
                "query_pattern": "access_db.get_vendor_data()",
                "query_type": "list_all"
            },
            {
                "nl_pattern": "How many invoices do we have",
                "query_pattern": "access_db.get_invoice_totals()",
                "query_type": "count"
            }
        ]
        
        for template in defaults:
            # Check if similar template already exists
            exists = False
            for existing in self.templates:
                if existing.nl_pattern.lower() == template["nl_pattern"].lower():
                    exists = True
                    break
            
            if not exists:
                self.add_template(
                    nl_pattern=template["nl_pattern"],
                    query_pattern=template["query_pattern"],
                    query_type=template["query_type"]
                )
        
        logger.info(f"Imported default templates")
    
    def export_templates(self, file_path: str):
        """Export templates to a JSON file for backup"""
        templates_data = [t.to_dict() for t in self.templates]
        
        with open(file_path, 'w') as f:
            json.dump(templates_data, f, indent=2)
            
        logger.info(f"Exported {len(templates_data)} templates to {file_path}")
    
    def import_templates(self, file_path: str):
        """Import templates from a JSON file"""
        with open(file_path, 'r') as f:
            templates_data = json.load(f)
            
        imported_count = 0
        for template_data in templates_data:
            # Skip if ID exists
            if any(t.id == template_data['id'] for t in self.templates):
                continue
                
            # Create template object
            template = QueryTemplate.from_dict(template_data)
            
            # Add to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Serialize parameter extractors
            param_extractors_json = json.dumps({
                name: {'param_name': extractor.param_name, 'patterns': extractor.patterns}
                for name, extractor in template.parameter_extractors.items()
            }) if template.parameter_extractors else None
            
            # Serialize embedding
            embedding_json = json.dumps(template.embedding.tolist() if isinstance(template.embedding, np.ndarray) 
                                     else template.embedding) if template.embedding is not None else None
            
            cursor.execute('''
                INSERT INTO query_templates 
                (id, nl_pattern, query_pattern, parameter_extractors, embedding, 
                 success_count, failure_count, query_type, last_used)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                template.id,
                template.nl_pattern, 
                template.query_pattern, 
                param_extractors_json,
                embedding_json,
                template.success_count,
                template.failure_count,
                template.query_type,
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            # Add to in-memory list
            self.templates.append(template)
            imported_count += 1
            
        logger.info(f"Imported {imported_count} templates from {file_path}")
        return imported_count 