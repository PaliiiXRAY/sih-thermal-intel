# Government Command & Responder — Test Checklist
# SIH26162: NTRO → Alert → Responder ACK → Log visible in Government view

## Prerequisites
- [ ] Backend running: `python app.py` on port 5002
- [ ] No data directory conflicts (fresh start recommended)

---

## 1. Backend API Contract Validation

### 1.1 GET /api/incidents
- [ ] Returns array of all incidents with current status
- [ ] Status overrides from previous sessions are applied
- [ ] Response shape matches fixture: `{ incidents: Incident[] }`

### 1.2 GET /api/incidents/:id
- [ ] Returns single incident object
- [ ] Returns 404 for non-existent ID
- [ ] Status reflects latest override

### 1.3 PATCH /api/incidents/:id/status
- [ ] **Valid transition (NEW → INVESTIGATING):** Returns 200 with `{ success: true }`
- [ ] **Invalid transition (DISPATCHED → RESOLVED):** Returns 409 with `{ error: "...", allowed_transitions: [...] }`
- [ ] **Status log updated:** GET /api/incidents/:id/status-log shows new entry
- [ ] **ground_note preserved:** Note appears in status log entry

### 1.4 POST /api/incidents/:id/alert
- [ ] **Success:** Returns `{ success: true, alert_id: "...", alert_type: "SIMULATED_DISPATCH" }`
- [ ] **Response includes:** `note: "Alert is a training simulation..."`
- [ ] **Invalid trigger status (from RESOLVED):** Returns 409
- [ ] **Status set to DISPATCHED:** Subsequent GET shows status as DISPATCHED
- [ ] **Status log updated:** Alert entry appears in log

### 1.5 GET /api/incidents/:id/responders
- [ ] Returns `{ responders: Responder[] }` for known incidents
- [ ] Returns empty array for incidents with no mock data
- [ ] Responder objects include: id, name, unit, type, distance_km, eta_mins, status

### 1.6 GET /api/incidents/:id/status-log
- [ ] Returns `{ log: StatusLogEntry[] }` in chronological order
- [ ] Each entry has: status, timestamp, note, actor

### 1.7 GET /api/export/:id/pdf
- [ ] Returns `{ success: true, filename: "...", pdf_url: "..." }`
- [ ] Filename includes incident ID and date

---

## 2. Government Command Portal

### 2.1 Master-Detail Layout
- [ ] Left panel shows incident list (master)
- [ ] Right panel shows selected incident dossier (detail)
- [ ] Clicking an incident in the left panel updates the right panel
- [ ] Active incident is highlighted in the list

### 2.2 Stat Cards
- [ ] Active Incidents count matches API
- [ ] Critical count (risk_score >= 70) is correct
- [ ] Dispatched count (DISPATCHED/EN ROUTE/ARRIVED) is correct
- [ ] Resolved count (RESOLVED/CONTAINED) is correct

### 2.3 Incident Dossier (Right Panel)
- [ ] Shows: title, location_name, status badge, risk_label
- [ ] Shows: FRP, confidence, classification
- [ ] Shows: coordinates
- [ ] Shows: AI Confidence Breakdown (dossier block)
- [ ] Shows: Wind Corridor (dossier block)
- [ ] Shows: Classification Rationale (dossier block)
- [ ] Shows: Assets at Risk (dossier block)
- [ ] Shows: Assigned Authority details
- [ ] Shows: Status Timeline (if log exists)

### 2.4 Generate Alert Flow
- [ ] Click "Generate Alert" opens Alert Preview modal
- [ ] Modal shows "SIMULATED DISPATCH" banner prominently
- [ ] Banner text: "This is a training/simulation alert. It will NOT reach any real government system."
- [ ] Modal shows: incident ID, title, location, authority, ETA
- [ ] Modal shows: Nearest Responders list (from API)
- [ ] "Cancel" button closes modal
- [ ] "Confirm Simulated Alert" button sends POST /api/incidents/:id/alert
- [ ] On success: alert result banner shows with ticket ID
- [ ] On 409: error message displayed
- [ ] On network error: error message displayed
- [ ] After alert: incident status updates to DISPATCHED
- [ ] After alert: status log shows new DISPATCHED entry

