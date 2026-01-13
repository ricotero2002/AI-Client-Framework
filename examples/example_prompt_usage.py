"""
Example Usage of Prompt Class
Demonstrates how to use the new Prompt class for structured message handling
"""
from prompt import Prompt, create_simple_prompt
from client_factory import create_client


def example_simple_prompt():
    """Example 1: Simple prompt with just user input"""
    print("=" * 60)
    print("EXAMPLE 1: Simple Prompt")
    print("=" * 60)
    
    # Create a simple prompt
    prompt = Prompt().set_user_input("What is Python?")
    
    # Or use the helper function
    prompt = create_simple_prompt("What is Python?")
    
    # Print the prompt
    print("\nPrompt structure:")
    print(prompt.print_formatted())
    
    # Use with client
    client = create_client('gemini')
    client.select_model('gemini-2.0-flash-exp')
    
    try:
        response, usage = client.get_response(prompt)
        print(f"\nResponse: {response}")
        print(f"Tokens used: {usage.total_tokens}")
    except Exception as e:
        print(f"Error: {e}")


def example_with_system_message():
    """Example 2: Prompt with system message"""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Prompt with System Message")
    print("=" * 60)
    
    # Create prompt with system message
    prompt = (Prompt()
        .set_system("You are a helpful programming assistant specialized in Python.")
        .set_user_input("Explain list comprehensions"))
    
    # Print the prompt
    print("\nPrompt structure:")
    print(prompt.print_formatted())
    
    # Analyze for caching
    client = create_client('gemini')
    analysis = prompt.analyze_for_caching(client.count_tokens)
    
    print(f"\nCaching Analysis:")
    print(f"  Total tokens: {analysis.total_tokens}")
    print(f"  Static tokens: {analysis.static_tokens}")
    print(f"  Dynamic tokens: {analysis.dynamic_tokens}")
    print(f"  Cacheable: {analysis.cacheable_percentage:.1f}%")
    print(f"  Should use caching: {analysis.should_use_caching}")
    
    print("\nRecommendations:")
    for rec in analysis.recommendations:
        print(f"  {rec}")


def example_with_few_shot():
    """Example 3: Prompt with few-shot examples"""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Prompt with Few-Shot Examples")
    print("=" * 60)
    
    # Create prompt with few-shot examples
    prompt = (Prompt()
        .set_system("You are a concise programming expert. Answer in one sentence.")
        .add_few_shot_example(
            user="What is JavaScript?",
            assistant="JavaScript is a high-level programming language primarily used for web development."
        )
        .add_few_shot_example(
            user="What is Java?",
            assistant="Java is an object-oriented programming language designed for platform independence."
        )
        .set_user_input("What is Python?"))
    
    # Print the prompt
    print("\nPrompt structure:")
    print(prompt.print_formatted(max_length=80))
    
    # Analyze for caching
    client = create_client('gemini')
    analysis = prompt.analyze_for_caching(client.count_tokens)
    
    print(f"\nCaching Analysis:")
    print(f"  Total tokens: {analysis.total_tokens}")
    print(f"  Static tokens: {analysis.static_tokens} ({analysis.cacheable_percentage:.1f}%)")
    print(f"  Dynamic tokens: {analysis.dynamic_tokens}")
    
    # Use with client
    try:
        response, usage = client.get_response(prompt)
        print(f"\nResponse: {response}")
        print(f"Cost: ${client.estimate_cost(usage.prompt_tokens, usage.completion_tokens).total_cost:.6f}")
    except Exception as e:
        print(f"Error: {e}")


def example_validation():
    """Example 5: Prompt validation"""
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Prompt Validation")
    print("=" * 60)
    
    # Valid prompt
    valid_prompt = Prompt().set_user_input("Hello")
    is_valid, error = valid_prompt.validate()
    print(f"Valid prompt: {is_valid}, Error: {error}")
    
    # Invalid prompt (no user input)
    invalid_prompt = Prompt().set_system("System message only")
    is_valid, error = invalid_prompt.validate()
    print(f"Invalid prompt: {is_valid}, Error: {error}")
    
    # Empty prompt
    empty_prompt = Prompt()
    print(f"Empty prompt: {empty_prompt.is_empty()}")


def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("PROMPT CLASS - USAGE EXAMPLES")
    print("=" * 60)
    
    try:
        example_simple_prompt()
    except Exception as e:
        print(f"Example 1 failed: {e}")
    
    try:
        example_with_system_message()
    except Exception as e:
        print(f"Example 2 failed: {e}")
    
    try:
        example_with_few_shot()
    except Exception as e:
        print(f"Example 3 failed: {e}")
    
    try:
        example_validation()
    except Exception as e:
        print(f"Example 5 failed: {e}")
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
