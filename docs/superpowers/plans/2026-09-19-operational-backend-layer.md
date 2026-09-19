# Operational Backend Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Build the operational backend layer: validated state machine, structured alert dispatch, incident audit logging, FIRMS cache with dedup, versioned demo scenarios with provenance, seed scripts, persistence scoring, and tests proving the alert->ack->log chain works.

**Architecture:** Extend the existing http.server-based app with new backend modules. State machine validates all transitions. Every transition + alert writes an append-only incident log. Alerts are structured JSON payloads labeled "SIMULATED DISPATCH". Scenarios are versioned JSON files loaded at startup. No new dependencies -- pure Python stdlib.

**Tech Stack:** Python 3.10+, stdlib only (json, os, uuid, datetime, math, http.server). No Flask, no database, no new pip packages.

**Spec:** Design from brainstorming session (2026-09-19)

## Global Constraints

- No new pip dependencies -- stdlib only
- Vercel serverless compatible -- no WebSockets, no persistent processes
- All demo data labeled "SIMULATED DISPATCH" / "curated/simulated"
- Scenarios reproduce identically each run (deterministic)
- Schema changes only via Aditya -- this plan proposes tables, does not create Alembic migrations
- Frontend never calls anything outside the frozen API contract
- Every alert payload includes "simulated": true and "label": "SIMULATED DISPATCH"
- JSON files for persistence (production would use PostGIS)
- data/ directory is gitignored -- seed scripts recreate state on each startup

---

## File Map

