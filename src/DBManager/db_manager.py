"""
Database manager for WJEC Exam Paper Processor.

This module provides functionality to interact with MongoDB for storing
and retrieving exam metadata and related information.
"""

import logging
import os
import datetime
from datetime import UTC
from typing import Dict, Any, List, Optional, Union

try:
    import pymongo
    from pymongo import MongoClient
    import gridfs
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, DuplicateKeyError
    from dotenv import load_dotenv
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False


class DBManager:
    """
    Manages MongoDB database connections and operations for exam metadata.
    
    This class provides methods for connecting to MongoDB, storing exam metadata,
    retrieving documents, and managing relationships between documents.
    """
    
    def __init__(self, connection_string: Optional[str] = None, database_name: Optional[str] = None, timeout_ms: Optional[int] = None):
        """
        Initialise the database manager with connection details.
        
        Environment variables used:
        - MONGODB_URI: MongoDB connection string
        - MONGODB_DATABASE_NAME: Name of the database to connect to
        - MONGODB_TIMEOUT_MS: Connection timeout in milliseconds (optional)
        
        Args:
            connection_string: MongoDB connection string. If None, uses environment variable
                              MONGODB_URI or falls back to localhost.
            database_name: Name of the MongoDB database to use.
            timeout_ms: Connection timeout in milliseconds.
        """
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        if not MONGODB_AVAILABLE:
            self.logger.warning("pymongo not installed. MongoDB functionality will not be available.")
            self.client = None
            self.db = None
            return
            
        # Load environment variables
        load_dotenv()
        
        # Get connection string from parameters or environment
        self.connection_string = connection_string or os.environ.get("MONGODB_URI")
        if not self.connection_string:
            self.logger.warning("MongoDB connection string not provided. Set MONGODB_URI environment variable or pass as parameter.")
            self.connection_string = "mongodb://localhost:27017/"
            
        # Get database name from parameters or environment
        self.database_name = database_name or os.environ.get("MONGODB_DATABASE_NAME", "wjec_exams")
        
        # Get timeout from parameters or environment
        env_timeout = os.environ.get("MONGODB_TIMEOUT_MS")
        if timeout_ms is not None:
            self.timeout_ms = timeout_ms
        elif env_timeout is not None:
            self.timeout_ms = int(env_timeout)
        else:
            self.timeout_ms = 5000  # Default timeout
            
        self.client = None
        self.db = None
        
        # Try to connect immediately
        try:
            self.connect()
        except ConnectionFailure as e:
            self.logger.error(f"Failed to connect to MongoDB: {e}")
    
    def connect(self):
        """
        Establish connection to MongoDB.
        
        Raises:
            ConnectionFailure: If connection to MongoDB fails.
            
        Returns:
            pymongo.database.Database: Connected database instance
        """
        if not MONGODB_AVAILABLE:
            self.logger.error("Cannot connect: pymongo not installed")
            return None
            
        try:
            # Attempt to establish connection with timeout
            self.client = MongoClient(
                self.connection_string, 
                serverSelectionTimeoutMS=self.timeout_ms
            )
            
            # Test connection by executing a command
            self.client.admin.command('ping')
            
            # Get database instance
            self.db = self.client[self.database_name]
            
            self.logger.info(f"Connected to MongoDB: {self.database_name}")
            
            # Check if database is initialised by looking for required collections
            self._check_and_initialise_database()
            
            return self.db
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            error_msg = f"Server not available: {e}"
            self.logger.error(error_msg)
            raise ConnectionFailure(error_msg)
    
    def _check_and_initialise_database(self):
        """
        Checks if required collections exist and initialises the database if needed.
        This method is called automatically when connecting to the database.
        """
        if not MONGODB_AVAILABLE:
            return
            
        try:
            required_collections = ['documents']
            
            # Get list of existing collections
            existing_collections = self.db.list_collection_names()
            
            # Check if all required collections exist
            all_collections_exist = all(collection in existing_collections for collection in required_collections)
            
            if not all_collections_exist:
                missing = [c for c in required_collections if c not in existing_collections]
                self.logger.info(f"Missing collections detected: {', '.join(missing)}. Initialising database...")
                
                # Call initialise_database directly
                self.initialise_database()
            else:
                self.logger.info("Database already initialised with all required collections")
                
        except Exception as e:
            self.logger.error(f"Error checking database initialisation status: {e}")
            self.logger.warning("Database may need to be initialised manually")
    
    def disconnect(self):
        """
        Close MongoDB connection.
        
        This is an alias for close_connection() for naming consistency.
        """
        return self.close_connection()
    
    def close_connection(self):
        """
        Close MongoDB connection.
        """
        if self.client is not None:
            self.client.close()
            self.client = None
            self.db = None
            self.logger.info("Disconnected from MongoDB")
    
    def get_database(self):
        """
        Return the database instance.
        
        Returns:
            pymongo.database.Database: The MongoDB database instance, or None if not connected.
        """
        if self.db is None:
            return self.connect()
        return self.db
    
    def get_collection(self, collection_name: str):
        """
        Get a collection from the database.
        
        Args:
            collection_name: Name of the collection to retrieve
            
        Returns:
            pymongo.collection.Collection: The requested collection
        """
        db = self.get_database()
        if db is None:
            self.logger.error("Not connected to MongoDB")
            return None
        return db[collection_name]
    
    # IMPORTANT: This will need refactoring later. This code won't work at the moment.
    def exam_exists(self, document_id: str) -> bool:
        """
        Check if a document with the given ID exists in the database.
        
        Args:
            document_id: The ID of the document to check.
            
        Returns:
            bool: True if the document exists, False otherwise.
        """
        try:
            collection = self.get_collection('exams')
            if collection is None:
                return False
            
            count = collection.count_documents({'examId': document_id}, limit=1)
            return count > 0
        except Exception as e:
            self.logger.error(f"Error checking if document exists: {e}")
            return False
    
    def save_exam_metadata(self, metadata: Dict[str, Any], document_id: Optional[str] = None) -> Optional[str]:
        """
        Store exam metadata in MongoDB.
        
        Args:
            metadata: Dictionary containing the metadata to store.
            document_id: Optional ID for the document. If None, will use metadata['examId']
                        or generate a new ID.
                        
        Returns:
            str: The ID of the stored document, or None if storage failed.
            
        Raises:
            ValueError: If required fields are missing from the metadata.
        """
        try:
            # Validate required fields in metadata
            required_fields = ['subject', 'qualification', 'year', 'season', 'unit']
            missing_fields = [field for field in required_fields if field not in metadata]
            
            if missing_fields:
                raise ValueError(f"Metadata missing required fields: {', '.join(missing_fields)}")
            
            # Ensure we have a database connection
            collection = self.get_collection('exams')
            if collection is None:
                self.logger.error("Not connected to MongoDB")
                return None
            
            # Set examId if not in metadata
            if 'examId' not in metadata and document_id:
                metadata['examId'] = document_id
            elif 'examId' not in metadata:
                # Generate an examId if neither is provided
                metadata['examId'] = f"{metadata['subject']}_{metadata['qualification']}_{metadata['unit']}_{metadata['year']}_{metadata['season']}"
            
            # Use specified document_id or the one from metadata
            doc_id = document_id or metadata['examId']
            
            # Add timestamp for when the document was processed
            if 'metadata' not in metadata:
                metadata['metadata'] = {}
            
            # Add timestamps
            now = datetime.datetime.now(UTC)
            if 'created_at' not in metadata:
                metadata['created_at'] = now
            metadata['updated_at'] = now
            
            # Insert or update the document
            result = collection.update_one(
                {'examId': doc_id},
                {'$set': metadata},
                 upsert=True
            )
            
            if result.upserted_id:
                self.logger.info(f"New exam metadata inserted with ID: {doc_id}")
            else:
                self.logger.info(f"Exam metadata updated for ID: {doc_id}")
            
            return doc_id
            
        except ValueError as ve:
            self.logger.error(f"Validation error: {str(ve)}")
            raise
        except pymongo.errors.DuplicateKeyError as dke:
            self.logger.error(f"Duplicate key error: {str(dke)}")
            raise
        except Exception as e:
            self.logger.error(f"Error saving exam metadata: {str(e)}")
            return None
    
    def get_exam_metadata(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific exam document from MongoDB by ID.
        
        Args:
            document_id: The unique identifier of the document to retrieve
            
        Returns:
            dict: The exam metadata document or None if not found
        """
        try:
            # Ensure we have a database connection
            collection = self.get_collection('exams')
            if collection is None:
                self.logger.error("Not connected to MongoDB")
                return None
            
            # Query for the document
            document = collection.find_one({'examId': document_id})
            
            if document:
                self.logger.info(f"Retrieved exam metadata for ID: {document_id}")
            else:
                self.logger.warning(f"No exam metadata found with ID: {document_id}")
            
            return document
            
        except Exception as e:
            self.logger.error(f"Error retrieving exam metadata: {str(e)}")
            return None
    
    def delete_exam_metadata(self, document_id: str) -> bool:
        """
        Remove a specific exam document from MongoDB by ID.
        
        Args:
            document_id: The unique identifier of the document to delete
            
        Returns:
            bool: True if document was deleted, False if document was not found
        """
        try:
            # Ensure we have a database connection
            collection = self.get_collection('exams')
            if collection is None:
                self.logger.error("Not connected to MongoDB")
                return False
            
            # Delete the document
            result = collection.delete_one({'examId': document_id})
            
            if result.deleted_count > 0:
                self.logger.info(f"Deleted exam metadata with ID: {document_id}")
                return True
            else:
                self.logger.warning(f"No exam metadata found to delete with ID: {document_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error deleting exam metadata: {str(e)}")
            return False
    
    def bulk_save_exam_metadata(self, metadata_list: List[Dict[str, Any]], document_ids: Optional[List[str]] = None) -> List[str]:
        """
        Store multiple exam metadata records efficiently.
        
        Args:
            metadata_list: List of metadata dictionaries to store.
            document_ids: Optional list of document IDs to use. If provided,
                         must match the length of metadata_list.
            
        Returns:
            List[str]: List of document IDs that were successfully stored.
        """
        try:
            # Validate document_ids if provided
            if document_ids and len(document_ids) != len(metadata_list):
                raise ValueError(f"Document IDs list length ({len(document_ids)}) doesn't match metadata list length ({len(metadata_list)})")
            
            # Ensure we have a database connection
            collection = self.get_collection('exams')
            if collection is None:
                self.logger.error("Not connected to MongoDB")
                return []
            
            if not metadata_list:
                return []
            
            saved_ids = []
            bulk_operations = []
            
            # Process each metadata record
            for i, metadata in enumerate(metadata_list):
                try:
                    # Validate required fields in metadata
                    required_fields = ['subject', 'qualification', 'year', 'season', 'unit']
                    missing_fields = [field for field in required_fields if field not in metadata]
                    
                    if missing_fields:
                        self.logger.warning(
                            f"Skipping document with missing fields: {', '.join(missing_fields)}"
                        )
                        continue
                    
                    # Set examId if not in metadata
                    doc_id = None
                    if document_ids:
                        doc_id = document_ids[i]
                        metadata['examId'] = doc_id
                    elif 'examId' not in metadata:
                        # Generate an examId if neither is provided
                        doc_id = f"{metadata['subject']}_{metadata['qualification']}_{metadata['unit']}_{metadata['year']}_{metadata['season']}"
                        metadata['examId'] = doc_id
                    else:
                        doc_id = metadata['examId']
                    
                    # Add timestamp for when the document was processed
                    if 'metadata' not in metadata:
                        metadata['metadata'] = {}
                    
                    # Add timestamps
                    now = datetime.datetime.now(UTC)
                    if 'created_at' not in metadata:
                        metadata['created_at'] = now
                    metadata['updated_at'] = now
                    
                    # Add to list of saved IDs
                    saved_ids.append(doc_id)
                    
                    # Create upsert operation for bulk execution
                    bulk_operations.append(
                        pymongo.UpdateOne(
                            {'examId': doc_id},
                            {'$set': metadata},
                            upsert=True
                        )
                    )
                
                except Exception as e:
                    self.logger.error(f"Error preparing document for bulk save: {e}")
            
            # Execute bulk operation if we have any operations
            if bulk_operations:
                result = collection.bulk_write(bulk_operations, ordered=False)
                self.logger.info(
                    f"Bulk operation: {result.upserted_count} inserted, "
                    f"{result.modified_count} modified"
                )
            else:
                self.logger.warning("No metadata records to save")
            
            return saved_ids
            
        except ValueError as ve:
            self.logger.error(f"Validation error in bulk save: {str(ve)}")
            raise
        except Exception as e:
            self.logger.error(f"Error performing bulk save of exam metadata: {str(e)}")
            return []
    
    def initialise_database(self) -> bool:
        """
        Initialises the MongoDB database with required collections and indexes
        for the WJEC exam paper processor system.
        
        Creates the documents collection if it doesn't exist and sets up appropriate indexes
        for optimised queries.
        
        Returns:
            bool: True if initialisation was successful, False otherwise
        """
        if not MONGODB_AVAILABLE:
            self.logger.error("Cannot initialise database: pymongo not installed")
            return False
            
        try:
            # Ensure we have a database connection
            db = self.get_database()
            if db is None:
                self.logger.error("Failed to connect to MongoDB database")
                return False
                
            self.logger.info('Connected to MongoDB database, checking collections')
            
            # Check and create collections if they don't exist
            collections = db.list_collection_names()
            
            # Create documents collection if it doesn't exist
            if 'documents' not in collections:
                self.logger.info('Creating documents collection...')
                db.create_collection('documents')
                
                # Create indexes for document lookup
                db['documents'].create_index([('document_id', pymongo.ASCENDING)], unique=True)
                
                self.logger.info('Documents collection and indexes created successfully')
            
            # Validate collections exist
            updated_collections = db.list_collection_names()
            required_collections = ['documents']
            all_collections_exist = all(collection in updated_collections for collection in required_collections)
            
            if all_collections_exist:
                self.logger.info('Database initialisation complete')
                return True
            else:
                missing = [c for c in required_collections if c not in updated_collections]
                self.logger.error(f'Failed to create all required collections. Missing: {", ".join(missing)}')
                return False
                
        except ConnectionFailure as ce:
            self.logger.error(f'Database connection failed during initialisation: {str(ce)}')
            return False
        except Exception as e:
            self.logger.error(f'Database initialisation failed: {str(e)}')
            return False
    
    def import_specification(self, qualification: str, subject: str, spec_file_path: str, 
                          year_introduced: Optional[int] = None, version: Optional[str] = None) -> bool:
        """
        Imports specification content from a markdown file into the specifications collection.
        
        Parses the markdown structure to extract units, sections, and individual specification points.
        
        Args:
            qualification: The qualification level (e.g., 'A2-Level', 'AS-Level')
            subject: The subject name (e.g., 'Computer Science')
            spec_file_path: Path to the markdown file containing specification content
            year_introduced: Year the specification was introduced
            version: Version identifier for the specification
            
        Returns:
            bool: True if import was successful, False otherwise
            
        Raises:
            FileNotFoundError: If the specification file cannot be found
        """
        if not MONGODB_AVAILABLE:
            self.logger.error("Cannot import specification: pymongo not installed")
            return False
            
        try:
            # Ensure we have a database connection
            db = self.get_database()
            if db is None:
                self.logger.error("Failed to connect to MongoDB database")
                return False
                
            self.logger.info(f'Importing specification for {qualification} {subject} from {spec_file_path}')
            
            # Check if file exists
            if not os.path.exists(spec_file_path):
                raise FileNotFoundError(f"Specification file not found: {spec_file_path}")
            
            # Read and parse the markdown file
            with open(spec_file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Parse the markdown structure to extract specification data
            units = []
            current_unit = None
            current_section = None
            
            # Split content by lines
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                
                # Skip empty lines and horizontal rules
                if not line or line.startswith('---'):
                    continue
                
                # Unit heading (level 2)
                if line.startswith('## '):
                    unit_title = line.replace('## ', '').strip()
                    # Extract unit number and name
                    parts = unit_title.split(' ', 2)
                    if len(parts) >= 3:
                        unit_number = parts[1].strip('*.')
                        unit_name = parts[2].strip('*')
                    else:
                        unit_number = parts[0].strip('*.')
                        unit_name = ' '.join(parts[1:]).strip('*')
                    
                    # Create new unit
                    current_unit = {
                        'unit_number': unit_number,
                        'unit_name': unit_name,
                        'sections': []
                    }
                    units.append(current_unit)
                    current_section = None
                
                # Section heading (level 3)
                elif line.startswith('### '):
                    if current_unit is None:
                        continue  # Skip if no current unit
                    
                    section_title = line.replace('### ', '').strip()
                    # Extract section number and name
                    parts = section_title.split(' ', 1)
                    if len(parts) >= 2:
                        section_number = parts[0].strip('*.')
                        section_name = parts[1].strip('*')
                    else:
                        section_number = parts[0].strip('*.')
                        section_name = parts[0].strip('*.')
                    
                    # Create new section
                    current_section = {
                        'section_number': section_number,
                        'section_name': section_name,
                        'items': []
                    }
                    current_unit['sections'].append(current_section)
                
                # Specification item (bullet point)
                elif line.startswith('- **') and current_section is not None:
                    # Extract spec reference and description
                    spec_ref_match = line.split('**', 2)
                    if len(spec_ref_match) >= 3:
                        spec_ref = spec_ref_match[1].strip()
                        description = spec_ref_match[2].strip().lstrip('** ').strip()
                        
                        # Extract keywords from description
                        keywords = []
                        for word in description.split():
                            word = word.lower().strip('.,;:()[]{}').strip()
                            if len(word) > 3 and word not in ['this', 'that', 'with', 'from', 'their', 'have', 'using']:
                                keywords.append(word)
                        
                        # Add specification item
                        current_section['items'].append({
                            'spec_ref': spec_ref,
                            'description': description,
                            'keywords': keywords
                        })
            
            # Create specification document
            spec_document = {
                'qualification': qualification,
                'subject': subject,
                'year_introduced': year_introduced,
                'version': version,
                'units': units,
                'imported_at': datetime.datetime.now(UTC)
            }
            
            # Insert or update specification document
            result = db['specifications'].update_one(
                {'qualification': qualification, 'subject': subject},
                {'$set': spec_document},
                upsert=True
            )
            
            self.logger.info(f'Specification import complete. Affected: {result.modified_count if result.matched_count > 0 else "1 (new)"}')
            return True
            
        except FileNotFoundError as fnf:
            self.logger.error(f'Specification file not found: {str(fnf)}')
            raise
        except Exception as e:
            self.logger.error(f'Specification import failed: {str(e)}')
            return False
    
    # Async methods from dbManager.py to be implemented as needed
    
    def _prepare_metadata_for_db(self, metadata: Dict[str, Any], document_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Prepare metadata dictionary for database storage.
        
        Args:
            metadata: The metadata dictionary to prepare.
            document_id: Optional document ID to use.
            
        Returns:
            Dict: Database-ready document.
        """
        # Create a copy to avoid modifying the original
        document = metadata.copy()
        
        # Set document ID
        if document_id:
            document["examId"] = document_id
        elif "document_id" in document:
            document["examId"] = document.pop("document_id")
        else:
            # Generate an ID based on metadata properties
            parts = [
                str(document.get("subject", "unknown")),
                str(document.get("qualification", "unknown")),
                str(document.get("unit", "00")),
                str(document.get("year", "0000")),
                str(document.get("season", "unknown"))
            ]
            document["examId"] = "-".join(parts).lower().replace(" ", "_")
        
        # Add timestamps
        now = datetime.datetime.now(UTC)
        if "created_at" not in document:
            document["created_at"] = now
        document["updated_at"] = now
        
        return document

    def get_gridfs(self):
        """
        Get a GridFS instance for the current database.
        
        Returns:
            pymongo.gridfs.GridFS: A GridFS instance if connected, None otherwise
        """
        db = self.get_database()
        if db is None:
            self.logger.error("Not connected to MongoDB - cannot create GridFS instance")
            return None
        return gridfs.GridFS(db)

    def store_file_in_gridfs(self, file_data, content_type=None, filename=None, metadata=None):
        """
        Store a file in GridFS.
        
        Args:
            file_data: File data as bytes, Path object, string path, or file-like object
            content_type: Optional MIME type of the file
            filename: Optional filename
            metadata: Optional dictionary with additional metadata
        
        Returns:
            str: The ID of the stored file as a string, or None if storage failed
        """
        try:
            # Ensure we have a database connection
            fs = self.get_gridfs()
            if fs is None:
                self.logger.error("Not connected to MongoDB GridFS")
                return None
            
            # Prepare file data
            if isinstance(file_data, bytes):
                data = file_data
            elif isinstance(file_data, str) and os.path.isfile(file_data):
                # String path to file
                with open(file_data, 'rb') as f:
                    data = f.read()
            elif hasattr(file_data, 'read') and callable(file_data.read):
                # File-like object
                pos = file_data.tell()
                file_data.seek(0)
                data = file_data.read()
                file_data.seek(pos)
            else:
                # Try to convert to bytes
                data = bytes(file_data)
            
            # Add upload timestamp to metadata
            meta = metadata or {}
            meta['upload_date'] = datetime.datetime.now(UTC)
            
            # Store file in GridFS
            file_id = fs.put(
                data, 
                content_type=content_type,
                filename=filename,
                metadata=meta
            )
            
            self.logger.info(f"File stored in GridFS with ID: {file_id}")
            return str(file_id)
            
        except Exception as e:
            self.logger.error(f"Error storing file in GridFS: {str(e)}")
            return None

    def get_file_from_gridfs(self, file_id):
        """
        Retrieve a file from GridFS.
        
        Args:
            file_id: The ID of the file to retrieve, as string or ObjectId
        
        Returns:
            GridOut: The file object, which can be read like a file
        
        Raises:
            NoFile: If no such file exists
        """
        try:
            # Ensure we have a database connection
            fs = self.get_gridfs()
            if fs is None:
                self.logger.error("Not connected to MongoDB GridFS")
                return None
            
            # Convert string ID to ObjectId if necessary
            if isinstance(file_id, str):
                file_id = pymongo.ObjectId(file_id)
            
            # Retrieve file
            grid_out = fs.get(file_id)
            return grid_out
            
        except pymongo.errors.NoFile as nf:
            self.logger.error(f"File not found in GridFS: {str(nf)}")
            raise
        except Exception as e:
            self.logger.error(f"Error retrieving file from GridFS: {str(e)}")
            return None

    def delete_file_from_gridfs(self, file_id):
        """
        Delete a file from GridFS.
        
        Args:
            file_id: The ID of the file to delete, as string or ObjectId
        
        Returns:
            bool: True if file was deleted, False otherwise
        """
        try:
            # Ensure we have a database connection
            fs = self.get_gridfs()
            if fs is None:
                self.logger.error("Not connected to MongoDB GridFS")
                return False
            
            # Convert string ID to ObjectId if necessary
            if isinstance(file_id, str):
                file_id = pymongo.ObjectId(file_id)
            
            # Delete file
            fs.delete(file_id)
            self.logger.info(f"File deleted from GridFS: {file_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting file from GridFS: {str(e)}")
            return False