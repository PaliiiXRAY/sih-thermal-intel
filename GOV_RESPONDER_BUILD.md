# Government Command & Responder — Build Summary

## What Was Built

### 1. Backend (app.py)
**New API Endpoints:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/incidents/:id/status` | PATCH | Update status with transition validation (409 on invalid) |
| `/api/incidents/:id/alert` | POST | Send simulated dispatch alert |
| `/api/incidents/:id/responders` | GET | List nearby responder units |
| `/api/incidents/:id/status-log` | GET | Chronological status change history |
| `/api/export/:id/pdf` | GET | Generate PDF export URL |

**Transition Validation:**
- Server validates every status change against `VALID_TRANSITIONS` dict
- Returns HTTP 409 with `allowed_transitions` array on invalid moves
- Returns HTTP 403 on permission errors
- Status log is persisted via `store.append_status_log()`

### 2. Government Command (`pages/Government.jsx` + `components/government/GovernmentCommand.jsx`)
**Master-Detail Layout:**
- Left panel: Active incidents list with status badges and risk scores
- Right panel: Selected incident dossier with all intelligence blocks

**Actions:**
- **Generate Alert**: Opens preview modal with "SIMULATED DISPATCH" banner
- **Acknowledge**: PATCH to INVESTIGATING status
- **Export PDF**: GET /api/export/:id/pdf
- **Track Status**: Status timeline from status-log API

**Alert Flow UI:**
- Modal clearly labeled "SIMULATED DISPATCH"
- Banner: "This is a training/simulation alert. It will NOT reach any real government system."
- Shows nearest responders from API
- Confirmation step before sending

**Shared Dossier Blocks (props contract with Pallabi):**
- `DossierConfidence({ confidence, breakdown })`
- `DossierAssets({ assets })`
- `DossierWindCorridor({ wind })`
- `DossierExplanation({ explanation })`

### 3. Responder Operations (`pages/Responder.jsx` + `components/responder/ResponderOperations.jsx`)
**State Machine:**
```
DISPATCHED → ACKNOWLEDGED → EN ROUTE → ARRIVED → CONTAINED → RESOLVED
```

**Buttons:**
- Single prominent next-action button (not 5 equal buttons)
- Disabled/hidden when transition is invalid
- Shows "Mission Complete" when RESOLVED

**Ground Verification Notes:**
- Textarea below state machine
- Sent with PATCH body: `{ ground_note: "..." }`
- Appears in status log history

**Error Handling:**
- 403: "Forbidden: You are not assigned to this incident"
- 409: "Invalid transition: X → Y. Allowed: [A, B]"
- Network: "Network error: Failed to fetch"

### 4. Store (backend/store.py)
**New Functions:**
- `get_status_log(incident_id)` — Returns chronological log
- `append_status_log(incident_id, status, note, actor)` — Adds entry

### 5. Fixtures (`static/fixtures/api_responses.json`)
Complete response shapes for:
- Alert response (success + 409 + 404)
- Status response (success + 409 + 403 + 404)
- Incident list response
- Nearby responders response
- PDF export response
- Status log response
- Transition table

### 6. Test Checklist (`tests/test_gov_responder_checklist.md`)
**10 Sections:**
1. Backend API Contract Validation
2. Government Command Portal
3. Responder Operations Portal
4. Cross-Portal State Sync
5. Error Handling (403, 409, network)
6. Constraint Compliance (no AI dispatch)
7. End-to-End Flow (NTRO → Alert → Responder → Government)
8. Fixture Validation
9. File Ownership Compliance
10. Shared Props Contract

---

## File Ownership

| File | Owner | Status |
|------|-------|--------|
| `pages/Government.jsx` | Adil | ✅ |
| `pages/Responder.jsx` | Adil | ✅ |
| `components/government/GovernmentCommand.jsx` | Adil | ✅ |
| `components/responder/ResponderOperations.jsx` | Adil | ✅ |
| `static/fixtures/api_responses.json` | Adil | ✅ |
| `tests/test_gov_responder_checklist.md` | Adil | ✅ |
| `app.py` (API endpoints) | Aditya/Faizaan | ✅ Updated |
| `backend/store.py` (status log) | Aditya/Faizaan | ✅ Updated |
| `static/portal-modules.js` (vanilla JS) | Adil | ✅ Updated |

---

## Cross-Portal State Sync

**Mechanism:** Polling every 5 seconds
- Government view polls `/api/incidents` and refreshes list + selected detail
- Responder view polls `/api/incidents` and refreshes dropdown + current incident
- Status changes made by either portal appear in the other after next poll

---

## Constraint Compliance

✅ **No autonomous AI dispatch language**
- Alert modal: "SIMULATED DISPATCH"
- Alert response: "This is NOT a real government alert"
- All dispatch actions require explicit user confirmation

✅ **No real government system implication**
- Alert response: "Alert is a training simulation and does not reach any live government system"
- Alert type: "SIMULATED_DISPATCH"

---

## How to Run

```bash
# Start backend
cd sih-thermal-intel
python app.py

# Access portals
# Government Command: http://localhost:5002/app?portal=command
# Responder Operations: http://localhost:5002/app?portal=responder
```

---

## API Examples

```bash
# Get all incidents
curl http://localhost:5002/api/incidents

# Get single incident
curl http://localhost:5002/api/incidents/INC-2026-0044

# Update status (valid transition)
curl -X PATCH http://localhost:5002/api/incidents/INC-2026-0044/status \
  -H "Content-Type: application/json" \
  -d '{"status": "ACKNOWLEDGED", "ground_note": "Unit acknowledged"}'

# Update status (invalid transition → 409)
curl -X PATCH http://localhost:5002/api/incidents/INC-2026-0044/status \
  -H "Content-Type: application/json" \
  -d '{"status": "RESOLVED"}'

# Send simulated alert
curl -X POST http://localhost:5002/api/incidents/INC-2026-0044/alert \
  -H "Content-Type: application/json" \
  -d '{"alert_type": "SIMULATED_DISPATCH"}'

# Get nearby responders
curl http://localhost:5002/api/incidents/INC-2026-0042/responders

# Get status log
curl http://localhost:5002/api/incidents/INC-2026-0044/status-log

# Export PDF
curl http://localhost:5002/api/export/INC-2026-0044/pdf
```
