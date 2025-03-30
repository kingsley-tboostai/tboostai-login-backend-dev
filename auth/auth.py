import os
import json
import sys
import requests
from fastapi import FastAPI, HTTPException, Request, Query
from typing import Optional, Callable
from pathlib import Path
import logging
import time

# 添加两个路径
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))  # 添加当前目录到路径
sys.path.append(str(current_dir.parent))  # 添加父目录到路径

from config import config
from fastapi.responses import RedirectResponse
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from google_auth_oauthlib.flow import Flow
import uvicorn
import jwt
from datetime import datetime, timedelta
import httpx
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from functools import wraps
from urllib.parse import quote
from utils.crypto import encrypt_data, decrypt_data  # 修改导入
from auth_schemas import (  # 添加所需的 schemas 导入
    MessageLimitCheckResult, 
    MessageLimitResponse, 
    MessageLimitCheckRequest
)

# 加载环境变量
load_dotenv()

# 配置 logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,
)

def create_flow():
    """创建新的 OAuth flow"""
    client_config = {
        "web": {
            "client_id": config.GOOGLE_CLIENT_ID,
            "client_secret": config.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [f"{config.AUTH_BACKEND_URL}/auth/google/callback"],
        }
    }
    return Flow.from_client_config(
        client_config=client_config,
        scopes=[
            'https://www.googleapis.com/auth/userinfo.profile',
            'https://www.googleapis.com/auth/userinfo.email',
            'openid'
        ],
        redirect_uri=f"{config.AUTH_BACKEND_URL}/auth/google/callback"
    )

def create_jwt_token(data: dict) -> str:
    if isinstance(data.get('user_id'), dict):
        user_id = data['user_id'].get('user_id')
    else:
        user_id = data.get('user_id')

    payload = {
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(days=30)
    }
    
    return jwt.encode(
        payload,
        config.JWT_SECRET,
        algorithm=config.JWT_ALGORITHM
    )

@app.get("/auth/google/url")
async def get_google_auth_url(session_id: Optional[str] = None):
    try:
        flow = create_flow()
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='select_account',
            state=session_id  # 通过state参数传递session_id
        )
        print(f"Generated Google auth URL: {auth_url}")
        return {"url": auth_url}  # 确保返回格式正确
    except Exception as e:
        print(f"Error generating URL: {str(e)}")
        raise

@app.get("/auth/google/callback")
async def google_auth_callback(code: str, state: Optional[str] = None):
    """处理 Google OAuth 回调"""
    print(f"Received callback with code: {code[:10]}...") 
    try:
        # 使用授权码获取凭证
        flow = create_flow()
        try:
            print("Fetching token...")
            flow.fetch_token(code=code)
            print("Token fetched successfully!")
            
            credentials = flow.credentials
            print("Got credentials")
            
            id_info = id_token.verify_oauth2_token(
                credentials.id_token,
                google_requests.Request(),
                config.GOOGLE_CLIENT_ID,
                clock_skew_in_seconds=300
            )
            print(f"User info: {id_info.get('email')}")
            
        except Exception as e:
            print(f"Error during token exchange: {str(e)}")
            raise
        
        email = id_info.get("email")
        name = id_info.get("name")
        picture = id_info.get("picture")
        google_id = id_info.get("sub")
        
        # 加密用户数据
        encrypted_user_data = encrypt_data({
            "email": email,
            "name": name,
            "picture": picture,
            "google_id": google_id
        })
        
        # 调用用户服务
        print(f"Calling user service at {config.USER_BACKEND_URL}/user/google/get")
        get_response = requests.get(
            f"{config.USER_BACKEND_URL}/user/google/get",
            params={"encrypted_data": encrypted_user_data}
        )
        print(f"User service response: {get_response.status_code}")
        print(f"User service response body: {get_response.text}")
        
        if get_response.status_code == 200 and get_response.json()["status"] == "success":
            user_data = get_response.json()["data"]
            if not user_data["user"].get("provider_user_id"):
                print("Updating user with Google info...")
                update_response = requests.put(
                    f"{config.USER_BACKEND_URL}/user/google/update",
                    json={"encrypted_data": encrypted_user_data}
                )
                print(f"Update response: {update_response.status_code}")
                if update_response.status_code == 200:
                    user_data = update_response.json()["data"]
        else:
            print("Creating new user with Google info...")
            create_response = requests.post(
                f"{config.USER_BACKEND_URL}/user/google/create",
                json={"encrypted_data": encrypted_user_data}
            )
            print(f"Create response: {create_response.status_code}")
            if create_response.status_code != 200:
                raise HTTPException(status_code=create_response.status_code)
            user_data = create_response.json()["data"]
        
        # 生成 JWT token
        token = create_jwt_token({"user_id": user_data["user"]["id"]})
        
        # 处理 session - 使用 handle-auth 端点
        session_id = state
        if session_id:
            try:
                print(f"Handling session with ID: {session_id}")
                session_response = requests.post(
                    f"{config.CHAT_BACKEND_URL}/sessions/handle-auth",
                    params={
                        "encrypted_data": encrypt_data({
                            "user_id": user_data["user"]["id"],
                            "session_id": session_id
                        })
                    }
                )
                print(f"Session response: {session_response.status_code}")
                if session_response.status_code == 200:
                    session_data = session_response.json()
                    session_id = session_data["session_id"]
                else:
                    logger.error(f"Failed to handle session: {session_response.text}")
                    session_id = None
            except Exception as e:
                logger.error(f"Error handling session: {str(e)}")
                session_id = None
        
        # 重定向回前端
        print("DEBUG - FRONTEND_URL is:", config.FRONTEND_URL)
        # redirect_url = f"{config.FRONTEND_URL}?token={token}&user={json.dumps(user_data['user'])}&session_id={session_id if session_id else ''}&ts={int(time.time())}"
        redirect_url = f"https://car-quest.tboostai.com?token={token}&user={json.dumps(user_data['user'])}&session_id={session_id if session_id else ''}&ts={int(time.time())}"
        # redirect_url = f"http://localhost:3000?token={token}&user={json.dumps(user_data['user'])}&session_id={session_id if session_id else ''}&ts={int(time.time())}"

        print(f"Redirecting to: {redirect_url}")  
        return RedirectResponse(
            url=redirect_url,
            status_code=302  # 明确使用 302
        )
        
    except Exception as e:
        
        print("DEBUG - FRONTEND_URL is:", config.FRONTEND_URL)
        print(f"Callback error: {str(e)}")
        return RedirectResponse(
            f"{config.FRONTEND_URL}/login?error={str(e)}",
            status_code=302
        )
    
