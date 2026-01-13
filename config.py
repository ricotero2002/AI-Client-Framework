"""
Configuration management for AI Client Framework
Handles API keys, model pricing, and default settings
"""
import os
from dotenv import load_dotenv
from typing import Dict, Optional

# Load environment variables
load_dotenv()


class Config:
    """Central configuration for all AI clients"""
    
    # API Keys
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    
    # Model Pricing (USD per 1M tokens)
    # Format: {model_name: {"input": price, "output": price, "cached_input": price}}
    OPENAI_PRICING = {
        "gpt-4": {
            "input": 30.0,
            "output": 60.0,
            "cached_input": None  # OpenAI doesn't have prompt caching yet
        },
        "gpt-4-turbo": {
            "input": 10.0,
            "output": 30.0,
            "cached_input": None
        },
        "gpt-3.5-turbo": {
            "input": 0.5,
            "output": 1.5,
            "cached_input": None
        },
        "gpt-4o": {
            "input": 2.5,
            "output": 10.0,
            "cached_input": 1.25  # 50% discount for cached
        },
        "gpt-4o-mini": {
            "input": 0.15,
            "output": 0.6,
            "cached_input": 0.075
        },
        "gpt-5-nano": {
            "input": 0.05,
            "output": 0.4,
            "cached_input": 0.025
        }
    }
    
    
    GEMINI_PRICING = {
        "gemini-1.5-pro": {
            "input": 1.25,
            "output": 5.0,
            "cached_input": 0.3125  # 75% discount for cached
        },
        "gemini-1.5-flash": {
            "input": 0.075,
            "output": 0.3,
            "cached_input": 0.01875
        },
        "gemini-2.0-flash-exp": {
            "input": 0.0,  # Free tier experimental
            "output": 0.0,
            "cached_input": 0.0
        },
        "gemini-3-flash-preview": {
            "input": 0.0,  # Preview/experimental
            "output": 0.0,
            "cached_input": 0.0
        },
        "gemini-2.5-flash-lite": {
            "input": 0.075,  # Estimated pricing similar to flash
            "output": 0.3,
            "cached_input": 0.01875
        }
    }
    
    # Default models
    DEFAULT_OPENAI_MODEL = "gpt-5-nano"
    DEFAULT_GEMINI_MODEL = "gemini-2.0-flash-exp"
    
    # Caching configuration
    MIN_TOKENS_FOR_CACHING = 1024  # Minimum tokens to recommend caching
    CACHE_WARMUP_COST_THRESHOLD = 0.5  # Recommend caching if saves > $0.50
    
    @classmethod
    def get_api_key(cls, provider: str) -> Optional[str]:
        """Get API key for a specific provider"""
        key_map = {
            "openai": cls.OPENAI_API_KEY,
            "gemini": cls.GEMINI_API_KEY,
            "anthropic": cls.ANTHROPIC_API_KEY
        }
        return key_map.get(provider.lower())
    
    @classmethod
    def get_pricing(cls, provider: str, model: str) -> Optional[Dict[str, float]]:
        """Get pricing information for a specific model"""
        pricing_map = {
            "openai": cls.OPENAI_PRICING,
            "gemini": cls.GEMINI_PRICING
        }
        provider_pricing = pricing_map.get(provider.lower(), {})
        return provider_pricing.get(model)
    
    @classmethod
    def get_default_model(cls, provider: str) -> Optional[str]:
        """Get default model for a provider"""
        default_map = {
            "openai": cls.DEFAULT_OPENAI_MODEL,
            "gemini": cls.DEFAULT_GEMINI_MODEL
        }
        return default_map.get(provider.lower())
