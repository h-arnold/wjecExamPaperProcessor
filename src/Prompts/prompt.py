from pathlib import Path
from typing import List, Optional, Union, Dict, Any
import os
import json
from json_repair import repair_json


class Prompt:
    """
    A class to construct a prompt by concatenating a set of strings or markdown files.

    Attributes:
        sources (List[str]):
            A list of strings to be concatenated into a prompt.

    """

    def __init__(self, sources: List[str]):
        """
        Initialise the Prompt object.

        Args:
            sources (Dict[str, Union[str, Path]]):
                Dictionary with values that are either literal strings or paths to markdown files.
        """
        self.sources = sources
        self._prompt = self._build_prompt()

    def _build_prompt(self) -> str:
        """
        Process the list and concatenate all text contents in order.

        Returns:
            str: The concatenated prompt text.
        """
        prompt_parts = []

        for value in self.sources:
            if not isinstance(value, str):
                raise ValueError(f"Error: '{value}' is not a string. All entries in the list must be strings.")
            prompt_parts.append(value.strip())

        return "\n\n".join(prompt_parts)

    def get(self) -> str:
        """
        Retrieve the concatenated prompt string.

        Returns:
            str: The final combined prompt.
        """
        return self._prompt

    def __str__(self):
        return self.get()


class MetadataPrompt(Prompt):
    """
    A specialized prompt class for metadata extraction from scanned document content.
    
    This class properly formats a document's text content with the metadata extraction prompt
    template loaded from the standard template file location.
    """
    
    # Default location of the metadata prompt template
    TEMPLATE_PATH = Path(__file__).parent.parent / "Prompts" / "MarkdownPrompts" / "metadataCreator.md"
    
    def __init__(self, text_content: str, template_path: Optional[Union[str, Path]] = None):
        """
        Initialize the MetadataPrompt with document text.
        
        Args:
            text_content (str): The extracted text content from a document
            template_path (Optional[Union[str, Path]]): Override the default template path
                                                      Default: None (use standard location)
        """
        # Use the provided template path or the default one
        template_path = Path(template_path) if template_path else self.TEMPLATE_PATH
        
        # Check if the template file exists
        if not template_path.exists():
            raise FileNotFoundError(f"Metadata prompt template not found at: {template_path}")
        
        # Load the template content
        with open(template_path, 'r', encoding='utf-8') as file:
            metadata_prompt_template = file.read()
        
        # Format the prompt with proper sections and spacing
        sources = [
            "# Scanned Document \n\n",
            text_content.strip(),
            "\n\n",
            metadata_prompt_template.strip()
        ]
        
        # Initialize the parent class with the formatted sources
        super().__init__(sources)


class QuestionIndexIdentifier(Prompt):
    """
    A specialized prompt class for identifying the index where questions begin in exam documents.
    
    This class formats the document content with the question index identification prompt template
    and extracts the appropriate portion of the document based on the document type.
    """
    
    # Default location of the prompt template
    TEMPLATE_PATH = Path(__file__).parent.parent / "Prompts" / "MarkdownPrompts" / "identifyIndexForQuestions.md"
    
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


