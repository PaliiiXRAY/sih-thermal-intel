# Phase 10 Implementation Report: Demo Scenarios & Offline/Degraded Mode

**Status:** COMPLETE  
**Schema Checkpoint:** `schema-vertical-slice-stable`  
**Alembic Head:** `a2b3c4d5e6f7`  
**Tests Passing:** 119 passed, 0 failures, 0 skipped  

---

## 1. Executive Summary

Phase 10 establishes a deterministic, reproducible, and verifiable suite of curated demonstration scenarios. Demonstrations run independently of live NASA FIRMS connectivity, guaranteeing high-reliability evaluations during hackathon judging sessions.

---

## 2. Curated Scenario Coverage

The 5 authoritative scenarios in the repository provide complete coverage of thermal event types across India:

| Scenario Key | Alias | Region | Provenance Metadata | Classification | FRP (MW) | Brightness (K) | Persistence | Initial Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `angul_thermal_plant` | `industrial_fire` | Angul, Odisha | `DATA_SOURCE=CURATED_DEMO, SCENARIO_ID=angul_thermal_plant` | `INDUSTRIAL_FIRE` | 96.7 | 355.0 | 88.5% | `ALERTED` |
| `jamnagar_refinery` | `gas_flare` | Jamnagar, Gujarat | `DATA_SOURCE=CURATED_DEMO, SCENARIO_ID=jamnagar_refinery` | `GAS_FLARE` | 88.4 | 358.2 | 94.0% | `CLASSIFIED` |
| `similipal_wildfire` | `wildfire` | Similipal, Odisha | `DATA_SOURCE=CURATED_DEMO, SCENARIO_ID=similipal_wildfire` | `WILDFIRE` | 142.6 | 369.4 | 45.0% | `ASSESSED` |
| `punjab_stubble` | `crop_burning` | Sangrur, Punjab | `DATA_SOURCE=CURATED_DEMO, SCENARIO_ID=punjab_stubble` | `CROP_BURNING` | 24.5 | 332.0 | 12.0% | `CLASSIFIED` |
| `clandestine_thermal_anomaly` | `unknown` | Singrauli, MP/UP | `DATA_SOURCE=CURATED_DEMO, SCENARIO_ID=clandestine_thermal_anomaly`| `UNKNOWN` | 52.3 | 344.0 | 68.0% | `DETECTED` |

Each scenario includes:
- PostGIS-indexed Critical Assets (power plants, flare stacks, national parks, grain markets, railways).
- PostGIS-indexed First Responders (fire brigades, hazmat squads, forest rangers, medical units).
- Raw Hotspot observations with satellite sensor metadata.
- Pre-calculated risk factor breakdowns with explanations.
- Simulated alerts where status >= `ALERTED`.
- Complete append-only audit trail in `incident_logs`.

---

## 3. Demo Seeding & Safe Reset Architecture

A unified command-line tool `seed_demo.py` is established:

```bash
# Seed all 5 curated demo scenarios
python seed_demo.py --scenario all

# Seed specific scenario by key or alias
python seed_demo.py --scenario industrial_fire
python seed_demo.py --scenario jamnagar_refinery

# Application-level clean reset (NEVER drops tables or deletes volumes)
python seed_demo.py --reset
```

**Idempotency Guarantee:**
- Re-running `seed_demo.py` executes UPSERT logic matching existing entity IDs.
- Schema, foreign keys, spatial indices, and migrations remain untouched.

---

## 4. Offline & Degraded Mode Verification

1. **Environment Configuration:**
   - `APP_MODE=demo`
   - `DATA_SOURCE=cache`
2. **Zero NASA API Dependency:**
   - Classification pipeline and scenario inspection execute entirely offline from cached FIRMS observations and PostGIS spatial tables.
   - If external Overpass OSM API is unavailable, the pipeline falls back seamlessly to cached local OSM context tags.
3. **End-to-End Lifecycle Verification:**
   - Verified via automated test `tests/test_phase10_demo_and_offline.py` that `inc_singrauli_unknown_05` moves from `DETECTED` to `RESOLVED` on the identical incident ID across all 12 transitions.
