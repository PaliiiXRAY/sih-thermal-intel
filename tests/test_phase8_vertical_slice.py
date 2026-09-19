"""
Integration tests for Phase 8: Full Backend Vertical-Slice Integration.
"""
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from geoalchemy2 import WKTElement

from backend.app.main import app
from backend.app.core.config import DATABASE_URL
from backend.app.core.security import create_access_token
from backend.app.models.incident import Incident
from backend.app.models.incident_log import IncidentLog
from backend.app.models.alert import Alert
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
        user_id = f"usr_p8_{role}_{uuid.uuid4().hex[:6]}"
        email = f"p8_{role}_{uuid.uuid4().hex[:6]}@firesense.org"
        u = User(
            id=user_id,
            email=email,
            hashed_password="hash",
            full_name=f"Phase8 Test {role.capitalize()}",
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
def phase8_test_incident(db_session):
    """Fixture to create a test incident and responder in PostgreSQL."""
    inc_id = f"inc_p8_{uuid.uuid4().hex[:8]}"
    inc = Incident(
        id=inc_id,
        status="DETECTED",
        severity="UNKNOWN",
        classification=None,  # Unclassified initially
        persistence_score=80.0,
        latitude=21.1458,
        longitude=79.0882,
        geometry=WKTElement("POINT(79.0882 21.1458)", srid=4326),
        explanation={"frp": 65.0, "tags": ["industrial", "refinery"]},
    )
    db_session.add(inc)

    resp_id = f"resp_p8_{uuid.uuid4().hex[:6]}"
    resp = Responder(
        id=resp_id,
        name="Phase 8 Demo Responder",
        type="fire_brigade",
        status="AVAILABLE",
        organization="Phase 8 Fire Services",
        latitude=21.1500,
        longitude=79.0900,
        geometry=WKTElement("POINT(79.0900 21.1500)", srid=4326),
    )
    db_session.add(resp)
    db_session.commit()

    yield {"incident_id": inc_id, "responder_id": resp_id}

    # Cleanup
    db_session.query(Alert).filter(Alert.incident_id == inc_id).delete()
    db_session.query(IncidentLog).filter(IncidentLog.incident_id == inc_id).delete()
    db_session.query(Incident).filter(Incident.id == inc_id).delete()
    db_session.query(Responder).filter(Responder.id == resp_id).delete()
    db_session.commit()


def test_complete_incident_vertical_slice(db_session, test_users, phase8_test_incident):
    """
    E2E Test:
    1. Incident starts as DETECTED/UNKNOWN
    2. Context enrichment (GET /context)
    3. Risk Engine (GET /risk)
    4. Classification (POST /classify)
    5. Alert Generation (POST /alert)
    6. Status Lifecycle (PUT /status) -> DISPATCHED -> RESPONDING -> MITIGATED -> RESOLVED
    7. Audit Logging verified at each step
    """
    auth_headers = {"Authorization": f"Bearer {test_users['tokens']['authority']}"}
    incident_id = phase8_test_incident["incident_id"]
    responder_id = phase8_test_incident["responder_id"]

    # 1. Initial State Check
    resp = client.get(f"/api/incidents/{incident_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == incident_id
    assert data["status"] == "DETECTED"
    assert data["classification"] is None

    # 2. Context Enrichment
    resp = client.get(f"/api/incidents/{incident_id}/context", headers=auth_headers)
    assert resp.status_code == 200
    context_data = resp.json()
    assert "nearest_assets" in context_data
    assert "nearest_responders" in context_data
    
    # Check that our responder is found nearby
    responder_ids = [r["id"] for r in context_data["nearest_responders"]]
    assert responder_id in responder_ids

    # 3. Classification (ML or Deterministic fallback)
    resp = client.post(f"/api/incidents/{incident_id}/classify", headers=auth_headers)
    assert resp.status_code == 200
    class_data = resp.json()
    assert class_data["classification"] is not None
    assert "classification_confidence" in class_data
    classification_value = class_data["classification"]

    # Verify state via GET
    resp = client.get(f"/api/incidents/{incident_id}", headers=auth_headers)
    assert resp.json()["classification"] == classification_value

    # 4. Risk Engine
    resp = client.get(f"/api/incidents/{incident_id}/risk", headers=auth_headers)
    assert resp.status_code == 200
    risk_data = resp.json()
    assert "risk_score" in risk_data
    assert "severity" in risk_data
    assert "factors" in risk_data
    assert 0 <= risk_data["risk_score"] <= 100

    # 5. Alert Generation
    alert_payload = {
        "responder_id": responder_id,
        "priority": "HIGH",
        "notes": "E2E Integration Test Dispatch"
    }
    resp = client.post(f"/api/incidents/{incident_id}/alert", headers=auth_headers, json=alert_payload)
    assert resp.status_code == 200
    alert_data = resp.json()
    assert alert_data["status"] == "SENT"
    assert alert_data["recommended_responder_id"] == responder_id

    # 6. Status Lifecycle updates
    # The alert endpoint doesn't mutate incident status directly in the response payload.
    # We must patch the status to move the lifecycle forward.
    # Note: VALID_STATUS_TRANSITIONS: CLASSIFIED -> ASSESSED -> ALERTED -> ACKNOWLEDGED -> EN_ROUTE -> ARRIVED -> CONTAINED -> RESOLVED

    # We are in CLASSIFIED.
    resp = client.patch(f"/api/incidents/{incident_id}/status", headers=auth_headers, json={"status": "ASSESSED", "notes": "Assessed"})
    assert resp.status_code == 200
    resp = client.patch(f"/api/incidents/{incident_id}/status", headers=auth_headers, json={"status": "ALERTED", "notes": "Alerted"})
    assert resp.status_code == 200
    resp = client.patch(f"/api/incidents/{incident_id}/status", headers=auth_headers, json={"status": "ACKNOWLEDGED", "notes": "Ack"})
    assert resp.status_code == 200
    resp = client.patch(f"/api/incidents/{incident_id}/status", headers=auth_headers, json={"status": "EN_ROUTE", "notes": "En route"})
    assert resp.status_code == 200
    resp = client.patch(f"/api/incidents/{incident_id}/status", headers=auth_headers, json={"status": "ARRIVED", "notes": "Arrived"})
    assert resp.status_code == 200
    resp = client.patch(f"/api/incidents/{incident_id}/status", headers=auth_headers, json={"status": "CONTAINED", "notes": "Contained"})
    assert resp.status_code == 200
    resp = client.patch(f"/api/incidents/{incident_id}/status", headers=auth_headers, json={"status": "RESOLVED", "notes": "Resolved directly"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "RESOLVED"

    # Verify cross-stage consistency
    assert alert_data["incident_id"] == incident_id
    assert alert_data["payload"]["classification"] == classification_value
    assert alert_data["payload"]["risk_score"] == risk_data["risk_score"]
    assert alert_data["is_simulated"] is True
    # Explanation check for ML Provenance
    incident_final = client.get(f"/api/incidents/{incident_id}", headers=auth_headers).json()
    assert incident_final["explanation"]["label_source"] in ["XGBOOST", "DETERMINISTIC_RULES"]

    # 7. Audit Log Verification
    logs = db_session.query(IncidentLog).filter(IncidentLog.incident_id == incident_id).order_by(IncidentLog.changed_at.asc()).all()
    
    actions = [log.action for log in logs]
    assert "CLASSIFY" in actions
    assert "ALERT_DISPATCH" in actions
    assert "STATUS_CHANGE" in actions

    status_updates = [log for log in logs if log.action == "STATUS_CHANGE"]
    patched_statuses = [log.new_status for log in status_updates]
    assert "ASSESSED" in patched_statuses
    assert "ALERTED" in patched_statuses
    assert "ACKNOWLEDGED" in patched_statuses
    assert "EN_ROUTE" in patched_statuses
    assert "ARRIVED" in patched_statuses
    assert "CONTAINED" in patched_statuses
    assert "RESOLVED" in patched_statuses
    
    # Verify audit log fields
    for log in logs:
        assert log.incident_id == incident_id
        assert log.action is not None
        assert log.changed_by is not None
        assert log.changed_at is not None
