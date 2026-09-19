"""
Hotspots API Router for FireSense FastAPI Layer.
Exposes live FIRMS hotspots, scenario pipeline execution, and database-backed hotspot observations.
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from backend.pipeline import HotspotPipeline
from backend.app.core.errors import AppException
from backend.app.db.session import get_db
from backend.app.models.hotspot import Hotspot
from backend.app.schemas.hotspot import HotspotResponse

router = APIRouter(prefix="/hotspots", tags=["hotspots"])


@router.get("", response_model=Dict[str, Any])
@router.get("/", response_model=Dict[str, Any])
def get_hotspots(
    source: Optional[str] = Query(None, description="Filter by data source (firms, demo, cache)"),
    satellite: Optional[str] = Query(None, description="Filter by satellite sensor"),
    min_frp: Optional[float] = Query(None, ge=0.0, description="Minimum Fire Radiative Power (MW)"),
    days: Optional[int] = Query(None, ge=1, le=30, description="Observations from past N days"),
    limit: int = Query(100, ge=1, le=1000, description="Max items to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
):
    """
    Get persisted thermal hotspot observations from PostgreSQL database.
    """
    try:
        query = db.query(Hotspot)
        if source:
            query = query.filter(Hotspot.source == source.lower())
        if satellite:
            query = query.filter(Hotspot.satellite.ilike(f"%{satellite}%"))
        if min_frp is not None:
            query = query.filter(Hotspot.frp >= min_frp)
        if days is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            query = query.filter(Hotspot.acquisition_time >= cutoff)

        total = query.count()
        hotspots = query.order_by(Hotspot.acquisition_time.desc()).offset(offset).limit(limit).all()

        items = [HotspotResponse.model_validate(h).model_dump() for h in hotspots]
        return {"hotspots": items, "total": total, "limit": limit, "offset": offset}
    except Exception as e:
        raise AppException(500, "DATABASE_ERROR", f"Failed to retrieve hotspots: {str(e)}")


@router.get("/scenario")
def get_scenario(
    id: str = Query("jamnagar_refinery", description="Scenario ID"),
    live_osm: bool = Query(False, description="Whether to query live OpenStreetMap Overpass API")
):
    """
    Run thermal hotspot classification scenario pipeline.
    Reuses existing HotspotPipeline.run_scenario without logic alteration.
    """
    try:
        data = HotspotPipeline.run_scenario(id, use_live_osm=live_osm)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/live")
def get_live(
    map_key: Optional[str] = Query(None, description="NASA FIRMS MAP_KEY"),
    bbox: str = Query("6,68,36,98", description="Bounding box min_lat,min_lon,max_lat,max_lon"),
    source: str = Query("viirs", description="FIRMS sensor source (viirs, modis)"),
    days: int = Query(1, description="Day range (1-10)"),
    live_osm: bool = Query(False, description="Whether to query live OpenStreetMap Overpass API")
):
    """
    Fetch live NASA FIRMS detections and execute classification pipeline.
    Reuses existing HotspotPipeline.run_live.
    """
    effective_map_key = map_key or os.environ.get("FIRMS_MAP_KEY", "")
    if not effective_map_key:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Missing 'map_key' query parameter. Get a free NASA FIRMS MAP_KEY at https://firms.modap.eosdis.nasa.gov/api/map_key/",
                "example": "/api/live?map_key=YOUR_KEY&bbox=6,68,36,98&source=viirs&days=1"
            }
        )

    try:
        bbox_tuple = tuple(float(x) for x in bbox.split(","))
        feature_collection = HotspotPipeline.run_live(
            effective_map_key,
            bbox_tuple,
            source=source,
            day_range=days,
            use_live_osm=live_osm
        )
        return feature_collection
    except Exception as e:
        return JSONResponse(status_code=502, content={"error": str(e)})
