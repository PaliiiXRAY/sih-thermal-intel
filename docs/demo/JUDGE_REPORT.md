# FireSense -- Operational Backend Layer
## SIH26162 | NTRO | Satellite-to-Ground Disaster Response

---

## What We Built

FireSense bridges the gap between raw NASA satellite thermal data and actionable emergency response. Satellites detect heat anomalies, but cannot distinguish a safe refinery flare from a catastrophic wildfire. Our system classifies, scores, alerts, and tracks every incident through its full lifecycle.

**This layer adds:** Validated state machine, structured alert dispatch, audit logging, data validation, persistence scoring, and 5 reproducible demo scenarios.

---

## The Problem

NASA FIRMS satellites detect thousands of thermal anomalies daily across India. The challenge: **raw thermal pixels cannot tell whether a heat spike is:**
- A scheduled gas flare at a refinery (safe, routine)
- An uncontrolled forest fire (emergency)
- Agricultural stubble burning (air quality hazard)
- An unregistered clandestine operation (national security concern)

**FireSense classifies, scores, and routes emergency alerts automatically.**

---

## What We Delivered

| Component | What It Does | Files |
|-----------|-------------|-------|
| **State Machine** | Enforces legal incident transitions: DETECTED → CLASSIFIED → ASSESSED → ALERTED → ACKNOWLEDGED → RESOLVED (with responder sub-states) | `backend/state_machine.py` |
| **Alert Service** | Generates structured dispatch payloads labeled "SIMULATED DISPATCH" with incident ID, location, classification, severity, risk reasons, nearest assets, recommended responder | `backend/alerts.py` |
| **Incident Logger** | Append-only audit trail: every transition and alert writes old_status, new_status, changed_by, note, timestamp | `backend/incident_logger.py` |
| **FIRMS Cache** | Validates and deduplicates satellite records (lat/lon bounds, FRP non-negative, ~11m spatial dedup) | `backend/firms_cache.py` |
| **Persistence Scorer** | Spatial-temporal recurrence scoring (0-100) with pattern labels: TRANSIENT, EPISODIC, RECURRENT, PERMANENT | `backend/persistence_scorer.py` |
| **Demo Scenarios** | 5 versioned, reproducible Indian scenarios with provenance documentation | `data/demo/*.json` |
| **Seed Data** | Facilities, responders, shelters, settlements for demo context | `data/facilities.json` |

---

## Architecture

```
NASA FIRMS VIIRS 375m Satellite Data
         |
    [FIRMS Cache] -- validates & deduplicates
         |
    [OSM Correlator] -- land-use context
         |
    [Persistence Scorer] -- 0-100 recurrence score
         |
    [AI Classifier] -- 5-class thermal source classification
         |
    [State Machine] -- validated transitions only
         |
    [Incident Logger] -- every step recorded
         |
    [Alert Service] -- SIMULATED DISPATCH payloads
         |
    [REST API] -- 6 new endpoints
```

---

## State Machine

```
DETECTED ──> CLASSIFIED ──> ASSESSED ──> ALERTED ──> ACKNOWLEDGED ──> RESOLVED
                                                                    │
                                                              EN_ROUTE
                                                                    │
                                                               ARRIVED
                                                                    │
                                                              CONTAINED ──> RESOLVED
```

- **Invalid transitions rejected** (e.g., DETECTED → RESOLVED raises error)
- **Every transition logged** with who changed it, when, and why
- **Responder workflow** branches from ACKNOWLEDGED

---

## API Endpoints

| Endpoint | Method | What It Does |
|----------|--------|-------------|
| `POST /api/incidents/{id}/alert` | POST | Dispatch alert, auto-transition through states |
| `PATCH /api/incidents/{id}/status` | PATCH | Validate + apply status change with audit log |
| `GET /api/responders/nearby?lat=&lon=` | GET | Nearest emergency responders (Haversine sort) |
| `GET /public/alerts` | GET | Public-facing approved alerts |
| `GET /api/incident/{id}/logs` | GET | Full audit trail for any incident |
| `GET /api/export/{id}/pdf` | GET | Export incident data |

---

## Demo Scenarios (5 Reproducible Indian Events)

| Scenario | Location | Type | Risk |
|----------|----------|------|------|
| **Jamnagar Refinery** | Gujarat | Industrial Gas Flare | SAFE (MONITOR) |
| **Similipal Wildfire** | Odisha | Forest Fire | CRITICAL |
| **Angul Power Plant** | Odisha | Coal Stockyard Fire | HIGH |
| **Sangrur Stubble** | Punjab | Agricultural Burning | HIGH (AIR QUALITY) |
| **Singrauli Anomaly** | MP/UP Border | Unregistered Thermal Source | CRITICAL (NTRO CHECK) |

