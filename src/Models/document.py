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
    """
    
    def __init__(
        self,
        document_id: str,
        file_name: str,
        document_type: str,
        ocr_pages: List[Dict[str, Any]],
        file_path: Optional[str] = None,
        images: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        processed: bool = False,
        created_at: datetime = None,
        updated_at: datetime = None,
        _id: Optional[ObjectId] = None
    ):
        """
        Initialise a Document object.
        
        Args:
            document_id (str): Unique identifier for the document (hash of PDF file)
            file_name (str): Original filename of the PDF
            document_type (str): Type of document ('Question Paper' or 'Mark Scheme')
            ocr_pages (List[Dict]): List of serialized OCR result pages
            file_path (str, optional): Path to the original file on disk, if available
            images (List[Dict], optional): List of images extracted from the document
            metadata (Dict, optional): Additional metadata about the document
            processed (bool): Flag indicating if the document has been fully processed
            created_at (datetime, optional): Timestamp when document was first created
            updated_at (datetime, optional): Timestamp when document was last updated
            _id (ObjectId, optional): MongoDB ObjectId
        """
        self.document_id = document_id
        self.file_name = file_name
        self.document_type = document_type
        self.ocr_pages = ocr_pages
        self.file_path = file_path
        self.images = images or []
        self.metadata = metadata or {}
        self.processed = processed
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
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

    @classmethod
    def from_pdf(cls, pdf_file: Union[str, Path], document_type: str = None, 
                 ocr_client = None, db_manager: Optional[DBManager] = None, 
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
            if file_manager.check_document_exists(document_id):
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
                file_name=pdf_filename,
                document_type=document_type,
                ocr_pages=[],  # Empty as OCR has not been performed
                file_path=str(pdf_path),
                images=[],
                processed=False,
                created_at=now,
                updated_at=now
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
                file_name=doc_data.get("pdf_filename", ""),
                document_type=doc_data.get("document_type", ""),
                ocr_pages=doc_data.get("ocr_json", []),
                images=doc_data.get("images", []),
                processed=doc_data.get("processed", False),
                created_at=doc_data.get("pdf_upload_date"),
                updated_at=doc_data.get("ocr_upload_date"),
                _id=doc_data.get("_id")
            )
            
        except Exception as e:
            logger.error(f"Error retrieving document {document_id} from database: {e}")
            raise ValueError(f"Failed to retrieve document from database: {str(e)}")