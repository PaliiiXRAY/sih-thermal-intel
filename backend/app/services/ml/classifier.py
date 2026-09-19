"""
Deterministic and ML (XGBoost) Classifier Service for FireSense.
Establishes the clean ML classification contract, feature extraction, XGBoost inference,
and deterministic fallback baseline logic.
"""
import logging
from typing import Any, Dict, List, Optional, Union

from backend.app.services.ml.features import extract_features
from backend.app.services.ml.model import predict_xgboost

logger = logging.getLogger("firesense.ml")

CANONICAL_CLASSES = {
    "INDUSTRIAL_FIRE",
    "GAS_FLARE",
    "WILDFIRE",
    "CROP_BURNING",
    "MINING_OTHER",
    "UNKNOWN",
}


class ClassificationResult:
    """Classification result matching team contract."""

    def __init__(self, classification_class: str, confidence: float, evidence: List[str]):
        if classification_class not in CANONICAL_CLASSES:
            raise ValueError(f"Invalid classification class: {classification_class}. Must be one of {CANONICAL_CLASSES}")
        
        # Clamp confidence to [0.0, 1.0]
        clamped_confidence = max(0.0, min(1.0, float(confidence)))
        
        self.classification_class = classification_class
        self.confidence = round(clamped_confidence, 4)
        self.evidence = evidence if isinstance(evidence, list) else [str(evidence)]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "class": self.classification_class,
            "confidence": self.confidence,
            "evidence": self.evidence,
        }


def _extract_feature(obj: Any, key: str, default: Any = None) -> Any:
    """Safely extract feature from dictionary or object attributes including nested explanation."""
    if isinstance(obj, dict):
        if key in obj and obj[key] is not None:
            return obj[key]
        explanation = obj.get("explanation")
        if isinstance(explanation, dict) and key in explanation and explanation[key] is not None:
            return explanation[key]
        return default

    # Attribute lookup on ORM or Pydantic models
    if hasattr(obj, key):
        val = getattr(obj, key)
        if val is not None:
            return val
    if hasattr(obj, "explanation"):
        explanation = getattr(obj, "explanation")
        if isinstance(explanation, dict) and key in explanation and explanation[key] is not None:
            return explanation[key]

    return default


