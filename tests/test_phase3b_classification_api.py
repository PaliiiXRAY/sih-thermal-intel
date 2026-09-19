"""
Integration tests for Phase 3B: Classification API Integration (POST /api/incidents/{id}/classify).
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
from backend.app.models.incident import Incident
from backend.app.models.incident_log import IncidentLog
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
    roles = ["analyst", "authority", "admin", "responder"]
    for role in roles:
        user_id = f"usr_test_{role}_{uuid.uuid4().hex[:6]}"
        email = f"test_{role}_{uuid.uuid4().hex[:6]}@firesense.org"
        u = User(
            id=user_id,
            email=email,
            hashed_password="hash",
            full_name=f"Test {role.capitalize()}",
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

    # Cleanup
    for u in users.values():
        db_session.delete(u)
    db_session.commit()


@pytest.fixture
def test_incident(db_session):
    """Fixture to create a clean test incident in PostgreSQL."""
    inc_id = f"inc_test_cls_{uuid.uuid4().hex[:8]}"
    point_geom = WKTElement("POINT(79.0882 21.1458)", srid=4326)
    inc = Incident(
        id=inc_id,
        status="DETECTED",
        classification=None,
        classification_confidence=None,
        detection_confidence="HIGH",
        persistence_score=75.0,
        risk_score=60.0,
        severity="MEDIUM",
        latitude=21.1458,
        longitude=79.0882,
        geometry=point_geom,
        explanation={"frp": 60.0, "tags": ["industrial", "factory"]},
    )
    db_session.add(inc)
    db_session.commit()

    yield inc

    # Cleanup incident and logs
    db_session.query(IncidentLog).filter(IncidentLog.incident_id == inc_id).delete()
    db_session.query(Incident).filter(Incident.id == inc_id).delete()
    db_session.commit()


def test_analyst_can_classify_incident(test_users, test_incident):
    """1. Verify analyst can trigger classification."""
    token = test_users["tokens"]["analyst"]
    res = client.post(
        f"/api/incidents/{test_incident.id}/classify",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["classification"] == "INDUSTRIAL_FIRE"
    assert data["status"] == "CLASSIFIED"


def test_authority_can_classify_incident(test_users, test_incident):
    """2. Verify authority can trigger classification."""
    token = test_users["tokens"]["authority"]
    res = client.post(
        f"/api/incidents/{test_incident.id}/classify",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    assert res.json()["classification"] == "INDUSTRIAL_FIRE"


def test_admin_can_classify_incident(test_users, test_incident):
    """3. Verify admin can trigger classification."""
    token = test_users["tokens"]["admin"]
    res = client.post(
        f"/api/incidents/{test_incident.id}/classify",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    assert res.json()["classification"] == "INDUSTRIAL_FIRE"


def test_responder_receives_403(test_users, test_incident):
    """4. Verify responder role receives 403 Forbidden."""
    token = test_users["tokens"]["responder"]
    res = client.post(
        f"/api/incidents/{test_incident.id}/classify",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 403
    err = res.json()
    assert "error" in err
    assert err["error"]["code"] == "FORBIDDEN"


def test_unauthenticated_request_receives_401(test_incident):
    """5. Verify unauthenticated request receives 401 Unauthorized."""
    res = client.post(f"/api/incidents/{test_incident.id}/classify")
    assert res.status_code == 401
    err = res.json()
    assert "error" in err
    assert err["error"]["code"] == "MISSING_TOKEN" or err["error"]["code"] == "UNAUTHENTICATED"


def test_nonexistent_incident_receives_404(test_users):
    """6. Verify nonexistent incident ID receives 404 Not Found."""
    token = test_users["tokens"]["analyst"]
    res = client.post(
        "/api/incidents/NON_EXISTENT_INCIDENT_999/classify",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 404
    err = res.json()
    assert "error" in err
    assert err["error"]["code"] == "NOT_FOUND"


def test_deterministic_classifier_invoked_and_persisted(test_users, test_incident, db_session):
    """7, 8, 9, 10, 11. Verify classifier invocation, DB persistence, explanation structure, status transition, and audit log."""
    token = test_users["tokens"]["analyst"]
    analyst_user = test_users["users"]["analyst"]

    res = client.post(
        f"/api/incidents/{test_incident.id}/classify",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    data = res.json()

    # Verify classification fields
    assert data["classification"] == "INDUSTRIAL_FIRE"
    assert 0.0 <= data["classification_confidence"] <= 1.0
    assert data["status"] == "CLASSIFIED"

    # Verify explanation contains structured classification evidence
    expl = data["explanation"]
    assert "evidence" in expl
    assert isinstance(expl["evidence"], list)
    assert expl["label_source"] == "DETERMINISTIC_RULES"
    assert expl["rule_version"] == "v1"
    assert expl["classification"]["class"] == "INDUSTRIAL_FIRE"

    # Query DB directly to verify persistence
    db_session.expire_all()
    db_inc = db_session.query(Incident).filter(Incident.id == test_incident.id).first()
    assert db_inc.classification == "INDUSTRIAL_FIRE"
    assert db_inc.status == "CLASSIFIED"

    # Verify audit log in incident_logs
    log = db_session.query(IncidentLog).filter(
        IncidentLog.incident_id == test_incident.id,
        IncidentLog.action == "CLASSIFY"
    ).first()
    assert log is not None
    assert log.old_status == "DETECTED"
    assert log.new_status == "CLASSIFIED"
    assert log.changed_by == analyst_user.id
    assert log.metadata_["classification"] == "INDUSTRIAL_FIRE"
    assert log.metadata_["label_source"] == "DETERMINISTIC_RULES"


def test_repeated_classification_does_not_move_lifecycle_backward(test_users, test_incident, db_session):
    """12. Verify re-classifying an already-classified or later-stage incident preserves status."""
    token = test_users["tokens"]["analyst"]

    # First classification: DETECTED -> CLASSIFIED
    r1 = client.post(
        f"/api/incidents/{test_incident.id}/classify",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert r1.status_code == 200
    assert r1.json()["status"] == "CLASSIFIED"

    # Set status manually to ASSESSED
    db_session.expire_all()
    db_inc = db_session.query(Incident).filter(Incident.id == test_incident.id).first()
    db_inc.status = "ASSESSED"
    db_session.commit()

    # Re-classify: status should remain ASSESSED
    r2 = client.post(
        f"/api/incidents/{test_incident.id}/classify",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "ASSESSED"

    # Verify a 2nd audit log entry was created
    db_session.expire_all()
    logs = db_session.query(IncidentLog).filter(
        IncidentLog.incident_id == test_incident.id,
        IncidentLog.action == "CLASSIFY"
    ).all()
    assert len(logs) == 2
    assert logs[1].old_status == "ASSESSED"
    assert logs[1].new_status == "ASSESSED"


def test_confidence_ranges_and_detection_confidence_separate(test_users, test_incident):
    """13, 14. Verify classification_confidence is 0-1 and detection_confidence remains untouched."""
    token = test_users["tokens"]["analyst"]
    res = client.post(
        f"/api/incidents/{test_incident.id}/classify",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert 0.0 <= data["classification_confidence"] <= 1.0
    assert data["detection_confidence"] == "HIGH"


def test_database_rollback_on_persistence_failure(test_users, test_incident):
    """15. Verify database rollback if persistence fails during commit."""
    token = test_users["tokens"]["analyst"]
    with patch("sqlalchemy.orm.Session.commit", side_effect=Exception("Database connection loss")):
        res = client.post(
            f"/api/incidents/{test_incident.id}/classify",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code == 500
        err = res.json()
        assert "error" in err
        assert err["error"]["code"] == "DATABASE_ERROR"
