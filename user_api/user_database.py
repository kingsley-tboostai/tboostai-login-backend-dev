# database.py
from sqlmodel import create_engine, SQLModel
from typing import Generator
from fastapi import Depends
from sqlmodel import Session
from urllib.parse import quote
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from config.config import SQLALCHEMY_DATABASE_URL
from .user_models import UserAccount, VerificationCode, AuthHistory, SocialAccount

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300
)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session