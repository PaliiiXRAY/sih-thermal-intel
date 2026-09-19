"""
ML Classification, Geospatial Context, and Risk engine Pydantic schemas.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ClassifyResponse(BaseModel):
    incident_id: str
    classification: str
    classification_confidence: float = Field(..., ge=0.0, le=1.0)
    explanation: Dict[str, Any]


class ContextResponse(BaseModel):
    incident_id: str
    nearest_assets: List[Dict[str, Any]] = Field(default_factory=list)
    nearest_responders: List[Dict[str, Any]] = Field(default_factory=list)


class RiskResponse(BaseModel):
    incident_id: str
    risk_score: float = Field(..., ge=0.0, le=100.0, description="Priority risk score (0-100), NOT a probability")
    severity: str
    severity_band: Optional[str] = None
    reasons: List[str] = Field(default_factory=list)
    factors: Dict[str, Any] = Field(default_factory=dict)

