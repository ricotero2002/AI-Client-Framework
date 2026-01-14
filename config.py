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
        # GPT-5.2 Series
        "gpt-5.2-pro": {
            "input": 21.0,
            "output": 168.0,
            "cached_input": 10.5
        },
        "gpt-5.2-chat-latest": {
            "input": 1.75,
            "output": 14.0,
            "cached_input": 0.875
        },
        "gpt-5.2": {
            "input": 1.75,
            "output": 14.0,
            "cached_input": 0.875
        },
        
        # GPT-5.1 Series
        "gpt-5.1-codex-mini": {
            "input": 0.25,
            "output": 2.0,
            "cached_input": 0.125
        },
        "gpt-5.1-codex": {
            "input": 1.25,
            "output": 10.0,
            "cached_input": 0.625
        },
        "gpt-5.1-chat-latest": {
            "input": 1.25,
            "output": 10.0,
            "cached_input": 0.625
        },
        "gpt-5.1": {
            "input": 1.25,
            "output": 10.0,
            "cached_input": 0.625
        },
        
        # GPT-5 Series
        "gpt-5-nano": {
            "input": 0.05,
            "output": 0.40,
            "cached_input": 0.025
        },
        "gpt-5-mini": {
            "input": 0.25,
            "output": 2.0,
            "cached_input": 0.125
        },
        "gpt-5": {
            "input": 1.25,
            "output": 10.0,
            "cached_input": 0.625
        },
        
        # GPT-4.5 Series
        "gpt-4.5-preview": {
            "input": 75.0,
            "output": 150.0,
            "cached_input": 37.5
        },
        "gpt-4.5-preview-2025-02-27": {
            "input": 75.0,
            "output": 150.0,
            "cached_input": 37.5
        },
        
        # GPT-4.1 Series
        "gpt-4.1-nano-2025-04-14": {
            "input": 0.10,
            "output": 0.40,
            "cached_input": 0.05
        },
        "gpt-4.1-nano": {
            "input": 0.10,
            "output": 0.40,
            "cached_input": 0.05
        },
        "gpt-4.1-mini-2025-04-14": {
            "input": 0.40,
            "output": 1.60,
            "cached_input": 0.20
        },
        "gpt-4.1-mini": {
            "input": 0.40,
            "output": 1.60,
            "cached_input": 0.20
        },
        "gpt-4.1-2025-04-14": {
            "input": 2.0,
            "output": 8.0,
            "cached_input": 1.0
        },
        "gpt-4.1": {
            "input": 2.0,
            "output": 8.0,
            "cached_input": 1.0
        },
        
        # GPT-4o Series
        "gpt-4o-2024-11-20": {
            "input": 2.50,
            "output": 10.0,
            "cached_input": 1.25
        },
        "gpt-4o-2024-08-06": {
            "input": 2.50,
            "output": 10.0,
            "cached_input": 1.25
        },
        "gpt-4o-2024-05-13": {
            "input": 5.0,
            "output": 15.0,
            "cached_input": 2.5
        },
        "gpt-4o": {
            "input": 2.50,
            "output": 10.0,
            "cached_input": 1.25
        },
        "chatgpt-4o-latest": {
            "input": 5.0,
            "output": 15.0,
            "cached_input": 2.5
        },
        "gpt-4o-mini-2024-07-18": {
            "input": 0.15,
            "output": 0.60,
            "cached_input": 0.075
        },
        "gpt-4o-mini": {
            "input": 0.15,
            "output": 0.60,
            "cached_input": 0.075
        },
        
        # GPT-4 Series
        "gpt-4": {
            "input": 30.0,
            "output": 60.0,
            "cached_input": None
        },
        "gpt-4-32k": {
            "input": 60.0,
            "output": 120.0,
            "cached_input": None
        },
        "gpt-4-turbo-2024-04-09": {
            "input": 10.0,
            "output": 30.0,
            "cached_input": 5.0
        },
        "gpt-4-turbo": {
            "input": 10.0,
            "output": 30.0,
            "cached_input": 5.0
        },
        "gpt-4-turbo-preview": {
            "input": 10.0,
            "output": 30.0,
            "cached_input": 5.0
        },
        "gpt-4-vision-preview": {
            "input": 10.0,
            "output": 30.0,
            "cached_input": 5.0
        },
        
        # GPT-3.5 Series
        "gpt-3.5-turbo": {
            "input": 0.50,
            "output": 1.50,
            "cached_input": None
        },
        "gpt-3.5-turbo-16k": {
            "input": 0.50,
            "output": 1.50,
            "cached_input": None
        },
        "gpt-3.5-turbo-1106": {
            "input": 1.0,
            "output": 2.0,
            "cached_input": None
        },
        "gpt-3.5-turbo-0125": {
            "input": 0.50,
            "output": 1.50,
            "cached_input": None
        },
        "gpt-3.5-turbo-instruct": {
            "input": 1.50,
            "output": 2.0,
            "cached_input": None
        },
        "ft:gpt-3.5-turbo": {
            "input": 12.0,
            "output": 16.0,
            "cached_input": None
        },
        
        # O-Series (Reasoning Models)
        "o3": {
            "input": 2.0,
            "output": 8.0,
            "cached_input": 1.0
        },
        "o3-mini": {
            "input": 1.10,
            "output": 4.40,
            "cached_input": 0.55
        },
        "o3-mini-2025-01-31": {
            "input": 1.10,
            "output": 4.40,
            "cached_input": 0.55
        },
        "o4-mini": {
            "input": 1.10,
            "output": 4.40,
            "cached_input": 0.55
        },
        "o1": {
            "input": 15.0,
            "output": 60.0,
            "cached_input": 7.5
        },
        "o1-2024-12-17": {
            "input": 15.0,
            "output": 60.0,
            "cached_input": 7.5
        },
        "o1-mini": {
            "input": 3.0,
            "output": 12.0,
            "cached_input": 1.5
        },
        "o1-mini-2024-09-12": {
            "input": 3.0,
            "output": 12.0,
            "cached_input": 1.5
        },
        "o1-preview": {
            "input": 15.0,
            "output": 60.0,
            "cached_input": 7.5
        },
        "o1-preview-2024-09-12": {
            "input": 15.0,
            "output": 60.0,
            "cached_input": 7.5
        }
    }
    
    
    GEMINI_PRICING = {
        # Gemini 3 Series
        "gemini-3-pro-preview": {
            "input": 2.0,
            "output": 12.0,
            "cached_input": 0.5
        },
        
        # Gemini 2.5 Series
        "gemini-2.5-pro": {
            "input": 1.25,
            "output": 10.0,
            "cached_input": 0.3125
        },
        "gemini-2.5-pro-preview": {
            "input": 1.25,
            "output": 10.0,
            "cached_input": 0.3125
        },
        "gemini-2.5-flash": {
            "input": 0.30,
            "output": 2.50,
            "cached_input": 0.075
        },
        "gemini-2.5-flash-lite": {
            "input": 0.10,
            "output": 0.40,
            "cached_input": 0.025
        },
        "gemini-2.5-flash-preview-05-20": {
            "input": 0.15,
            "output": 0.60,
            "cached_input": 0.0375
        },
        
        # Gemini 2.0 Series
        "gemini-2.0-flash": {
            "input": 0.10,
            "output": 0.40,
            "cached_input": 0.025
        },
        "gemini-2.0-flash-lite": {
            "input": 0.075,
            "output": 0.30,
            "cached_input": 0.01875
        },
        "gemini-2.0-flash-exp": {
            "input": 0.0,  # Free tier experimental
            "output": 0.0,
            "cached_input": 0.0
        },
        
        # Gemini 1.5 Series
        "gemini-1.5-pro": {
            "input": 1.25,
            "output": 5.0,
            "cached_input": 0.3125
        },
        "gemini-1.5-pro-latest": {
            "input": 1.25,
            "output": 5.0,
            "cached_input": 0.3125
        },
        "gemini-1.5-flash": {
            "input": 0.075,
            "output": 0.30,
            "cached_input": 0.01875
        },
        "gemini-1.5-flash-latest": {
            "input": 0.075,
            "output": 0.30,
            "cached_input": 0.01875
        },
        "gemini-1.5-flash-8b": {
            "input": 0.0375,
            "output": 0.15,
            "cached_input": 0.009375
        },
        "gemini-1.5-flash-8b-latest": {
            "input": 0.0375,
            "output": 0.15,
            "cached_input": 0.009375
        },
        
        # Legacy/Preview
        "gemini-3-flash-preview": {
            "input": 0.0,  # Preview/experimental
            "output": 0.0,
            "cached_input": 0.0
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
