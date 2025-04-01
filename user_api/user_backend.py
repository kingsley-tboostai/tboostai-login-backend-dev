from sqlalchemy import select
import uvicorn
# import requests
import base64
import json
import sys
from pathlib import Path
from .user_database import get_session
from .user_models import UserAccount, GoogleAuthRequest, EmailVerificationRequest, CompleteProfileRequest, EmailCodeVerificationRequest,EmailUserCreateRequest, VerificationCode, SocialAccount
from fastapi import FastAPI, Depends, HTTPException, Request, Query
from fastapi.requests import Request as FastAPIRequest
from sqlmodel import Session, SQLModel
from .user_crud import (
    get_user_by_email,
    create_user,
    save_verification_code,
    verify_code
)
from .gmail_service import GmailService
from utils.crypto import encrypt_data, decrypt_data
from config.config import ALLOWED_ORIGINS
import random
import string
# from google.oauth2 import id_token
# from google.auth.transport import requests
from dotenv import load_dotenv
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
sys.path.append(str(Path(__file__).parent.parent))
from auth.auth import require_auth
from auth import auth
require_auth = auth.require_auth
# from config import config
# import pytz
import os
import logging
logger = logging.getLogger(__name__)
import traceback

app = FastAPI(title="User Service API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,
)

# Initialize Gmail service
gmail_service = GmailService(sender_email=os.getenv('GMAIL_SENDER_EMAIL', 'info@tboostai.com'))  # 从环境变量读取发件人邮箱

# 加载环境变量
load_dotenv()

# 获取环境变量
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')

@app.on_event("startup")
async def startup_event():
    pass


@app.post("/user/email/request-code")
async def request_verification_code(
    encrypted_data: str,
    db: Session = Depends(get_session)
):
    try:
        # 解密数据
        data = decrypt_data(encrypted_data)
        email = data["email"]
        
        code = ''.join(random.choices(string.digits, k=6))
        await save_verification_code(db, email, code)
        
        if not await gmail_service.send_verification_email(email, code):
            raise HTTPException(500, "Failed to send verification code")
        
        return {"message": "Verification code sent"}
        
    except Exception as e:
        logger.error(f"Error in request_verification_code: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/user/email/verify")
async def verify_email_code(
    encrypted_data: str = Query(...),
    db: Session = Depends(get_session)
):
    try:
        data = decrypt_data(encrypted_data)
        email = data["email"]
        code = data["code"]
        print(f"Received email: {email}, code: {code}") 
        verification = db.exec(
            select(VerificationCode)
            .where(
                VerificationCode.email == email,
                VerificationCode.code == code
            )
            .order_by(VerificationCode.created_at.desc())
        ).scalars().first()

        print(f"Verification: {verification}")
        
        if not verification:
            latest = db.exec(
                select(VerificationCode)
                .where(VerificationCode.email == email)
                .order_by(VerificationCode.created_at.desc())
            ).scalars().first()
            
            if not latest:
                raise HTTPException(400, "No verification code found")
            elif getattr(latest, "is_used", False):
                raise HTTPException(400, "Code has already been used")
            elif latest.expires_at is None:
                raise HTTPException(400, "Invalid expiration date")
            elif latest.expires_at <= datetime.utcnow():
                raise HTTPException(400, "Code has expired")
            else:
                raise HTTPException(400, "Invalid code")
        
        # 刷新 verification 对象，确保 expires_at 已经加载
        db.refresh(verification)
        expires_at = getattr(verification, "expires_at", None)
        print(f"Type of expires_at: {type(expires_at)}; value: {expires_at}")
        
        if expires_at is None:
            raise HTTPException(400, "Invalid expiration date")
        if expires_at <= datetime.utcnow():
            raise HTTPException(400, "Code has expired")
        if getattr(verification, "is_used", False):
            raise HTTPException(400, "Code has already been used")
        
        verification.is_used = True
        db.commit()
        
        # 创建或获取用户
        user = await get_user_by_email(db, email)
        if not user:
            user = await create_user(
                db=db,
                email=email,
                is_email_verified=True
            )
        else:
            user.is_email_verified = True
            db.commit()
            db.refresh(user)
        
        print(f"[EmailVerify] Created/Updated user: {user}")
        
        return {
            "status": "success", 
            "email": email,
            "user": user
        }
    except Exception as e:
        logger.error(f"Error in verify_email_code: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/user/email/create")
