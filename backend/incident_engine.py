"""
Upgraded Incident & Asset-at-Risk Model for SIH26162
Implements:
1. Incident Ticket Model with State Machine (NEW -> INVESTIGATING -> VERIFIED -> DISPATCHED -> CONTAINED -> RESOLVED)
2. Assets-at-Risk / Exposure Matrix (Population, Roads, Schools, Hospitals)
3. Explain Classification Engine (Evidence & Counter-evidence)
4. Local Historical Baseline (This location specific)
5. Authority Routing & Simulated First Responder Workflow
"""

INCIDENTS = {
    "INC-2026-0042": {
        "id": "INC-2026-0042",
        "title": "Similipal Forest Fire",
        "timestamp": "11:42 IST (Satellite Overpass)",
        "coordinates": {"lat": 21.8540, "lon": 86.3520},
        "location_name": "Similipal National Park, Mayurbhanj District, Odisha",
        "classification": "WILDFIRE",
        "confidence": 91,
        "confidence_breakdown": {
            "score": 91,
            "rating": "HIGH",
            "sensor_signal": "96% (Sharp 4µm thermal infrared contrast)",
            "cross_satellite": "Confirmed by 2 separate satellite passes",
            "cloud_interference": "Low (20% thin haze on western edge)",
            "dispatch_protocol": "Confidence >85% qualifies for direct fire brigade alert"
        },
        "risk_score": 87,
        "risk_label": "CRITICAL",
        "frp_mw": 142.6,
        "brightness_c": 96.2,
        "status": "NEW",  # NEW -> INVESTIGATING -> VERIFIED -> DISPATCHED -> CONTAINED -> RESOLVED
        "assigned_authority": {
            "name": "Baripada Fire & Emergency Services",
            "jurisdiction": "Mayurbhanj District, Ward 4",
            "distance_km": 14.2,
            "eta_mins": 25,
            "contact_role": "Station Officer / Field Chief",
            "secondary_agency": "Similipal Forest Range North Division"
        },
        "explain_classification": {
            "evidence": [
                "Fire area grew by +42% over the last 3 days",
                "Located in dense protected forest land (natural woodland)",
                "No factories or industrial chimneys anywhere within 12 km",
                "Very high heat intensity indicating active burning forest trees"
            ],
            "counter_evidence": [
                "Possible light cloud haze on western edge (20%)",
                "No official controlled forestry burn permits recorded"
            ]
        },
        "local_baseline": {
            "location_history_passes": 6,
            "normal_seasonal_range": "0-1 times / 60 days",
            "anomaly_ratio": "Very unusual activity",
            "verdict": "This location normally has almost no fire activity. High-priority alert requiring immediate ground check."
        },
        "wind_corridor": {
            "speed_kmh": 18,
            "direction": "North-East (NE)",
            "potential_corridor_km": 2.8,
            "description": "Wind: NE at 18 km/h • Risk area: ~2.8 km downwind"
        },
        "assets_at_risk": [
            {"asset": "Village Kaptipada (Settlement)", "type": "Habitation", "population": "1,420 people", "distance_km": 1.4, "risk_tier": "CRITICAL", "color": "red"},
            {"asset": "NH-49 National Highway", "type": "Transport Corridor", "population": "Major Transit Road", "distance_km": 2.1, "risk_tier": "HIGH", "color": "orange"},
            {"asset": "Kaptipada Primary Health Sub-Centre", "type": "Healthcare", "population": "Critical Care Unit", "distance_km": 4.2, "risk_tier": "ELEVATED", "color": "yellow"},
            {"asset": "Similipal Eco-Tourism Buffer Zone", "type": "Protected Wildlife", "population": "Habitat Reserve", "distance_km": 5.8, "risk_tier": "MONITOR", "color": "green"}
        ]
    },

    "INC-2026-0043": {
        "id": "INC-2026-0043",
        "title": "Jamnagar Refinery Flare Stack",
        "timestamp": "11:42 IST (Satellite Overpass)",
        "coordinates": {"lat": 22.3585, "lon": 69.8310},
        "location_name": "Petrochemical Refining Complex, Jamnagar, Gujarat",
        "classification": "FACTORY FLARE",
        "confidence": 94,
        "confidence_breakdown": {
            "score": 94,
            "rating": "VERY HIGH",
            "sensor_signal": "98% (Constant high-temp hydrocarbon flare)",
            "cross_satellite": "48 repeat passes at exact same point",
            "cloud_interference": "None (Clear coastal atmosphere)",
            "dispatch_protocol": "Known registered site; zero false alarm risk"
        },
        "risk_score": 38,
        "risk_label": "SAFE / NORMAL (MONITOR)",
        "frp_mw": 88.4,
        "brightness_c": 85.1,
        "status": "VERIFIED",
        "assigned_authority": {
            "name": "Gujarat Pollution Control Board (GPCB) Jamnagar",
            "jurisdiction": "Jamnagar Industrial Cluster",
            "distance_km": 3.8,
            "eta_mins": 10,
            "contact_role": "Industrial Environmental Inspector",
            "secondary_agency": "Plant Safety Division"
        },
        "explain_classification": {
            "evidence": [
                "Heat detected 48 times in 60 days at the exact same spot",
                "Matches registered licensed industrial refinery chimney",
                "Located inside refinery boundary (120m from center)",
                "Normal gas flare combustion from regular plant operations"
            ],
            "counter_evidence": [
                "Small heat uptick (+15 MW) logged for routine review"
            ]
        },
        "local_baseline": {
            "location_history_passes": 48,
            "normal_seasonal_range": "40-50 times / 60 days",
            "anomaly_ratio": "Normal plant operating range",
            "verdict": "Routine stationary factory flare. Normal safe operation, no evacuation needed."
        },
        "wind_corridor": {
            "speed_kmh": 12,
            "direction": "South-West (SW)",
            "potential_corridor_km": 1.2,
            "description": "Wind: SW at 12 km/h • Carries smoke toward open sea"
        },
        "assets_at_risk": [
            {"asset": "Refinery Tank Farm Area B", "type": "Industrial Facility", "population": "Plant Personnel", "distance_km": 0.6, "risk_tier": "MODERATE", "color": "yellow"},
            {"asset": "Moti Khavdi Township Buffer", "type": "Habitation", "population": "Corporate Colony", "distance_km": 3.4, "risk_tier": "SAFE", "color": "green"}
        ]
    },

    "INC-2026-0044": {
        "id": "INC-2026-0044",
        "title": "Sangrur Farm Stubble Burning",
        "timestamp": "11:42 IST (Satellite Overpass)",
        "coordinates": {"lat": 30.2480, "lon": 75.8390},
        "location_name": "Sangrur Agricultural District, Punjab",
        "classification": "CROP SMOKE",
        "confidence": 89,
        "confidence_breakdown": {
            "score": 89,
            "rating": "HIGH",
            "sensor_signal": "90% (Low-intensity smoke & smoldering)",
            "cross_satellite": "Cross-verified across agricultural cluster",
            "cloud_interference": "Low (Clear autumn skies)",
            "dispatch_protocol": "Confidence >85%: Issues air quality alert to local administration"
        },
        "risk_score": 62,
        "risk_label": "HIGH (AIR QUALITY IMPACT)",
        "frp_mw": 24.5,
        "brightness_c": 58.8,
        "status": "NEW",
        "assigned_authority": {
            "name": "District Agriculture & Air Quality Flying Squad",
            "jurisdiction": "Sangrur Block 2",
            "distance_km": 8.5,
            "eta_mins": 15,
            "contact_role": "Nodal Revenue Officer",
            "secondary_agency": "Pollution Control Board"
        },
        "explain_classification": {
            "evidence": [
                "Cluster of fires detected across open crop fields",
                "Short-lived burning: seen only 1-2 times (typical crop fire)",
                "Moderate heat intensity matching open-field straw burning",
                "Occurring during regional harvest season"
            ],
            "counter_evidence": [
                "Smoke near rural road may temporarily reduce visibility"
            ]
        },
        "local_baseline": {
            "location_history_passes": 2,
            "normal_seasonal_range": "0 in off-season, 1-3 in harvest",
            "anomaly_ratio": "Seasonal Spike",
            "verdict": "Short-term seasonal farm fire. Air quality alert issued to nearby villages."
        },
        "wind_corridor": {
            "speed_kmh": 14,
            "direction": "North-West (NW)",
            "potential_corridor_km": 4.5,
            "description": "Wind: NW at 14 km/h • Smoke drifting toward regional highways"
        },
        "assets_at_risk": [
            {"asset": "Bhawani Village Primary School", "type": "Education", "population": "280 Students", "distance_km": 1.1, "risk_tier": "HIGH (SMOKE)", "color": "orange"},
            {"asset": "Sangrur-Patiala Link Road", "type": "Transport", "population": "Rural Traffic", "distance_km": 1.8, "risk_tier": "MODERATE", "color": "yellow"}
        ]
    },

    "INC-2026-0045": {
        "id": "INC-2026-0045",
        "title": "Singrauli Unregistered Hotspot",
        "timestamp": "11:42 IST (Satellite Overpass)",
        "coordinates": {"lat": 24.1840, "lon": 82.6530},
        "location_name": "Singrauli Scrubland, MP/UP Border",
        "classification": "SUSPICIOUS ACTIVITY",
        "confidence": 78,
        "confidence_breakdown": {
            "score": 78,
            "rating": "MODERATE",
            "sensor_signal": "82% (Intermittent heat signature)",
            "cross_satellite": "Stationary coordinate observed on 34 passes",
            "cloud_interference": "Moderate (Valley dust and haze)",
            "dispatch_protocol": "Confidence <85%: Automated drone reconnaissance dispatched before ground unit"
        },
        "risk_score": 79,
        "risk_label": "CRITICAL (NTRO CHECK REQUIRED)",
        "frp_mw": 52.3,
        "brightness_c": 70.8,
        "status": "NEW",
        "assigned_authority": {
            "name": "District Magistrate & Field Task Force",
            "jurisdiction": "Singrauli Buffer Zone",
            "distance_km": 11.2,
            "eta_mins": 30,
            "contact_role": "Field Team Liaison",
            "secondary_agency": "State Enforcement Squad"
        },
        "explain_classification": {
            "evidence": [
                "Heat source detected 34 times in 60 days at fixed spot",
                "Located on scrubland with zero licensed factory permits",
                "No environmental clearances on government portals",
                "High heat output suggests illegal furnace or unpermitted kiln"
            ],
            "counter_evidence": [
                "Underground coal seam burning requires drone check to verify"
            ]
        },
        "local_baseline": {
            "location_history_passes": 34,
            "normal_seasonal_range": "0 times (Normally untouched scrubland)",
            "anomaly_ratio": "34× Unprecedented Activity",
            "verdict": "Unregistered continuous heat source. Drone reconnaissance recommended."
        },
        "wind_corridor": {
            "speed_kmh": 8,
            "direction": "South-East (SE)",
            "potential_corridor_km": 1.5,
            "description": "Wind: SE at 8 km/h • Smoke confined inside valley basin"
        },
        "assets_at_risk": [
            {"asset": "Dudhichua Forest Border", "type": "Natural Resource", "population": "Reserved Forest", "distance_km": 1.9, "risk_tier": "HIGH", "color": "orange"},
            {"asset": "Tribal Hamlet Basti", "type": "Habitation", "population": "320 Residents", "distance_km": 2.4, "risk_tier": "MODERATE", "color": "yellow"}
        ]
    }
}
