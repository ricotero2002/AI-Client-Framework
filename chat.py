"""
Chat System - Interactive Conversation Management
Manages chat sessions with database persistence and context optimization
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from database import get_db_manager, Message as DBMessage
from prompt import Prompt


class ConversationOptimizer:
    """Handles conversation context optimization"""
    
    def __init__(self, max_messages: int = 10):
        """
        Initialize optimizer
        
        Args:
            max_messages: Maximum messages before compression
        """
        self.max_messages = max_messages
    
    def should_optimize(self, message_count: int) -> bool:
        """Check if conversation should be optimized"""
        return message_count > self.max_messages
    
    def summarize_messages(self, messages: List[Dict[str, str]], client, summary_prompt: Optional[Prompt] = None) -> str:
        """
        Create a summary of older messages
        
        Args:
            messages: List of messages to summarize
            client: AI client to use for summarization
            summary_prompt: Optional custom prompt for summarization
            
        Returns:
            Summary text
        """
        # Build conversation text
        conversation_text = "\n".join([
            f"{msg['role'].upper()}: {msg['content']}"
            for msg in messages
        ])
        
        # Create summarization prompt
        if summary_prompt is None:
            summary_prompt = Prompt()
            summary_prompt.set_system(
                "You are a conversation summarizer. Create a concise summary of the conversation "
                "that preserves key information, decisions, and context. Keep it brief but informative."
            )
        
        summary_prompt.set_user_input(
            f"Summarize this conversation:\n\n{conversation_text}"
        )
        
        # Get summary
        summary, _ = client.get_response(summary_prompt)
        return summary
    
    def compress_conversation(
        self,
        messages: List[Dict[str, str]],
        client,
        keep_recent: int = 5
    ) -> List[Dict[str, str]]:
        """
        Compress conversation by summarizing older messages
        
        Args:
            messages: All messages in conversation
            client: AI client for summarization
            keep_recent: Number of recent messages to keep intact
            
        Returns:
            Compressed message list with summary + recent messages
        """
        if len(messages) <= keep_recent:
            return messages
        
        # Split into old and recent
        old_messages = messages[:-keep_recent]
        recent_messages = messages[-keep_recent:]
        
        # Summarize old messages
        summary = self.summarize_messages(old_messages, client)
        
        # Create summary message
        summary_msg = {
            'role': 'system',
            'content': f"[Previous conversation summary]: {summary}"
        }
        
        # Return summary + recent messages
        return [summary_msg] + recent_messages


class ChatSession:
    """Manages an interactive chat session with database persistence"""
    
    def __init__(
        self,
        title: str = "New Conversation",
        conversation_id: Optional[int] = None,
        max_messages: int = 10
    ):
        """
        Initialize chat session
        
        Args:
            title: Conversation title
            conversation_id: Existing conversation ID to load
            max_messages: Maximum messages before optimization
        """
        self.db = get_db_manager()
        self.max_messages = max_messages
        self.optimizer = ConversationOptimizer(max_messages=max_messages)
        self.messages: List[Dict[str, Any]] = []
        self.conversation_id = conversation_id
        self.title = title
        
        # Load existing conversation or create new
        if conversation_id:
            self._load_conversation(conversation_id)
        else:
            # Create new conversation in database
            conversation = self.db.create_conversation(title, max_messages=max_messages)
            self.conversation_id = conversation.id
    
    def _load_conversation(self, conversation_id: int):
        """Load existing conversation from database"""
        conversation = self.db.get_conversation(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        self.title = conversation.title
        self.max_messages = conversation.max_messages
        
        print(f"\n{'='*60}")
        print(f"[*] Loading Conversation (ID: {conversation_id})")
        print(f"{'='*60}")
        print(f"Title: {self.title}")
        print(f"Max Messages: {self.max_messages}")
        
        # Load messages up to max_messages (or from last compression)
        db_messages = self.db.get_messages(conversation_id, limit=self.max_messages)
        self.messages = [
            {
                'role': msg.role,
                'content': msg.content,
                'model': msg.model,
                'prompt_id': msg.prompt_id,
                'is_compressed': msg.is_compressed,
                'timestamp': msg.timestamp
            }
            for msg in db_messages
        ]
        
        # Print loaded messages
        print(f"\nLoaded {len(self.messages)} messages:")
        for i, msg in enumerate(self.messages, 1):
            is_compressed_flag = " [COMPRESSED]" if msg.get('is_compressed', 0) == 1 else ""
            content_preview = msg['content'][:60] + "..." if len(msg['content']) > 60 else msg['content']
            print(f"  {i}. [{msg['role'].upper()}]{is_compressed_flag}: {content_preview}")
        print(f"{'='*60}\n")
    
    def add_message(
        self,
        role: str,
        content: str,
        model: Optional[str] = None,
        prompt_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Add a message to the conversation
        
        Args:
            role: Message role ('user', 'assistant', 'system')
            content: Message content
            model: Model used to generate this message (for assistant messages)
            prompt_id: Prompt ID used (for assistant messages)
            
        Returns:
            Message dictionary
        """
        # Save to database
        db_message = self.db.add_message(
            conversation_id=self.conversation_id,
            role=role,
            content=content,
            model=model,
            prompt_id=prompt_id
        )
        
        # Add to local cache
        message = {
            'role': role,
            'content': content,
            'model': model,
            'prompt_id': prompt_id,
            'timestamp': db_message.timestamp
        }
        self.messages.append(message)
        
        return message
    
    def get_response(self, client, prompt: Prompt) -> str:
        """
        Get AI response using a Prompt object
        
        This method:
        1. Ensures the prompt is saved to database
        2. Sets conversation context in the prompt
        3. Gets response from client
        4. Saves the response as a message with model and prompt tracking
        5. Saves usage statistics
        
        Args:
            client: AI client instance
            prompt: Prompt object with system message and user input
            
        Returns:
            Response text
            
        Example:
            >>> chat = ChatSession(title="My Chat")
            >>> prompt = Prompt().set_system("You are helpful")
            >>> prompt.set_user_input("Hello")
            >>> response = chat.get_response(client, prompt)
        """
        # Ensure prompt is saved to get ID
        if prompt.get_id() is None:
            prompt.save()
        
        # Set conversation context (use recent messages)
        if self.messages:
            # Get recent messages for context (up to max_messages)
            recent_messages = self.messages[-self.max_messages:] if len(self.messages) > self.max_messages else self.messages
            context_messages = [
                {'role': msg['role'], 'content': msg['content']}
                for msg in recent_messages
            ]
            prompt.set_conversation_context(context_messages, max_context_messages=self.max_messages)
        
        # Get response from client
        response_text, token_usage = client.get_response(prompt)
        
        # Add assistant message with model and prompt tracking
        self.add_message(
            role='assistant',
            content=response_text,
            model=client.current_model,
            prompt_id=prompt.get_id()
        )
        
        # Save usage statistics
        cost_estimate = client.estimate_cost(
            prompt_tokens=token_usage.prompt_tokens,
            completion_tokens=token_usage.completion_tokens,
            cached_tokens=token_usage.cached_tokens
        )
        
        prompt.save_usage(
            model=client.current_model,
            input_tokens=token_usage.prompt_tokens,
            output_tokens=token_usage.completion_tokens,
            response=response_text,
            cost=cost_estimate.total_cost
        )
        
        # Check if optimization is needed
        if self.optimizer.should_optimize(len(self.messages)):
            self.optimize_context(client)
        
        return response_text
    
    def optimize_context(self, client):
        """
        Optimize conversation context by compressing older messages
        
        This method:
        1. Summarizes old messages
        2. Deletes old messages from database
        3. Saves summary as a compressed message with timestamp of last compressed message
        4. Updates local message cache
        
        Args:
            client: AI client for summarization
        """
        print(f"\n{'='*60}")
        print(f"[*] Starting Conversation Optimization")
        print(f"{'='*60}")
        
        # Get non-compressed messages for compression
        non_compressed = [msg for msg in self.messages if msg.get('is_compressed', 0) == 0]
        
        print(f"Total messages: {len(self.messages)}")
        print(f"Non-compressed messages: {len(non_compressed)}")
        print(f"Max messages: {self.max_messages}")
        
        if len(non_compressed) <= self.max_messages:
            print("[!] No optimization needed (within limit)")
            print(f"{'='*60}\n")
            return  # Nothing to compress
        
        # Determine how many to keep
        keep_recent = max(3, self.max_messages // 2)  # Keep at least 3, or half of max
        
        print(f"\nCompression strategy:")
        print(f"  Keep recent: {keep_recent} messages")
        print(f"  To compress: {len(non_compressed) - keep_recent} messages")
        
        # Split into old and recent
        old_messages = non_compressed[:-keep_recent]
        recent_messages = non_compressed[-keep_recent:]
        
        # Print messages to be compressed
        print(f"\n[*] Messages to compress ({len(old_messages)}):")
        for i, msg in enumerate(old_messages, 1):
            content_preview = msg['content'][:50] + "..." if len(msg['content']) > 50 else msg['content']
            print(f"  {i}. [{msg['role'].upper()}]: {content_preview}")
        
        # Build conversation text for summarization
        conversation_text = "\n".join([
            f"{msg['role'].upper()}: {msg['content']}"
            for msg in old_messages
        ])
        
        # Create summarization prompt
        summary_prompt = Prompt()
        summary_prompt.set_system(
            "You are a conversation summarizer. Create a concise summary of the conversation "
            "that preserves key information, decisions, and context. Keep it brief but informative."
        )
        summary_prompt.set_user_input(f"Summarize this conversation:\n\n{conversation_text}")
        
        # Get summary
        print(f"\n[*] Generating summary...")
        summary, _ = client.get_response(summary_prompt)
        
        print(f"\n[*] Generated Summary:")
        print(f"{'─'*60}")
        print(summary)
        print(f"{'─'*60}")
        
        # Get timestamp of last message being compressed (to maintain order)
        last_compressed_timestamp = old_messages[-1]['timestamp']
        
        # Delete old messages from database
        if old_messages:
            print(f"\n[*] Deleting {len(old_messages)} old messages from database...")
            # Delete all messages before the first recent message
            delete_before_timestamp = recent_messages[0]['timestamp']
            deleted_count = self.db.delete_messages(self.conversation_id, delete_before_timestamp)
            print(f"[+] Deleted {deleted_count} messages")
        
        # Add summary as compressed message to database with timestamp of last compressed message
        summary_content = f"[Previous conversation summary]: {summary}"
        print(f"\n[*] Saving summary to database (timestamp: {last_compressed_timestamp})...")
        db_message = self.db.add_message(
            conversation_id=self.conversation_id,
            role='system',
            content=summary_content,
            is_compressed=1,
            timestamp=last_compressed_timestamp
        )
        print(f"[+] Summary saved")
        
        # Update local cache
        summary_msg = {
            'role': 'system',
            'content': summary_content,
            'model': None,
            'prompt_id': None,
            'is_compressed': 1,
            'timestamp': last_compressed_timestamp
        }
        
        # Rebuild messages list: compressed messages + summary + recent
        compressed_msgs = [msg for msg in self.messages if msg.get('is_compressed', 0) == 1]
        self.messages = compressed_msgs + [summary_msg] + recent_messages
        
        print(f"\n[SUCCESS] Optimization complete!")
        print(f"  Before: {len(non_compressed)} messages")
        print(f"  After: {len(self.messages)} messages ({len(compressed_msgs)} old summaries + 1 new summary + {len(recent_messages)} recent)")
        print(f"{'='*60}\n")
    
    def get_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get conversation history
        
        Args:
            limit: Maximum number of messages to return (most recent)
            
        Returns:
            List of message dictionaries with metadata
        """
        if limit:
            return self.messages[-limit:]
        return self.messages
    
    def save(self):
        """
        Save conversation to database
        
        Note: Messages are already saved incrementally, this is mainly
        for updating conversation metadata
        """
        if self.conversation_id:
            self.db.update_conversation(self.conversation_id, self.title)
    
    @classmethod
    def load(cls, conversation_id: int, max_messages: int = 10) -> 'ChatSession':
        """
        Load an existing conversation
        
        Args:
            conversation_id: ID of conversation to load
            max_messages: Maximum messages before optimization
            
        Returns:
            ChatSession instance
            
        Example:
            >>> chat = ChatSession.load(conversation_id=5)
        """
        return cls(conversation_id=conversation_id, max_messages=max_messages)
    
    def delete(self):
        """Delete this conversation from database"""
        if self.conversation_id:
            self.db.delete_conversation(self.conversation_id)
            self.conversation_id = None
            self.messages = []
    
    def __repr__(self) -> str:
        return f"ChatSession(id={self.conversation_id}, title='{self.title}', messages={len(self.messages)})"
