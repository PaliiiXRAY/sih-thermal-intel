# AeroThermal | SIH26162 (NTRO)
### Satellite-to-Ground Disaster Management & Persistent Thermal Anomaly Intelligence

> **Live Production Platform:** [https://sih-thermal-intel.vercel.app](https://sih-thermal-intel.vercel.app)  
> **Problem Statement ID:** SIH26162  
> **Ministry / Organization:** National Technical Research Organisation (NTRO)  
> **Domain:** Miscellaneous / Geospatial Disaster Intelligence  

---

## 🛰️ What is AeroThermal?
NASA satellites (VIIRS / MODIS) detect thousands of thermal infrared anomalies across India daily. However, spaceborne sensors cannot distinguish whether a heat signature is a legitimate refinery gas flare, dangerous crop residue smoke, a spreading forest wildfire, or an **unregistered clandestine industrial operation**.

**AeroThermal converts raw NASA satellite thermal pixels into prioritized, actionable incident dossiers, identifies nearby villages and critical infrastructure at risk, routes alerts to local fire stations, and tracks the response until resolution.**

---

## 🧱 The 6-Module Operational Architecture
1. **Module 1: DETECT** — Ingestion of NASA FIRMS VIIRS 375m active fire telemetry (Fire Radiative Power, Brightness Temperature, Acquisition Timestamp).
2. **Module 2: CLASSIFY & EXPLAIN** — Distinguishes Wildfires, Agricultural Stubble Burns, Industrial Flares, and Clandestine Anomalies with an explicit evidence/counter-evidence panel.
3. **Module 3: CONTEXTUALIZE** — Correlates coordinates with OpenStreetMap (OSM) vector boundaries and a 60-day local historical baseline for this specific 375m cell.
4. **Module 4: ASSESS (RISK ENGINE)** — Calculates a Composite Danger Score (0-100), builds an Assets-at-Risk Table (population exposure, highways, healthcare), and computes a Downwind Impact Zone.
5. **Module 5: RESPOND & DISPATCH** — Generates Incident Tickets (`#INC-2026-0042`) and triggers simulated encrypted dispatches to nearest emergency authorities (e.g. Baripada Fire Station).
6. **Module 6: TRACK & FEEDBACK** — Provides a dual-view interface: Control Room Commander view and First Responder Mobile Field Terminal (`Acknowledge` $\to$ `En Route` $\to$ `Arrived` $\to$ `Contained` $\to$ `Resolved`).

---

## 🚀 Quick Start (Running Locally)

### Prerequisites:
* Python 3.10+
* Any web browser

### Run the server:
```bash
# 1. Clone the repository
git clone <YOUR_REPO_URL>
cd sih-thermal-intel

# 2. Run the HTTP server (Zero external dependencies needed!)
python app.py
```

Open your browser and navigate to:  
👉 **`http://localhost:5002`**

---

## 📁 Repository Structure
```
sih-thermal-intel/
├── app.py                     # Core HTTP server exposing REST APIs & static assets (Port 5002)
├── backend/
│   ├── firms_loader.py        # NASA FIRMS Active Fire data parser
│   ├── osm_correlator.py      # OpenStreetMap vector land-use correlator
│   ├── persistence_engine.py  # 60-day satellite overpass recurrence calculator
│   ├── classifier.py          # AI classification heuristics & agency routing
│   ├── incident_engine.py     # State machine & Asset-at-Risk exposure database
│   └── samples.py             # Pre-cached operational Indian geographic scenarios
├── static/
│   ├── index.html             # High-density dual-view Tactical Dashboard (Control Room & Responder)
│   ├── app.js                 # Leaflet map, state machine transitions, PDF/GeoJSON exports
│   └── style.css              # Dark cyber styling & thermal pulse animations
├── presentation/
│   ├── SIH_SLIDES.md          # 7 official SIH PowerPoint slides content
│   └── DEMO_SCRIPT.md         # 2-minute stage pitch script with judge Q&A defense
├── SIH_WINNING_TEMPLATE_AEROTHERMAL_SIH26162.pptx  # Official SIH PowerPoint Deck
├── requirements.txt           # Python dependencies (for cloud serverless)
└── vercel.json                # Vercel production deployment configuration
```

---

## 🏆 Presentation Materials
* **PowerPoint Presentation:** Double-click [`SIH_WINNING_TEMPLATE_AEROTHERMAL_SIH26162.pptx`](SIH_WINNING_TEMPLATE_AEROTHERMAL_SIH26162.pptx) to open in Microsoft PowerPoint or Google Slides.
* **Stage Pitch Script:** Read [`presentation/DEMO_SCRIPT.md`](presentation/DEMO_SCRIPT.md) for word-for-word instructions on how to deliver the live demo.

---

## 👥 6-Person Team Sprint Execution
* **Person 1 (Data):** NASA FIRMS telemetry ingestion & preprocessing
* **Person 2 (Intelligence):** Classification heuristics & Explainability Evidence Engine
* **Person 3 (GIS):** OpenStreetMap boundaries, Asset-at-Risk queries & downwind impact zones
* **Person 4 (Backend):** Incident lifecycle state machine & REST API endpoints
* **Person 5 (Responder):** First Responder dashboard & simulated emergency dispatch workflow
* **Person 6 (Frontend & Pitch):** Control Room UI integration, map layer sync & presentation delivery
