from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.app.core.auth import get_current_user
from backend.app.core.config import JWT_ACCESS_TOKEN_EXPIRE_MINUTES
from backend.app.core.errors import unauthenticated_error
from backend.app.core.security import (
    create_access_token,
    seed_demo_users_if_needed,
    verify_password,
)
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.auth import LoginRequest, TokenResponse, UserResponse

router = APIRouter(tags=["Authentication"])


@router.post("/auth/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate user with email and password, returning a JWT token."""
    # Ensure demo users are present if database is empty
    seed_demo_users_if_needed(db)

    user = db.query(User).filter(User.email == request.email).first()
    if not user or not verify_password(request.password, user.hashed_password):
        raise unauthenticated_error("Invalid email or password", code="INVALID_CREDENTIALS")

    if not user.is_active:
        raise unauthenticated_error("User account is inactive", code="USER_INACTIVE")

    access_token = create_access_token(
        data={"sub": user.id, "email": user.email, "role": user.role}
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
    )


@router.get("/auth/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Return profile details for the currently authenticated user."""
    return UserResponse.model_validate(current_user)
