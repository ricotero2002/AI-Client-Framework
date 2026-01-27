"""
Gemini Client Implementation
Concrete implementation of BaseAIClient for Google Gemini API
"""
from typing import List, Dict, Optional, Tuple
from base_client import BaseAIClient, TokenUsage, CostEstimate, CachingRecommendation
from prompt_optimizer import PromptOptimizer
from config import Config



class GeminiClient(BaseAIClient):
    """Google Gemini API client implementation"""
    
    def __init__(self, api_key: Optional[str] = None, langsmith: bool = False):
        """Initialize Gemini client"""
        super().__init__(api_key, langsmith)
        
        # Get API key from config if not provided
        if not self.api_key:
            self.api_key = Config.get_api_key("gemini")
        
        if not self.api_key:
            raise ValueError("Gemini API key not found. Set GEMINI_API_KEY environment variable.")
        
        # Initialize Gemini client with new SDK
        try:
            from google import genai
            self._genai = genai
            self._client = genai.Client(api_key=self.api_key)
        except ImportError:
            raise ImportError(
                "google-genai is required for Gemini. "
                "Install it with: pip install google-genai"
            )
        
        # Set default model
        self.current_model = Config.get_default_model("gemini")
        
        # Model fallback configuration (similar price alternatives)
        self._model_fallbacks = {
            # gemini-2.0-flash alternatives (input: 0.10, output: 0.40)
            "gemini-2.0-flash": ["gemini-2.5-flash-lite", "gemini-2.0-flash-lite", "gemini-2.0-flash-exp"],
            
            # gemini-2.0-flash-lite alternatives (input: 0.075, output: 0.30)
            "gemini-2.0-flash-lite": ["gemini-2.0-flash-exp", "gemini-2.5-flash-lite", "gemini-2.0-flash"],
            
            # gemini-2.5-flash alternatives (input: 0.30, output: 2.50)
            "gemini-2.5-flash": ["gemini-2.0-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash-exp"],
            
            # gemini-2.5-flash-lite alternatives (input: 0.10, output: 0.40)
            "gemini-2.5-flash-lite": ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-2.0-flash-exp"],
            
            # gemini-2.0-flash-exp alternatives (FREE)
            "gemini-2.0-flash-exp": ["gemini-2.0-flash-lite", "gemini-2.5-flash-lite", "gemini-2.0-flash"],
        }
    
    def select_model(self, model_name: str) -> None:
        """Select the model to use"""
        available_models = self.get_available_models()
        if model_name not in available_models:
            raise ValueError(
                f"Model '{model_name}' not found. Available models: {', '.join(available_models)}"
            )
        self.current_model = model_name
    
    def _convert_messages_to_gemini_format(
        self, 
        messages: List[Dict[str, str]]
    ) -> Tuple[Optional[str], str]:
        """
        Convert OpenAI-style messages to Gemini format
        
        Returns:
            Tuple of (system_instruction, user_content)
        """
        system_instruction = None
        user_parts = []
        
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            
            if role == 'system':
                # Gemini uses system_instruction separately
                system_instruction = content
            else:
                # Accumulate all user/assistant messages into user content
                user_parts.append(content)
        
        # Join all parts into a single prompt
        user_content = "\n\n".join(user_parts)
        
        return system_instruction, user_content
    
    def get_response(
        self, 
        prompt, 
        **kwargs
    ) -> Tuple[str, TokenUsage]:
        """Get response from Gemini API using new google.genai SDK"""
        try:
            # Import Prompt class to check type
            from prompt import Prompt
            
            # Store original prompt to check for structured output
            original_prompt = prompt
            
            # Convert prompt to messages format
            messages = self._convert_prompt_to_messages(prompt)
            
            # Convert messages to Gemini format
            system_instruction, user_content = self._convert_messages_to_gemini_format(messages)
            
            # Prepare config
            from google.genai import types
            config_params = {}
            
            # Add system instruction if present
            if system_instruction:
                config_params['system_instruction'] = system_instruction
            
            # Get generation config and map to Gemini parameter names
            gen_config = self.get_generation_config()
            
            # Map our parameter names to Gemini's expected names
            gemini_gen_config = {}
            if 'temperature' in gen_config:
                gemini_gen_config['temperature'] = gen_config['temperature']
            if 'top_p' in gen_config:
                gemini_gen_config['top_p'] = gen_config['top_p']
            if 'top_k' in gen_config:
                gemini_gen_config['top_k'] = gen_config['top_k']
            if 'max_tokens' in gen_config:
                gemini_gen_config['max_output_tokens'] = gen_config['max_tokens']
            # Note: Gemini doesn't support frequency_penalty and presence_penalty
            
            # Merge with any additional kwargs (kwargs take precedence)
            config_params.update(gemini_gen_config)
            
            # Check for structured output only if original_prompt is a Prompt object
            if isinstance(original_prompt, Prompt) and original_prompt.has_structured_output():
                config_params['response_mime_type'] = "application/json"
                config_params['response_json_schema'] = original_prompt.get_pydantic_model().model_json_schema()
            
            # Create config object if we have parameters
            config = types.GenerateContentConfig(**config_params) if config_params else None
            

            # Make API call using new SDK
            response = self._client.models.generate_content(
                model=self.current_model,
                contents=user_content,
                config=config
            )
            
            # Extract response text
            response_text = response.text
            
            # Extract token usage
            usage_metadata = response.usage_metadata
            
            # Get cached tokens safely
            cached_tokens = 0
            if hasattr(usage_metadata, 'cached_content_token_count'):
                cached_tokens = usage_metadata.cached_content_token_count or 0
            
            token_usage = TokenUsage(
                prompt_tokens=usage_metadata.prompt_token_count,
                completion_tokens=usage_metadata.candidates_token_count,
                total_tokens=usage_metadata.total_token_count,
                cached_tokens=cached_tokens
            )

            return response_text, token_usage
            
        except Exception as e:
            error_str = str(e)
            
            # Check for rate limiting (429) or service unavailable (503) errors
            if ("429" in error_str or "RESOURCE_EXHAUSTED" in error_str or 
                "503" in error_str or "UNAVAILABLE" in error_str or "overloaded" in error_str.lower()):
                
                if "503" in error_str or "overloaded" in error_str.lower():
                    print(f"⚠️  Service overloaded for {self.current_model}. Trying fallback models...")
                else:
                    print(f"⚠️  Rate limit hit for {self.current_model}. Trying fallback models...")
                
                # Get fallback models for current model
                fallbacks = self._model_fallbacks.get(self.current_model, [])
                
                for fallback_model in fallbacks:
                    try:
                        print(f"🔄 Attempting with {fallback_model}...")
                        
                        # Temporarily switch model
                        original_model = self.current_model
                        self.current_model = fallback_model
                        
                        # Retry with fallback model
                        response = self._client.models.generate_content(
                            model=self.current_model,
                            contents=user_content,
                            config=config
                        )
                        
                        # Success!
                        print(f"✅ Success with {fallback_model}!")
                        
                        # Extract response
                        response_text = response.text
                        usage_metadata = response.usage_metadata
                        
                        cached_tokens = 0
                        if hasattr(usage_metadata, 'cached_content_token_count'):
                            cached_tokens = usage_metadata.cached_content_token_count or 0
                        
                        token_usage = TokenUsage(
                            prompt_tokens=usage_metadata.prompt_token_count,
                            completion_tokens=usage_metadata.candidates_token_count,
                            total_tokens=usage_metadata.total_token_count,
                            cached_tokens=cached_tokens
                        )
                        
                        # Keep the fallback model for future requests
                        print(f"ℹ️  Switched from {original_model} to {fallback_model} due to availability issues")
                        
                        return response_text, token_usage
                        
                    except Exception as fallback_error:
                        # This fallback also failed, try next one
                        fallback_error_str = str(fallback_error)
                        if ("429" in fallback_error_str or "RESOURCE_EXHAUSTED" in fallback_error_str or
                            "503" in fallback_error_str or "UNAVAILABLE" in fallback_error_str or 
                            "overloaded" in fallback_error_str.lower()):
                            print(f"❌ {fallback_model} also unavailable")
                            self.current_model = original_model  # Restore
                            continue
                        else:
                            # Different error, restore and raise
                            self.current_model = original_model
                            raise fallback_error
                
                # All fallbacks failed
                print(f"❌ All fallback models exhausted. Original error: {error_str}")
                raise Exception(f"Gemini API error (all models unavailable): {error_str}")
            
            # Not a rate limit or availability error, raise original exception
            raise Exception(f"Gemini API error: {error_str}")
    
    def count_tokens(self, text: str, model: Optional[str] = None) -> int:
        """Count tokens using Gemini's API"""
        try:
            model_name = model or self.current_model
            model_obj = self._genai.GenerativeModel(model_name)
            result = model_obj.count_tokens(text)
            return result.total_tokens
        except Exception as e:
            # Fallback: rough estimation (1 token ≈ 4 characters for English)
            return len(text) // 4
    
    def estimate_cost(
        self, 
        prompt_tokens: int, 
        completion_tokens: int,
        cached_tokens: int = 0,
        model: Optional[str] = None
    ) -> CostEstimate:
        """Estimate cost for Gemini request"""
        model_name = model or self.current_model
        pricing = Config.get_pricing("gemini", model_name)
        
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
        """Get list of available Gemini models"""
        return list(Config.GEMINI_PRICING.keys())
    
    def supports_caching(self, model: Optional[str] = None) -> bool:
        """Check if model supports context caching"""
        model_name = model or self.current_model
        pricing = Config.get_pricing("gemini", model_name)
        
        if not pricing:
            return False
        
        # Gemini 1.5 Pro and Flash support context caching
        return pricing.get('cached_input') is not None
    

