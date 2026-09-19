"""
Integration tests for Phase 6: Alert Generation + Incident Status Lifecycle + Audit Logging.
"""
import uuid
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from geoalchemy2 import WKTElement

from backend.app.main import app
from backend.app.core.config import DATABASE_URL
from backend.app.core.security import create_access_token
from backend.app.models.alert import Alert
from backend.app.models.asset import Asset
from backend.app.models.incident import Incident
from backend.app.models.incident_log import IncidentLog
from backend.app.models.responder import Responder
from backend.app.models.user import User

client = TestClient(app)
engine = create_engine(DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    """Provides clean database session for test setup and cleanup."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_users(db_session):
    """Seed test users for each role."""
    users = {}
    roles = ["analyst", "authority", "responder", "admin", "citizen"]
    for role in roles:
        user_id = f"usr_p6_{role}_{uuid.uuid4().hex[:6]}"
        email = f"p6_{role}_{uuid.uuid4().hex[:6]}@firesense.org"
        u = User(
            id=user_id,
            email=email,
            hashed_password="hash",
            full_name=f"Phase6 Test {role.capitalize()}",
            role=role,
            is_active=True,
        )
        db_session.add(u)
        users[role] = u
    db_session.commit()

    tokens = {
        role: create_access_token({"sub": users[role].id, "email": users[role].email, "role": role})
        for role in roles
    }

    yield {"users": users, "tokens": tokens}

    # Cleanup users
    for u in users.values():
        db_session.delete(u)
    db_session.commit()


@pytest.fixture
def phase6_test_incident(db_session):
    """Fixture to create a test incident and optional responder in PostgreSQL."""
    inc_id = f"inc_p6_{uuid.uuid4().hex[:8]}"
    inc = Incident(
        id=inc_id,
        status="DETECTED",
        severity="HIGH",
        classification="WILDFIRE",
        persistence_score=80.0,
        latitude=21.1458,
        longitude=79.0882,
        geometry=WKTElement("POINT(79.0882 21.1458)", srid=4326),
    )
    db_session.add(inc)

    resp_id = f"resp_p6_{uuid.uuid4().hex[:6]}"
    resp = Responder(
        id=resp_id,
        name="Nagpur Fast Response Unit 1",
        type="fire_brigade",
        status="AVAILABLE",
        organization="Nagpur Fire Services",
        latitude=21.1500,
        longitude=79.0900,
        geometry=WKTElement("POINT(79.0900 21.1500)", srid=4326),
    )
    db_session.add(resp)
    db_session.commit()

    yield {"incident_id": inc_id, "responder_id": resp_id}

    # Cleanup alerts, logs, incident, responder
    db_session.query(Alert).filter(Alert.incident_id == inc_id).delete()
    db_session.query(IncidentLog).filter(IncidentLog.incident_id == inc_id).delete()
    db_session.query(Incident).filter(Incident.id == inc_id).delete()
    db_session.query(Responder).filter(Responder.id == resp_id).delete()
    db_session.commit()


# =====================================================================
# ALERT ENDPOINT TESTS (1–14)
# =====================================================================

def test_unauthenticated_alert_receives_401(phase6_test_incident):
    """1. Unauthenticated alert request -> 401."""
    inc_id = phase6_test_incident["incident_id"]
    res = client.post(f"/api/incidents/{inc_id}/alert")
    assert res.status_code == 401


def test_analyst_alert_receives_403(test_users, phase6_test_incident):
    """2. Analyst role alert request -> 403."""
    token = test_users["tokens"]["analyst"]
    inc_id = phase6_test_incident["incident_id"]
    res = client.post(f"/api/incidents/{inc_id}/alert", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403


def test_responder_alert_receives_403(test_users, phase6_test_incident):
    """3. Responder role alert request -> 403."""
    token = test_users["tokens"]["responder"]
    inc_id = phase6_test_incident["incident_id"]
    res = client.post(f"/api/incidents/{inc_id}/alert", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403


def test_authority_alert_success(test_users, phase6_test_incident):
    """4. Authority role alert request -> success 200."""
    token = test_users["tokens"]["authority"]
    inc_id = phase6_test_incident["incident_id"]
    res = client.post(f"/api/incidents/{inc_id}/alert", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["incident_id"] == inc_id
    assert data["is_simulated"] is True


def test_admin_alert_success(test_users, phase6_test_incident):
    """5. Admin role alert request -> success 200."""
    token = test_users["tokens"]["admin"]
    inc_id = phase6_test_incident["incident_id"]
    res = client.post(f"/api/incidents/{inc_id}/alert", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["is_simulated"] is True


def test_nonexistent_incident_alert_receives_404(test_users):
    """6. Nonexistent incident ID -> 404 Not Found."""
    token = test_users["tokens"]["authority"]
    res = client.post("/api/incidents/NON_EXISTENT_INC_9999/alert", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 404


def test_alert_payload_required_fields_and_is_simulated(test_users, phase6_test_incident, db_session):
    """7, 8, 9, 11, 12, 13. Verify alert payload structure, is_simulated == true, responder selection, alert DB row, and log."""
    token = test_users["tokens"]["authority"]
    inc_id = phase6_test_incident["incident_id"]
    res = client.post(f"/api/incidents/{inc_id}/alert", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()

    assert data["is_simulated"] is True
    assert data["recommended_responder_id"] == phase6_test_incident["responder_id"]

    payload = data["payload"]
    assert payload["is_simulated"] is True
    assert "risk_score" in payload
    assert "risk_reasons" in payload
    assert payload["recommended_responder"]["id"] == phase6_test_incident["responder_id"]

    # Verify Alert row persisted in DB
    alert_db = db_session.query(Alert).filter(Alert.incident_id == inc_id).first()
    assert alert_db is not None
    assert alert_db.is_simulated is True
    assert alert_db.recommended_responder_id == phase6_test_incident["responder_id"]

    # Verify IncidentLog row persisted in DB
    log_db = db_session.query(IncidentLog).filter(
        IncidentLog.incident_id == inc_id,
        IncidentLog.action == "ALERT_DISPATCH"
    ).first()
    assert log_db is not None
    assert log_db.metadata_["is_simulated"] is True


def test_no_responder_leaves_recommended_responder_id_null(test_users, db_session):
    """10. Verify no nearby responder leaves recommended_responder_id as None (does not invent fake responder)."""
    inc_remote_id = f"inc_remote_{uuid.uuid4().hex[:8]}"
    inc_remote = Incident(
        id=inc_remote_id,
        status="DETECTED",
        latitude=0.0,
        longitude=0.0,
        geometry=WKTElement("POINT(0.0 0.0)", srid=4326),
    )
    db_session.add(inc_remote)
    db_session.commit()

    try:
        token = test_users["tokens"]["authority"]
        res = client.post(f"/api/incidents/{inc_remote_id}/alert", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        data = res.json()
        assert data["recommended_responder_id"] is None
        assert data["payload"]["recommended_responder"] is None
    finally:
        db_session.query(Alert).filter(Alert.incident_id == inc_remote_id).delete()
        db_session.query(IncidentLog).filter(IncidentLog.incident_id == inc_remote_id).delete()
        db_session.query(Incident).filter(Incident.id == inc_remote_id).delete()
        db_session.commit()


def test_api_v2_alert_compatibility_route(test_users, phase6_test_incident):
    """14. Verify /api/v2/incidents/{id}/alert delegates to same implementation."""
    token = test_users["tokens"]["authority"]
    inc_id = phase6_test_incident["incident_id"]
    res = client.post(f"/api/v2/incidents/{inc_id}/alert", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["incident_id"] == inc_id


# =====================================================================
# STATUS STATE MACHINE & PATCH TESTS (15–32)
# =====================================================================

def test_valid_status_transitions_sequence(test_users, phase6_test_incident, db_session):
    """15-22, 28, 29, 30. Verify full canonical lifecycle sequence: DETECTED -> CLASSIFIED -> ASSESSED -> ALERTED -> ACKNOWLEDGED -> EN_ROUTE -> ARRIVED -> CONTAINED -> RESOLVED."""
    token = test_users["tokens"]["authority"]
    user_id = test_users["users"]["authority"].id
    inc_id = phase6_test_incident["incident_id"]

    lifecycle = [
        "CLASSIFIED", "ASSESSED", "ALERTED", "ACKNOWLEDGED",
        "EN_ROUTE", "ARRIVED", "CONTAINED", "RESOLVED"
    ]

    for next_status in lifecycle:
        res = client.patch(
            f"/api/incidents/{inc_id}/status",
            json={"status": next_status, "note": f"Transition to {next_status}"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code == 200
        assert res.json()["status"] == next_status

    # Verify audit log in incident_logs for the last transition (CONTAINED -> RESOLVED)
    db_session.expire_all()
    logs = db_session.query(IncidentLog).filter(
        IncidentLog.incident_id == inc_id,
        IncidentLog.action == "STATUS_CHANGE"
    ).all()
    assert len(logs) == len(lifecycle)
    last_log = logs[-1]
    assert last_log.old_status == "CONTAINED"
    assert last_log.new_status == "RESOLVED"
    assert last_log.changed_by == user_id


def test_valid_shortcut_acknowledged_to_resolved(test_users, db_session):
    """23. Verify valid shortcut ACKNOWLEDGED -> RESOLVED."""
    inc_id = f"inc_ack_{uuid.uuid4().hex[:8]}"
    inc = Incident(
        id=inc_id,
        status="ACKNOWLEDGED",
        latitude=21.1458,
        longitude=79.0882,
        geometry=WKTElement("POINT(79.0882 21.1458)", srid=4326),
    )
    db_session.add(inc)
    db_session.commit()

    try:
        token = test_users["tokens"]["authority"]
        res = client.patch(
            f"/api/incidents/{inc_id}/status",
            json={"status": "RESOLVED"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code == 200
        assert res.json()["status"] == "RESOLVED"
    finally:
        db_session.query(IncidentLog).filter(IncidentLog.incident_id == inc_id).delete()
        db_session.query(Incident).filter(Incident.id == inc_id).delete()
        db_session.commit()


def test_invalid_backward_transition_receives_409(test_users, db_session):
    """24. Verify invalid backward transition (e.g. ARRIVED -> DETECTED) returns 409 Conflict."""
    inc_id = f"inc_arr_{uuid.uuid4().hex[:8]}"
    inc = Incident(
        id=inc_id,
        status="ARRIVED",
        latitude=21.1458,
        longitude=79.0882,
        geometry=WKTElement("POINT(79.0882 21.1458)", srid=4326),
    )
    db_session.add(inc)
    db_session.commit()

    try:
        token = test_users["tokens"]["authority"]
        res = client.patch(
            f"/api/incidents/{inc_id}/status",
            json={"status": "DETECTED"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code == 409
        err = res.json()
        assert "error" in err
        assert err["error"]["code"] == "INVALID_STATUS_TRANSITION"
    finally:
        db_session.query(Incident).filter(Incident.id == inc_id).delete()
        db_session.commit()


def test_invalid_skipped_transition_receives_409(test_users, phase6_test_incident):
    """25. Verify invalid skipped transition (e.g. DETECTED -> RESOLVED) returns 409 Conflict."""
    token = test_users["tokens"]["authority"]
    inc_id = phase6_test_incident["incident_id"]
    res = client.patch(
        f"/api/incidents/{inc_id}/status",
        json={"status": "RESOLVED"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 409
    err = res.json()
    assert "error" in err
    assert err["error"]["code"] == "INVALID_STATUS_TRANSITION"


def test_resolved_cannot_transition_further(test_users, db_session):
    """26. Verify RESOLVED state cannot transition further."""
    inc_id = f"inc_res_{uuid.uuid4().hex[:8]}"
    inc = Incident(
        id=inc_id,
        status="RESOLVED",
        latitude=21.1458,
        longitude=79.0882,
        geometry=WKTElement("POINT(79.0882 21.1458)", srid=4326),
    )
    db_session.add(inc)
    db_session.commit()

    try:
        token = test_users["tokens"]["authority"]
        res = client.patch(
            f"/api/incidents/{inc_id}/status",
            json={"status": "DETECTED"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code == 409
        assert res.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"
    finally:
        db_session.query(Incident).filter(Incident.id == inc_id).delete()
        db_session.commit()


def test_invalid_status_value_receives_422(test_users, phase6_test_incident):
    """27. Verify invalid status string returns 422 Unprocessable Entity."""
    token = test_users["tokens"]["authority"]
    inc_id = phase6_test_incident["incident_id"]
    res = client.patch(
        f"/api/incidents/{inc_id}/status",
        json={"status": "INVALID_UNKNOWN_STATUS_123"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 422
    err = res.json()
    assert "error" in err
    assert err["error"]["code"] == "VALIDATION_ERROR"


def test_status_patch_rollback_on_failure(test_users, phase6_test_incident):
    """31. Verify atomic rollback if database commit fails during status patch."""
    token = test_users["tokens"]["authority"]
    inc_id = phase6_test_incident["incident_id"]

    with patch("sqlalchemy.orm.Session.commit", side_effect=Exception("Database write error")):
        res = client.patch(
            f"/api/incidents/{inc_id}/status",
            json={"status": "CLASSIFIED"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code == 500
        assert res.json()["error"]["code"] == "DATABASE_ERROR"


def test_api_v2_status_patch_compatibility(test_users, phase6_test_incident):
    """32. Verify /api/v2/incidents/{id}/status PATCH route delegates to same implementation."""
    token = test_users["tokens"]["authority"]
    inc_id = phase6_test_incident["incident_id"]
    res = client.patch(
        f"/api/v2/incidents/{inc_id}/status",
        json={"status": "CLASSIFIED"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    assert res.json()["status"] == "CLASSIFIED"
