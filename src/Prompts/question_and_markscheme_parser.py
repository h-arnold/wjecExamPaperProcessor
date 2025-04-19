from pathlib import Path
from typing import List, Optional, Union, Dict, Any
import json
from .base_prompt import Prompt


class QuestionAndMarkschemeParser(Prompt):
    """
    A specialized prompt class for generating prompts that combine question paper
    and mark scheme content for parsing.

    This class takes question paper JSON, mark scheme JSON, and relevant indices
    to construct a prompt for extracting structured data.
    """

    # Default location of the prompt template
    TEMPLATE_PATH = Path(__file__).parent.parent / "Prompts" / "MarkdownPrompts" / "questionAndMarkschemeParserPrompt.md"

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