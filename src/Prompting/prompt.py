from pathlib import Path
from typing import List, Optional, Union

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
    TEMPLATE_PATH = Path(__file__).parent.parent / "Prompts" / "metadataCreator.md"
    
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
