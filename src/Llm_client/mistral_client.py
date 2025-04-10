"""
MistralLLMClient implementation for interacting with Mistral AI's API.
"""

from .base_client import LLMClient
from mistralai import Mistral
from typing import Dict, Any, Optional
import json
from json_repair import repair_json


class MistralLLMClient(LLMClient):
    """Implementation of LLMClient for Mistral AI"""
    
    def __init__(self, api_key: str, model: str = "mistral-large-latest", **kwargs):
        """
        Initialize the Mistral client with API key and model.
        
        Args:
            api_key (str): The Mistral API key
            model (str): The model name to use. Default is 'mistral-large-latest'
            **kwargs: Additional configuration options
        """
        self.client = Mistral(api_key=api_key)
        self.model = model
        self.options = kwargs
        
    def generate_text(self, prompt: str, **kwargs) -> str:
        """
        Generate text from Mistral API.
        
        Args:
            prompt (str): The input prompt to send to the model
            **kwargs: Additional parameters to pass to the API call
            
        Returns:
            str: The generated text response
        """
        options = {**self.options, **kwargs}
        response = self.client.chat.complete(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            **options
        )
        return response.choices[0].message.content
        
    def generate_json(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Generate JSON from Mistral API with explicit formatting instructions.
        
        Args:
            prompt (str): The input prompt to send to the model
            **kwargs: Additional parameters to pass to the API call
            
        Returns:
            Dict[str, Any]: The structured JSON response
        """
        options = {**self.options, **kwargs}
        
        response = self.client.chat.complete(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            **options
        )
        
        try:
            # Extract JSON from the response
            text_response = response.choices[0].message.content
            # Strip everything before the first { and after the last }
            first_brace = text_response.find('{')
            last_brace = text_response.rfind('}')
            if first_brace != -1 and last_brace != -1:
                text_response = text_response[first_brace:last_brace+1]
                # Use json_repair to clean up any malformed JSON
                repaired_json = repair_json(text_response)
            
            return json.loads(repaired_json)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response from Mistral API: {e}")
    
    def extract_metadata(self, prompt: str) -> Dict[str, Any]:
        """
        Extract metadata using Mistral's understanding of the content.
        
        Args:
            prompt (str): The prompt that guides the metadata extraction process
            
        Returns:
            Dict[str, Any]: The extracted metadata as a structured dictionary
        """
        return self.generate_json(prompt)
