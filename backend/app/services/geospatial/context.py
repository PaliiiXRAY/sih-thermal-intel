"""
PostGIS Context Enrichment Service for FireSense.
Queries nearest spatial assets and responders using PostgreSQL/PostGIS functions.
"""
from typing import Any, Dict
from sqlalchemy import func
from sqlalchemy.orm import Session
from geoalchemy2 import Geography

from backend.app.core.errors import bad_request_error, AppException
from backend.app.models.asset import Asset
from backend.app.models.incident import Incident
from backend.app.models.responder import Responder


def get_incident_context(
    db: Session,
    incident: Incident,
    max_assets: int = 10,
    max_responders: int = 10,
    radius_km: float = 100.0,
) -> Dict[str, Any]:
    """
    Query PostGIS for nearest assets and responders relative to the given incident.

    Args:
        db: Active SQLAlchemy database session.
        incident: Incident ORM instance.
        max_assets: Maximum number of nearest assets to return.
        max_responders: Maximum number of nearest responders to return.
        radius_km: Search radius limit in kilometers.

    Returns:
        Structured context dictionary matching team response contract.
    """
    # 1. Location Validation
    if (
        incident.latitude is None
        or incident.longitude is None
        or incident.geometry is None
    ):
        raise bad_request_error(
            f"Incident '{incident.id}' has missing or invalid coordinates",
            code="INVALID_LOCATION",
        )

    lat = float(incident.latitude)
    lon = float(incident.longitude)
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        raise bad_request_error(
            f"Incident '{incident.id}' has out-of-bounds coordinates (lat: {lat}, lon: {lon})",
            code="INVALID_LOCATION",
        )

    radius_meters = radius_km * 1000.0
    # Construct PostGIS point directly from verified float coordinates (lon, lat)
    inc_point = func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326)
    inc_geog = func.cast(inc_point, Geography)

    # 2. PostGIS Nearest Assets Query
    try:
        asset_dist_km = (
            func.ST_Distance(func.cast(Asset.geometry, Geography), inc_geog) / 1000.0
        ).label("distance_km")

        asset_rows = (
            db.query(
                Asset.id,
                Asset.name,
                Asset.type,
                Asset.category,
                asset_dist_km,
            )
            .filter(
                func.ST_DWithin(
                    func.cast(Asset.geometry, Geography),
                    inc_geog,
                    radius_meters,
                )
            )
            .order_by("distance_km")
            .limit(max_assets)
            .all()
        )

        nearest_assets = [
            {
                "id": row.id,
                "name": row.name,
                "type": row.type,
                "category": row.category,
                "distance_km": round(float(row.distance_km), 2),
            }
            for row in asset_rows
        ]
    except Exception as e:
        raise AppException(
            500, "POSTGIS_ERROR", f"Failed to execute PostGIS asset proximity query: {str(e)}"
        )

    # 3. PostGIS Nearest Responders Query
    try:
        resp_dist_km = (
            func.ST_Distance(func.cast(Responder.geometry, Geography), inc_geog) / 1000.0
        ).label("distance_km")

        resp_rows = (
            db.query(
                Responder.id,
                Responder.name,
                Responder.type,
                Responder.status,
                Responder.organization,
                resp_dist_km,
            )
            .filter(
                func.ST_DWithin(
                    func.cast(Responder.geometry, Geography),
                    inc_geog,
                    radius_meters,
                )
            )
            .order_by("distance_km")
            .limit(max_responders)
            .all()
        )

        nearest_responders = [
            {
                "id": row.id,
                "name": row.name,
                "type": row.type,
                "status": row.status,
                "organization": row.organization,
                "distance_km": round(float(row.distance_km), 2),
            }
            for row in resp_rows
        ]
    except Exception as e:
        raise AppException(
            500, "POSTGIS_ERROR", f"Failed to execute PostGIS responder proximity query: {str(e)}"
        )

    # 4. Construct response dictionary
    return {
        "incident_id": incident.id,
        "location": {
            "latitude": lat,
            "longitude": lon,
        },
        "nearest_assets": nearest_assets,
        "nearest_responders": nearest_responders,
    }
