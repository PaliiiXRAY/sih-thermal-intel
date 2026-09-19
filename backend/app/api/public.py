"""
Public Advisory API Router for FireSense.
Exposes public-safe alerts and advisories without leaking internal PII,
responder private contacts, or internal audit trails.
"""
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.core.errors import AppException
from backend.app.db.session import get_db
from backend.app.models.alert import Alert
from backend.app.models.incident import Incident

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/alerts", response_model=Dict[str, Any])
def get_public_alerts(
    limit: int = Query(20, ge=1, le=100, description="Max alerts to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
):
    """
    Get public safety alerts and advisories.
    Does NOT leak internal user info, responder personal contacts, or internal audit logs.
    Explicitly tags all simulated alerts with is_simulated=True.
    """
    try:
        query = (
            db.query(Alert, Incident)
            .outerjoin(Incident, Alert.incident_id == Incident.id)
            .order_by(Alert.created_at.desc())
        )
        total = query.count()
        rows = query.offset(offset).limit(limit).all()

        alerts_list = []
        for alert, inc in rows:
            alerts_list.append({
                "id": alert.id,
                "incident_id": alert.incident_id,
                "alert_type": alert.alert_type,
                "status": alert.status,
                "is_simulated": bool(alert.is_simulated),
                "severity": inc.severity if inc else "MEDIUM",
                "classification": inc.classification if inc else "UNKNOWN",
                "location": {
                    "latitude": float(inc.latitude) if inc and inc.latitude is not None else None,
                    "longitude": float(inc.longitude) if inc and inc.longitude is not None else None,
                },
                "message": alert.message or "Thermal anomaly advisory",
                "sent_at": alert.sent_at.isoformat() if alert.sent_at else None,
                "created_at": alert.created_at.isoformat() if alert.created_at else None,
            })

        return {
            "alerts": alerts_list,
            "total": total,
            "limit": limit,
            "offset": offset,
            "notice": "All emergency alerts displayed are simulated for training and demonstration purposes."
        }
    except Exception as e:
        raise AppException(500, "DATABASE_ERROR", f"Failed to retrieve public alerts: {str(e)}")
