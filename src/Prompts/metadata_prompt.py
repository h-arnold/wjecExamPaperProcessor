from pathlib import Path
from typing import Optional, Union

from .base_prompt import Prompt


class MetadataPrompt(Prompt):
    """
    A specialized prompt class for metadata extraction from scanned document content.
    
    This class properly formats a document's text content with the metadata extraction prompt
    template loaded from the standard template file location.
    """
    
    # Default location of the metadata prompt template
    TEMPLATE_PATH = Path(__file__).parent / "MarkdownPrompts" / "metadataCreator.md"
    
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