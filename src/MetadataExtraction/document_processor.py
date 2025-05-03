"""
Document processor module for coordinating the end-to-end processing pipeline.

This module integrates the various components of the system to process
exam documents, extract metadata, and manage the document index.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from src.Llm_client.base_client import LLMClient
from src.MetadataExtraction.metadata_extractor import MetadataExtractor
from src.FileManager.file_manager import FileManager
from src.DBManager.db_manager import DBManager


class DocumentProcessor:
    """
    Coordinates the end-to-end processing of exam documents.
    
    This class integrates the various components of the system to:
    - Process OCR files
    - Extract metadata using LLM
    - Store metadata in MongoDB
    - Find related documents
    """
    
    def __init__(self, 
                 llm_client: LLMClient,
                 file_manager: Optional[FileManager] = None,
                 db_manager: DBManager = None,
                 mongodb_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the document processor.
        
        Args:
            llm_client (LLMClient): An initialized LLM client
            file_manager (MetadataFileManager, optional): File manager for reading OCR files
            db_manager (DBManager): Database manager for storing metadata
            mongodb_config (Dict[str, Any], optional): MongoDB configuration options
        
        Raises:
            ValueError: If no valid database manager is provided or can be created
        """
        self.llm_client = llm_client
        self.file_manager = file_manager or FileManager()
        
        # Handle the DBManager creation with proper config
        if db_manager is not None:
            self.db_manager = db_manager
        elif mongodb_config is not None:
            # Extract config values and pass them as individual parameters
            try:
                self.db_manager = DBManager(
                    connection_string=mongodb_config.get("connection_string"),
                    database_name=mongodb_config.get("database_name"),
                    timeout_ms=mongodb_config.get("timeout_ms")
                )
            except Exception as e:
                error_msg = f"Cannot connect to MongoDB: {e}"
                print(f"Error: {error_msg}")
                raise ValueError(error_msg)
        else:
            # DBManager is now required - no default creation
            raise ValueError("DBManager is required. Provide either a db_manager instance or mongodb_config.")
            
        self.metadata_extractor = MetadataExtractor(llm_client)
        
    
    def process_document(self, ocr_file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Process a single document end-to-end.
        
        This method:
        1. Reads the OCR file
        2. Extracts metadata using LLM
        3. Identifies question start index
        4. Enriches metadata with file path and question index
        5. Stores metadata in MongoDB
        
        Args:
            ocr_file_path (str or Path): Path to the OCR JSON file
            
        Returns:
            Dict[str, Any]: Processed document metadata and related info
            
        Raises:
            FileNotFoundError: If OCR file is not found
            ValueError: If metadata extraction fails
        """
        ocr_file_path = Path(ocr_file_path)
        document_id = self.file_manager.extract_document_id(ocr_file_path)
        
        # Check if document exists in MongoDB
        if self.db_manager.exam_exists(document_id):
            print(f"Document {document_id} already exists in MongoDB, retrieving metadata")
            mongodb_metadata = self.db_manager.get_exam_metadata(document_id)
            if mongodb_metadata:
                return {
                    "document_id": document_id,
                    "metadata": mongodb_metadata,
                    "source": "mongodb",
                    "status": "existing"
                }
        
        # Read OCR file
        ocr_content = self.file_manager.read_ocr_file(ocr_file_path)
        
        # Extract metadata
        metadata = self.metadata_extractor.extract_metadata(ocr_content)
        
        # Identify question start index if document type is available
        if "Type" in metadata and metadata["Type"] in ["Question Paper", "Mark Scheme"]:
            try:
                question_start_index = self.metadata_extractor.identify_question_start_index(
                    str(ocr_file_path), 
                    metadata["Type"]
                )
                # Add question start index to metadata
                metadata["QuestionStartIndex"] = question_start_index
            except Exception as e:
                print(f"Warning: Could not identify question start index: {str(e)}")
        
        # Enrich metadata with file path
        enriched_metadata = self.metadata_extractor.enrich_metadata(metadata, str(ocr_file_path))
        
        # Create response object
        result = {
            "document_id": document_id,
            "metadata": enriched_metadata
        }
        
        try:
            # Convert the metadata to ensure it is MongoDB-compatible
            db_metadata = self._prepare_metadata_for_db(enriched_metadata)
            # Save to MongoDB
            saved_id = self.db_manager.save_exam_metadata(db_metadata, document_id)
            result["mongodb_id"] = saved_id
            result["stored_in_db"] = True
        except Exception as e:
            error_msg = f"Error storing metadata in MongoDB: {str(e)}"
            print(error_msg)
            result["stored_in_db"] = False
            result["db_error"] = str(e)
            raise ValueError(error_msg)
        
        return result
    
    def process_directory(self, 
                         directory_path: Union[str, Path], 
                         pattern: str = "*.json",
                         batch_size: int = 20) -> List[Dict[str, Any]]:
        """
        Process all matching documents in a directory.
        
        Args:
            directory_path (str or Path): Path to directory containing OCR files
            pattern (str): Glob pattern for matching OCR files
            batch_size (int): Size of batches for bulk operations
            
        Returns:
            List[Dict[str, Any]]: Results for all processed documents
        """
        directory_path = Path(directory_path)
        
        # Find all matching files
        file_paths = list(directory_path.glob(pattern))
        
        if not file_paths:
            print(f"No files matching pattern '{pattern}' found in {directory_path}")
            return []
        
        # Process files in batches for MongoDB
        return self._process_directory_with_mongodb(file_paths, batch_size)
    
    def _prepare_metadata_for_db(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert metadata to ensure it is MongoDB-compatible.
        
        Args:
            metadata (Dict[str, Any]): The metadata to be prepared for MongoDB storage
            
        Returns:
            Dict[str, Any]: MongoDB-compatible metadata
        """
        # Create a new dict to avoid modifying the original
        db_metadata = metadata.copy()
        
        # Map the original metadata fields to required MongoDB fields
        field_mappings = {
            'Subject': 'subject',
            'Qualification': 'qualification',
            'Year': 'year',
            'Exam Season': 'season',
            'Exam Paper': 'unit',
            'Type': 'paper_type',
            'Exam Board': 'exam_board'
        }
        
        # Apply mappings to standard fields
        for orig_field, db_field in field_mappings.items():
            if orig_field in db_metadata and db_field not in db_metadata:
                db_metadata[db_field] = db_metadata[orig_field]
        
        # Ensure we have the required fields
        required_fields = ['subject', 'qualification', 'year', 'season', 'unit']
        for field in required_fields:
            if field not in db_metadata:
                # Try to derive the field from other metadata if possible
                if field == 'year' and 'Date' in db_metadata:
                    # Try to extract year from date
                    import re
                    year_match = re.search(r'20\d\d', db_metadata['Date'])
                    if year_match:
                        db_metadata['year'] = int(year_match.group(0))
                elif field == 'unit' and 'Exam Paper' in db_metadata:
                    # Extract unit information from Exam Paper field
                    db_metadata['unit'] = db_metadata['Exam Paper']
                    
        # Ensure year is an integer
        if 'year' in db_metadata and isinstance(db_metadata['year'], str):
            try:
                db_metadata['year'] = int(db_metadata['year'])
            except ValueError:
                pass  # Keep as string if conversion fails
                
        return db_metadata
    
    def _process_directory_with_mongodb(self, 
                                file_paths: List[Path],
                                batch_size: int = 20) -> List[Dict[str, Any]]:
        """
        Process directory using MongoDB bulk operations for better performance.
        
        Args:
            file_paths (List[Path]): List of file paths to process
            batch_size (int): Number of documents to process in each batch
            
        Returns:
            List[Dict[str, Any]]: Results for all processed documents
        """
        results = []
        total_files = len(file_paths)
        processed = 0
        
        # Process files in batches
        for i in range(0, total_files, batch_size):
            batch_files = file_paths[i:i+batch_size]
            batch_metadata = []
            document_ids = []
            batch_results = []
            
            print(f"Processing batch {i//batch_size + 1}/{(total_files-1)//batch_size + 1} ({len(batch_files)} files)")
            
            # First, check which documents already exist in MongoDB
            for file_path in batch_files:
                try:
                    document_id = self.file_manager.extract_document_id(file_path)
                    document_ids.append(document_id)
                    
                    # Check if document already exists in MongoDB
                    if self.db_manager.exam_exists(document_id):
                        # Retrieve existing document
                        mongodb_metadata = self.db_manager.get_exam_metadata(document_id)
                        batch_results.append({
                            "document_id": document_id,
                            "metadata": mongodb_metadata,
                            "source": "mongodb",
                            "status": "existing"
                        })
                    else:
                        # Document needs processing
                        batch_results.append(None)  # Placeholder for later
                except Exception as e:
                    print(f"Error checking document existence: {str(e)}")
                    batch_results.append({
                        "document_id": document_id if 'document_id' in locals() else "unknown",
                        "error": str(e),
                        "status": "error"
                    })
            
            # Process documents that don't exist yet
            new_metadata_list = []
            new_document_ids = []
            new_indices = []
            
            for i, (file_path, result) in enumerate(zip(batch_files, batch_results)):
                if result is None:  # Need to process this document
                    try:
                        # Extract metadata but don't save to DB yet
                        document_id = document_ids[i]
                        ocr_content = self.file_manager.read_ocr_file(file_path)
                        metadata = self.metadata_extractor.extract_metadata(ocr_content)
                        
                        # Process question start index
                        if "Type" in metadata and metadata["Type"] in ["Question Paper", "Mark Scheme"]:
                            try:
                                question_start_index = self.metadata_extractor.identify_question_start_index(
                                    str(file_path), 
                                    metadata["Type"]
                                )
                                metadata["QuestionStartIndex"] = question_start_index
                            except Exception as e:
                                print(f"Warning: Could not identify question start index: {str(e)}")
                        
                        # Enrich metadata
                        enriched_metadata = self.metadata_extractor.enrich_metadata(metadata, str(file_path))
                        
                        # Convert for MongoDB and add to batch
                        db_metadata = self._prepare_metadata_for_db(enriched_metadata)
                        new_metadata_list.append(db_metadata)
                        new_document_ids.append(document_id)
                        new_indices.append(i)
                        
                    except Exception as e:
                        print(f"Error processing {file_path}: {str(e)}")
                        batch_results[i] = {
                            "document_id": document_ids[i],
                            "error": str(e),
                            "status": "error"
                        }
            
            # Bulk save to MongoDB if we have new items
            if new_metadata_list:
                try:
                    saved_ids = self.db_manager.bulk_save_exam_metadata(new_metadata_list, new_document_ids)
                    
                    # Update results with saved information
                    for j, idx in enumerate(new_indices):
                        metadata = new_metadata_list[j]
                        document_id = new_document_ids[j]
                        
                        result = {
                            "document_id": document_id,
                            "metadata": metadata,
                            "stored_in_db": True,
                            "mongodb_id": saved_ids[j],
                            "status": "new"
                        }
                        
                        batch_results[idx] = result
                        
                except Exception as e:
                    print(f"Error during bulk save to MongoDB: {str(e)}")
                    # Update all new documents with the error
                    for idx in new_indices:
                        if batch_results[idx] is None:
                            batch_results[idx] = {
                                "document_id": document_ids[idx],
                                "error": f"Bulk save error: {str(e)}",
                                "status": "error"
                            }
            
            # Add batch results to overall results
            for result in batch_results:
                if result is not None:
                    results.append(result)
            
            processed += len(batch_files)
            print(f"Processed {processed}/{total_files} files ({processed/total_files*100:.1f}%)")
            
        return results