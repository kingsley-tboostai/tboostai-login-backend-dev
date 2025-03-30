# message_service/schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional, Union
from datetime import datetime, date
from .chat_models import ChatSessionStatus


class Config:
    """Pydantic config for datetime handling"""
    json_encoders = {
        datetime: lambda v: v.isoformat()
    }
    from_attributes = True

class ChatSessionCreate(BaseModel):
    user_id: str
    title: Optional[str] = None

    class Config(Config):
        pass

class ChatSessionResponse(BaseModel):
    id: str
    user_id: str
    status: ChatSessionStatus
    created_at: datetime
    last_message_at: datetime
    total_messages: int
    title: str

    class Config(Config):
        pass

class MessageCreate(BaseModel):
    content: str
    
    class Config(Config):
        pass

class MessageResponse(BaseModel):
    id: str
    chat_session_id: str
    role: str
    content: str
    timestamp: datetime
    tokens: Optional[int]
    options: Optional[List[str]] = None

    class Config(Config):
        pass

class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: List[MessageResponse]

    class Config(Config):
        pass

class SessionMessageCountResponse(BaseModel):
    session_id: str
    total_messages: int

class MessageLimitResponse(BaseModel):
    need_login: bool
    message: str
    status_code: int = 200