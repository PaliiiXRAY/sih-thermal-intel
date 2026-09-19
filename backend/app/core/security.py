import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import bcrypt
import jwt
from sqlalchemy.orm import Session

from backend.app.core.config import (
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    JWT_ALGORITHM,
    JWT_SECRET_KEY,
)
from backend.app.db.session import SessionLocal
from backend.app.models.user import User


def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT access token."""
    return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])


DEMO_USERS = [
    {"email": "analyst@firesense.org", "full_name": "Analyst User", "role": "analyst"},
    {"email": "authority@firesense.org", "full_name": "Authority User", "role": "authority"},
    {"email": "responder@firesense.org", "full_name": "Responder User", "role": "responder"},
    {"email": "admin@firesense.org", "full_name": "Admin User", "role": "admin"},
]

def seed_demo_users_if_needed(db: Session) -> None:
    """Seed demo accounts into database if users table is empty."""
    try:
        existing_count = db.query(User).count()
        if existing_count == 0:
            default_password_hash = hash_password("password123")
            for uinfo in DEMO_USERS:
                user = User(
                    id=f"usr_{uuid.uuid4().hex[:12]}",
                    email=uinfo["email"],
                    hashed_password=default_password_hash,
                    full_name=uinfo["full_name"],
                    role=uinfo["role"],
                    is_active=True,
                )
                db.add(user)
            db.commit()
    except Exception as e:
        db.rollback()
