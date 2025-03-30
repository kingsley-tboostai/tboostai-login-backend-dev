# chat_backend.py
import sys
import os
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import json
from fastapi import FastAPI, Depends, HTTPException, Request, Query, APIRouter
from sqlmodel import Session, select
from typing import List, Optional, Union
import logging
import uuid
from datetime import datetime
from .chat_database import get_session as get_chat_session
from user_api.user_database import get_session as get_user_session
from .chat_models import UserChatSession, ChatMessage, ChatSessionStatus
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from .chat_schemas import (
    ChatSessionResponse,
    ChatHistoryResponse
)
from config.config import ALLOWED_ORIGINS
from fastapi.responses import JSONResponse
from auth.auth_schemas import MessageLimitResponse
from utils.crypto import decrypt_data  
from auth.auth import require_auth

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create a router that does not require authentication
public_router = APIRouter(prefix="/public")

# Creating a Master Application
app = FastAPI(title="Message Service API")

# 添加自定义 CORS 中间件
class CustomCORSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Access-Control-Allow-Origin"] = "http://localhost:3002"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response

# 添加请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url}")
    logger.info(f"Headers: {request.headers}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    return response

# 添加 CORS 中间件
logger.info(f"ALLOWED_ORIGINS: {ALLOWED_ORIGINS}")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# 添加自定义 CORS 中间件
app.add_middleware(CustomCORSMiddleware)

# 添加测试路由
@app.get("/test-cors")
async def test_cors():
    return {"message": "CORS test successful"}

@public_router.get("/message-count")
async def get_message_count(
    encrypted_data: str,
    db_session: Session = Depends(get_chat_session)
):
    try:
        decrypted_data = decrypt_data(encrypted_data)
        session_id = decrypted_data.get("session_id")
        
        if not session_id:
            raise HTTPException(status_code=400, detail="Invalid session data")
            
        chat_session = db_session.get(UserChatSession, session_id)
        if not chat_session:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        return {
            "session_id": session_id,
            "total_messages": chat_session.total_messages
        }
        
    except Exception as e:
        logger.error(f"Error getting message count: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Includes public router
app.include_router(public_router)

# Get the directory containing the current script
current_dir = os.path.dirname(os.path.abspath(__file__))

# Add IP rate limit
@app.post("/sessions/create")
def create_chat_session(
    db_session: Session = Depends(get_chat_session)
):
    """Create a new unassigned chat session"""
    logger.info("Received request to create chat session")
    try:
        chat_session = UserChatSession(
            id=str(uuid.uuid4()),
            status=ChatSessionStatus.ACTIVE,
            created_at=datetime.utcnow(),
            last_message_at=datetime.utcnow(),
            total_messages=0
        )
        db_session.add(chat_session)
        db_session.commit()
        db_session.refresh(chat_session)
        # did not use a schema to return, need to fix
        return JSONResponse(
                status_code=200,
                content={"chat_session_id": chat_session.id}
            )
    except Exception as e:
        logger.error(f"Error creating chat session: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create chat session: {str(e)}"
        )

@app.post("/sessions/{session_id}/link-user")
@require_auth
async def link_chat_session_with_user(
    request: Request,
    session_id: str,
    user_id: str,
    db_session: Session = Depends(get_chat_session)
):
    """Link an existing chat session with a user"""
    chat_session = db_session.get(UserChatSession, session_id)
    if not chat_session:
        raise HTTPException(status_code=404, detail="Chat session not found")
        
    chat_session.user_id = user_id
    db_session.commit()
    db_session.refresh(chat_session)
    return chat_session

@app.get("/sessions/user/{user_id}/latest")
@require_auth
async def get_latest_session(
    user_id: str,
    db_session: Session = Depends(get_chat_session)
):
    """Get the latest chat session for a user"""
    latest_session = db_session.exec(
        select(UserChatSession)
        .where(UserChatSession.user_id == user_id)
        .order_by(UserChatSession.created_at.desc())
    ).first()
    
    if not latest_session:
        raise HTTPException(status_code=404, detail="No chat session found for user")
    return latest_session

@app.get("/sessions/user/{user_id}/all")
@require_auth
async def get_user_chat_sessions(
    user_id: str,
    db_session: Session = Depends(get_chat_session)
):
    """Get all chat sessions for a user"""
    chat_sessions = db_session.exec(
        select(UserChatSession)
        .where(UserChatSession.user_id == user_id)
        .order_by(UserChatSession.last_message_at.desc())
    ).all()
    
    return chat_sessions

@app.get("/sessions/user")
@require_auth
def get_chat_session_id(
    user_id: str,
    db_session: Session = Depends(get_chat_session)
):
    # 查询用户的聊天会话
    print(f"Searching for chat session with user_id: {user_id}")
    
    chat_session = db_session.exec(
        select(UserChatSession).where(UserChatSession.user_id == user_id)
    ).first()
    
    if chat_session:
        print(f"Found chat session: {chat_session.id}")
    else:
        print("No chat session found")
    
    return {"chat_session_id": chat_session.id}



@app.get("/sessions/{session_id}", response_model=ChatSessionResponse)
@require_auth
def get_chat_session_info(
    session_id: str,
    db_session: Session = Depends(get_chat_session)
):
    chat_session = db_session.get(UserChatSession, session_id)
    if not chat_session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return chat_session

#add auth in the future
@app.get("/sessions/{session_id}/messages", response_model=ChatHistoryResponse)
def get_chat_history(
    session_id: str,
    limit: int = 50,
    before_message_id: Optional[str] = None,
    db_session: Session = Depends(get_chat_session)
):
    # First verify the chat session exists
    chat_session = db_session.get(UserChatSession, session_id)
    if not chat_session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    # Build the query
    query = select(ChatMessage).where(ChatMessage.chat_session_id == session_id)
    
    if before_message_id:
        before_msg = db_session.get(ChatMessage, before_message_id)
        if before_msg:
            query = query.where(ChatMessage.timestamp < before_msg.timestamp)
    
    # Get messages ordered by timestamp
    messages = db_session.exec(
        query.order_by(ChatMessage.timestamp.desc()).limit(limit)
    ).all()
    
    return ChatHistoryResponse(
        session_id=session_id,
        messages=list(reversed(messages))  # Return in chronological order
    )

@app.post("/sessions/handle-auth")
async def handle_auth_session(
    encrypted_data: str = Query(...),  # 使用 Query 参数装饰器
    db_session: Session = Depends(get_chat_session)
) -> dict:
    """Handle session management during authentication"""
    try:
        # 解密数据
        data = decrypt_data(encrypted_data)
        user_id = data["user_id"]
        session_id = data.get("session_id")
        
        logger.info(f"Handling auth session for user {user_id} with session {session_id}")

        if session_id and session_id != "undefined":
            # Check if current session has any messages
            current_session = db_session.get(UserChatSession, session_id)
            if current_session and current_session.total_messages == 0:
                # Get all user's sessions ordered by last message time
                user_sessions = db_session.exec(
                    select(UserChatSession)
                    .where(UserChatSession.user_id == user_id)
                    .where(UserChatSession.total_messages > 0)
                    .where(UserChatSession.id != session_id)  # Exclude current session
                    .order_by(UserChatSession.last_message_at.desc())
                ).all()
                
                # Find the first session with messages
                for session in user_sessions:
                    if session.total_messages > 0:
                        session_id = session.id
                        logger.info(f"Using session with history: {session_id}")
                        break

        if not session_id or session_id == "undefined":
            # Try to get user's latest session
            try:
                latest_session = db_session.exec(
                    select(UserChatSession)
                    .where(UserChatSession.user_id == user_id)
                    .order_by(UserChatSession.last_message_at.desc())
                ).first()

                if latest_session:
                    session_id = latest_session.id
                    logger.info(f"Found latest session: {session_id}")
                else:
                    # Create new session if none exists
                    logger.info("No existing session, creating new one...")
                    new_session = UserChatSession(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        status=ChatSessionStatus.ACTIVE
                    )
                    db_session.add(new_session)
                    db_session.commit()
                    session_id = new_session.id
                    logger.info(f"Created new session: {session_id}")
            except Exception as e:
                logger.error(f"Error getting/creating session: {e}")
                # Create new session if error occurs
                new_session = UserChatSession(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    status=ChatSessionStatus.ACTIVE
                )
                db_session.add(new_session)
                db_session.commit()
                session_id = new_session.id

        # Link user to session if needed
        if session_id:
            session = db_session.get(UserChatSession, session_id)
            if session and not session.user_id:
                session.user_id = user_id
                db_session.commit()

        return {
            "session_id": session_id
        }
    except Exception as e:
        logger.error(f"Error handling auth session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001,log_level="info")