### 2.5 Acknowledge Button
- [ ] Sends PATCH /api/incidents/:id/status with status "INVESTIGATING"
- [ ] On success: incident list and detail refresh
- [ ] On 409: error alert shown
- [ ] On 403: permission error shown
- [ ] On network error: error message shown

### 2.6 Export PDF
- [ ] Click "Export PDF" calls GET /api/export/:id/pdf
- [ ] On success: opens PDF URL in new tab (or shows filename)
- [ ] On error: error alert shown

### 2.7 Polling
- [ ] Incident list refreshes every 5 seconds
- [ ] Selected incident detail refreshes on poll
- [ ] Status changes from Responder appear in Government view after poll

---

## 3. Responder Operations Portal

### 3.1 Incident Selection
- [ ] Dropdown shows all incidents from API
- [ ] Selecting an incident loads its details
- [ ] Default auto-selects first incident

### 3.2 Tactical Card
- [ ] Shows: mission title, location_name
- [ ] Shows: classification badge, severity badge
- [ ] Shows: GPS coordinates, FRP, hazard rating, wind
- [ ] Shows: assigned authority with ETA

### 3.3 State Machine Visual Pipeline
- [ ] Shows 6 steps: Dispatched → Acknowledged → En Route → Arrived → Contained → Resolved
- [ ] Current state highlighted (orange, "ACTIVE NOW")
- [ ] Past states marked (green, "✓ COMPLETED")
- [ ] Future states dimmed (gray, "PENDING")

### 3.4 State Transitions
- [ ] **DISPATCHED → ACKNOWLEDGED:** Click button → success
- [ ] **ACKNOWLEDGED → EN ROUTE:** Click button → success
- [ ] **EN ROUTE → ARRIVED:** Click button → success
- [ ] **ARRIVED → CONTAINED:** Click button → success
- [ ] **CONTAINED → RESOLVED:** Click button → success
- [ ] **Invalid (DISPATCHED → RESOLVED):** Error message, button disabled/hidden
- [ ] **409 response:** Error message displayed: "Invalid transition..."
- [ ] **403 response:** "Forbidden: You are not assigned..."
- [ ] **Network error:** Error message with retry option

### 3.5 Ground Verification Note
- [ ] Textarea visible below state machine
- [ ] Note is sent with status update (PATCH body: `ground_note`)
- [ ] Note appears in status log history
- [ ] Note is cleared after successful transition

### 3.6 Status History
- [ ] Shows chronological log of transitions
- [ ] Each entry: status badge, timestamp, note (if any)
- [ ] Updates after each successful transition

### 3.7 Mission Complete State
- [ ] When RESOLVED: shows "Mission Complete" card
- [ ] No further transition buttons shown

---

## 4. Cross-Portal State Sync

### 4.1 Responder → Government
- [ ] Responder changes status (e.g., EN ROUTE → ARRIVED)
- [ ] Government view shows updated status after poll (≤5 seconds)
- [ ] Government status timeline shows new entry

### 4.2 Government Alert → Responder
- [ ] Government sends alert (status → DISPATCHED)
- [ ] Responder dropdown shows updated status
- [ ] Responder state machine shows DISPATCHED as current state

### 4.3 Multiple Status Changes
- [ ] Responder completes full flow: DISPATCHED → ACKNOWLEDGED → EN ROUTE → ARRIVED → CONTAINED → RESOLVED
- [ ] Government view reflects each transition
- [ ] Status log contains all 5 transition entries

---

## 5. Error Handling

### 5.1 HTTP 403 (Forbidden)
- [ ] Attempting status change on unassigned incident returns 403
- [ ] UI shows clear "not assigned" message

### 5.2 HTTP 409 (Invalid Transition)
- [ ] Attempting impossible state jump returns 409
- [ ] Response includes `allowed_transitions` array
- [ ] UI shows which transitions are valid

