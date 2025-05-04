"""
File management module for the WJEC Exam Paper Processor.
Handles file I/O operations for OCR result files.
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Union, Optional, BinaryIO


class FileManager:
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