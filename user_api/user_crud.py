from sqlmodel import Session, select
from .user_models import UserAccount, VerificationCode, AuthHistory, SocialAccount
from datetime import datetime, timedelta
import uuid
from typing import Optional
from fastapi import HTTPException
import requests
import sys
from pathlib import Path
import logging
import traceback
sys.path.append(str(Path(__file__).parent.parent))
from config import config

logger = logging.getLogger(__name__)

DEFAULT_AVATAR_URL = ""

async def get_user_by_email(db: Session, email: str) -> Optional[UserAccount]:
    try:
        print(f"=== Getting user by email: {email} ===")
        result = db.exec(select(UserAccount).where(UserAccount.email == email)).first()
        print(f"Query result: {result}")
        if result:
            print(f"Found user with email: {email}")
            print(f"User details: {result}")
        else:
            print(f"No user found with email: {email}")
        return result
    except Exception as e:
        print(f"Error in get_user_by_email: {str(e)}")
        logger.error(f"Error in get_user_by_email: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error traceback: {traceback.format_exc()}")
        raise

async def get_user_by_id(db: Session, id: str) -> Optional[UserAccount]:
    return db.exec(select(UserAccount).where(UserAccount.id == id)).first()

async def create_user(
    db: Session,
    email: str,
    full_name: Optional[str] = None,
    avatar_url: Optional[str] = DEFAULT_AVATAR_URL,
    provider: Optional[str] = None,
    provider_user_id: Optional[str] = None,
    is_email_verified: bool = False  # 新增参数，默认 False
) -> UserAccount:
    user = UserAccount(
        id=str(uuid.uuid4()),
        email=email,
        full_name=full_name,
        avatar_url=avatar_url,
        is_email_verified=is_email_verified  # 传递参数
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # 如果提供了 provider 信息，则创建一条 SocialAccount 记录
    if provider and provider_user_id:
        social_account = SocialAccount(
            id=str(uuid.uuid4()),
            user_id=user.id,
            provider=provider,
            provider_user_id=provider_user_id,
            email=email,
            full_name=full_name,
            avatar_url=avatar_url,
        )
        db.add(social_account)
        db.commit()
    return user

async def save_verification_code(db: Session, email: str, code: str, purpose: str = "verify_email") -> VerificationCode:
    verification = VerificationCode(
        id=str(uuid.uuid4()),
        email=email,
        code=code,
        purpose=purpose, 
        created_at=datetime.utcnow(), 
        expires_at=datetime.utcnow() + timedelta(minutes=10),
        is_used=False,
        attempts=0
    )
    db.add(verification)
    db.commit()
    return verification

async def verify_code(db: Session, email: str, code: str) -> bool:
    print("DEBUG: select is", select)
    verification = db.exec(
        select(VerificationCode)
        .where(
            VerificationCode.email == email,
            VerificationCode.code == code,
            VerificationCode.is_used == False,
            VerificationCode.expires_at > datetime.utcnow()
        )
    ).first()
    
    if not verification:
        all_codes = db.exec(
            select(VerificationCode)
            .where(VerificationCode.email == email)
            .order_by(VerificationCode.created_at.desc())
        ).first()
        
        if all_codes:
            if all_codes.is_used:
                print(f"Code {code} for {email} has already been used")
            elif all_codes.expires_at <= datetime.utcnow():
                print(f"Code {code} for {email} has expired")
            else:
                print(f"Invalid code {code} for {email}")
        else:
            print(f"No verification code found for {email}")
        return False
        
    verification.is_used = True
    db.commit()
    return True, "Verification successful"

async def create_auth_history(
    db: Session,
    user_id: str,
    auth_method: str,
    auth_type: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    device_id: Optional[str] = None,
    location: Optional[str] = None,
    status: int = 1,
    failure_reason: Optional[str] = None,
    metadata: Optional[dict] = None
) -> AuthHistory:
    auth_history = AuthHistory(
        id=str(uuid.uuid4()),
        user_id=user_id,
        auth_method=auth_method,
        auth_type=auth_type,
        ip_address=ip_address,
        user_agent=user_agent,
        device_id=device_id,
        location=location,
        status=status,
        failure_reason=failure_reason,
        metadata=metadata
    )
    db.add(auth_history)
    db.commit()
    db.refresh(auth_history)
    return auth_history