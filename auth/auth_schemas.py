from pydantic import BaseModel
from typing import Optional

class MessageLimitCheckRequest(BaseModel):
    session_id: str

class MessageLimitCheckResponse(BaseModel):
    need_login: bool
    message: str = ""

class MessageLimitCheckResult(BaseModel):
    need_login: bool
    message: str = ""

class MessageLimitResponse(BaseModel):
    need_login: bool
    message: str = ""
    status_code: int = 200

class AuthResponse(BaseModel):
    token: str
    user: dict
    needsProfile: bool = False
    session_id: Optional[str] = None 