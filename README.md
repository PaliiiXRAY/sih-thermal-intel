# 🔥 FireSense | SIH26162 (NTRO)
### Spaceborne Thermal Anomaly Intelligence & Autonomous Disaster Response

[![Deployment](https://img.shields.io/badge/Deployment-Redeploy%20Pending%20%E2%80%A2%20P0%2BP1%20Done-blue?style=flat-square&logo=vercel)](https://sih-thermal-intel.vercel.app)
[![Problem Statement](https://img.shields.io/badge/SIH-SIH26162-orange?style=flat-square)](https://sih-thermal-intel.vercel.app)
[![Agency](https://img.shields.io/badge/Agency-NTRO-blue?style=flat-square)](https://sih-thermal-intel.vercel.app)
[![Satellite Data](https://img.shields.io/badge/Satellite-NASA%20FIRMS%20VIIRS%20375m-red?style=flat-square)](https://firms.modaps.eosdis.nasa.gov/)
[![Database](https://img.shields.io/badge/Database-PostgreSQL%20%2B%20PostGIS-336791?style=flat-square&logo=postgresql)](https://postgis.net)
[![Backend](https://img.shields.io/badge/Backend-Legacy%20HTTP%20%2B%20FastAPI-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![Tests](https://img.shields.io/badge/Tests-192%20passing-brightgreen?style=flat-square)](https://docs.pytest.org)

> **Deployment status (2026-09-20):** the public URL runs the legacy stdlib HTTP handler
> (`app.py` / `api/index.py`) and is **still exposed to unauthenticated admin access until the in-tree P0
> auth fix is redeployed**. The FastAPI backend (`backend/app/`) runs only via Docker. Post-deploy the demo
> password is set by `FIRESENSE_DEMO_PASSWORD` — there is no default credential, and missing env config
> yields 401/503. An automated CI pipeline (`.github/workflows/ci.yml`) runs the test suite on push/PR.

> **Live Production Platform:** [https://sih-thermal-intel.vercel.app](https://sih-thermal-intel.vercel.app)  
> **Tactical Operations Dashboard:** [https://sih-thermal-intel.vercel.app/app](https://sih-thermal-intel.vercel.app/app)  
> **Problem Statement ID:** SIH26162  
> **Ministry / Organization:** National Technical Research Organisation (NTRO)  
> **Domain:** Geospatial Intelligence, Defense, & Industrial Disaster Response  

---

## 🛰️ Executive Overview

NASA earth-observation satellites (**Suomi NPP / NOAA-20 VIIRS 375m** and **Terra/Aqua MODIS 1km**) register thousands of thermal infrared anomalies across the Indian subcontinent daily. However, spaceborne sensors only transmit raw thermal flux pixels (brightness temperature and Fire Radiative Power in MW). 

**The Challenge:** Spaceborne sensors cannot inherently tell whether a thermal spike is a routine, licensed gas flare in an oil refinery (burning at 600°C–1000°C), an uncontrolled explosion, agricultural stubble burning, or an **unregistered clandestine thermal anomaly** operating outside regulatory cadastre.

**FireSense converts raw satellite detections into action:**
$$\text{Detection} \longrightarrow \text{Classification} \longrightarrow \text{Contextualization} \longrightarrow \text{Prioritization} \longrightarrow \text{Simulated Alert} \longrightarrow \text{Tactical Tracking}$$

FireSense correlates spaceborne thermal anomalies with **PostgreSQL/PostGIS geospatial databases**, **OpenStreetMap (OSM) cadastres**, and **temporal cell persistence baselines**. It computes transparent danger scores, enriches events with nearby critical infrastructure, triggers simulated alerts to recommended emergency units, and tracks field operations through an immutable audit trail.

---

## 🏛️ System Architecture & Data Flow

```text
                                  [DATA SOURCES]
                 NASA FIRMS (VIIRS 375m / MODIS)  +  OSM Overpass API
                                         │
                                         ▼
                            [POSTGIS GEOSPATIAL ENGINE]
                 • PostGIS SRID 4326 R-Tree / GiST Geodesic Proximity
                 • Temporal Persistence Cell Baseline (60-Day Lookback)
                 • Critical Infrastructure Correlator (Plants, Schools, Reserves)
                                         │
                                         ▼
                       [AI CLASSIFICATION & SAFETY FALLBACK]
                 • XGBoost Decision Tree Classifier (FRP, Temp, Day/Night)
                 • Deterministic Expert Rule Fallback Layer
                 • Classes: Industrial Fire, Gas Flare, Wildfire, Crop Burning, Unknown
                                         │
                                         ▼
                          [TRANSPARENT RISK ENGINE (0-100)]
                 • 0.30 Severity + 0.25 Persistence + 0.20 Exposure
                   + 0.15 Infrastructure + 0.10 Growth Proxy
                                         │
                                         ▼
                 [CANONICAL STATE MACHINE & AUDIT LOGGING]
                 • Append-Only Immutable Audit Trail (IncidentLog)
                 • Strict Canonical Lifecycle State Machine
                                         │
                 ┌───────────────────────┼───────────────────────┐
                 ▼                       ▼                       ▼
      [NTRO INTELLIGENCE]     [GOVERNMENT COMMAND]    [FIRST RESPONDER]
      • Anomaly Telemetry     • Situational Map       • Tactical Queue
      • Evidence Dossier      • Simulated Dispatch    • En Route / Arrive
      • ML Re-Classification  • District Directives   • Contain / Resolve
                                         │
                                         ▼
                            [PUBLIC SAFETY ADVISORY]
                            • Simulated Bulletins (No PII)
                            • Designated Safe Shelters
                            • Crowdsourced Smoke Verification
```

---

## 🔄 Canonical Incident Lifecycle State Machine

The platform strictly enforces the canonical lifecycle contract across all API endpoints and dashboards:

```text
   DETECTED
      ↓
  CLASSIFIED
      ↓
   ASSESSED
      ↓
   ALERTED
      ↓
 ACKNOWLEDGED  ─────────┐ (Direct Shortcut)
      ↓                 │
   EN_ROUTE             │
      ↓                 │
   ARRIVED              │
      ↓                 │
  CONTAINED             │
      ↓                 │
   RESOLVED  ◄──────────┘
```

- **Alerting is Side-Effect Free:** Dispatching a simulated alert does not silently mutate incident status.
- **Strict Status Validation:** Transitions are managed exclusively via `PATCH /api/incidents/{id}/status`.
- **Forbidden Statuses:** `DISPATCHED`, `RESPONDING`, and `MITIGATED` are rejected by validation.

---

## ⚖️ Transparent Priority Risk Engine

The Risk Score is an operational **prioritization score (0–100)** and **explicitly NOT a ground fire probability**:

$$\text{Priority Score} = 0.30 \times S + 0.25 \times P + 0.20 \times E + 0.15 \times I + 0.10 \times G$$

1. **Severity ($S$, 30%):** Fire Radiative Power (MW) and brightness temperature differential.
2. **Persistence ($P$, 25%):** Temporal repetition count over historical satellite overpasses.
3. **Exposure ($E$, 20%):** Estimated population settlement proximity and density.
4. **Infrastructure ($I$, 15%):** PostGIS geodesic proximity (`ST_DWithin`) to high-value assets (power plants, fuel depots, substations).
5. **Growth Proxy ($G$, 10%):** Multi-pass spatial bounding box expansion rate (proxy, not CFD fire-spread prediction).

---

## ⚡ 5 Curated Offline Demonstration Scenarios

Pre-cached in PostgreSQL for 100% reliable hackathon presentation without external NASA API dependence:

1. **Angul Thermal Power Station (`industrial_fire`):** Coal stockyard spontaneous combustion event with critical infrastructure downwind threat corridor.
2. **Jamnagar Petrochemical Complex (`gas_flare`):** Stationary industrial flare stack verified against licensed petrochemical cadastre (94% persistence).
3. **Similipal Biosphere Reserve (`wildfire`):** Episodic forest canopy wildfire perimeter encroaching toward tribal settlements.
4. **Sangrur Agricultural District (`crop_burning`):** Seasonal stubble burning cluster with transient persistence (<15%).
5. **Singrauli Hinterland Belt (`unknown`):** High-heat anomaly with zero registered industrial zoning in scrubland, flagged for tactical NTRO investigation.

---

## 🔐 Role-Based Access Control (RBAC) Matrix

| Endpoint | Method | Analyst | Authority | Responder | Admin | Public |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `/auth/login` | POST | ✓ | ✓ | ✓ | ✓ | ✓ |
| `/auth/me` | GET | ✓ | ✓ | ✓ | ✓ | ✗ (401) |
| `/api/incidents/{id}/classify` | POST | ✓ | ✓ | ✗ (403) | ✓ | ✗ (401) |
| `/api/incidents/{id}/context` | GET | ✓ | ✓ | ✓ | ✓ | ✗ (401) |
| `/api/incidents/{id}/risk` | GET | ✓ | ✓ | ✓ | ✓ | ✗ (401) |
| `/api/incidents/{id}/alert` | POST | ✗ (403) | ✓ | ✗ (403) | ✓ | ✗ (401) |
| `/api/incidents/{id}/status` | PATCH | ✗ (403) | ✓ | ✓ | ✓ | ✗ (401) |
| `/api/incidents/{id}/timeline` | GET | ✓ | ✓ | ✓ | ✓ | ✗ (401) |
| `/public/alerts` | GET | ✓ | ✓ | ✓ | ✓ | ✓ (200) |

---

## 🚀 Quick Start (Running Locally)

### 1. Clone & Setup Python Virtual Environment
```bash
git clone https://github.com/PaliiiXRAY/sih-thermal-intel.git
cd sih-thermal-intel

python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Start PostgreSQL / PostGIS Database
```bash
# Using Docker Compose
docker compose up -d db
```

### 3. Verify Migrations & Seed Curated Scenarios
```bash
# Verify Alembic head (expected: a2b3c4d5e6f7)
alembic current

# Seed 5 curated scenarios with provenance metadata
python seed_demo.py --scenario all
```

### 4. Launch Unified Application Server
```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

- **Application Portal:** [http://localhost:8000/app](http://localhost:8000/app)
- **Landing Page:** [http://localhost:8000/](http://localhost:8000/)
- **Swagger Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)

### 5. Run Automated Test Suite
```bash
pytest -q
# Output: 119 passed, 0 failures, 0 skipped
```

---

## ⚠️ Explicit Technical Limitations & Disclaimers

1. **Thermal Anomaly $\neq$ Confirmed Ground Fire:** Satellite detections identify thermal radiant flux; ground ground-truth verification is mandatory before deploying life-safety assets.
2. **Uncalibrated Confidence:** XGBoost model confidence represents internal tree margin certainty, not calibrated physical probabilities.
3. **Prioritization Score:** Risk score represents operational urgency (0–100), NOT physical flame ignition probability.
4. **Growth Proxy:** Growth rate is estimated from multi-pass satellite bounding box expansions, not CFD thermodynamic fire propagation modeling.
5. **Simulated Dispatches:** All alerting is simulated (`is_simulated: true`). Real emergency dispatch requires production inter-agency MoUs.

---

## 📚 Documentation Links
- **[SIH Jury Q&A Guide](docs/SIH_QA.md):** 15 deep-dive architectural and algorithmic defense answers.
- **[Demonstration Runbook](docs/DEMO_RUNBOOK.md):** 5-minute judge walkthrough script.
- **[Implementation Status](docs/IMPLEMENTATION_STATUS.md):** Full Phase 1–13 verification tracking.
