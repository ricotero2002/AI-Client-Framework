"""
Interactive Chat Test - Manual Testing Tool
Use this to test the chat system interactively
"""
from chat import ChatSession
from client_factory import create_client
from prompt import Prompt
from database import get_db_manager


def create_new_chat():
    """Create a new chat session"""
    print("\n" + "="*60)
    print("Creating New Chat Session")
    print("="*60)
    
    # Get chat configuration
    title = input("Chat title (default: 'Test Chat'): ").strip() or "Test Chat"
    max_msg = input("Max messages before compression (default: 10): ").strip()
    max_messages = int(max_msg) if max_msg else 10
    
    # Create chat
    chat = ChatSession(title=title, max_messages=max_messages)
    print(f"\n[+] Created chat session (ID: {chat.conversation_id})")
    
    # Configure prompt
    print("\n" + "-"*60)
    print("Configure Prompt")
    print("-"*60)
    
    system_msg = input("System message (default: helpful assistant): ").strip()
    if not system_msg:
        system_msg = "You are a helpful AI assistant. Provide clear and concise answers."
    
    prompt = Prompt()
    prompt.set_system(system_msg)
    
    # Optional: Add few-shot examples
    add_examples = input("\nAdd few-shot examples? (y/n, default: n): ").strip().lower()
    if add_examples == 'y':
        print("\nEnter few-shot examples (empty user input to finish):")
        while True:
            user_ex = input("  User: ").strip()
            if not user_ex:
                break
            assistant_ex = input("  Assistant: ").strip()
            if assistant_ex:
                prompt.add_few_shot_example(user_ex, assistant_ex)
                print("  [+] Example added")
    
    prompt.save()
    print(f"\n[+] Prompt configured and saved (ID: {prompt.get_id()})")
    
    return chat, prompt


def load_existing_chat():
    """Load an existing chat session"""
    print("\n" + "="*60)
    print("Load Existing Chat")
    print("="*60)
    
    # List available conversations
    db = get_db_manager()
    conversations = db.list_conversations(limit=20)
    
    if not conversations:
        print("\n[!] No existing conversations found.")
        print("    Create a new chat instead.")
        return None, None
    
    print("\nAvailable conversations:")
    for conv in conversations:
        msg_count = len(db.get_messages(conv.id))
        print(f"  [{conv.id}] {conv.title} - {msg_count} messages (max: {conv.max_messages})")
    
    # Get conversation ID
    conv_id_input = input("\nEnter conversation ID to load: ").strip()
    try:
        conv_id = int(conv_id_input)
    except ValueError:
        print("[!] Invalid ID")
        return None, None
    
    # Load chat
    try:
        chat = ChatSession.load(conv_id)
        print(f"\n[+] Loaded chat: {chat.title}")
        
        # Load or create prompt
        print("\n" + "-"*60)
        print("Prompt Configuration")
        print("-"*60)
        
        use_existing = input("Use existing prompt? (y/n, default: y): ").strip().lower()
        
        if use_existing != 'n':
            # Try to get prompt from last message
            if chat.messages:
                last_prompt_id = None
                for msg in reversed(chat.messages):
                    if msg.get('prompt_id'):
                        last_prompt_id = msg['prompt_id']
                        break
                
                if last_prompt_id:
                    prompt_record = db.get_prompt(last_prompt_id)
                    if prompt_record:
                        prompt = Prompt()
                        prompt._prompt_id = prompt_record.id
                        prompt._prompt_hash = prompt_record.prompt_hash
                        prompt.set_system(prompt_record.system_message or "")
                        print(f"[+] Loaded prompt (ID: {last_prompt_id})")
                        print(f"    System: {prompt_record.system_message[:60]}...")
                        return chat, prompt
            
            print("[!] No prompt found in conversation history")
        
        # Create new prompt
        print("\nCreating new prompt...")
        system_msg = input("System message: ").strip()
        if not system_msg:
            system_msg = "You are a helpful AI assistant."
        
        prompt = Prompt()
        prompt.set_system(system_msg)
        prompt.save()
        print(f"[+] New prompt created (ID: {prompt.get_id()})")
        
        return chat, prompt
        
    except Exception as e:
        print(f"[!] Error loading chat: {e}")
        return None, None


