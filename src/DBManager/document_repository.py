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

from src.DBManager.base_repository import BaseRepository

class DocumentRepository(BaseRepository):
    """
    Repository for document-related database operations.
    
    This class handles all database interactions for document objects,
    providing methods for saving, retrieving, and deleting documents.
    """
    
    def __init__(self):
        """
        Initialise the document repository.
        
        This class automatically uses the DBManager singleton instance from BaseRepository.
        """
        super().__init__(collection_name='documents')
        
    def check_document_exists(self, document_id: str) -> bool:
        """
        Check if a document with the given ID exists in the database.
        
        Args:
            document_id: The document ID (hash) to check
            
        Returns:
            bool: True if the document exists, False otherwise
        """
        return self.exists("document_id", document_id)
            
    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a document from the database by ID.
        
        Args:
            document_id: The document ID to retrieve
            
        Returns:
            dict: The document data or None if not found
        """
        return self.get_by_id("document_id", document_id)
            
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
        
        return self.create_or_update("document_id", document_id, document)
            
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
            doc_data = self.get_document(document_id)
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
            return self.delete("document_id", document_id)
            
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
        return self.update("document_id", document_id, update_fields)

    def store_binary_in_gridfs(self, binary_data, filename: str, content_type: str, metadata: Dict[str, Any]) -> Optional[str]:
        """
        Store binary data in GridFS.
        
        Args:
            binary_data: The binary data to store
            filename: Name to give the stored file
            content_type: MIME type of the content
            metadata: Additional metadata to store with the file
            
        Returns:
            str: The GridFS file ID or None if storage failed
        """
        try:
            return self.db_manager.store_binary_in_gridfs(
                binary_data,
                filename=filename,
                content_type=content_type,
                metadata=metadata
            )
        except Exception as e:
            self.logger.error(f"Error storing binary data in GridFS: {str(e)}")
            return None