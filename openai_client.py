"""
OpenAI Client Implementation
Concrete implementation of BaseAIClient for OpenAI API
"""
from typing import List, Dict, Optional, Tuple
from openai import OpenAI, APIConnectionError, RateLimitError, APIError
from base_client import BaseAIClient, TokenUsage, CostEstimate, CachingRecommendation
from prompt_optimizer import PromptOptimizer
from config import Config


class OpenAIClient(BaseAIClient):
    """OpenAI API client implementation"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize OpenAI client"""
        super().__init__(api_key)
        
        # Get API key from config if not provided
        if not self.api_key:
            self.api_key = Config.get_api_key("openai")
        
        if not self.api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
        
        # Initialize OpenAI client
        self._client = OpenAI(api_key=self.api_key)
        
        # Set default model
        self.current_model = Config.get_default_model("openai")
        
        # Initialize tiktoken for token counting
        self._tokenizer = None
    
    def _get_tokenizer(self, model: Optional[str] = None):
        """Get or create tokenizer for the model"""
        try:
            import tiktoken
            model_name = model or self.current_model
            return tiktoken.encoding_for_model(model_name)
        except ImportError:
            raise ImportError(
                "tiktoken is required for OpenAI token counting. "
                "Install it with: pip install tiktoken"
            )
        except Exception:
            # Fallback to cl100k_base encoding for unknown models
            import tiktoken
            return tiktoken.get_encoding("cl100k_base")
    
    def select_model(self, model_name: str) -> None:
        """Select the model to use"""
        available_models = self.get_available_models()
        if model_name not in available_models:
            raise ValueError(
                f"Model '{model_name}' not found. Available models: {', '.join(available_models)}"
            )
        self.current_model = model_name
    
    
    def get_response(
        self, 
        prompt, 
        **kwargs
    ) -> Tuple[str, TokenUsage]:
        """Get response from OpenAI API using the new Responses API"""
        try:
            # Convert prompt to messages format
            messages = self._convert_prompt_to_messages(prompt)
            
            # Use current model if not specified
            model = kwargs.pop('model', self.current_model)
            
            # Merge generation config with kwargs (kwargs take precedence)
            config = self.get_generation_config()
            
            # Map our parameter names to OpenAI's expected names
            if 'max_tokens' in config:
                config['max_completion_tokens'] = config.pop('max_tokens')
            
            # Merge configs (kwargs override generation_config)
            final_config = {**config, **kwargs}
            
            # Make API call using new Responses API
            response = self._client.responses.create(
                model=model,
                input=messages,
                **final_config
            )
            
            # Extract response text from output
            response_text = response.output_text
            
            # Extract token usage - handle both old and new API formats
            usage = response.usage
            
            # Try to get cached tokens safely
            cached_tokens = 0
            if hasattr(usage, 'input_tokens_details') and usage.input_tokens_details:
                if isinstance(usage.input_tokens_details, dict):
                    cached_tokens = usage.input_tokens_details.get('cached_tokens', 0)
                else:
                    cached_tokens = getattr(usage.input_tokens_details, 'cached_tokens', 0)
            
            token_usage = TokenUsage(
                prompt_tokens=usage.input_tokens,
                completion_tokens=usage.output_tokens,
                total_tokens=usage.total_tokens,
                cached_tokens=cached_tokens
            )
            
            return response_text, token_usage
            
        except RateLimitError as e:
            raise Exception(f"Rate limit exceeded: {str(e)}")
        except APIConnectionError as e:
            raise Exception(f"Connection to OpenAI API failed: {str(e)}")
        except APIError as e:
            raise Exception(f"OpenAI API error: {str(e)}")
        except Exception as e:
            raise Exception(f"Unexpected error: {str(e)}")
    
    def count_tokens(self, text: str, model: Optional[str] = None) -> int:
        """Count tokens in text using tiktoken"""
        tokenizer = self._get_tokenizer(model)
        return len(tokenizer.encode(text))
    
    def estimate_cost(
        self, 
        prompt_tokens: int, 
        completion_tokens: int,
        cached_tokens: int = 0,
        model: Optional[str] = None
    ) -> CostEstimate:
        """Estimate cost for OpenAI request"""
        model_name = model or self.current_model
        pricing = Config.get_pricing("openai", model_name)
        
        if not pricing:
            return CostEstimate(
                prompt_cost=0,
                completion_cost=0,
                cached_cost=0,
                total_cost=0,
                currency="USD"
            )
        
        # Calculate costs (pricing is per 1M tokens)
        uncached_tokens = prompt_tokens - cached_tokens
        prompt_cost = (uncached_tokens / 1_000_000) * pricing['input']
        completion_cost = (completion_tokens / 1_000_000) * pricing['output']
        
        cached_cost = 0
        if cached_tokens > 0 and pricing.get('cached_input'):
            cached_cost = (cached_tokens / 1_000_000) * pricing['cached_input']
        
        total_cost = prompt_cost + completion_cost + cached_cost
        
        return CostEstimate(
            prompt_cost=prompt_cost,
            completion_cost=completion_cost,
            cached_cost=cached_cost,
            total_cost=total_cost,
            currency="USD"
        )
    
    def get_available_models(self) -> List[str]:
        """Get list of available OpenAI models"""
        return list(Config.OPENAI_PRICING.keys())
    
    def supports_caching(self, model: Optional[str] = None) -> bool:
        """Check if model supports prompt caching"""
        model_name = model or self.current_model
        pricing = Config.get_pricing("openai", model_name)
        
        if not pricing:
            return False
        
        return pricing.get('cached_input') is not None
    

