"""
Prompt Optimization Utilities
Provides tools for analyzing and optimizing prompts for better performance and cost efficiency
"""
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from config import Config


@dataclass
class PromptAnalysis:
    """Analysis results for a prompt"""
    total_tokens: int
    static_tokens: int  # Tokens that don't change between requests
    dynamic_tokens: int  # Tokens that vary
    message_count: int
    has_system_message: bool
    cacheable_portion: float  # Percentage of prompt that could be cached


class PromptOptimizer:
    """Utility class for prompt optimization"""
    
    @staticmethod
    def analyze_prompt_structure(
        messages: List[Dict[str, str]], 
        token_counter_fn
    ) -> PromptAnalysis:
        """
        Analyze the structure of a prompt to identify optimization opportunities
        
        Args:
            messages: List of message dictionaries
            token_counter_fn: Function to count tokens in text
        
        Returns:
            PromptAnalysis with detailed breakdown
        """
        total_tokens = 0
        static_tokens = 0
        has_system = False
        
        for i, msg in enumerate(messages):
            content = msg.get('content', '')
            tokens = token_counter_fn(content)
            total_tokens += tokens
            
            # System messages and early messages are typically static
            if msg.get('role') == 'system':
                has_system = True
                static_tokens += tokens
            elif i < len(messages) - 2:  # All but last 2 messages are likely static
                static_tokens += tokens
        
        dynamic_tokens = total_tokens - static_tokens
        cacheable_portion = (static_tokens / total_tokens * 100) if total_tokens > 0 else 0
        
        return PromptAnalysis(
            total_tokens=total_tokens,
            static_tokens=static_tokens,
            dynamic_tokens=dynamic_tokens,
            message_count=len(messages),
            has_system_message=has_system,
            cacheable_portion=cacheable_portion
        )
    
    @staticmethod
    def suggest_caching_optimization(
        analysis: PromptAnalysis,
        supports_caching: bool,
        pricing: Optional[Dict[str, float]] = None
    ) -> List[str]:
        """
        Generate specific suggestions for caching optimization
        
        Args:
            analysis: PromptAnalysis object
            supports_caching: Whether the model supports caching
            pricing: Pricing information for the model
        
        Returns:
            List of optimization suggestions
        """
        suggestions = []
        
        if not supports_caching:
            suggestions.append("⚠️ This model doesn't support prompt caching")
            return suggestions
        
        # Check if prompt is large enough for caching
        if analysis.static_tokens < Config.MIN_TOKENS_FOR_CACHING:
            suggestions.append(
                f"💡 Static portion ({analysis.static_tokens} tokens) is below "
                f"minimum threshold ({Config.MIN_TOKENS_FOR_CACHING} tokens) for effective caching"
            )
        else:
            suggestions.append(
                f"✅ Static portion ({analysis.static_tokens} tokens) is suitable for caching"
            )
        
        # Analyze cacheable portion
        if analysis.cacheable_portion > 70:
            suggestions.append(
                f"🎯 Excellent caching potential: {analysis.cacheable_portion:.1f}% of prompt is static"
            )
        elif analysis.cacheable_portion > 40:
            suggestions.append(
                f"👍 Good caching potential: {analysis.cacheable_portion:.1f}% of prompt is static"
            )
        else:
            suggestions.append(
                f"⚠️ Low caching potential: Only {analysis.cacheable_portion:.1f}% of prompt is static"
            )
        
        # Structure recommendations
        if not analysis.has_system_message:
            suggestions.append(
                "💡 Consider adding a system message with static instructions for better caching"
            )
        
        if analysis.dynamic_tokens > analysis.static_tokens:
            suggestions.append(
                "💡 Move variable/dynamic content to the end of your messages for better cache hits"
            )
        
        # Cost estimation if pricing available
        if pricing and pricing.get('cached_input'):
            cache_discount = (1 - pricing['cached_input'] / pricing['input']) * 100
            potential_savings = (
                analysis.static_tokens / 1_000_000 * 
                (pricing['input'] - pricing['cached_input'])
            )
            suggestions.append(
                f"💰 Caching provides {cache_discount:.0f}% discount on cached tokens "
                f"(~${potential_savings:.4f} savings per request on static portion)"
            )
        
        return suggestions
    
    @staticmethod
    def restructure_for_caching(
        messages: List[Dict[str, str]]
    ) -> Tuple[List[Dict[str, str]], str]:
        """
        Suggest a restructured version of messages optimized for caching
        
        Args:
            messages: Original list of messages
        
        Returns:
            Tuple of (optimized_messages, explanation)
        """
        if len(messages) <= 1:
            return messages, "Prompt is too short to optimize"
        
        optimized = []
        explanation_parts = []
        
        # Separate system messages (should be first for caching)
        system_msgs = [m for m in messages if m.get('role') == 'system']
        other_msgs = [m for m in messages if m.get('role') != 'system']
        
        if system_msgs:
            optimized.extend(system_msgs)
            explanation_parts.append("✓ System messages placed first (best for caching)")
        else:
            explanation_parts.append("💡 Consider adding a system message with static instructions")
        
        # Add other messages
        if len(other_msgs) > 2:
            # Static context messages
            optimized.extend(other_msgs[:-2])
            explanation_parts.append(
                f"✓ {len(other_msgs) - 2} context messages placed before dynamic content"
            )
            # Dynamic messages at the end
            optimized.extend(other_msgs[-2:])
            explanation_parts.append("✓ Recent/dynamic messages placed at the end")
        else:
            optimized.extend(other_msgs)
        
        explanation = "\n".join(explanation_parts)
        return optimized, explanation
    
    @staticmethod
    def estimate_cache_savings(
        requests_per_day: int,
        static_tokens: int,
        pricing: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Estimate cost savings from using caching
        
        Args:
            requests_per_day: Number of requests per day
            static_tokens: Number of static tokens that can be cached
            pricing: Pricing information with 'input' and 'cached_input' keys
        
        Returns:
            Dictionary with savings estimates
        """
        if not pricing.get('cached_input'):
            return {
                "daily_savings": 0,
                "monthly_savings": 0,
                "yearly_savings": 0,
                "note": "Caching not available for this model"
            }
        
        # First request pays full price, subsequent requests use cache
        tokens_per_million = static_tokens / 1_000_000
        cost_without_cache = requests_per_day * tokens_per_million * pricing['input']
        
        # With cache: first request full price, rest cached
        cost_with_cache = (
            tokens_per_million * pricing['input'] +  # First request
            (requests_per_day - 1) * tokens_per_million * pricing['cached_input']  # Cached
        )
        
        daily_savings = cost_without_cache - cost_with_cache
        
        return {
            "daily_savings": daily_savings,
            "monthly_savings": daily_savings * 30,
            "yearly_savings": daily_savings * 365,
            "cache_hit_rate": ((requests_per_day - 1) / requests_per_day * 100) if requests_per_day > 0 else 0,
            "cost_reduction_percent": (daily_savings / cost_without_cache * 100) if cost_without_cache > 0 else 0
        }
