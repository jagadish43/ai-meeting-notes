"""Shared SQLAlchemy engine and session factory for all authentication routes."""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from backend.core import get_settings


class Base(DeclarativeBase):
    pass


url = get_settings().database_url
# SQLite needs this option because FastAPI handles sync routes in worker threads.
engine = create_engine(url, connect_args={"check_same_thread": False} if url.startswith("sqlite") else {})
SessionLocal = sessionmaker(bind=engine)
