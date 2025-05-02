"""
File management module for the WJEC Exam Paper Processor.
Handles file I/O operations for OCR result files.
"""

import json
from pathlib import Path
from typing import Dict, Any, Union


class MetadataFileManager:
    """
    Manages file operations related to OCR results.
    
    This class handles reading OCR files and extracting document IDs.
    """
    
    def __init__(self):
        """
        Initialize the file manager.
        """
        pass
    
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