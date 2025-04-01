# user_database/database.py
from sqlmodel import create_engine, SQLModel, Session
from typing import Generator
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))
from config.config import SQLALCHEMY_DATABASE_URL
from .user_models import UserAccount, VerificationCode, AuthHistory, SocialAccount
import ssl

connect_args = {"ssl": {"cert_reqs": ssl.CERT_NONE}}

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args=connect_args
)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
