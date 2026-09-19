"""
Incident Pydantic models.
"""
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class IncidentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str = "DETECTED"
    classification: Optional[str] = None
    
    # ML classification confidence (0.0 to 1.0)
    classification_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    
    # Satellite/sensor detection confidence (e.g. LOW, NOMINAL, HIGH)
    detection_confidence: Optional[str] = None
    
    persistence_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    
    # Priority risk score (0.0 to 100.0), NOT a probability
    risk_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    
    severity: Optional[str] = None
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    
    explanation: Optional[Dict[str, Any]] = None
    assigned_responder_id: Optional[str] = None
    
    created_at: datetime
    updated_at: datetime


class IncidentStatusUpdate(BaseModel):
    status: str = "DETECTED"
    note: Optional[str] = None
