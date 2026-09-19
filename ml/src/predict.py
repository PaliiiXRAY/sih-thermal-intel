import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def classify(incident):
    """
    Classifies a FIRMS incident based on deterministic rules.

    Interface:
    - Input: incident (dict) containing FIRMS data and enriched features.
    - Output: {"class": str, "confidence": float, "evidence": list[str]}

    This is the deterministic baseline. It will be replaced by
    XGBoost inference once the model is trained.
    """

    # Default response
    result = {
        "class": "UNKNOWN",
        "confidence": 0.0,
        "evidence": []
    }

    if not incident:
        return result

    # Baseline Rule-Based Logic
    # Note: These are very coarse rules for the initial integration.
    # Refined logic will move to feature_engineering and weak_supervision.

    frp = incident.get("frp", 0)
    land_cover = incident.get("land_cover", "unknown")
    dist_to_industrial = incident.get("dist_to_industrial", float('inf'))
    persistence = incident.get("persistence_count", 0)

    # Rule 1: Industrial Fire (Strong proximity + thermal signal)
    if dist_to_industrial < 1000 and frp > 50:
        result["class"] = "INDUSTRIAL_FIRE"
        result["confidence"] = 0.7
        result["evidence"].append("industrial_proximity")
        result["evidence"].append("significant_frp")
        return result

    # Rule 2: Gas Flare (High persistence, usually specific locations)
    # Guardrail: Persistence alone is not enough for flare.
    if persistence > 10 and land_cover == "industrial":
        result["class"] = "GAS_FLARE"
        result["confidence"] = 0.6
        result["evidence"].append("high_persistence")
        result["evidence"].append("industrial_landcover")
        return result

    # Rule 3: Wildfire (Forest land cover + thermal signal)
    # Guardrail: Land cover alone cannot label wildfire.
    if land_cover in ["forest", "shrubland"] and frp > 30:
        result["class"] = "WILDFIRE"
        result["confidence"] = 0.5
        result["evidence"].append("forest_landcover")
        result["evidence"].append("thermal_signal")
        return result

    # Rule 4: Crop Burning (Agricultural land cover + short duration)
    if land_cover == "cropland" and persistence < 3:
        result["class"] = "CROP_BURNING"
        result["confidence"] = 0.4
        result["evidence"].append("cropland_landcover")
        result["evidence"].append("low_persistence")
        return result

    return result

if __name__ == "__main__":
    # Basic test cases to verify output schema
    test_incidents = [
        {"frp": 100, "dist_to_industrial": 500, "land_cover": "industrial", "persistence_count": 1},
        {"frp": 10, "dist_to_industrial": 5000, "land_cover": "forest", "persistence_count": 1},
        {"frp": 80, "dist_to_industrial": 5000, "land_cover": "forest", "persistence_count": 2},
        {"frp": 20, "dist_to_industrial": 10000, "land_cover": "cropland", "persistence_count": 1},
        {"frp": 5, "dist_to_industrial": 10000, "land_cover": "unknown", "persistence_count": 1},
    ]

    for i, inc in enumerate(test_incidents):
        print(f"Incident {i}: {classify(inc)}")
