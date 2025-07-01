"""Database configuration and session management for Djobea AI"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from config import get_settings

settings = get_settings()

# Database setup
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()