Each scenario includes:
- Real coordinates with OSM land-use context
- Historical satellite observations (repeated over 60 days)
- Assigned emergency authority with ETA
- Assets at risk (villages, roads, hospitals)
- **Provenance documentation** (curated vs simulated fields)

---

## Persistence Scoring

The system computes a **0-100 persistence score** for every thermal anomaly:

| Score | Pattern | Meaning | Example |
|-------|---------|---------|---------|
| >= 60 | PERMANENT | Stationary industrial infrastructure | Refinery flare stack |
| >= 25 | RECURRENT | Batch process or coal seam fire | Power plant, kiln |
| >= 8 | EPISODIC | Multi-day fire event | Spreading wildfire |
| < 8 | TRANSIENT | Single-pass detection | Sporadic stubble fire |

**Spatial tolerance:** 375m (matching VIIRS sensor resolution)
**Temporal window:** 60 days of satellite passes

---

## Alert Payload (SIMULATED DISPATCH)

```json
{
  "dispatch_id": "DISP-A1B2C3D4",
  "incident_id": "INC-2026-0042",
  "location": {"lat": 21.854, "lon": 86.352},
  "classification": "WILDFIRE",
  "severity": "CRITICAL",
  "risk_reasons": [
    "Fire area grew by +42% over 3 days",
    "Located in dense protected forest",
    "No factories within 12 km"
  ],
  "nearest_assets": [
    {"asset": "Village Kaptipada", "distance_km": 1.4, "risk_tier": "CRITICAL"}
  ],
  "recommended_responder": {
    "name": "Baripada Fire & Emergency Services",
    "eta_mins": 25
  },
  "simulated": true,
  "label": "SIMULATED DISPATCH -- Not connected to real emergency services"
}
```

---

## Test Results

| Suite | Tests | Status |
|-------|-------|--------|
| Pipeline & Classifier (existing) | 27 | ALL PASS |
| State Machine | 9 | ALL PASS |
| Alert Workflow | 4 | ALL PASS |
| FIRMS Cache | 7 | ALL PASS |
| Persistence Scorer | 6 | ALL PASS |
| Failure Drills | 10 | ALL PASS |
| **TOTAL** | **63** | **ALL PASS** |

### Key Test Scenarios Proven

1. **Full alert chain:** DETECTED → CLASSIFIED → ASSESSED → ALERTED → ACKNOWLEDGED with audit log at every step
2. **Invalid transitions rejected:** DETECTED → RESOLVED raises ValueError
3. **Data validation:** Invalid coordinates rejected, negative FRP rejected, duplicates deduped
4. **Failure drills:** Nonexistent incidents return 404, bad records rejected, missing fields handled gracefully

---

## Technical Decisions

| Decision | Why |
|----------|-----|
| Pure Python stdlib (zero new deps) | Deploy anywhere, no pip install needed |
| JSON file persistence | Demo scope; production would use PostGIS |
| Keep http.server (no Flask) | Vercel serverless compatible |
| Haversine for nearby responders | Simple, accurate for demo; PostGIS for production |
| 375m spatial tolerance | Matches VIIRS sensor pixel resolution |
| All alerts labeled "SIMULATED DISPATCH" | Never claims to reach real emergency systems |

---

## What's NOT Included (By Design)

- **No live NASA API calls** in demo mode (uses cached scenarios)
- **No database** (JSON files; production would add PostGIS + Alembic migrations)
- **No authentication** (all endpoints open for demo)
- **No WebSocket** (REST polling implemented; SSE deferred)
- **No real PDF export** (stub returns JSON)

---

## How to Run

```bash
# Start server
python app.py

# Run all tests (63 total)
python tests/run_tests.py
python tests/test_state_machine.py
python tests/test_alert_workflow.py
python tests/test_firms_cache.py
python tests/test_persistence_scorer.py
python tests/test_failure_drill.py

# Validate demo data
python data/seed.py
```

**Live at:** http://localhost:5002
**Dashboard:** http://localhost:5002/app

---

## Code Metrics

| Metric | Value |
|--------|-------|
| New backend modules | 6 |
| New test files | 4 |
| Scenario JSONs | 5 |
| Total tests | 63 (all passing) |
| New API routes | 6 |
| New dependencies | 0 |
| Lines of new code | ~1,200 |

---

## Data Provenance

All demo data is documented with:
- **Curated fields:** Based on real NASA FIRMS VIIRS 375m data patterns
- **Simulated fields:** Risk scores, assigned authorities, assets at risk
- **Reproducible:** Same coordinates produce identical classification results every run
- **Labeled:** Every alert payload explicitly marked "SIMULATED DISPATCH"

---

*FireSense -- Spaceborne Thermal Intelligence & Autonomous Industrial Disaster Response*
*SIH26162 | NTRO | Smart India Hackathon 2026*
