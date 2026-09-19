"""
Validated Incident State Machine for SIH26162.
Enforces legal transitions. Every call returns a transition record for logging.
"""

VALID_TRANSITIONS = {
    "DETECTED":     ["CLASSIFIED"],
    "CLASSIFIED":   ["ASSESSED"],
    "ASSESSED":     ["ALERTED"],
    "ALERTED":      ["ACKNOWLEDGED"],
    "ACKNOWLEDGED": ["RESOLVED", "EN_ROUTE"],
    "RESOLVED":     [],
    "EN_ROUTE":     ["ARRIVED"],
    "ARRIVED":      ["CONTAINED"],
    "CONTAINED":    ["RESOLVED"],
}


def can_transition(current: str, next_status: str) -> bool:
    return next_status in VALID_TRANSITIONS.get(current, [])


def validate_and_transition(incident_id: str, current: str, new_status: str,
                            changed_by: str, note: str = "") -> dict:
    if not can_transition(current, new_status):
        raise ValueError(
            f"Invalid transition: {incident_id} cannot go from {current} to {new_status}. "
            f"Allowed: {VALID_TRANSITIONS.get(current, [])}"
        )
    return {
        "incident_id": incident_id,
        "old_status": current,
        "new_status": new_status,
        "changed_by": changed_by,
        "note": note,
    }
