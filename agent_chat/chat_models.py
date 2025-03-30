# chat_models.py
from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from enum import Enum
import uuid
from sqlalchemy import JSON, Column

class ChatSessionStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"

class UserChatSession(SQLModel, table=True):
    __tablename__ = "user_chat_sessions"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: Optional[str] = Field(default=None, foreign_key="user_accounts.id")
    status: str = Field(default=ChatSessionStatus.ACTIVE.value, max_length=20)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_message_at: datetime = Field(default_factory=datetime.utcnow)
    total_messages: int = Field(default=0)
    title: Optional[str] = Field(default=None, max_length=200)
    
    # Relationships
    messages: List["ChatMessage"] = Relationship(back_populates="chat_session")

class ChatMessage(SQLModel, table=True):
    __tablename__ = "chat_messages"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    chat_session_id: str = Field(foreign_key="user_chat_sessions.id")
    user_id: Optional[str] = Field(default=None, foreign_key="user_accounts.id")
    role: str = Field(max_length=20)
    content: str
    agent_content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tokens: Optional[int] = None
    options: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    
    # Relationship
    chat_session: UserChatSession = Relationship(back_populates="messages")
