"""
Test script to verify chat system fixes
"""
from chat import ChatSession
from client_factory import create_client
from prompt import Prompt
from database import get_db_manager


def test_max_messages_persistence():
    """Test that max_messages is saved and loaded correctly"""
    print("Testing max_messages persistence...")
    
    # Create chat with custom max_messages
    chat1 = ChatSession(title="Test Max Messages", max_messages=5)
    assert chat1.max_messages == 5
    conv_id = chat1.conversation_id
    print(f"✓ Created chat with max_messages=5 (ID: {conv_id})")
    
    # Load the chat
    chat2 = ChatSession.load(conv_id)
    assert chat2.max_messages == 5, f"Expected 5, got {chat2.max_messages}"
    print("✓ max_messages loaded correctly from database")


def test_message_loading_limit():
    """Test that messages are loaded up to max_messages"""
    print("\nTesting message loading limit...")
    
    # Create chat with max_messages=3
    chat = ChatSession(title="Test Loading", max_messages=3)
    
    # Add 5 messages
    for i in range(5):
        chat.add_message('user', f'Message {i}')
    
    conv_id = chat.conversation_id
    print(f"✓ Added 5 messages to chat (max_messages=3)")
    
    # Reload chat
    chat2 = ChatSession.load(conv_id)
    print(f"✓ Loaded chat, got {len(chat2.messages)} messages")
    
    # Should load only last 3 messages
    assert len(chat2.messages) <= 3, f"Expected <=3 messages, got {len(chat2.messages)}"
    print("✓ Message loading respects max_messages limit")


def test_conversation_context_separation():
    """Test that conversation context doesn't overwrite few-shots"""
    print("\nTesting conversation context separation...")
    
    # Create prompt with few-shot examples
    prompt = Prompt()
    prompt.set_system("You are helpful")
    prompt.add_few_shot_example("What is 2+2?", "4")
    prompt.add_few_shot_example("What is 3+3?", "6")
    
    # Add conversation context
    context = [
        {'role': 'user', 'content': 'Hello'},
        {'role': 'assistant', 'content': 'Hi!'}
    ]
    prompt.set_conversation_context(context)
    
    # Check that few-shots are still there
    assert len(prompt._few_shot_examples) == 2, "Few-shots should not be cleared"
    assert len(prompt._conversation_context) == 2, "Context should be stored"
    print("✓ Few-shots preserved when setting conversation context")
    
    # Check messages
    messages = prompt.to_messages()
    print(f"✓ Generated {len(messages)} messages")
    
    # Should have: system + 2 few-shots (4 msgs) + 2 context (2 msgs) = 6 messages (no user input yet)
    # Actually: system(1) + few-shot1(2) + few-shot2(2) + context(2) = 7
    print(f"  Message breakdown:")
    for i, msg in enumerate(messages):
        print(f"    {i+1}. {msg['role']}: {msg['content'][:30]}...")


def test_compression_flag():
    """Test that compression flag is saved correctly"""
    print("\nTesting compression flag...")
    
    db = get_db_manager()
    chat = ChatSession(title="Test Compression", max_messages=3)
    
    # Add normal message
    chat.add_message('user', 'Normal message')
    
    # Add compressed message directly
    db.add_message(
        conversation_id=chat.conversation_id,
        role='system',
        content='[Summary]: This is a summary',
        is_compressed=1
    )
    
    # Reload and check
    chat2 = ChatSession.load(chat.conversation_id)
    compressed_msgs = [msg for msg in chat2.messages if msg.get('is_compressed', 0) == 1]
    
    assert len(compressed_msgs) > 0, "Should have at least one compressed message"
    print(f"✓ Found {len(compressed_msgs)} compressed message(s)")


def test_context_limit():
    """Test that conversation context is limited to max_context_messages"""
    print("\nTesting conversation context limit...")
    
    prompt = Prompt()
    prompt.set_system("You are helpful")
    
    # Add 15 context messages
    context = []
    for i in range(15):
        context.append({'role': 'user', 'content': f'User {i}'})
        context.append({'role': 'assistant', 'content': f'Assistant {i}'})
    
    # Set context with max of 10
    prompt.set_conversation_context(context, max_context_messages=10)
    
    messages = prompt.to_messages()
    
    # Count context messages (exclude system)
    context_msgs = [m for m in messages if m['role'] in ['user', 'assistant']]
    
    print(f"✓ Added 30 context messages, limited to 10, got {len(context_msgs)} in output")
    assert len(context_msgs) <= 10, f"Expected <=10 context messages, got {len(context_msgs)}"


def main():
    print("=" * 60)
    print("Chat System Fixes Verification")
    print("=" * 60)
    
    try:
        test_max_messages_persistence()
        test_message_loading_limit()
        test_conversation_context_separation()
        test_compression_flag()
        test_context_limit()
        
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
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
