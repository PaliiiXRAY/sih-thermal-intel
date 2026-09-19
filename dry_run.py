import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.session import SessionLocal, engine
from backend.app.db.base import Base
from seed_demo import seed_scenario, CURATED_SCENARIOS

client = TestClient(app)

def run_dry_run():
    # 1. Start required services (Using TestClient on existing DB)
    db = SessionLocal()
    
    # 2. Seed one scenario
    scenario = CURATED_SCENARIOS["clandestine_thermal_anomaly"]
    inc = seed_scenario(db, scenario)
    incident_id = inc.id
    print(f"Seeded incident: {incident_id}")

    # Admin Login to get token
    login_resp = client.post("/auth/login", json={"email": "admin@firesense.org", "password": "password123"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Retrieve incident
    resp = client.get(f"/api/incidents/{incident_id}", headers=headers)
    assert resp.status_code == 200
    print("Retrieve incident: OK")

    # 4. Classify
    resp = client.post(f"/api/incidents/{incident_id}/classify", headers=headers)
    assert resp.status_code == 200
    print("Classify: OK")

    # 5. Get context
    resp = client.get(f"/api/incidents/{incident_id}/context", headers=headers)
    assert resp.status_code == 200
    print("Context: OK")

    # 6. Get risk
    resp = client.get(f"/api/incidents/{incident_id}/risk", headers=headers)
    assert resp.status_code == 200
    print("Risk: OK")

    # 7. Dispatch simulated alert
    resp = client.post(f"/api/incidents/{incident_id}/alert", headers=headers)
    assert resp.status_code == 200
    print("Alert: OK")

    # 8-12. Status Transitions
    transitions = ["ACKNOWLEDGED", "EN_ROUTE", "ARRIVED", "CONTAINED", "RESOLVED"]
    for status in transitions:
        resp = client.patch(f"/api/incidents/{incident_id}/status", json={"status": status}, headers=headers)
        assert resp.status_code == 200
        print(f"Status -> {status}: OK")

    # 13. Verify audit trail
    resp = client.get(f"/api/incidents/{incident_id}/timeline", headers=headers)
    if resp.status_code == 404:
        # Some versions use /logs
        resp = client.get(f"/api/incidents/{incident_id}/logs", headers=headers)
    assert resp.status_code == 200
    logs = resp.json()["logs"]
    assert len(logs) >= len(transitions) + 2
    print("Audit trail verified: OK")
    print("DRY_RUN_SUCCESS")

if __name__ == "__main__":
    run_dry_run()
