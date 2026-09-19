"""
Hotspot Pydantic models.
Note: GeoJSON FeatureCollection outputs preserve raw dict structures to ensure exact compatibility.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class HotspotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    acquisition_time: datetime
    satellite: Optional[str] = None
    instrument: Optional[str] = None
    frp: Optional[float] = None
    bright_ti4: Optional[float] = None
    bright_ti5: Optional[float] = None
    detection_confidence: Optional[str] = None
    source: str = "firms"
    created_at: datetime


class LiveHotspotQuery(BaseModel):
    map_key: str
    bbox: Optional[str] = "6,68,36,98"
    source: Optional[str] = "viirs"
    days: Optional[int] = 1
    live_osm: Optional[bool] = False
