"""
Metadata extraction module for exam paper content.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

from src.Llm_client.base_client import LLMClient


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
    
    def extract_metadata(self, ocr_content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metadata from OCR content using the LLM client.
        
        Args:
            ocr_content (Dict[str, Any]): The OCR JSON content
            metadata_prompt (str, optional): Optional custom metadata prompt text to use instead of loading
                                           the default template. Default: None (use standard template)
            
        Returns:
            Dict[str, Any]: Extracted metadata
            
        Raises:
            ValueError: If metadata extraction fails
        """
        # Extract the text content from OCR JSON
        text_content = self._extract_text_from_ocr(ocr_content)
        
        # Create a metadata prompt using our specialized class
        from src.Prompts.prompt import MetadataPrompt
        formatted_prompt = MetadataPrompt(text_content).get()
        
        try:
            # Use the LLM client to extract metadata
            metadata = self.llm_client.extract_metadata(formatted_prompt)
            
            # Check for missing fields and retry if needed
            missing_fields = self._validate_required_fields(metadata, raise_error=False)
            if missing_fields:
                # Try one more time with a targeted retry prompt
                metadata = self._retry_metadata_extraction(metadata, text_content, missing_fields)
            
            # Validate the required fields after final attempt
            self._validate_required_fields(metadata)
            
            return metadata
        except Exception as e:
            raise ValueError(f"Metadata extraction failed: {str(e)}")
    
    def identify_question_start_index(self, document_path: str, document_type: str) -> int:
        """
        Identifies the index where questions begin in a given document.
        
        Args:
            document_path (str): Path to the OCR JSON document file
            document_type (str): Type of document, either "Question Paper" or "Mark Scheme"
            
        Returns:
            int: The index where questions start
            
        Raises:
            ValueError: If the index cannot be determined or is invalid
        """
        from src.Prompts.prompt import QuestionIndexIdentifier
        
        # Validate document type
        if document_type not in ["Question Paper", "Mark Scheme"]:
            raise ValueError(f"Invalid document type: {document_type}. Must be 'Question Paper' or 'Mark Scheme'")
            
        # Create a QuestionIndexIdentifier prompt for this document
        prompt = QuestionIndexIdentifier(document_type, document_path).get()
        
        try:
            # Send the prompt to the LLM client
            response = self.llm_client.generate_text(prompt)
            
            # Clean and validate the response
            return self._validate_question_index_response(response)
        except Exception as e:
            raise ValueError(f"Failed to identify question start index: {str(e)}")
    
    def _validate_question_index_response(self, response: str) -> int:
        """
        Validates and extracts an integer index from the LLM response.
        
        Args:
            response (str): The raw response from the LLM
            
        Returns:
            int: The validated index
            
        Raises:
            ValueError: If the response cannot be parsed as a valid index
        """
        # Clean the response by removing any non-digit characters
        cleaned_response = ''.join(char for char in response if char.isdigit())
        
        # Handle empty response
        if not cleaned_response:
            raise ValueError("Could not extract a valid index number from LLM response")
        
        try:
            # Convert to integer
            index = int(cleaned_response)
            
            # Validate the index is reasonable (not negative and not too large)
            if index < 0 or index > 10:  # 10 is a reasonable upper limit for question indices
                raise ValueError(f"Extracted index {index} is outside reasonable range (0-100)")
                
            return index
        except ValueError as e:
            raise ValueError(f"Failed to parse question index: {str(e)}")
    
    def _retry_metadata_extraction(self, initial_metadata: Dict[str, Any], 
                                 text_content: str, 
                                 missing_fields: List[str]) -> Dict[str, Any]:
        """
        Retry metadata extraction with a targeted prompt focusing on missing fields.
        
        Args:
            initial_metadata (Dict[str, Any]): The initially extracted metadata with missing fields
            text_content (str): The original text content
            missing_fields (List[str]): List of missing required fields
            
        Returns:
            Dict[str, Any]: The updated metadata after retry
        """
        # Create a specific retry prompt that includes the original results and what's missing
        retry_prompt_text = (
            f"You previously extracted the following metadata from an exam paper:\n"
            f"{json.dumps(initial_metadata, indent=2)}\n\n"
            f"However, the following required fields are missing or incomplete: {', '.join(missing_fields)}\n"
            f"Please analyze the text again and return a COMPLETE JSON object with ALL required fields filled in.\n"
            f"Focus especially on finding the missing information. Required fields are: "
            f"Type, Qualification, Year, Subject, Exam Paper, Exam Season, Exam Length.\n\n"
            f"Original text content:\n{text_content}"
        )
        
        # Create a prompt object for the retry
        from src.Prompts.prompt import Prompt
        retry_prompt = Prompt(retry_prompt_text)
        
        # Try again with the enhanced prompt
        retry_metadata = self.llm_client.extract_metadata(retry_prompt.get())
        
        # Merge the results, preferring the new extraction but keeping any old fields that might be lost
        for key, value in initial_metadata.items():
            if key not in retry_metadata and value:  # Keep any non-empty values from the original
                retry_metadata[key] = value
                
        return retry_metadata
    
    def _validate_required_fields(self, metadata: Dict[str, Any], raise_error: bool = True) -> Optional[List[str]]:
        """
        Validate that metadata contains all required fields.
        
        Args:
            metadata (Dict[str, Any]): Metadata to validate
            raise_error (bool, optional): Whether to raise an error if fields are missing. Default: True
            
        Returns:
            Optional[List[str]]: List of missing field names if raise_error is False, None otherwise
            
        Raises:
            ValueError: If any required field is missing and raise_error is True
        """
        required_fields = [
            "Type", "Qualification", "Year", "Subject", 
            "Exam Paper", "Exam Season"
        ]
        
        missing_fields = []
        for field in required_fields:
            if field not in metadata or not metadata[field]:
                missing_fields.append(field)
        
        if missing_fields and raise_error:
            raise ValueError(f"Missing required metadata fields: {', '.join(missing_fields)}")
        
        return missing_fields if not raise_error else None
    
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
                # Extract text only from the first self.max_index pages
                text_content = ""
                max_pages = min(self.max_index, len(ocr_content))
                for i in range(max_pages):
                    if "markdown" in ocr_content[i]:
                        text_content += ocr_content[i]["markdown"] + "\n\n"
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