def classify_deterministic(incident: Union[Any, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Classify an incident using deterministic rule-based feature logic (Mandatory Fallback).
    """
    frp = _extract_feature(incident, "frp", None)
    persistence = _extract_feature(incident, "persistence_score", None)
    detection_conf = _extract_feature(incident, "detection_confidence", None)
    landcover = _extract_feature(incident, "landcover", None)
    facility_type = _extract_feature(incident, "facility_type", None)
    site_category = _extract_feature(incident, "site_category", None)
    tags = _extract_feature(incident, "tags", [])
    evidence_tags = _extract_feature(incident, "evidence", [])
    classification_hint = _extract_feature(incident, "classification", None)

    if not isinstance(tags, list):
        tags = []
    if not isinstance(evidence_tags, list):
        evidence_tags = []

    combined_tags = [str(t).lower() for t in (tags + evidence_tags)]
    if landcover:
        combined_tags.append(str(landcover).lower())
    if facility_type:
        combined_tags.append(str(facility_type).lower())
    if site_category:
        combined_tags.append(str(site_category).lower())
    if classification_hint:
        combined_tags.append(str(classification_hint).lower())

    # 1. GAS_FLARE
    is_gas_flare_tag = any(t in ["gas_flare", "flare_stack", "petrochemical", "refinery_flare"] for t in combined_tags)
    if (persistence is not None and persistence >= 80.0 and is_gas_flare_tag) or (
        is_gas_flare_tag and (frp is None or frp >= 15.0)
    ) or (persistence is not None and persistence >= 85.0 and (frp is not None and 10.0 <= frp <= 100.0) and "forest" not in combined_tags):
        evidence = []
        if persistence is not None and persistence >= 80.0:
            evidence.append(f"High thermal persistence score ({persistence:.1f}) indicating stationary continuous heat source")
        if is_gas_flare_tag:
            evidence.append("Facility tag or landcover matches gas flare / refinery infrastructure signature")
        if frp is not None:
            evidence.append(f"Thermal intensity FRP {frp:.1f} MW within typical gas flaring operating range")
        
        confidence = 0.88 if (persistence is not None and persistence >= 80.0 and is_gas_flare_tag) else 0.78
        res = ClassificationResult("GAS_FLARE", confidence, evidence).to_dict()
        res["label_source"] = "DETERMINISTIC_RULES"
        res["rule_version"] = "v1"
        return res

    # 2. INDUSTRIAL_FIRE
    is_industrial_tag = any(t in ["industrial", "industrial_fire", "factory", "refinery", "warehouse", "manufacturing", "chemical_plant"] for t in combined_tags)
    if (is_industrial_tag and (frp is None or frp >= 25.0)) or (
        frp is not None and frp >= 50.0 and persistence is not None and persistence >= 50.0
    ):
        evidence = []
        if frp is not None and frp >= 25.0:
            evidence.append(f"High Fire Radiative Power (FRP {frp:.1f} MW)")
        if persistence is not None and persistence >= 50.0:
            evidence.append(f"Elevated thermal persistence score ({persistence:.1f})")
        if is_industrial_tag:
            evidence.append("Location landcover/tags match industrial or manufacturing zone")

        confidence = 0.90 if (is_industrial_tag and frp is not None and frp >= 50.0) else 0.80
        res = ClassificationResult("INDUSTRIAL_FIRE", confidence, evidence).to_dict()
        res["label_source"] = "DETERMINISTIC_RULES"
        res["rule_version"] = "v1"
        return res

    # 3. WILDFIRE
    is_wildfire_tag = any(t in ["wildfire", "forest", "wildland", "woodland", "shrubland", "forest_landcover", "vegetation"] for t in combined_tags)
    if is_wildfire_tag or (frp is not None and frp >= 40.0 and (persistence is None or persistence < 80.0) and not is_industrial_tag):
        evidence = []
        if is_wildfire_tag:
            evidence.append("Landcover or location tag indicates forest/wildland vegetation cover")
        if frp is not None:
            evidence.append(f"Significant thermal radiative intensity (FRP {frp:.1f} MW)")
        if detection_conf:
            evidence.append(f"Satellite detection confidence level: {detection_conf}")

        confidence = 0.85 if (is_wildfire_tag and frp is not None and frp >= 40.0) else 0.75
        res = ClassificationResult("WILDFIRE", confidence, evidence).to_dict()
        res["label_source"] = "DETERMINISTIC_RULES"
        res["rule_version"] = "v1"
        return res

    # 4. CROP_BURNING
    is_crop_tag = any(t in ["crop_burning", "stubble_burning", "cropland", "agricultural", "farm", "field"] for t in combined_tags)
    if is_crop_tag or (
        frp is not None and frp < 40.0 and persistence is not None and persistence < 40.0 and not is_wildfire_tag
    ):
        evidence = []
        if is_crop_tag:
            evidence.append("Agricultural or cropland landcover classification")
        if persistence is not None and persistence < 40.0:
            evidence.append(f"Low thermal persistence score ({persistence:.1f}) consistent with transient biomass burning")
        if frp is not None:
            evidence.append(f"Moderate thermal intensity (FRP {frp:.1f} MW)")

        confidence = 0.82 if (is_crop_tag and persistence is not None and persistence < 40.0) else 0.70
        res = ClassificationResult("CROP_BURNING", confidence, evidence).to_dict()
        res["label_source"] = "DETERMINISTIC_RULES"
        res["rule_version"] = "v1"
        return res

    # 5. MINING_OTHER
    is_mining_tag = any(t in ["mining", "mining_other", "quarry", "open_pit", "coal_field", "extraction"] for t in combined_tags)
    if is_mining_tag:
        evidence = [
            "Thermal signature located within designated mining or extraction facility boundary"
        ]
        if persistence is not None:
            evidence.append(f"Observed thermal persistence score ({persistence:.1f})")

        confidence = 0.80
        res = ClassificationResult("MINING_OTHER", confidence, evidence).to_dict()
        res["label_source"] = "DETERMINISTIC_RULES"
        res["rule_version"] = "v1"
        return res

    # 6. UNKNOWN (Guardrail)
    res = ClassificationResult(
        "UNKNOWN",
        0.35,
        ["Insufficient contextual evidence for a specific class"]
    ).to_dict()
    res["label_source"] = "DETERMINISTIC_RULES"
    res["rule_version"] = "v1"
    return res


def classify(
    incident: Union[Any, Dict[str, Any]],
    context: Optional[Dict[str, Any]] = None,
    force_fallback: bool = False,
) -> Dict[str, Any]:
    """
    Classify an incident using XGBoost ML model with deterministic rule fallback.

    Args:
        incident: Incident ORM model, Pydantic model, or feature dictionary.
        context: Optional spatial context dictionary.
        force_fallback: If True, bypasses XGBoost and forces deterministic fallback.

    Returns:
        Classification result dictionary matching frozen API contract.
    """
    if not force_fallback:
        try:
            feature_dict = extract_features(incident, context)
            ml_result = predict_xgboost(feature_dict)
            if ml_result is not None:
                return ml_result
        except Exception as e:
            logger.warning(f"XGBoost classification failed ({e}); invoking deterministic fallback.")

    # Fallback to deterministic rule-based classifier
    return classify_deterministic(incident)

