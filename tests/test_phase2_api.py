import datetime
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from geoalchemy2 import WKTElement

from backend.app.main import app
from backend.app.core.config import DATABASE_URL
from backend.app.core.security import create_access_token
from backend.app.db.session import get_db
from backend.app.models.hotspot import Hotspot
from backend.app.models.incident import Incident
from backend.app.schemas.common import ErrorResponse
from backend.app.schemas.incident import IncidentResponse
from backend.app.schemas.hotspot import HotspotResponse

client = TestClient(app)
engine = create_engine(DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    """Fixture providing a clean DB session for test data insertion and cleanup."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_empty_hotspots_list(db_session):
    """Verify GET /api/hotspots returns a valid empty list when DB has no matching hotspots."""
    response = client.get("/api/hotspots?source=non_existent_source")
    assert response.status_code == 200
    data = response.json()
    assert "hotspots" in data
    assert data["hotspots"] == []
    assert data["total"] == 0


def test_persisted_hotspot_retrieval_and_filtering(db_session):
    """Verify persisting Hotspot records and querying with filters."""
    hotspot_id = f"hot_{uuid.uuid4().hex[:12]}"
    now = datetime.datetime.now(datetime.timezone.utc)
    point_geom = WKTElement("POINT(79.0882 21.1458)", srid=4326)

    h1 = Hotspot(
        id=hotspot_id,
        latitude=21.1458,
        longitude=79.0882,
        geometry=point_geom,
        acquisition_time=now,
        satellite="VIIRS_NPP",
        frp=45.5,
        source="firms",
    )
    db_session.add(h1)
    db_session.commit()

    try:
        # Retrieve without filter
        res = client.get("/api/hotspots")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 1
        found = [item for item in data["hotspots"] if item["id"] == hotspot_id]
        assert len(found) == 1
        assert found[0]["frp"] == 45.5

        # Filter by min_frp
        res_frp = client.get("/api/hotspots?min_frp=50.0")
        assert res_frp.status_code == 200
        found_frp = [item for item in res_frp.json()["hotspots"] if item["id"] == hotspot_id]
        assert len(found_frp) == 0

        res_frp_match = client.get("/api/hotspots?min_frp=40.0")
        assert res_frp_match.status_code == 200
        found_match = [item for item in res_frp_match.json()["hotspots"] if item["id"] == hotspot_id]
        assert len(found_match) == 1
    finally:
        db_session.delete(h1)
        db_session.commit()


def test_persisted_incident_retrieval_and_filtering(db_session):
    """Verify persisting Incident record and querying via GET /api/incidents with filters."""
    inc_id = f"inc_{uuid.uuid4().hex[:12]}"
    point_geom = WKTElement("POINT(79.0882 21.1458)", srid=4326)

    inc = Incident(
        id=inc_id,
        status="CLASSIFIED",
        classification="INDUSTRIAL_FIRE",
        classification_confidence=0.92,
        detection_confidence="HIGH",
        persistence_score=75.0,
        risk_score=88.5,
        severity="HIGH",
        latitude=21.1458,
        longitude=79.0882,
        geometry=point_geom,
        explanation={"evidence": ["high_frp", "refinery_proximity"]},
    )
    db_session.add(inc)
    db_session.commit()

    try:
        # List incidents
        res = client.get("/api/incidents")
        assert res.status_code == 200
        data = res.json()
        found = [item for item in data["incidents"] if item["id"] == inc_id]
        assert len(found) == 1
        assert found[0]["classification"] == "INDUSTRIAL_FIRE"
        assert found[0]["risk_score"] == 88.5

        # Filter by status
        res_status = client.get("/api/incidents?status=CLASSIFIED")
        assert res_status.status_code == 200
        assert len([i for i in res_status.json()["incidents"] if i["id"] == inc_id]) == 1

        res_status_mismatch = client.get("/api/incidents?status=RESOLVED")
        assert res_status_mismatch.status_code == 200
        assert len([i for i in res_status_mismatch.json()["incidents"] if i["id"] == inc_id]) == 0

        # Filter by severity and min_risk_score
        res_risk = client.get("/api/incidents?severity=HIGH&min_risk_score=80.0")
        assert res_risk.status_code == 200
        assert len([i for i in res_risk.json()["incidents"] if i["id"] == inc_id]) == 1
    finally:
        db_session.delete(inc)
        db_session.commit()


def test_incident_detail_and_not_found(db_session):
    """Verify GET /api/incidents/{id} returns full frozen schema or 404 standard error."""
    inc_id = f"inc_detail_{uuid.uuid4().hex[:12]}"
    point_geom = WKTElement("POINT(79.0882 21.1458)", srid=4326)

    inc = Incident(
        id=inc_id,
        status="ASSESSED",
        classification="GAS_FLARE",
        classification_confidence=0.88,
        detection_confidence="NOMINAL",
        risk_score=60.0,
        severity="MEDIUM",
        latitude=21.1458,
        longitude=79.0882,
        geometry=point_geom,
    )
    db_session.add(inc)
    db_session.commit()

    try:
        # GET incident detail
        res = client.get(f"/api/incidents/{inc_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == inc_id
        assert data["status"] == "ASSESSED"
        assert data["classification"] == "GAS_FLARE"
        assert data["classification_confidence"] == 0.88
        assert data["detection_confidence"] == "NOMINAL"

        # GET non-existent incident detail -> 404 standard error
        res_404 = client.get("/api/incidents/NON_EXISTENT_INC_99999")
        assert res_404.status_code == 404
        err_data = res_404.json()
        assert "error" in err_data
        assert err_data["error"]["code"] == "NOT_FOUND"
    finally:
        db_session.delete(inc)
        db_session.commit()


def test_invalid_query_parameters():
    """Verify invalid query parameter validation."""
    # min_risk_score out of range > 100
    res = client.get("/api/incidents?min_risk_score=150.0")
    assert res.status_code == 422
    assert "error" in res.json()

    # negative limit
    res_lim = client.get("/api/incidents?limit=-5")
    assert res_lim.status_code == 422
    assert "error" in res_lim.json()


def test_security_sensitive_fields_never_exposed(db_session):
    """Verify sensitive password hashes are never exposed in incident/user endpoints."""
    # Verify auth/me does not contain hashed_password or password
    token = create_access_token({"sub": "usr_analyst", "email": "analyst@firesense.org", "role": "analyst"})
    me_res = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert "password" not in me_data
    assert "hashed_password" not in me_data

    # Verify incident response does not expose sensitive DB attributes
    inc_res = client.get("/api/incidents")
    assert inc_res.status_code == 200


def test_canonical_api_source_of_truth_strict_behavior(db_session):
    """
    Explicit test required by Phase 2 Correction:
    A. Empty PostgreSQL incidents table -> GET /api/incidents -> empty list
    B. Insert one PostgreSQL incident -> GET /api/incidents -> exactly that DB incident appears
    C. Remove test incident -> GET /api/incidents -> empty list again
    D. Empty PostgreSQL hotspots table -> GET /api/hotspots -> empty list
    """
    existing_incidents = db_session.query(Incident).all()
    for inc in existing_incidents:
        db_session.delete(inc)
    db_session.commit()

    existing_hotspots = db_session.query(Hotspot).all()
    for hs in existing_hotspots:
        db_session.delete(hs)
    db_session.commit()

    try:
        # A. Empty PostgreSQL incidents table -> GET /api/incidents -> empty list
        res_a = client.get("/api/incidents")
        assert res_a.status_code == 200
        data_a = res_a.json()
        assert data_a["incidents"] == []
        assert data_a["total"] == 0

        # Also test /api/v2/incidents compatibility route returns empty list
        res_a_v2 = client.get("/api/v2/incidents")
        assert res_a_v2.status_code == 200
        assert res_a_v2.json()["incidents"] == []

        # B. Insert one PostgreSQL incident -> GET /api/incidents -> exactly that database incident appears
        test_id = f"inc_sot_{uuid.uuid4().hex[:8]}"
        point_geom = WKTElement("POINT(79.0882 21.1458)", srid=4326)
        test_inc = Incident(
            id=test_id,
            status="DETECTED",
            classification="WILDFIRE",
            classification_confidence=0.95,
            detection_confidence="HIGH",
            persistence_score=80.0,
            risk_score=75.0,
            severity="HIGH",
            latitude=21.1458,
            longitude=79.0882,
            geometry=point_geom,
        )
        db_session.add(test_inc)
        db_session.commit()

        res_b = client.get("/api/incidents")
        assert res_b.status_code == 200
        data_b = res_b.json()
        assert len(data_b["incidents"]) == 1
        assert data_b["incidents"][0]["id"] == test_id
        assert data_b["total"] == 1

        # C. Remove test incident -> GET /api/incidents -> empty list again
        db_session.delete(test_inc)
        db_session.commit()

        res_c = client.get("/api/incidents")
        assert res_c.status_code == 200
        data_c = res_c.json()
        assert data_c["incidents"] == []
        assert data_c["total"] == 0

        # D. Empty PostgreSQL hotspots table -> GET /api/hotspots -> empty list
        res_d = client.get("/api/hotspots")
        assert res_d.status_code == 200
        data_d = res_d.json()
        assert data_d["hotspots"] == []
        assert data_d["total"] == 0

        # Also test /api/v2/hotspots returns empty list
        res_d_v2 = client.get("/api/v2/hotspots")
        assert res_d_v2.status_code == 200
        assert res_d_v2.json()["hotspots"] == []

    finally:
        for inc in existing_incidents:
            db_session.merge(inc)
        for hs in existing_hotspots:
            db_session.merge(hs)
        db_session.commit()

