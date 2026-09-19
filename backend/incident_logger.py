"""
Append-only incident audit log for SIH26162.
Every state transition and alert dispatch writes a row.
File: data/incident_logs.json
"""
import os
import json
from datetime import datetime, timezone

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
LOG_FILE = os.path.join(LOG_DIR, "incident_logs.json")


def _load():
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save(logs):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    tmp = LOG_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2)
    os.replace(tmp, LOG_FILE)


def log_transition(record: dict) -> dict:
    entry = {
        "incident_id": record["incident_id"],
        "old_status": record["old_status"],
        "new_status": record["new_status"],
        "changed_by": record["changed_by"],
        "note": record.get("note", ""),
        "changed_at": datetime.now(timezone.utc).isoformat(),
    }
    logs = _load()
    logs.append(entry)
    _save(logs)
    return entry


def get_logs(incident_id: str) -> list:
    return [l for l in _load() if l["incident_id"] == incident_id]


def get_all_logs() -> list:
    return _load()
