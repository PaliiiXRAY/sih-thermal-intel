"""
FIRMS Thermal Anomaly Cache with Validation and Dedup.
Normalizes records to: lat, lon, brightness_kelvin, frp, acq_date, acq_time, satellite, confidence.
Deduplicates on (lat, lon, acq_date, acq_time) within floating-point tolerance.
"""

class FIRMSCache:
    def __init__(self):
        self._records = []
        self._seen = set()

    def add(self, record: dict) -> bool:
        lat = record.get("lat", record.get("latitude", None))
        lon = record.get("lon", record.get("longitude", None))
        if lat is None or lon is None:
            return False
        try:
            lat, lon = float(lat), float(lon)
        except (TypeError, ValueError):
            return False
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            return False

        frp = float(record.get("frp", record.get("fire_radiative_power", 0)) or 0)
        brightness = float(record.get("brightness_kelvin", record.get("bright_ti4", record.get("brightness", 0))) or 0)
        if frp < 0 or brightness < 0:
            return False

        acq_date = record.get("acq_date", "unknown")
        acq_time = record.get("acq_time", "0000")

        key = (round(lat, 4), round(lon, 4), acq_date, acq_time)
        if key in self._seen:
            return False
        self._seen.add(key)

        self._records.append({
            "lat": lat, "lon": lon,
            "brightness_kelvin": brightness, "frp": frp,
            "acq_date": acq_date, "acq_time": acq_time,
            "satellite": record.get("satellite", record.get("instrument", "unknown")),
            "confidence": record.get("confidence", "nominal"),
        })
        return True

    def query(self, bbox=None, date_range=None) -> list:
        results = self._records
        if bbox:
            south, west, north, east = bbox
            results = [r for r in results if south <= r["lat"] <= north and west <= r["lon"] <= east]
        if date_range:
            start, end = date_range
            results = [r for r in results if start <= r["acq_date"] <= end]
        return results

    def count(self) -> int:
        return len(self._records)