async def create_email_user(
    encrypted_data: str = Query(...),
    db: Session = Depends(get_session)
):
    try:
        print("=== Create Email User ===")
        data = decrypt_data(encrypted_data)
        email = data["email"]
        print(f"Decrypted email: {email}")
        
        user = await get_user_by_email(db, email)
        print(f"Existing user: {user}")
        needs_profile = False

        if not user:
            print("Creating new user...")
            # Create new user
            user = await create_user(
                db=db,
                email=email
            )
            needs_profile = True
            print(f"Created new user: {user}")
        elif not user.full_name:
            print("User exists but needs profile...")
            # Existing user but no profile
            needs_profile = True
        
        print(f"Returning response with needsProfile: {needs_profile}")
        return {
            "status": "success",
            "data": {
                "user": user,
                "needsProfile": needs_profile
            }
        }
    except Exception as e:
        print(f"Error in create_email_user: {str(e)}")
        logger.error(f"Error in create_email_user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

#change name to update profile
@app.post("/user/complete-profile") 
@require_auth
async def complete_profile(
    request: FastAPIRequest, 
    profile_data: CompleteProfileRequest, 
    user_id: str = None, 
    db: Session = Depends(get_session)
):
    print("=== Complete Profile Endpoint ===")
    print(f"Received request: {profile_data}")  # 添加日志
    print(f"User ID from token: {user_id}")
    print(f"Request headers: {request.headers}")  # 添加请求头日志
    try:
        # 使用 scalars().first() 获取用户对象
        user = db.exec(select(UserAccount).where(UserAccount.id == user_id)).scalars().first()
        print(f"[CompleteProfile] Query result for user_id {user_id}: {user}")
        if not user:
            print(f"[CompleteProfile] User not found with ID: {user_id}")
            raise HTTPException(404, "User not found")
        
        print(f"[CompleteProfile] Updating user with full_name: {profile_data.full_name}")
        user.full_name = profile_data.full_name
        db.commit()
        db.refresh(user)
        print(f"[CompleteProfile] Updated user: {user}")
        
        return {
            "status": "success",
            "data": {
                "user": user
            }
        }
    except Exception as e:
        print(f"Error in complete_profile: {str(e)}")
        print(f"Error type: {type(e)}")
        print(f"Error traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.get("/user/profile") #user backend +auth
@require_auth
async def get_user_profile(
    email: str,
    db: Session = Depends(get_session)
):
    user = await get_user_by_email(db, email)
    if not user:
        raise HTTPException(404, "User not found")
        
    return {
        "status": "success",
        "data": {
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "avatar_url": user.avatar_url
            }
        }
    }

# 添加请求模型
class EncryptedDataRequest(BaseModel):
    encrypted_data: str


@app.post("/user/google/create")
async def create_google_user(
    request: EncryptedDataRequest,
    db: Session = Depends(get_session)
):
    try:
        print(f"Received request with encrypted_data: {request.encrypted_data[:50]}...")  # 只打印前50个字符
        data = decrypt_data(request.encrypted_data)
        print(f"Decrypted data type: {type(data)}")  # 添加类型检查
        print(f"Decrypted data: {data}")  # 打印解密后的数据
        
        if not isinstance(data, dict):
            raise ValueError(f"Decrypted data is not a dictionary: {type(data)}")
            
        if "email" not in data:
            raise ValueError("Decrypted data does not contain email field")
            
        # 先查询用户是否存在
        existing_user = await get_user_by_email(db, data["email"])
        if existing_user:
            # 用户已存在，返回现有用户数据
            return {
                "status": "success",
                "data": {
                    "user": {
                        "id": existing_user.id,
                        "email": existing_user.email,
                        "full_name": existing_user.full_name,
                        "avatar_url": existing_user.avatar_url
                    }
                }
            }
        else:
            # 创建新用户，并同时创建 SocialAccount 记录
            user = await create_user(
                db=db,
                email=data["email"],
                full_name=data["name"],
                avatar_url=data["picture"],
                provider="google",
                provider_user_id=data["google_id"]
            )
            
            return {
                "status": "success",
                "data": {
                    "user": {
                        "id": user.id,
                        "email": user.email,
                        "full_name": user.full_name,
                        "avatar_url": user.avatar_url
                    }
                }
            }
    except Exception as e:
        logger.error(f"Error in create_google_user: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/user/google/update")
async def update_google_user(
    request: EncryptedDataRequest,
    db: Session = Depends(get_session)
):
    try:
        data = decrypt_data(request.encrypted_data)
        user = await get_user_by_email(db, data["email"])
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        if not user.provider_user_id:
            user.provider_user_id = data["google_id"]
            user.avatar_url = data["picture"] or user.avatar_url
            db.commit()
            db.refresh(user)
            
        return {
            "status": "success",
            "data": {
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "full_name": user.full_name,
                    "avatar_url": user.avatar_url
                }
            }
        }
    except Exception as e:
        logger.error(f"Error in update_google_user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/user/google/get")
async def get_google_user(
    encrypted_data: str,
    db: Session = Depends(get_session)
):
    try:
        print(f"Received encrypted_data: {encrypted_data[:50]}...")  # 只打印前50个字符
        data = decrypt_data(encrypted_data)
        print(f"Decrypted data type: {type(data)}")  # 添加类型检查
        print(f"Decrypted data: {data}")  # 打印解密后的数据
        
        if not isinstance(data, dict):
            raise ValueError(f"Decrypted data is not a dictionary: {type(data)}")
            
        if "email" not in data:
            raise ValueError("Decrypted data does not contain email field")
            
        user = await get_user_by_email(db, data["email"])
        if not user:
            return {"status": "not_found"}
            
        # 查询关联的 SocialAccount（provider 为 "google"）
        social_account = db.exec(
            select(SocialAccount).where(
                SocialAccount.user_id == user.id,
                SocialAccount.provider == "google"
            )
        ).first()
        provider_user_id = social_account.provider_user_id if social_account else None
        
        return {
            "status": "success",
            "data": {
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "full_name": user.full_name,
                    "avatar_url": user.avatar_url,
                    "provider_user_id": provider_user_id
                }
            }
        }
    except Exception as e:
        logger.error(f"Error in get_google_user: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "user_backend:app",
        host="0.0.0.0",
        port=8003,
        reload=True,
        log_level="info"
    )