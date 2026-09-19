"""
Common API Pydantic response models and canonical enums.
"""
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class RoleEnum(str, Enum):
    ANALYST = "analyst"
    AUTHORITY = "authority"
    RESPONDER = "responder"
    ADMIN = "admin"


class ClassificationEnum(str, Enum):
    INDUSTRIAL_FIRE = "INDUSTRIAL_FIRE"
    GAS_FLARE = "GAS_FLARE"
    WILDFIRE = "WILDFIRE"
    CROP_BURNING = "CROP_BURNING"
    MINING_OTHER = "MINING_OTHER"
    UNKNOWN = "UNKNOWN"


class IncidentStatusEnum(str, Enum):
    DETECTED = "DETECTED"
    CLASSIFIED = "CLASSIFIED"
    ASSESSED = "ASSESSED"
    ALERTED = "ALERTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    EN_ROUTE = "EN_ROUTE"
    ARRIVED = "ARRIVED"
    CONTAINED = "CONTAINED"
    RESOLVED = "RESOLVED"


class SeverityEnum(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ErrorDetail(BaseModel):
    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error description")
    details: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context or validation details")


class ErrorResponse(BaseModel):
    error: ErrorDetail


class SuccessResponse(BaseModel):
    success: bool = True
    message: Optional[str] = None
