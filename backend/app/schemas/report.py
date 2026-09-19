"""
Citizen Report Pydantic models matching app.py contracts.
"""
from typing import Any, Optional
from pydantic import BaseModel, Field


class CitizenReportCreate(BaseModel):
    location: str
    type: Optional[str] = "Smoke plume"
    notes: Optional[str] = ""
    gps: Optional[Any] = None
    time: Optional[str] = ""


class CitizenReportVerify(BaseModel):
    id: str = ""
