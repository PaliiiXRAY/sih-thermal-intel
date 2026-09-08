"""
Lightweight Server-Side Persistence (SIH26162)
Survives warm-instance restarts and keeps data out of the browser:
incident state transitions and citizen reports are stored as JSON on disk.
On Vercel serverless the writable path is /tmp (per-instance, warm-reuse);
locally it is ./data (fully persistent). Production would swap this module
for PostGIS / a managed DB behind the same API contract.
"""
import os
import json
import tempfile

STORAGE_DIR = os.environ.get("AEROTHERMAL_DATA_DIR") or (
    tempfile.gettempdir() if os.environ.get("VERCEL") else
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
)

INCIDENT_STATE_FILE = os.path.join(STORAGE_DIR, "incident_state.json")
REPORTS_FILE = os.path.join(STORAGE_DIR, "citizen_reports.json")


def _load(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save(path, data):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)
        return True
    except Exception:
        return False


# ---- Incident state (status transitions survive restarts) ----

def load_incident_overrides():
    return _load(INCIDENT_STATE_FILE, {})


def save_incident_status(incident_id, status):
    state = _load(INCIDENT_STATE_FILE, {})
    state[incident_id] = {"status": status}
    return _save(INCIDENT_STATE_FILE, state)


# ---- Citizen reports (server-side, cross-portal) ----

def get_reports():
    return _load(REPORTS_FILE, [])


def add_report(report):
    reports = get_reports()
    reports.insert(0, report)
    return _save(REPORTS_FILE, reports[:100])


def verify_report(report_id):
    reports = get_reports()
    for r in reports:
        if r.get("id") == report_id:
            r["status"] = "VERIFIED"
            ok = _save(REPORTS_FILE, reports)
            return (ok, r)
    return (False, None)
