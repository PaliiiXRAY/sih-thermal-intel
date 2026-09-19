"""
Authentication and User Pydantic models.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.common import RoleEnum


class LoginRequest(BaseModel):
    email: str = Field(..., json_schema_extra={"example": "analyst@firesense.org"})
    password: str = Field(..., json_schema_extra={"example": "password123"})


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 86400
    user: "UserResponse"


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: Optional[str] = None
    role: str
    is_active: bool = True
    created_at: datetime


TokenResponse.model_rebuild()
