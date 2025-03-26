"""
Custom Elasticsearch handler for direct logging to Elasticsearch.

This handler allows direct communication with Elasticsearch without requiring Logstash as an intermediary,
providing redundancy in case Logstash is unavailable or overloaded.
"""

import logging
import socket
import datetime
import json
import threading
import uuid
import os
import platform
import sys
from elasticsearch import Elasticsearch, helpers
from elasticsearch.exceptions import ConnectionError, ConnectionTimeout, TransportError

class ElasticsearchHandler(logging.Handler):
    """
    Elasticsearch log handler that sends log records directly to Elasticsearch.
    
    This handler provides a redundant path for logs to reach Elasticsearch, bypassing
    Logstash when needed. It includes batch processing with error handling and retry logic.
    """
    
    def __init__(self, hosts, index_name=None, auth_type=None, api_key=None, 
                username=None, password=None, es_additional_fields=None,
                buffer_size=100, flush_interval=5.0, es_retry_count=3):
        """
        Initialize the Elasticsearch handler.
        
        Args:
            hosts: List of Elasticsearch hosts or host strings
            index_name: Name of the index to write to (defaults to app_name-logs-YYYY.MM.DD)
            auth_type: Authentication type (api_key, basic, or None)
            api_key: API key for authentication if auth_type is 'api_key'
            username: Username for basic auth if auth_type is 'basic'
            password: Password for basic auth if auth_type is 'basic'
            es_additional_fields: Additional fields to include in all logs
            buffer_size: Number of records to buffer before bulk insert
            flush_interval: Maximum time between flushes in seconds
            es_retry_count: Number of retries for Elasticsearch operations
        """
        super().__init__()
        
        # Set up basic handler properties
        self.hosts = hosts if isinstance(hosts, list) else [hosts]
        self.index_name_pattern = index_name or "logs-{app_name}-{date}"
        self.auth_type = auth_type
        self.api_key = api_key
        self.username = username
        self.password = password
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval
        self.retry_count = es_retry_count
        
        # Add standard fields
        self.es_additional_fields = es_additional_fields or {}
        if 'host' not in self.es_additional_fields:
            self.es_additional_fields['host'] = socket.gethostname()
        if 'environment' not in self.es_additional_fields:
            self.es_additional_fields['environment'] = os.environ.get('ENVIRONMENT', 'development')
        if 'app_name' not in self.es_additional_fields:
            self.es_additional_fields['app_name'] = os.environ.get('APP_NAME', 'finance_assistant')
            
        # Set up client
        self.client = None
        self._connect()
        
        # Set up buffer
        self.buffer = []
        self.buffer_lock = threading.RLock()
        self.last_flush = datetime.datetime.now()
        
        # Start background thread for periodic flushing
        self._timer = None
        self._schedule_flush()
    
    def _connect(self):
        """Create the Elasticsearch client connection with appropriate authentication."""
        # Set up authentication
        auth_params = {}
        if self.auth_type == 'api_key' and self.api_key:
            auth_params['api_key'] = self.api_key
        elif self.auth_type == 'basic' and self.username and self.password:
            auth_params['basic_auth'] = (self.username, self.password)
        
        # Add SSL settings for secured connections
        if any(host.startswith('https://') for host in self.hosts):
            auth_params['verify_certs'] = True
        
        # Create the client
        try:
            self.client = Elasticsearch(hosts=self.hosts, **auth_params)
        except Exception as e:
            # Don't fail initialization if connection fails - we'll retry later
            self.client = None
            print(f"Error connecting to Elasticsearch: {str(e)}")
    
    def _get_index_name(self):
        """Get the actual index name based on the pattern."""
        app_name = self.es_additional_fields.get('app_name', 'logs')
        date_str = datetime.datetime.now().strftime('%Y.%m.%d')
        
        # If using a daily index pattern
        return self.index_name_pattern.format(
            app_name=app_name,
            date=date_str,
            env=self.es_additional_fields.get('environment', 'development')
        )
    
    def _schedule_flush(self):
        """Schedule the next flush operation."""
        # Cancel any existing timer
        if self._timer:
            self._timer.cancel()
        
        # Create a new timer for periodic flushing
        self._timer = threading.Timer(self.flush_interval, self.flush_buffer)
        self._timer.daemon = True
        self._timer.start()
    
    def emit(self, record):
        """Process a log record for sending to Elasticsearch."""
        try:
            # Format the record
            document = self.format_document(record)
            
            # Add to buffer
            with self.buffer_lock:
                self.buffer.append(document)
            
            # Check if we need to flush the buffer
            if len(self.buffer) >= self.buffer_size:
                self.flush_buffer()
            elif (datetime.datetime.now() - self.last_flush).total_seconds() >= self.flush_interval:
                # It's also time for a scheduled flush
                self.flush_buffer()
                
        except Exception as e:
            # Don't crash on logging failures
            print(f"Error in Elasticsearch log handler: {str(e)}")
    
    def format_document(self, record):
        """Format a log record into an Elasticsearch document."""
        # Get basic document with timestamp
        document = {
            '_index': self._get_index_name(),
            '_id': str(uuid.uuid4()),  # Generate a unique ID
            '@timestamp': datetime.datetime.utcfromtimestamp(record.created).isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': self.format(record),
        }
        
        # Add exception info if present
        if record.exc_info:
            document['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else '',
                'message': str(record.exc_info[1]) if record.exc_info[1] else '',
                'traceback': self.formatException(record.exc_info) if record.exc_info else ''
            }
        
        # Add source location
        document['source'] = {
            'file': record.pathname,
            'line': record.lineno,
            'function': record.funcName
        }
        
        # Add process info
        document['process'] = {
            'pid': record.process,
            'name': record.processName,
            'thread_id': record.thread,
            'thread_name': record.threadName
        }
        
        # Add host and platform info
        document['host'] = {
            'name': socket.gethostname(),
            'platform': platform.platform(),
            'python': platform.python_version()
        }
        
        # Add additional standard fields
        for key, value in self.es_additional_fields.items():
            if key not in document:
                document[key] = value
        
        # Add all extra attributes from the record
        for key, value in record.__dict__.items():
            # Skip standard LogRecord attributes and already included fields
            if (key not in document and 
                not key.startswith('_') and
                key not in ('args', 'asctime', 'created', 'exc_info', 'exc_text', 
                          'filename', 'funcName', 'id', 'levelname', 'levelno', 
                          'lineno', 'module', 'msecs', 'message', 'msg', 'name', 
                          'pathname', 'process', 'processName', 'relativeCreated', 
                          'thread', 'threadName')):
                try:
                    # Try to include the field as is
                    document[key] = value
                except (TypeError, OverflowError):
                    # Convert to string if not serializable
                    document[key] = str(value)
                    
        return document
    
    def flush_buffer(self):
        """Flush the buffer by sending all documents to Elasticsearch."""
        if not self.buffer:
            # Nothing to flush
            self._schedule_flush()
            return
            
        # Get documents to send
        with self.buffer_lock:
            documents = self.buffer.copy()
            self.buffer = []
            self.last_flush = datetime.datetime.now()
        
        # Check if we have a client
        if not self.client:
            # Try to reconnect
            self._connect()
            if not self.client:
                # Still no client, put documents back in buffer
                with self.buffer_lock:
                    self.buffer = documents + self.buffer
                self._schedule_flush()
                return
        
        # Try to send to Elasticsearch
        try:
            if documents:
                # Set up index template if needed
                self._ensure_index_template()
                
                # Use helpers.bulk for more efficient indexing
                response = helpers.bulk(
                    self.client,
                    documents,
                    chunk_size=min(len(documents), 500),  # Use reasonable chunk size
                    max_retries=self.retry_count,
                    initial_backoff=0.2,  # Start with a small backoff
                    max_backoff=60.0     # But allow up to 60s for retries
                )
                
                # Log success if this isn't a direct log (prevent infinite recursion)
                if len(documents) > 10:
                    print(f"Successfully sent {len(documents)} logs to Elasticsearch")
                    
        except (ConnectionError, ConnectionTimeout) as e:
            # Connection issues - try to reconnect
            print(f"Elasticsearch connection error: {str(e)}")
            self._connect()
            
            # Put documents back in buffer for retry
            with self.buffer_lock:
                self.buffer = documents + self.buffer
        except Exception as e:
            # Other errors - print but don't retry to avoid infinite issues
            print(f"Error sending logs to Elasticsearch: {str(e)}")
        
        # Schedule the next flush
        self._schedule_flush()
    
    def _ensure_index_template(self):
        """Ensure the index template exists for proper mapping of log fields."""
        try:
            # Only create template if it doesn't exist already
            template_name = "finance_assistant_logs_template"
            if not self.client.indices.exists_index_template(name=template_name):
                # Define a template for proper field mapping
                template = {
                    "index_patterns": ["logs-*"],
                    "template": {
                        "settings": {
                            "number_of_shards": 1,
                            "number_of_replicas": 1,
                            "refresh_interval": "5s"
                        },
                        "mappings": {
                            "properties": {
                                "@timestamp": {"type": "date"},
                                "message": {"type": "text"},
                                "level": {"type": "keyword"},
                                "logger": {"type": "keyword"},
                                "environment": {"type": "keyword"},
                                "app_name": {"type": "keyword"},
                                "correlation_id": {"type": "keyword"},
                                "exception": {
                                    "properties": {
                                        "type": {"type": "keyword"},
                                        "message": {"type": "text"},
                                        "traceback": {"type": "text"}
                                    }
                                },
                                "source": {
                                    "properties": {
                                        "file": {"type": "keyword"},
                                        "line": {"type": "integer"},
                                        "function": {"type": "keyword"}
                                    }
                                },
                                "host": {
                                    "properties": {
                                        "name": {"type": "keyword"},
                                        "platform": {"type": "keyword"},
                                        "python": {"type": "keyword"}
                                    }
                                },
                                "process": {
                                    "properties": {
                                        "pid": {"type": "long"},
                                        "name": {"type": "keyword"},
                                        "thread_id": {"type": "long"},
                                        "thread_name": {"type": "keyword"}
                                    }
                                },
                                "context": {"type": "object", "dynamic": True}
                            }
                        }
                    }
                }
                
                # Create the template
                self.client.indices.put_index_template(name=template_name, body=template)
        except Exception as e:
            # Don't fail if template creation fails
            print(f"Could not create Elasticsearch index template: {str(e)}")
    
    def close(self):
        """Close the handler, flushing any remaining logs."""
        try:
            # Cancel the timer
            if self._timer:
                self._timer.cancel()
                self._timer = None
            
            # Final flush
            self.flush_buffer()
            
            # Close the client
            if self.client:
                self.client.close()
                self.client = None
        except Exception as e:
            print(f"Error closing Elasticsearch handler: {str(e)}")
        finally:
            super().close()

