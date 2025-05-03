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
    
    def _process_ocr_images(self, ocr_result):
        """
        Process OCR result to extract images and decide storage strategy.
        
        Args:
            ocr_result: The OCR result containing pages with images
        
        Returns:
            tuple: (processed_ocr_result, image_references)
        """

        import json
        
        MAX_INLINE_SIZE = 500 * 1024  # 500KB
        image_refs = []
        
        # Create a deep copy to avoid modifying the original
        processed_ocr = json.loads(json.dumps(ocr_result))
        
        # Process each page in the OCR result
        for page_idx, page in enumerate(processed_ocr):
            if 'images' in page and page['images']:
                for img_idx, img in enumerate(page['images']):
                    if 'image_base64' in img and img['image_base64']:
                        # Extract image data
                        img_data = img['image_base64']
                        if ',' in img_data:
                            format_part, base64_data = img_data.split(',', 1)
                            img_format = format_part.split(';')[0].split('/')[1]
                        else:
                            base64_data = img_data
                            img_format = 'jpeg'
                        
                        # Estimate size
                        decoded_size = (len(base64_data) * 3) // 4
                        
                        # Generate unique image ID
                        image_id = f"img_p{page_idx}_{img_idx}"
                        
                        # Create image reference
                        image_ref = {
                            "image_id": image_id,
                            "page": page_idx,
                            "index": img_idx,
                            "format": img_format,
                            "size_bytes": decoded_size
                        }
                        
                        # Handle based on size
                        if decoded_size <= MAX_INLINE_SIZE:
                            # Small image - store inline
                            image_ref["storage"] = "inline"
                            image_ref["data"] = base64_data
                        else:
                            # Large image - store in GridFS
                            image_ref["storage"] = "gridfs"
                            # We'll store the actual image data later when saving the document
                            image_ref["_temp_data"] = base64_data
                        
                        # Update reference in OCR result
                        img["image_id"] = image_id
                        del img["image_base64"]
                        
                        # Add to image references
                        image_refs.append(image_ref)
        
        return processed_ocr, image_refs

    def add_document_to_db_with_images(self, pdf_file, ocr_result, document_type):
        """
        Store PDF, OCR results and all images in MongoDB using hybrid approach.
        
        Args:
            pdf_file: The PDF file as bytes, path, or file-like object
            ocr_result: The OCR result containing text and images
            document_type: Type of document (e.g., "Question Paper", "Mark Scheme")
            
        Returns:
            str: The document ID if successful, None otherwise
        """
        import json
        import base64
        import datetime
        from datetime import UTC
        
        # Ensure we have a DB manager
        if self.db_manager is None:
            self.db_manager = DBManager()
        
        try:
            # 1. Generate document ID (hash) from PDF
            document_id = self.get_file_hash(pdf_file)
            
            # 2. Get filename if pdf_file is a path
            pdf_filename = None
            if isinstance(pdf_file, (str, Path)):
                pdf_path = Path(pdf_file)
                pdf_filename = pdf_path.name
            
            # 3. Store PDF in GridFS
            pdf_id = self.db_manager.store_file_in_gridfs(
                pdf_file, 
                content_type="application/pdf",
                filename=pdf_filename,
                metadata={"document_id": document_id, "document_type": document_type}
            )
            
            if not pdf_id:
                raise ValueError("Failed to store PDF in GridFS")
            
            # 4. Process OCR result to extract and handle images
            processed_ocr, image_refs = self._process_ocr_images(ocr_result)
            
            # 5. Decide whether to store OCR inline or in GridFS
            ocr_json_str = json.dumps(processed_ocr)
            ocr_size = len(ocr_json_str.encode('utf-8'))
            
            if ocr_size > 5 * 1024 * 1024:  # 5MB threshold
                # Store OCR in GridFS
                ocr_id = self.db_manager.store_file_in_gridfs(
                    ocr_json_str.encode('utf-8'), 
                    content_type="application/json",
                    filename=f"{document_id}_ocr.json",
                    metadata={"document_id": document_id}
                )
                if not ocr_id:
                    raise ValueError("Failed to store OCR JSON in GridFS")
                ocr_storage = "gridfs"
            else:
                # Store OCR inline
                ocr_id = None
                ocr_storage = "inline"
            
            # 6. Store large images in GridFS
            for img_ref in image_refs:
                if img_ref.get("storage") == "gridfs" and "_temp_data" in img_ref:
                    # Get image data from temporary storage
                    img_data = img_ref["_temp_data"]
                    img_format = img_ref.get("format", "jpeg")
                    
                    # Store in GridFS
                    file_id = self.db_manager.store_file_in_gridfs(
                        base64.b64decode(img_data),
                        content_type=f"image/{img_format}",
                        filename=f"{document_id}_{img_ref['image_id']}.{img_format}",
                        metadata={
                            "document_id": document_id,
                            "image_id": img_ref["image_id"],
                            "page": img_ref["page"],
                            "index": img_ref["index"]
                        }
                    )
                    
                    if not file_id:
                        raise ValueError(f"Failed to store image {img_ref['image_id']} in GridFS")
                    
                    # Update image reference with GridFS file ID
                    img_ref["file_id"] = file_id
                    del img_ref["_temp_data"]
            
            # 7. Create main document
            now = datetime.datetime.now(UTC)
            document = {
                "document_id": document_id,
                "document_type": document_type,
                "pdf_file_id": pdf_id,
                "pdf_filename": pdf_filename,
                "pdf_upload_date": now,
                "ocr_storage": ocr_storage,
                "ocr_upload_date": now,
                "images": image_refs
            }
            
            # Add OCR data based on storage method
            if ocr_storage == "inline":
                document["ocr_json"] = processed_ocr
            else:
                document["ocr_file_id"] = ocr_id
            
            # 8. Store in documents collection
            collection = self.db_manager.get_collection('documents')
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
            raise ValueError(f"Error storing document with images: {str(e)}")

    def get_document_with_images(self, document_id):
        """
        Retrieve a document with its images from the database.
        
        This method fetches the document and all associated images, retrieving
        GridFS files as needed.
        
        Args:
            document_id: The ID of the document to retrieve
            
        Returns:
            dict: The document with its OCR data and images
        """
        import pymongo
        import base64
        
        # Ensure we have a DB manager
        if self.db_manager is None:
            self.db_manager = DBManager()
        
        try:
            # 1. Get the document from MongoDB
            collection = self.db_manager.get_collection('documents')
            if collection is None:
                raise ValueError("Failed to connect to MongoDB")
            
            document = collection.find_one({"document_id": document_id})
            
            if not document:
                raise ValueError(f"Document with ID {document_id} not found")
            
            # 2. Get OCR data from GridFS if necessary
            if document.get("ocr_storage") == "gridfs" and "ocr_file_id" in document:
                try:
                    ocr_file = self.db_manager.get_file_from_gridfs(document["ocr_file_id"])
                    if ocr_file:
                        import json
                        document["ocr_json"] = json.loads(ocr_file.read().decode('utf-8'))
                except Exception as e:
                    raise ValueError(f"Failed to retrieve OCR data from GridFS: {str(e)}")
            
            # 3. Get image data from GridFS if necessary
            if "images" in document:
                for img_ref in document["images"]:
                    if img_ref.get("storage") == "gridfs" and "file_id" in img_ref:
                        try:
                            img_file = self.db_manager.get_file_from_gridfs(img_ref["file_id"])
                            if img_file:
                                # Read binary data and convert to base64
                                img_data = base64.b64encode(img_file.read()).decode('utf-8')
                                # Add the data to the image reference
                                img_ref["data"] = img_data
                        except Exception as e:
                            # Log error but continue with other images
                            print(f"Failed to retrieve image {img_ref['image_id']} from GridFS: {str(e)}")
            
            return document
            
        except Exception as e:
            raise ValueError(f"Error retrieving document with images: {str(e)}")

    def delete_document_with_images(self, document_id):
        """
        Delete a document and all associated files (PDF, OCR, images) from the database.
        
        Args:
            document_id: The ID of the document to delete
            
        Returns:
            bool: True if document was deleted, False otherwise
        """
        # Ensure we have a DB manager
        if self.db_manager is None:
            self.db_manager = DBManager()
        
        try:
            # 1. Get the document from MongoDB to find associated files
            collection = self.db_manager.get_collection('documents')
            if collection is None:
                raise ValueError("Failed to connect to MongoDB")
            
            document = collection.find_one({"document_id": document_id})
            
            if not document:
                return False  # Document not found
            
            # 2. Delete PDF file from GridFS
            if "pdf_file_id" in document:
                self.db_manager.delete_file_from_gridfs(document["pdf_file_id"])
            
            # 3. Delete OCR data from GridFS if stored there
            if document.get("ocr_storage") == "gridfs" and "ocr_file_id" in document:
                self.db_manager.delete_file_from_gridfs(document["ocr_file_id"])
            
            # 4. Delete image files from GridFS
            if "images" in document:
                for img_ref in document["images"]:
                    if img_ref.get("storage") == "gridfs" and "file_id" in img_ref:
                        self.db_manager.delete_file_from_gridfs(img_ref["file_id"])
            
            # 5. Delete the document itself
            result = collection.delete_one({"document_id": document_id})
            
            return result.deleted_count > 0
            
        except Exception as e:
            raise ValueError(f"Error deleting document with images: {str(e)}")