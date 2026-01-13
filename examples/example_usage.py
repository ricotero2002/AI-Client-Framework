"""
Example Usage of AI Client Framework
Demonstrates how to use the framework with different providers
"""
from client_factory import create_client, ClientFactory
from base_client import BaseAIClient


def example_basic_usage():
    """Basic usage example - switching between providers"""
    print("=" * 60)
    print("EXAMPLE 1: Basic Usage - Switching Between Providers")
    print("=" * 60)
    
    # Create OpenAI client
    print("\n1. Using OpenAI:")
    openai_client = create_client('openai')
    openai_client.select_model('gpt-5-nano')
    
    messages = [
        {'role': 'system', 'content': 'You are an american comedian.'},
        {'role': 'user', 'content': 'Tell me a joke.'}
    ]
    
    try:
        response, usage = openai_client.get_response(messages)
        print(f"Response: {response}")
        print(f"Token Usage: {usage}")
        cost = openai_client.estimate_cost(
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        cached_tokens=0
        )
        print(f"Token Price: {cost}")

    except Exception as e:
        print(f"Error: {e}")
    
    # Create Gemini client
    print("\n2. Using Gemini:")
    try:
        gemini_client = create_client('gemini')
        gemini_client.select_model('gemini-2.0-flash-exp')
        
        response, usage = gemini_client.get_response(messages)
        print(f"Response: {response}")
        print(f"Token Usage: {usage}")
        cost = gemini_client.estimate_cost(
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        cached_tokens=0
        )
        print(f"Token Price: {cost}")
    except Exception as e:
        print(f"Error: {e}")


def example_token_counting():
    """Example of token counting and cost estimation"""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Token Counting and Cost Estimation")
    print("=" * 60)
    
    client = create_client('openai')
    client.select_model('gpt-4o-mini')
    
    # Count tokens in text
    text = "This is a sample text for token counting. It contains multiple sentences."
    token_count = client.count_tokens(text)
    print(f"\nText: {text}")
    print(f"Token count: {token_count}")
    
    # Count tokens in messages
    messages = [
        {'role': 'system', 'content': 'You are a helpful coding assistant specialized in Python.'},
        {'role': 'user', 'content': 'Explain list comprehensions in Python with examples.'}
    ]
    
    total_tokens = client.count_messages_tokens(messages)
    print(f"\nMessages token count: {total_tokens}")
    
    # Estimate cost
    cost = client.estimate_cost(
        prompt_tokens=total_tokens,
        completion_tokens=500,  # Estimated response length
        cached_tokens=0
    )
    
    print(f"\nCost Estimation:")
    print(f"  Prompt cost: ${cost.prompt_cost:.6f}")
    print(f"  Completion cost: ${cost.completion_cost:.6f}")
    print(f"  Total cost: ${cost.total_cost:.6f}")


def example_caching_optimization():
    """Example of prompt caching optimization"""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Prompt Caching Optimization")
    print("=" * 60)
    
    client = create_client('openai')
    client.select_model('gpt-4o-mini')
    
    # Example with long system message (good for caching)
    messages = [
        {
            'role': 'system', 
            'content': '''You are an expert Python developer with deep knowledge of:
            - Object-oriented programming and design patterns
            - Functional programming paradigms
            - Asynchronous programming with asyncio
            - Testing with pytest and unittest
            - Performance optimization techniques
            - Best practices for code organization
            - Type hints and static type checking
            - Documentation standards
            
            When answering questions:
            1. Provide clear, concise explanations
            2. Include practical code examples
            3. Mention potential pitfalls
            4. Suggest best practices
            5. Consider performance implications
            '''
        },
        {'role': 'user', 'content': 'How do I implement a singleton pattern?'}
    ]
    
    # Get caching recommendations
    recommendation = client.optimize_prompt_for_caching(messages)
    
    print(f"\nShould use caching: {recommendation.should_use_caching}")
    print(f"Reason: {recommendation.reason}")
    print(f"Estimated monthly savings: ${recommendation.estimated_savings:.4f}")
    
    print("\nOptimization Tips:")
    for tip in recommendation.optimization_tips:
        print(f"  {tip}")
    
    if recommendation.optimized_structure:
        analysis = recommendation.optimized_structure['analysis']
        print(f"\nPrompt Analysis:")
        print(f"  Total tokens: {analysis['total_tokens']}")
        print(f"  Static tokens: {analysis['static_tokens']}")
        print(f"  Dynamic tokens: {analysis['dynamic_tokens']}")
        print(f"  Cacheable portion: {analysis['cacheable_portion']}")


def example_model_comparison():
    """Compare different models and their costs"""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Model Comparison")
    print("=" * 60)
    
    client = create_client('openai')
    
    # Sample usage
    prompt_tokens = 1000
    completion_tokens = 500
    
    print(f"\nFor {prompt_tokens} prompt tokens and {completion_tokens} completion tokens:\n")
    
    models = client.get_available_models()
    for model in models:
        client.select_model(model)
        cost = client.estimate_cost(prompt_tokens, completion_tokens)
        supports_cache = client.supports_caching()
        
        print(f"{model}:")
        print(f"  Cost: ${cost.total_cost:.6f}")
        print(f"  Caching support: {'Yes' if supports_cache else 'No'}")
        
        if supports_cache:
            # Show cost with caching
            cached_cost = client.estimate_cost(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cached_tokens=prompt_tokens  # Assume all prompt tokens cached
            )
            savings = cost.total_cost - cached_cost.total_cost
            print(f"  With caching: ${cached_cost.total_cost:.6f} (saves ${savings:.6f})")
        print()


def example_available_providers():
    """Show all available providers"""
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Available Providers and Models")
    print("=" * 60)
    
    providers = ClientFactory.get_available_providers()
    print(f"\nAvailable providers: {', '.join(providers)}\n")
    
    for provider in providers:
        try:
            client = create_client(provider)
            models = client.get_available_models()
            print(f"{provider.upper()}:")
            for model in models:
                print(f"  - {model}")
            print()
        except Exception as e:
            print(f"{provider.upper()}: Error - {e}\n")


def example_custom_client_registration():
    """Example of registering a custom client"""
    print("\n" + "=" * 60)
    print("EXAMPLE 6: Custom Client Registration")
    print("=" * 60)
    
    # This is just a demonstration - you would implement a real client
    print("\nTo add a custom client:")
    print("""
    from base_client import BaseAIClient
    from client_factory import ClientFactory
    
    class AnthropicClient(BaseAIClient):
        # Implement all abstract methods
        def select_model(self, model_name: str):
            # Implementation
            pass
        
        def get_response(self, messages, **kwargs):
            # Implementation
            pass
        
        # ... implement other methods
    
    # Register the client
    ClientFactory.register_client('anthropic', AnthropicClient)
    
    # Now you can use it
    client = create_client('anthropic')
    """)


def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("AI CLIENT FRAMEWORK - USAGE EXAMPLES")
    print("=" * 60)
    
    try:
        example_basic_usage()
    except Exception as e:
        print(f"Example 1 failed: {e}")
    
    try:
        example_token_counting()
    except Exception as e:
        print(f"Example 2 failed: {e}")
    
    try:
        example_caching_optimization()
    except Exception as e:
        print(f"Example 3 failed: {e}")
    
    '''
    try:
        example_model_comparison()
    except Exception as e:
        print(f"Example 4 failed: {e}")
    
    try:
        example_available_providers()
    except Exception as e:
        print(f"Example 5 failed: {e}")
    
    example_custom_client_registration()
    '''
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
