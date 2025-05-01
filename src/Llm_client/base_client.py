"""
Abstract base class for LLM API clients.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class LLMClient(ABC):
    """
    Abstract base class for LLM API clients.
    Implementations should handle specific providers like Mistral, OpenAI, etc.
    """
    
    @abstractmethod
    def __init__(self, api_key: str, system_prompt: Optional[str] = None, **kwargs):
        """Initialize the LLM client with API key and additional parameters"""
        self.api_key = api_key
        self.default_system_prompt = system_prompt # Store the default system prompt
        
    @abstractmethod
    def generate_text(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """
        Generate text response from a prompt.
        
        Args:
            prompt (str): The input prompt to send to the LLM
            system_prompt_override (Optional[str]): A system prompt to use for this specific call, overriding the default.
            **kwargs: Additional provider-specific parameters
            
        Returns:
            str: The generated text response
        """
        pass
    
    @abstractmethod
    def generate_json(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Generate structured JSON response from a prompt.
        
        Args:
            prompt (str): The input prompt to send to the LLM
            system_prompt_override (Optional[str]): A system prompt to use for this specific call, overriding the default.
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Dict[str, Any]: The structured JSON response
        """
        pass
    
    @abstractmethod
    def extract_metadata(self, content: str, metadata_prompt: str) -> Dict[str, Any]:
        """
        Extract metadata from content based on a metadata extraction prompt.
        
        Args:
            content (str): The content to extract metadata from
            metadata_prompt (str): The prompt that guides the extraction process
            
        Returns:
            Dict[str, Any]: The extracted metadata as a structured dictionary
        """
        pass