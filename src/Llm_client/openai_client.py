"""
OpenAILLMClient implementation for interacting with OpenAI's API.
"""

from .base_client import LLMClient
from openai import OpenAI
from typing import Dict, Any, Optional
import json
from json_repair import repair_json


class OpenAILLMClient(LLMClient):
    """Implementation of LLMClient for OpenAI"""
    
    def __init__(self, api_key: str, model: str = "gpt-4.1-mini", system_prompt: Optional[str] = None, **kwargs):
        """
        Initialize the OpenAI client with API key and model.
        
        Args:
            api_key (str): The OpenAI API key
            model (str): The model name to use. Default is 'gpt-4.1-mini'
            system_prompt (Optional[str]): An optional system prompt to guide the model's behavior.
            **kwargs: Additional configuration options
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.system_prompt = system_prompt
        default_options = {
            "temperature": 0.0,
            "max_tokens": 10000,
        }
        self.options = {**default_options, **kwargs}  # User options override defaults
        
    def generate_text(self, prompt: str, system_prompt: Optional[str], **kwargs) -> str:
        """
        Generate text from OpenAI API.
        
        Args:
            prompt (str): The input prompt to send to the model
            **kwargs: Additional parameters to pass to the API call
            
        Returns:
            str: The generated text response
        """
        options = {**self.options, **kwargs}
        
        # Extract parameters that are specifically for OpenAI
        max_tokens = options.pop('max_tokens', 4096)
        temperature = options.pop('temperature', 0.0)
        
        messages = []
        if system_prompt:
            messages.append({"role": "developer", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **options
        )
        
        return response.choices[0].message.content
        
    def generate_json(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Generate JSON from OpenAI API with explicit formatting instructions.
        
        Args:
            prompt (str): The input prompt to send to the model
            **kwargs: Additional parameters to pass to the API call
            
        Returns:
            Dict[str, Any]: The structured JSON response
        """
        options = {**self.options, **kwargs}
        
        # Append instructions to encourage proper JSON formatting
        json_prompt = f"{prompt}\n\nPlease format your response as valid JSON."
        
        # Extract parameters that are specifically for OpenAI
        max_tokens = options.pop('max_tokens', 4096)
        temperature = options.pop('temperature', 0.0)
        
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": json_prompt})
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
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
                repaired_json = repair_json(text_response, return_objects=True)
            
            return repaired_json
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response from OpenAI API: {e}")
    
    def extract_metadata(self, prompt: str) -> Dict[str, Any]:
        """
        Extract metadata using OpenAI's understanding of the content.
        
        Args:
            prompt (str): The prompt that guides the metadata extraction process
            
        Returns:
            Dict[str, Any]: The extracted metadata as a structured dictionary
        """
        return self.generate_json(prompt)
