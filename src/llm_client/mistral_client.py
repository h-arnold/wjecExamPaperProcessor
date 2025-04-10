"""
MistralLLMClient implementation for interacting with Mistral AI's API.
"""

from .base_client import LLMClient
from mistralai import Mistral
from typing import Dict, Any, Optional
import json


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
        response = self.client.chat(
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
        json_prompt = f"{prompt}\n\nPlease provide your response in valid JSON format only."
        options = {**self.options, **kwargs}
        
        response = self.client.chat(
            model=self.model,
            messages=[{"role": "user", "content": json_prompt}],
            **options
        )
        
        try:
            # Extract JSON from the response
            text_response = response.choices[0].message.content
            # Strip any markdown code block formatting if present
            if "```json" in text_response:
                text_response = text_response.split("```json")[1].split("```")[0].strip()
            elif "```" in text_response:
                text_response = text_response.split("```")[1].split("```")[0].strip()
            
            return json.loads(text_response)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response from Mistral API: {e}")
    
    def extract_metadata(self, content: str, metadata_prompt: str) -> Dict[str, Any]:
        """
        Extract metadata using Mistral's understanding of the content.
        
        Args:
            content (str): The content to extract metadata from
            metadata_prompt (str): The prompt that guides the extraction process
            
        Returns:
            Dict[str, Any]: The extracted metadata as a structured dictionary
        """
        full_prompt = f"{metadata_prompt}\n\nAnalyze the following content to extract metadata:\n\n{content}"
        return self.generate_json(full_prompt)