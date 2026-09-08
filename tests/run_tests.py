"""
AeroThermal Backend Test Suite (zero dependencies)
Run:  python tests/run_tests.py
Covers the classification rules, persistence engine, land-cover resolver,
FIRMS parser and the end-to-end pipeline over all demo scenarios.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.classifier import ThermalClassifier
from backend.persistence_engine import PersistenceEngine
from backend.landcover import LandCoverResolver
from backend.firms_loader import FIRMSLoader
from backend.osm_correlator import OSMCorrelator
from backend.pipeline import HotspotPipeline
from backend.samples import SCENARIOS
from backend.stats import compute_stats

PASS = 0
FAIL = 0

def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}  {detail}")

def osm(landuse, facility=None, dist=100):
    return {"landuse": landuse, "osm_tag": f"landuse={landuse}",
            "facility_name": facility, "facility_type": facility or "None",
            "distance_to_facility_m": dist}

print("== Persistence Engine ==")
p = PersistenceEngine.calculate_persistence("X", 48, 60)
check("48/60 passes -> HIGH PERSISTENCE", p["is_persistent"] and p["persistence_score"] == 80.0, p)
p = PersistenceEngine.calculate_persistence("X", 1, 60)
check("1/60 pass -> TRANSIENT", not p["is_persistent"], p)
p = PersistenceEngine.calculate_persistence("X", 60, 60)
check("60/60 passes capped at 100%", p["persistence_score"] == 100.0, p)

print("== Classifier rules ==")
res = ThermalClassifier.classify(
    {"frp": 88, "brightness_celsius": 85},
    osm("industrial", "Refinery", 120),
    PersistenceEngine.calculate_persistence("X", 48, 60))
check("persistent + refinery -> GAS FLARE", "GAS FLARE" in res["classification"], res["classification"])

res = ThermalClassifier.classify(
    {"frp": 96, "brightness_celsius": 82},
    osm("industrial", "power", 90),
    PersistenceEngine.calculate_persistence("X", 52, 60))
check("persistent + power -> THERMAL POWER PLANT", "THERMAL POWER PLANT" in res["classification"], res["classification"])

res = ThermalClassifier.classify(
    {"frp": 55, "brightness_celsius": 70},
    osm("quarry", "mining", 200),
    PersistenceEngine.calculate_persistence("X", 50, 60))
check("persistent + mining -> MINING SOURCE", "MINING" in res["classification"], res["classification"])

res = ThermalClassifier.classify(
    {"frp": 142, "brightness_celsius": 96},
    osm("forest", "Forest Reserve", 12000),
    PersistenceEngine.calculate_persistence("X", 6, 60))
check("forest + episodic -> WILDFIRE", "WILDFIRE" in res["classification"], res["classification"])

res = ThermalClassifier.classify(
    {"frp": 25, "brightness_celsius": 59},
    osm("farmland", None, 4200),
    PersistenceEngine.calculate_persistence("X", 2, 60))
check("farmland + transient -> STUBBLE BURNING", "AGRICULTURAL" in res["classification"], res["classification"])

res = ThermalClassifier.classify(
    {"frp": 52, "brightness_celsius": 71},
    osm("scrub", None, 8500),
    PersistenceEngine.calculate_persistence("X", 34, 60))
check("persistent + scrub + no facility -> CLANDESTINE", "CLANDESTINE" in res["classification"], res["classification"])

print("== Land-cover resolver ==")
lc = LandCoverResolver.resolve(osm("forest"))
check("forest -> Tree Cover", "Tree Cover" in lc["worldcover_class"], lc)
lc = LandCoverResolver.resolve(osm("farmland"))
check("farmland -> Cropland", lc["worldcover_class"] == "Cropland", lc)
lc = LandCoverResolver.resolve(osm("forest"))
check("tree cover flagged burn-restricted", lc["burn_restricted"], lc)

print("== FIRMS parser ==")
rows = [{"latitude": "22.35", "longitude": "69.83", "frp": "88.4",
         "bright_ti4": "358.2", "confidence": "high", "acq_date": "2026-09-09", "acq_time": "0430"}]
hs = FIRMSLoader.parse_hotspots(rows)[0]
check("parses lat/lon/frp", abs(hs["lat"] - 22.35) < 1e-6 and abs(hs["frp"] - 88.4) < 1e-6, hs)
check("kelvin -> celsius", abs(hs["brightness_celsius"] - 85.1) < 0.05, hs)
check("id assigned", hs["id"] == "FIRMS-0001", hs)

print("== OSM correlator ==")
d = OSMCorrelator.haversine_distance(22.35, 69.83, 22.36, 69.83)
check("haversine ~1.11km per 0.01deg lat", 1000 < d < 1250, d)
ctx = OSMCorrelator.correlate_hotspot(22.35, 69.83, {"landuse": "industrial", "distance_m": 120})
check("cached context passthrough", ctx["landuse"] == "industrial" and ctx["distance_to_facility_m"] == 120, ctx)

print("== End-to-end pipeline over all scenarios ==")
EXPECTED = {
    "jamnagar_refinery": "GAS FLARE",
    "punjab_stubble": "AGRICULTURAL",
    "similipal_wildfire": "WILDFIRE",
    "angul_thermal_plant": "THERMAL POWER PLANT",
    "clandestine_thermal_anomaly": "CLANDESTINE",
}
for sid, expect in EXPECTED.items():
    fc = HotspotPipeline.run_scenario(sid)
    labels = [f["properties"]["classification"]["classification"] for f in fc["features"]]
    # primary hotspot (first) must carry the expected class; co-located secondary
    # hotspots may classify into related classes (e.g. coal stockyard -> MINING)
    check(f"{sid} -> {expect}", len(labels) > 0 and expect in labels[0], labels)

print("== GeoJSON structure ==")
fc = HotspotPipeline.run_scenario("jamnagar_refinery")
f0 = fc["features"][0]
check("FeatureCollection with Point features",
      fc["type"] == "FeatureCollection" and f0["geometry"]["type"] == "Point", fc["type"])
props = f0["properties"]
check("dossier has firms/osm/persistence/landcover/classification",
      all(k in props for k in ("firms", "osm", "persistence", "landcover", "classification")), list(props))

print("== Stats ==")
st = compute_stats()
check("stats cover all scenarios", st["scenarios"] == len(SCENARIOS), st)
check("all hotspots classified", st["auto_classified"] == st["hotspots_analyzed"] and st["hotspots_analyzed"] > 0, st)
check("avg confidence 80-100", 80 <= st["avg_confidence"] <= 100, st["avg_confidence"])

print(f"\n{'='*40}\nRESULT: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
