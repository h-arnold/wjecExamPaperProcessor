import logging
import os
import pymongo
import datetime  # Import datetime module
from datetime import UTC  # Import UTC for timezone-aware datetimes
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from dotenv import load_dotenv


class DBManager:
    """
    Manages connections to MongoDB Atlas database for the WJEC Exam Paper Processor.
    Provides methods for initialising and accessing the database connection.
    """
    
    def __init__(self, connection_string: str = None, database_name: str = None, timeout_ms: int = None):
        """
        Initialise the database manager with connection details from environment variables.
        
        Environment variables used:
        - MONGODB_URI: MongoDB Atlas connection string
        - MONGODB_DATABASE_NAME: Name of the database to connect to
        - MONGODB_TIMEOUT_MS: Connection timeout in milliseconds (optional)
        
        Args:
            connection_string (str, optional): Override environment variable
            database_name (str, optional): Override environment variable
            timeout_ms (int, optional): Override environment variable
        
        Raises:
            ValueError: If required environment variables are not set and no parameters provided
        """
        # Load environment variables from .env file
        load_dotenv()
        
        # Use provided parameters or environment variables
        self.connection_string = connection_string or os.getenv("MONGODB_URI")
        self.database_name = database_name or os.getenv("MONGODB_DATABASE_NAME")
        
        # Convert timeout to int if provided as string in env vars
        env_timeout = os.getenv("MONGODB_TIMEOUT_MS")
        if timeout_ms is not None:
            self.timeout_ms = timeout_ms
        elif env_timeout is not None:
            self.timeout_ms = int(env_timeout)
        else:
            self.timeout_ms = 5000  # Default timeout
        
        # Validate required parameters
        if not self.connection_string:
            raise ValueError("MongoDB connection string not provided. Set MONGODB_URI environment variable or pass as parameter.")
        if not self.database_name:
            raise ValueError("MongoDB database name not provided. Set MONGODB_DATABASE_NAME environment variable or pass as parameter.")
        
        self.client = None
        self.db = None
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def connect(self):
        """
        Establish connection to MongoDB Atlas.
        
        Raises:
            ConnectionError: If unable to connect to the database
        
        Returns:
            pymongo.database.Database: Connected database instance
        """
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
            
            self.logger.info(f"Successfully connected to MongoDB Atlas database: {self.database_name}")
            return self.db
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            error_msg = f"Failed to connect to MongoDB Atlas: {str(e)}"
            self.logger.error(error_msg)
            raise ConnectionError(error_msg)
    
    def get_database(self):
        """
        Get the current database connection or establish a new one if none exists.
        
        Raises:
            ConnectionError: If unable to connect to the database
            
        Returns:
            pymongo.database.Database: Connected database instance
        """
        if not self.db:
            return self.connect()
        return self.db
    
    def get_collection(self, collection_name: str):
        """
        Get a collection from the database.
        
        Args:
            collection_name (str): Name of the collection to retrieve
            
        Returns:
            pymongo.collection.Collection: The requested collection
        """
        db = self.get_database()
        return db[collection_name]
    
    async def initialize_database(self):
        """
        Initializes the MongoDB database with required collections and indexes
        for the WJEC exam paper processor system. Creates collections if they
        don't exist and sets up appropriate indexes for optimized queries.
        
        Returns:
            bool: True if initialization was successful
            
        Raises:
            ConnectionError: If database connection fails
            Exception: If initialization encounters an error
        """
        try:
            # Ensure we have a database connection
            db = self.get_database()
            self.logger.info('Connected to MongoDB database, checking collections')
            
            # Check and create collections if they don't exist
            collections = await db.list_collection_names()
            
            # Create exams collection if it doesn't exist
            if 'exams' not in collections:
                self.logger.info('Creating exams collection...')
                await db.create_collection('exams')
                
                # Create indexes for common query patterns
                await db['exams'].create_index([('subject', pymongo.ASCENDING), 
                                               ('year', pymongo.ASCENDING), 
                                               ('season', pymongo.ASCENDING)])
                await db['exams'].create_index([('examId', pymongo.ASCENDING)], unique=True)
                await db['exams'].create_index([('questions.spec_refs', pymongo.ASCENDING)])
                await db['exams'].create_index([
                    ('subject', pymongo.TEXT), 
                    ('questions.question_text', pymongo.TEXT),
                    ('questions.mark_scheme', pymongo.TEXT)
                ])
                self.logger.info('Exams collection and indexes created successfully')
            
            # Create specifications collection if it doesn't exist
            if 'specifications' not in collections:
                self.logger.info('Creating specifications collection...')
                await db.create_collection('specifications')
                
                # Create indexes for specification lookup
                await db['specifications'].create_index([
                    ('qualification', pymongo.ASCENDING), 
                    ('subject', pymongo.ASCENDING)
                ])
                await db['specifications'].create_index([
                    ('units.sections.items.spec_ref', pymongo.ASCENDING)
                ])
                await db['specifications'].create_index([
                    ('units.sections.items.keywords', pymongo.ASCENDING)
                ])
                self.logger.info('Specifications collection and indexes created successfully')
            
            # Create spec_coverage collection if it doesn't exist
            if 'spec_coverage' not in collections:
                self.logger.info('Creating spec_coverage collection...')
                await db.create_collection('spec_coverage')
                
                # Create indexes for coverage analysis
                await db['spec_coverage'].create_index([
                    ('qualification', pymongo.ASCENDING), 
                    ('subject', pymongo.ASCENDING), 
                    ('spec_ref', pymongo.ASCENDING)
                ], unique=True)
                await db['spec_coverage'].create_index([
                    ('coverage_frequency', pymongo.ASCENDING)
                ])
                self.logger.info('Spec_coverage collection and indexes created successfully')
            
            # Validate collections exist
            updated_collections = await db.list_collection_names()
            required_collections = ['exams', 'specifications', 'spec_coverage']
            all_collections_exist = all(collection in updated_collections for collection in required_collections)
            
            if all_collections_exist:
                self.logger.info('Database initialization complete')
                return True
            else:
                missing = [c for c in required_collections if c not in updated_collections]
                error_msg = f'Failed to create all required collections. Missing: {", ".join(missing)}'
                self.logger.error(error_msg)
                raise Exception(error_msg)
                
        except ConnectionError as ce:
            self.logger.error(f'Database connection failed during initialization: {str(ce)}')
            raise
        except Exception as e:
            self.logger.error(f'Database initialization failed: {str(e)}')
            raise
    
    async def import_specification(self, qualification: str, subject: str, spec_file_path: str, year_introduced: int = None, version: str = None):
        """
        Imports specification content from a markdown file into the specifications collection.
        Parses the markdown structure to extract units, sections, and individual specification points.
        
        Args:
            qualification (str): The qualification level (e.g., 'A2-Level', 'AS-Level')
            subject (str): The subject name (e.g., 'Computer Science')
            spec_file_path (str): Path to the markdown file containing specification content
            year_introduced (int, optional): Year the specification was introduced
            version (str, optional): Version identifier for the specification
            
        Returns:
            bool: True if import was successful
            
        Raises:
            FileNotFoundError: If the specification file cannot be found
            Exception: If the import process encounters an error
        """
        try:
            # Ensure we have a database connection
            db = self.get_database()
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
            result = await db['specifications'].update_one(
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
            raise
    
    def close_connection(self):
        """
        Close the MongoDB connection.
        """
        if self.client:
            self.client.close()
            self.client = None
            self.db = None
            self.logger.info("MongoDB Atlas connection closed")
            
    def disconnect(self):
        """
        Alias for close_connection() to maintain naming consistency with the integration plan.
        
        Closes the MongoDB connection and resets client and database references.
        """
        return self.close_connection()
    
    def save_exam_metadata(self, metadata, document_id=None):
        """
        Store extracted exam metadata in MongoDB.
        
        Args:
            metadata (dict): The metadata to be stored in the database
            document_id (str, optional): The document ID to use. If not provided,
                                         the system will use metadata['examId'] or generate a new ID
        
        Returns:
            str: The document ID of the saved metadata
            
        Raises:
            ValueError: If metadata doesn't contain required fields
            ConnectionError: If database connection fails
            pymongo.errors.DuplicateKeyError: If a document with the same examId already exists
        """
        try:
            # Validate required fields in metadata
            required_fields = ['subject', 'qualification', 'year', 'season', 'unit']
            missing_fields = [field for field in required_fields if field not in metadata]
            
            if missing_fields:
                raise ValueError(f"Metadata missing required fields: {', '.join(missing_fields)}")
            
            # Ensure we have a database connection
            collection = self.get_collection('exams')
            
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
            
            metadata['metadata']['processed_date'] = datetime.datetime.now(UTC)
            
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
            raise
    
    def get_exam_metadata(self, document_id):
        """
        Retrieve a specific exam document from MongoDB by ID.
        
        Args:
            document_id (str): The unique identifier of the document to retrieve
            
        Returns:
            dict: The exam metadata document or None if not found
            
        Raises:
            ConnectionError: If database connection fails
        """
        try:
            # Ensure we have a database connection
            collection = self.get_collection('exams')
            
            # Query for the document
            document = collection.find_one({'examId': document_id})
            
            if document:
                self.logger.info(f"Retrieved exam metadata for ID: {document_id}")
            else:
                self.logger.warning(f"No exam metadata found with ID: {document_id}")
            
            return document
            
        except Exception as e:
            self.logger.error(f"Error retrieving exam metadata: {str(e)}")
            raise
    
    def delete_exam_metadata(self, document_id):
        """
        Remove a specific exam document from MongoDB by ID.
        
        Args:
            document_id (str): The unique identifier of the document to delete
            
        Returns:
            bool: True if document was deleted, False if document was not found
            
        Raises:
            ConnectionError: If database connection fails
        """
        try:
            # Ensure we have a database connection
            collection = self.get_collection('exams')
            
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
            raise
    
    def document_exists(self, document_id):
        """
        Check if a document already exists in the exams collection.
        
        Args:
            document_id (str): The document ID to check
            
        Returns:
            bool: True if document exists, False otherwise
        """
        try:
            collection = self.get_collection('exams')
            count = collection.count_documents({'examId': document_id}, limit=1)
            return count > 0
        except Exception as e:
            self.logger.error(f"Error checking document existence: {str(e)}")
            raise