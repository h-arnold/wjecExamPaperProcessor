from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from bson import ObjectId
from pathlib import Path
import logging


from src.FileManager.file_manager import FileManager
from src.DBManager.db_manager import DBManager
from src.DBManager.document_repository import DocumentRepository
from src.Prompts import QuestionIndexIdentifier
from src.Llm_client import LLMClientFactory

class Document:
    """
    Represents a WJEC exam document (Question Paper or Mark Scheme).
    This class models the document structure as stored in MongoDB.
    Document objects will normally form part of an `exam` object.
    """
    
    def __init__(
        self,
        document_id: str,
        document_type: str,
        pdf_filename: str,
        pdf_file_id: str,
        ocr_json: Optional[List[Dict[str, Any]]] = None,
        ocr_storage: Optional[str] = None,
        pdf_upload_date: Optional[datetime] = None,
        ocr_upload_date: Optional[datetime] = None,
        images: Optional[List[Dict[str, Any]]] = None,
        processed: bool = False,
        question_start_index: Optional[int] = None,
        _id: Optional[ObjectId] = None,
        db_manager: Optional[DBManager] = None,
        document_repository: Optional[DocumentRepository] = None,
        pdf_data: Optional[bytes] = None,
        document_collection = None,
        exam_id: Optional[str] = None
    ):
        """
        Initialise a Document object.
        
        Args:
            document_id (str): Unique identifier for the document (hash of PDF file)
            document_type (str): Type of document ('Question Paper' or 'Mark Scheme')
            pdf_filename (str): Original filename of the PDF
            pdf_file_id (str): GridFS file ID of the stored PDF
            ocr_json (List[Dict], optional): List of serialised OCR result pages
            ocr_storage (str, optional): Storage type for OCR data (e.g. 'inline')
            pdf_upload_date (datetime, optional): Timestamp when PDF was uploaded
            ocr_upload_date (datetime, optional): Timestamp when OCR was completed
            images (List[Dict], optional): List of images extracted from the document
            processed (bool): Flag indicating if the document has been fully processed
            question_start_index (int, optional): Index where questions begin in the document
            _id (ObjectId, optional): MongoDB ObjectId
            db_manager (DBManager, optional): Database manager instance - ideally passed from elsewhere to avoid creating a new DB connection for each document.
            document_repository (DocumentRepository, optional): Repository for document operations
            pdf_data (bytes, optional): The actual PDF file content as bytes
            document_collection: MongoDB collection for documents (if already available)
            exam_id (str, optional): ID of the exam this document belongs to
        """
        self.document_id = document_id
        self.document_type = document_type
        self.pdf_filename = pdf_filename
        self.pdf_file_id = pdf_file_id
        self.ocr_json = ocr_json or []
        self.ocr_storage = ocr_storage
        self.pdf_upload_date = pdf_upload_date
        self.ocr_upload_date = ocr_upload_date
        self.images = images or []
        self.processed = processed
        self._question_start_index = question_start_index
        self._id = _id
        self.db_manager = db_manager or DBManager()
        self._pdf_data = pdf_data  # Store PDF data internally (use property for access)
        self._document_collection = document_collection  # Cache the collection if provided
        self._exam_id = exam_id
        
        # Initialize document repository
        if document_repository is None and db_manager is not None:
            self.document_repository = DocumentRepository(db_manager)
        else:
            self.document_repository = document_repository or DocumentRepository(self.db_manager)

    # Read-only properties that shouldn't change after initialization
    @property
    def id(self) -> Optional[ObjectId]:
        """MongoDB ObjectId of the document."""
        return self._id
        
    @property
    def pdf_upload_date(self) -> Optional[datetime]:
        """Date and time when the PDF was uploaded."""
        return self._pdf_upload_date
        
    @pdf_upload_date.setter
    def pdf_upload_date(self, value: Optional[datetime]):
        if value is not None and not isinstance(value, datetime):
            raise TypeError("pdf_upload_date must be a datetime object or None")
        self._pdf_upload_date = value
        
    @property
    def ocr_upload_date(self) -> Optional[datetime]:
        """Date and time when OCR processing was completed."""
        return self._ocr_upload_date
        
    @ocr_upload_date.setter
    def ocr_upload_date(self, value: Optional[datetime]):
        if value is not None and not isinstance(value, datetime):
            raise TypeError("ocr_upload_date must be a datetime object or None")
        self._ocr_upload_date = value
    
    @property
    def document_id(self) -> str:
        """Unique identifier for the document (hash of PDF file)."""
        return self._document_id
        
    @document_id.setter
    def document_id(self, value: str):
        if not isinstance(value, str) or not value:
            raise ValueError("document_id must be a non-empty string")
        
        # Validate SHA-256 hash format (64 hexadecimal characters)
        import re
        if not re.match(r'^[0-9a-f]{64}$', value.lower()):
            raise ValueError("document_id must be a valid SHA-256 hash (64 hexadecimal characters)")
            
        self._document_id = value
    
    @property
    def document_type(self) -> str:
        """Type of document (Question Paper, Mark Scheme, or Unknown)."""
        return self._document_type
        
    @document_type.setter
    def document_type(self, value: str):
        valid_types = ["Question Paper", "Mark Scheme", "Unknown"]
        if not isinstance(value, str) or value not in valid_types:
            raise ValueError(f"document_type must be one of: {', '.join(valid_types)}")
        self._document_type = value
    
    @property
    def pdf_filename(self) -> str:
        """Original filename of the PDF."""
        return self._pdf_filename
        
    @pdf_filename.setter
    def pdf_filename(self, value: str):
        if not isinstance(value, str):
            raise ValueError("pdf_filename must be a string")
        
        # Ensure the filename ends with .pdf extension (case-insensitive)
        if not value.lower().endswith('.pdf'):
            raise ValueError("pdf_filename must end with .pdf extension")
            
        self._pdf_filename = value
    
    @property
    def pdf_file_id(self) -> str:
        """GridFS file ID of the stored PDF."""
        return self._pdf_file_id
        
    @pdf_file_id.setter
    def pdf_file_id(self, value: str):
        if not isinstance(value, str) and value is not None:
            raise ValueError("pdf_file_id must be a string or None")
        self._pdf_file_id = value
    
    @property
    def ocr_json(self) -> List[Dict[str, Any]]:
        """List of serialised OCR result pages."""
        return self._ocr_json
        
    @ocr_json.setter
    def ocr_json(self, value: List[Dict[str, Any]]):
        if not isinstance(value, list):
            raise ValueError("ocr_json must be a list")
        self._ocr_json = value
    
    @property
    def ocr_storage(self) -> Optional[str]:
        """Storage type for OCR data (e.g. 'inline', 'gridfs')."""
        return self._ocr_storage
        
    @ocr_storage.setter
    def ocr_storage(self, value: Optional[str]):
        valid_storage_types = [None, "inline", "gridfs"]
        if value not in valid_storage_types:
            raise ValueError(f"ocr_storage must be one of: {', '.join(str(t) for t in valid_storage_types)}")
        self._ocr_storage = value
    
    @property
    def images(self) -> List[Dict[str, Any]]:
        """List of images extracted from the document."""
        return self._images
        
    @images.setter
    def images(self, value: List[Dict[str, Any]]):
        if not isinstance(value, list):
            raise ValueError("images must be a list")
        self._images = value
    
    @property
    def processed(self) -> bool:
        """Flag indicating if the document has been fully processed."""
        return self._processed
        
    @processed.setter
    def processed(self, value: bool):
        if not isinstance(value, bool):
            raise ValueError("processed must be a boolean value")
        self._processed = value

    @property
    def pdf_data(self) -> Optional[bytes]:
        """
        Get the PDF data. If not already loaded, fetch it from GridFS.
        
        Returns:
            bytes: The PDF file content as bytes, or None if retrieval fails
        """
        if self._pdf_data is None:
            try:
                self._pdf_data = self.get_pdf_file()
            except ValueError as e:
                logging.warning(f"Failed to load PDF data: {e}")
                return None
        return self._pdf_data

    @property
    def question_start_index(self) -> Optional[int]:
        """Index where questions begin in the document."""
        return self._question_start_index
        
    @question_start_index.setter
    def question_start_index(self, value: Optional[int]):
        if value is not None and not isinstance(value, int):
            raise TypeError("question_start_index must be an integer or None")
        if value is not None and (value < 0 or value > 10):  # Reasonable upper limit for question indices
            raise ValueError(f"question_start_index {value} is outside reasonable range (0-10)")
        self._question_start_index = value

    @property
    def document_collection(self):
        """
        Get the documents collection, caching it for future use.
        
        Note: This property is maintained for backward compatibility.
        New code should use document_repository for database operations.
        
        Returns:
            The MongoDB documents collection or None if it can't be accessed
        """
        if self._document_collection is None:
            self._document_collection = self.db_manager.get_collection('documents')
        return self._document_collection

    @property
    def exam_id(self) -> Optional[str]:
        """ID of the exam this document belongs to."""
        return self._exam_id
        
    @exam_id.setter
    def exam_id(self, value: Optional[str]):
        if value is not None and not isinstance(value, str):
            raise TypeError("exam_id must be a string or None")
        self._exam_id = value

    @staticmethod
    def _determine_document_type(filename: str) -> str:
        """
        Determine the document type based on the filename.
        
        Args:
            filename (str): The filename to analyse
            
        Returns:
            str: The determined document type ('Mark Scheme', 'Question Paper', or 'Unknown')
        """
        filename = filename.lower()
        
        # Check for mark scheme indicators
        if any(pattern in filename for pattern in ["ms", "mark scheme", "markscheme", "mark_scheme"]):
            return "Mark Scheme"
        
        # Check for question paper indicators
        elif any(pattern in filename for pattern in ["qp", "question paper", "questionpaper", "question_paper", "exam_paper"]):
            return "Question Paper"
        
        # Default to question paper if no pattern matches - mark schemes are usually explicitly labelled. This may need to be reviewed.
        else:
            return "Question Paper"

    @staticmethod
    def check_document_exists(document_id: str, db_manager: Optional[DBManager] = None,
                              document_repository: Optional[DocumentRepository] = None) -> bool:
        """
        Check if a document with the given ID exists in the database.
        
        Args:
            document_id: The document ID (hash) to check
            db_manager: Optional DBManager instance to use for database operations
            document_repository: Optional DocumentRepository instance to use for document operations
            
        Returns:
            bool: True if the document exists, False otherwise
        """
        # Use document_repository if provided
        if document_repository is not None:
            return document_repository.check_document_exists(document_id)
            
        # Initialize DB manager and document repository if not provided
        if db_manager is None:
            db_manager = DBManager()
        
        doc_repo = DocumentRepository(db_manager)
        return doc_repo.check_document_exists(document_id)

    @classmethod
    def from_pdf(cls, pdf_file: Union[str, Path], 
                 db_manager: Optional[DBManager] = None, 
                 file_manager: Optional[FileManager] = None,
                 document_repository: Optional[DocumentRepository] = None) -> 'Document':
        """
        Create a Document instance from a PDF file, without OCR processing.
        
        This method hashes the PDF file, checks if it exists in the database,
        and if not, uploads it to GridFS. OCR processing must be performed separately.
        
        Args:
            pdf_file (str or Path): Path to the PDF file
            db_manager (DBManager, optional): Database manager instance
            file_manager (FileManager, optional): File manager instance
            document_repository (DocumentRepository, optional): Repository for document operations
            
        Returns:
            Document: The created document instance
            
        Raises:
            ValueError: If the PDF file cannot be processed
        """
        logger = logging.getLogger(__name__)
        
        # Initialize managers if not provided
        if db_manager is None:
            db_manager = DBManager()
        if file_manager is None:
            file_manager = FileManager()
        if document_repository is None:
            document_repository = DocumentRepository(db_manager)
        
        try:
            # Convert to Path object
            pdf_path = Path(pdf_file)
            
            # 1. Generate document_id (hash) for the PDF file
            document_id = file_manager.get_file_hash(pdf_path)
            logger.info(f"Generated document ID (hash): {document_id}")
            
            # 2. Check if document already exists in the database
            if document_repository.check_document_exists(document_id):
                logger.info(f"Document with ID {document_id} already exists in the database")
                return cls.from_database(document_id, db_manager, document_repository=document_repository)
            
            # Read PDF data before storing it in GridFS
            with open(pdf_path, 'rb') as pdf_file_obj:
                pdf_data = pdf_file_obj.read()
            
            # 3. Determine document type from filename
            pdf_filename = pdf_path.name
            document_type = cls._determine_document_type(pdf_filename)
            if document_type == "Unknown":
                logger.warning(f"Could not determine document type for {pdf_filename}, setting to 'Unknown'")
            
            # 4. Store PDF in GridFS using document repository
            pdf_id = document_repository.store_pdf_in_gridfs(pdf_path, document_id, document_type)
            
            if not pdf_id:
                raise ValueError("Failed to store PDF in GridFS")
            
            # 5. Create basic document entry in MongoDB (without OCR data)
            import datetime
            from datetime import UTC
            
            now = datetime.datetime.now(UTC)
            
            # 6. Create document using document repository
            success = document_repository.create_document_from_pdf(
                document_id=document_id,
                document_type=document_type,
                pdf_filename=pdf_filename,
                pdf_id=pdf_id,
                now=now
            )
            
            if not success:
                raise ValueError("Failed to store document in database")
            
            # 7. Create a Document instance with minimal data and include PDF data
            return cls(
                document_id=document_id,
                document_type=document_type,
                ocr_json=[],  # Empty as OCR has not been performed
                pdf_filename=pdf_filename,
                pdf_file_id=pdf_id,
                pdf_upload_date=now,
                ocr_upload_date=None,
                images=[],
                processed=False,
                _id=None,
                db_manager=db_manager,
                document_repository=document_repository,
                pdf_data=pdf_data  # Include the PDF data
            )
            
        except Exception as e:
            logger.error(f"Error creating document from PDF {pdf_file}: {e}")
            raise ValueError(f"Failed to create document from PDF: {str(e)}")

    @classmethod
    def from_database(cls, document_id: str, db_manager: Optional[DBManager] = None, 
                     load_pdf_data: bool = False,
                     document_repository: Optional[DocumentRepository] = None) -> 'Document':
        """
        Create a Document instance from a document stored in the database.
        
        Args:
            document_id (str): The ID of the document to retrieve
            db_manager (DBManager, optional): Database manager instance
            load_pdf_data (bool): Whether to load the PDF data immediately
            document_repository (DocumentRepository, optional): Repository for document operations
            
        Returns:
            Document: The retrieved document instance
            
        Raises:
            ValueError: If the document cannot be found or retrieved
        """
        logger = logging.getLogger(__name__)
        
        # Initialize database manager if not provided
        if db_manager is None:
            db_manager = DBManager()
        
        # Initialize document repository if not provided
        if document_repository is None:
            document_repository = DocumentRepository(db_manager)
        
        try:
            # Retrieve the document from the database using document repository
            doc_data = document_repository.get_document(document_id)
            
            if not doc_data:
                raise ValueError(f"Document with ID {document_id} not found in database")
            
            # Retrieve associated images if they exist
            images = []
            if "image_file_ids" in doc_data and doc_data["image_file_ids"]:
                try:
                    # Get images collection
                    images_collection = db_manager.get_collection('images')
                    if images_collection is not None:
                        # Find all images associated with this document
                        cursor = images_collection.find({"_id": {"$in": doc_data["image_file_ids"]}})
                        for img_doc in cursor:
                            # Add image data to list
                            images.append({
                                "image_id": str(img_doc["_id"]),
                                "page_number": img_doc.get("page_number"),
                                "width": img_doc.get("width"),
                                "height": img_doc.get("height"),
                                "image_data": img_doc.get("image_data")
                            })
                except Exception as img_error:
                    logger.error(f"Error retrieving images for document {document_id}: {str(img_error)}")
            
            # Get OCR data if it exists
            ocr_json = []
            if "ocr_json" in doc_data and doc_data["ocr_json"]:
                ocr_json = doc_data["ocr_json"]
            
            # Get PDF data if requested
            pdf_data = None
            if load_pdf_data and doc_data.get("pdf_file_id"):
                try:
                    pdf_data = document_repository.get_pdf_from_gridfs(doc_data.get("pdf_file_id"))
                except Exception as pdf_error:
                    logger.warning(f"Failed to load PDF data for document {document_id}: {pdf_error}")
            
            # Extract document data
            return cls(
                document_id=doc_data["document_id"],
                document_type=doc_data.get("document_type", ""),
                ocr_json=ocr_json,
                pdf_filename=doc_data.get("pdf_filename", ""),
                pdf_file_id=doc_data.get("pdf_file_id", None),
                ocr_storage=doc_data.get("ocr_storage", None),
                pdf_upload_date=doc_data.get("pdf_upload_date"),
                ocr_upload_date=doc_data.get("ocr_upload_date"),
                images=images,
                processed=doc_data.get("processed", False),
                _id=doc_data.get("_id"),
                db_manager=db_manager,
                document_repository=document_repository,
                pdf_data=pdf_data,  # Include the PDF data if loaded
            )
            
        except Exception as e:
            logger.error(f"Error retrieving document {document_id} from database: {e}")
            raise ValueError(f"Failed to retrieve document from database: {str(e)}")

    def get_pdf_file(self) -> bytes:
        """
        Retrieves the PDF file associated with this document from GridFS.
        If the PDF data is already loaded, returns the cached version.
        
        Returns:
            bytes: The PDF file content as bytes
            
        Raises:
            ValueError: If the PDF file cannot be retrieved
        """
        logger = logging.getLogger(__name__)
        
        # Return cached PDF data if available
        if self._pdf_data is not None:
            return self._pdf_data
            
        try:
            if not self.pdf_file_id:
                raise ValueError(f"Document {self.document_id} has no associated PDF file ID")
            
            # Use document repository to retrieve the file
            pdf_data = self.document_repository.get_pdf_from_gridfs(self.pdf_file_id)
            
            if pdf_data is None:
                raise ValueError(f"Failed to retrieve PDF file with ID {self.pdf_file_id}")
            
            # Store the result for future access
            self._pdf_data = pdf_data
            return pdf_data
            
        except Exception as e:
            logger.error(f"Error retrieving PDF file for document {self.document_id}: {str(e)}")
            raise ValueError(f"Failed to retrieve PDF file: {str(e)}")

    def delete_document(self) -> bool:
        """
        Delete this document and all associated files (PDF, OCR, images) from the database.
        
        Returns:
            bool: True if document was deleted, False otherwise
            
        Raises:
            ValueError: If deletion fails for any reason
        """
        logger = logging.getLogger(__name__)
        
        try:
            # Use document repository to delete the document
            return self.document_repository.delete_document(
                document_id=self.document_id,
                pdf_file_id=self.pdf_file_id,
                ocr_file_id=self.ocr_storage == "gridfs" and getattr(self, 'ocr_file_id', None),
                image_file_ids=getattr(self, '_image_file_ids', None)
            )
            
        except Exception as e:
            logger.error(f"Error deleting document {self.document_id}: {str(e)}")
            raise ValueError(f"Failed to delete document: {str(e)}")

    def _serialise_ocr_result(self, obj):
        """
        Convert OCR result objects to serialisable dictionaries.
        """
        if hasattr(obj, '__dict__'):
            # For custom objects with __dict__ attribute
            result = {}
            for key, value in obj.__dict__.items():
                # Skip private attributes
                if not key.startswith('_'):
                    if isinstance(value, list):
                        result[key] = [self._serialise_ocr_result(item) for item in value]
                    else:
                        result[key] = self._serialise_ocr_result(value)
            return result
        elif isinstance(obj, list):
            return [self._serialise_ocr_result(item) for item in obj]
        elif isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        else:
            # For other types, convert to string
            return str(obj)
    
    def perform_ocr(self, ocr_client):
        """
        Perform OCR processing on the PDF document.
        """
        logger = logging.getLogger(__name__)
        
        try:
            # Check if document already has OCR data
            if self.processed and self.ocr_json:
                logger.info(f"Document {self.document_id} already has OCR data")
                return True
                
            # Get PDF data
            pdf_data = self.pdf_data
            if not pdf_data:
                raise ValueError(f"Cannot perform OCR: PDF data not available for document {self.document_id}")
            
            # Validate PDF data - check for null bytes
            if b'\x00' in pdf_data:
                raise ValueError("PDF contains embedded null bytes which may cause upload failures")
                
            # Validate PDF data is not empty and has proper PDF header
            if not pdf_data.startswith(b'%PDF-'):
                raise ValueError("Invalid PDF: File does not start with PDF header")
                
            # Step 1: Upload the PDF to OCR service
            logger.info(f"Uploading file: {self.pdf_filename}")
            try:
                uploaded_file = ocr_client.upload_pdf(pdf_data)
            except Exception as upload_error:
                raise ValueError(f"Failed to upload PDF: {str(upload_error)}")
                
            file_id = uploaded_file.id
            logger.info(f"File uploaded successfully. File ID: {file_id}")
            
            # Step 2: Get the signed URL using the file_id
            signed_url_response = ocr_client.get_signed_url(file_id)
            signed_url = signed_url_response.url
            logger.info(f"Retrieved signed URL for processing")
            
            # Step 3: Process OCR with the signed URL
            logger.info(f"Processing OCR for file: {self.pdf_filename}")
            ocr_result = ocr_client.ocr_pdf(signed_url)
            
            # Step 4: Serialise the OCR result pages
            serialised_pages = [self._serialise_ocr_result(page) for page in ocr_result.pages]
            
            # Step 5: Update document attributes (no DB writes)
            self.update_with_ocr_results(serialised_pages)
            self.extract_and_store_images(ocr_result)
            
            # Step 6: Identify question start index 
            try:
                question_index = self.identify_question_start_index()
                logger.info(f"Identified question start index: {question_index}")
            except Exception as e:
                logger.error(f"Error identifying question start index: {str(e)}")
            
            # Write all changes to database at once
            if not self.write_to_db():
                logger.error("Failed to write OCR results to database")
                return False
                
            return True
            
        except ValueError as ve:
            logger.error(f"Validation error for document {self.document_id}: {str(ve)}")
            raise
        except Exception as e:
            logger.error(f"Error performing OCR on document {self.document_id}: {str(e)}")
            return False

    def update_with_ocr_results(self, serialised_pages, ocr_storage='inline'):
        """
        Update document attributes with OCR results (no DB write).
        """
        logger = logging.getLogger(__name__)
        
        try:
            # Update instance attributes only
            self.ocr_json = serialised_pages
            self.ocr_storage = ocr_storage
            from datetime import UTC
            self.ocr_upload_date = datetime.now(UTC)
            self.processed = True
            
            logger.info(f"Document {self.document_id} attributes updated with OCR results")
            return True
            
        except Exception as e:
            logger.error(f"Error updating document attributes with OCR results: {str(e)}")
            return False
    
    def extract_and_store_images(self, ocr_result):
        """
        Extract images and store them in GridFS. Updates document attributes but doesn't write to DB.
        """
        logger = logging.getLogger(__name__)
        
        try:
            image_file_ids = []
            images_data = []
            
            # Process each page in OCR result
            for page_idx, page in enumerate(ocr_result.pages):
                if hasattr(page, 'images') and page.images:
                    for img_idx, img in enumerate(page.images):
                        if hasattr(img, 'image') and img.image:
                            # Create unique image ID
                            img_id = f"{self.document_id}_p{page_idx}_i{img_idx}"
                            
                            # Store image in GridFS using document repository
                            img_file_id = self.document_repository.store_binary_in_gridfs(
                                img.image,
                                filename=f"{img_id}.png",
                                content_type="image/png",
                                metadata={
                                    "document_id": self.document_id,
                                    "page_number": page_idx + 1,
                                    "image_index": img_idx
                                }
                            )
                            
                            if img_file_id:
                                image_file_ids.append(img_file_id)
                                images_data.append({
                                    "image_id": str(img_file_id),
                                    "page_number": page_idx + 1,
                                    "width": getattr(img, 'width', 0),
                                    "height": getattr(img, 'height', 0)
                                })
            
            # Update instance attributes only
            if image_file_ids:
                self.images = images_data
                self._image_file_ids = image_file_ids  # Store for database update
                logger.info(f"Document attributes updated with {len(image_file_ids)} images")
            
            return True
            
        except Exception as e:
            logger.error(f"Error extracting and storing images: {str(e)}")
            return False

    def identify_question_start_index(self) -> Optional[int]:
        """
        Identifies the index where questions begin in this document.
        """
        logger = logging.getLogger(__name__)
        
        llm_client = LLMClientFactory().create_client("mistral")
        
        # Validate document type
        if self.document_type not in ["Question Paper", "Mark Scheme"]:
            logger.warning(f"Cannot identify question start index for document type: {self.document_type}")
            return None
            
        # Check if we already have the index
        if self._question_start_index is not None:
            return self._question_start_index
            
        # Ensure we have OCR data
        if not self.ocr_json:
            logger.warning("Cannot identify question start index: No OCR data available")
            return None
            
        try:
            # Create a QuestionIndexIdentifier prompt for this document
            prompt = QuestionIndexIdentifier(self.document_type, self.ocr_json).get()
            
            # Send the prompt to the LLM client
            response = llm_client.generate_text(prompt)
            
            # Extract and set the index (setter will handle validation)
            try:
                # Clean the response by removing any non-digit characters
                cleaned_response = ''.join(char for char in response if char.isdigit())
                
                # Handle empty response
                if not cleaned_response:
                    raise ValueError("Could not extract a valid index number from LLM response")
                
                # Convert to integer and set (will be validated by setter)
                index = int(cleaned_response)
                self.question_start_index = index
                
            except ValueError as e:
                logger.error(f"Failed to parse question index: {str(e)}")
                return None
            
            # Write the updated document to the database using write_to_db()
            self.write_to_db()
            return self._question_start_index
        except Exception as e:
            logger.error(f"Failed to identify question start index: {str(e)}")
            return None

    def write_to_db(self) -> bool:
        """
        Write the current document state to the database.
        """
        logger = logging.getLogger(__name__)
        try:
            update_fields = {
                "document_id": self.document_id,
                "document_type": self.document_type,
                "pdf_filename": self.pdf_filename,
                "pdf_file_id": self.pdf_file_id,
                "ocr_json": self.ocr_json,
                "ocr_storage": self.ocr_storage,
                "pdf_upload_date": self._pdf_upload_date,
                "ocr_upload_date": self._ocr_upload_date,
                "images": self.images,
                "processed": self.processed,
                "question_start_index": self._question_start_index,
                "exam_id": self._exam_id,
            }
            
            # Add image_file_ids if they exist
            if hasattr(self, '_image_file_ids') and self._image_file_ids:
                update_fields["image_file_ids"] = self._image_file_ids
            
            # Use document repository to update the document
            success = self.document_repository.update_document(self.document_id, update_fields)
            
            if success:
                logger.info(f"Document {self.document_id} updated in database")
            else:
                logger.error(f"Failed to update document {self.document_id} in database")
                
            return success
            
        except Exception as e:
            logger.error(f"Error writing document {self.document_id} to database: {str(e)}")
            return False