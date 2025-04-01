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
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://car-quest.tboostai.com")

# Google OAuth 配置
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"
GOOGLE_AUTH_PROVIDER_CERT_URL = "https://www.googleapis.com/oauth2/v1/certs"
GOOGLE_REDIRECT_URIS = [f"{AUTH_BACKEND_URL}/auth/google/callback"]

# JWT 配置
JWT_SECRET = os.getenv("JWT_SECRET")
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
DB_USERNAME = os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_CHAT_NAME = os.getenv("DB_CHAT_NAME")

print(f"DB_USERNAME: {DB_USERNAME}")
print(f"DB_PASSWORD: {DB_PASSWORD}")
print(f"DB_HOST: {DB_HOST}")
print(f"DB_NAME: {DB_NAME}")
print(f"DB_CHAT_NAME: {DB_CHAT_NAME}")

# 修改数据库连接 URL，使用正确的 SSL 配置
# config.py（相关部分）
SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
SQLALCHEMY_CHAT_DATABASE_URL = f"mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}/{DB_CHAT_NAME}"