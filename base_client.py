"""
Abstract Base Class for AI Clients
Defines the interface that all AI client implementations must follow
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass


@dataclass
class TokenUsage:
    """Token usage information"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cached_tokens: int = 0


@dataclass
class CostEstimate:
    """Cost estimation details"""
    prompt_cost: float
    completion_cost: float
    cached_cost: float
    total_cost: float
    currency: str = "USD"


@dataclass
class CachingRecommendation:
    """Recommendation for prompt caching optimization"""
    should_use_caching: bool
    reason: str
    estimated_savings: float
    optimization_tips: List[str]
    optimized_structure: Optional[Dict[str, Any]] = None


class BaseAIClient(ABC):
    """
    Abstract base class for AI API clients.
    All concrete implementations (OpenAI, Gemini, etc.) must implement these methods.
    """
    
    def __init__(self, api_key: Optional[str] = None, langsmith: bool = False):
        """
        Initialize the AI client
        
        Args:
            api_key: API key for the service. If None, will try to load from environment
            langsmith: Whether to enable LangSmith tracing (default: False)
        """
        self.api_key = api_key
        self.langsmith = langsmith
        self.current_model: Optional[str] = None
        self._client = None
        
        # Generation parameters
        self._generation_config = {
            'temperature': None,
            'top_p': None,
            'top_k': None,
            'max_tokens': None
        }
    
    # ==================== Configuration Methods ====================
    
    def set_temperature(self, temperature: float) -> 'BaseAIClient':
        """
        Set the temperature for generation (0.0 to 2.0)
        Higher values make output more random, lower values more deterministic
        
        Args:
            temperature: Temperature value (typically 0.0 to 2.0)
        
        Returns:
            Self for method chaining
        """
        self._generation_config['temperature'] = temperature
        return self
    
    def set_top_p(self, top_p: float) -> 'BaseAIClient':
        """
        Set nucleus sampling parameter (0.0 to 1.0)
        
        Args:
            top_p: Top-p value for nucleus sampling
        
        Returns:
            Self for method chaining
        """
        self._generation_config['top_p'] = top_p
        return self
    
    def set_top_k(self, top_k: int) -> 'BaseAIClient':
        """
        Set top-k sampling parameter
        
        Args:
            top_k: Number of top tokens to consider
        
        Returns:
            Self for method chaining
        """
        self._generation_config['top_k'] = top_k
        return self
    
    def set_max_tokens(self, max_tokens: int) -> 'BaseAIClient':
        """
        Set maximum tokens for generation
        
        Args:
            max_tokens: Maximum number of tokens to generate
        
        Returns:
            Self for method chaining
        """
        self._generation_config['max_tokens'] = max_tokens
        return self
    
    def reset_generation_config(self) -> 'BaseAIClient':
        """
        Reset all generation parameters to None (use API defaults)
        
        Returns:
            Self for method chaining
        """
        for key in self._generation_config:
            self._generation_config[key] = None
        return self
    
    def get_generation_config(self) -> Dict[str, Any]:
        """
        Get current generation configuration (only non-None values)
        
        Returns:
            Dictionary of active generation parameters
        """
        return {k: v for k, v in self._generation_config.items() if v is not None}
    
    # ==================== Abstract Methods ====================
    
    @abstractmethod
    def select_model(self, model_name: str) -> None:
        """
        Select the model to use for requests
        
        Args:
            model_name: Name of the model to use
        
        Raises:
            ValueError: If model is not available
        """
        pass
    
    @abstractmethod
    def get_response(
        self, 
        prompt, 
        **kwargs
    ) -> Tuple[str, TokenUsage]:
        """
        Get a response from the AI model
        
        Args:
            prompt: Can be a Prompt object, list of message dicts, or a simple string
            **kwargs: Additional parameters specific to the API
        
        Returns:
            Tuple of (response_text, token_usage)
        
        Raises:
            Exception: If API call fails
        """
        pass
    
    def _convert_prompt_to_messages(self, prompt) -> List[Dict[str, str]]:
        """
        Convert various prompt formats to standard message list
        Validates Prompt objects before conversion
        
        Args:
            prompt: Prompt object, list of messages, or string
        
        Returns:
            List of message dictionaries
            
        Raises:
            ValueError: If prompt is invalid or has undefined variables
        """
        # Import here to avoid circular dependency
        from prompt import Prompt
        
        if isinstance(prompt, Prompt):
            # Validate the prompt before conversion
            is_valid, error_message = prompt.validate()
            if not is_valid:
                raise ValueError(f"Invalid prompt: {error_message}")
            
            return prompt.to_messages()
        elif isinstance(prompt, str):
            return [{'role': 'user', 'content': prompt}]
        elif isinstance(prompt, list):
            return prompt
        else:
            raise ValueError(f"Unsupported prompt type: {type(prompt)}")
    
    @abstractmethod
    def count_tokens(self, text: str, model: Optional[str] = None) -> int:
        """
        Count the number of tokens in a text
        
        Args:
            text: Text to count tokens for
            model: Model to use for counting (uses current_model if None)
        
        Returns:
            Number of tokens
        """
        pass
    
    @abstractmethod
    def estimate_cost(
        self, 
        prompt_tokens: int, 
        completion_tokens: int,
        cached_tokens: int = 0,
        model: Optional[str] = None
    ) -> CostEstimate:
        """
        Estimate the cost of a request
        
        Args:
            prompt_tokens: Number of tokens in the prompt
            completion_tokens: Number of tokens in the completion
            cached_tokens: Number of tokens served from cache
            model: Model to estimate for (uses current_model if None)
        
        Returns:
            CostEstimate object with detailed cost breakdown
        """
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """
        Get list of available models for this provider
        
        Returns:
            List of model names
        """
        pass
    
    @abstractmethod
    def supports_caching(self, model: Optional[str] = None) -> bool:
        """
        Check if the model supports prompt caching
        
        Args:
            model: Model to check (uses current_model if None)
        
        Returns:
            True if caching is supported
        """
        pass
    

    
    def get_provider_name(self) -> str:
        """
        Get the name of the provider
        
        Returns:
            Provider name (e.g., 'openai', 'gemini')
        """
        return self.__class__.__name__.replace('Client', '').lower()
    
    def count_messages_tokens(
        self, 
        messages: List[Dict[str, str]], 
        model: Optional[str] = None
    ) -> int:
        """
        Count total tokens in a list of messages
        
        Args:
            messages: List of message dictionaries
            model: Model to use for counting
        
        Returns:
            Total number of tokens
        """
        total = 0
        for message in messages:
            # Count tokens in content
            total += self.count_tokens(message.get('content', ''), model)
            # Add overhead for message structure (role, formatting, etc.)
            total += 4  # Approximate overhead per message
        return total
    
    def count_embedding_tokens(self, texts: List[str], model: Optional[str] = None) -> int:
        """
        Count total tokens for embedding generation
        
        Args:
            texts: List of texts to embed
            model: Model to use for counting
        
        Returns:
            Total number of tokens across all texts
        """
        return sum(self.count_tokens(text, model) for text in texts)
