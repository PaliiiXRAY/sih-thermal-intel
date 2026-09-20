# FINAL FIRESENSE RELEASE AUDIT

**STATUS (re-verified 2026-09-20): CODE-LEVEL P0 + P1/P2 REMEDIATION COMPLETE — SECURITY FIX NOT YET DEPLOYED**
The live deployment at `https://sih-thermal-intel.vercel.app` still runs the pre-fix handler and accepts
unauthenticated admin access until redeployed. Treat every section below as evidence-based, not as a
certification of the live site.

## A. Test result
**PASS — measured 2026-09-20**
- `python -m pytest -q`: **192 passed, 0 failed, 5 warnings in ~48s**.
- Full green reached 2026-09-20: the 6 state-machine failures were resolved by aligning the legacy
  tree's tests and `backend/alerts.py` dispatch path to the legacy vocabulary
  (`backend/state_machine.py`), not by reverting the vocabulary or touching user work.
- The earlier "119 passed" figure predates those additions and is stale.

## B. Alembic result
**PASS**
- Migration chain is linear `f0ee81829371` → `a2b3c4d5e6f7` (verified via `git log`).
- `alembic current` / `alembic heads` require a live PostgreSQL; not re-run in this pass.

## C. Schema checkpoint result
**PARTIAL**
- `schema-vertical-slice-stable` tag exists. Whether the runtime schema is "locked" is unverified this pass;
  the ticket states committed migrations resolve to head `a2b3c4d5e6f7`.

## D. API contract result
**PARTIAL**
- The `backend/app/api/` routing layer defines the canonical endpoints and enforces HTTP methods.
- Caveat: the **live deployment does not run FastAPI at all** — `vercel.json` routes everything to
  `api/index.py` (legacy `app.py`, stdlib HTTP). Only the Docker path serves `/docs` and the FastAPI
  contract. Full-contract compliance of the live site is therefore unverified.

## E. Lifecycle result
**PARTIAL**
- FastAPI canonical vocabulary (`backend/app/`): `DETECTED → CLASSIFIED → ASSESSED → ALERTED → ACKNOWLEDGED → EN_ROUTE →
  ARRIVED → CONTAINED → RESOLVED`.
- Legacy handler/state-machine vocabulary (`app.py`, `backend/state_machine.py`): `NEW → INVESTIGATING → VERIFIED → DISPATCHED →
  ACKNOWLEDGED → EN ROUTE → ARRIVED → CONTAINED → RESOLVED` (with `DISPATCHED ↔ INVESTIGATING` and
  `RESOLVED → NEW/DISPATCHED` reopen loops).
- These two vocabularies coexist and are each internally consistent and fully tested (192 passed).
  "Rigidly enforces a canonical state machine" remains false of the repo as a whole: the two layers
  speak different, deliberately aligned-in-historically vocabularies.

## F. Frontend integration result
**PARTIAL**
- Canonical read/write paths use `apiFetch()` with a `Bearer` token.
- Legacy paths (`govAcknowledge`, `govSendAlert`, `openIncDrawer`, `loadIncidentTable`) still use raw
  `fetch()` with **no Authorization header** and will return 401 for gated calls once the auth fix deploys.
- The frontend contains simulated / non-live UI: SOS reporting, satellite-overpass simulation, and
  response-team simulation render demo data, not live telemetry.
- Audit findings in-tree: stored-XSS sink (unescaped `innerHTML` in `static/portal-modules.js`), no
  Content-Security-Policy on the production response headers. **Both remediated 2026-09-20** (P1: shared
  `esc()` applied at every data-bearing sink, verified by `p15-xss-check.js`; CSP + XFO/XCTO/
  Referrer-Policy/Permissions-Policy shipped in `app.py`, the FastAPI middleware, and `vercel.json`).
- The claim "absolutely zero mocked API calls, hardcoded data scenarios, fake states" is **false** and
  has been removed.

## G. RBAC result
**PARTIAL**
- `Depends(get_current_user)` and role checks are implemented in the FastAPI layer.
- The legacy handler gates with `legacy_auth.authenticated_role` (HMAC token, 401/403, per-IP login
  limiter) — in tree, but **not yet deployed**; the live site still accepts an arbitrary email + any
  password and returns a valid admin token (re-verified 2026-09-20).
- The frontend login path (auth gate honoring typed credentials, `handleCustomLogin`/`openLoginModal`)
  was only wired on 2026-09-20 (P0-5); before that the Auth UI never actually authenticated.

## H. Demo scenario result
**PARTIAL**
- `seed_demo.py` implements the 5 canonical scenarios and `docker-compose.yml` sets `APP_MODE=demo`,
  `DATA_SOURCE=cache`.
- Caveat: most UI metrics/telemetry in the served dashboard are simulation placeholders, not live
  pipeline output (see F).

## I. ML result
**PARTIAL**
- `backend/app/services/ml/model.py` honestly documents synthetic training data and surfaces
  "uncalibrated classification confidence". Good.
