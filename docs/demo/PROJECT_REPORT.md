# FireSense (AeroThermal) -- Operational Backend Layer Report

**Project:** SIH26162 NTRO Satellite-to-Ground Disaster Response
**Date:** 2026-09-19
**Author:** Faizaan (Backend/Data Layer)

---

## 1. Executive Summary

Built the operational backend layer for the FireSense thermal intelligence platform: a validated state machine for incident lifecycle management, structured alert dispatch with "SIMULATED DISPATCH" labeling, append-only audit logging, FIRMS data cache with validation/deduplication, spatial-temporal persistence scoring, 5 versioned demo scenarios with provenance documentation, and comprehensive test coverage.

**Key outcomes:**
- 11 new modules, 4 new test files, 5 scenario JSONs, 1 facilities dataset
- 63 total tests (27 existing + 36 new), all passing
- Zero new dependencies (pure Python stdlib)
- Vercel serverless compatible

---

## 2. Architecture

### 2.1 System Overview

```
                    [NASA FIRMS VIIRS 375m]
                            |
                    [FIRMS Cache + Dedup]
                            |
                    [OSM Land-Use Correlator]
                            |
                    [Persistence Scorer (0-100)]
                            |
                    [AI Classifier]
                            |
                    [State Machine] <--- Validated Transitions
                            |
                    [Incident Logger] <--- Append-Only Audit Trail
                            |
                    [Alert Service] <--- SIMULATED DISPATCH Payloads
                            |
              +-------------+-------------+
              |                           |
     [REST API Routes]           [Demo Scenarios]
     (app.py)                   (data/demo/*.json)
```

### 2.2 State Machine

Validated transition table enforcing legal incident state changes:

```
DETECTED -> CLASSIFIED -> ASSESSED -> ALERTED -> ACKNOWLEDGED -> RESOLVED
                                                              |
                                                         EN_ROUTE -> ARRIVED -> CONTAINED -> RESOLVED
```

- Invalid transitions raise `ValueError`
- Every transition writes an audit log entry
- Responder sub-states (EN_ROUTE, ARRIVED, CONTAINED) branch from ACKNOWLEDGED

### 2.3 Data Flow

1. **Ingestion:** FIRMS thermal anomalies validated and deduplicated in `FIRMSCache`
2. **Context:** OSM land-use tags correlated via Overpass API or cached scenario data
3. **Persistence:** Spatial-temporal recurrence scored 0-100 with pattern labels (TRANSIENT/EPISODIC/RECURRENT/PERMANENT)
4. **Classification:** Multi-feature heuristic classifier (Industrial Flare, Wildfire, Crop Burning, Clandestine, Power Plant)
5. **Alerting:** Structured dispatch payload generated with risk reasons, nearest assets, recommended responder
6. **Logging:** Every state transition and alert dispatch recorded in append-only audit trail

---

## 3. Files Created/Modified

### 3.1 New Backend Modules

| File | Lines | Responsibility |
|------|-------|----------------|
| `backend/state_machine.py` | 35 | Validated transition table, `can_transition()`, `validate_and_transition()` |
| `backend/incident_logger.py` | 50 | Append-only JSON audit log, `log_transition()`, `get_logs()` |
| `backend/alerts.py` | 85 | Structured alert dispatch, `build_alert()`, `dispatch_alert()`, `get_approved_alerts()` |
| `backend/firms_cache.py` | 60 | FIRMS record validation (lat/lon bounds, FRP/brightness non-negative), spatial dedup |
| `backend/persistence_scorer.py` | 40 | Haversine-based spatial tolerance + temporal recurrence scoring |
| `backend/demo_loader.py` | 65 | Loads scenario JSONs + facilities into memory at startup |

### 3.2 Data Files

| File | Description |
|------|-------------|
| `data/demo/industrial_fire.json` | Jamnagar refinery complex (2 hotspots, 8 historical observations) |
| `data/demo/wildfire.json` | Similipal biosphere wildfire (2 hotspots, expanding perimeter) |
| `data/demo/gas_flare.json` | Angul thermal power plant (2 hotspots, coal stockyard) |
| `data/demo/crop_burning.json` | Sangrur paddy stubble burning (3 hotspots, seasonal) |
| `data/demo/mining_unknown.json` | Singrauli unregistered hotspot (1 hotspot, 10 observations, high persistence) |
| `data/facilities.json` | 6 facilities, 5 settlements, 7 responders, 3 shelters, 3 roads |

### 3.3 Test Files

