"""
Spatial-Temporal Persistence Scorer for SIH26162.
Evaluates recurrence of thermal anomalies within a spatial tolerance over a time window.
Returns a 0-100 score and a pattern label.
"""
import math


def _haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def compute_persistence_score(
    lat: float, lon: float,
    historical_observations: list,
    spatial_tolerance_m: float = 375.0,
    temporal_window_days: int = 60,
) -> dict:
    total = len(historical_observations)
    if total == 0:
        return {"score": 0, "pattern_label": "TRANSIENT",
                "spatial_matches": 0, "total_observations": 0, "recurrence_rate": 0.0}

    spatial_matches = sum(
        1 for obs in historical_observations
        if _haversine_m(lat, lon, obs["lat"], obs["lon"]) <= spatial_tolerance_m
    )

    recurrence_rate = min(1.0, spatial_matches / max(1, temporal_window_days))
    score = round(recurrence_rate * 100, 1)

    if score >= 60:
        label = "PERMANENT"
    elif score >= 25:
        label = "RECURRENT"
    elif score >= 8:
        label = "EPISODIC"
    else:
        label = "TRANSIENT"

    return {"score": score, "pattern_label": label,
            "spatial_matches": spatial_matches, "total_observations": total,
            "recurrence_rate": round(recurrence_rate, 4)}
