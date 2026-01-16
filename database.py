"""
Database Layer for Chat System
Manages conversations, messages, prompts, and usage tracking with SQLAlchemy
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.pool import StaticPool
import hashlib
import json
import os

Base = declarative_base()


class Conversation(Base):
    """Stores conversation metadata"""
    __tablename__ = 'conversations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    max_messages = Column(Integer, default=10, nullable=False)  # Max messages before compression
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'title': self.title,
            'max_messages': self.max_messages,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class Message(Base):
    """Stores individual messages in conversations"""
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey('conversations.id'), nullable=False)
    role = Column(String(50), nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    model = Column(String(100), nullable=True)  # Model used to generate this message
    prompt_id = Column(Integer, ForeignKey('prompts.id'), nullable=True)  # Prompt used
    is_compressed = Column(Integer, default=0, nullable=False)  # 1 if this is a compression summary
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    prompt = relationship("Prompt", back_populates="messages")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'role': self.role,
            'content': self.content,
            'model': self.model,
            'prompt_id': self.prompt_id,
            'is_compressed': self.is_compressed,
            'timestamp': self.timestamp.isoformat()
        }


class Prompt(Base):
    """Stores prompt templates"""
    __tablename__ = 'prompts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    prompt_hash = Column(String(64), unique=True, nullable=False, index=True)
    system_message = Column(Text, nullable=True)
    few_shot_examples = Column(Text, nullable=True)  # JSON serialized
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    messages = relationship("Message", back_populates="prompt")
    usage_records = relationship("PromptUsage", back_populates="prompt", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'prompt_hash': self.prompt_hash,
            'system_message': self.system_message,
            'few_shot_examples': self.few_shot_examples,
            'created_at': self.created_at.isoformat()
        }


class PromptUsage(Base):
    """Stores prompt execution metrics"""
    __tablename__ = 'prompt_usage'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    prompt_id = Column(Integer, ForeignKey('prompts.id'), nullable=False)
    model = Column(String(100), nullable=False)
    input_tokens = Column(Integer, nullable=False)
    output_tokens = Column(Integer, nullable=False)
    response = Column(Text, nullable=True)
    quality_score = Column(Float, nullable=True)
    cost = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    prompt = relationship("Prompt", back_populates="usage_records")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'prompt_id': self.prompt_id,
            'model': self.model,
            'input_tokens': self.input_tokens,
            'output_tokens': self.output_tokens,
            'response': self.response,
            'quality_score': self.quality_score,
            'cost': self.cost,
            'timestamp': self.timestamp.isoformat()
        }


class TestCase(Base):
    """Stores golden examples for prompt evaluation"""
    __tablename__ = 'test_cases'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    prompt_id = Column(Integer, ForeignKey('prompts.id'), nullable=False)
    input = Column(Text, nullable=False)
    expected_output = Column(Text, nullable=False)
    category = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    prompt = relationship("Prompt")
    evaluations = relationship("Evaluation", back_populates="test_case", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'prompt_id': self.prompt_id,
            'input': self.input,
            'expected_output': self.expected_output,
            'category': self.category,
            'notes': self.notes,
            'created_at': self.created_at.isoformat()
        }


class Evaluation(Base):
    """Stores evaluation results for prompt test cases"""
    __tablename__ = 'evaluations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    prompt_id = Column(Integer, ForeignKey('prompts.id'), nullable=False)
    test_case_id = Column(Integer, ForeignKey('test_cases.id'), nullable=False)
    response = Column(Text, nullable=False)
    llm_score = Column(Float, nullable=True)  # 0.0 to 1.0
    llm_reasoning = Column(Text, nullable=True)
    human_score = Column(Float, nullable=True)  # 0.0 to 1.0
    human_feedback = Column(Text, nullable=True)
    model = Column(String(100), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    prompt = relationship("Prompt")
    test_case = relationship("TestCase", back_populates="evaluations")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'prompt_id': self.prompt_id,
            'test_case_id': self.test_case_id,
            'response': self.response,
            'llm_score': self.llm_score,
            'llm_reasoning': self.llm_reasoning,
            'human_score': self.human_score,
            'human_feedback': self.human_feedback,
            'model': self.model,
            'timestamp': self.timestamp.isoformat()
        }


class PromptVersion(Base):
    """Stores prompt version history and improvements"""
    __tablename__ = 'prompt_versions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    parent_prompt_id = Column(Integer, ForeignKey('prompts.id'), nullable=False)
    version = Column(Integer, nullable=False)
    system_message = Column(Text, nullable=True)
    few_shot_examples = Column(Text, nullable=True)  # JSON serialized
    improvement_reason = Column(Text, nullable=True)
    avg_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    parent_prompt = relationship("Prompt")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'parent_prompt_id': self.parent_prompt_id,
            'version': self.version,
            'system_message': self.system_message,
            'few_shot_examples': self.few_shot_examples,
            'improvement_reason': self.improvement_reason,
            'avg_score': self.avg_score,
            'created_at': self.created_at.isoformat()
        }


class DatabaseManager:
    """Manages database connections and operations"""
    
    def __init__(self, db_path: str = "./data/chat.db"):
        """
        Initialize database manager
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        
        # Create data directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Create engine
        self.engine = create_engine(
            f'sqlite:///{db_path}',
            connect_args={'check_same_thread': False},
            poolclass=StaticPool
        )
        
        # Create session factory
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Create tables
        Base.metadata.create_all(self.engine)
    
    def get_session(self) -> Session:
        """Get a new database session"""
        return self.SessionLocal()
    
    # ==================== Conversation Operations ====================
    
    def create_conversation(self, title: str, max_messages: int = 10) -> Conversation:
        """Create a new conversation"""
        session = self.get_session()
        try:
            conversation = Conversation(title=title, max_messages=max_messages)
            session.add(conversation)
            session.commit()
            session.refresh(conversation)
            return conversation
        finally:
            session.close()
    
    def get_conversation(self, conversation_id: int) -> Optional[Conversation]:
        """Get conversation by ID"""
        session = self.get_session()
        try:
            return session.query(Conversation).filter(Conversation.id == conversation_id).first()
        finally:
            session.close()
    
    def update_conversation(self, conversation_id: int, title: str) -> Optional[Conversation]:
        """Update conversation title"""
        session = self.get_session()
        try:
            conversation = session.query(Conversation).filter(Conversation.id == conversation_id).first()
            if conversation:
                conversation.title = title
                conversation.updated_at = datetime.utcnow()
                session.commit()
                session.refresh(conversation)
            return conversation
        finally:
            session.close()
    
    def delete_conversation(self, conversation_id: int) -> bool:
        """Delete conversation and all its messages"""
        session = self.get_session()
        try:
            conversation = session.query(Conversation).filter(Conversation.id == conversation_id).first()
            if conversation:
                session.delete(conversation)
                session.commit()
                return True
            return False
        finally:
            session.close()
    
    def list_conversations(self, limit: int = 50) -> List[Conversation]:
        """List all conversations, most recent first"""
        session = self.get_session()
        try:
            return session.query(Conversation).order_by(Conversation.updated_at.desc()).limit(limit).all()
        finally:
            session.close()
    
    # ==================== Message Operations ====================
    
    def add_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        model: Optional[str] = None,
        prompt_id: Optional[int] = None,
        is_compressed: int = 0,
        timestamp: Optional[datetime] = None
    ) -> Message:
        """Add a message to a conversation"""
        session = self.get_session()
        try:
            message = Message(
                conversation_id=conversation_id,
                role=role,
                content=content,
                model=model,
                prompt_id=prompt_id,
                is_compressed=is_compressed,
                timestamp=timestamp if timestamp else datetime.utcnow()
            )
            session.add(message)
            
            # Update conversation's updated_at
            conversation = session.query(Conversation).filter(Conversation.id == conversation_id).first()
            if conversation:
                conversation.updated_at = datetime.utcnow()
            
            session.commit()
            session.refresh(message)
            return message
        finally:
            session.close()
    
    def get_messages(self, conversation_id: int, limit: Optional[int] = None) -> List[Message]:
        """
        Get messages for a conversation
        
        If compression exists: loads ALL messages from last compression onwards (old messages are deleted)
        If no compression: loads last N messages up to limit
        """
        session = self.get_session()
        try:
            # Get total count
            total_count = session.query(Message).filter(Message.conversation_id == conversation_id).count()
            
            # Find last compression point
            last_compressed = session.query(Message).filter(
                Message.conversation_id == conversation_id,
                Message.is_compressed == 1
            ).order_by(Message.timestamp.desc()).first()
            
            if last_compressed:
                # Load ALL messages from last compression onwards (no limit)
                # Old messages have been deleted, so we want everything that remains
                messages_after_compression = session.query(Message).filter(
                    Message.conversation_id == conversation_id,
                    Message.timestamp >= last_compressed.timestamp
                ).order_by(Message.timestamp).all()
                return messages_after_compression
            elif limit:
                # No compression, just get last N messages
                all_messages = session.query(Message).filter(
                    Message.conversation_id == conversation_id
                ).order_by(Message.timestamp).all()
                return all_messages[-limit:] if len(all_messages) > limit else all_messages
            else:
                # No limit, get all
                return session.query(Message).filter(
                    Message.conversation_id == conversation_id
                ).order_by(Message.timestamp).all()
        finally:
            session.close()
    
    def delete_messages(self, conversation_id: int, before_timestamp: datetime) -> int:
        """Delete messages before a certain timestamp"""
        session = self.get_session()
        try:
            count = session.query(Message).filter(
                Message.conversation_id == conversation_id,
                Message.timestamp < before_timestamp
            ).delete()
            session.commit()
            return count
        finally:
            session.close()
    
    # ==================== Prompt Operations ====================
    
    def save_prompt(self, system_message: Optional[str], few_shot_examples: Optional[List[Dict]]) -> Prompt:
        """
        Save a prompt template to database
        
        Args:
            system_message: System message content
            few_shot_examples: List of few-shot examples
            
        Returns:
            Prompt object with assigned ID
        """
        session = self.get_session()
        try:
            # Generate hash for deduplication
            prompt_hash = self._generate_prompt_hash(system_message, few_shot_examples)
            
            # Check if prompt already exists
            existing = session.query(Prompt).filter(Prompt.prompt_hash == prompt_hash).first()
            if existing:
                return existing
            
            # Create new prompt
            prompt = Prompt(
                prompt_hash=prompt_hash,
                system_message=system_message,
                few_shot_examples=json.dumps(few_shot_examples) if few_shot_examples else None
            )
            session.add(prompt)
            session.commit()
            session.refresh(prompt)
            return prompt
        finally:
            session.close()
    
    def get_prompt(self, prompt_id: int) -> Optional[Prompt]:
        """Get prompt by ID"""
        session = self.get_session()
        try:
            return session.query(Prompt).filter(Prompt.id == prompt_id).first()
        finally:
            session.close()
    
    def _generate_prompt_hash(self, system_message: Optional[str], few_shot_examples: Optional[List[Dict]]) -> str:
        """Generate unique hash for prompt template"""
        content = f"{system_message or ''}|{json.dumps(few_shot_examples) if few_shot_examples else ''}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    # ==================== Prompt Usage Operations ====================
    
    def save_usage(
        self,
        prompt_id: int,
        model: str,
        input_tokens: int,
        output_tokens: int,
        response: Optional[str] = None,
        quality_score: Optional[float] = None,
        cost: Optional[float] = None
    ) -> PromptUsage:
        """Save prompt usage metrics"""
        session = self.get_session()
        try:
            usage = PromptUsage(
                prompt_id=prompt_id,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                response=response,
                quality_score=quality_score,
                cost=cost
            )
            session.add(usage)
            session.commit()
            session.refresh(usage)
            return usage
        finally:
            session.close()
    
    def get_usage_stats(self, prompt_id: int) -> Dict[str, Any]:
        """Get usage statistics for a prompt"""
        session = self.get_session()
        try:
            usages = session.query(PromptUsage).filter(PromptUsage.prompt_id == prompt_id).all()
            
            if not usages:
                return {
                    'total_calls': 0,
                    'total_input_tokens': 0,
                    'total_output_tokens': 0,
                    'total_cost': 0.0,
                    'avg_quality_score': None
                }
            
            total_calls = len(usages)
            total_input_tokens = sum(u.input_tokens for u in usages)
            total_output_tokens = sum(u.output_tokens for u in usages)
            total_cost = sum(u.cost for u in usages if u.cost is not None)
            
            quality_scores = [u.quality_score for u in usages if u.quality_score is not None]
            avg_quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else None
            
            return {
                'total_calls': total_calls,
                'total_input_tokens': total_input_tokens,
                'total_output_tokens': total_output_tokens,
                'total_cost': total_cost,
                'avg_quality_score': avg_quality_score
            }
        finally:
            session.close()


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager(db_path: str = "./data/chat.db") -> DatabaseManager:
    """Get or create global database manager instance"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(db_path)
    return _db_manager
