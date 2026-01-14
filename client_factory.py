"""
Client Factory
Factory pattern for creating AI clients
"""
from typing import Optional, List
from base_client import BaseAIClient
from openai_client import OpenAIClient
from gemini_client import GeminiClient
from openai_client_smith import OpenAIClientSmith
from gemini_client_smith import GeminiClientSmith


class ClientFactory:
    """Factory for creating AI client instances"""
    
    # Registry of available clients
    _clients = {
        'openai': OpenAIClient,
        'gemini': GeminiClient,
    }
    
    # Registry of LangSmith-enabled clients
    _clients_smith = {
        'openai': OpenAIClientSmith,
        'gemini': GeminiClientSmith,
    }
    
    @classmethod
    def create_client(
        cls, 
        provider: str, 
        api_key: Optional[str] = None,
        langsmith: bool = False
    ) -> BaseAIClient:
        """
        Create an AI client for the specified provider
        
        Args:
            provider: Name of the provider ('openai', 'gemini', etc.)
            api_key: Optional API key. If not provided, will use environment variable
            langsmith: Whether to enable LangSmith tracing (default: False)
        
        Returns:
            Instance of the appropriate client
        
        Raises:
            ValueError: If provider is not supported
        
        Example:
            >>> client = ClientFactory.create_client('openai')
            >>> client.select_model('gpt-4o-mini')
            >>> response, usage = client.get_response([
            ...     {'role': 'user', 'content': 'Hello!'}
            ... ])
        """
        provider_lower = provider.lower()
        
        if provider_lower not in cls._clients:
            available = ', '.join(cls._clients.keys())
            raise ValueError(
                f"Provider '{provider}' not supported. "
                f"Available providers: {available}"
            )
        
        # Choose the appropriate client class based on langsmith flag
        if langsmith:
            client_class = cls._clients_smith.get(provider_lower)
            if not client_class:
                # Fallback to regular client if Smith variant doesn't exist
                print(f"Warning: LangSmith variant not available for {provider}, using regular client")
                client_class = cls._clients[provider_lower]
        else:
            client_class = cls._clients[provider_lower]
        
        return client_class(api_key=api_key, langsmith=langsmith)
    
    @classmethod
    def get_available_providers(cls) -> List[str]:
        """
        Get list of all available providers
        
        Returns:
            List of provider names
        
        Example:
            >>> providers = ClientFactory.get_available_providers()
            >>> print(providers)
            ['openai', 'gemini']
        """
        return list(cls._clients.keys())
    
    @classmethod
    def register_client(cls, provider: str, client_class: type): #ver bien como funciona esto
        """
        Register a new client implementation
        
        This allows extending the framework with custom clients
        
        Args:
            provider: Name of the provider
            client_class: Class that implements BaseAIClient
        
        Raises:
            TypeError: If client_class doesn't inherit from BaseAIClient
        
        Example:
            >>> class CustomClient(BaseAIClient):
            ...     # Implementation here
            ...     pass
            >>> ClientFactory.register_client('custom', CustomClient)
        """
        if not issubclass(client_class, BaseAIClient):
            raise TypeError(
                f"{client_class.__name__} must inherit from BaseAIClient"
            )
        
        cls._clients[provider.lower()] = client_class
    
    @classmethod
    def unregister_client(cls, provider: str):
        """
        Remove a client from the registry
        
        Args:
            provider: Name of the provider to remove
        """
        provider_lower = provider.lower()
        if provider_lower in cls._clients:
            del cls._clients[provider_lower]


# Convenience function for quick client creation
def create_client(provider: str, api_key: Optional[str] = None, langsmith: bool = False) -> BaseAIClient:
    """
    Convenience function to create a client
    
    Args:
        provider: Name of the provider ('openai', 'gemini', etc.)
        api_key: Optional API key
        langsmith: Whether to enable LangSmith tracing (default: False)
    
    Returns:
        Instance of the appropriate client
    
    Example:
        >>> from client_factory import create_client
        >>> client = create_client('openai')
    """
    return ClientFactory.create_client(provider, api_key, langsmith)