class BufferedElasticsearchHandler(ElasticsearchHandler):
    """
    Extended handler with improved buffering for high-volume logging scenarios.
    
    This version includes a more robust buffer with disk-based persistence for
    reliability in case of application crashes or restarts.
    """
    
    def __init__(self, *args, backup_file=None, **kwargs):
        """
        Initialize with additional buffer persistence options.
        
        Args:
            backup_file: File path to use for buffer persistence
            *args, **kwargs: Same as ElasticsearchHandler
        """
        # Configure backup file
        self.backup_file = backup_file or os.path.join(
            os.environ.get('LOG_DIR', 'logs'),
            'elasticsearch_buffer.json'
        )
        
        # Make sure the directory exists
        os.makedirs(os.path.dirname(self.backup_file), exist_ok=True)
        
        # Call parent constructor
        super().__init__(*args, **kwargs)
        
        # Restore any buffered logs from previous runs
        self._restore_buffer()
    
    def _restore_buffer(self):
        """Restore buffered logs from disk if available."""
        try:
            if os.path.exists(self.backup_file):
                with open(self.backup_file, 'r') as f:
                    saved_buffer = json.load(f)
                    
                # Add to current buffer
                with self.buffer_lock:
                    self.buffer.extend(saved_buffer)
                    
                # Log restoration
                count = len(saved_buffer)
                if count > 0:
                    print(f"Restored {count} buffered logs from {self.backup_file}")
                    
                # Delete the file after successful restore
                os.unlink(self.backup_file)
        except Exception as e:
            print(f"Could not restore buffered logs: {str(e)}")
    
    def _save_buffer(self):
        """Save buffer to disk for persistence."""
        try:
            if self.buffer:
                with open(self.backup_file, 'w') as f:
                    json.dump(self.buffer, f)
        except Exception as e:
            print(f"Could not save buffer to disk: {str(e)}")
    
    def flush_buffer(self):
        """Override to add persistence in case of failures."""
        try:
            super().flush_buffer()
        except Exception as e:
            print(f"Failed to flush buffer, saving to disk: {str(e)}")
            self._save_buffer()
    
    def emit(self, record):
        """Override to add additional error handling."""
        super().emit(record)
        
        # Save buffer periodically if it's getting large
        if len(self.buffer) > self.buffer_size * 2:
            self._save_buffer()
    
    def close(self):
        """Override to ensure buffer is saved before closing."""
        # Save any remaining logs
        if self.buffer:
            self._save_buffer()
            
        # Call parent to finish normal closing
        super().close() 