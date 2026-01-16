"""
Test script to verify chat system implementation
"""
from chat import ChatSession
from client_factory import create_client
from prompt import Prompt
from database import get_db_manager


def test_database():
    """Test database initialization"""
    print("Testing database initialization...")
    db = get_db_manager()
    print("✓ Database initialized successfully")
    return db


def test_prompt_persistence():
    """Test prompt save and retrieval"""
    print("\nTesting prompt persistence...")
    
    prompt = Prompt()
    prompt.set_system("Test system message")
    prompt.add_few_shot_example("Test user", "Test assistant")
    
    # Save prompt
    prompt.save()
    prompt_id = prompt.get_id()
    
    assert prompt_id is not None, "Prompt ID should not be None after save"
    print(f"✓ Prompt saved with ID: {prompt_id}")
    
    # Test usage stats (should be empty)
    stats = prompt.get_usage_stats()
    assert stats['total_calls'] == 0, "New prompt should have 0 calls"
    print("✓ Usage stats retrieved successfully")
    
    return prompt


def test_chat_session():
    """Test chat session creation and message handling"""
    print("\nTesting chat session...")
    
    # Create chat session
    chat = ChatSession(title="Test Conversation")
    assert chat.conversation_id is not None, "Chat should have conversation ID"
    print(f"✓ Chat session created (ID: {chat.conversation_id})")
    
    # Add messages
    chat.add_message('user', 'Hello', model=None, prompt_id=None)
    chat.add_message('assistant', 'Hi there!', model='gpt-4o', prompt_id=1)
    
    assert len(chat.messages) == 2, "Should have 2 messages"
    print(f"✓ Messages added successfully ({len(chat.messages)} messages)")
    
    # Get history
    history = chat.get_history()
    assert len(history) == 2, "History should have 2 messages"
    assert history[0]['role'] == 'user'
    assert history[1]['role'] == 'assistant'
    assert history[1]['model'] == 'gpt-4o'
    print("✓ Message history retrieved successfully")
    
    return chat


def test_chat_load():
    """Test loading existing conversation"""
    print("\nTesting conversation loading...")
    
    # Create and save a conversation
    chat1 = ChatSession(title="Load Test")
    chat1.add_message('user', 'Test message')
    conv_id = chat1.conversation_id
    
    # Load the conversation
    chat2 = ChatSession.load(conv_id)
    assert chat2.conversation_id == conv_id
    assert len(chat2.messages) == 1
    assert chat2.messages[0]['content'] == 'Test message'
    print(f"✓ Conversation loaded successfully (ID: {conv_id})")
    
    return chat2


def test_integration_simple():
    """Test simple integration without actual API calls"""
    print("\nTesting integration (without API calls)...")
    
    # Create prompt
    prompt = Prompt()
    prompt.set_system("You are helpful")
    prompt.save()
    
    # Create chat
    chat = ChatSession(title="Integration Test")
    
    # Add user message
    chat.add_message('user', 'Hello')
    
    # Simulate response (without actual API call)
    chat.add_message(
        'assistant',
        'Hello! How can I help?',
        model='gpt-4o-mini',
        prompt_id=prompt.get_id()
    )
    
    # Save usage
    prompt.save_usage(
        model='gpt-4o-mini',
        input_tokens=10,
        output_tokens=5,
        response='Hello! How can I help?',
        cost=0.0001
    )
    
    # Check stats
    stats = prompt.get_usage_stats()
    assert stats['total_calls'] == 1
    assert stats['total_input_tokens'] == 10
    assert stats['total_output_tokens'] == 5
    
    print("✓ Integration test passed")
    print(f"  - Chat has {len(chat.messages)} messages")
    print(f"  - Prompt used {stats['total_calls']} times")
    print(f"  - Total cost: ${stats['total_cost']:.6f}")


def main():
    print("=" * 60)
    print("Chat System Verification Tests")
    print("=" * 60)
    
    try:
        test_database()
        test_prompt_persistence()
        test_chat_session()
        test_chat_load()
        test_integration_simple()
        
        print("\n" + "=" * 60)
        print("✓ All tests passed successfully!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