| File | Responsibility |
|---|---|
| ackend/state_machine.py | Validated transition table, can_transition(), alidate_and_transition() |
| ackend/incident_logger.py | Append-only incident log writer, log_transition(), get_logs() |
| ackend/alerts.py | Structured alert payload builder, uild_alert(), get_approved_alerts() |
| ackend/firms_cache.py | FIRMS record validation, dedup, spatial query |
| ackend/persistence_scorer.py | Spatial-temporal persistence -> 0-100 score + pattern label |
| ackend/demo_loader.py | Loads scenario JSONs + facilities into memory at startup |
| data/demo/*.json | 5 versioned scenario files |
| data/facilities.json | Seeded facilities, settlements, responders, shelters |
| data/seed.py | CLI script: validates + loads all scenarios |
| 	ests/test_state_machine.py | State machine transition validation tests |
| 	ests/test_alert_workflow.py | Alert -> ack -> log chain test |
| 	ests/test_failure_drill.py | Bad records, missing context, invalid transitions |
| 	ests/test_persistence_scorer.py | Persistence scoring unit tests |
| 	ests/test_firms_cache.py | FIRMS validation + dedup tests |
| docs/demo/provenance.md | Data provenance documentation |
| pp.py | Modified: wire new routes, call demo_loader on startup |

---

### Task 1: State Machine

**Files:**
- Create: ackend/state_machine.py
- Create: 	ests/test_state_machine.py

**Interfaces:**
- Consumes: nothing (foundation module)
- Produces: VALID_TRANSITIONS dict, can_transition(current, next_status) -> bool, alidate_and_transition(incident_id, current, new_status, changed_by, note) -> dict

- [ ] **Step 1: Write the failing tests**

`python
# tests/test_state_machine.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.state_machine import can_transition, validate_and_transition, VALID_TRANSITIONS

def test_valid_forward_transitions():
    assert can_transition("DETECTED", "CLASSIFIED")
    assert can_transition("CLASSIFIED", "ASSESSED")
    assert can_transition("ASSESSED", "ALERTED")
    assert can_transition("ALERTED", "ACKNOWLEDGED")
    assert can_transition("ACKNOWLEDGED", "RESOLVED")

def test_invalid_transitions():
    assert not can_transition("DETECTED", "RESOLVED")
    assert not can_transition("DETECTED", "ALERTED")
    assert not can_transition("RESOLVED", "DETECTED")
    assert not can_transition("ACKNOWLEDGED", "CLASSIFIED")

def test_responder_sub_states():
    assert can_transition("ACKNOWLEDGED", "EN_ROUTE")
    assert can_transition("EN_ROUTE", "ARRIVED")
    assert can_transition("ARRIVED", "CONTAINED")
    assert can_transition("CONTAINED", "RESOLVED")

def test_responder_invalid():
    assert not can_transition("DETECTED", "EN_ROUTE")
    assert not can_transition("EN_ROUTE", "RESOLVED")

def test_validate_and_transition_success():
    result = validate_and_transition("INC-001", "DETECTED", "CLASSIFIED", "system", "Auto-classified")
    assert result["old_status"] == "DETECTED"
    assert result["new_status"] == "CLASSIFIED"
    assert result["changed_by"] == "system"
    assert result["incident_id"] == "INC-001"

def test_validate_and_transition_failure():
    try:
        validate_and_transition("INC-001", "DETECTED", "RESOLVED", "system")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "DETECTED" in str(e) and "RESOLVED" in str(e)

def test_terminal_state():
    assert not can_transition("RESOLVED", "DETECTED")
    assert not can_transition("RESOLVED", "ACKNOWLEDGED")

if __name__ == "__main__":
    test_valid_forward_transitions()
    test_invalid_transitions()
    test_responder_sub_states()
    test_responder_invalid()
    test_validate_and_transition_success()
    test_validate_and_transition_failure()
    test_terminal_state()
    print("All state_machine tests passed")
`

- [ ] **Step 2: Run tests to verify they fail**

Run: python tests/test_state_machine.py
Expected: ModuleNotFoundError: No module named 'backend.state_machine'

- [ ] **Step 3: Implement state_machine.py**

`python
# backend/state_machine.py
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
`

- [ ] **Step 4: Run tests to verify they pass**

Run: python tests/test_state_machine.py
Expected: All state_machine tests passed

- [ ] **Step 5: Commit**

`ash
git add backend/state_machine.py tests/test_state_machine.py
git commit -m "feat: validated state machine with legal transition table"
`

---

### Task 2: Incident Logger

**Files:**
- Create: ackend/incident_logger.py
- Modify: 	ests/test_state_machine.py (add logger integration tests)

**Interfaces:**
- Consumes: alidate_and_transition() from Task 1
- Produces: log_transition(record) -> dict, get_logs(incident_id) -> list, get_all_logs() -> list

- [ ] **Step 1: Write the failing test**

Add to 	ests/test_state_machine.py:

`python
from backend.incident_logger import log_transition, get_logs, get_all_logs

def test_log_writes_and_reads():
    record = validate_and_transition("INC-TEST-001", "DETECTED", "CLASSIFIED", "system", "auto")
    log_transition(record)
    logs = get_logs("INC-TEST-001")
    assert len(logs) >= 1
    assert logs[-1]["new_status"] == "CLASSIFIED"
    assert logs[-1]["incident_id"] == "INC-TEST-001"

def test_log_all():
    all_logs = get_all_logs()
    assert isinstance(all_logs, list)
`

- [ ] **Step 2: Run test to verify it fails**

Run: python tests/test_state_machine.py
Expected: ModuleNotFoundError: No module named 'backend.incident_logger'

- [ ] **Step 3: Implement incident_logger.py**

`python
# backend/incident_logger.py
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
`

- [ ] **Step 4: Run tests to verify they pass**

Run: python tests/test_state_machine.py
Expected: All state_machine tests passed (including new logger tests)

- [ ] **Step 5: Commit**

`ash
git add backend/incident_logger.py tests/test_state_machine.py
git commit -m "feat: append-only incident audit log"
`

---


### Task 3: Alert Service

**Files:**
- Create: ackend/alerts.py
- Create: 	ests/test_alert_workflow.py

**Interfaces:**
- Consumes: validate_and_transition() from Task 1, log_transition() from Task 2, INCIDENTS from incident_engine.py
- Produces: build_alert(incident, nearest_assets, recommended_responder) -> dict, dispatch_alert(incident_id) -> dict, get_approved_alerts() -> list

- [ ] Step 1: Write the failing tests (tests/test_alert_workflow.py)
- [ ] Step 2: Run tests to verify they fail (ModuleNotFoundError)
- [ ] Step 3: Implement backend/alerts.py with build_alert(), dispatch_alert(), get_approved_alerts()
- [ ] Step 4: Run tests to verify they pass
- [ ] Step 5: Commit

Key implementation details:
- build_alert() returns dispatch_id, incident_id, location, classification, severity, risk_reasons, nearest_assets, recommended_responder, simulated=True, label="SIMULATED DISPATCH"
- dispatch_alert() walks the path DETECTED->CLASSIFIED->ASSESSED->ALERTED, writing logs at each step
- get_approved_alerts() filters outbox for simulated=True alerts
- Alert outbox stored in data/alerts_outbox.json

---

### Task 4: FIRMS Cache

**Files:** Create ackend/firms_cache.py, 	ests/test_firms_cache.py

**Interfaces:** FIRMSCache class with add(record) -> bool, query(bbox) -> list, count() -> int

- [ ] Step 1: Write tests for valid record add, invalid lat rejection, negative FRP rejection, dedup, bbox query
- [ ] Step 2: Run tests (ModuleNotFoundError expected)
- [ ] Step 3: Implement FIRMSCache with validation (lat -90..90, lon -180..180, frp>=0, brightness>=0) and dedup on (round(lat,4), round(lon,4), acq_date, acq_time)
- [ ] Step 4: Run tests (all pass)
- [ ] Step 5: Commit

### Task 5: Persistence Scorer

**Files:** Create ackend/persistence_scorer.py, 	ests/test_persistence_scorer.py

**Interfaces:** compute_persistence_score(lat, lon, observations, spatial_tolerance_m=375, temporal_window_days=60) -> dict with score (0-100), pattern_label, spatial_matches, total_observations, recurrence_rate

- [ ] Step 1: Write tests for PERMANENT (score>=60), TRANSIENT (score<8), EPISODIC (8<=score<25), spatial filter, empty obs
- [ ] Step 2: Run tests (ModuleNotFoundError expected)
- [ ] Step 3: Implement with haversine distance check, recurrence_rate = min(1.0, spatial_matches / window_days), score = rate * 100
- [ ] Step 4: Run tests (all pass)
- [ ] Step 5: Commit

---

### Task 6: Scenario JSON Files

**Files:** Create data/demo/ directory with 5 versioned JSON files

- [ ] Step 1: mkdir -p data/demo
- [ ] Step 2: Create data/demo/industrial_fire.json (Jamnagar refinery, 2 hotspots, 5+ historical obs, provenance note)
- [ ] Step 3: Create data/demo/wildfire.json (Similipal forest fire, 2 hotspots, expanding perimeter)
- [ ] Step 4: Create data/demo/gas_flare.json (Angul power plant, 2 hotspots, coal stockyard)
- [ ] Step 5: Create data/demo/crop_burning.json (Sangrur stubble, 3 hotspots, seasonal)
- [ ] Step 6: Create data/demo/mining_unknown.json (Singrauli clandestine, 1 hotspot, high persistence)
- [ ] Step 7: Commit

Each JSON must have: version, id, title, category, region_name, center, zoom, provenance (created, data_source, simulated_fields, curated_fields, note), hotspots (lat, lon, frp, brightness, confidence, osm_context), historical_observations (lat, lon, timestamp, frp), risk_score, risk_label, assigned_authority, assets_at_risk

### Task 7: Facilities & Seed Data

**Files:** Create data/facilities.json, data/seed.py

- [ ] Step 1: Create data/facilities.json with facilities (5-8), settlements (5-10), responders (5-8), shelters (3-5), roads (3-5) -- each with lat/lon
- [ ] Step 2: Create data/seed.py CLI script that loads all scenario JSONs + facilities, validates schema, prints summary
- [ ] Step 3: Test seed script: python data/seed.py should load all scenarios without errors
- [ ] Step 4: Commit

### Task 8: Demo Loader & API Wiring

**Files:** Create ackend/demo_loader.py, modify pp.py

- [ ] Step 1: Create ackend/demo_loader.py with load_all_scenarios() that reads data/demo/*.json into memory
- [ ] Step 2: Modify pp.py to call demo_loader on startup
- [ ] Step 3: Add new routes to app.py:
  - POST /api/incidents/{id}/alert -> dispatch_alert()
  - PATCH /api/incidents/{id}/status -> validate_and_transition() + log_transition()
  - GET /api/responders/nearby?lat=&lon= -> haversine sort from facilities.json
  - GET /public/alerts -> get_approved_alerts()
  - GET /api/export/{id}/pdf -> stub JSON export
- [ ] Step 4: Test all routes manually with curl
- [ ] Step 5: Commit

---

### Task 9: Failure Drill Tests

**Files:** Create 	ests/test_failure_drill.py

- [ ] Step 1: Write test for invalid FIRMS record (lat=999) -> rejected by cache
- [ ] Step 2: Write test for FIRMS record with missing optional fields -> accepted with defaults
- [ ] Step 3: Write test for alert on nonexistent incident -> ValueError
- [ ] Step 4: Write test for invalid status transition (DETECTED -> RESOLVED) -> ValueError
- [ ] Step 5: Write test for missing provenance in scenario JSON -> seed warns but loads
- [ ] Step 6: Run all tests
- [ ] Step 7: Commit

### Task 10: Full Test Suite Run

- [ ] Step 1: Run python tests/run_tests.py (existing 27 assertions still pass)
- [ ] Step 2: Run python tests/test_state_machine.py
- [ ] Step 3: Run python tests/test_alert_workflow.py
- [ ] Step 4: Run python tests/test_firms_cache.py
- [ ] Step 5: Run python tests/test_persistence_scorer.py
- [ ] Step 6: Run python tests/test_failure_drill.py
- [ ] Step 7: Verify all pass, fix any failures

### Task 11: Provenance Documentation

**Files:** Create docs/demo/provenance.md

- [ ] Step 1: Document data sources (NASA FIRMS VIIRS 375m, OSM Overpass API, ESA WorldCover)
- [ ] Step 2: Document which fields are curated vs simulated per scenario
- [ ] Step 3: Document that all alert payloads are labeled SIMULATED DISPATCH
- [ ] Step 4: Document scenario reproduction (identical each run)
- [ ] Step 5: Commit

### Task 12: Requirements & Final Verification

- [ ] Step 1: Verify requirements.txt has no new dependencies (stdlib only)
- [ ] Step 2: Run full test suite one final time
- [ ] Step 3: Verify python app.py starts without errors
- [ ] Step 4: Test POST /api/incidents/INC-2026-0042/alert returns SIMULATED DISPATCH payload
- [ ] Step 5: Test PATCH /api/incidents/INC-2026-0042/status with valid transition
- [ ] Step 6: Test GET /public/alerts returns approved alerts
- [ ] Step 7: Final commit

---

## Execution Order

1. Task 1: State Machine (foundation, no deps)
2. Task 2: Incident Logger (depends on Task 1)
3. Task 3: Alert Service (depends on Tasks 1+2)
4. Task 4: FIRMS Cache (standalone)
5. Task 5: Persistence Scorer (standalone)
6. Task 6: Scenario JSON Files (standalone)
7. Task 7: Facilities & Seed Data (standalone)
8. Task 8: Demo Loader & API Wiring (depends on Tasks 3,6,7)
9. Task 9: Failure Drill Tests (depends on all above)
10. Task 10: Full Test Suite Run (depends on all above)
11. Task 11: Provenance Documentation (standalone)
12. Task 12: Final Verification (depends on all above)

Tasks 4, 5, 6, 7 can run in parallel with Tasks 1-3.
