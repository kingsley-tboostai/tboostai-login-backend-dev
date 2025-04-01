# chat_database/database.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from sqlmodel import create_engine, SQLModel, Session
from typing import Generator
from config.config import SQLALCHEMY_CHAT_DATABASE_URL
import ssl

connect_args = {"ssl": {"cert_reqs": ssl.CERT_NONE}}

engine = create_engine(
    SQLALCHEMY_CHAT_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args=connect_args
)

def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
