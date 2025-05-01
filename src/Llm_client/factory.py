"""
Factory for creating LLM clients based on provider name.
"""

from typing import Dict, Any
from .base_client import LLMClient
from .mistral_client import MistralLLMClient
from .openai_client import OpenAILLMClient


class LLMClientFactory:
    """Factory for creating LLM clients based on provider name"""
    
    @staticmethod
    def create_client(provider: str, api_key: str, **kwargs) -> LLMClient:
        """
        Create and return an LLM client based on the specified provider.
        
        Args:
            provider (str): Name of the LLM provider ("mistral", "openai", etc.)
            api_key (str): API key for the selected provider
            **kwargs: Additional options to pass to the client
            
        Returns:
            LLMClient: An instance of LLMClient for the specified provider
            
        Raises:
            ValueError: If the specified provider is not supported
        """
        if provider.lower() == "mistral":
            return MistralLLMClient(api_key, **kwargs)
        elif provider.lower() == "openai":
            return OpenAILLMClient(api_key, **kwargs)
        # Placeholder for future providers
        # elif provider.lower() == "anthropic":
        #     return AnthropicClient(api_key, **kwargs)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")