"""
Document repository for WJEC Exam Paper Processor.

This module provides a repository for document operations, separating
database access logic from the Document domain model.
"""

import logging
import datetime
from datetime import UTC
from typing import Dict, Any, List, Optional
from pathlib import Path

from src.DBManager.db_manager import DBManager

class DocumentRepository:
    """
    Repository for document-related database operations.
    
    This class handles all database interactions for document objects,
    providing methods for saving, retrieving, and deleting documents.
    """
    
    def __init__(self, db_manager: DBManager):
        """
        Initialise the document repository with a database manager instance.
        
        Args:
            db_manager: The database manager to use for database operations
        """
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
        self.document_collection = self.db_manager.get_collection('documents')
        
    def check_document_exists(self, document_id: str) -> bool:
        """
        Check if a document with the given ID exists in the database.
        
        Args:
            document_id: The document ID (hash) to check
            
        Returns:
            bool: True if the document exists, False otherwise
        """
        try:
            if self.document_collection is None:
                return False
                
            # Count documents matching the ID (limit to 1 for efficiency)
            count = self.document_collection.count_documents({"document_id": document_id}, limit=1)
            return count > 0
            
        except Exception as e:
            # Log the error but return False rather than raising an exception
            self.logger.error(f"Error checking if document exists: {str(e)}")
            return False
            
    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a document from the database by ID.
        
        Args:
            document_id: The document ID to retrieve
            
        Returns:
            dict: The document data or None if not found
        """
        try:
            if self.document_collection is None:
                self.logger.error("Failed to access documents collection")
                return None
            
            # Retrieve the document from the database
            return self.document_collection.find_one({"document_id": document_id})
            
        except Exception as e:
            self.logger.error(f"Error retrieving document {document_id} from database: {e}")
            return None
            
    def create_document_from_pdf(self, document_id: str, document_type: str, 
                               pdf_filename: str, pdf_id: str, now: datetime.datetime) -> bool:
        """
        Create a new document record in the database.
        
        Args:
            document_id: The document ID (hash)
            document_type: Type of document ('Question Paper' or 'Mark Scheme')
            pdf_filename: Original filename of the PDF
            pdf_id: GridFS file ID of the stored PDF
            now: Timestamp for PDF upload date
            
        Returns:
            bool: True if creation was successful, False otherwise
        """
        try:
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
            
            # Store in documents collection
            if self.document_collection is None:
                self.logger.error("Failed to access documents collection")
                return False
                
            result = self.document_collection.update_one(
                {'document_id': document_id},
                {'$set': document},
                upsert=True
            )
            
            return bool(result.upserted_id or result.modified_count > 0)
            
        except Exception as e:
            self.logger.error(f"Error creating document record: {str(e)}")
            return False
            
    def store_pdf_in_gridfs(self, pdf_path: Path, document_id: str, document_type: str) -> Optional[str]:
        """
        Store a PDF file in GridFS.
        
        Args:
            pdf_path: Path to the PDF file
            document_id: The document ID (hash)
            document_type: Type of document
            
        Returns:
            str: The GridFS file ID or None if storage failed
        """
        try:
            # Store PDF in GridFS
            return self.db_manager.store_file_in_gridfs(
                pdf_path, 
                content_type="application/pdf",
                filename=pdf_path.name,
                metadata={"document_id": document_id, "document_type": document_type}
            )
        except Exception as e:
            self.logger.error(f"Error storing PDF in GridFS: {str(e)}")
            return None
            
    def get_pdf_from_gridfs(self, pdf_file_id: str) -> Optional[bytes]:
        """
        Retrieve a PDF file from GridFS.
        
        Args:
            pdf_file_id: The GridFS file ID
            
        Returns:
            bytes: The PDF file content or None if retrieval failed
        """
        try:
            if not pdf_file_id:
                raise ValueError("No PDF file ID provided")
                
            return self.db_manager.get_file_from_gridfs(pdf_file_id)
            
        except Exception as e:
            self.logger.error(f"Error retrieving PDF from GridFS: {str(e)}")
            return None
            
    def delete_document(self, document_id: str, pdf_file_id: Optional[str] = None, 
                      ocr_file_id: Optional[str] = None, image_file_ids: Optional[List] = None) -> bool:
        """
        Delete a document and all associated files from the database.
        
        Args:
            document_id: The document ID to delete
            pdf_file_id: Optional PDF file ID to delete from GridFS
            ocr_file_id: Optional OCR file ID to delete from GridFS
            image_file_ids: Optional list of image file IDs to delete from GridFS
            
        Returns:
            bool: True if document was deleted, False otherwise
        """
        try:
            # Verify document exists
            if self.document_collection is None:
                self.logger.error("Failed to access documents collection")
                return False
                
            doc_data = self.document_collection.find_one({"document_id": document_id})
            if not doc_data:
                self.logger.warning(f"Document with ID {document_id} not found in database")
                return False
            
            # Delete PDF file from GridFS
            if pdf_file_id:
                self.db_manager.delete_file_from_gridfs(pdf_file_id)
                self.logger.info(f"Deleted PDF file with ID {pdf_file_id}")
            
            # Delete OCR data from GridFS if stored there
            if ocr_file_id:
                self.db_manager.delete_file_from_gridfs(ocr_file_id)
                self.logger.info(f"Deleted OCR file with ID {ocr_file_id}")

            # Delete image files from GridFS
            if image_file_ids:
                for img_id in image_file_ids:
                    self.db_manager.delete_file_from_gridfs(img_id)
                    self.logger.info(f"Deleted image file with ID {img_id}")
            
            # Delete the document record
            result = self.document_collection.delete_one({"document_id": document_id})
            
            deleted = result.deleted_count > 0
            if deleted:
                self.logger.info(f"Successfully deleted document {document_id} from database")
            else:
                self.logger.warning(f"Document {document_id} was not deleted from database")
            
            return deleted
            
        except Exception as e:
            self.logger.error(f"Error deleting document {document_id}: {str(e)}")
            return False
            
    def update_document(self, document_id: str, update_fields: Dict[str, Any]) -> bool:
        """
        Update a document in the database.
        
        Args:
            document_id: The document ID to update
            update_fields: Dictionary of fields to update
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            if self.document_collection is None:
                self.logger.error("Failed to access documents collection")
                return False
                
            result = self.document_collection.update_one(
                {"document_id": document_id},
                {"$set": update_fields},
                upsert=True
            )
            
            success = result.upserted_id is not None or result.modified_count > 0
            if success:
                self.logger.info(f"Document {document_id} updated successfully")
            else:
                self.logger.info(f"No changes made to document {document_id} (state already up-to-date)")
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating document {document_id}: {str(e)}")
            return False