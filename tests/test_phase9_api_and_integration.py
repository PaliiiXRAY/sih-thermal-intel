"""
Phase 9 Backend Contract Integration Tests.
Verifies public alerts, nearby responders, incident audit timeline, and static route serving.
"""
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from geoalchemy2.elements import WKTElement

from backend.app.main import app
from backend.app.core.config import DATABASE_URL
from backend.app.models.alert import Alert
from backend.app.models.incident import Incident
from backend.app.models.incident_log import IncidentLog
from backend.app.models.responder import Responder
from backend.app.models.user import User
from backend.app.core.security import create_access_token

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
        user_id = f"usr_p9_{role}_{uuid.uuid4().hex[:6]}"
        email = f"p9_{role}_{uuid.uuid4().hex[:6]}@firesense.org"
        u = User(
            id=user_id,
            email=email,
            hashed_password="hash",
            full_name=f"Phase9 Test {role.capitalize()}",
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


def test_public_alerts_endpoint(db_session: Session):
    """Verify GET /public/alerts returns public safe simulated alerts without leaking PII."""
    # Create test incident and alert
    inc_id = f"inc_pub_{uuid.uuid4().hex[:8]}"
    inc = Incident(
        id=inc_id,
        latitude=20.85,
        longitude=85.10,
        geometry=WKTElement("POINT(85.10 20.85)", srid=4326),
        status="ALERTED",
        severity="HIGH",
        classification="INDUSTRIAL_FIRE",
    )
    db_session.add(inc)
    db_session.commit()

    alert = Alert(
        incident_id=inc_id,
        alert_type="INCIDENT_PRIORITY_ALERT",
        is_simulated=True,
        status="SENT",
        message="Simulated Public Alert Test",
    )
    db_session.add(alert)
    db_session.commit()

    # Public endpoint requires NO authentication
    resp = client.get("/public/alerts")
    assert resp.status_code == 200
    data = resp.json()
    assert "alerts" in data
    assert "notice" in data
    assert data["total"] >= 1
    
    # Verify public alert structure contains no sensitive details
    matching = [a for a in data["alerts"] if a["incident_id"] == inc_id]
    assert len(matching) == 1
    alert_obj = matching[0]
    assert alert_obj["is_simulated"] is True
    assert alert_obj["classification"] == "INDUSTRIAL_FIRE"
    assert alert_obj["severity"] == "HIGH"
    assert alert_obj["location"]["latitude"] == 20.85
    assert "metadata" not in alert_obj  # No internal metadata
    assert "recommended_responder_id" not in alert_obj  # No responder personal ID


def test_nearby_responders_endpoint(db_session: Session):
    """Verify GET /api/responders/nearby uses PostGIS to find nearest units."""
    # Seed responder near Angul (20.84, 85.10)
    resp_id = f"resp_test_{uuid.uuid4().hex[:6]}"
    responder = Responder(
        id=resp_id,
        name="Angul Fire Station 1",
        type="fire_brigade",
        status="AVAILABLE",
        organization="Odisha Fire Service",
        contact_info="Synthetic Radio Ch-1",
        latitude=20.842,
        longitude=85.102,
        geometry=WKTElement("POINT(85.102 20.842)", srid=4326),
    )
    db_session.add(responder)
    db_session.commit()

    # Query within 20km
    resp = client.get("/api/responders/nearby", params={"latitude": 20.840, "longitude": 85.100, "radius_km": 20.0})
    assert resp.status_code == 200
    data = resp.json()
    assert "responders" in data
    assert data["total"] >= 1
    
    matching = [r for r in data["responders"] if r["id"] == resp_id]
    assert len(matching) == 1
    unit = matching[0]
    assert unit["name"] == "Angul Fire Station 1"
    assert unit["type"] == "fire_brigade"
    assert "contact_info" not in unit  # Private contact details excluded
    assert unit["distance_km"] < 5.0


def test_incident_audit_timeline_endpoint(db_session: Session, test_users):
    """Verify GET /api/incidents/{id}/timeline returns append-only audit trail."""
    inc_id = f"inc_timeline_{uuid.uuid4().hex[:8]}"
    inc = Incident(
        id=inc_id,
        latitude=20.85,
        longitude=85.10,
        geometry=WKTElement("POINT(85.10 20.85)", srid=4326),
        status="DETECTED",
    )
    db_session.add(inc)

    log1 = IncidentLog(
        incident_id=inc_id,
        action="DETECTED",
        old_status=None,
        new_status="DETECTED",
        changed_by="SYSTEM",
        note="Initial satellite detection ingested",
    )
    log2 = IncidentLog(
        incident_id=inc_id,
        action="CLASSIFY",
        old_status="DETECTED",
        new_status="CLASSIFIED",
        changed_by="analyst",
        note="Classified as INDUSTRIAL_FIRE",
    )
    db_session.add_all([log1, log2])
    db_session.commit()

    # Unauthenticated should receive 401
    unauth_resp = client.get(f"/api/incidents/{inc_id}/timeline")
    assert unauth_resp.status_code == 401

    # Authorized roles (analyst, authority, responder, admin) should receive 200
    for role in ["analyst", "authority", "responder", "admin"]:
        auth_hdr = {"Authorization": f"Bearer {test_users['tokens'][role]}"}
        res = client.get(f"/api/incidents/{inc_id}/timeline", headers=auth_hdr)
        assert res.status_code == 200
        data = res.json()
        assert data["incident_id"] == inc_id
        assert data["total_events"] >= 2
        assert len(data["timeline"]) >= 2
        assert data["timeline"][0]["action"] == "DETECTED"
        assert data["timeline"][1]["action"] == "CLASSIFY"


def test_static_routes_and_frontend_serving():
    """Verify root HTML and app views are correctly served by FastAPI."""
    resp_root = client.get("/")
    assert resp_root.status_code == 200
    assert "text/html" in resp_root.headers.get("content-type", "")

    resp_app = client.get("/app")
    assert resp_app.status_code == 200
    assert "text/html" in resp_app.headers.get("content-type", "")
    assert "FireSense" in resp_app.text
