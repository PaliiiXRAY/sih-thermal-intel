"""
Alert Pydantic schemas.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    incident_id: str
    alert_type: str = "INCIDENT_PRIORITY_ALERT"
    target_role: Optional[str] = "authority"
    recommended_responder_id: Optional[str] = None
    is_simulated: bool = True
    status: str = "SENT"
    message: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    created_at: datetime
    sent_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
