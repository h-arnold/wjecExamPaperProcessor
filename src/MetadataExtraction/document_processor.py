"""
Document processor module for coordinating the end-to-end processing pipeline.

This module integrates the various components of the system to process
exam documents, extract metadata, and manage the document index.
"""

import os
import glob
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from Llm_client.base_client import LLMClient
from MetadataExtraction.metadata_extractor import MetadataExtractor
from MetadataExtraction.file_manager import MetadataFileManager
from MetadataExtraction.index_manager import IndexManager


class DocumentProcessor:
    """
    Coordinates the end-to-end processing of exam documents.
    
    This class integrates the various components of the system to:
    - Process OCR files
    - Extract metadata
    - Save metadata files
    - Update the document index
    - Find related documents
    """
    
    def __init__(self, 
                 llm_client: LLMClient,
                 file_manager: Optional[MetadataFileManager] = None,
                 index_manager: Optional[IndexManager] = None,
                 metadata_prompt_path: Optional[str] = None):
        """
        Initialize the document processor.
        
        Args:
            llm_client (LLMClient): An initialized LLM client
            file_manager (MetadataFileManager, optional): File manager
            index_manager (IndexManager, optional): Index manager
            metadata_prompt_path (str, optional): Path to the metadata extraction prompt
        """
        self.llm_client = llm_client
        self.file_manager = file_manager or MetadataFileManager()
        self.index_manager = index_manager or IndexManager()
        self.metadata_extractor = MetadataExtractor(llm_client)
        
        # Load metadata prompt if provided
        if metadata_prompt_path:
            self.metadata_prompt = Path(metadata_prompt_path).read_text(encoding='utf-8')
        else:
            # Default to looking in a standard location
            default_prompt_path = Path("src/Prompts/metadataCreator.md")
            if default_prompt_path.exists():
                self.metadata_prompt = default_prompt_path.read_text(encoding='utf-8')
            else:
                raise ValueError("Metadata prompt not found. Please provide a valid path.")
    
    def process_document(self, ocr_file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Process a single document end-to-end.
        
        This method:
        1. Reads the OCR file
        2. Extracts metadata using LLM
        3. Enriches metadata with file path
        4. Saves metadata to file
        5. Updates the document index
        
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
        
        # Read OCR file
        ocr_content = self.file_manager.read_ocr_file(ocr_file_path)
        
        # Extract metadata
        metadata = self.metadata_extractor.extract_metadata(ocr_content, self.metadata_prompt)
        
        # Enrich metadata with file path
        enriched_metadata = self.metadata_extractor.enrich_metadata(metadata, str(ocr_file_path))
        
        # Save metadata to file
        metadata_file_path = self.file_manager.save_metadata(enriched_metadata, document_id)
        
        # Update document index
        index_entry = self.index_manager.update_index(
            metadata=enriched_metadata,
            content_path=str(ocr_file_path),
            metadata_path=str(metadata_file_path)
        )
        
        # Find related documents
        related_docs = self.index_manager.find_related_documents(document_id)
        
        # Return result
        return {
            "document_id": document_id,
            "metadata": enriched_metadata,
            "metadata_path": str(metadata_file_path),
            "index_entry": index_entry,
            "related_documents": related_docs
        }
    
    def process_directory(self, 
                         directory_path: Union[str, Path], 
                         pattern: str = "*.json") -> List[Dict[str, Any]]:
        """
        Process all matching documents in a directory.
        
        Args:
            directory_path (str or Path): Path to directory containing OCR files
            pattern (str): Glob pattern for matching OCR files
            
        Returns:
            List[Dict[str, Any]]: Results for all processed documents
        """
        directory_path = Path(directory_path)
        results = []
        
        # Find all matching files
        file_paths = list(directory_path.glob(pattern))
        
        if not file_paths:
            print(f"No files matching pattern '{pattern}' found in {directory_path}")
            return results
            
        # Process each file
        for file_path in file_paths:
            try:
                result = self.process_document(file_path)
                results.append(result)
                print(f"Successfully processed {file_path}")
            except Exception as e:
                print(f"Error processing {file_path}: {str(e)}")
                
        return results
    
    def find_related_documents(self, document_id: str) -> List[Dict[str, Any]]:
        """
        Find related documents for a given document ID.
        
        Args:
            document_id (str): The document ID to find relations for
            
        Returns:
            List[Dict[str, Any]]: List of related documents
        """
        return self.index_manager.find_related_documents(document_id)