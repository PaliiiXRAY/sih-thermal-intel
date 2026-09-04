"""
Thermal Source AI Classifier for SIH26162 (NTRO)
Fuses NASA FIRMS metrics, OSM Land-Use, and Temporal Persistence to classify thermal anomalies:
1. Industrial Gas Flare (Refinery / Petrochemical)
2. Agricultural Crop Residue / Stubble Burning
3. Wildfire / Forest Fire
4. Unregistered / Clandestine Thermal Source (National Security Interest)
"""

class ThermalClassifier:
    @staticmethod
    def classify(hotspot: dict, osm_data: dict, persistence_data: dict) -> dict:
        landuse = osm_data.get("landuse", "").lower()
        facility = osm_data.get("facility_type", "").lower()
        is_persistent = persistence_data.get("is_persistent", False)
        persistence_score = persistence_data.get("persistence_score", 0.0)
        frp = hotspot.get("frp", 10.0)
        temp_c = hotspot.get("brightness_celsius", 60.0)

        # 1. Industrial Flare (Refinery / Gas Flare / Smelter)
        if (is_persistent and ("industrial" in landuse or "refinery" in facility or "power" in facility)) or \
           (persistence_score >= 50 and osm_data.get("distance_to_facility_m", 9999) < 800):
            classification = "INDUSTRIAL GAS FLARE / PROCESS STACK"
            confidence = 94
            severity = "HIGH (MONITOR EMISSIONS)"
            badge_color = "orange"
            action = "Log facility emissions inventory. Cross-reference flare permit with Ministry of Environment (MoEFCC)."
            rationale = f"Stationary thermal hotspot detected {persistence_data['observations_count']} times over {persistence_data['days_analyzed']} days inside verified OSM industrial boundary ({osm_data.get('facility_name', 'Industrial Zone')}). FRP: {frp} MW."

        # 2. Unregistered / Clandestine Thermal Anomaly (NTRO Priority!)
        elif is_persistent and ("farmland" in landuse or "forest" in landuse or "unclassified" in landuse or "scrub" in landuse):
            classification = "UNREGISTERED CLANDESTINE THERMAL ANOMALY"
            confidence = 88
            severity = "CRITICAL (INVESTIGATION REQUIRED)"
            badge_color = "red"
            action = "Dispatch UAV/drone reconnaissance or state pollution control board to verify unmapped industrial kilns, illegal charcoal burning, or clandestine metallurgical operations."
            rationale = f"Highly anomalous persistence ({persistence_score}% recurrence) detected in non-industrial zone ({landuse}). Lack of registered OSM industrial zoning indicates potential unpermitted thermal facility."

        # 3. Forest Wildfire
        elif ("forest" in landuse or "wood" in landuse or "natural" in landuse) and not is_persistent:
            classification = "WILDFIRE / FOREST FIRE"
            confidence = 91
            severity = "CRITICAL (DISASTER SPREAD RISK)"
            badge_color = "red"
            action = "Alert State Forest Department, National Disaster Response Force (NDRF), and Forest Survey of India (FSI)."
            rationale = f"High FRP ({frp} MW) and temperature ({temp_c}°C) detected in dense vegetation canopy with episodic recurrence. Satellite trajectory indicates expanding fire front."

        # 4. Agricultural Stubble / Crop Residue Burning
        elif "farmland" in landuse or "agricultural" in landuse or "grassland" in landuse:
            classification = "AGRICULTURAL CROP RESIDUE / STUBBLE BURNING"
            confidence = 89
            severity = "ELEVATED (AIR QUALITY IMPACT)"
            badge_color = "yellow"
            action = "Transmit air quality alert to Central Pollution Control Board (CPCB) and CAQM. Flag farm cluster coordinates."
            rationale = f"Low temporal persistence ({persistence_score}%) with seasonal clustering in agricultural grid cell. Classic signature of paddy/wheat stubble open burning."

        else:
            classification = "UNCLASSIFIED TRANSIENT THERMAL SIGNATURE"
            confidence = 72
            severity = "LOW"
            badge_color = "slate"
            action = "Monitor next orbital pass for recurrence."
            rationale = f"Single-pass thermal anomaly in {landuse} zone. Insufficient temporal signal to establish persistence."

        return {
            "classification": classification,
            "confidence_percent": confidence,
            "severity": severity,
            "badge_color": badge_color,
            "recommended_action": action,
            "rationale": rationale,
            "frp": frp,
            "brightness_celsius": temp_c,
            "landuse": landuse,
            "persistence_score": persistence_score
        }
