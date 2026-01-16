"""
Prompt Tracking Example - Usage Analytics and Monitoring
Demonstrates prompt usage tracking and statistics
"""
from client_factory import create_client
from prompt import Prompt
from database import get_db_manager


def example_basic_tracking():
    """Example: Basic prompt usage tracking"""
    print("=" * 60)
    print("Example 1: Basic Prompt Usage Tracking")
    print("=" * 60 + "\n")
    
    # Create a prompt
    prompt = Prompt()
    prompt.set_system("You are a helpful assistant that explains concepts clearly.")
    prompt.set_user_input("Explain quantum computing in simple terms")
    
    # Save prompt to database
    prompt.save()
    print(f"✓ Prompt saved with ID: {prompt.get_id()}")
    
    # Create client and get response
    client = create_client('gemini')
    
    
    print(f"✓ Getting response from {client.current_model}...")
    response, usage = client.get_response(prompt)
    
    print(f"\n📝 Response: {response[:100]}...")
    print(f"\n📊 Token Usage:")
    print(f"  Input: {usage.prompt_tokens}")
    print(f"  Output: {usage.completion_tokens}")
    print(f"  Total: {usage.total_tokens}")
    
    # Calculate cost
    cost = client.estimate_cost(
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens
    )
    print(f"  Cost: ${cost.total_cost:.6f}")
    
    # Save usage to database
    prompt.save_usage(
        model=client.current_model,
        input_tokens=usage.prompt_tokens,
        output_tokens=usage.completion_tokens,
        response=response,
        cost=cost.total_cost,
        quality_score=0.9  # Optional: you could implement quality scoring
    )
    print(f"\n✓ Usage data saved to database")


def example_usage_statistics():
    """Example: Retrieve and analyze usage statistics"""
    print("\n" + "=" * 60)
    print("Example 2: Usage Statistics Analysis")
    print("=" * 60 + "\n")
    
    # Create a reusable prompt
    prompt = Prompt()
    prompt.set_system("You are a code reviewer. Provide constructive feedback.")
    prompt.save()
    
    client = create_client('gemini')
    
    # Simulate multiple uses of the same prompt
    code_samples = [
        "def add(a, b): return a + b",
        "for i in range(10): print(i)",
        "x = [i**2 for i in range(5)]"
    ]
    
    print(f"Using prompt {prompt.get_id()} for {len(code_samples)} code reviews...\n")
    
    for i, code in enumerate(code_samples, 1):
        prompt.set_user_input(f"Review this code:\n{code}")
        response, usage = client.get_response(prompt)
        
        cost = client.estimate_cost(
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens
        )
        
        prompt.save_usage(
            model=client.current_model,
            input_tokens=usage.prompt_tokens,
            output_tokens=usage.completion_tokens,
            response=response,
            cost=cost.total_cost
        )
        
        print(f"  Review {i}: {usage.total_tokens} tokens, ${cost.total_cost:.6f}")
    
    # Get aggregated statistics
    stats = prompt.get_usage_stats()
    
    print(f"\n📊 Aggregated Statistics for Prompt {prompt.get_id()}:")
    print(f"  Total calls: {stats['total_calls']}")
    print(f"  Total input tokens: {stats['total_input_tokens']:,}")
    print(f"  Total output tokens: {stats['total_output_tokens']:,}")
    print(f"  Total tokens: {stats['total_input_tokens'] + stats['total_output_tokens']:,}")
    print(f"  Total cost: ${stats['total_cost']:.6f}")
    print(f"  Avg tokens per call: {(stats['total_input_tokens'] + stats['total_output_tokens']) / stats['total_calls']:.1f}")
    print(f"  Avg cost per call: ${stats['total_cost'] / stats['total_calls']:.6f}")


def example_compare_prompts():
    """Example: Compare different prompt strategies"""
    print("\n" + "=" * 60)
    print("Example 3: Comparing Prompt Strategies")
    print("=" * 60 + "\n")
    
    client = create_client('gemini')
    
    # Strategy 1: Simple prompt
    prompt1 = Prompt()
    prompt1.set_system("You are helpful.")
    prompt1.set_user_input("What is Python?")
    prompt1.save()
    
    response1, usage1 = client.get_response(prompt1)
    cost1 = client.estimate_cost(usage1.prompt_tokens, usage1.completion_tokens)
    prompt1.save_usage(client.current_model, usage1.prompt_tokens, usage1.completion_tokens, 
                       response1, cost1.total_cost)
    
    # Strategy 2: Detailed prompt with few-shot
    prompt2 = Prompt()
    prompt2.set_system("You are a programming expert. Provide detailed, educational explanations.")
    prompt2.add_few_shot_example(
        "What is JavaScript?",
        "JavaScript is a high-level programming language primarily used for web development..."
    )
    prompt2.set_user_input("What is Python?")
    prompt2.save()
    
    response2, usage2 = client.get_response(prompt2)
    cost2 = client.estimate_cost(usage2.prompt_tokens, usage2.completion_tokens)
    prompt2.save_usage(client.current_model, usage2.prompt_tokens, usage2.completion_tokens,
                       response2, cost2.total_cost)
    
    # Compare
    print("Strategy 1 (Simple):")
    print(f"  Tokens: {usage1.total_tokens}, Cost: ${cost1.total_cost:.6f}")
    print(f"  Response length: {len(response1)} chars")
    
    print("\nStrategy 2 (Detailed + Few-shot):")
    print(f"  Tokens: {usage2.total_tokens}, Cost: ${cost2.total_cost:.6f}")
    print(f"  Response length: {len(response2)} chars")
    
    print(f"\nDifference:")
    print(f"  Token overhead: +{usage2.total_tokens - usage1.total_tokens} tokens")
    print(f"  Cost overhead: +${cost2.total_cost - cost1.total_cost:.6f}")
    print(f"  Response improvement: +{len(response2) - len(response1)} chars")


def example_list_all_prompts():
    """Example: List all prompts in database"""
    print("\n" + "=" * 60)
    print("Example 4: Database Overview")
    print("=" * 60 + "\n")
    
    db = get_db_manager()
    
    # This would require adding a method to DatabaseManager
    # For now, we'll just show the concept
    print("📚 All Prompts in Database:")
    print("  (This would list all saved prompts with their usage stats)")
    print("  Feature: Coming soon!")


if __name__ == "__main__":
    try:
        example_basic_tracking()
        example_usage_statistics()
        example_compare_prompts()
        example_list_all_prompts()
        
        print("\n" + "=" * 60)
        print("✓ All examples completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
