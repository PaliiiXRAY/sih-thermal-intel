# tests/test_persistence_scorer.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.persistence_scorer import compute_persistence_score

def test_permanent_pattern():
    obs = [{"lat": 22.3585, "lon": 69.8310, "timestamp": f"2026-08-{d:02d}T12:00:00Z"}
           for d in range(1, 51)]
    result = compute_persistence_score(22.3585, 69.8310, obs)
    assert result["score"] >= 60
    assert result["pattern_label"] == "PERMANENT"

def test_transient_pattern():
    obs = [{"lat": 22.3585, "lon": 69.8310, "timestamp": "2026-09-01T12:00:00Z"}]
    result = compute_persistence_score(22.3585, 69.8310, obs)
    assert result["score"] < 8
    assert result["pattern_label"] == "TRANSIENT"

def test_episodic_pattern():
    obs = [{"lat": 22.3585, "lon": 69.8310, "timestamp": f"2026-09-{d:02d}T12:00:00Z"}
           for d in range(1, 6)]
    result = compute_persistence_score(22.3585, 69.8310, obs)
    assert 8 <= result["score"] < 25
    assert result["pattern_label"] == "EPISODIC"

def test_spatial_filter():
    obs = [
        {"lat": 22.3585, "lon": 69.8310, "timestamp": "2026-09-01T12:00:00Z"},
        {"lat": 23.0000, "lon": 70.0000, "timestamp": "2026-09-02T12:00:00Z"},
    ]
    result = compute_persistence_score(22.3585, 69.8310, obs, spatial_tolerance_m=375)
    assert result["spatial_matches"] == 1
    assert result["total_observations"] == 2

def test_empty_observations():
    result = compute_persistence_score(22.3585, 69.8310, [])
    assert result["score"] == 0
    assert result["pattern_label"] == "TRANSIENT"

def test_score_range():
    obs = [{"lat": 22.3585, "lon": 69.8310, "timestamp": f"2026-08-{d:02d}T12:00:00Z"}
           for d in range(1, 61)]
    result = compute_persistence_score(22.3585, 69.8310, obs)
    assert 0 <= result["score"] <= 100

if __name__ == "__main__":
    test_permanent_pattern()
    test_transient_pattern()
    test_episodic_pattern()
    test_spatial_filter()
    test_empty_observations()
    test_score_range()
    print("All persistence_scorer tests passed")
