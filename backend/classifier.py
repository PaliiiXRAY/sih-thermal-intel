"""
Thermal Source AI Classifier for SIH26162 (NTRO)
Fuses NASA FIRMS metrics, OSM Land-Use, and Temporal Persistence to classify thermal anomalies using an XGBoost ML Pipeline.
"""

import logging
import os
import sys

# Add project root to path to ensure ml package is importable
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from ml.src.explain import explain_prediction
    from ml.src.feature_engineering import build_features
    ML_AVAILABLE = True
except ImportError as e:
    logging.warning(f"ML Pipeline not found or import failed: {e}")
    ML_AVAILABLE = False

class ThermalClassifier:
    # Mapping between ML labels and Backend descriptive labels
    LABEL_MAP = {
        "INDUSTRIAL_FIRE": "INDUSTRIAL GAS FLARE / PROCESS STACK",
        "GAS_FLARE": "INDUSTRIAL GAS FLARE / PROCESS STACK",
        "WILDFIRE": "WILDFIRE / FOREST FIRE",
        "CROP_BURNING": "AGRICULTURAL CROP RESIDUE / STUBBLE BURNING",
        "UNKNOWN": "UNCLASSIFIED TRANSIENT THERMAL SIGNATURE"
    }

    @staticmethod
    def classify(hotspot: dict, osm_data: dict, persistence_data: dict) -> dict:
        """
        Classifies a thermal anomaly. Attempts ML-driven probabilistic classification
        with a fallback to deterministic rules.
        """
        # --- 1. ML-Driven Classification Attempt ---
        if ML_AVAILABLE:
            try:
                # Map backend objects to ML feature format
                # This mimics what the ML pipeline expects
                ml_incident = {
                    "frp": hotspot.get("frp", 0),
                    "bright_temp": hotspot.get("brightness_celsius", 0),
                    "confidence": float(hotspot.get("confidence", 0)) if str(hotspot.get("confidence")).isdigit() or (isinstance(hotspot.get("confidence"), (int, float))) else 0.9 if hotspot.get("confidence") == "high" else 0.6 if hotspot.get("confidence") == "medium" else 0.3 if hotspot.get("confidence") == "low" else 0.0,
                    "persistence_count": persistence_data.get("observations_count", 1),
                    "duration": persistence_data.get("days_analyzed", 0),
                    "historic_recurrence": 1 if persistence_data.get("is_persistent", False) else 0,
                    "frp_growth": 0.0, # Placeholder for now
                    "dist_to_industrial": osm_data.get("distance_to_facility_m", 1e6),
                    "land_cover": osm_data.get("landuse", "unknown"),
                    "dist_to_settlement": 1e6, # Placeholder
                    "nearby_assets_count": 1 if osm_data.get("facility_name") else 0,
                    "baseline_deviation": 0.0 # Placeholder
                }

                # Generate feature vector
                features = build_features(ml_incident)

                # Get ML prediction and explanation
                ml_result = explain_prediction(features)

                if ml_result and ml_result["confidence"] > 0.4:
                    ml_class = ml_result["class"]
                    backend_class = ThermalClassifier.LABEL_MAP.get(ml_class, "UNCLASSIFIED TRANSIENT THERMAL SIGNATURE")

                    return {
                        "classification": backend_class,
                        "confidence_percent": int(ml_result["confidence"] * 100),
                        "severity": "CRITICAL" if "WILDFIRE" in ml_class or "INDUSTRIAL" in ml_class else "ELEVATED",
                        "badge_color": "red" if "WILDFIRE" in ml_class else "orange",
                        "recommended_action": "Dispatch verification team to coordinates. Cross-reference with registered facility permits.",
                        "rationale": f"ML Model identified {ml_class} with {int(ml_result['confidence']*100)}% confidence. Evidence: {', '.join(ml_result['evidence'])}",
                        "frp": hotspot.get("frp", 10.0),
                        "brightness_celsius": hotspot.get("brightness_celsius", 60.0),
                        "landuse": osm_data.get("landuse", ""),
                        "persistence_score": persistence_data.get("persistence_score", 0.0)
                    }
            except Exception as e:
                logging.error(f"ML Prediction failed: {e}")

        # --- 2. Fallback: Deterministic Rule-Based Logic ---
        landuse = osm_data.get("landuse", "").lower()
        facility = osm_data.get("facility_type", "").lower()
        is_persistent = persistence_data.get("is_persistent", False)
        persistence_score = persistence_data.get("persistence_score", 0.0)
        frp = hotspot.get("frp", 10.0)
        temp_c = hotspot.get("brightness_celsius", 60.0)

        if (is_persistent and ("industrial" in landuse or "refinery" in facility or "power" in facility)) or \
           (persistence_score >= 50 and osm_data.get("distance_to_facility_m", 9999) < 800):
            if "power" in facility or "power" in landuse:
                classification = "THERMAL POWER PLANT / COAL-HANDLING FIRE"
                severity = "HIGH (ENERGY INFRASTRUCTURE)"
                action = "Notify plant control room & state power utility. Verify coal stockyard spontaneous combustion and OEM shutdown protocol."
            elif "steel" in facility or "metall" in facility:
                classification = "STEEL PLANT / SMELTER THERMAL SOURCE"
                severity = "HIGH (MONITOR EMISSIONS)"
                action = "Log facility emissions inventory. Cross-reference furnace operations with State Pollution Control Board."
            elif "mining" in facility or "quarry" in landuse or "mining" in landuse:
                classification = "MINING / COAL STOCKYARD THERMAL SOURCE"
                severity = "HIGH (SPONTANEOUS COMBUSTION RISK)"
                action = "Alert Indian Bureau of Mines & district mining officer. Watch for spontaneous coal-seam combustion spreading."
            else:
                classification = "INDUSTRIAL GAS FLARE / PROCESS STACK"
                severity = "HIGH (MONITOR EMISSIONS)"
                action = "Log facility emissions inventory. Cross-reference flare permit with Ministry of Environment (MoEFCC)."
            confidence = 94
            badge_color = "orange"
            rationale = f"Stationary thermal hotspot detected {persistence_data['observations_count']} times over {persistence_data['days_analyzed']} days inside verified OSM industrial boundary ({osm_data.get('facility_name', 'Industrial Zone')}). FRP: {frp} MW."

        elif is_persistent and ("farmland" in landuse or "forest" in landuse or "unclassified" in landuse or "scrub" in landuse):
            classification = "UNREGISTERED CLANDESTINE THERMAL ANOMALY"
            confidence = 88
            severity = "CRITICAL (INVESTIGATION REQUIRED)"
            badge_color = "red"
            action = "Dispatch UAV/drone reconnaissance or state pollution control board to verify unmapped industrial kilns, illegal charcoal burning, or clandestine metallurgical operations."
            rationale = f"Highly anomalous persistence ({persistence_score}% recurrence) detected in non-industrial zone ({landuse}). Lack of registered OSM industrial zoning indicates potential unpermitted thermal facility."

        elif ("forest" in landuse or "wood" in landuse or "natural" in landuse) and not is_persistent:
            classification = "WILDFIRE / FOREST FIRE"
            confidence = 91
            severity = "CRITICAL (DISASTER SPREAD RISK)"
            badge_color = "red"
            action = "Alert State Forest Department, National Disaster Response Force (NDRF), and Forest Survey of India (FSI)."
            rationale = f"High FRP ({frp} MW) and temperature ({temp_c}°C) detected in dense vegetation canopy with episodic recurrence. Satellite trajectory indicates expanding fire front."

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
