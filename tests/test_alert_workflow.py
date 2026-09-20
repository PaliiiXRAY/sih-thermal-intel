# tests/test_alert_workflow.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.alerts import build_alert, dispatch_alert, get_approved_alerts
from backend.incident_logger import get_logs
from backend.state_machine import validate_and_transition

def test_build_alert_structure():
    incident = {
        "id": "INC-TEST-ALERT",
        "coordinates": {"lat": 21.85, "lon": 86.35},
        "classification": "WILDFIRE",
        "risk_label": "CRITICAL",
    }
    assets = [{"asset": "Village X", "distance_km": 1.4, "risk_tier": "CRITICAL"}]
    responder = {"name": "Fire Station A", "eta_mins": 20}
    alert = build_alert(incident, assets, responder)
    assert alert["incident_id"] == "INC-TEST-ALERT"
    assert alert["simulated"] is True
    assert "SIMULATED DISPATCH" in alert["label"]
    assert alert["classification"] == "WILDFIRE"
    assert len(alert["nearest_assets"]) == 1
    assert alert["recommended_responder"]["name"] == "Fire Station A"

def test_dispatch_alert_writes_log():
    test_id = "INC-DISPATCH-TEST"
    from backend.incident_engine import INCIDENTS
    INCIDENTS[test_id] = {
        "id": test_id,
        "classification": "TEST",
        "risk_label": "TEST",
        "coordinates": {"lat": 0, "lon": 0},
        "status": "NEW",
        "assigned_authority": {"name": "Test Authority", "eta_mins": 10},
    }
    try:
        alert = dispatch_alert(test_id)
        assert alert["simulated"] is True
        assert "SIMULATED DISPATCH" in alert["label"]
        logs = get_logs(test_id)
        assert len(logs) >= 1
        # dispatch_alert walks the legacy chain to DISPATCHED then dispatches.
        assert logs[-1]["new_status"] == "DISPATCHED"
    finally:
        del INCIDENTS[test_id]

def test_get_approved_only():
    alerts = get_approved_alerts()
    assert isinstance(alerts, list)
    for a in alerts:
        assert a.get("simulated") is True

def test_alert_full_workflow():
    """Prove: NEW -> INVESTIGATING -> VERIFIED -> DISPATCHED -> ACKNOWLEDGED with logs."""
    test_id = "INC-FULL-WORKFLOW"
    from backend.incident_engine import INCIDENTS
    INCIDENTS[test_id] = {
        "id": test_id, "classification": "TEST", "risk_label": "TEST",
        "coordinates": {"lat": 0, "lon": 0}, "status": "NEW",
        "assigned_authority": {"name": "Test Authority", "eta_mins": 10},
    }
    try:
        from backend.incident_logger import log_transition
        for old, new in [("NEW","INVESTIGATING"), ("INVESTIGATING","VERIFIED"), ("VERIFIED","DISPATCHED")]:
            rec = validate_and_transition(test_id, old, new, "system", f"auto {new.lower()}")
            log_transition(rec)
            INCIDENTS[test_id]["status"] = new
        alert = dispatch_alert(test_id)
        assert alert["simulated"] is True
        rec = validate_and_transition(test_id, "DISPATCHED", "ACKNOWLEDGED", "resp-1", "OK")
        log_transition(rec)
        INCIDENTS[test_id]["status"] = "ACKNOWLEDGED"
        logs = get_logs(test_id)
        statuses = [l["new_status"] for l in logs]
        assert "INVESTIGATING" in statuses
        assert "VERIFIED" in statuses
        assert "DISPATCHED" in statuses
        assert "ACKNOWLEDGED" in statuses
    finally:
        del INCIDENTS[test_id]

if __name__ == "__main__":
    test_build_alert_structure()
    test_dispatch_alert_writes_log()
    test_get_approved_only()
    test_alert_full_workflow()
    print("All alert_workflow tests passed")
