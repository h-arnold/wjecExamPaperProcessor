"""
File management module for the WJEC Exam Paper Processor.
Handles file I/O operations and organization of metadata files.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, Union


class MetadataFileManager:
    """
    Manages file operations related to OCR results and metadata.
    
    This class handles reading OCR files, writing metadata files,
    and organizing files based on document types (question papers vs mark schemes).
    """
    
    def __init__(self, 
                 base_dir: str = "metadata",
                 question_papers_dir: str = "question_papers",
                 mark_schemes_dir: str = "mark_schemes"):
        """
        Initialize the file manager.
        
        Args:
            base_dir (str): Base directory for metadata files
            question_papers_dir (str): Subdirectory for question paper metadata
            mark_schemes_dir (str): Subdirectory for mark scheme metadata
        """
        self.base_dir = Path(base_dir)
        self.question_papers_dir = self.base_dir / question_papers_dir
        self.mark_schemes_dir = self.base_dir / mark_schemes_dir
        
        # Create directories if they don't exist
        self._create_directories()
        
    def _create_directories(self):
        """Create necessary directory structure if it doesn't exist."""
        self.base_dir.mkdir(exist_ok=True)
        self.question_papers_dir.mkdir(exist_ok=True)
        self.mark_schemes_dir.mkdir(exist_ok=True)
    
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
    
    def get_metadata_path(self, document_id: str, document_type: str) -> Path:
        """
        Generate the appropriate path for a metadata file.
        
        Args:
            document_id (str): Unique identifier for the document
            document_type (str): Type of document ('Question Paper' or 'Mark Scheme')
            
        Returns:
            Path: Path object for the metadata file
            
        Raises:
            ValueError: If document_type is invalid
        """
        if document_type == "Question Paper":
            return self.question_papers_dir / f"{document_id}-metadata.json"
        elif document_type == "Mark Scheme":
            return self.mark_schemes_dir / f"{document_id}-metadata.json"
        else:
            raise ValueError(f"Invalid document type: {document_type}")
    
    def save_metadata(self, metadata: Dict[str, Any], document_id: str) -> Path:
        """
        Save metadata to individual JSON file based on document type.
        
        Args:
            metadata (Dict[str, Any]): Metadata to save
            document_id (str): Unique identifier for the document
            
        Returns:
            Path: Path where the metadata was saved
            
        Raises:
            KeyError: If metadata doesn't contain 'Type' field
            ValueError: If document type is invalid
        """
        if "Type" not in metadata:
            raise KeyError("Metadata must contain 'Type' field")
            
        document_type = metadata["Type"]
        file_path = self.get_metadata_path(document_id, document_type)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            return file_path
        except Exception as e:
            raise IOError(f"Failed to save metadata to {file_path}: {str(e)}")
    
    def get_metadata(self, document_id: str, document_type: str) -> Optional[Dict[str, Any]]:
        """
        Read metadata from file.
        
        Args:
            document_id (str): Unique identifier for the document
            document_type (str): Type of document ('Question Paper' or 'Mark Scheme')
            
        Returns:
            Dict[str, Any] or None: Parsed metadata or None if file doesn't exist
            
        Raises:
            json.JSONDecodeError: If the file contains invalid JSON
        """
        file_path = self.get_metadata_path(document_id, document_type)
        
        if not file_path.exists():
            return None
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(
                f"Failed to parse metadata file {file_path}: {str(e)}",
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