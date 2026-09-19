"""
Responders API Router for FireSense.
Exposes spatial proximity lookups for first responders.
"""
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from geoalchemy2 import Geography

from backend.app.core.errors import AppException
from backend.app.db.session import get_db
from backend.app.models.responder import Responder

router = APIRouter(prefix="/responders", tags=["responders"])


@router.get("/nearby", response_model=Dict[str, Any])
def get_nearby_responders(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Latitude of location"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Longitude of location"),
    radius_km: float = Query(50.0, ge=0.1, le=500.0, description="Search radius in km"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of responders to return"),
    db: Session = Depends(get_db),
):
    """
    Find nearest responders to the specified coordinates using PostGIS.
    Returns operational unit info without private contact details.
    """
    try:
        radius_meters = radius_km * 1000.0
        point = func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)
        geog = func.cast(point, Geography)
        dist_km = (
            func.ST_Distance(func.cast(Responder.geometry, Geography), geog) / 1000.0
        ).label("distance_km")

        rows = (
            db.query(
                Responder.id,
                Responder.name,
                Responder.type,
                Responder.status,
                Responder.organization,
                Responder.latitude,
                Responder.longitude,
                dist_km,
            )
            .filter(
                func.ST_DWithin(
                    func.cast(Responder.geometry, Geography),
                    geog,
                    radius_meters,
                )
            )
            .order_by("distance_km")
            .limit(limit)
            .all()
        )

        results = [
            {
                "id": r.id,
                "name": r.name,
                "type": r.type,
                "status": r.status,
                "organization": r.organization,
                "latitude": float(r.latitude),
                "longitude": float(r.longitude),
                "distance_km": round(float(r.distance_km), 2),
            }
            for r in rows
        ]

        return {
            "responders": results,
            "total": len(results),
            "search_radius_km": radius_km,
            "center": {"latitude": latitude, "longitude": longitude},
        }
    except Exception as e:
        raise AppException(500, "POSTGIS_ERROR", f"Failed to query nearby responders: {str(e)}")
