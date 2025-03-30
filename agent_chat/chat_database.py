# database.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))  # 添加父目录到系统路径
from sqlmodel import create_engine, SQLModel
from typing import Generator
from fastapi import Depends
from sqlmodel import Session
from urllib.parse import quote
from config.config import SQLALCHEMY_CHAT_DATABASE_URL

engine = create_engine(
    SQLALCHEMY_CHAT_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300
)

def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session