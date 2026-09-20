"""
Structured Alert Dispatch Service for SIH26162.
Builds SIMULATED DISPATCH payloads and manages the alert outbox.
"""
import os
import json
from datetime import datetime, timezone
from uuid import uuid4

from backend.state_machine import validate_and_transition, can_transition
from backend.incident_logger import log_transition
from backend.incident_engine import INCIDENTS

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
ALERTS_FILE = os.path.join(DATA_DIR, "alerts_outbox.json")


def _load_alerts():
    try:
        with open(ALERTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_alerts(alerts):
    os.makedirs(os.path.dirname(ALERTS_FILE), exist_ok=True)
    tmp = ALERTS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(alerts, f, indent=2)
    os.replace(tmp, ALERTS_FILE)


def build_alert(incident: dict, nearest_assets: list = None, recommended_responder: dict = None) -> dict:
    return {
        "dispatch_id": f"DISP-{uuid4().hex[:8].upper()}",
        "incident_id": incident["id"],
        "location": incident.get("coordinates", {}),
        "classification": incident.get("classification", "UNKNOWN"),
        "severity": incident.get("risk_label", "UNKNOWN"),
        "risk_reasons": incident.get("explain_classification", {}).get("evidence", []),
        "nearest_assets": nearest_assets or [],
        "recommended_responder": recommended_responder or incident.get("assigned_authority", {}),
        "simulated": True,
        "label": "SIMULATED DISPATCH -- Not connected to real emergency services",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def dispatch_alert(incident_id: str) -> dict:
    incident = INCIDENTS.get(incident_id)
    if not incident:
        raise ValueError(f"Incident {incident_id} not found")

    current = incident.get("status", "NEW")
    for old, new in _path_to_dispatch(current):
        rec = validate_and_transition(incident_id, old, new, "system", f"auto {new.lower()}")
        log_transition(rec)
        incident["status"] = new

    alert = build_alert(
        incident,
        nearest_assets=incident.get("assets_at_risk", []),
        recommended_responder=incident.get("assigned_authority"),
    )

    alerts = _load_alerts()
    alerts.append(alert)
    _save_alerts(alerts)
    return alert


def _path_to_dispatch(current: str) -> list:
    # Legacy vocabulary (backend/state_machine.py): an incident becomes
    # alert-dispatchable once it reaches DISPATCHED.
    path = []
    chain = ["NEW", "INVESTIGATING", "VERIFIED", "DISPATCHED"]
    try:
        start = chain.index(current)
    except ValueError:
        return path
    for i in range(start, len(chain) - 1):
        path.append((chain[i], chain[i + 1]))
    return path


def get_approved_alerts() -> list:
    return [a for a in _load_alerts() if a.get("simulated") is True]