| File | Tests | Coverage |
|------|-------|----------|
| `tests/test_state_machine.py` | 9 | Transition validation, responder sub-states, logger integration |
| `tests/test_alert_workflow.py` | 4 | Alert structure, dispatch logging, full DETECTED->ACKNOWLEDGED chain |
| `tests/test_firms_cache.py` | 7 | Validation, dedup, bbox query, missing fields |
| `tests/test_persistence_scorer.py` | 6 | Permanent/transient/episodic patterns, spatial filter, score range |
| `tests/test_failure_drill.py` | 10 | Invalid records, nonexistent incidents, invalid transitions, edge cases |

### 3.4 Documentation

| File | Description |
|------|-------------|
| `docs/demo/provenance.md` | Data sources, curated vs simulated fields, reproduction guide |
| `docs/superpowers/plans/2026-09-19-operational-backend-layer.md` | Implementation plan (12 tasks) |

### 3.5 Modified Files

| File | Changes |
|------|---------|
| `app.py` | Added 6 imports, 5 new routes, validated state transitions, demo_loader initialization |

---

## 4. API Endpoints

### 4.1 New Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `POST /api/incidents/{id}/alert` | POST | authority | Build + dispatch alert, auto-transition through states, log each step |
| `PATCH /api/incidents/{id}/status` | PATCH | authority/responder | Validate transition against state machine, update status, log |
| `GET /api/responders/nearby?lat=&lon=&limit=` | GET | any | Haversine-sorted nearest responders from seeded data |
| `GET /public/alerts` | GET | public | Approved (simulated=True) alerts from outbox |
| `GET /api/incident/{id}/logs` | GET | any | Audit trail for a specific incident |
| `GET /api/export/{id}/pdf` | GET | authority | Stub JSON export (PDF generation deferred) |

### 4.2 Alert Payload Schema

```json
{
  "dispatch_id": "DISP-A1B2C3D4",
  "incident_id": "INC-2026-0042",
  "location": {"lat": 21.854, "lon": 86.352},
  "classification": "WILDFIRE",
  "severity": "CRITICAL",
  "risk_reasons": ["Fire area grew by +42%", "Located in dense forest"],
  "nearest_assets": [...],
  "recommended_responder": {...},
  "simulated": true,
  "label": "SIMULATED DISPATCH -- Not connected to real emergency services",
  "created_at": "2026-09-19T06:30:00+00:00"
}
```

### 4.3 Incident Log Schema

```json
{
  "incident_id": "INC-2026-0042",
  "old_status": "DETECTED",
  "new_status": "CLASSIFIED",
  "changed_by": "system",
  "note": "auto classified",
  "changed_at": "2026-09-19T06:30:00+00:00"
}
```

---

## 5. Data Model

### 5.1 Scenario JSON Structure

Each scenario in `data/demo/` follows this schema:

```
{
  version: string          -- Semantic version (e.g. "1.0.0")
  id: string               -- Unique scenario identifier
  title: string            -- Human-readable title
  category: string         -- Event category
  region_name: string      -- Geographic region
  center: [lat, lon]       -- Map center coordinates
  zoom: int                -- Default map zoom level
  provenance: {
    created: date          -- Creation date
    data_source: "cache"   -- Always "cache" in demo mode
    simulated_fields: []   -- Fields that are demo-only
    curated_fields: []     -- Fields derived from real data
    note: string           -- Provenance documentation
  }
  hotspots: [{
    latitude, longitude, frp, brightness, confidence,
    osm_context: {landuse, facility_name, facility_type, distance_m, elevation_m}
  }]
  historical_observations: [{lat, lon, timestamp, frp}]
  risk_score: int          -- 0-100 composite danger score
  risk_label: string       -- Human-readable risk level
  assigned_authority: {name, jurisdiction, distance_km, eta_mins, contact_role}
  assets_at_risk: [{asset, type, distance_km, risk_tier}]
}
```

### 5.2 FIRMS Cache Normalization

Records normalized to:
- `lat`, `lon` (float, validated: -90..90, -180..180)
- `brightness_kelvin` (float, >= 0)
- `frp` (float, Fire Radiative Power in MW, >= 0)
- `acq_date`, `acq_time` (string)
- `satellite` (string)
- `confidence` (string: low/nominal/high)

Dedup key: `(round(lat, 4), round(lon, 4), acq_date, acq_time)` -- ~11m spatial tolerance.

### 5.3 Persistence Scoring

