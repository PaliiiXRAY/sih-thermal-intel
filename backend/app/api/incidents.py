import datetime
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from backend.app.core.auth import get_current_user
from backend.app.core.errors import (
    conflict_error,
    forbidden_error,
    not_found_error,
    validation_error,
    AppException,
)
from backend.app.db.session import get_db
from backend.app.models.alert import Alert
from backend.app.models.incident import Incident
from backend.app.models.incident_log import IncidentLog
from backend.app.models.user import User
from backend.app.schemas.alert import AlertResponse
from backend.app.schemas.incident import IncidentResponse, IncidentStatusUpdate
from backend.app.services.geospatial.context import get_incident_context
from backend.app.services.ml.classifier import classify
from backend.app.services.risk.engine import calculate_risk

router = APIRouter(prefix="/incidents", tags=["incidents"])

ALLOWED_CLASSIFY_ROLES = {"analyst", "authority", "admin"}
ALLOWED_CONTEXT_ROLES = {"analyst", "authority", "responder", "admin"}
ALLOWED_RISK_ROLES = {"analyst", "authority", "responder", "admin"}
ALLOWED_ALERT_ROLES = {"authority", "admin"}
ALLOWED_STATUS_UPDATE_ROLES = {"authority", "responder", "admin"}

VALID_CANONICAL_STATUSES = {
    "DETECTED", "CLASSIFIED", "ASSESSED", "ALERTED", "ACKNOWLEDGED",
    "EN_ROUTE", "ARRIVED", "CONTAINED", "RESOLVED"
}

VALID_STATUS_TRANSITIONS = {
    "DETECTED": {"CLASSIFIED"},
    "CLASSIFIED": {"ASSESSED"},
    "ASSESSED": {"ALERTED"},
    "ALERTED": {"ACKNOWLEDGED"},
    "ACKNOWLEDGED": {"EN_ROUTE", "RESOLVED"},
    "EN_ROUTE": {"ARRIVED"},
    "ARRIVED": {"CONTAINED"},
    "CONTAINED": {"RESOLVED"},
    "RESOLVED": set(),
}





