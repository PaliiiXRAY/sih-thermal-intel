"""
Integration tests for Phase 5: Transparent Risk / Priority Engine (GET /api/incidents/{id}/risk).
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
from backend.app.models.asset import Asset
from backend.app.models.incident import Incident
from backend.app.models.user import User
from backend.app.services.risk.engine import (
    calculate_risk,
    get_severity_band,
    SEVERITY_MAP,
    SEVERITY_WEIGHT,
    PERSISTENCE_WEIGHT,
    EXPOSURE_WEIGHT,
    INFRASTRUCTURE_WEIGHT,
    GROWTH_WEIGHT,
)

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
        user_id = f"usr_risk_{role}_{uuid.uuid4().hex[:6]}"
        email = f"risk_{role}_{uuid.uuid4().hex[:6]}@firesense.org"
        u = User(
            id=user_id,
            email=email,
            hashed_password="hash",
            full_name=f"Risk Test {role.capitalize()}",
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
def risk_test_incident(db_session):
    """Fixture to create a test incident and nearby asset in PostgreSQL."""
    inc_id = f"inc_rsk_{uuid.uuid4().hex[:8]}"
    inc = Incident(
        id=inc_id,
        status="DETECTED",
        severity="HIGH",
        persistence_score=80.0,
        latitude=21.1458,
        longitude=79.0882,
        geometry=WKTElement("POINT(79.0882 21.1458)", srid=4326),
        explanation={"frp": 65.0},
    )
    db_session.add(inc)

    ast_id = f"ast_rsk_{uuid.uuid4().hex[:6]}"
    ast = Asset(
        id=ast_id,
        name="Nagpur Central Power Station",
        type="industrial_plant",
        category="critical_infrastructure",
        latitude=21.1500,
        longitude=79.0900,
        geometry=WKTElement("POINT(79.0900 21.1500)", srid=4326),
    )
    db_session.add(ast)
    db_session.commit()

    yield {"incident_id": inc_id, "asset_id": ast_id}

    db_session.query(Incident).filter(Incident.id == inc_id).delete()
    db_session.query(Asset).filter(Asset.id == ast_id).delete()
    db_session.commit()


def test_analyst_can_retrieve_risk(test_users, risk_test_incident):
    """1. Verify analyst role can access risk endpoint."""
    token = test_users["tokens"]["analyst"]
    inc_id = risk_test_incident["incident_id"]
    res = client.get(f"/api/incidents/{inc_id}/risk", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["incident_id"] == inc_id
    assert "risk_score" in data
    assert "severity" in data
    assert "reasons" in data


def test_authority_can_retrieve_risk(test_users, risk_test_incident):
    """2. Verify authority role can access risk endpoint."""
    token = test_users["tokens"]["authority"]
    inc_id = risk_test_incident["incident_id"]
    res = client.get(f"/api/incidents/{inc_id}/risk", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["incident_id"] == inc_id


def test_responder_can_retrieve_risk(test_users, risk_test_incident):
    """3. Verify responder role can access risk endpoint."""
    token = test_users["tokens"]["responder"]
    inc_id = risk_test_incident["incident_id"]
    res = client.get(f"/api/incidents/{inc_id}/risk", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["incident_id"] == inc_id


def test_admin_can_retrieve_risk(test_users, risk_test_incident):
    """4. Verify admin role can access risk endpoint."""
    token = test_users["tokens"]["admin"]
    inc_id = risk_test_incident["incident_id"]
    res = client.get(f"/api/incidents/{inc_id}/risk", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["incident_id"] == inc_id


def test_unauthenticated_request_receives_401(risk_test_incident):
    """5. Verify unauthenticated request receives 401 Unauthorized."""
    inc_id = risk_test_incident["incident_id"]
    res = client.get(f"/api/incidents/{inc_id}/risk")
    assert res.status_code == 401
    err = res.json()
    assert "error" in err
    assert err["error"]["code"] in ["MISSING_TOKEN", "UNAUTHENTICATED"]


def test_unauthorized_role_receives_403(test_users, risk_test_incident):
    """6. Verify citizen role receives 403 Forbidden."""
    token = test_users["tokens"]["citizen"]
    inc_id = risk_test_incident["incident_id"]
    res = client.get(f"/api/incidents/{inc_id}/risk", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403
    err = res.json()
    assert "error" in err
    assert err["error"]["code"] == "FORBIDDEN"


def test_nonexistent_incident_receives_404(test_users):
    """7. Verify non-existent incident ID receives 404 Not Found."""
    token = test_users["tokens"]["analyst"]
    res = client.get("/api/incidents/NON_EXISTENT_INC_9999/risk", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 404
    err = res.json()
    assert "error" in err
    assert err["error"]["code"] == "NOT_FOUND"


def test_deterministic_score_calculation_and_bounds():
    """8, 9, 17. Verify score calculation is deterministic and remains strictly between 0 and 100."""
    inc_data = {
        "id": "INC-DET-1",
        "severity": "CRITICAL",
        "persistence_score": 95.0,
        "frp": 80.0,
    }
    context_data = {
        "nearest_assets": [
            {"id": "ast_1", "type": "industrial_plant", "category": "critical_infrastructure", "distance_km": 1.2}
        ]
    }

    res1 = calculate_risk(inc_data, context_data)
    res2 = calculate_risk(inc_data, context_data)

    assert res1 == res2
    assert 0.0 <= res1["risk_score"] <= 100.0
    assert res1["severity_band"] == "CRITICAL"


def test_severity_normalization_mapping():
    """10. Verify severity normalization mapping for CRITICAL, HIGH, MEDIUM, LOW."""
    assert SEVERITY_MAP["CRITICAL"] == 100.0
    assert SEVERITY_MAP["HIGH"] == 75.0
    assert SEVERITY_MAP["MEDIUM"] == 50.0
    assert SEVERITY_MAP["LOW"] == 25.0

    r_crit = calculate_risk({"severity": "CRITICAL"})
    r_low = calculate_risk({"severity": "LOW"})
    assert r_crit["factors"]["severity"] == 100.0
    assert r_low["factors"]["severity"] == 25.0


def test_factors_and_reasons_returned():
    """11, 12, 13, 14, 15, 16. Verify all 5 component factors, severity band, and explanations are returned."""
    inc_data = {
        "id": "INC-FACTORS",
        "severity": "HIGH",
        "persistence_score": 80.0,
        "frp": 50.0,
    }
    context_data = {
        "nearest_assets": [
            {"id": "ast_sub", "type": "substation", "category": "critical_infrastructure", "distance_km": 2.0}
        ]
    }
    res = calculate_risk(inc_data, context_data)

    factors = res["factors"]
    assert "severity" in factors
    assert "persistence" in factors
    assert "exposure" in factors
    assert "infrastructure" in factors
    assert "growth" in factors

    assert isinstance(res["reasons"], list)
    assert len(res["reasons"]) > 0
    assert get_severity_band(res["risk_score"]) == res["severity_band"]


def test_get_risk_does_not_mutate_incident(test_users, risk_test_incident, db_session):
    """18. Verify GET risk endpoint is read-only and does not mutate incident in DB."""
    token = test_users["tokens"]["analyst"]
    inc_id = risk_test_incident["incident_id"]

    db_session.expire_all()
    inc_before = db_session.query(Incident).filter(Incident.id == inc_id).first()
    updated_at_before = inc_before.updated_at

    res = client.get(f"/api/incidents/{inc_id}/risk", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200

    db_session.expire_all()
    inc_after = db_session.query(Incident).filter(Incident.id == inc_id).first()
    assert inc_after.updated_at == updated_at_before


def test_missing_contextual_and_persistence_data_handled_safely():
    """19. Verify missing contextual or persistence data is handled safely with neutral defaults."""
    sparse_inc = {"id": "INC-SPARSE"}
    res = calculate_risk(sparse_inc, None)

    assert 0.0 <= res["risk_score"] <= 100.0
    assert len(res["reasons"]) > 0
    assert any("Persistence score missing" in r or "neutral" in r for r in res["reasons"])


def test_api_v2_compatibility_route(test_users, risk_test_incident):
    """20. Verify /api/v2/incidents/{id}/risk delegates to same implementation."""
    token = test_users["tokens"]["analyst"]
    inc_id = risk_test_incident["incident_id"]
    res = client.get(f"/api/v2/incidents/{inc_id}/risk", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["incident_id"] == inc_id
