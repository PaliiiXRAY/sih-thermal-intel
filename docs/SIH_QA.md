# FireSense: Smart India Hackathon (SIH26162) Technical Q&A Guide

Comprehensive architectural, algorithmic, and operational defense guide for jury evaluation.

---

### Q1: Why NASA FIRMS data?
**Answer:** NASA FIRMS (Fire Information for Resource Management System) provides real-time thermal anomaly detections from moderate-resolution polar-orbiting satellites: VIIRS (375m spatial resolution, S-NPP and NOAA-20/21) and MODIS (1km resolution, Terra and Aqua). It offers calibrated Fire Radiative Power (FRP in Megawatts) and brightness temperatures across India every 3 hours without requiring custom orbital ground stations.

### Q2: Why PostgreSQL + PostGIS instead of MongoDB, SQLite, or flat JSON?
**Answer:** Thermal disaster management is inherently geospatial and transactional. PostGIS provides industry-standard spatial indexing (R-Tree / GiST) and geodesic calculations (`ST_DWithin`, `ST_Distance` on WGS84 geography types). PostgreSQL guarantees ACID compliance for atomic lifecycle transitions and maintains relational foreign-key integrity between Hotspots, Incidents, Critical Assets, First Responders, and append-only Incident Logs.

### Q3: Why XGBoost for classification instead of deep learning (CNNs/Transformers)?
**Answer:** 
1. **Feature Modality:** Satellite thermal anomaly detection records are tabular/geospatial records (FRP, brightness temperature, background temperature differential, day/night flag, temporal persistence count, distance to registered industrial zoning, landcover category). Gradient-boosted decision trees (XGBoost) consistently outperform deep networks on structured tabular datasets.
2. **Deterministic Fallback:** If the ML artifact is unavailable or missing, a deterministic expert-rules classifier immediately takes over with zero downtime.
3. **Inference Latency & Portability:** XGBoost models execute in <2ms on modest CPU hardware without GPU infrastructure, critical for edge emergency operations centers.
4. **Explainability:** Decision trees provide transparent feature importance (gain/weight), allowing operators to audit why an event was classified as a refinery flare vs. a wildfire.

### Q4: How is an industrial gas flare distinguished from an uncontrolled fire?
**Answer:** By correlating three distinct signals:
1. **Temporal Persistence:** Gas flares are stationary, continuous operational processes exhibiting persistence scores >80% across 40+ satellite overpasses over 60 days.
2. **Geospatial Cadastre Context:** PostGIS distance queries correlate the hotspot with registered industrial land-use zones (e.g. refineries, chemical plants, offshore terminals).
3. **Thermal Signature:** Flares typically have high brightness temperatures with localized, stable FRP signatures that do not demonstrate perimeter expansion.

### Q5: How is temporal persistence calculated?
**Answer:**
$$\text{Persistence Score} = \min\left(100.0, \frac{\text{Historical Passes Observed}}{\text{Total Satellite Passes in Lookback Window}} \times 100\right)$$
A threshold of $\ge 50\%$ with spatial variance $<200\text{m}$ indicates stationary industrial combustion, whereas wildfires and crop burning demonstrate low persistence (<20%) or episodic multi-day bursts with shifting centroid coordinates.

### Q6: What does the Risk Score mean? Is it a probability?
**Answer:** The Risk Score is an operational **prioritization score (0–100)**, **NOT a probability of ground fire**. It balances five transparent operational components:
$$\text{Priority Score} = 0.30 \times \text{Severity} + 0.25 \times \text{Persistence} + 0.20 \times \text{Exposure} + 0.15 \times \text{Infrastructure} + 0.10 \times \text{Growth Proxy}$$
- **Severity (30%):** Satellite FRP and peak brightness temperature.
- **Persistence (25%):** Duration of thermal anomaly.
- **Exposure (20%):** Proximity to human population settlements and schools.
- **Infrastructure (15%):** PostGIS proximity to power plants, substations, and fuel storage.
- **Growth Proxy (10%):** Spread rate between successive satellite passes.

