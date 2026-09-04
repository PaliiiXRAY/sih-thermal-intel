"""
NASA FIRMS Thermal Anomaly Data Ingestion & Parser (SIH26162)
Handles VIIRS (375m) and MODIS (1km) Active Fire Detection Data:
Coordinates, Brightness Temperature (Kelvin), Fire Radiative Power (MW), Confidence, Date/Time.
"""

class FIRMSLoader:
    @staticmethod
    def parse_hotspots(records: list) -> list:
        """Standardizes and enriches raw thermal anomaly detections."""
        standardized = []
        for idx, r in enumerate(records):
            lat = float(r.get("latitude", r.get("lat", 0.0)))
            lon = float(r.get("longitude", r.get("lon", 0.0)))
            frp = float(r.get("frp", 15.0))  # Fire Radiative Power in MegaWatts
            brightness = float(r.get("bright_ti4", r.get("brightness", 335.0))) # Kelvin
            confidence = r.get("confidence", "nominal") # low, nominal, high
            acq_date = r.get("acq_date", "2026-09-02")
            acq_time = r.get("acq_time", "1200")
            instrument = r.get("instrument", "VIIRS-SNPP (375m)")

            standardized.append({
                "id": f"FIRMS-{idx+1:04d}",
                "lat": lat,
                "lon": lon,
                "frp": frp,
                "brightness_kelvin": brightness,
                "brightness_celsius": round(brightness - 273.15, 1),
                "confidence": confidence,
                "acq_date": acq_date,
                "acq_time": acq_time,
                "instrument": instrument
            })
        return standardized
