from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.core.config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    echo=False,
    # Adjust pool parameters based on production needs later
    pool_pre_ping=True, 
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """FastAPI dependency to get database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
