# config.py
import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(override=True)

# 获取项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 服务地址与跨域配置
ALLOWED_ORIGINS = [
    "https://tboostai-login-frontend-dev.vercel.app",
    "http://localhost:3002",
    "http://127.0.0.1:3002"
]
AUTH_BACKEND_URL = os.getenv("AUTH_BACKEND_URL", "http://localhost:8004")
USER_BACKEND_URL = os.getenv("USER_BACKEND_URL", "http://localhost:8003")
CHAT_BACKEND_URL = os.getenv("CHAT_BACKEND_URL", "http://localhost:8001")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3002")

# Google OAuth 配置
GOOGLE_CLIENT_ID = "771384916731-rlvt5800trutb500j7dvphtp9pp5qa65.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "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"
GOOGLE_AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"
GOOGLE_AUTH_PROVIDER_CERT_URL = "https://www.googleapis.com/oauth2/v1/certs"
GOOGLE_REDIRECT_URIS = [f"{AUTH_BACKEND_URL}/auth/google/callback"]

# JWT 配置
JWT_SECRET = os.getenv("JWT_SECRET", "your_jwt_secret")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

# 密钥路径配置
PUBLIC_KEY_PEM = str(BASE_DIR / "keys" / "public.pem")
PRIVATE_KEY_PEM = str(BASE_DIR / "keys" / "private.pem")

# 数据库配置
# 线上数据库配置
# DB_USERNAME = "tboostai_intern"
# DB_PASSWORD = "K9#mPx$2vLq8"
# DB_HOST = "tboostai-core-db.mysql.database.azure.com:3306"
# DB_NAME = "tboostai_user_db"
# DB_CHAT_NAME = "tboostai_chat_db"

# 本地数据库配置
DB_USERNAME = "root"
DB_PASSWORD = "123456password"
DB_HOST = "localhost:3306"
DB_NAME = "com_tboostAI_core"
DB_CHAT_NAME = "com_tboostAI_core"

# 数据库连接 URL
SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
SQLALCHEMY_CHAT_DATABASE_URL = f"mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}/{DB_CHAT_NAME}"
