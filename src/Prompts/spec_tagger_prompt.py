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
        questionContext (Optional[str]): When you're tagging a sub-quesiton, it is helpful for the LLM to have access to the whole quesiton so that it can tag it accurately. This gets provided here.
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
                 mark_scheme: Optional[str] = None,
                 questionContext: Optional[str] = None):
        """
        Initialize the SpecTaggerPrompt with question, qualification, and optional mark scheme.
        
        Args:
            question (str): The question text to be tagged
            qualification (Qualification): The qualification level (AS-Level or A2-Level)
            mark_scheme (Optional[str]): The corresponding mark scheme text, if available
                                      Default: None
            questionContext (Optional[str]): Additional context for the question
                                          Default: None
        """
        self.question = question
        self.mark_scheme = mark_scheme
        self.qualification = qualification
        self.questionContext = questionContext
        
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
        sources = []
        
        # Add context if provided
        if self.questionContext:
            sources.extend([
                "# Question Context:\n",
                self.questionContext.strip(),
                "\n"
            ])
            
        sources.extend([
            "# Question to Tag:\n",
            self.question.strip()
        ])
        
        # Add mark scheme if provided
        if self.mark_scheme:
            sources.extend([
                "\n# Mark Scheme to Tag:\n",
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
    
    def generateQuestionContext(self, questions: list[dict], include_markscheme: bool = False, current_question_number: Optional[str] = None) -> str:
        """
        Generate a markdown formatted context string from a list of related questions.

        Args:
            questions (list[dict]): List of dictionaries containing question data including question_number,
                                  question_text, mark_scheme, max_marks, and assessment_objectives
            include_markscheme (bool, optional): Whether to include mark scheme in output. Defaults to False.
            current_question_number (Optional[str], optional): Current question number for context. Defaults to None.

        Returns:
            str: Markdown formatted string containing concatenated question context
        """
        output_parts = []

        # Add current question number context if provided
        if current_question_number:
            output_parts.append(f"Current Question: {current_question_number}\n")

        # Process each question in the list
        for question in questions:
            # Add question number and text
            output_parts.extend([
                f"Question {question['question_number']}",
                question['question_text']
            ])

            # Add mark scheme if requested and available
            if include_markscheme and 'mark_scheme' in question:
                output_parts.extend([
                    "\nMark Scheme:",
                    question['mark_scheme']
                ])
            
            # Add a blank line between questions
            output_parts.append("")

        # Join all parts with newlines and return
        # Remove any trailing newlines
        return "\n".join(output_parts).strip()