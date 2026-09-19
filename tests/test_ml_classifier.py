"""
Unit tests for deterministic ML classifier service (Phase 3A).
"""
import pytest
from backend.app.services.ml.classifier import classify, CANONICAL_CLASSES, ClassificationResult
from backend.app.models.incident import Incident


def test_deterministic_repeated_input():
    """1. Verify same input produces exact same output repeatedly."""
    incident_data = {
        "frp": 65.0,
        "persistence_score": 75.0,
        "landcover": "industrial",
        "tags": ["warehouse"]
    }
    result1 = classify(incident_data)
    result2 = classify(incident_data)
    result3 = classify(incident_data)

    assert result1 == result2 == result3
    assert result1["class"] == "INDUSTRIAL_FIRE"


def test_industrial_fire_like_scenario():
    """2. Verify industrial-fire-like scenario classification."""
    incident_dict = {
        "frp": 75.0,
        "persistence_score": 60.0,
        "tags": ["industrial", "factory_complex"]
    }
    res = classify(incident_dict)
    assert res["class"] == "INDUSTRIAL_FIRE"
    assert res["confidence"] >= 0.80
    assert len(res["evidence"]) > 0
    assert any("industrial" in e.lower() or "frp" in e.lower() for e in res["evidence"])


def test_gas_flare_like_scenario():
    """3. Verify gas-flare-like scenario classification."""
    incident_dict = {
        "frp": 35.0,
        "persistence_score": 90.0,
        "tags": ["refinery_flare", "petrochemical"]
    }
    res = classify(incident_dict)
    assert res["class"] == "GAS_FLARE"
    assert res["confidence"] >= 0.75
    assert len(res["evidence"]) > 0
    assert any("gas flare" in e.lower() or "persistence" in e.lower() for e in res["evidence"])


def test_wildfire_like_scenario():
    """4. Verify wildfire-like scenario classification."""
    incident_dict = {
        "frp": 85.0,
        "persistence_score": 30.0,
        "landcover": "forest",
        "detection_confidence": "HIGH"
    }
    res = classify(incident_dict)
    assert res["class"] == "WILDFIRE"
    assert res["confidence"] >= 0.70
    assert len(res["evidence"]) > 0
    assert any("forest" in e.lower() or "vegetation" in e.lower() for e in res["evidence"])


def test_crop_burning_like_scenario():
    """5. Verify crop-burning-like scenario classification."""
    incident_dict = {
        "frp": 15.0,
        "persistence_score": 20.0,
        "landcover": "cropland",
        "tags": ["stubble_burning"]
    }
    res = classify(incident_dict)
    assert res["class"] == "CROP_BURNING"
    assert res["confidence"] >= 0.70
    assert len(res["evidence"]) > 0
    assert any("cropland" in e.lower() or "agricultural" in e.lower() for e in res["evidence"])


def test_mining_other_scenario():
    """6. Verify mining/other scenario classification."""
    incident_dict = {
        "persistence_score": 50.0,
        "tags": ["mining", "open_pit"]
    }
    res = classify(incident_dict)
    assert res["class"] == "MINING_OTHER"
    assert res["confidence"] >= 0.75
    assert len(res["evidence"]) > 0
    assert any("mining" in e.lower() for e in res["evidence"])


def test_insufficient_evidence_unknown_guardrail():
    """7. Verify sparse or empty inputs fall back safely to UNKNOWN."""
    empty_incident = {}
    res = classify(empty_incident)
    assert res["class"] == "UNKNOWN"
    assert res["confidence"] == 0.35
    assert res["evidence"] == ["Insufficient contextual evidence for a specific class"]


def test_confidence_range():
    """8. Verify classification confidence is strictly within range 0.0 to 1.0."""
    test_cases = [
        {},
        {"frp": 100.0, "persistence_score": 90.0, "tags": ["industrial"]},
        {"frp": 5.0, "persistence_score": 10.0, "landcover": "cropland"},
        {"tags": ["mining_other"]}
    ]
    for case in test_cases:
        res = classify(case)
        assert 0.0 <= res["confidence"] <= 1.0


def test_canonical_class_vocabulary():
    """9. Verify output class strictly belongs to the frozen canonical vocabulary."""
    test_inputs = [
        {"tags": ["industrial"]},
        {"tags": ["gas_flare"]},
        {"tags": ["wildfire"]},
        {"tags": ["crop_burning"]},
        {"tags": ["mining"]},
        {}
    ]
    for inp in test_inputs:
        res = classify(inp)
        assert res["class"] in CANONICAL_CLASSES


def test_evidence_is_returned():
    """10. Verify evidence is always returned as a non-empty list of strings."""
    res = classify({"frp": 45.0, "landcover": "forest"})
    assert isinstance(res["evidence"], list)
    assert len(res["evidence"]) > 0
    assert all(isinstance(item, str) for item in res["evidence"])


def test_classification_with_orm_incident_model():
    """Verify classify accepts SQLAlchemy Incident ORM instance safely."""
    inc = Incident(
        id="INC-TEST-99",
        latitude=21.1458,
        longitude=79.0882,
        persistence_score=85.0,
        detection_confidence="HIGH",
        explanation={"frp": 55.0, "tags": ["industrial", "refinery"]}
    )
    res = classify(inc)
    assert res["class"] in CANONICAL_CLASSES
    assert 0.0 <= res["confidence"] <= 1.0
    assert len(res["evidence"]) > 0
