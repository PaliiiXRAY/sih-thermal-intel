# tests/test_failure_drill.py
"""Failure drill tests: bad records, missing context, invalid transitions."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.firms_cache import FIRMSCache
from backend.state_machine import can_transition, validate_and_transition
from backend.alerts import build_alert, dispatch_alert
from backend.persistence_scorer import compute_persistence_score

def test_invalid_firms_record_rejected():
    cache = FIRMSCache()
    ok = cache.add({"lat": 999, "lon": 69.83, "brightness_kelvin": 358, "frp": 88})
    assert ok is False
    assert cache.count() == 0

def test_missing_optional_firms_fields_accepted():
    cache = FIRMSCache()
    ok = cache.add({"lat": 22.35, "lon": 69.83})
    assert ok is True
    assert cache.count() == 1

def test_negative_frp_rejected():
    cache = FIRMSCache()
    ok = cache.add({"lat": 22.35, "lon": 69.83, "frp": -10, "brightness_kelvin": 300})
    assert ok is False

def test_alert_nonexistent_incident():
    try:
        dispatch_alert("INC-NONEXISTENT-999")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "not found" in str(e)

def test_invalid_transition_detected_to_resolved():
    try:
        validate_and_transition("INC-TEST", "DETECTED", "RESOLVED", "system")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "DETECTED" in str(e) and "RESOLVED" in str(e)

def test_invalid_transition_resolved_to_detected():
    try:
        validate_and_transition("INC-TEST", "RESOLVED", "DETECTED", "system")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "RESOLVED" in str(e) and "DETECTED" in str(e)

def test_invalid_transition_en_route_to_resolved():
    assert not can_transition("EN_ROUTE", "RESOLVED")

def test_persistence_empty_observations():
    result = compute_persistence_score(22.3585, 69.8310, [])
    assert result["score"] == 0
    assert result["pattern_label"] == "TRANSIENT"

def test_persistence_far_observations():
    obs = [{"lat": 0.0, "lon": 0.0, "timestamp": "2026-09-01T12:00:00Z"}]
    result = compute_persistence_score(22.3585, 69.8310, obs, spatial_tolerance_m=375)
    assert result["spatial_matches"] == 0

def test_build_alert_with_minimal_incident():
    incident = {"id": "INC-MINIMAL"}
    alert = build_alert(incident)
    assert alert["incident_id"] == "INC-MINIMAL"
    assert alert["simulated"] is True
    assert alert["classification"] == "UNKNOWN"

if __name__ == "__main__":
    test_invalid_firms_record_rejected()
    test_missing_optional_firms_fields_accepted()
    test_negative_frp_rejected()
    test_alert_nonexistent_incident()
    test_invalid_transition_detected_to_resolved()
    test_invalid_transition_resolved_to_detected()
    test_invalid_transition_en_route_to_resolved()
    test_persistence_empty_observations()
    test_persistence_far_observations()
    test_build_alert_with_minimal_incident()
    print("All failure_drill tests passed")
