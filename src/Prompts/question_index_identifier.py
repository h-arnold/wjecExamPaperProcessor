from pathlib import Path
from typing import Optional, Union, Dict, Any, List
import os
import json

from .base_prompt import Prompt


class QuestionIndexIdentifier(Prompt):
    """
    A specialized prompt class for identifying the index where questions begin in exam documents.
    
    This class formats the document content with the question index identification prompt template
    and extracts the appropriate portion of the document based on the document type.
    """
    
    # Default location of the prompt template
    TEMPLATE_PATH = Path(__file__).parent / "MarkdownPrompts" / "identifyIndexForQuestions.md"
    
    def __init__(self, document_type: str, document_contents: Union[str, Dict[str, Any]], template_path: Optional[Union[str, Path]] = None):
        """
        Initialize the QuestionIndexIdentifier with the document type and content.
        
        Args:
            document_type (str): The type of document ("Question Paper" or "Mark Scheme")
            document_contents (Union[str, Dict[str, Any]]): The path to the document file or the OCR content
            template_path (Optional[Union[str, Path]]): Override the default template path
                                                      Default: None (use standard location)
        """
        self.document_type = document_type
        
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()
        
        # Get environment variables for the maximum index based on document type
        self.max_index_mark_scheme = int(os.getenv('MAX_INDEX_FOR_FIRST_QUESTION_IN_MARKSCHEME', '5'))
        self.max_index_question_paper = int(os.getenv('MAX_INDEX_FOR_FIRST_QUESTION_IN_QUESTION_PAPER', '5'))
        
        # Load document contents if a string path was provided
        if isinstance(document_contents, str) and Path(document_contents).exists():
            with open(document_contents, 'r', encoding='utf-8') as file:
                self.ocr_content = json.load(file)
        else:
            self.ocr_content = document_contents
        
        # Use the provided template path or the default one
        template_path = Path(template_path) if template_path else self.TEMPLATE_PATH
        
        # Check if the template file exists
        if not template_path.exists():
            raise FileNotFoundError(f"Question index identification template not found at: {template_path}")
        
        # Load the template content
        with open(template_path, 'r', encoding='utf-8') as file:
            question_index_template = file.read()
        
        # Extract text based on document type
        extracted_text = self._extract_text_for_question_index()
        
        # Format the prompt with proper sections and spacing
        sources = [
            "# Scanned Document JSON Content\n\n```json\n",
            json.dumps(extracted_text, indent=2),
            "```\n\n",
            question_index_template.strip()
        ]
        
        # Initialize the parent class with the formatted sources
        super().__init__(sources)
    
    def _extract_text_for_question_index(self) -> List[Dict[str, Any]]:
        """
        Extract text content from OCR JSON based on document type.
        
        Returns:
            List[Dict[str, Any]]: Extracted content limited to relevant pages
        """
        # Determine the maximum index to use based on document type
        max_index = self.max_index_mark_scheme if self.document_type == "Mark Scheme" else self.max_index_question_paper
        
        # Extract text from the first few pages (starting from index 1, not 0)
        extracted_content = []
        
        # Check if OCR content is in the expected array format
        if isinstance(self.ocr_content, list) and len(self.ocr_content) > 1:
            # Start from index 1 (skip cover page) and go up to max_index
            end_index = min(max_index + 1, len(self.ocr_content))
            for i in range(1, end_index):
                if i < len(self.ocr_content) and "markdown" in self.ocr_content[i]:
                    extracted_content.append({
                        "index": i,
                        "markdown": self.ocr_content[i]["markdown"]
                    })
        
        return extracted_content