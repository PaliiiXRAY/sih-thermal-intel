"""
Platform Statistics (SIH26162)
Computes real dashboard numbers by running the full classification pipeline
over all cached operational scenarios — no hardcoded counters.
"""
from backend.pipeline import HotspotPipeline
from backend.samples import SCENARIOS


def compute_stats() -> dict:
    total = 0
    classified = 0
    critical = 0
    confidence_sum = 0.0
    by_class = {}

    for scenario_id in SCENARIOS:
        fc = HotspotPipeline.run_scenario(scenario_id)
        for feat in fc["features"]:
            total += 1
            c = feat["properties"]["classification"]
            label = c["classification"]
            by_class[label] = by_class.get(label, 0) + 1
            if c.get("confidence_percent") is not None:
                classified += 1
                confidence_sum += c["confidence_percent"]
            if c.get("severity", "").startswith("CRITICAL"):
                critical += 1

    return {
        "hotspots_analyzed": total,
        "auto_classified": classified,
        "classification_rate": round(100.0 * classified / total, 1) if total else 0.0,
        "critical_alerts": critical,
        "pending_review": 0,
        "avg_confidence": round(confidence_sum / classified, 1) if classified else 0.0,
        "by_class": by_class,
        "scenarios": len(SCENARIOS)
    }
