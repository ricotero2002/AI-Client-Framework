"""
Chat Example - Interactive Conversation with Database Persistence
Demonstrates the chat system with prompt tracking and conversation history
"""
from chat import ChatSession
from client_factory import create_client
from prompt import Prompt


def main():
    print("=" * 60)
    print("AI Chat System - Interactive Demo")
    print("=" * 60)
    
    # Create a new chat session
    chat = ChatSession(title="Technical Discussion")
    print(f"\n✓ Created new chat session: {chat}")
    
    # Create client
    client = create_client('openai')
    client.select_model('gpt-4o-mini')
    print(f"✓ Using model: {client.current_model}")
    
    # Create a prompt template for the conversation
    prompt = Prompt()
    prompt.set_system("You are a helpful technical assistant. Provide clear, concise answers.")
    prompt.save()  # Save to database to get ID
    print(f"✓ Created prompt (ID: {prompt.get_id()})")
    
    print("\n" + "=" * 60)
    print("Chat started! Type 'exit' to quit, 'stats' for usage statistics")
    print("=" * 60 + "\n")
    
    # Interactive chat loop
    while True:
        try:
            # Get user input
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() == 'exit':
                print("\n👋 Goodbye!")
                break
            
            if user_input.lower() == 'stats':
                # Show usage statistics
                stats = prompt.get_usage_stats()
                print("\n📊 Prompt Usage Statistics:")
                print(f"  Total calls: {stats['total_calls']}")
                print(f"  Total input tokens: {stats['total_input_tokens']:,}")
                print(f"  Total output tokens: {stats['total_output_tokens']:,}")
                print(f"  Total cost: ${stats['total_cost']:.4f}")
                if stats['avg_quality_score']:
                    print(f"  Avg quality score: {stats['avg_quality_score']:.2f}")
                print()
                continue
            
            # Add user message to chat
            chat.add_message('user', user_input)
            
            # Set user input in the prompt
            prompt.set_user_input(user_input)
            
            # Get response (automatically tracks model and prompt_id)
            print("Assistant: ", end="", flush=True)
            response = chat.get_response(client, prompt)
            print(response)
            print()
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")
    
    # Save conversation
    chat.save()
    print(f"\n✓ Conversation saved (ID: {chat.conversation_id})")
    
    # Show final statistics
    print("\n" + "=" * 60)
    print("Session Summary")
    print("=" * 60)
    print(f"Messages: {len(chat.messages)}")
    stats = prompt.get_usage_stats()
    print(f"Total tokens: {stats['total_input_tokens'] + stats['total_output_tokens']:,}")
    print(f"Total cost: ${stats['total_cost']:.4f}")
    print()


def load_existing_conversation():
    """Example: Load and continue an existing conversation"""
    print("Loading existing conversation...")
    
    # List available conversations
    from database import get_db_manager
    db = get_db_manager()
    conversations = db.list_conversations(limit=10)
    
    if not conversations:
        print("No existing conversations found.")
        return
    
    print("\nAvailable conversations:")
    for conv in conversations:
        print(f"  [{conv.id}] {conv.title} - {len(conv.messages)} messages")
    
    # Load a conversation
    conv_id = int(input("\nEnter conversation ID to load: "))
    chat = ChatSession.load(conv_id)
    
    print(f"\n✓ Loaded conversation: {chat}")
    print(f"Message history ({len(chat.messages)} messages):")
    
    for msg in chat.get_history(limit=5):
        role = msg['role'].upper()
        content = msg['content'][:50] + "..." if len(msg['content']) > 50 else msg['content']
        print(f"  {role}: {content}")
        if msg['model']:
            print(f"    (Model: {msg['model']}, Prompt ID: {msg['prompt_id']})")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--load":
        load_existing_conversation()
    else:
        main()