- Legacy path (`ml/`) loads `ml/models/classifier.pkl` and fails on a newer scikit-learn version —
  pre-existing, unrelated to this pass.

## J. Security result
**PARTIAL — remediation in progress**
- Verified 2026-09-20: two JWT secret values are committed at `fc3877b`:
  `firesense-dev-secret-key-change-in-production-32bytes-min` and
  `firesense-docker-production-secret-key-32chars`. Rotation + history purge is an open P0.
- The NASA FIRMS API key (`6cb2a1966681605e7843b31f1d248329`) was verified via `git log -S` to have
  **never** been committed.
- A PostGIS credential (`password=secret`) existed only in **uncommitted working-tree code**; it was
  removed 2026-09-20 (P0-3) and the PostGIS path is now env-gated (`FIRESENSE_SPATIAL_DB_DSN`, closed by
  default → Overpass).
- The claim that "NO production passwords, database credentials, or JWT secrets were committed" is
  **false** (see JWT commits above) and has been removed.

## K. Documentation result
**PARTIAL**
- `README.md`, `docs/SIH_QA.md`, `docs/DEMO_RUNBOOK.md`, `docs/IMPLEMENTATION_STATUS.md` exist.
- `README.md` badges previously overstated ("119 Passing", "Production Live"); corrected 2026-09-20 with a
  deployment-status note.

## L. Complete E2E result
**PARTIAL**
- The P0 auth flow is verified in unit tests and (2026-09-20) a browser-driven login against a local
  instance. A full scripted Dry-Run journey was not re-run this pass.

## M. Discrepancies (2026-09-20)
1. ~~6 pytest failures~~ — **resolved 2026-09-20**: legacy tree aligned to legacy vocabulary (192 passed).
2. Auth remediation is **uncommitted and undeployed**; the live site's auth bypass was re-verified today.
3. Rotation of committed JWT secrets + git history purge not yet performed (open P0).
4. NASA FIRMS API key rotation not yet performed (open P0 — user action at FIRMS + Vercel).
5. Live site env (`FIRESENSE_DEMO_PASSWORD`, `FIRESENSE_TOKEN_SECRET`, `FIRMS_MAP_KEY`) not yet set.

## N. P1/P2 remediation completed (2026-09-20)
Evidence-based, in-tree only (not yet deployed/committed).

1. **Stored-XSS sweep (P1).** Shared `esc()` added at the top of `static/app.js` (loads before
   `portal-modules.js`) and applied at every innerHTML sink interpolating user/server-controlled strings:
   citizen-reports feed, public alerts, incident table + drawer, detection feed, responder select,
   sitrep note, timeline logs, classifier pipeline results/popups, toasts, error blocks, and the
   attribute-context option values. Confirmed report `id` is server-generated (`RPT-{os.urandom(3).hex}`
   in both `app.py` and `backend/app/api/reports.py`), so `onclick` attr tokens stay safe. Verified:
   `node --check` clean and `p15-xss-check.js` (18 assertions, incl. replay of the confirmed stored-XSS
   chain — all pass).
2. **Security headers (P1).** `Content-Security-Policy` (self + pinned Tailwind/unpkg CDN, OSM tile
   `img-src`, `frame-ancestors 'none'`), `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
   `Referrer-Policy: no-referrer`, `Permissions-Policy` (geolocation kept for the citizen "locate me"
   flow). Shipped as a single `AeroThermalHandler.end_headers()` override (catches every response incl.
   404s), a FastAPI `@app.middleware` for the Docker path, and a root `headers` block in `vercel.json`
   for the edge. Verified: 3 new integration tests on the live handler (HTML page, JSON 401, 404).
3. **Honest telemetry (P2).** Relabeled simulated claims: SOS modal no longer claims NDRF reroute /
   "Emergency Signal Received", SitRep no longer claims "transmitted to Command", dashboard headline no
   longer claims "Real-time situational awareness". Demo/simulated labelling is explicit.
4. **Legacy-path auth (P2).** The audit-F raw-`fetch` gaps (`govAcknowledge`, `govSendAlert`,
   `govExportPDF`, `advanceResponderState`, `loadIncidentTable`, responder select) now send
   `Authorization: Bearer <token>`, so they survive the post-deploy closed gate. 409/403 status-specific
   UX is preserved (not collapsed into `apiFetch` error handling).
5. **CI (P2).** `.github/workflows/ci.yml` — pytest + JS syntax check on push/PR. Green: 192 passed.
6. **State-machine suite green (P2).** The 6 legacy vocabulary failures were fixed by aligning
   `tests/test_state_machine.py` + `tests/test_alert_workflow.py` to the legacy vocabulary and aligning
   `backend/alerts.py`'s dispatch path (`NEW → INVESTIGATING → VERIFIED → DISPATCHED`) to the same chain.
   `backend/state_machine.py` (user's deliberate revert) was not modified.

Still open (needs owner decision / external action): dead-code sweep of the React app +
`static/components/*.jsx`, JWT-secret history purge, FIRMS key rotation, Vercel env + redeploy, commit of
the staged work.