### 5.3 Network Failure
- [ ] Backend down: UI shows "Network error" with retry
- [ ] Polling continues (doesn't crash on failure)
- [ ] Retry buttons work after backend recovers

### 5.4 404 Not Found
- [ ] Invalid incident ID returns 404
- [ ] UI handles gracefully (no crash)

---

## 6. Constraint Compliance

### 6.1 No Autonomous AI Dispatch
- [ ] Alert modal banner: "SIMULATED DISPATCH"
- [ ] Alert response includes: "This is NOT a real government alert"
- [ ] No UI element implies AI is dispatching units
- [ ] All dispatch actions require explicit user confirmation

### 6.2 No Real Government System Implication
- [ ] Alert response `note`: "Alert is a training simulation..."
- [ ] Alert response `alert_type`: "SIMULATED_DISPATCH"
- [ ] No UI text suggests alerts reach real systems

---

## 7. End-to-End Flow (NTRO → Alert → Responder → Government)

### Scenario: Full Incident Lifecycle
1. [ ] **NTRO detects incident** (pre-existing: INC-2026-0044, status: NEW)
2. [ ] **Government views incident** in Command Center
3. [ ] **Government clicks "Generate Alert"**
4. [ ] **Alert Preview modal** shows with SIMULATED DISPATCH banner
5. [ ] **Government confirms alert** → status changes to DISPATCHED
6. [ ] **Government status log** shows: NEW → DISPATCHED (alert entry)
7. [ ] **Responder selects incident** → sees DISPATCHED status
8. [ ] **Responder clicks "ACKNOWLEDGE"** → status changes to ACKNOWLEDGED
9. [ ] **Government view** (after poll) shows ACKNOWLEDGED status
10. [ ] **Government status log** shows: DISPATCHED → ACKNOWLEDGED
11. [ ] **Responder clicks "EN ROUTE"** → status changes to EN ROUTE
12. [ ] **Responder adds ground note** → "Wind shifting NE, 15 km/h"
13. [ ] **Government status log** shows: ACKNOWLEDGED → EN ROUTE with note
14. [ ] **Responder clicks "ARRIVED"** → status changes to ARRIVED
15. [ ] **Responder clicks "CONTAINED"** → status changes to CONTAINED
16. [ ] **Responder clicks "RESOLVED"** → status changes to RESOLVED
17. [ ] **Responder** shows "Mission Complete" card
18. [ ] **Government** shows RESOLVED in list and stat cards
19. [ ] **Government status log** shows full 6-step lifecycle
20. [ ] **PDF export** generates dossier with all status transitions

---

## 8. Fixture Validation

- [ ] `static/fixtures/api_responses.json` contains all response shapes
- [ ] `alert_response.success_200` matches actual API response
- [ ] `status_response.success_200` matches actual API response
- [ ] `transition_table` matches backend VALID_TRANSITIONS dict
- [ ] `responders_nearby.success_200` matches actual API response
- [ ] `status_log.success_200` matches actual API response

---

## 9. File Ownership Compliance

| File | Owner | Status |
|------|-------|--------|
| `pages/Government.jsx` | Adil | ✅ Created |
| `components/government/GovernmentCommand.jsx` | Adil | ✅ Created |
| `pages/Responder.jsx` | Adil | ✅ Created |
| `components/responder/ResponderOperations.jsx` | Adil | ✅ Created |
| `static/fixtures/api_responses.json` | Adil | ✅ Created |
| `tests/test_gov_responder_checklist.md` | Adil | ✅ This file |
| `app.py` (API endpoints) | Aditya/Faizaan | ✅ Updated |
| `backend/store.py` (status log) | Aditya/Faizaan | ✅ Updated |
| `components/ntro/*` | Pallabi | Not modified |
| `services/*`, `hooks/*`, `context/*` | Priyanshu | Not modified |

---

## 10. Shared Props Contract (Adil ↔ Pallabi)

The following dossier blocks are shared between Government and NTRO views:
- `DossierConfidence({ confidence, breakdown })`
- `DossierAssets({ assets })`
- `DossierWindCorridor({ wind })`
- `DossierExplanation({ explanation })`

**Props are stable.** Any changes to these props must be communicated to both Adil and Pallabi.

---

**Sign-off:**
- [ ] All 10 sections pass
- [ ] No 409 errors on valid transitions
- [ ] No autonomous AI dispatch language anywhere
- [ ] Cross-portal sync works within 5 seconds
