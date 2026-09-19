# FireSense: SIH Hackathon Presentation Demo Runbook

Step-by-step instructions for running, demonstrating, and resetting the FireSense thermal intelligence platform.

---

## 1. Prerequisites & Environment Setup

### System Requirements
- Python 3.10+ (Recommended: Python 3.11 / 3.12 / 3.13)
- PostgreSQL 14+ with PostGIS 3.3+ (or Docker)
- Modern Web Browser (Chrome, Edge, Firefox)

### Setup Local Environment
```bash
# Clone and enter workspace
git clone https://github.com/PaliiiXRAY/sih-thermal-intel.git
cd sih-thermal-intel

# Create virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## 2. Database Initialization & Migrations

### Option A: Using Local PostgreSQL / PostGIS
Ensure PostgreSQL is running on port 5432 and database `firesense` exists with PostGIS enabled:
```sql
CREATE DATABASE firesense;
\c firesense;
CREATE EXTENSION IF NOT EXISTS postgis;
```

### Option B: Using Docker Compose
```bash
docker compose up -d db
```

### Verify Alembic Migrations
```bash
# Verify migration status
alembic current
# Expected head: a2b3c4d5e6f7

# Run upgrade if fresh database
alembic upgrade head
```

---

## 3. Demo Data Seeding

Seed the 5 authoritative curated demo scenarios into PostgreSQL:
```bash
python seed_demo.py --scenario all
```
Expected terminal output:
```text
Seeding demo users...
Seeding curated demo scenarios...
  [OK] Angul Thermal Power Plant & Coal Stockyard Fire -> ID: inc_angul_thermal_01 [ALERTED]
  [OK] Jamnagar Petrochemical Complex Stationary Gas Flare -> ID: inc_jamnagar_flare_02 [CLASSIFIED]
  [OK] Similipal Biosphere Reserve Forest Wildfire -> ID: inc_similipal_wild_03 [ASSESSED]
  [OK] Sangrur Agricultural Farmland Stubble Burning -> ID: inc_punjab_stubble_04 [CLASSIFIED]
  [OK] Singrauli Hinterland Unregistered Thermal Anomaly -> ID: inc_singrauli_unknown_05 [DETECTED]
```

---

## 4. Launch Application Server

Start the unified FastAPI application (serves both REST APIs and the HTML/JS frontend):
```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open in your browser:
- **Application Portal:** [http://localhost:8000/app](http://localhost:8000/app)
- **Landing Page:** [http://localhost:8000/](http://localhost:8000/)
- **Interactive OpenAPI Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 5. Recommended 5-Minute Presentation Sequence

### Step 1: Open NTRO Intelligence Portal
- Navigate to `http://localhost:8000/app` and click **🛰️ NTRO Intelligence**.
- Role is set to `Analyst (analyst@firesense.org)`.
- Select `inc_singrauli_unknown_05` in `DETECTED` status:
  - Point out **Satellite Detection Confidence: HIGH**.
  - Show the **"Run Deterministic / XGBoost Classifier"** button.
  - Click it $\to$ state advances to `CLASSIFIED` with confidence metrics and evidence dossier.
  - Point out the **PostGIS Proximity Card**: nearest assets and responders retrieved via `ST_DWithin`.
  - Point out the **Transparent Priority Score**: 0.30 severity + 0.25 persistence + 0.20 exposure + 0.15 infrastructure + 0.10 growth proxy.
  - Explain that **Priority Risk is NOT a fire probability**.

### Step 2: Open Government Command Dashboard
- Click **🏛️ Government Command**.
- Role selector in top bar automatically reflects or allows switching to `Authority (authority@firesense.org)`.
- Select `inc_angul_thermal_01` (Angul Thermal Power Station):
  - View affected population exposure estimate (82K).
  - Click **"Dispatch Simulated Alert"** $\to$ generates structured simulated alert.
  - Point out the banner: **"SIMULATED DISPATCH"** (honestly stating real emergency services are not contacted).
  - Advance status in the Lifecycle Tracker from `ALERTED` to `ACKNOWLEDGED`.

### Step 3: Open First Responder Operational Console
- Click **🚒 First Responder**.
- Switch top role to `Responder (responder@firesense.org)`.
- Notice `inc_angul_thermal_01` appears in the tasking queue.
- Demonstrate canonical lifecycle progression:
  1. Click **"Transition → EN_ROUTE"** $\to$ status updates, logged in audit trail.
  2. Click **"Transition → ARRIVED"** $\to$ field unit on scene.
  3. Click **"Transition → CONTAINED"** $\to$ thermal spread arrested.
  4. Click **"Transition → RESOLVED"** $\to$ terminal state reached.
- Inspect the **Immutable Incident Audit Trail**: verify every transition recorded timestamp, operator ID, and action.

### Step 4: Open Citizen Services & Public Advisory
- Click **👥 Citizen Services** (Role: Public Citizen / Unauthenticated).
- Show **Active Alerts Near You** populated from `GET /public/alerts`.
- Demonstrate that **no private responder numbers or internal user PII is exposed**.
- Show multilingual support (English, Hindi, Odia).
- Submit a crowdsourced citizen report and observe it appear in the Government Command inbox.

---

## 6. Demo Reset Procedure

To restore the demonstration back to its pristine initial state at any time:
```bash
python seed_demo.py --reset
```
*Note: This command safely resets incident tables without dropping PostgreSQL database volumes or breaking Alembic migrations.*

---

## 7. Troubleshooting

| Issue | Cause | Resolution |
| :--- | :--- | :--- |
| `Cannot reach backend on port 8000` | Server process not running | Run `uvicorn backend.app.main:app --port 8000` |
| `Database connection failed` | PostgreSQL service stopped | Run `docker compose up -d db` or start local PostgreSQL service |
| `Role forbidden (403)` | Operating with unauthorized role | Use top bar dropdown to switch to `Analyst` or `Authority` |
| `Incident queue empty` | Clean database | Run `python seed_demo.py --scenario all` or click "Seed Curated Scenarios" in UI |
