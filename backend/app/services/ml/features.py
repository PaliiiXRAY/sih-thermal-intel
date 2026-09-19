"""
Feature Extraction Layer for FireSense ML Classification.
Produces a deterministic 8-element numerical feature vector.

FEATURE SEMANTICS & LIMITATIONS:
1. Sentinel / Default Values:
   - nearest_asset_dist_km = 999.0 is a sentinel default representing missing or unavailable spatial context data,
     NOT a measured physical ground distance.
   - 0.0 binary indicators (is_industrial_zone, is_forest_zone, is_agricultural_zone) represent the explicit absence
     or unavailability of the corresponding contextual signal.
2. Raw Coordinate Limitations:
   - latitude and longitude are included as raw numerical features for baseline prototype demonstration.
   - Note: Including raw coordinates in baseline ML models may introduce spatial overfitting or geographic shortcut bias.
     Production deployment should replace raw coordinates with regional embeddings or spatial context features.
"""
from typing import Any, Dict, List, Optional

FEATURE_NAMES = [
    "frp",
    "persistence_score",
    "latitude",
    "longitude",
    "nearest_asset_dist_km",
    "is_industrial_zone",
    "is_forest_zone",
    "is_agricultural_zone",
]


def _extract_feature(obj: Any, key: str, default: Any = None) -> Any:
    """Safely extract feature from object attribute, dict key, or nested explanation dict."""
    if isinstance(obj, dict):
        if key in obj and obj[key] is not None:
            return obj[key]
        explanation = obj.get("explanation")
        if isinstance(explanation, dict) and key in explanation and explanation[key] is not None:
            return explanation[key]
        return default

    if hasattr(obj, key):
        val = getattr(obj, key)
        if val is not None:
            return val
    if hasattr(obj, "explanation"):
        explanation = getattr(obj, "explanation")
        if isinstance(explanation, dict) and key in explanation and explanation[key] is not None:
            return explanation[key]

    return default


def extract_features(
    incident: Any, context: Optional[Dict[str, Any]] = None
) -> Dict[str, float]:
    """
    Extract deterministic numeric feature vector for XGBoost model inference.

    Returns:
        Dict mapping feature names to float values.
    """
    raw_frp = _extract_feature(incident, "frp", 0.0)
    try:
        frp = float(raw_frp) if raw_frp is not None else 0.0
    except (ValueError, TypeError):
        frp = 0.0

    raw_persistence = _extract_feature(incident, "persistence_score", 0.0)
    try:
        persistence = float(raw_persistence) if raw_persistence is not None else 0.0
    except (ValueError, TypeError):
        persistence = 0.0

    raw_lat = _extract_feature(incident, "latitude", 0.0)
    try:
        lat = float(raw_lat) if raw_lat is not None else 0.0
    except (ValueError, TypeError):
        lat = 0.0

    raw_lon = _extract_feature(incident, "longitude", 0.0)
    try:
        lon = float(raw_lon) if raw_lon is not None else 0.0
    except (ValueError, TypeError):
        lon = 0.0

    # Nearest asset distance from context if available (999.0 = sentinel default for missing spatial context)
    nearest_asset_dist = 999.0
    if isinstance(context, dict) and "nearest_assets" in context:
        assets = context.get("nearest_assets") or []
        if assets and isinstance(assets, list):
            first_dist = assets[0].get("distance_km")
            if first_dist is not None:
                try:
                    nearest_asset_dist = float(first_dist)
                except (ValueError, TypeError):
                    nearest_asset_dist = 999.0

    # Landcover & Tags indicators (0.0 = explicit absence or unavailability of contextual signal)
    landcover = str(_extract_feature(incident, "landcover", "")).lower()
    facility_type = str(_extract_feature(incident, "facility_type", "")).lower()
    tags = _extract_feature(incident, "tags", [])
    if not isinstance(tags, list):
        tags = []
    combined_str = " ".join([landcover, facility_type] + [str(t).lower() for t in tags])

    is_industrial = 1.0 if any(k in combined_str for k in ["industrial", "refinery", "factory", "warehouse"]) else 0.0
    is_forest = 1.0 if any(k in combined_str for k in ["forest", "wildfire", "wildland", "woodland"]) else 0.0
    is_agricultural = 1.0 if any(k in combined_str for k in ["crop", "cropland", "farm", "stubble"]) else 0.0

    return {
        "frp": frp,
        "persistence_score": persistence,
        "latitude": lat,
        "longitude": lon,
        "nearest_asset_dist_km": nearest_asset_dist,
        "is_industrial_zone": is_industrial,
        "is_forest_zone": is_forest,
        "is_agricultural_zone": is_agricultural,
    }

