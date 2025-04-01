# user_models.py
from typing import Optional, List
from pydantic import BaseModel, EmailStr
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime, timedelta
import uuid
from enum import Enum as PyEnum
from sqlalchemy import Column, Text, Index, JSON

class AccountStatus(int, PyEnum):
    ACTIVE = 1
    INACTIVE = 0
    SUSPENDED = 2
    DELETED = 3

    def __int__(self):
        return self.value

class AuthMethod(str, PyEnum):
    EMAIL = "email"
    GOOGLE = "google"
    PHONE = "phone"

class AuthType(str, PyEnum):
    LOGIN = "login"
    REGISTER = "register"
    VERIFY = "verify"
    RESET_PASSWORD = "reset_password"

class DeviceType(str, PyEnum):
    MOBILE = "mobile"
    TABLET = "tablet"
    DESKTOP = "desktop"
    UNKNOWN = "unknown"

class ChatSessionStatus(str, PyEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"

class UserAccount(SQLModel, table=True):
    __tablename__ = "user_accounts"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    email: str = Field(unique=True, index=True)
    full_name: Optional[str] = Field(default=None, max_length=100)
    avatar_url: Optional[str] = Field(default=None, max_length=255)
    phone_number: Optional[str] = Field(default=None, max_length=20)
    status: int = Field(default=AccountStatus.ACTIVE.value)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login_at: Optional[datetime] = None
    last_login_ip: Optional[str] = Field(default=None, max_length=45)
    last_login_device: Optional[str] = Field(default=None, max_length=255)
    is_email_verified: bool = Field(default=False)
    is_phone_verified: bool = Field(default=False)
    two_factor_enabled: bool = Field(default=False)
    two_factor_method: Optional[str] = Field(default=None, max_length=20)
    deleted_at: Optional[datetime] = None

class SocialAccount(SQLModel, table=True):
    __tablename__ = "social_accounts"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: str = Field(foreign_key="user_accounts.id")
    provider: str = Field(max_length=20)
    provider_user_id: str = Field(max_length=191)
    email: Optional[str] = Field(default=None, max_length=191)
    full_name: Optional[str] = Field(default=None, max_length=100)
    avatar_url: Optional[str] = Field(default=None, max_length=255)
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_used_at: datetime = Field(default_factory=datetime.utcnow)
    is_primary: bool = Field(default=False)
    status: int = Field(default=AccountStatus.ACTIVE.value)
    deleted_at: Optional[datetime] = None

class UserDevice(SQLModel, table=True):
    __tablename__ = "user_devices"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: str = Field(foreign_key="user_accounts.id")
    device_id: str = Field(max_length=100)
    device_name: Optional[str] = Field(default=None, max_length=100)
    device_type: Optional[str] = Field(default=None, max_length=20)
    os_name: Optional[str] = Field(default=None, max_length=50)
    os_version: Optional[str] = Field(default=None, max_length=50)
    browser_name: Optional[str] = Field(default=None, max_length=50)
    browser_version: Optional[str] = Field(default=None, max_length=50)
    last_used_at: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: int = Field(default=AccountStatus.ACTIVE.value)
    deleted_at: Optional[datetime] = None

class AuthHistory(SQLModel, table=True):
    __tablename__ = "auth_history"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: str = Field(foreign_key="user_accounts.id")
    auth_method: str = Field(max_length=20)
    auth_type: str = Field(max_length=20)
    ip_address: Optional[str] = Field(default=None, max_length=45)
    user_agent: Optional[str] = Field(default=None, max_length=255)
    device_id: Optional[str] = Field(default=None, max_length=100)
    location: Optional[str] = Field(default=None, max_length=100)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: int = Field(default=1)
    failure_reason: Optional[str] = Field(default=None, max_length=255)
    metadata_json: Optional[dict] = Field(default=None, sa_column=Column("metadata", JSON))

class VerificationCode(SQLModel, table=True):
    __tablename__ = "verification_codes"
    
    id: str = Field(primary_key=True)
    email: str = Field(max_length=255)
    code: str = Field(max_length=255)
    purpose: str = Field(max_length=255)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    is_used: bool = Field(default=False)
    attempts: int = Field(default=0)

# Pydantic models for API requests/responses
class GoogleAuthRequest(BaseModel):
    idToken: str

class EmailVerificationRequest(BaseModel):
    email: EmailStr

class EmailCodeVerificationRequest(BaseModel):
    email: EmailStr
    code: str

class CompleteProfileRequest(BaseModel):
    email: str
    full_name: str
    phone_number: Optional[str] = None

class EmailUserCreateRequest(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None

class EncryptedDataRequest(BaseModel):
    encrypted_data: str
    