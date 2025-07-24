"""Database connection and session handling for notes_backend"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from dotenv import load_dotenv

# Load environment variables from .env if available
load_dotenv()

# Database URL should be set via environment variable DATABASE_URL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# PUBLIC_INTERFACE
def get_db():
    """Gets a SQLAlchemy DB session for FastAPI dependency injection."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
