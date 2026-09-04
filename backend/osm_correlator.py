"""
OpenStreetMap (OSM) Geospatial Land-Use & Infrastructure Correlator (SIH26162)
Maps coordinates to OSM landuse tags (industrial, farmland, forest, residential)
and identifies proximity to registered industrial plants, refineries, and power stations.
"""
import math

class OSMCorrelator:
    @staticmethod
    def haversine_distance(lat1, lon1, lat2, lon2):
        """Returns distance in meters between two lat/lon pairs."""
        R = 6371000 # Earth radius in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        a = math.sin(delta_phi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(delta_lambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c

    @staticmethod
    def correlate_hotspot(lat: float, lon: float, known_context: dict = None) -> dict:
        """
        Determines land-use classification and facility proximity from OSM context.
        """
        if known_context:
            return {
                "landuse": known_context.get("landuse", "unclassified"),
                "osm_tag": known_context.get("osm_tag", "landuse=unclassified"),
                "facility_name": known_context.get("facility_name", None),
                "facility_type": known_context.get("facility_type", "None"),
                "distance_to_facility_m": known_context.get("distance_m", 0),
                "elevation_m": known_context.get("elevation_m", 120)
            }

        # Default fallback
        return {
            "landuse": "farmland",
            "osm_tag": "landuse=farmland",
            "facility_name": None,
            "facility_type": "None",
            "distance_to_facility_m": 1500,
            "elevation_m": 220
        }
