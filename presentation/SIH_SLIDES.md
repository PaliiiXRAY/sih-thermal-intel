# SIH26162 Presentation Slides Content (NTRO)
**Problem Statement Title:** AI-Based Detection and Classification of Industrial Fires and Persistent Thermal Sources Using NASA FIRMS, OSM & Satellite Data  
**Organization:** National Technical Research Organisation (NTRO)  
**Category:** Software | **Domain:** Miscellaneous / Geospatial Intelligence  
**Platform Name:** AeroThermal  

---

## Slide 1: Title Slide
* **Project Name:** AeroThermal (SIH26162)
* **Tagline:** Geospatial Thermal Anomaly Classifier Fusing NASA FIRMS, OpenStreetMap & Multi-Temporal Persistence
* **Theme:** National Geospatial Intelligence (NTRO)
* **Team Name:** [Your Team Name]
* **Team Members:** [List 6 Members + College IDs]
* **Institute:** [Your College / University Name]

---

## Slide 2: The Core Problem & National Security Context
* **The Geospatial Blind Spot:**
  * Spaceborne thermal infrared sensors (VIIRS / MODIS) detect thousands of thermal anomalies across India daily.
  * **The Challenge:** To a satellite, a heat pixel is just a bright temperature value. Is it:
    1. A legitimate petrochemical refinery gas flare?
    2. Seasonal agricultural stubble burning causing hazardous AQI?
    3. An escalating forest wildfire threatening a biosphere?
    4. Or an **unregistered, clandestine industrial facility** operating without environmental or security clearance?
* **Why Traditional Alert Systems Fail:**
  * Raw FIRMS feeds lack semantic context (land-use boundaries, industrial zoning, temporal recurrence).

---

## Slide 3: Proposed Solution — AeroThermal Architecture
* **The Tri-Vector Intelligence Fusion:**
  1. **Orbital Thermal Telemetry:** Ingestion of NASA FIRMS VIIRS 375m active fire data (Brightness Temperature, Fire Radiative Power - FRP, Acquisition Time).
  2. **OpenStreetMap (OSM) Semantic Boundary Correlation:** Intersects hot pixel coordinates with OSM land-use layers (`industrial=refinery`, `landuse=farmland`, `natural=wood`).
  3. **Multi-Temporal Persistence Engine:** Analyzes recurrence over a 60-day baseline to separate permanent stationary combustion from transient episodic events.
* **National Security Value for NTRO:**
  * Automatically flags **high-persistence thermal anomalies located in non-industrial or unmapped zones** (e.g., illegal brick kilns, clandestine metal smelters).

---

## Slide 4: Technical Architecture Pipeline
```
[NASA FIRMS VIIRS 375m Feed]       [OpenStreetMap Overpass API]
            │                                     │
            ▼                                     ▼
┌──────────────────────────┐         ┌──────────────────────────┐
│  Thermal Hotspot Engine  │         │  OSM Land-Use Extractor  │
│  - Lat/Lon, FRP (MW)     │         │  - Industrial / Farmland │
│  - Brightness Temp (K)   │         │  - Facility Proximity (m)│
└────────────┬─────────────┘         └────────────┬─────────────┘
             │                                    │
             └─────────────────┬──────────────────┘
                               │
                               ▼
            ┌──────────────────────────────────────┐
            │   Multi-Temporal Persistence Core    │
            │   - 60-Day Overpass Recurrence Index │
            │   - Stationary vs Transient Filter   │
            └──────────────────┬───────────────────┘
                               │
                               ▼
            ┌──────────────────────────────────────┐
            │       AI Classification Engine       │
            │  1. Industrial Flare (Refinery)      │
            │  2. Stubble Burning (Farmland)       │
            │  3. Forest Wildfire (Canopy spread)  │
            │  4. Clandestine Anomaly (NTRO Alert) │
            └──────────────────┬───────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                    Geospatial SOC Dashboard                      │
│  • Tactical Satellite Map (Leaflet) • FRP Sized Thermal Circles  │
│  • Actionable Agency Dispatch       • PDF Dossier & GeoJSON Export│
└──────────────────────────────────────────────────────────────────┘
```

---

## Slide 5: Innovation & Honest Technical Boundaries
* **Temporal Persistence as the Prime Differentiator:**
  * Conventional classifiers look only at single satellite overpasses. AeroThermal builds a 60-day spatial history—a refinery flare burns 300+ days/year in the exact same 375m cell, whereas stubble burning disappears after 48 hours.
* **Honesty on Resolution Boundaries (Winning the Jury):**
  * *Spatial Limit:* VIIRS resolution is 375m per pixel. AeroThermal attributes to the *facility zone*, not individual valves or pipes. Evaluators respect defensible scientific honesty over exaggerated claims.

---

## Slide 6: Feasibility & Agency Actionability
* **Inter-Agency Interoperability:**
  * Outputs tailored alerts:
    * *Industrial Flare* $\rightarrow$ Ministry of Environment (MoEFCC) emissions monitoring.
    * *Stubble Burning* $\rightarrow$ Commission for Air Quality Management (CAQM) & CPCB.
    * *Forest Fire* $\rightarrow$ State Forest Dept & Forest Survey of India (FSI).
    * *Clandestine Anomaly* $\rightarrow$ NTRO / State Intelligence UAV reconnaissance.
* **Open Data & Zero Cost:**
  * 100% powered by free public feeds (NASA LANCE/FIRMS & OpenStreetMap).

---

## Slide 7: Roadmap & Next Phases
* **Phase 1 (Hackathon MVP - Live Today):** Multi-temporal persistence engine, OSM land-use correlator, 4 Indian scenario classifications, interactive satellite dashboard, PDF/GeoJSON export.
* **Phase 2 (6 Months):** Sentinel-2 MSI (20m SWIR) high-resolution optical validation + automated UAV drone dispatch integration.
* **Phase 3:** National 24/7 Automated Thermal Surveillance Grid for Indian Critical Infrastructure.
