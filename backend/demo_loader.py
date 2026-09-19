"""
Demo Loader for SIH26162.
Loads scenario JSONs + facilities into memory at startup.
"""
import os
import json

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DEMO_DIR = os.path.join(DATA_DIR, "demo")
FACILITIES_FILE = os.path.join(DATA_DIR, "facilities.json")

_loaded_scenarios = {}
_loaded_facilities = {}


def load_all_scenarios() -> dict:
    global _loaded_scenarios
    if _loaded_scenarios:
        return _loaded_scenarios
    if not os.path.isdir(DEMO_DIR):
        return _loaded_scenarios

    for fname in sorted(os.listdir(DEMO_DIR)):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(DEMO_DIR, fname)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            _loaded_scenarios[data["id"]] = data
        except Exception as e:
            print(f"[DEMO LOADER] Warning: failed to load {fname}: {e}")

    return _loaded_scenarios


def load_facilities() -> dict:
    global _loaded_facilities
    if _loaded_facilities:
        return _loaded_facilities

    try:
        with open(FACILITIES_FILE, "r", encoding="utf-8") as f:
            _loaded_facilities = json.load(f)
    except Exception as e:
        print(f"[DEMO LOADER] Warning: failed to load facilities: {e}")
        _loaded_facilities = {}

    return _loaded_facilities


def get_scenario(scenario_id: str) -> dict:
    if not _loaded_scenarios:
        load_all_scenarios()
    return _loaded_scenarios.get(scenario_id)


def get_responders_nearby(lat: float, lon: float, limit: int = 5) -> list:
    import math

    facilities = load_facilities()
    responders = facilities.get("responders", [])

    def haversine(lat1, lon1, lat2, lon2):
        R = 6371
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    for r in responders:
        r["distance_km"] = round(haversine(lat, lon, r["lat"], r["lon"]), 1)

    return sorted(responders, key=lambda r: r["distance_km"])[:limit]
