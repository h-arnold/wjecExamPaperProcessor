"""
File management module for the WJEC Exam Paper Processor.
Handles file I/O operations for OCR result files.
"""

import json
import hashlib
import datetime
from datetime import UTC
from pathlib import Path
from typing import Dict, Any, Union, Optional, BinaryIO

# Import the DBManager class
from src.DBManager.db_manager import DBManager


class FileManager:
    """
    Manages file operations related to OCR results.
    
    This class handles reading OCR files and extracting document IDs.
    """
    
    def __init__(self, db_manager: Optional[DBManager] = None):
        """
        Initialize the file manager.
        
        Args:
            db_manager: Optional DBManager instance for database operations.
                       If not provided, a new instance will be created when needed.
        """
        self.db_manager = db_manager
    
    def read_ocr_file(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Read and parse OCR JSON file.
        
        Args:
            file_path (str or Path): Path to the OCR JSON file
            
        Returns:
            Dict[str, Any]: Parsed OCR content
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            json.JSONDecodeError: If the file contains invalid JSON
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"OCR file not found: {file_path}")
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(
                f"Failed to parse OCR file {file_path}: {str(e)}",
                e.doc, e.pos
            )
            
    def extract_document_id(self, ocr_file_path: Union[str, Path]) -> str:
        """
        Extract document ID from OCR file path.
        
        Args:
            ocr_file_path (str or Path): Path to the OCR JSON file
            
        Returns:
            str: Extracted document ID
        """
        file_path = Path(ocr_file_path)
        return file_path.stem  # Get filename without extension

    def get_file_hash(self, data: Union[bytes, str, Dict, Path, BinaryIO]) -> str:
        """
        Generate a SHA-256 hash for the given data.
        
        Args:
            data: The data to hash. Can be bytes, string, dictionary, file path, or file-like object.
            
        Returns:
            str: The hex digest of the SHA-256 hash
            
        Raises:
            TypeError: If the data type is unsupported
            IOError: If there is an error reading a file
        """
        sha256 = hashlib.sha256()
        
        try:
            if isinstance(data, bytes):
                # Data is already bytes
                sha256.update(data)
            elif isinstance(data, str):
                # String data
                sha256.update(data.encode('utf-8'))
            elif isinstance(data, dict):
                # Dictionary/JSON data - convert to sorted JSON string first
                sha256.update(json.dumps(data, sort_keys=True).encode('utf-8'))
            elif isinstance(data, Path) or isinstance(data, str) and Path(data).exists():
                # File path
                path = Path(data) if isinstance(data, str) else data
                with open(path, 'rb') as f:
                    # Read file in chunks to handle large files
                    for chunk in iter(lambda: f.read(4096), b''):
                        sha256.update(chunk)
            elif hasattr(data, 'read') and callable(data.read):
                # File-like object
                # Save current position
                pos = data.tell()
                # Reset to beginning
                data.seek(0)
                # Read file in chunks
                for chunk in iter(lambda: data.read(4096), b''):
                    if isinstance(chunk, str):
                        sha256.update(chunk.encode('utf-8'))
                    else:
                        sha256.update(chunk)
                # Restore position
                data.seek(pos)
            else:
                raise TypeError(f"Unsupported data type for hashing: {type(data)}")
                
            return sha256.hexdigest()
            
        except Exception as e:
            if isinstance(data, Path):
                raise IOError(f"Error hashing file {data}: {str(e)}")
            else:
                raise IOError(f"Error generating hash: {str(e)}")
    
    def add_document_to_db(self, 
                          pdf_file: Union[bytes, Path, str, BinaryIO], 
                          ocr_json_output: Dict[str, Any], 
                          document_type: str,
                          pdf_filename: Optional[str] = None, 
                          ocr_filename: Optional[str] = None) -> Optional[str]:
        """
        Add a document to the MongoDB database.
        
        Args:
            pdf_file: The PDF file as bytes, path, or file-like object
            ocr_json_output: The OCR JSON output
            document_type: Type of document (e.g., "Question Paper", "Mark Scheme")
            pdf_filename: Optional name of the PDF file
            ocr_filename: Optional name of the OCR output file
            
        Returns:
            str: The document ID (hash) if successful, None otherwise
            
        Raises:
            ValueError: If the PDF file or OCR output is invalid
        """
        # Ensure we have a DB manager
        if self.db_manager is None:
            self.db_manager = DBManager()
            
        # Generate document ID (hash) from PDF
        try:
            document_id = self.get_file_hash(pdf_file)
        except Exception as e:
            raise ValueError(f"Failed to hash PDF file: {str(e)}")
            
        # Prepare PDF binary data
        if isinstance(pdf_file, bytes):
            pdf_binary = pdf_file
        elif isinstance(pdf_file, (str, Path)):
            path = Path(pdf_file)
            with open(path, 'rb') as f:
                pdf_binary = f.read()
            # Use filename from path if not specified
            if pdf_filename is None:
                pdf_filename = path.name
        elif hasattr(pdf_file, 'read') and callable(pdf_file.read):
            # File-like object
            pos = pdf_file.tell()
            pdf_file.seek(0)
            pdf_binary = pdf_file.read()
            pdf_file.seek(pos)
        else:
            raise ValueError(f"Unsupported PDF file type: {type(pdf_file)}")
            
        # Get current timestamp
        now = datetime.datetime.now(UTC)
            
        # Create document
        document = {
            "document_id": document_id,
            "document_type": document_type,
            "pdf_binary": pdf_binary,
            "pdf_filename": pdf_filename,
            "pdf_upload_date": now,
            "ocr_json": ocr_json_output,
            "ocr_filename": ocr_filename,
            "ocr_upload_date": now
        }
        
        # Store in database
        try:
            collection = self.db_manager.get_collection('documents')
            if collection is None:
                raise ValueError("Failed to connect to MongoDB")
                
            # Insert or update document
            result = collection.update_one(
                {'document_id': document_id},
                {'$set': document},
                upsert=True
            )
            
            if result.upserted_id or result.modified_count > 0:
                return document_id
            else:
                raise ValueError("Failed to store document in database")
                
        except Exception as e:
            raise ValueError(f"Error storing document in database: {str(e)}")
            
    def get_document_from_db(self, 
                           document_id: str, 
                           include_ocr_json: bool = True,
                           include_pdf: bool = False) -> Optional[Dict[str, Any]]:
        """
        Retrieve a document from the MongoDB database.
        
        Args:
            document_id: The document ID (hash) to retrieve
            include_ocr_json: Whether to include the OCR JSON output
            include_pdf: Whether to include the PDF binary data
            
        Returns:
            Dict: Document data if found, None otherwise
            
        Raises:
            ValueError: If the document ID is invalid or database connection fails
        """
        # Ensure we have a DB manager
        if self.db_manager is None:
            self.db_manager = DBManager()
            
        try:
            collection = self.db_manager.get_collection('documents')
            if collection is None:
                raise ValueError("Failed to connect to MongoDB")
                
            # Build projection to include/exclude fields
            projection = {
                "_id": 0,
                "document_id": 1,
                "document_type": 1,
                "pdf_filename": 1,
                "pdf_upload_date": 1,
                "ocr_filename": 1,
                "ocr_upload_date": 1
            }
            
            if include_ocr_json:
                projection["ocr_json"] = 1
                
            if include_pdf:
                projection["pdf_binary"] = 1
                
            # Query document
            document = collection.find_one(
                {"document_id": document_id},
                projection
            )
            
            return document
            
        except Exception as e:
            raise ValueError(f"Error retrieving document from database: {str(e)}")