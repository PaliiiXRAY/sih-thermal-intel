"""
Integration tests for Phase 4: PostGIS Context Enrichment (GET /api/incidents/{id}/context).
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
        user_id = f"usr_ctx_{role}_{uuid.uuid4().hex[:6]}"
        email = f"ctx_{role}_{uuid.uuid4().hex[:6]}@firesense.org"
        u = User(
            id=user_id,
            email=email,
            hashed_password="hash",
            full_name=f"Context Test {role.capitalize()}",
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
def spatial_test_data(db_session):
    """
    Seed an incident, 2 assets at known distances, and 2 responders at known distances.
    Incident: (21.1458, 79.0882) - Nagpur center
    Asset 1 (Near): ~1.0 km away (21.1500, 79.0950)
    Asset 2 (Far): ~12.0 km away (21.2500, 79.1500)
    Responder 1 (Near): ~2.0 km away (21.1600, 79.0900)
    Responder 2 (Far): ~25.0 km away (21.3500, 79.2500)
    """
    inc_id = f"inc_ctx_{uuid.uuid4().hex[:8]}"
    inc_geom = WKTElement("POINT(79.0882 21.1458)", srid=4326)

    inc = Incident(
        id=inc_id,
        status="DETECTED",
        classification="WILDFIRE",
        latitude=21.1458,
        longitude=79.0882,
        geometry=inc_geom,
    )
    db_session.add(inc)

    # Near Asset (~1 km)
    ast1_id = f"ast_near_{uuid.uuid4().hex[:6]}"
    ast1 = Asset(
        id=ast1_id,
        name="Nagpur Substation Alpha",
        type="industrial_plant",
        category="critical_infrastructure",
        latitude=21.1500,
        longitude=79.0950,
        geometry=WKTElement("POINT(79.0950 21.1500)", srid=4326),
    )
    db_session.add(ast1)

    # Far Asset (~12 km)
    ast2_id = f"ast_far_{uuid.uuid4().hex[:6]}"
    ast2 = Asset(
        id=ast2_id,
        name="Kamptee Power Hub",
        type="facility",
        category="critical_infrastructure",
        latitude=21.2500,
        longitude=79.1500,
        geometry=WKTElement("POINT(79.1500 21.2500)", srid=4326),
    )
    db_session.add(ast2)

    # Near Responder (~2 km)
    resp1_id = f"resp_near_{uuid.uuid4().hex[:6]}"
    resp1 = Responder(
        id=resp1_id,
        name="Nagpur Fire Brigade Unit 1",
        type="fire_brigade",
        status="AVAILABLE",
        organization="Nagpur Municipal Corp",
        latitude=21.1600,
        longitude=79.0900,
        geometry=WKTElement("POINT(79.0900 21.1600)", srid=4326),
    )
    db_session.add(resp1)

    # Far Responder (~25 km)
    resp2_id = f"resp_far_{uuid.uuid4().hex[:6]}"
    resp2 = Responder(
        id=resp2_id,
        name="Bhandara Hazmat Squad",
        type="hazmat_unit",
        status="AVAILABLE",
        organization="State Disaster Force",
        latitude=21.3500,
        longitude=79.2500,
        geometry=WKTElement("POINT(79.2500 21.3500)", srid=4326),
    )
    db_session.add(resp2)

    db_session.commit()

    yield {
        "incident_id": inc_id,
        "near_asset_id": ast1_id,
        "far_asset_id": ast2_id,
        "near_responder_id": resp1_id,
        "far_responder_id": resp2_id,
    }

    # Cleanup
    db_session.query(Incident).filter(Incident.id == inc_id).delete()
    db_session.query(Asset).filter(Asset.id.in_([ast1_id, ast2_id])).delete()
    db_session.query(Responder).filter(Responder.id.in_([resp1_id, resp2_id])).delete()
    db_session.commit()


def test_analyst_can_retrieve_context(test_users, spatial_test_data):
    """1. Verify analyst role can access context endpoint."""
    token = test_users["tokens"]["analyst"]
    inc_id = spatial_test_data["incident_id"]
    res = client.get(f"/api/incidents/{inc_id}/context", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["incident_id"] == inc_id
    assert "nearest_assets" in data
    assert "nearest_responders" in data


def test_authority_can_retrieve_context(test_users, spatial_test_data):
    """2. Verify authority role can access context endpoint."""
    token = test_users["tokens"]["authority"]
    inc_id = spatial_test_data["incident_id"]
    res = client.get(f"/api/incidents/{inc_id}/context", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["incident_id"] == inc_id


def test_responder_can_retrieve_context(test_users, spatial_test_data):
    """3. Verify responder role can access context endpoint for operational use."""
    token = test_users["tokens"]["responder"]
    inc_id = spatial_test_data["incident_id"]
    res = client.get(f"/api/incidents/{inc_id}/context", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["incident_id"] == inc_id


def test_admin_can_retrieve_context(test_users, spatial_test_data):
    """4. Verify admin role can access context endpoint."""
    token = test_users["tokens"]["admin"]
    inc_id = spatial_test_data["incident_id"]
    res = client.get(f"/api/incidents/{inc_id}/context", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["incident_id"] == inc_id


def test_unauthenticated_request_receives_401(spatial_test_data):
    """5. Verify unauthenticated request receives 401 Unauthorized."""
    inc_id = spatial_test_data["incident_id"]
    res = client.get(f"/api/incidents/{inc_id}/context")
    assert res.status_code == 401
    err = res.json()
    assert "error" in err
    assert err["error"]["code"] in ["MISSING_TOKEN", "UNAUTHENTICATED"]


def test_unauthorized_role_receives_403(test_users, spatial_test_data):
    """6. Verify citizen role receives 403 Forbidden."""
    token = test_users["tokens"]["citizen"]
    inc_id = spatial_test_data["incident_id"]
    res = client.get(f"/api/incidents/{inc_id}/context", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403
    err = res.json()
    assert "error" in err
    assert err["error"]["code"] == "FORBIDDEN"


def test_nonexistent_incident_receives_404(test_users):
    """7. Verify non-existent incident ID receives 404 Not Found."""
    token = test_users["tokens"]["analyst"]
    res = client.get("/api/incidents/NON_EXISTENT_INCIDENT_9999/context", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 404
    err = res.json()
    assert "error" in err
    assert err["error"]["code"] == "NOT_FOUND"


def test_nearest_asset_responder_calculation_and_sorting(test_users, spatial_test_data):
    """8, 9, 10, 15. Verify PostGIS distance calculation, ordering (nearest first), and persisted records."""
    token = test_users["tokens"]["analyst"]
    inc_id = spatial_test_data["incident_id"]
    res = client.get(f"/api/incidents/{inc_id}/context", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()

    # Verify Assets
    assets = data["nearest_assets"]
    assert len(assets) >= 2
    # Verify sorting: nearest first
    assert assets[0]["id"] == spatial_test_data["near_asset_id"]
    assert assets[1]["id"] == spatial_test_data["far_asset_id"]
    assert assets[0]["distance_km"] < assets[1]["distance_km"]
    assert 0.5 <= assets[0]["distance_km"] <= 1.5  # ~1 km
    assert 10.0 <= assets[1]["distance_km"] <= 15.0  # ~12 km

    # Verify Responders
    responders = data["nearest_responders"]
    assert len(responders) >= 2
    # Verify sorting: nearest first
    assert responders[0]["id"] == spatial_test_data["near_responder_id"]
    assert responders[1]["id"] == spatial_test_data["far_responder_id"]
    assert responders[0]["distance_km"] < responders[1]["distance_km"]
    assert 1.0 <= responders[0]["distance_km"] <= 3.0  # ~2 km
    assert 20.0 <= responders[1]["distance_km"] <= 30.0  # ~25 km


def test_empty_nearby_assets_and_responders(test_users, db_session):
    """11, 12. Verify incident with no nearby entities within search radius returns empty lists."""
    # Create isolated incident in remote location (e.g., middle of ocean - 0.0, 0.0)
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
        token = test_users["tokens"]["analyst"]
        res = client.get(f"/api/incidents/{inc_remote_id}/context", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        data = res.json()
        assert data["nearest_assets"] == []
        assert data["nearest_responders"] == []
    finally:
        db_session.delete(inc_remote)
        db_session.commit()


def test_incident_location_validation(test_users, db_session):
    """13. Verify incident with out-of-bounds coordinates triggers controlled 400 error."""
    inc_invalid_id = f"inc_inv_{uuid.uuid4().hex[:8]}"
    inc_invalid = Incident(
        id=inc_invalid_id,
        status="DETECTED",
        latitude=190.0,  # Invalid lat > 90
        longitude=79.0882,
        geometry=WKTElement("POINT(79.0882 190.0)", srid=4326),
    )
    db_session.add(inc_invalid)
    db_session.commit()

    try:
        token = test_users["tokens"]["analyst"]
        res = client.get(f"/api/incidents/{inc_invalid_id}/context", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 400
        err = res.json()
        assert "error" in err
        assert err["error"]["code"] == "INVALID_LOCATION"
    finally:
        db_session.delete(inc_invalid)
        db_session.commit()


def test_context_retrieval_does_not_modify_incident(test_users, spatial_test_data, db_session):
    """14. Verify context enrichment endpoint is read-only and side-effect free."""
    token = test_users["tokens"]["analyst"]
    inc_id = spatial_test_data["incident_id"]

    db_session.expire_all()
    inc_before = db_session.query(Incident).filter(Incident.id == inc_id).first()
    status_before = inc_before.status
    updated_at_before = inc_before.updated_at

    res = client.get(f"/api/incidents/{inc_id}/context", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200

    db_session.expire_all()
    inc_after = db_session.query(Incident).filter(Incident.id == inc_id).first()
    assert inc_after.status == status_before
    assert inc_after.updated_at == updated_at_before


def test_api_v2_compatibility_route(test_users, spatial_test_data):
    """16. Verify /api/v2/incidents/{id}/context delegates to same implementation."""
    token = test_users["tokens"]["analyst"]
    inc_id = spatial_test_data["incident_id"]
    res = client.get(f"/api/v2/incidents/{inc_id}/context", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["incident_id"] == inc_id
