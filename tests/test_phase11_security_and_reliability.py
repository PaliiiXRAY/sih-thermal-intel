"""
Phase 11 Security, Reliability & Authorization Hardening Tests.
Verifies RBAC access matrix, consistent error envelopes, sanitized health checks,
and credential protection.
"""
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from geoalchemy2.elements import WKTElement

from backend.app.main import app
from backend.app.core.config import DATABASE_URL
from backend.app.core.security import create_access_token, verify_password, hash_password
from backend.app.models.incident import Incident
from backend.app.models.user import User

client = TestClient(app)
engine = create_engine(DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_rbac_users(db_session):
    users = {}
    tokens = {}
    for role in ["analyst", "authority", "responder", "admin", "citizen"]:
        u_id = f"usr_p11_{role}_{uuid.uuid4().hex[:6]}"
        email = f"p11_{role}_{uuid.uuid4().hex[:6]}@firesense.org"
        u = User(
            id=u_id,
            email=email,
            hashed_password=hash_password("password123"),
            full_name=f"Phase11 {role.capitalize()}",
            role=role,
            is_active=True,
        )
        db_session.add(u)
        users[role] = u
    db_session.commit()

    for role, u in users.items():
        tokens[role] = create_access_token({"sub": u.id, "email": u.email, "role": u.role})

    return {"users": users, "tokens": tokens}


def test_rbac_authorization_matrix(db_session: Session, test_rbac_users):
    """
    Verify strict role-based access control matrix across core endpoints:
    Endpoint                      Analyst   Authority   Responder   Admin   Unauth
    POST /classify                200       200         403         200     401
    POST /alert                   403       200         403         200     401
    PATCH /status                 403       200         200         200     401
    GET /public/alerts            200       200         200         200     200
    """
    tokens = test_rbac_users["tokens"]

    # Create test incident
    inc_id = f"inc_rbac_{uuid.uuid4().hex[:8]}"
    inc = Incident(
        id=inc_id,
        latitude=20.85,
        longitude=85.10,
        geometry=WKTElement("POINT(85.10 20.85)", srid=4326),
        status="DETECTED",
        severity="HIGH",
    )
    db_session.add(inc)
    db_session.commit()

    # --- 1. POST /classify ---
    unauth_resp = client.post(f"/api/incidents/{inc_id}/classify")
    assert unauth_resp.status_code == 401

    resp_forbidden = client.post(
        f"/api/incidents/{inc_id}/classify",
        headers={"Authorization": f"Bearer {tokens['responder']}"},
    )
    assert resp_forbidden.status_code == 403

    analyst_ok = client.post(
        f"/api/incidents/{inc_id}/classify",
        headers={"Authorization": f"Bearer {tokens['analyst']}"},
    )
    assert analyst_ok.status_code == 200

    # Advance to ASSESSED for alert testing
    inc_refreshed = db_session.query(Incident).filter(Incident.id == inc_id).first()
    inc_refreshed.status = "ASSESSED"
    db_session.commit()

    # --- 2. POST /alert ---
    unauth_alert = client.post(f"/api/incidents/{inc_id}/alert")
    assert unauth_alert.status_code == 401

    analyst_alert_denied = client.post(
        f"/api/incidents/{inc_id}/alert",
        headers={"Authorization": f"Bearer {tokens['analyst']}"},
    )
    assert analyst_alert_denied.status_code == 403

    resp_alert_denied = client.post(
        f"/api/incidents/{inc_id}/alert",
        headers={"Authorization": f"Bearer {tokens['responder']}"},
    )
    assert resp_alert_denied.status_code == 403

    auth_alert_ok = client.post(
        f"/api/incidents/{inc_id}/alert",
        headers={"Authorization": f"Bearer {tokens['authority']}"},
    )
    assert auth_alert_ok.status_code == 200

    # --- 3. PATCH /status ---
    unauth_status = client.patch(f"/api/incidents/{inc_id}/status", json={"status": "ALERTED"})
    assert unauth_status.status_code == 401

    analyst_status_denied = client.patch(
        f"/api/incidents/{inc_id}/status",
        json={"status": "ALERTED"},
        headers={"Authorization": f"Bearer {tokens['analyst']}"},
    )
    assert analyst_status_denied.status_code == 403

    auth_status_ok = client.patch(
        f"/api/incidents/{inc_id}/status",
        json={"status": "ALERTED"},
        headers={"Authorization": f"Bearer {tokens['authority']}"},
    )
    assert auth_status_ok.status_code == 200

    responder_status_ok = client.patch(
        f"/api/incidents/{inc_id}/status",
        json={"status": "ACKNOWLEDGED"},
        headers={"Authorization": f"Bearer {tokens['responder']}"},
    )
    assert responder_status_ok.status_code == 200

    # --- 4. GET /public/alerts ---
    pub_unauth = client.get("/public/alerts")
    assert pub_unauth.status_code == 200


def test_consistent_error_response_envelope():
    """Verify API errors follow uniform {error: {code, message, details}} envelope."""
    # 404 test
    resp_404 = client.get("/api/incidents/inc_nonexistent_99999")
    assert resp_404.status_code == 404
    data_404 = resp_404.json()
    assert "error" in data_404
    assert data_404["error"]["code"] == "NOT_FOUND"
    assert "message" in data_404["error"]

    # 422 validation error test
    resp_422 = client.get("/api/hotspots?min_frp=-50")
    assert resp_422.status_code == 422
    data_422 = resp_422.json()
    assert "error" in data_422
    assert data_422["error"]["code"] == "VALIDATION_ERROR"
    assert "Traceback" not in resp_422.text  # Zero stack trace leaks


def test_health_check_endpoints_sanitized():
    """Verify health endpoints return useful info without leaking database passwords/URIs."""
    h1 = client.get("/health")
    assert h1.status_code == 200
    assert h1.json()["status"] == "ok"

    h2 = client.get("/api/v2/health")
    assert h2.status_code == 200
    assert h2.json()["status"] == "ok"
    assert h2.json()["service"] == "firesense-backend"

    h3 = client.get("/api/v2/health/database")
    assert h3.status_code == 200
    data_h3 = h3.json()
    assert data_h3["status"] == "ok"
    assert data_h3["database"] == "connected"
    assert "password" not in str(data_h3).lower()
    assert "postgresql://" not in str(data_h3).lower()


def test_password_hashing_security():
    """Verify bcrypt hashing generates salted non-reversible hashes."""
    pwd = "HackathonSecurePassword2026!"
    h1 = hash_password(pwd)
    h2 = hash_password(pwd)
    assert h1 != h2  # Salt ensures distinct hashes
    assert verify_password(pwd, h1) is True
    assert verify_password(pwd, h2) is True
    assert verify_password("WrongPassword", h1) is False
