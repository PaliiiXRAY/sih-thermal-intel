"""
AeroThermal Live Hotspot Pipeline (SIH26162)
End-to-end path required by the problem statement:
  NASA FIRMS hotspot detections -> OSM context (live Overpass or cached) ->
  temporal persistence -> ESA WorldCover land-cover -> AI classification.

Output is a classified, map-ready GeoJSON FeatureCollection + evidence dossiers
for the GIS overlay deliverable.
"""
import json

from backend.firms_api import FIRMSApiClient
from backend.firms_loader import FIRMSLoader
from backend.osm_correlator import OSMCorrelator
from backend.persistence_engine import PersistenceEngine
from backend.landcover import LandCoverResolver
from backend.classifier import ThermalClassifier
from backend.samples import SCENARIOS


class HotspotPipeline:
    @staticmethod
    def classify_firms_rows(rows: list, use_live_osm: bool = False) -> dict:
        """Classify a list of raw FIRMS CSV rows into map-ready features."""
        hotspots = FIRMSLoader.parse_hotspots(rows)
        features = []
        for hs, raw in zip(hotspots, rows):
            # FIRMSLoader standardizes core fields; carry the archive count through
            hs["historical_passes"] = int(raw.get("historical_passes", 2))

            context = raw.get("osm_context")
            if use_live_osm:
                try:
                    context = OSMCorrelator.fetch_live_context(hs["lat"], hs["lon"])
                except Exception:
                    pass  # fall back to cached scenario context

            osm_data = OSMCorrelator.correlate_hotspot(hs["lat"], hs["lon"], context)
            persistence = PersistenceEngine.calculate_persistence(
                hs["id"], hs["historical_passes"])
            landcover = LandCoverResolver.resolve(osm_data)
            result = ThermalClassifier.classify(hs, osm_data, persistence)

            features.append({
                "type": "Feature",
                "geometry": {"type": "Point",
                             "coordinates": [hs["lon"], hs["lat"]]},
                "properties": {
                    "id": hs["id"],
                    "firms": hs,
                    "osm": osm_data,
                    "persistence": persistence,
                    "landcover": landcover,
                    "classification": result
                }
            })
        return {
            "type": "FeatureCollection",
            "feature_count": len(features),
            "features": features
        }

    @staticmethod
    def run_live(map_key: str, bbox: tuple, source: str = "viirs",
                 day_range: int = 1, use_live_osm: bool = False) -> dict:
        """Live FIRMS ingestion for a bounding box (south, west, north, east)."""
        rows = FIRMSApiClient.fetch_area_hotspots(
            map_key, bbox, source=source, day_range=day_range)
        if not rows:
            return {"type": "FeatureCollection", "feature_count": 0, "features": [],
                    "note": "No thermal anomalies detected in the requested area/time window."}
        fc = HotspotPipeline.classify_firms_rows(rows, use_live_osm=use_live_osm)
        fc["source"] = f"NASA FIRMS {source.upper()} NRT, last {day_range} day(s)"
        return fc

    @staticmethod
    def run_scenario(scenario_id: str, use_live_osm: bool = False) -> dict:
        """Run the identical pipeline on a pre-cached operational scenario (demo mode)."""
        scenario = SCENARIOS.get(scenario_id)
        if not scenario:
            return {"error": f"Unknown scenario '{scenario_id}'",
                    "available": list(SCENARIOS.keys())}
        rows = []
        for hs in scenario["hotspots"]:
            row = {
                "latitude": hs["latitude"], "longitude": hs["longitude"],
                "frp": hs["frp"], "brightness": hs["brightness"],
                "confidence": hs["confidence"], "acq_date": "2026-09-09",
                "acq_time": "0430", "instrument": "VIIRS-SNPP (375m)",
                "historical_passes": hs["historical_passes"]
            }
            if not use_live_osm:
                row["osm_context"] = hs["osm_context"]
            rows.append(row)

        fc = HotspotPipeline.classify_firms_rows(rows, use_live_osm=use_live_osm)
        fc["source"] = f"Cached scenario: {scenario['title']}"
        fc["scenario"] = {"id": scenario_id, "title": scenario["title"],
                          "category": scenario["category"],
                          "region_name": scenario["region_name"]}
        return fc


if __name__ == "__main__":
    demo = HotspotPipeline.run_scenario("jamnagar_refinery")
    print(json.dumps(demo, indent=2)[:2000])