class EmailVerificationRequest(BaseModel):
    email: str
@app.post("/auth/email/request-code")
async def request_verification_code(request: EmailVerificationRequest):
    try:
        print(f"Received request for email: {request.email}")
        
        # 加密数据
        encrypted_data = encrypt_data({
            "email": request.email
        })
        
        response = requests.post(
            f"{config.USER_BACKEND_URL}/user/email/request-code",
            params={"encrypted_data": encrypted_data}  # 使用 params 因为数据量小
        )
        
        if response.status_code != 200:
            print(f"User service error: {response.text}")
            raise HTTPException(
                status_code=response.status_code,
                detail=response.text
            )
            
        return response.json()
        
    except Exception as e:
        print(f"Error requesting verification code: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.post("/auth/email/verify")
async def verify_email_code(
    email: str,
    code: str,
    session_id: Optional[str] = None
):
    try:
        # 1. 验证代码
        encrypted_verify_data = encrypt_data({
            "email": email,
            "code": code
        })
        
        verify_response = requests.post(
            f"{config.USER_BACKEND_URL}/user/email/verify",
            params={"encrypted_data": encrypted_verify_data}
        )
        if verify_response.status_code != 200:
            raise HTTPException(status_code=verify_response.status_code, detail=verify_response.text)
        
        # 2. 创建/获取用户
        encrypted_create_data = encrypt_data({
            "email": email
        })
        
        create_response = requests.post(
            f"{config.USER_BACKEND_URL}/user/email/create",
            params={"encrypted_data": encrypted_create_data}
        )
        if create_response.status_code != 200:
            raise HTTPException(status_code=create_response.status_code, detail=create_response.text)
            
        user_data = create_response.json()["data"]
        user_id = user_data["user"]["id"]
        
        # 3. 生成 JWT token
        token = create_jwt_token({"user_id": user_id})

        # 4. 处理聊天会话
        session_data = encrypt_data({
            "user_id": user_id,
            "session_id": session_id
        })
        
        session_response = requests.post(
            f"{config.CHAT_BACKEND_URL}/sessions/handle-auth",
            params={"encrypted_data": session_data}
        )
        if session_response.status_code != 200:
            raise HTTPException(status_code=session_response.status_code, detail=session_response.text)
            
        session_data = session_response.json()
        
        return {
            "token": token,
            "user": user_data["user"],
            "needsProfile": user_data["needsProfile"],
            "session_id": session_data["session_id"]
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in verify_email_code: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Token 验证函数
def verify_token(token: str) -> dict:
    try:
        print(f"Verifying token: {token[:20]}...")
        payload = jwt.decode(
            token, 
            config.JWT_SECRET,
            algorithms=[config.JWT_ALGORITHM]
        )
        print(f"Token payload: {payload}")
        return payload
    except jwt.ExpiredSignatureError as e:
        print(f"Token expired: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail="Login expired"
        )
    except jwt.InvalidTokenError:
        print(f"Invalid token: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail="Invalid login token"
        )
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
    

def require_auth(func: Callable):
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        # 直接从 request 对象获取 header
        authorization = request.headers.get("Authorization")
        print("=== Auth Check ===")
        print(f"Authorization header: {authorization}")
        
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail="Missing or invalid authorization header"
            )
        
        try:
            token = authorization.split(" ")[1]
            payload = verify_token(token)
            user_id = payload.get("user_id")
            if not user_id:
                raise HTTPException(401, "Invalid token: no user_id found")
            
            # 将 user_id 添加到 kwargs
            kwargs["user_id"] = user_id
            return await func(request, *args, **kwargs)
        except Exception as e:
            print(f"Auth error: {e}")
            raise HTTPException(401, str(e))
    
    return wrapper
    
if __name__ == "__main__":
    uvicorn.run(
        "auth:app",
        host="0.0.0.0",
        port=8004,
        reload=True,
        log_level="info"
    )