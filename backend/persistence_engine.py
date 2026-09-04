"""
Temporal Persistence Engine for SIH26162 NTRO
Evaluates historical recurrence of thermal anomalies in the same spatial grid (375m radius).
High persistence = Stationary industrial flare / permanent facility.
Low persistence + high clustering = Seasonal crop residue burning or spreading wildfire.
"""

class PersistenceEngine:
    @staticmethod
    def calculate_persistence(hotspot_id: str, historical_observations: int, days_window: int = 60) -> dict:
        """
        Computes recurrence index (0 - 100%) across satellite passes.
        """
        recurrence_rate = min(1.0, historical_observations / max(1, days_window))
        persistence_score = round(recurrence_rate * 100, 1)

        if persistence_score >= 60:
            category = "PERMANENT / HIGH PERSISTENCE"
            is_persistent = True
            interpretation = "Hotspot consistently observed in multiple overpasses over 60 days. Strong indicator of stationary industrial thermal infrastructure (flare, furnace, kiln)."
        elif persistence_score >= 25:
            category = "RECURRENT / INTERMITTENT"
            is_persistent = True
            interpretation = "Hotspot recurs periodically (e.g. batch industrial process or active coal seam fire)."
        elif persistence_score >= 8:
            category = "EPISODIC / MULTI-DAY EVENT"
            is_persistent = False
            interpretation = "Continuous detection over consecutive days. Characteristic of active forest fire perimeter or sustained crop residue burns."
        else:
            category = "TRANSIENT / SINGLE PASS"
            is_persistent = False
            interpretation = "Detected on single satellite pass. Characteristic of sporadic stubble fire or transient thermal flash."

        return {
            "observations_count": historical_observations,
            "days_analyzed": days_window,
            "persistence_score": persistence_score,
            "category": category,
            "is_persistent": is_persistent,
            "interpretation": interpretation
        }