@router.get("", response_model=Dict[str, Any])
@router.get("/", response_model=Dict[str, Any])
def get_incidents(
    status: Optional[str] = Query(None, description="Filter by incident status"),
    classification: Optional[str] = Query(None, description="Filter by ML/Rule classification"),
    severity: Optional[str] = Query(None, description="Filter by severity level (CRITICAL, HIGH, MEDIUM, LOW)"),
    min_risk_score: Optional[float] = Query(None, ge=0.0, le=100.0, description="Minimum priority risk score (0-100)"),
    limit: int = Query(50, ge=1, le=500, description="Max incidents to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
):
    """
    List incidents strictly from PostgreSQL database with optional filtering.
    Returns valid empty list when database is empty (no legacy fallback).
    """
    try:
        query = db.query(Incident)
        if status:
            query = query.filter(Incident.status == status.upper())
        if classification:
            query = query.filter(Incident.classification == classification.upper())
        if severity:
            query = query.filter(Incident.severity == severity.upper())
        if min_risk_score is not None:
            query = query.filter(Incident.risk_score >= min_risk_score)

        db_count = query.count()
        db_incidents = query.order_by(Incident.created_at.desc()).offset(offset).limit(limit).all()
        items = [IncidentResponse.model_validate(inc).model_dump() for inc in db_incidents]

        return {
            "incidents": items,
            "total": db_count,
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        raise AppException(500, "DATABASE_ERROR", f"Failed to query incidents: {str(e)}")


@router.get("/{incident_id}/risk")
def get_incident_risk_endpoint(
    incident_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get transparent risk/priority score evaluation for an incident.
    Requires role: analyst, authority, responder, or admin.
    Pure read-only operation with zero side effects on incident state.
    """
    # 1. Authorization Check
    user_role = (current_user.role or "").lower()
    if user_role not in ALLOWED_RISK_ROLES:
        raise forbidden_error(
            f"Role '{current_user.role}' is not authorized to access incident risk evaluation",
            code="FORBIDDEN",
        )

    # 2. Fetch Incident from PostgreSQL
    inc_id = incident_id.strip()
    inc = db.query(Incident).filter(Incident.id == inc_id).first()
    if not inc:
        raise not_found_error(f"Incident '{inc_id}' not found", code="NOT_FOUND")

    # 3. Fetch Spatial Context (safely handling missing/invalid location)
    try:
        context = get_incident_context(db, inc)
    except Exception:
        context = None

    # 4. Calculate Risk
    return calculate_risk(inc, context)


@router.get("/{incident_id}/context")
def get_incident_context_endpoint(

    incident_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get PostGIS-enriched spatial context (nearest assets and responders) for an incident.
    Requires role: analyst, authority, responder, or admin.
    Pure read-only operation with zero side effects.
    """
    # 1. Authorization Check
    user_role = (current_user.role or "").lower()
    if user_role not in ALLOWED_CONTEXT_ROLES:
        raise forbidden_error(
            f"Role '{current_user.role}' is not authorized to access incident context",
            code="FORBIDDEN",
        )

    # 2. Fetch Incident from PostgreSQL
    inc_id = incident_id.strip()
    inc = db.query(Incident).filter(Incident.id == inc_id).first()
    if not inc:
        raise not_found_error(f"Incident '{inc_id}' not found", code="NOT_FOUND")

    # 3. Execute PostGIS Context Service
    return get_incident_context(db, inc)


@router.get("/{incident_id}")
def get_incident(incident_id: str, db: Session = Depends(get_db)):

    """
    Get detailed incident by ID strictly from PostgreSQL database.
    """
    inc_id = incident_id.strip()
    try:
        inc = db.query(Incident).filter(Incident.id == inc_id).first()
        if inc:
            return IncidentResponse.model_validate(inc).model_dump()
    except Exception as e:
        raise AppException(500, "DATABASE_ERROR", f"Failed to fetch incident: {str(e)}")

    raise not_found_error(f"Incident '{inc_id}' not found", code="NOT_FOUND")


@router.post("/{incident_id}/classify")
def classify_incident_endpoint(
    incident_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Classify an incident using deterministic ML classifier service.
    Requires role: analyst, authority, or admin.
    Persists classification attributes, updates status DETECTED -> CLASSIFIED,
    and appends an append-only audit log entry in incident_logs.
    """
    # 1. Role Authorization Check
    user_role = (current_user.role or "").lower()
    if user_role not in ALLOWED_CLASSIFY_ROLES:
        raise forbidden_error(
            f"Role '{current_user.role}' is not authorized to perform incident classification",
            code="FORBIDDEN",
        )

    # 2. Fetch Incident from PostgreSQL
    inc_id = incident_id.strip()
    inc = db.query(Incident).filter(Incident.id == inc_id).first()
    if not inc:
        raise not_found_error(f"Incident '{inc_id}' not found", code="NOT_FOUND")

    # 3. Call Classifier Service
    try:
        result = classify(inc)
    except Exception as e:
        raise AppException(500, "CLASSIFIER_ERROR", f"Failed to execute classification service: {str(e)}")

    # 4. Determine status transition & log attributes
    old_status = inc.status or "DETECTED"
    # DETECTED -> CLASSIFIED; for existing CLASSIFIED or later states, preserve current status
    new_status = "CLASSIFIED" if old_status == "DETECTED" else old_status

    # 5. Persist Incident & append IncidentLog in atomic transaction
    try:
        inc.status = new_status
        inc.classification = result["class"]
        inc.classification_confidence = result["confidence"]

        # Update explanation object without overwriting unrelated fields
        explanation = dict(inc.explanation or {})
        explanation["evidence"] = result["evidence"]
        explanation["label_source"] = "DETERMINISTIC_RULES"
        explanation["rule_version"] = "v1"
        explanation["classification"] = {
            "class": result["class"],
            "confidence": result["confidence"],
        }
        inc.explanation = explanation
        flag_modified(inc, "explanation")

        # Append append-only audit log entry
        log_entry = IncidentLog(
            incident_id=inc.id,
            old_status=old_status,
            new_status=new_status,
            action="CLASSIFY",
            changed_by=current_user.id,
            note=f"Incident classified as {result['class']} with confidence {result['confidence']:.2f}",
            metadata_={
                "classification": result["class"],
                "classification_confidence": result["confidence"],
                "label_source": "DETERMINISTIC_RULES",
                "rule_version": "v1",
            },
        )
        db.add(log_entry)
        db.commit()
        db.refresh(inc)

        return IncidentResponse.model_validate(inc).model_dump()
    except Exception as e:
        db.rollback()
        raise AppException(500, "DATABASE_ERROR", f"Failed to persist incident classification: {str(e)}")


@router.post("/{incident_id}/alert")
def create_incident_alert_endpoint(
    incident_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate structured simulated authority alert and store in PostgreSQL database.
    Requires role: authority or admin.
    Atomically inserts Alert record and appends IncidentLog entry.
    """
    # 1. Authorization Check
    user_role = (current_user.role or "").lower()
    if user_role not in ALLOWED_ALERT_ROLES:
        raise forbidden_error(
            f"Role '{current_user.role}' is not authorized to generate alerts",
            code="FORBIDDEN",
        )

    # 2. Fetch Incident from PostgreSQL
    inc_id = incident_id.strip()
    inc = db.query(Incident).filter(Incident.id == inc_id).first()
    if not inc:
        raise not_found_error(f"Incident '{inc_id}' not found", code="NOT_FOUND")

    # 3. Fetch Spatial Context & Priority Risk
    try:
        context = get_incident_context(db, inc)
    except Exception:
        context = {"nearest_assets": [], "nearest_responders": []}

    risk_data = calculate_risk(inc, context)

    # 4. Recommended Responder Selection
    nearest_responders = context.get("nearest_responders", [])
    if nearest_responders:
        recommended_resp = nearest_responders[0]
        recommended_responder_id = recommended_resp.get("id")
    else:
        recommended_resp = None
        recommended_responder_id = None

    # 5. Build Alert Payload matching frozen contract
    alert_payload = {
        "incident_id": inc.id,
        "location": {
            "latitude": float(inc.latitude),
            "longitude": float(inc.longitude),
        },
        "classification": inc.classification or "UNKNOWN",
        "severity": inc.severity or "MEDIUM",
        "risk_score": risk_data.get("risk_score", 0.0),
        "is_simulated": True,
        "risk_reasons": risk_data.get("reasons", []),
        "nearest_assets": context.get("nearest_assets", []),
        "recommended_responder": recommended_resp,
    }

    # 6. Atomic Transaction: Insert Alert record and IncidentLog entry
    try:
        now = datetime.datetime.now(datetime.timezone.utc)
        alert_record = Alert(
            incident_id=inc.id,
            alert_type="INCIDENT_PRIORITY_ALERT",
            target_role="authority",
            recommended_responder_id=recommended_responder_id,
            is_simulated=True,
            status="SENT",
            message=f"Simulated authority priority alert for incident {inc.id}",
            payload=alert_payload,
            sent_at=now,
            metadata_={
                "dispatched_by_role": current_user.role,
                "dispatched_by_user_id": current_user.id,
            },
        )
        db.add(alert_record)

        log_entry = IncidentLog(
            incident_id=inc.id,
            old_status=inc.status,
            new_status=inc.status,
            action="ALERT_DISPATCH",
            changed_by=current_user.id,
            note="Simulated authority alert dispatched",
            metadata_={
                "alert_type": "INCIDENT_PRIORITY_ALERT",
                "target_role": "authority",
                "is_simulated": True,
                "recommended_responder_id": recommended_responder_id,
            },
        )
        db.add(log_entry)
        db.commit()
        db.refresh(alert_record)

        return AlertResponse.model_validate(alert_record).model_dump()
    except Exception as e:
        db.rollback()
        raise AppException(500, "DATABASE_ERROR", f"Failed to generate alert: {str(e)}")


@router.patch("/{incident_id}/status")
def patch_incident_status_endpoint(
    incident_id: str,
    payload: IncidentStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Perform authenticated controlled status lifecycle transition on an incident.
    Requires role: authority, responder, or admin.
    Enforces strict state machine rules and records append-only incident log.
    """
    # 1. Authorization Check
    user_role = (current_user.role or "").lower()
    if user_role not in ALLOWED_STATUS_UPDATE_ROLES:
        raise forbidden_error(
            f"Role '{current_user.role}' is not authorized to perform status transitions",
            code="FORBIDDEN",
        )

    # 2. Fetch Incident from PostgreSQL
    inc_id = incident_id.strip()
    inc = db.query(Incident).filter(Incident.id == inc_id).first()
    if not inc:
        raise not_found_error(f"Incident '{inc_id}' not found", code="NOT_FOUND")

    # 3. Status Vocabulary Validation
    raw_status = (payload.status or "").strip().upper()
    if raw_status not in VALID_CANONICAL_STATUSES:
        raise validation_error(
            f"Invalid status value '{payload.status}'. Must be one of canonical vocabulary: {sorted(list(VALID_CANONICAL_STATUSES))}",
            code="VALIDATION_ERROR",
        )

    old_status = (inc.status or "DETECTED").upper()

    # If status is identical, return current incident (no-op)
    if raw_status == old_status:
        return IncidentResponse.model_validate(inc).model_dump()

    # 4. State Machine Transition Validation
    allowed_next_states = VALID_STATUS_TRANSITIONS.get(old_status, set())
    if raw_status not in allowed_next_states:
        raise conflict_error(
            f"Cannot transition incident status from '{old_status}' to '{raw_status}'",
            code="INVALID_STATUS_TRANSITION",
        )

    # 5. Atomic Transaction: Update Incident status and insert IncidentLog
    try:
        inc.status = raw_status

        log_entry = IncidentLog(
            incident_id=inc.id,
            old_status=old_status,
            new_status=raw_status,
            action="STATUS_CHANGE",
            changed_by=current_user.id,
            note=payload.note or f"Status changed from {old_status} to {raw_status}",
            metadata_={
                "updated_by_role": current_user.role,
                "updated_by_user_id": current_user.id,
            },
        )
        db.add(log_entry)
        db.commit()
        db.refresh(inc)

        return IncidentResponse.model_validate(inc).model_dump()
    except Exception as e:
        db.rollback()
        raise AppException(500, "DATABASE_ERROR", f"Failed to update status: {str(e)}")


@router.post("/{incident_id}/dispatch")
def dispatch_incident(
    incident_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Dispatch responders for an incident (authority/admin only).
    Requires ASSESSED -> ALERTED transition; records an append-only IncidentLog.
    """
    # 1. Authorization Check
    user_role = (current_user.role or "").lower()
    if user_role not in ALLOWED_ALERT_ROLES:
        raise forbidden_error(
            f"Role '{current_user.role}' is not authorized to dispatch responders",
            code="FORBIDDEN",
        )

    # 2. Fetch Incident from PostgreSQL
    inc_id = incident_id.strip()
    inc = db.query(Incident).filter(Incident.id == inc_id).first()
    if not inc:
        raise not_found_error(f"Incident '{inc_id}' not found", code="NOT_FOUND")

    # 3. State Machine Transition Validation (ASSESSED -> ALERTED)
    old_status = (inc.status or "DETECTED").upper()
    allowed_next = VALID_STATUS_TRANSITIONS.get(old_status, set())
    if "ALERTED" not in allowed_next:
        raise conflict_error(
            f"Cannot dispatch incident from status '{old_status}' (allowed: {sorted(allowed_next)})",
            code="INVALID_STATUS_TRANSITION",
        )

    # 4. Atomic Transaction: Update Incident status and insert IncidentLog
    try:
        inc.status = "ALERTED"

        log_entry = IncidentLog(
            incident_id=inc.id,
            old_status=old_status,
            new_status="ALERTED",
            action="ALERT_DISPATCH",
            changed_by=current_user.id,
            note="Responder dispatch simulated",
            metadata_={
                "dispatched_by_role": current_user.role,
                "dispatched_by_user_id": current_user.id,
            },
        )
        db.add(log_entry)
        db.commit()
        db.refresh(inc)

        return {
            "success": True,
            "incident_id": inc_id,
            "old_status": old_status,
            "status": "ALERTED",
            "message": f"Simulated dispatch triggered for incident {inc_id}",
        }
    except AppException:
        raise
    except Exception as e:
        db.rollback()
        raise AppException(500, "DATABASE_ERROR", f"Failed to dispatch incident: {str(e)}")


@router.get("/{incident_id}/timeline", response_model=Dict[str, Any])
@router.get("/{incident_id}/logs", response_model=Dict[str, Any])
def get_incident_timeline_endpoint(
    incident_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get append-only audit timeline logs for an incident.
    Requires role: analyst, authority, responder, or admin.
    """
    user_role = (current_user.role or "").lower()
    if user_role not in ALLOWED_CONTEXT_ROLES:
        raise forbidden_error(
            f"Role '{current_user.role}' is not authorized to access incident audit logs",
            code="FORBIDDEN",
        )

    inc_id = incident_id.strip()
    inc = db.query(Incident).filter(Incident.id == inc_id).first()
    if not inc:
        raise not_found_error(f"Incident '{inc_id}' not found", code="NOT_FOUND")

    logs = (
        db.query(IncidentLog)
        .filter(IncidentLog.incident_id == inc_id)
        .order_by(IncidentLog.changed_at.asc())
        .all()
    )

    timeline = [
        {
            "id": log.id,
            "action": log.action,
            "old_status": log.old_status,
            "new_status": log.new_status,
            "changed_by": log.changed_by,
            "note": log.note,
            "changed_at": log.changed_at.isoformat() if log.changed_at else None,
            "metadata": log.metadata_,
        }
        for log in logs
    ]

    return {
        "incident_id": inc.id,
        "current_status": inc.status,
        "timeline": timeline,
        "total_events": len(timeline),
    }



