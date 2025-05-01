from pathlib import Path
from typing import Dict, Optional, Union, Literal
from enum import Enum

from .base_prompt import Prompt


class Qualification(Enum):
    """Enumeration of available qualification levels."""
    AS_LEVEL = "AS-Level"
    A2_LEVEL = "A2-Level"


class SpecTaggerPrompt:
    """
    A specialized prompt class for tagging exam questions with specification areas.
    
    This class creates two separate prompts:
    1. A system prompt containing the relevant specification content and tagging instructions
    2. A content prompt containing the question and optionally the mark scheme to be tagged
    
    Attributes:
        question (str): The question text to be tagged
        mark_scheme (Optional[str]): The corresponding mark scheme text, if available
        qualification (Qualification): The qualification level (AS-Level or A2-Level)
        _system_prompt (str): The generated system prompt with specification and instructions
        _content_prompt (str): The generated content prompt with question and mark scheme
    """
    
    # Mapping from qualification to specification file path
    SPEC_PATHS = {
        Qualification.AS_LEVEL: Path(__file__).parent / "MarkdownPrompts" / "SupportingDocs" / "AS-Level-Spec-2015.md",
        Qualification.A2_LEVEL: Path(__file__).parent / "MarkdownPrompts" / "SupportingDocs" / "A2-Level-Spec-2015.md"
    }
    
    # Path to the spec tagger instruction file
    TAGGER_INSTRUCTIONS_PATH = Path(__file__).parent / "MarkdownPrompts" / "specAreaTagger.md"
    
    def __init__(self, 
                 question: str, 
                 qualification: Qualification, 
                 mark_scheme: Optional[str] = None):
        """
        Initialize the SpecTaggerPrompt with question, qualification, and optional mark scheme.
        
        Args:
            question (str): The question text to be tagged
            qualification (Qualification): The qualification level (AS-Level or A2-Level)
            mark_scheme (Optional[str]): The corresponding mark scheme text, if available
                                      Default: None
        """
        self.question = question
        self.mark_scheme = mark_scheme
        self.qualification = qualification
        
        # Check if the specification file exists
        spec_path = self.SPEC_PATHS.get(qualification)
        if not spec_path or not spec_path.exists():
            raise FileNotFoundError(f"Specification file not found for {qualification.value}")
        
        # Check if the tagger instructions file exists
        if not self.TAGGER_INSTRUCTIONS_PATH.exists():
            raise FileNotFoundError(f"Tagger instructions file not found at: {self.TAGGER_INSTRUCTIONS_PATH}")
        
        # Generate the prompts
        self._system_prompt = self._generate_system_prompt()
        self._content_prompt = self._generate_content_prompt()
    
    def _generate_system_prompt(self) -> str:
        """
        Generate the system prompt containing specification and tagging instructions.
        
        Returns:
            str: The formatted system prompt
        """
        # Load the specification content
        spec_path = self.SPEC_PATHS[self.qualification]
        with open(spec_path, 'r', encoding='utf-8') as spec_file:
            spec_content = spec_file.read()
        
        # Load the tagger instructions
        with open(self.TAGGER_INSTRUCTIONS_PATH, 'r', encoding='utf-8') as tagger_file:
            tagger_instructions = tagger_file.read()
        
        # Format the system prompt
        sources = [
            f"# {self.qualification.value} Specification\n",
            spec_content.strip(),
            "\n",
            tagger_instructions.strip()
        ]
        
        # Use the base Prompt class to join the content
        prompt = Prompt(sources)
        return prompt.get()
    
    def _generate_content_prompt(self) -> str:
        """
        Generate the content prompt containing the question and mark scheme.
        
        Returns:
            str: The formatted content prompt
        """
        sources = [
            "# Question:\n",
            self.question.strip()
        ]
        
        # Add mark scheme if provided
        if self.mark_scheme:
            sources.extend([
                "\n# Mark Scheme:\n",
                self.mark_scheme.strip()
            ])
        
        # Use the base Prompt class to join the content
        prompt = Prompt(sources)
        return prompt.get()
    
    def get_system_prompt(self) -> str:
        """
        Get the system prompt with specification and tagging instructions.
        
        Returns:
            str: The system prompt
        """
        return self._system_prompt
    
    def get_content_prompt(self) -> str:
        """
        Get the content prompt with question and mark scheme.
        
        Returns:
            str: The content prompt
        """
        return self._content_prompt
    
    def get_combined_prompt(self) -> str:
        """
        Get both prompts combined for use in systems that don't support separate system prompts.
        
        Returns:
            str: The combined system and content prompts
        """
        return f"{self._system_prompt}\n\n{self._content_prompt}"