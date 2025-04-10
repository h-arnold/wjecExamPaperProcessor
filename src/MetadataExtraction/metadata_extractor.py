"""
Metadata extraction module for exam paper content.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from Llm_client.base_client import LLMClient
from Prompting.prompt import Prompt


class MetadataExtractor:
    """
    Extracts structured metadata from exam paper content.
    
    This class uses an LLM client to extract metadata from OCR content
    and enriches it with additional information like file paths.
    """
    
    def __init__(self, llm_client: LLMClient):
        """
        Initialize the metadata extractor.
        
        Args:
            llm_client (LLMClient): An initialized LLM client
        """
        self.llm_client = llm_client
        # Load environment variables for configuration
        load_dotenv()
        self.max_index = int(os.getenv('MAX_INDEX_FOR_METADATA_SCANNING', '4'))
    
    def extract_metadata(self, ocr_content: Dict[str, Any], metadata_prompt: str) -> Dict[str, Any]:
        """
        Extract metadata from OCR content using the LLM client.
        
        Args:
            ocr_content (Dict[str, Any]): The OCR JSON content
            metadata_prompt (str): The prompt that guides metadata extraction
            
        Returns:
            Dict[str, Any]: Extracted metadata
            
        Raises:
            ValueError: If metadata extraction fails
        """
        # Extract the text content from OCR JSON
        text_content = self._extract_text_from_ocr(ocr_content)
        
        ## Combine the prompt.
        #  TODO: Make a metadata prompt class.

        prompt_contents = [text_content, "\n\n", metadata_prompt]
        metadata_prompt = Prompt(prompt_contents).get()
        
        
        try:
            # Use the LLM client to extract metadata
            metadata = self.llm_client.extract_metadata(metadata_prompt)
            
            # Validate the required fields
            self._validate_required_fields(metadata)
            
            return metadata
        except Exception as e:
            raise ValueError(f"Metadata extraction failed: {str(e)}")
    
    def _extract_text_from_ocr(self, ocr_content: Dict[str, Any]) -> str:
        """
        Extract text content from OCR JSON.
        
        Args:
            ocr_content (Dict[str, Any]): The OCR JSON content
            
        Returns:
            str: Extracted text content
            
        Raises:
            ValueError: If text content cannot be extracted
        """
        try:
            # Check if OCR content is in the expected array format with index and markdown
            if isinstance(ocr_content, list) and len(ocr_content) > 0 and "index" in ocr_content[0] and "markdown" in ocr_content[0]:
                # Extract text from each page up to the max index for metadata scanning
                text_content = ""
                for page in ocr_content:
                    if "index" in page and page["index"] <= self.max_index and "markdown" in page:
                        text_content += page["markdown"] + "\n\n"
                return text_content
            # Check if OCR content has pages structure
            elif "pages" in ocr_content:
                # Extract text from each page
                text_content = ""
                for page in ocr_content["pages"]:
                    if "text" in page:
                        text_content += page["text"] + "\n\n"
                return text_content
            # Check for simple text field
            elif "text" in ocr_content:
                # Simple format with just text field
                return ocr_content["text"]
            else:
                raise ValueError("Unexpected OCR content format")
        except Exception as e:
            raise ValueError(f"Failed to extract text from OCR content: {str(e)}")
    
    def _validate_required_fields(self, metadata: Dict[str, Any]):
        """
        Validate that metadata contains all required fields.
        
        Args:
            metadata (Dict[str, Any]): Metadata to validate
            
        Raises:
            ValueError: If any required field is missing
        """
        required_fields = [
            "Type", "Qualification", "Year", "Subject", 
            "Exam Paper", "Exam Season", "Exam Length"
        ]
        
        missing_fields = []
        for field in required_fields:
            if field not in metadata:
                missing_fields.append(field)
                
        if missing_fields:
            raise ValueError(f"Missing required metadata fields: {', '.join(missing_fields)}")
    
    def enrich_metadata(self, metadata: Dict[str, Any], file_path: str) -> Dict[str, Any]:
        """
        Add additional metadata like file path.
        
        Args:
            metadata (Dict[str, Any]): Extracted metadata
            file_path (str): Path to the OCR file
            
        Returns:
            Dict[str, Any]: Enriched metadata
        """
        # Make a copy to avoid modifying the original
        enriched = metadata.copy()
        
        # Add file path information
        enriched["FilePath"] = str(Path(file_path).absolute())
        
        return enriched