from appwrite.client import Client
from appwrite.services.databases import Databases
from appwrite.query import Query
from datetime import datetime
import json
import sqlite3
import logging
import os
from dotenv import load_dotenv
from typing import Dict, Any, Set, Tuple, Optional, List

class AppwriteDataWriter:
    def __init__(self, log_level: str = "INFO"):
        load_dotenv()
        
        # Configure logger with proper formatting and handlers
        self._setup_logging(log_level)
        
        # Initialize Appwrite client
        self._init_appwrite_client()
        
        # Database configuration
        self.database_id = "Jaguar"
        self.collection_id = "mission_results"
        
        self.logger.info("AppwriteDataWriter initialized successfully")
        
        # Ensure database attributes exist
        self._ensure_attributes()

    def _setup_logging(self, log_level: str) -> None:
        """Setup comprehensive logging configuration"""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Prevent duplicate handlers if logger already configured
        if self.logger.handlers:
            return
            
        self.logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        
        # Create console handler with formatting
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        
        # Create file handler for persistent logging
        file_handler = logging.FileHandler('appwrite_operations.log')
        file_handler.setLevel(logging.INFO)
        
        # Create detailed formatter
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Create simple formatter for console
        simple_formatter = logging.Formatter(
            '%(levelname)s - %(funcName)s - %(message)s'
        )
        
        console_handler.setFormatter(simple_formatter)
        file_handler.setFormatter(detailed_formatter)
        
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)

    def _init_appwrite_client(self) -> None:
        """Initialize Appwrite client with error handling"""
        try:
            self.client = Client()
            self.client.set_endpoint("http://192.168.1.22:8880/v1")
            self.client.set_project("68643fcb0001cf502505")
            
            api_key = os.getenv("APPWRITE_API_KEY")
            if not api_key:
                raise ValueError("APPWRITE_API_KEY environment variable not set")
                
            self.client.set_key(api_key)
            self.db = Databases(self.client)
            
            self.logger.info("Appwrite client initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Appwrite client: {e}")
            raise

    def _ensure_attributes(self) -> None:
        """Ensure all required database attributes exist"""
        attributes = [
            ("date", "string", 20),
            ("index", "integer", None),
            ("group_number", "integer", None),
            ("feature", "string", 255),
            ("value", "double", None),
            ("result_id", "string", 100),
            ("mission_id", "string", 100)  # Missing required attribute
        ]
        
        self.logger.info("Ensuring database attributes exist")
        created_count = 0
        existing_count = 0
        
        for key, attr_type, size in attributes:
            try:
                if attr_type == "string":
                    self.db.create_string_attribute(
                        self.database_id, 
                        self.collection_id, 
                        key=key, 
                        size=size, 
                        required=True if key in ["result_id", "mission_id"] else False
                    )
                elif attr_type == "integer":
                    self.db.create_integer_attribute(
                        self.database_id, 
                        self.collection_id, 
                        key=key, 
                        required=False
                    )
                elif attr_type == "double":
                    self.db.create_float_attribute(
                        self.database_id, 
                        self.collection_id, 
                        key=key, 
                        required=False
                    )
                
                self.logger.debug(f"Created attribute: {key} ({attr_type})")
                created_count += 1
                
            except Exception as e:
                if "already exists" in str(e).lower():
                    self.logger.debug(f"Attribute already exists: {key}")
                    existing_count += 1
                else:
                    self.logger.error(f"Failed to create attribute '{key}': {e}")
                    
        self.logger.info(f"Attributes status - Created: {created_count}, Existing: {existing_count}")

    def is_appwrite_available(self) -> bool:
        """Check if Appwrite service is available"""
        try:
            self.logger.debug("Checking Appwrite availability")
            
            response = self.db.list_documents(
                database_id=self.database_id,
                collection_id=self.collection_id,
                queries=[Query.limit(1)]
            )
            
            self.logger.debug("Appwrite service is available")
            return True
            
        except Exception as e:
            self.logger.warning(f"Appwrite service unavailable: {e}")
            return False

    def write_to_sqlite(self, result: Dict[str, Any], index: int, group_number: int, mission_id: str = None) -> None:
        """Write data to local SQLite buffer with optimized logging"""
        self.logger.debug(f"Buffering {len(result)} features - index: {index}, Group: {group_number}")
        
        try:
            conn = sqlite3.connect("local_buffer.db")
            cursor = conn.cursor()
            
            # Check if result_id and mission_id columns exist, add if not
            cursor.execute("PRAGMA table_info(buffered_results)")
            columns = [column[1] for column in cursor.fetchall()]
            
            # Create table with all required columns
            if 'buffered_results' not in [row[0] for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]:
                cursor.execute("""
                    CREATE TABLE buffered_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT,
                        index INTEGER,
                        group_number INTEGER,
                        feature TEXT,
                        value REAL,
                        result_id TEXT,
                        mission_id TEXT
                    )
                """)
            else:
                # Add missing columns if they don't exist
                if 'result_id' not in columns:
                    cursor.execute("ALTER TABLE buffered_results ADD COLUMN result_id TEXT")
                    self.logger.info("Added result_id column to buffered_results table")
                if 'mission_id' not in columns:
                    cursor.execute("ALTER TABLE buffered_results ADD COLUMN mission_id TEXT")
                    self.logger.info("Added mission_id column to buffered_results table")
            
            records_written = 0
            failed_conversions = 0
            result_id = f"iter_{index}_group_{group_number}_{datetime.now().strftime('%H%M%S')}"
            mission_id = mission_id or f"mission_{group_number}"
            
            for feature, raw_value in result.items():
                try:
                    value = float(raw_value) if raw_value is not None else None
                except (ValueError, TypeError):
                    if failed_conversions == 0:  # Log only first conversion error to reduce noise
                        self.logger.warning(f"Value conversion issues detected in batch (index {index})")
                    value = None
                    failed_conversions += 1
                
                cursor.execute("""
                    INSERT INTO buffered_results (date, index, group_number, feature, value, result_id, mission_id)
                    VALUES (DATE('now'), ?, ?, ?, ?, ?, ?)
                """, (index, group_number, feature, value, result_id, mission_id))
                
                records_written += 1
            
            conn.commit()
            conn.close()
            
            if failed_conversions > 0:
                self.logger.info(f"Buffered {records_written} records with {failed_conversions} conversion issues")
            else:
                self.logger.debug(f"Successfully buffered {records_written} records")
            
        except Exception as e:
            self.logger.error(f"Failed to write to SQLite buffer: {e}")
            raise

    def get_current_group_info(self) -> Tuple[int, Set[int]]:
        """Get current group information with detailed logging"""
        try:
            self.logger.debug("Retrieving current group information")
            
            # Get the highest group number
            max_group_result = self.db.list_documents(
                database_id=self.database_id,
                collection_id=self.collection_id,
                queries=[
                    Query.order_desc("group_number"),
                    Query.limit(1)
                ]
            )
            
            current_group = 0
            if max_group_result['documents']:
                current_group = max_group_result['documents'][0]['group_number']
                self.logger.debug(f"Found current group: {current_group}")
            else:
                self.logger.info("No existing groups found, starting with group 0")
            
            # Get all indexs for the current group
            group_results = self.db.list_documents(
                database_id=self.database_id,
                collection_id=self.collection_id,
                queries=[
                    Query.equal("group_number", current_group),
                    Query.limit(1000)
                ]
            )
            
            group_indices = set()
            for doc in group_results['documents']:
                group_indices.add(doc['index'])
            
            self.logger.info(f"Group {current_group} has {len(group_indices)} indexs: {sorted(group_indices)}")
            return current_group, group_indices
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve group information: {e}")
            return 0, set()

    def flush_sqlite_to_appwrite(self) -> None:
        """Flush buffered SQLite data to Appwrite with optimized error handling"""
        try:
            self.logger.debug("Checking for buffered data to flush")
            
            conn = sqlite3.connect("local_buffer.db")
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM buffered_results")
            buffered_data = cursor.fetchall()
            
            if not buffered_data:
                self.logger.debug("No buffered data to flush")
                conn.close()
                return
            
            self.logger.info(f"Flushing {len(buffered_data)} buffered records to Appwrite")
            
            successful_writes = 0
            failed_writes = 0
            error_messages = set()  # Use set to avoid duplicate error messages
            
            for i, row in enumerate(buffered_data, 1):
                # Handle different row formats for backward compatibility
                if len(row) == 6:  # Old format: id, date, index, group_number, feature, value
                    _, date, index, group_number, feature, value = row
                    result_id = f"iter_{index}_group_{group_number}_{i}"
                    mission_id = f"mission_{group_number}"
                elif len(row) == 7:  # Format with result_id: id, date, index, group_number, feature, value, result_id
                    _, date, index, group_number, feature, value, result_id = row
                    mission_id = f"mission_{group_number}"
                else:  # New format with both: id, date, index, group_number, feature, value, result_id, mission_id
                    _, date, index, group_number, feature, value, result_id, mission_id = row
                
                document_data = {
                    "date": date,
                    "index": index,
                    "group_number": group_number,
                    "feature": feature,
                    "value": value,
                    "result_id": result_id,
                    "mission_id": mission_id
                }
                
                try:
                    self.db.create_document(
                        database_id=self.database_id,
                        collection_id=self.collection_id,
                        document_id="unique()",
                        data=document_data
                    )
                    successful_writes += 1
                    
                except Exception as e:
                    error_messages.add(str(e))
                    failed_writes += 1
                    # Log only every 10th error to reduce log spam
                    if failed_writes <= 3 or failed_writes % 10 == 0:
                        self.logger.error(f"Flush error (#{failed_writes}): {e}")
            
            # Delete successfully written records
            if successful_writes > 0:
                success_ids = [row[0] for row in buffered_data[:successful_writes]]
                placeholders = ",".join(["?" for _ in success_ids])
                cursor.execute(f"DELETE FROM buffered_results WHERE id IN ({placeholders})", success_ids)
                conn.commit()
            
            conn.close()
            
            if failed_writes > 0:
                self.logger.warning(f"Flush completed with issues - Success: {successful_writes}, Failed: {failed_writes}")
                if len(error_messages) <= 3:  # Log unique error messages if few
                    for error_msg in error_messages:
                        self.logger.error(f"Unique error: {error_msg}")
            else:
                self.logger.info(f"Successfully flushed {successful_writes} records")
            
        except Exception as e:
            self.logger.error(f"Critical error during flush operation: {e}")

    def write_to_db(self, result: Dict[str, Any], index: int, group_number: int, mission_id: str = None) -> None:
        """Write data to database with intelligent error handling and reduced logging noise"""
        self.logger.info(f"Database write - index: {index}, Group: {group_number}, Features: {len(result)}")
        
        try:
            # First, try to flush any existing buffered data
            self.flush_sqlite_to_appwrite()
            
            successful_writes = 0
            failed_writes = 0
            result_id = f"iter_{index}_group_{group_number}_{datetime.now().strftime('%H%M%S')}"
            mission_id = mission_id or f"mission_{group_number}"
            error_messages = set()  # Track unique errors
            
            for feature_name, raw_value in result.items():
                try:
                    value_float = float(raw_value) if raw_value is not None else None
                except (ValueError, TypeError):
                    if failed_writes == 0:  # Log conversion issues once per batch
                        self.logger.warning(f"Data type conversion issues in index {index}")
                    value_float = None
                
                document_data = {
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "index": index,
                    "group_number": group_number,
                    "feature": feature_name,
                    "value": value_float,
                    "result_id": result_id,
                    "mission_id": mission_id
                }
                
                try:
                    response = self.db.create_document(
                        database_id=self.database_id,
                        collection_id=self.collection_id,
                        document_id="unique()",
                        data=document_data
                    )
                    successful_writes += 1
                    
                except Exception as e:
                    error_messages.add(str(e))
                    failed_writes += 1
                    # Log only first few errors to avoid spam
                    if failed_writes <= 2:
                        self.logger.warning(f"Appwrite write failed for '{feature_name}', buffering: {e}")
            
            # Batch buffer failed writes
            if failed_writes > 0:
                failed_features = {k: v for i, (k, v) in enumerate(result.items()) if i >= successful_writes}
                self.write_to_sqlite(failed_features, index, group_number, mission_id)
                
                if failed_writes > 2:  # Summarize if many failures
                    self.logger.warning(f"Multiple write failures ({failed_writes} total), all buffered locally")
            
            # Summary logging
            if successful_writes > 0 and failed_writes == 0:
                self.logger.info(f"✓ All {successful_writes} features written successfully")
            elif successful_writes > 0:
                self.logger.info(f"Partial success - Written: {successful_writes}, Buffered: {failed_writes}")
            else:
                self.logger.warning(f"All {failed_writes} features buffered due to Appwrite issues")
            
        except Exception as e:
            self.logger.error(f"Critical error during database write, buffering all data: {e}")
            self.write_to_sqlite(result, index, group_number, mission_id)

    def create_document(self, data: Dict[str, Any], document_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Create a single document with enhanced logging"""
        self.logger.debug(f"Creating document with ID: {document_id or 'auto-generated'}")
        
        try:
            result = self.db.create_document(
                database_id=self.database_id,
                collection_id=self.collection_id,
                document_id=document_id or "unique()",
                data=data
            )
            self.logger.info(f"Document created successfully: {result['$id']}")
            return result
            
        except Exception as e:
            self.logger.error(f"Document creation failed: {e}")
            return None

    def update_document(self, document_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a document with enhanced logging"""
        self.logger.debug(f"Updating document: {document_id}")
        
        try:
            result = self.db.update_document(
                database_id=self.database_id,
                collection_id=self.collection_id,
                document_id=document_id,
                data=data
            )
            self.logger.info(f"Document updated successfully: {document_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"Document update failed for {document_id}: {e}")
            return None

    def create_multiple_documents(self, data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create multiple documents with progress logging"""
        self.logger.info(f"Creating {len(data_list)} documents")
        
        results = []
        successful = 0
        failed = 0
        
        for i, data in enumerate(data_list, 1):
            result = self.create_document(data)
            if result:
                results.append(result)
                successful += 1
            else:
                failed += 1
            
            # Log progress for large batches
            if i % 20 == 0 or i == len(data_list):
                self.logger.debug(f"Batch progress: {i}/{len(data_list)} processed")
        
        self.logger.info(f"Batch creation completed - Success: {successful}, Failed: {failed}")
        return results

    def upsert_document(self, document_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Upsert (update or create) a document with detailed logging"""
        self.logger.debug(f"Attempting upsert for document: {document_id}")
        
        # Try update first
        result = self.update_document(document_id, data)
        if result:
            self.logger.debug(f"Document updated via upsert: {document_id}")
            return result
        
        # If update fails, try create
        self.logger.debug(f"Update failed, attempting create for: {document_id}")
        try:
            result = self.create_document(data, document_id)
            if result:
                self.logger.info(f"Document created via upsert: {document_id}")
            return result
        except Exception as e:
            self.logger.error(f"Upsert operation completely failed for {document_id}: {e}")
            return None