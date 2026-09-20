import json
import os
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


def bootstrap_demo_users_if_needed(db: Session) -> None:
    """Bootstrap demo users from FIRESENSE_BOOTSTRAP_USERS (JSON) when the users table is empty.

    Closed by default: with the env var unset, no users are created and login
    fails closed (INVALID_CREDENTIALS). Passwords are never shipped in code.
    Expected JSON shape:
        [{"email": "...", "password": "...", "role": "...", "full_name": "..."}]
    """
    raw = os.environ.get("FIRESENSE_BOOTSTRAP_USERS")
    if not raw:
        return
    try:
        spec = json.loads(raw)
    except ValueError:
        return
    try:
        if db.query(User).count() > 0:
            return
        for uinfo in spec:
            user = User(
                id=f"usr_{uuid.uuid4().hex[:12]}",
                email=uinfo["email"],
                hashed_password=hash_password(uinfo["password"]),
                full_name=uinfo.get("full_name", uinfo["role"].title() + " User"),
                role=uinfo["role"],
                is_active=True,
            )
            db.add(user)
        db.commit()
    except Exception:
        db.rollback()