class QuestionAndMarkschemeParser(Prompt):
    """
    A specialized prompt class for generating prompts that combine question paper
    and mark scheme content for parsing.

    This class takes question paper JSON, mark scheme JSON, and relevant indices
    to construct a prompt for extracting structured data.
    """

    # Default location of the prompt template
    TEMPLATE_PATH = Path(__file__).parent / "MarkdownPrompts" / "questionAndMarkschemeParserPrompt.md"

    def __init__(self, params: Dict[str, Any], template_path: Optional[Union[str, Path]] = None):
        """
        Initialize the QuestionAndMarkschemeParser with necessary parameters.

        Args:
            params (Dict[str, Any]): A dictionary containing:
                - 'question_paper_content': JSON content of the question paper.
                - 'mark_scheme_content': JSON content of the mark scheme.
                - 'question_start_index': Index where questions start in the paper.
                - 'mark_scheme_start_index': Index where the mark scheme starts.
                - 'current_question_number' (int, optional): The question number to start from (default: 1).
                - 'current_question_paper_index' (int, optional): Index in question paper (default: question_start_index).
                - 'current_mark_scheme_index' (int, optional): Index in mark scheme (default: mark_scheme_start_index).
            template_path (Optional[Union[str, Path]]): Override the default template path.
                                                      Default: None (use standard location).
        """
        # Validate required parameters
        required_keys = ['question_paper_content', 'mark_scheme_content', 'question_start_index', 'mark_scheme_start_index']
        if not all(key in params for key in required_keys):
            missing_keys = [key for key in required_keys if key not in params]
            raise ValueError(f"Missing required parameters: {', '.join(missing_keys)}")

        self.params = params

        # Set defaults for optional parameters
        self.current_question_number = params.get('current_question_number', 1)
        self.current_qp_index = params.get('current_question_paper_index', params['question_start_index'])
        self.current_ms_index = params.get('current_mark_scheme_index', params['mark_scheme_start_index'])

        # Use the provided template path or the default one
        template_path = Path(template_path) if template_path else self.TEMPLATE_PATH

        # Check if the template file exists
        if not template_path.exists():
            raise FileNotFoundError(f"Question and Mark Scheme parser template not found at: {template_path}")

        # Load the template content
        with open(template_path, 'r', encoding='utf-8') as file:
            parser_template = file.read()

        # Extract content from question paper and mark scheme
        qp_content_md = self._extract_markdown_content(params['question_paper_content'], self.current_qp_index)
        ms_content_md = self._extract_markdown_content(params['mark_scheme_content'], self.current_ms_index)

        # Format the prompt
        sources = [
            "## Question Paper Content\n\n```markdown\n",
            qp_content_md,
            "\n```\n\n---\n\n## Mark Scheme Content\n\n```markdown\n",
            ms_content_md,
            "\n```\n\n---\n\n",
            parser_template.strip(),
            "\n\n---\n\n",
            f"Please continue from question number {self.current_question_number}."
        ]

        # Initialize the parent class with the formatted sources
        # Note: The base Prompt class expects a List[str], not Dict
        super().__init__(sources)

    def _extract_markdown_content(self, content_json: List[Dict[str, Any]], start_index: int) -> str:
        """
        Extracts markdown content from the specified index and the next index, if available.

        Args:
            content_json (List[Dict[str, Any]]): The JSON content (list of page objects).
            start_index (int): The starting index to extract from.

        Returns:
            str: The combined markdown content from the specified pages.
                 Returns an error message if the index is invalid or content is missing.
        """
        extracted_parts = []
        max_index = len(content_json) - 1

        # Ensure content_json is a list
        if not isinstance(content_json, list):
            return f"Error: Expected a list of page objects, but received {type(content_json)}."

        # Extract from start_index
        if 0 <= start_index <= max_index:
            page = content_json[start_index]
            if isinstance(page, dict) and "markdown" in page:
                extracted_parts.append(f"--- Page Index: {start_index} ---\n{page['markdown'].strip()}")
            else:
                 extracted_parts.append(f"Error: Content at index {start_index} is not in the expected format or missing 'markdown' key.")
        else:
            extracted_parts.append(f"Error: Start index {start_index} is out of bounds (0-{max_index}).")

        # Extract from start_index + 1
        next_index = start_index + 1
        if 0 <= next_index <= max_index:
            next_page = content_json[next_index]
            if isinstance(next_page, dict) and "markdown" in next_page:
                 extracted_parts.append(f"--- Page Index: {next_index} ---\n{next_page['markdown'].strip()}")
            # No error message if next page format is wrong, just skip it.
        # No error message if next_index is out of bounds, just means no next page.


        if not extracted_parts:
             return f"Error: No valid markdown content found at or after index {start_index}."

        return "\n\n".join(extracted_parts)