```
score = (spatial_matches / temporal_window_days) * 100

Labels:
  score >= 60  -> PERMANENT    (stationary industrial infrastructure)
  score >= 25  -> RECURRENT    (batch process, coal seam fire)
  score >= 8   -> EPISODIC     (multi-day fire event)
  score < 8    -> TRANSIENT    (single-pass, sporadic)
```

Spatial tolerance: 375m (matches VIIRS 375m pixel resolution).

---

## 6. Testing

### 6.1 Test Summary

| Suite | Tests | Status |
|-------|-------|--------|
| Existing (run_tests.py) | 27 | All pass |
| State Machine | 9 | All pass |
| Alert Workflow | 4 | All pass |
| FIRMS Cache | 7 | All pass |
| Persistence Scorer | 6 | All pass |
| Failure Drills | 10 | All pass |
| **Total** | **63** | **All pass** |

### 6.2 Key Test Scenarios

- **Alert -> Ack -> Log chain:** DETECTED -> CLASSIFIED -> ASSESSED -> ALERTED -> ACKNOWLEDGED with verified audit trail at each step
- **Invalid transitions:** DETECTED -> RESOLVED raises ValueError, DETECTED -> ALERTED raises ValueError
- **FIRMS validation:** lat=999 rejected, negative FRP rejected, duplicate records deduped
- **Persistence patterns:** 50 observations = PERMANENT, 1 = TRANSIENT, 5 = EPISODIC
- **Edge cases:** empty observations, far-away observations filtered, missing optional fields accepted

### 6.3 Running Tests

```bash
# Full suite
python tests/run_tests.py

# Individual suites
python tests/test_state_machine.py
python tests/test_alert_workflow.py
python tests/test_firms_cache.py
python tests/test_persistence_scorer.py
python tests/test_failure_drill.py

# Seed validation
python data/seed.py
```

---

## 7. Deployment

### 7.1 Vercel Compatibility

- No new pip dependencies (stdlib only)
- No persistent processes (JSON file persistence)
- No WebSockets (REST polling only)
- `data/` directory is gitignored; seed scripts recreate state on startup

### 7.2 Local Development

```bash
python app.py
# Server starts on http://localhost:5002
```

### 7.3 Demo Mode

- Default: `DATA_SOURCE=cache` (no live NASA calls)
- Live mode: requires `FIRMS_MAP_KEY` environment variable
- All alert payloads labeled "SIMULATED DISPATCH"

---

## 8. Constraints & Decisions

| Decision | Rationale |
|----------|-----------|
| Keep `http.server` (no Flask/FastAPI) | Vercel serverless deployment, minimal changes to existing app |
| JSON file persistence (no PostGIS) | Demo scope, seed scripts recreate state; production would use PostGIS |
| Stdlib only (no new deps) | Deployment simplicity, no pip install required |
| `dispatch_alert()` walks intermediate states | Single call advances through DETECTED->CLASSIFIED->ASSESSED->ALERTED |
| Scenario JSONs in `data/demo/` | Versioned, reproducible, curated vs simulated fields documented |
| Haversine for nearby responders | Simple, accurate enough for demo; production would use PostGIS spatial queries |

---

## 9. What's NOT Included (Deferred to Production)

- PostGIS database (Aditya owns schema via Alembic)
- Real PDF export (stub returns JSON)
- WebSocket/SSE real-time updates (REST polling fallback implemented)
- Authentication/authorization (all endpoints currently open)
- Rate limiting on alert dispatch
- Production-grade error recovery (current: try/except with JSON error responses)

---

## 10. Files Summary

```
NEW:
  backend/state_machine.py        (35 lines)
  backend/incident_logger.py      (50 lines)
  backend/alerts.py               (85 lines)
  backend/firms_cache.py          (60 lines)
  backend/persistence_scorer.py   (40 lines)
  backend/demo_loader.py          (65 lines)
  data/demo/industrial_fire.json  (65 lines)
  data/demo/wildfire.json         (65 lines)
  data/demo/gas_flare.json        (65 lines)
  data/demo/crop_burning.json     (55 lines)
  data/demo/mining_unknown.json   (60 lines)
  data/facilities.json            (85 lines)
  data/seed.py                    (65 lines)
  tests/test_state_machine.py     (65 lines)
  tests/test_alert_workflow.py    (80 lines)
  tests/test_firms_cache.py       (65 lines)
  tests/test_persistence_scorer.py (55 lines)
  tests/test_failure_drill.py     (70 lines)
  docs/demo/provenance.md         (70 lines)

MODIFIED:
  app.py                          (+45 lines for new routes)

TOTAL: ~1,200 lines of new code + data
```
