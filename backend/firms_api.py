"""
Live NASA FIRMS API Client (SIH26162)
Fetches real VIIRS/MODIS active fire hotspot detections from:
https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/{SOURCE}/{AREA}/{DAY_RANGE}/{DATE}

A free MAP_KEY is obtained at https://firms.modap.eosdis.nasa.gov/api/map_key/
If no key is configured, callers fall back to the pre-cached sample scenarios.
"""
import io
import csv
import urllib.request
from urllib.parse import urlencode

FIRMS_AREA_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"

SOURCES = {
    "viirs": "VIIRS_SNPP_NRT",       # 375m, primary sensor for the PS
    "viirs_noaa": "VIIRS_NOAA20_NRT",
    "modis": "MODIS_NRT"             # 1km
}


class FIRMSApiClient:
    @staticmethod
    def fetch_area_hotspots(map_key: str, bbox: tuple, source: str = "viirs",
                            day_range: int = 1, date: str = None, timeout: int = 20) -> list:
        """
        bbox = (south, west, north, east). Returns raw FIRMS rows as dicts,
        ready for FIRMSLoader.parse_hotspots().
        """
        south, west, north, east = bbox
        src = SOURCES.get(source.lower(), SOURCES["viirs"])
        area = f"{west},{south},{east},{north}"
        params = [map_key, src, area, str(day_range)]
        if date:
            params.append(date)
        url = f"{FIRMS_AREA_URL}/{'/'.join(params)}"

        req = urllib.request.Request(url, headers={"User-Agent": "AeroThermal-SIH26162/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8", errors="replace")

        if not text or text.lstrip().startswith("Invalid"):
            raise ValueError(f"FIRMS API rejected the request: {text[:120]}")

        rows = []
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            rows.append(dict(row))
        return rows

    @staticmethod
    def fetch_country_hotspots(map_key: str, source: str = "viirs",
                               day_range: int = 1, timeout: int = 30) -> list:
        """India bounding box (roughly 6N-36N, 68E-98E) for national monitoring."""
        return FIRMSApiClient.fetch_area_hotspots(
            map_key, (6.0, 68.0, 36.0, 98.0), source=source,
            day_range=day_range, timeout=timeout)
