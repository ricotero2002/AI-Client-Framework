"""
Test to verify compression timestamp fix
"""
from chat import ChatSession
from client_factory import create_client
from prompt import Prompt
from datetime import datetime, timedelta


def test_compression_timestamp_order():
    """Test that compression summary has correct timestamp to maintain order"""
    print("=" * 60)
    print("Testing Compression Timestamp Order")
    print("=" * 60)
    
    # Create chat with max_messages=3
    chat = ChatSession(title="Timestamp Test", max_messages=3)
    
    # Add 6 messages (will trigger compression)
    print("\n[*] Adding 6 messages...")
    for i in range(6):
        chat.add_message('user', f'Message {i}')
        print(f"  Added message {i}")
    
    print(f"\nMessages before optimization: {len(chat.messages)}")
    
    # Create client for compression
    client = create_client('gemini')
    client.select_model('gemini-2.0-flash-lite')
    
    # Trigger optimization
    print("\n[*] Triggering optimization...")
    chat.optimize_context(client)
    
    print(f"\nMessages after optimization: {len(chat.messages)}")
    
    # Check message order by timestamp
    print("\n[*] Checking message timestamps:")
    for i, msg in enumerate(chat.messages):
        is_compressed = " [COMPRESSED]" if msg.get('is_compressed', 0) == 1 else ""
        print(f"  {i+1}. {msg['timestamp']}{is_compressed}: {msg['content'][:40]}...")
    
    # Verify timestamps are in order
    timestamps = [msg['timestamp'] for msg in chat.messages]
    sorted_timestamps = sorted(timestamps)
    
    if timestamps == sorted_timestamps:
        print("\n[SUCCESS] Messages are in correct chronological order!")
    else:
        print("\n[FAIL] Messages are NOT in chronological order!")
        print(f"  Expected: {sorted_timestamps}")
        print(f"  Got: {timestamps}")
    
    # Reload chat and verify
    print(f"\n[*] Reloading chat (ID: {chat.conversation_id})...")
    chat2 = ChatSession.load(chat.conversation_id)
    
    print(f"\nMessages after reload: {len(chat2.messages)}")
    
    # Check that summary is still before recent messages
    compressed_msgs = [msg for msg in chat2.messages if msg.get('is_compressed', 0) == 1]
    non_compressed_msgs = [msg for msg in chat2.messages if msg.get('is_compressed', 0) == 0]
    
    print(f"\n[*] Message breakdown:")
    print(f"  Compressed summaries: {len(compressed_msgs)}")
    print(f"  Recent messages: {len(non_compressed_msgs)}")
    
    if compressed_msgs and non_compressed_msgs:
        last_compressed_time = compressed_msgs[-1]['timestamp']
        first_recent_time = non_compressed_msgs[0]['timestamp']
        
        if last_compressed_time <= first_recent_time:
            print(f"\n[SUCCESS] Summary timestamp ({last_compressed_time}) is before recent messages ({first_recent_time})")
        else:
            print(f"\n[FAIL] Summary timestamp ({last_compressed_time}) is AFTER recent messages ({first_recent_time})")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_compression_timestamp_order()
