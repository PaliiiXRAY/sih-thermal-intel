import datetime
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.sql import func

from backend.app.db.base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    
    # Canonical roles: analyst, authority, responder, admin
    role = Column(String, nullable=False, default="analyst", index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
