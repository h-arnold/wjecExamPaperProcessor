"""
Factory module for creating LLM clients.

This module provides a factory class for creating different LLM clients
based on the provider name.
"""

import os
import logging

from .base_client import LLMClient
from .openai_client import OpenAILLMClient
from .mistral_client import MistralLLMClient

class LLMClientFactory:
    """
    Factory class for creating LLM clients.
    
    This class provides methods to create different LLM clients based on the
    provider name.
    """
    
    def __init__(self):
        """Initialize the LLMClientFactory."""
        self.logger = logging.getLogger(__name__)
    
    def create_client(self, provider: str, **kwargs) -> LLMClient:
        """
        Create an LLM client using an API key from environment variables.
        
        Args:
            provider (str): Name of the LLM provider ("openai", "mistral", etc.)
            **kwargs: Additional options for the client, including model name
            
        Returns:
            LLMClient: A client for the specified provider and model
            
        Raises:
            ValueError: If the API key is missing or provider is not supported
        """
        provider = provider.lower()
        api_key = os.environ.get(f"{provider.upper()}_API_KEY")
        
        if not api_key:
            raise ValueError(f"Missing API key for {provider}. Set {provider.upper()}_API_KEY environment variable.")
        
        return self.create_specific_client(provider, api_key, **kwargs)
    
    def create_specific_client(self, provider: str, api_key: str, **kwargs) -> LLMClient:
        """
        Create an LLM client for the specified provider.
        
        Args:
            provider (str): Name of the LLM provider ("openai", "mistral")
            api_key (str): API key for the provider
            **kwargs: Additional options for the client
            
        Returns:
            LLMClient: A client for the specified provider
            
        Raises:
            ValueError: If the provider is not supported
        """
        provider = provider.lower()
        
        if provider == "openai":
            return OpenAILLMClient(api_key, **kwargs)
        elif provider == "mistral":
            return MistralLLMClient(api_key, **kwargs)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")