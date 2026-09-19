from typing import Optional
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
import jwt

from backend.app.core.errors import unauthenticated_error
from backend.app.core.security import decode_access_token
from backend.app.db.session import get_db
from backend.app.models.user import User

security_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Dependency to get current authenticated User from JWT token."""
    token = None
    if credentials:
        token = credentials.credentials
    else:
        # Fallback to checking Authorization header directly
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]

    if not token:
        raise unauthenticated_error("Authentication token required", code="MISSING_TOKEN")

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub") or payload.get("user_id")
        email = payload.get("email")

        if not user_id and not email:
            raise unauthenticated_error("Invalid token payload", code="INVALID_TOKEN")
    except jwt.ExpiredSignatureError:
        raise unauthenticated_error("Authentication token has expired", code="TOKEN_EXPIRED")
    except jwt.PyJWTError:
        raise unauthenticated_error("Invalid authentication token", code="INVALID_TOKEN")

    # Fetch user from DB
    user = None
    if user_id:
        user = db.query(User).filter(User.id == user_id).first()
    if not user and email:
        user = db.query(User).filter(User.email == email).first()

    if not user:
        raise unauthenticated_error("User associated with token not found", code="USER_NOT_FOUND")

    if not user.is_active:
        raise unauthenticated_error("User account is inactive", code="USER_INACTIVE")

    return user
