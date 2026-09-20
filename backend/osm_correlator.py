"""
OpenStreetMap (OSM) Geospatial Land-Use & Infrastructure Correlator (SIH26162)
Maps coordinates to OSM landuse tags (industrial, farmland, forest, residential)
and identifies proximity to registered industrial plants, refineries, and power stations.
"""
import math
import json
import os
import urllib.request
import urllib.parse
try:
    import psycopg2
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
SEARCH_RADIUS_M = 1000  # facility / landuse query radius around a hotspot

# PostGIS is opt-in and closed by default: credentials are never hardcoded.
# Only when a deployment supplies FIRESENSE_SPATIAL_DB_DSN (e.g.
# "dbname=spatial_db user=... password=... host=...") does fetch_live_context
# attempt the local zero-latency query; otherwise it goes straight to Overpass.
SPATIAL_DB_DSN = os.environ.get("FIRESENSE_SPATIAL_DB_DSN", "")


class OSMCorrelator:
    @staticmethod
    def fetch_live_context(lat: float, lon: float, timeout: int = 20) -> dict:
        """
        Live context query. First attempts local PostGIS database (zero-latency).
        If database is unavailable or missing, gracefully falls back to the Overpass API.
        """
        if HAS_PSYCOPG2 and SPATIAL_DB_DSN:
            try:
                # 2-second timeout so it fails fast if DB is not running
                conn = psycopg2.connect(SPATIAL_DB_DSN, connect_timeout=2)
                cursor = conn.cursor()
                
                # Query for nearest industrial feature
                query_fac = """
                    SELECT tags->'name', tags->'industrial', tags->'man_made',
                           ST_Distance(way::geography, ST_MakePoint(%s, %s)::geography) as dist
                    FROM planet_osm_polygon
                    WHERE ST_DWithin(way::geography, ST_MakePoint(%s, %s)::geography, %s)
                      AND (tags ? 'industrial' OR tags ? 'man_made')
                    ORDER BY dist ASC LIMIT 1;
                """
                cursor.execute(query_fac, (lon, lat, lon, lat, SEARCH_RADIUS_M))
                facility_row = cursor.fetchone()
                
                # Query for landuse
                query_lu = """
                    SELECT tags->'landuse', tags->'natural'
                    FROM planet_osm_polygon
                    WHERE ST_Intersects(way::geography, ST_MakePoint(%s, %s)::geography)
                      AND (tags ? 'landuse' OR tags ? 'natural')
                    LIMIT 1;
                """
                cursor.execute(query_lu, (lon, lat))
                lu_row = cursor.fetchone()
                
                conn.close()
                
                facility_name = None
                facility_type = "None"
                best_dist = SEARCH_RADIUS_M * 2
                if facility_row:
                    name, ind, man, dist = facility_row
                    facility_name = name or "Unnamed Industrial Feature"
                    facility_type = ind or man or "industrial"
                    best_dist = float(dist)
                
                landuse = "unclassified"
                osm_tag = "landuse=unclassified"
                if lu_row:
                    lu, nat = lu_row
                    landuse = lu or nat or "unclassified"
                    osm_tag = f"{'landuse' if lu else 'natural'}={landuse}"

                return {
                    "landuse": landuse,
                    "osm_tag": osm_tag,
                    "facility_name": facility_name,
                    "facility_type": facility_type,
                    "distance_to_facility_m": round(best_dist, 1),
                    "live": True
                }
            except Exception as e:
                print(f"[PostGIS] Connection or query failed ({e}). Falling back to Overpass API...")
                pass
                
        # --- Fallback to Original HTTP Overpass API ---
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
