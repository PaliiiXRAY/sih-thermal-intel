"""
Realistic Geospatial Thermal Test Scenarios for SIH26162 Live Presentations
Covers 4 distinct operational categories across India.
"""

SCENARIOS = {
    "jamnagar_refinery": {
        "id": "jamnagar_refinery",
        "title": "🏭 Jamnagar Refinery Gas Flare (Gujarat)",
        "category": "Industrial Petrochemical Flare",
        "description": "Stationary gas flare detected continuously over 48 out of 60 satellite passes within Reliance/Nayara refinery complex.",
        "center": [22.3562, 69.8320],
        "zoom": 12,
        "region_name": "Jamnagar Petrochemical Complex, Gujarat",
        "hotspots": [
            {
                "latitude": 22.3585, "longitude": 69.8310, "frp": 88.4, "brightness": 358.2,
                "confidence": "high", "historical_passes": 48,
                "osm_context": {
                    "landuse": "industrial", "osm_tag": "industrial=refinery",
                    "facility_name": "Jamnagar Petroleum Refinery Complex", "facility_type": "Refinery",
                    "distance_m": 120, "elevation_m": 24
                }
            },
            {
                "latitude": 22.3610, "longitude": 69.8360, "frp": 64.2, "brightness": 346.5,
                "confidence": "high", "historical_passes": 41,
                "osm_context": {
                    "landuse": "industrial", "osm_tag": "industrial=flare_stack",
                    "facility_name": "Cracker Unit Flare Stack #3", "facility_type": "Flare Stack",
                    "distance_m": 45, "elevation_m": 30
                }
            }
        ]
    },

    "punjab_stubble": {
        "id": "punjab_stubble",
        "title": "🌾 Sangrur Paddy Stubble Burning (Punjab)",
        "category": "Agricultural Crop Residue",
        "description": "Seasonal cluster of open farm fires with low temporal persistence (1-2 days) across agricultural land during harvest season.",
        "center": [30.2450, 75.8420],
        "zoom": 11,
        "region_name": "Sangrur Agricultural District, Punjab",
        "hotspots": [
            {
                "latitude": 30.2480, "longitude": 75.8390, "frp": 24.5, "brightness": 332.0,
                "confidence": "nominal", "historical_passes": 2,
                "osm_context": {
                    "landuse": "farmland", "osm_tag": "landuse=farmland",
                    "facility_name": None, "facility_type": "Cropland",
                    "distance_m": 4200, "elevation_m": 235
                }
            },
            {
                "latitude": 30.2610, "longitude": 75.8550, "frp": 31.8, "brightness": 338.4,
                "confidence": "nominal", "historical_passes": 1,
                "osm_context": {
                    "landuse": "farmland", "osm_tag": "landuse=farmland",
                    "facility_name": None, "facility_type": "Cropland",
                    "distance_m": 3800, "elevation_m": 238
                }
            },
            {
                "latitude": 30.2310, "longitude": 75.8210, "frp": 19.2, "brightness": 329.1,
                "confidence": "nominal", "historical_passes": 1,
                "osm_context": {
                    "landuse": "farmland", "osm_tag": "landuse=farmland",
                    "facility_name": None, "facility_type": "Cropland",
                    "distance_m": 5100, "elevation_m": 232
                }
            }
        ]
    },

    "similipal_wildfire": {
        "id": "similipal_wildfire",
        "title": "🌲 Similipal Biosphere Wildfire (Odisha)",
        "category": "Forest Wildfire Spread",
        "description": "Expanding high-FRP fire perimeter moving across protected sal forest canopy with multi-day episodic progression.",
        "center": [21.8500, 86.3500],
        "zoom": 11,
        "region_name": "Similipal National Park, Mayurbhanj, Odisha",
        "hotspots": [
            {
                "latitude": 21.8540, "longitude": 86.3520, "frp": 142.6, "brightness": 369.4,
                "confidence": "high", "historical_passes": 6,
                "osm_context": {
                    "landuse": "forest", "osm_tag": "natural=wood",
                    "facility_name": "Similipal Protected Forest Reserve", "facility_type": "Forest Canopy",
                    "distance_m": 12000, "elevation_m": 780
                }
            },
            {
                "latitude": 21.8620, "longitude": 86.3680, "frp": 115.0, "brightness": 361.2,
                "confidence": "high", "historical_passes": 5,
                "osm_context": {
                    "landuse": "forest", "osm_tag": "natural=wood",
                    "facility_name": "Similipal Protected Forest Reserve", "facility_type": "Forest Canopy",
                    "distance_m": 13500, "elevation_m": 820
                }
            }
        ]
    },

    "clandestine_thermal_anomaly": {
        "id": "clandestine_thermal_anomaly",
        "title": "⚠️ Unregistered Clandestine Anomaly (Singrauli Belt)",
        "category": "Suspicious Unpermitted Thermal Infrastructure (NTRO)",
        "description": "High persistence (34 passes) thermal anomaly in unclassified scrubland with NO registered OSM industrial zoning.",
        "center": [24.1800, 82.6500],
        "zoom": 12,
        "region_name": "Singrauli Hinterland, MP/UP Border",
        "hotspots": [
            {
                "latitude": 24.1840, "longitude": 82.6530, "frp": 52.3, "brightness": 344.0,
                "confidence": "high", "historical_passes": 34,
                "osm_context": {
                    "landuse": "scrub", "osm_tag": "natural=scrub",
                    "facility_name": None, "facility_type": "Unmapped Structure",
                    "distance_m": 8500, "elevation_m": 310
                }
            }
        ]
    }
}
