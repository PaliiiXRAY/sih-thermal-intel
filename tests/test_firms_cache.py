# tests/test_firms_cache.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.firms_cache import FIRMSCache

def test_add_valid_record():
    cache = FIRMSCache()
    ok = cache.add({"lat": 22.35, "lon": 69.83, "brightness_kelvin": 358.2,
                     "frp": 88.4, "acq_date": "2026-09-09", "acq_time": "0430",
                     "satellite": "VIIRS-SNPP", "confidence": "high"})
    assert ok is True
    assert cache.count() == 1

def test_reject_invalid_lat():
    cache = FIRMSCache()
    ok = cache.add({"lat": 999, "lon": 69.83, "brightness_kelvin": 358, "frp": 88})
    assert ok is False
    assert cache.count() == 0

def test_reject_negative_frp():
    cache = FIRMSCache()
    ok = cache.add({"lat": 22.35, "lon": 69.83, "brightness_kelvin": 358, "frp": -5})
    assert ok is False

def test_dedup_same_record():
    cache = FIRMSCache()
    rec = {"lat": 22.35, "lon": 69.83, "brightness_kelvin": 358, "frp": 88,
           "acq_date": "2026-09-09", "acq_time": "0430"}
    cache.add(rec)
    ok = cache.add(rec)
    assert ok is False
    assert cache.count() == 1

def test_different_time_not_deduped():
    cache = FIRMSCache()
    cache.add({"lat": 22.35, "lon": 69.83, "brightness_kelvin": 358, "frp": 88,
               "acq_date": "2026-09-09", "acq_time": "0430"})
    ok = cache.add({"lat": 22.35, "lon": 69.83, "brightness_kelvin": 358, "frp": 88,
                     "acq_date": "2026-09-09", "acq_time": "1630"})
    assert ok is True
    assert cache.count() == 2

def test_query_bbox():
    cache = FIRMSCache()
    cache.add({"lat": 22.35, "lon": 69.83, "brightness_kelvin": 358, "frp": 88,
               "acq_date": "2026-09-09", "acq_time": "0430"})
    cache.add({"lat": 30.25, "lon": 75.84, "brightness_kelvin": 332, "frp": 24,
               "acq_date": "2026-09-09", "acq_time": "0430"})
    results = cache.query(bbox=(22.0, 69.0, 23.0, 70.0))
    assert len(results) == 1
    assert results[0]["lat"] == 22.35

def test_missing_optional_fields_accepted():
    cache = FIRMSCache()
    ok = cache.add({"lat": 22.35, "lon": 69.83})
    assert ok is True

if __name__ == "__main__":
    test_add_valid_record()
    test_reject_invalid_lat()
    test_reject_negative_frp()
    test_dedup_same_record()
    test_different_time_not_deduped()
    test_query_bbox()
    test_missing_optional_fields_accepted()
    print("All firms_cache tests passed")