### Q7: Why are Detection Confidence and Classification Confidence kept separate?
**Answer:** They measure entirely different uncertainties:
1. **Detection Confidence (`detection_confidence`):** Represents the satellite sensor's optical signal-to-noise quality (LOW, NOMINAL, HIGH) as reported by the FIRMS processing algorithm.
2. **Classification Confidence (`classification_confidence`):** Represents the ML model's or deterministic classifier's confidence (0.0 to 1.0) that the detected anomaly belongs to a specific semantic class (e.g. `WILDFIRE` vs `GAS_FLARE`).
Conflating the two would mislead commanders into mistaking a clear satellite sensor reading of a benign gas flare for a high-probability wildfire.

### Q8: How does geospatial context enrichment work?
**Answer:** PostGIS functions `ST_DWithin` and `ST_Distance` perform geodesic distance calculations against spatial tables (`assets` and `responders`) indexed with SRID 4326. The backend queries all critical infrastructure within a 100km radius and selects the closest available specialized responder unit (e.g., hazmat unit for petrochemical fires, forest ranger squads for forest reserves).

### Q9: How do alerts work? Is the government system actually contacted?
**Answer:** In compliance with honest demonstration practices, **ALL alerts in FireSense are explicitly simulated (`is_simulated: true`)**. The backend generates structured JSON payloads with recommended responders and sends them to the authority dashboard and public advisory feeds. Real emergency dispatch integration (e.g., ERSS 112, NDRF automated dispatch) would require production ministerial agreements and authenticated telecommunication gateways.

### Q10: How is auditability and accountability implemented?
**Answer:** FireSense implements an append-only audit trail table `incident_logs`. Every lifecycle action (`CLASSIFY`, `ALERT_DISPATCH`, `STATUS_CHANGE`) records:
- Event action
- Timestamp (`changed_at`)
- Transition (`old_status` $\to$ `new_status`)
- Operator identifier (`changed_by`)
- Provenance metadata (algorithm version, role credentials, notes)
This log is immutable and cannot be edited or deleted by users.

### Q11: What happens when NASA FIRMS or external APIs are unavailable?
**Answer:** FireSense operates in an **Offline / Degraded Mode (`APP_MODE=demo`, `DATA_SOURCE=cache`)**. Curated, verified satellite telemetry passes and local OSM spatial tags are cached locally in PostgreSQL and JSON fixtures. The platform seamlessly runs demonstration scenarios and training simulations without live internet access.

### Q12: How does the system scale?
**Answer:**
- **FastAPI Core:** Non-blocking async endpoints capable of handling thousands of concurrent requests per worker.
- **PostGIS Spatial Partitioning:** Spatial indices (GiST) ensure $O(\log N)$ spatial lookup times even across millions of national hotspot records.
- **Modular Monolith Architecture:** Decoupled service modules (`ml`, `geospatial`, `risk`, `alerting`) can be decomposed into independent microservices or background worker queues (Celery/Redis) as national telemetry volume scales.

### Q13: Why FastAPI over Django or Flask?
**Answer:** FastAPI provides native Pydantic v2 data validation, OpenAPI/Swagger interactive documentation, async ASGI performance comparable to Go/NodeJS, and modern type annotations that prevent runtime schema bugs across the 119 verified test endpoints.

### Q14: What are the current technical limitations?
**Answer:**
1. **Thermal anomaly $\neq$ Confirmed ground fire:** Satellite sensors detect surface heat; ground truth requires field confirmation.
2. **Uncalibrated ML Output:** Classification confidence represents tree margin scores, not calibrated physical probabilities.
3. **Growth is a proxy:** Growth rate is estimated from multi-pass satellite bounding box expansions, not full thermodynamic CFD flame propagation.
4. **Simulated Dispatches:** Real governmental integration requires inter-agency MoUs.

### Q15: What would be added in a post-hackathon production deployment?
**Answer:**
1. Integration with ISRO Bhuvan satellite feeds for sovereign domestic coverage.
2. Production ERSS 112 / NDRF API gateway integrations.
3. LoRaWAN / Satellite-direct field telemetry sensor relays for zero-connectivity zones.
4. Real-time WebSocket / SSE broadcast push channels for active tactical field tracking.
