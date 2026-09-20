import os
import sys
import datetime
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from geoalchemy2 import WKTElement

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.main import app
from backend.app.core.config import DATABASE_URL
from backend.app.models.incident import Incident
from backend.app.models.user import User
from backend.app.core.security import create_access_token, hash_password

client = TestClient(app)
engine = create_engine(DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_test_incident():
    """Ensure a test incident exists in PostgreSQL for route testing, cleaned up afterward."""
    db = TestingSessionLocal()
    inc_id = "INC-2026-0042"
    point_geom = WKTElement("POINT(79.0882 21.1458)", srid=4326)

    # Check if exists, else insert
    inc = db.query(Incident).filter(Incident.id == inc_id).first()
    if not inc:
        inc = Incident(
            id=inc_id,
            status="DETECTED",
            classification="WILDFIRE",
            classification_confidence=0.91,
            detection_confidence="HIGH",
            persistence_score=80.0,
            risk_score=87.0,
            severity="CRITICAL",
            latitude=21.1458,
            longitude=79.0882,
            geometry=point_geom,
            explanation={"evidence": ["high_frp", "forest_landcover"]},
        )
        db.add(inc)
        db.commit()

    # Reset incident status so tests are order-independent
    if inc and inc.status != "DETECTED":
        inc.status = "DETECTED"
        db.commit()

    yield

    # Cleanup
    try:
        db.query(Incident).filter(Incident.id == inc_id).delete()
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def test_health_endpoints():
    r1 = client.get("/health")
    assert r1.status_code == 200
    assert r1.json() == {"status": "ok"}

    r2 = client.get("/api/v2/health")
    assert r2.status_code == 200
    assert r2.json() == {"status": "ok", "service": "firesense-backend"}


def test_get_incidents():
    response = client.get("/api/v2/incidents")
    assert response.status_code == 200
    data = response.json()
    assert "incidents" in data
    assert isinstance(data["incidents"], list)
    assert len(data["incidents"]) > 0


def test_get_single_incident():
    inc_id = "INC-2026-0042"
    response = client.get(f"/api/v2/incidents/{inc_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == inc_id

    # Test non-existent incident
    r_notfound = client.get("/api/v2/incidents/NON_EXISTENT_ID_999")
    assert r_notfound.status_code == 404
    assert "error" in r_notfound.json()


def _admin_headers():
    """Create (or reuse) an admin user and return auth headers."""
    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == "route-admin@firesense.org").first()
    if not user:
        user = User(
            id="usr_route_admin",
            email="route-admin@firesense.org",
            hashed_password=hash_password("test-pass"),
            full_name="Route Admin",
            role="admin",
            is_active=True,
        )
        db.add(user)
        db.commit()
    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})
    db.close()
    return {"Authorization": f"Bearer {token}"}


def test_update_incident_status_unauthenticated_rejected():
    """The insecure unauthenticated POST status alias must be gone; PATCH requires auth."""
    inc_id = "INC-2026-0042"
    assert client.post(f"/api/v2/incidents/{inc_id}/status", json={"status": "CLASSIFIED"}).status_code == 405
    assert client.patch(f"/api/v2/incidents/{inc_id}/status", json={"status": "CLASSIFIED"}).status_code == 401


def test_update_incident_status_with_auth():
    inc_id = "INC-2026-0042"
    headers = _admin_headers()
    res = client.patch(f"/api/v2/incidents/{inc_id}/status", json={"status": "CLASSIFIED"}, headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "CLASSIFIED"
    assert data["id"] == inc_id


def test_dispatch_incident_requires_auth():
    assert client.post("/api/v2/incidents/INC-2026-0042/dispatch").status_code == 401


def test_dispatch_incident_with_auth():
    inc_id = "INC-2026-0042"
    headers = _admin_headers()

    def transition(to_status):
        r = client.patch(f"/api/v2/incidents/{inc_id}/status", json={"status": to_status}, headers=headers)
        assert r.status_code == 200, r.text
        return r.json()

    transition("CLASSIFIED")
    transition("ASSESSED")
    res = client.post(f"/api/v2/incidents/{inc_id}/dispatch", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["success"] is True
    assert data["status"] == "ALERTED"
    assert data["old_status"] == "ASSESSED"


def test_get_stats():
    response = client.get("/api/v2/stats")
    assert response.status_code == 200
    data = response.json()
    assert "hotspots_analyzed" in data
    assert "critical_alerts" in data


def test_get_reports_requires_auth():
    assert client.get("/api/v2/reports").status_code == 401
    res = client.get("/api/v2/reports", headers=_admin_headers())
    assert res.status_code == 200
    data = res.json()
    assert "reports" in data
    assert isinstance(data["reports"], list)


def test_submit_and_verify_report():
    # Submit stays public
    submit_res = client.post(
        "/api/v2/reports/submit",
        json={
            "location": "Test Location Ward 12",
            "type": "Smoke plume",
            "notes": "Test report notes"
        }
    )
    assert submit_res.status_code == 200
    res_data = submit_res.json()
    assert res_data["success"] is True
    report_id = res_data["report"]["id"]

    # Verify now requires auth
    assert client.post("/api/v2/reports/verify", json={"id": report_id}).status_code == 401

    verify_res = client.post(
        "/api/v2/reports/verify",
        json={"id": report_id},
        headers=_admin_headers(),
    )
    assert verify_res.status_code == 200
    verify_data = verify_res.json()
    assert verify_data["success"] is True
    assert verify_data["report"]["status"] == "VERIFIED"


def test_get_hotspots_scenario():
    response = client.get("/api/v2/hotspots/scenario?id=jamnagar_refinery&live_osm=0")
    assert response.status_code == 200
    geojson = response.json()
    assert geojson.get("type") == "FeatureCollection"
    assert "features" in geojson
    assert len(geojson["features"]) > 0

    # Verify GeoJSON properties structure remained intact
    feat = geojson["features"][0]
    assert "properties" in feat
    props = feat["properties"]
    assert "firms" in props
    assert "osm" in props
    assert "persistence" in props
    assert "landcover" in props
    assert "classification" in props


def test_get_hotspots_live_missing_key():
    response = client.get("/api/v2/hotspots/live")
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
