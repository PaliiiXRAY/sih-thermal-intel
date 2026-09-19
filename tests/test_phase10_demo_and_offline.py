"""
Phase 10 Demo Scenarios & Offline Mode Verification Tests.
Verifies curated scenarios, provenance metadata, and end-to-end lifecycle progression
on the same incident ID without breaking frozen schema.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.main import app
from backend.app.core.config import DATABASE_URL
from backend.app.core.security import create_access_token
from backend.app.models.incident import Incident
from backend.app.models.user import User
from seed_demo import CURATED_SCENARIOS, seed_all_scenarios, seed_scenario

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
def auth_tokens(db_session):
    tokens = {}
    for role in ["analyst", "authority", "responder", "admin"]:
        user = db_session.query(User).filter(User.role == role).first()
        assert user is not None, f"Demo user for {role} must exist"
        tokens[role] = create_access_token({"sub": user.id, "email": user.email, "role": user.role})
    return tokens


def test_curated_scenarios_seeded_and_provenance(db_session: Session):
    """Verify all 5 curated demo scenarios have proper provenance metadata."""
    seed_all_scenarios(db_session)

    for key, sc in CURATED_SCENARIOS.items():
        inc = db_session.query(Incident).filter(Incident.id == sc["incident_id"]).first()
        assert inc is not None, f"Scenario {sc['title']} must exist in DB"
        assert inc.classification == sc["classification"]
        assert inc.latitude == sc["latitude"]
        assert inc.longitude == sc["longitude"]
        assert inc.explanation is not None
        assert inc.explanation.get("data_source") == "CURATED_DEMO"
        assert inc.explanation.get("scenario_id") == sc["scenario_id"]


def test_full_scenario_lifecycle_single_incident_id(db_session: Session, auth_tokens):
    """
    Test complete lifecycle on a curated scenario using one consistent incident ID:
    DETECTED -> CLASSIFIED -> ASSESSED -> ALERTED -> ACKNOWLEDGED -> EN_ROUTE -> ARRIVED -> CONTAINED -> RESOLVED
    """
    # 1. Reset scenario to DETECTED state
    sc = CURATED_SCENARIOS["clandestine_thermal_anomaly"]
    inc_id = sc["incident_id"]
    inc = seed_scenario(db_session, sc)
    assert inc.id == inc_id
    assert inc.status == "DETECTED"

    analyst_header = {"Authorization": f"Bearer {auth_tokens['analyst']}"}
    authority_header = {"Authorization": f"Bearer {auth_tokens['authority']}"}
    responder_header = {"Authorization": f"Bearer {auth_tokens['responder']}"}

    # 2. Classify: DETECTED -> CLASSIFIED
    classify_resp = client.post(f"/api/incidents/{inc_id}/classify", headers=analyst_header)
    assert classify_resp.status_code == 200
    assert classify_resp.json()["status"] == "CLASSIFIED"
    assert classify_resp.json()["id"] == inc_id

    # 3. PostGIS Context Enrichment
    ctx_resp = client.get(f"/api/incidents/{inc_id}/context", headers=analyst_header)
    assert ctx_resp.status_code == 200
    ctx_data = ctx_resp.json()
    assert ctx_data["incident_id"] == inc_id
    assert "nearest_assets" in ctx_data

    # 4. Transparent Risk Evaluation
    risk_resp = client.get(f"/api/incidents/{inc_id}/risk", headers=analyst_header)
    assert risk_resp.status_code == 200
    risk_data = risk_resp.json()
    assert 0.0 <= risk_data["risk_score"] <= 100.0
    assert "factors" in risk_data
    assert "reasons" in risk_data

    # 5. Transition to ASSESSED
    status_resp = client.patch(
        f"/api/incidents/{inc_id}/status",
        json={"status": "ASSESSED", "note": "Analyst risk assessment completed"},
        headers=authority_header,
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "ASSESSED"

    # 6. Simulated Priority Alert Generation
    alert_resp = client.post(f"/api/incidents/{inc_id}/alert", headers=authority_header)
    assert alert_resp.status_code == 200
    alert_data = alert_resp.json()
    assert alert_data["incident_id"] == inc_id
    assert alert_data["is_simulated"] is True

    # 7. Transition to ALERTED
    status_resp = client.patch(
        f"/api/incidents/{inc_id}/status",
        json={"status": "ALERTED", "note": "Simulated authority alert dispatched"},
        headers=authority_header,
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "ALERTED"

    # 8. Responder Acknowledges
    status_resp = client.patch(
        f"/api/incidents/{inc_id}/status",
        json={"status": "ACKNOWLEDGED", "note": "Tasking received and acknowledged by unit"},
        headers=responder_header,
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "ACKNOWLEDGED"

    # 9. Responder En Route
    status_resp = client.patch(
        f"/api/incidents/{inc_id}/status",
        json={"status": "EN_ROUTE", "note": "Unit rolling out to site"},
        headers=responder_header,
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "EN_ROUTE"

    # 10. Responder Arrived
    status_resp = client.patch(
        f"/api/incidents/{inc_id}/status",
        json={"status": "ARRIVED", "note": "Unit on site, setting up defensive perimeter"},
        headers=responder_header,
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "ARRIVED"

    # 11. Incident Contained
    status_resp = client.patch(
        f"/api/incidents/{inc_id}/status",
        json={"status": "CONTAINED", "note": "Thermal spread arrested"},
        headers=responder_header,
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "CONTAINED"

    # 12. Incident Resolved
    status_resp = client.patch(
        f"/api/incidents/{inc_id}/status",
        json={"status": "RESOLVED", "note": "Thermal signature neutralized, area declared safe"},
        headers=responder_header,
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "RESOLVED"

    # 13. Audit Timeline Verification
    timeline_resp = client.get(f"/api/incidents/{inc_id}/timeline", headers=analyst_header)
    assert timeline_resp.status_code == 200
    timeline_data = timeline_resp.json()
    assert timeline_data["incident_id"] == inc_id
    assert timeline_data["current_status"] == "RESOLVED"
    actions = [evt["action"] for evt in timeline_data["timeline"]]
    assert "CLASSIFY" in actions
    assert "ALERT_DISPATCH" in actions
    assert "STATUS_CHANGE" in actions
