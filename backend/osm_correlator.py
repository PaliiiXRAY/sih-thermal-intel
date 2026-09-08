"""
OpenStreetMap (OSM) Geospatial Land-Use & Infrastructure Correlator (SIH26162)
Maps coordinates to OSM landuse tags (industrial, farmland, forest, residential)
and identifies proximity to registered industrial plants, refineries, and power stations.
"""
import math
import json
import urllib.request
import urllib.parse

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
SEARCH_RADIUS_M = 1000  # facility / landuse query radius around a hotspot


class OSMCorrelator:
    @staticmethod
    def fetch_live_context(lat: float, lon: float, timeout: int = 20) -> dict:
        """
        Live Overpass API query: finds the dominant landuse polygon and nearest
        registered industrial facility within SEARCH_RADIUS_M of the hotspot.
        Returns the same schema as correlate_hotspot(); raises on network failure
        so the caller can fall back to cached context.
        """
        query = f"""
        [out:json][timeout:15];
        (
          way(around:{SEARCH_RADIUS_M},{lat},{lon})["landuse"];
          way(around:{SEARCH_RADIUS_M},{lat},{lon})["natural"~"wood|scrub"];
          node(around:{SEARCH_RADIUS_M},{lat},{lon})["man_made"~"chimney|flare|works"];
          way(around:{SEARCH_RADIUS_M},{lat},{lon})["man_made"~"chimney|flare|works"];
          nwr(around:{SEARCH_RADIUS_M},{lat},{lon})["industrial"~"refinery|oil|gas|power|steel|chemical|mining"];
        );
        out center tags;
        """
        req = urllib.request.Request(
            OVERPASS_URL,
            data=("data=" + urllib.parse.quote(query)).encode("utf-8"),
            headers={"User-Agent": "AeroThermal-SIH26162/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))

        elements = data.get("elements", [])
        landuse, osm_tag = "unclassified", "landuse=unclassified"
        facility_name, facility_type, best_dist = None, "None", SEARCH_RADIUS_M * 2

        for el in elements:
            tags = el.get("tags", {})
            el_lat = el.get("lat") or el.get("center", {}).get("lat")
            el_lon = el.get("lon") or el.get("center", {}).get("lon")
            if "landuse" in tags or "natural" in tags:
                landuse = tags.get("landuse") or tags.get("natural") or landuse
                osm_tag = f"{'landuse' if 'landuse' in tags else 'natural'}={landuse}"
            if el_lat is not None and el_lon is not None and tags.get("industrial") or tags.get("man_made"):
                d = OSMCorrelator.haversine_distance(lat, lon, el_lat, el_lon)
                if d < best_dist:
                    best_dist = d
                    facility_name = tags.get("name", "Unnamed Industrial Feature")
                    facility_type = tags.get("industrial") or tags.get("man_made")

        return {
            "landuse": landuse,
            "osm_tag": osm_tag,
            "facility_name": facility_name,
            "facility_type": facility_type,
            "distance_to_facility_m": round(best_dist, 1),
            "live": True
        }

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