def interactive_chat(chat: ChatSession, prompt: Prompt):
    """Run interactive chat loop"""
    print("\n" + "="*60)
    print(f"Chat: {chat.title} (ID: {chat.conversation_id})")
    print("="*60)
    print("Commands:")
    print("  'exit' or 'quit' - Exit chat")
    print("  'stats' - Show usage statistics")
    print("  'history' - Show message history")
    print("  'clear' - Clear screen")
    print("="*60 + "\n")
    
    # Create client
    provider = input("Select provider (openai/gemini, default: gemini): ").strip().lower() or "gemini"
    client = create_client(provider)
    
    # Select model
    print(f"\nAvailable {provider} models:")
    models = client.get_available_models()
    for i, model in enumerate(models[:10], 1):  # Show first 10
        print(f"  {i}. {model}")
    
    model_choice = input(f"\nSelect model (default: {client.current_model}): ").strip()
    if model_choice:
        try:
            model_idx = int(model_choice) - 1
            if 0 <= model_idx < len(models):
                client.select_model(models[model_idx])
        except ValueError:
            client.select_model(model_choice)
    
    print(f"\n[+] Using model: {client.current_model}")
    print("\n" + "="*60)
    print("Start chatting! (type your message and press Enter)")
    print("="*60 + "\n")
    
    # Chat loop
    while True:
        try:
            # Get user input
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            # Handle commands
            if user_input.lower() in ['exit', 'quit']:
                print("\n[*] Saving conversation...")
                chat.save()
                print("[+] Goodbye!")
                break
            
            if user_input.lower() == 'stats':
                stats = prompt.get_usage_stats()
                print(f"\n--- Prompt Usage Statistics ---")
                print(f"Total calls: {stats['total_calls']}")
                print(f"Total input tokens: {stats['total_input_tokens']:,}")
                print(f"Total output tokens: {stats['total_output_tokens']:,}")
                print(f"Total cost: ${stats['total_cost']:.6f}")
                if stats['avg_quality_score']:
                    print(f"Avg quality score: {stats['avg_quality_score']:.2f}")
                print()
                continue
            
            if user_input.lower() == 'history':
                print(f"\n--- Message History ({len(chat.messages)} messages) ---")
                for i, msg in enumerate(chat.messages, 1):
                    role = msg['role'].upper()
                    compressed = " [COMPRESSED]" if msg.get('is_compressed', 0) == 1 else ""
                    content = msg['content'][:80] + "..." if len(msg['content']) > 80 else msg['content']
                    print(f"{i}. [{role}]{compressed}: {content}")
                print()
                continue
            
            if user_input.lower() == 'clear':
                import os
                os.system('cls' if os.name == 'nt' else 'clear')
                continue
            
            # Add user message
            chat.add_message('user', user_input)
            
            # Set user input in prompt and get response
            prompt.set_user_input(user_input)
            
            print("\nAssistant: ", end="", flush=True)
            response = chat.get_response(client, prompt)
            print(response)
            print()
            
        except KeyboardInterrupt:
            print("\n\n[*] Interrupted. Saving conversation...")
            chat.save()
            print("[+] Goodbye!")
            break
        except Exception as e:
            print(f"\n[!] Error: {e}")
            import traceback
            traceback.print_exc()
            print()


def main():
    """Main entry point"""
    print("\n" + "="*60)
    print("Interactive Chat Test Tool")
    print("="*60)
    
    # Choose mode
    print("\nSelect mode:")
    print("  1. Create new chat")
    print("  2. Load existing chat")
    
    choice = input("\nYour choice (1/2, default: 1): ").strip() or "1"
    
    if choice == "2":
        chat, prompt = load_existing_chat()
    else:
        chat, prompt = create_new_chat()
    
    if chat is None or prompt is None:
        print("\n[!] Failed to initialize chat. Exiting.")
        return
    
    # Start interactive chat
    interactive_chat(chat, prompt)


if __name__ == "__main__":
    main()
