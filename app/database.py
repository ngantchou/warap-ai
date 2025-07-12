"""Database configuration and session management for Djobea AI"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import get_settings

settings = get_settings()

# Get database URL with fallback for Docker environment
database_url = settings.database_url

# Fix malformed database URL if needed
if database_url and ("2025@postgres" in database_url or "2025@localhost" in database_url):
    # Extract the actual password and construct proper URL
    if "POSTGRES_PASSWORD" in os.environ:
        password = os.environ["POSTGRES_PASSWORD"]
    else:
        password = "djobea_secure_password"
    
    # Check if we're in Docker environment
    if "postgres" in os.environ.get("PGHOST", ""):
        host = "postgres"  # Docker service name
    else:
        host = os.environ.get("PGHOST", "localhost")
    
    port = os.environ.get("PGPORT", "5432")
    user = os.environ.get("PGUSER", "djobea_user")
    database = os.environ.get("PGDATABASE", "djobea_ai")
    
    database_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"

# Database setup
engine = create_engine(
    database_url,
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