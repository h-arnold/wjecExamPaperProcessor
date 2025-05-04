from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from bson import ObjectId
from pathlib import Path
import logging

from src.FileManager.file_manager import FileManager
from src.DBManager.db_manager import DBManager

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
        _id: Optional[ObjectId] = None
    ):
        """
        Initialise a Document object.
        
        Args:
            document_id (str): Unique identifier for the document (hash of PDF file)
            document_type (str): Type of document ('Question Paper' or 'Mark Scheme')
            pdf_filename (str): Original filename of the PDF
            pdf_file_id (str): GridFS file ID of the stored PDF
            ocr_json (List[Dict], optional): List of serialized OCR result pages
            ocr_storage (str, optional): Storage type for OCR data (e.g. 'inline')
            pdf_upload_date (datetime, optional): Timestamp when PDF was uploaded
            ocr_upload_date (datetime, optional): Timestamp when OCR was completed
            images (List[Dict], optional): List of images extracted from the document
            processed (bool): Flag indicating if the document has been fully processed
            _id (ObjectId, optional): MongoDB ObjectId
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
        self._id = _id

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
        
        # Default to Unknown if no pattern matches
        else:
            return "Unknown"

    @staticmethod
    def check_document_exists(document_id: str, db_manager: Optional[DBManager] = None) -> bool:
        """
        Check if a document with the given ID exists in the database.
        
        Args:
            document_id: The document ID (hash) to check
            db_manager: Optional DBManager instance to use for database operations
            
        Returns:
            bool: True if the document exists, False otherwise
        """
        # Initialise DB manager if not provided
        if db_manager is None:
            db_manager = DBManager()
            
        try:
            collection = db_manager.get_collection('documents')
            if collection is None:
                return False
                
            # Count documents matching the ID (limit to 1 for efficiency)
            count = collection.count_documents({"document_id": document_id}, limit=1)
            return count > 0
            
        except Exception as e:
            # Log the error but return False rather than raising an exception
            logging.error(f"Error checking if document exists: {str(e)}")
            return False

    @classmethod
    def from_pdf(cls, pdf_file: Union[str, Path], document_type: str = None, 
                 db_manager: Optional[DBManager] = None, 
                 file_manager: Optional[FileManager] = None) -> 'Document':
        """
        Create a Document instance from a PDF file, without OCR processing.
        
        This method hashes the PDF file, checks if it exists in the database,
        and if not, uploads it to GridFS. OCR processing must be performed separately.
        
        Args:
            pdf_file (str or Path): Path to the PDF file
            document_type (str, optional): Type of document ('Question Paper' or 'Mark Scheme')
                                          If None, will be determined from filename
            ocr_client: OCR client instance (not used in this method, but accepted for compatibility)
            db_manager (DBManager, optional): Database manager instance
            file_manager (FileManager, optional): File manager instance
            
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
            file_manager = FileManager(db_manager)
        
        try:
            # Convert to Path object
            pdf_path = Path(pdf_file)
            
            # 1. Generate document_id (hash) for the PDF file
            document_id = file_manager.get_file_hash(pdf_path)
            logger.info(f"Generated document ID (hash): {document_id}")
            
            # 2. Check if document already exists in the database
            if cls.check_document_exists(document_id, db_manager):
                logger.info(f"Document with ID {document_id} already exists in the database")
                return cls.from_database(document_id, db_manager, file_manager)
            
            # 3. Determine document type if not provided
            pdf_filename = pdf_path.name
            if document_type is None:
                document_type = cls._determine_document_type(pdf_filename)
                if document_type == "Unknown":
                    logger.warning(f"Could not determine document type for {pdf_filename}, setting to 'Unknown'")
            
            # 4. Store PDF in GridFS
            pdf_id = db_manager.store_file_in_gridfs(
                pdf_path, 
                content_type="application/pdf",
                filename=pdf_filename,
                metadata={"document_id": document_id, "document_type": document_type}
            )
            
            if not pdf_id:
                raise ValueError("Failed to store PDF in GridFS")
            
            # 5. Create basic document entry in MongoDB (without OCR data)
            import datetime
            from datetime import UTC
            
            now = datetime.datetime.now(UTC)
            document = {
                "document_id": document_id,
                "document_type": document_type,
                "pdf_file_id": pdf_id,
                "pdf_filename": pdf_filename,
                "pdf_upload_date": now,
                "ocr_storage": None,
                "ocr_upload_date": None,
                "images": [],
                "processed": False
            }
            
            # 6. Store in documents collection
            collection = db_manager.get_collection('documents')
            result = collection.update_one(
                {'document_id': document_id},
                {'$set': document},
                upsert=True
            )
            
            if not (result.upserted_id or result.modified_count > 0):
                raise ValueError("Failed to store document in database")
            
            # 7. Create a Document instance with minimal data
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
                _id=None
            )
            
        except Exception as e:
            logger.error(f"Error creating document from PDF {pdf_file}: {e}")
            raise ValueError(f"Failed to create document from PDF: {str(e)}")

    @classmethod
    def from_database(cls, document_id: str, db_manager: Optional[DBManager] = None, 
                     file_manager: Optional[FileManager] = None) -> 'Document':
        """
        Create a Document instance from a document stored in the database.
        
        Args:
            document_id (str): The ID of the document to retrieve
            db_manager (DBManager, optional): Database manager instance
            file_manager (FileManager, optional): File manager instance
            
        Returns:
            Document: The retrieved document instance
            
        Raises:
            ValueError: If the document cannot be found or retrieved
        """
        logger = logging.getLogger(__name__)
        
        # Initialize managers if not provided
        if db_manager is None:
            db_manager = DBManager()
        if file_manager is None:
            file_manager = FileManager(db_manager)
        
        try:
            # Retrieve the document from the database
            doc_data = file_manager.get_document_with_images(document_id)
            
            if not doc_data:
                raise ValueError(f"Document with ID {document_id} not found in database")
            
            # Extract document data
            return cls(
                document_id=doc_data["document_id"],
                document_type=doc_data.get("document_type", ""),
                ocr_json=doc_data.get("ocr_json", []),
                pdf_filename=doc_data.get("pdf_filename", ""),
                pdf_file_id=doc_data.get("pdf_file_id", None),
                ocr_storage=doc_data.get("ocr_storage", None),
                pdf_upload_date=doc_data.get("pdf_upload_date"),
                ocr_upload_date=doc_data.get("ocr_upload_date"),
                images=doc_data.get("images", []),
                processed=doc_data.get("processed", False),
                _id=doc_data.get("_id")
            )
            
        except Exception as e:
            logger.error(f"Error retrieving document {document_id} from database: {e}")
            raise ValueError(f"Failed to retrieve document from database: {str(e)}")