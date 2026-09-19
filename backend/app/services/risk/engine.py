"""
Transparent Risk & Priority Engine for FireSense.
Combines incident signals and spatial context into a transparent 0-100 priority score.
Note: Baseline demo-tuned weights; not scientifically calibrated.
"""
from typing import Any, Dict, List, Optional, Union

# Centralized Weight Configuration (Baseline demo-tuned weights; not scientifically calibrated)
SEVERITY_WEIGHT = 0.30
PERSISTENCE_WEIGHT = 0.25
EXPOSURE_WEIGHT = 0.20
INFRASTRUCTURE_WEIGHT = 0.15
GROWTH_WEIGHT = 0.10

# Normalized Severity Mapping
SEVERITY_MAP = {
    "CRITICAL": 100.0,
    "HIGH": 75.0,
    "MEDIUM": 50.0,
    "LOW": 25.0,
}


def _extract_attr(obj: Any, key: str, default: Any = None) -> Any:
    """Extract feature safely from object attribute or dictionary."""
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


def get_severity_band(score: float) -> str:
    """
    Map numerical risk score (0-100) to human-readable severity band.
    0-24.99: LOW, 25-49.99: MEDIUM, 50-74.99: HIGH, 75-100: CRITICAL
    """
    if score >= 75.0:
        return "CRITICAL"
    elif score >= 50.0:
        return "HIGH"
    elif score >= 25.0:
        return "MEDIUM"
    else:
        return "LOW"


def calculate_risk(
    incident: Union[Any, Dict[str, Any]],
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Calculate transparent 0-100 priority risk score for an incident.

    Args:
        incident: Incident ORM model or dictionary.
        context: Optional spatial context dictionary containing nearest_assets/responders.

    Returns:
        Structured risk response matching team schema.
    """
    reasons: List[str] = []

    # 1. Severity Contribution (30%)
    raw_severity = _extract_attr(incident, "severity", "MEDIUM")
    severity_str = str(raw_severity).upper() if raw_severity else "MEDIUM"
    severity_score = SEVERITY_MAP.get(severity_str, 50.0)
    reasons.append(f"Severity rating '{severity_str}' contributes {severity_score:.0f}/100 to risk baseline")

    # 2. Persistence Contribution (25%)
    raw_persistence = _extract_attr(incident, "persistence_score", None)
    if raw_persistence is not None:
        try:
            persistence_score = max(0.0, min(100.0, float(raw_persistence)))
            reasons.append(f"Observed thermal persistence score: {persistence_score:.1f}")
        except (ValueError, TypeError):
            persistence_score = 50.0
            reasons.append("Persistence score invalid; applied neutral default (50.0)")
    else:
        persistence_score = 50.0
        reasons.append("Persistence score missing; applied neutral default (50.0)")

    # 3. Exposure Contribution (20%)
    nearest_assets = []
    if isinstance(context, dict) and "nearest_assets" in context:
        nearest_assets = context["nearest_assets"] or []

    if nearest_assets:
        min_dist = min([a.get("distance_km", 999.0) for a in nearest_assets], default=999.0)
        if min_dist <= 5.0:
            exposure_score = 90.0
            reasons.append(f"High exposure: nearby assets detected within {min_dist:.1f} km")
        elif min_dist <= 15.0:
            exposure_score = 70.0
            reasons.append(f"Moderate exposure: nearby assets detected within {min_dist:.1f} km")
        elif min_dist <= 30.0:
            exposure_score = 45.0
            reasons.append(f"Low exposure: assets present within {min_dist:.1f} km")
        else:
            exposure_score = 20.0
            reasons.append("Minimal exposure: assets present beyond 30 km radius")
    else:
        exposure_score = 0.0
        reasons.append("No nearby assets detected in spatial context; exposure score is 0")

    # 4. Infrastructure Contribution (15%)
    infra_assets = [
        a for a in nearest_assets
        if (
            str(a.get("category", "")).lower() in ["critical_infrastructure", "industrial"]
            or str(a.get("type", "")).lower() in [
                "industrial_plant", "facility", "pipeline", "utility", "power_hub", "substation", "refinery"
            ]
        )
    ]
    if infra_assets:
        min_infra_dist = min([a.get("distance_km", 999.0) for a in infra_assets], default=999.0)
        if min_infra_dist <= 5.0:
            infrastructure_score = 100.0
            reasons.append(f"Critical infrastructure within {min_infra_dist:.1f} km proximity")
        elif min_infra_dist <= 15.0:
            infrastructure_score = 75.0
            reasons.append(f"Critical infrastructure within {min_infra_dist:.1f} km proximity")
        elif min_infra_dist <= 30.0:
            infrastructure_score = 50.0
            reasons.append(f"Critical infrastructure within {min_infra_dist:.1f} km proximity")
        else:
            infrastructure_score = 25.0
    else:
        infrastructure_score = 0.0

    # 5. Growth Contribution (10%) - Thermal Activity Proxy (Not fire propagation)
    frp = _extract_attr(incident, "frp", None)
    if frp is not None:
        try:
            frp_val = float(frp)
            if frp_val >= 60.0:
                growth_score = 90.0
                reasons.append(f"High thermal activity intensity (FRP {frp_val:.1f} MW)")
            elif frp_val >= 35.0:
                growth_score = 70.0
                reasons.append(f"Elevated thermal activity intensity (FRP {frp_val:.1f} MW)")
            elif frp_val >= 15.0:
                growth_score = 50.0
                reasons.append(f"Moderate thermal activity intensity (FRP {frp_val:.1f} MW)")
            else:
                growth_score = 25.0
        except (ValueError, TypeError):
            growth_score = 40.0
            reasons.append("Thermal activity FRP invalid; using default baseline (40.0)")
    else:
        growth_score = 40.0
        reasons.append("Thermal activity FRP missing; using default baseline (40.0)")

    # 6. Weighted Sum & Final Score
    raw_total = (
        (SEVERITY_WEIGHT * severity_score)
        + (PERSISTENCE_WEIGHT * persistence_score)
        + (EXPOSURE_WEIGHT * exposure_score)
        + (INFRASTRUCTURE_WEIGHT * infrastructure_score)
        + (GROWTH_WEIGHT * growth_score)
    )
    final_score = round(max(0.0, min(100.0, raw_total)), 1)
    band = get_severity_band(final_score)

    incident_id = _extract_attr(incident, "id", "UNKNOWN_INCIDENT")

    return {
        "incident_id": str(incident_id),
        "risk_score": final_score,
        "severity": band,
        "severity_band": band,
        "reasons": reasons,
        "factors": {
            "severity": round(severity_score, 1),
            "persistence": round(persistence_score, 1),
            "exposure": round(exposure_score, 1),
            "infrastructure": round(infrastructure_score, 1),
            "growth": round(growth_score, 1),
        },
    }
