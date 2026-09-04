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
        "title": "Similipal Biosphere Reserve Canopy Fire",
        "timestamp": "11:42 IST (VIIRS Overpass)",
        "coordinates": {"lat": 21.8540, "lon": 86.3520},
        "location_name": "Similipal National Park, Mayurbhanj District, Odisha",
        "classification": "WILDFIRE",
        "confidence": 91,
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
            "contact_role": "Station Officer / Range Officer",
            "secondary_agency": "Similipal Forest Range North Division"
        },
        "explain_classification": {
            "evidence": [
                "3-day progressive expansion of thermal footprint (+42% cluster growth)",
                "Located in dense deciduous sal forest canopy (OSM: natural=wood)",
                "Zero registered industrial facilities within 12 km radius",
                "High Fire Radiative Power (142.6 MW) indicating intense biomass combustion"
            ],
            "counter_evidence": [
                "20% cloud haze contamination possible along western perimeter",
                "Controlled seasonal forestry burn permit unverified in local records"
            ]
        },
        "local_baseline": {
            "location_history_passes": 6,
            "normal_seasonal_range": "0-1 passes / 60 days",
            "anomaly_ratio": "6× above historical baseline",
            "verdict": "6× above historical baseline. High-priority anomaly requiring ground verification."
        },
        "wind_corridor": {
            "speed_kmh": 18,
            "direction": "North-East (NE)",
            "potential_corridor_km": 2.8,
            "description": "Wind: NE at 18 km/h • Potential affected corridor: 2.8 km"
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
        "title": "Jamnagar Refinery Cracker Unit Thermal Flare",
        "timestamp": "11:42 IST (VIIRS Overpass)",
        "coordinates": {"lat": 22.3585, "lon": 69.8310},
        "location_name": "Petrochemical Refining Complex, Jamnagar, Gujarat",
        "classification": "INDUSTRIAL GAS FLARE",
        "confidence": 94,
        "risk_score": 38,
        "risk_label": "MONITOR / COMPLIANCE",
        "frp_mw": 88.4,
        "brightness_c": 85.1,
        "status": "VERIFIED",
        "assigned_authority": {
            "name": "Gujarat Pollution Control Board (GPCB) Jamnagar",
            "jurisdiction": "Jamnagar SEZ Industrial Cluster",
            "distance_km": 3.8,
            "eta_mins": 10,
            "contact_role": "Industrial Environmental Inspector",
            "secondary_agency": "Petroleum & Explosives Safety Org (PESO)"
        },
        "explain_classification": {
            "evidence": [
                "48 out of 60 orbital overpasses detected in exact same 375m spatial cell (80% persistence)",
                "Stationary coordinates matching registered industrial flare stack (OSM: industrial=refinery)",
                "Distance to verified industrial refinery boundary: 120 meters",
                "High thermal intensity consistent with licensed hydrocarbon gas combustion"
            ],
            "counter_evidence": [
                "Spike of +15 MW above quarterly baseline requires routine emissions check"
            ]
        },
        "local_baseline": {
            "location_history_passes": 48,
            "normal_seasonal_range": "40-50 passes / 60 days",
            "anomaly_ratio": "1.05× historical baseline (Within Permitted Parameters)",
            "verdict": "Routine stationary industrial flare. Zero population evacuation needed."
        },
        "wind_corridor": {
            "speed_kmh": 12,
            "direction": "South-West (SW)",
            "potential_corridor_km": 1.2,
            "description": "Downwind plume dissipates over Gulf of Kutch maritime zone"
        },
        "assets_at_risk": [
            {"asset": "Refinery Tank Farm Area B", "type": "Industrial Facility", "population": "Plant Personnel", "distance_km": 0.6, "risk_tier": "MODERATE", "color": "yellow"},
            {"asset": "Moti Khavdi Township Buffer", "type": "Habitation", "population": "Corporate Colony", "distance_km": 3.4, "risk_tier": "SAFE", "color": "green"}
        ]
    },

    "INC-2026-0044": {
        "id": "INC-2026-0044",
        "title": "Sangrur Cluster Paddy Residue Burning",
        "timestamp": "11:42 IST (VIIRS Overpass)",
        "coordinates": {"lat": 30.2480, "lon": 75.8390},
        "location_name": "Sangrur Agricultural District, Punjab",
        "classification": "AGRICULTURAL CROP RESIDUE",
        "confidence": 89,
        "risk_score": 62,
        "risk_label": "HIGH (AIR QUALITY IMPACT)",
        "frp_mw": 24.5,
        "brightness_c": 58.8,
        "status": "NEW",
        "assigned_authority": {
            "name": "District Agriculture & CAQM Flying Squad",
            "jurisdiction": "Sangrur Block 2",
            "distance_km": 8.5,
            "eta_mins": 15,
            "contact_role": "Nodal Revenue Officer (Patwari)",
            "secondary_agency": "Punjab Pollution Control Board (PPCB)"
        },
        "explain_classification": {
            "evidence": [
                "Seasonal spatial clustering in designated farmland (OSM: landuse=farmland)",
                "Low temporal persistence: 1-2 passes observed (characteristic of transient stubble fire)",
                "Low FRP (24.5 MW) consistent with open field biomass residue burning",
                "Aligns with regional harvesting calendar window (Oct-Nov)"
            ],
            "counter_evidence": [
                "Proximity to rural grid road may impact local visibility"
            ]
        },
        "local_baseline": {
            "location_history_passes": 2,
            "normal_seasonal_range": "0 passes in off-season, 1-3 in harvest",
            "anomaly_ratio": "Seasonal Spike (Air Quality Hazard)",
            "verdict": "Transient open-field agricultural burn. Generates air quality hazard alert."
        },
        "wind_corridor": {
            "speed_kmh": 14,
            "direction": "North-West (NW)",
            "potential_corridor_km": 4.5,
            "description": "Smoke plume trajectory directed toward Delhi-NCR airshed"
        },
        "assets_at_risk": [
            {"asset": "Bhawani Village Primary School", "type": "Education", "population": "280 Students", "distance_km": 1.1, "risk_tier": "HIGH (SMOKE)", "color": "orange"},
            {"asset": "Sangrur-Patiala Link Road", "type": "Transport", "population": "Rural Traffic", "distance_km": 1.8, "risk_tier": "MODERATE", "color": "yellow"}
        ]
    },

    "INC-2026-0045": {
        "id": "INC-2026-0045",
        "title": "Unregistered Clandestine Thermal Anomaly",
        "timestamp": "11:42 IST (VIIRS Overpass)",
        "coordinates": {"lat": 24.1840, "lon": 82.6530},
        "location_name": "Singrauli Scrubland Hinterland, MP/UP Border",
        "classification": "CLANDESTINE THERMAL ANOMALY",
        "confidence": 88,
        "risk_score": 79,
        "risk_label": "CRITICAL (NTRO RECON REQUIRED)",
        "frp_mw": 52.3,
        "brightness_c": 70.8,
        "status": "NEW",
        "assigned_authority": {
            "name": "District Magistrate & NTRO Field Liaison Unit",
            "jurisdiction": "Singrauli Mining Buffer Zone",
            "distance_km": 11.2,
            "eta_mins": 30,
            "contact_role": "Special Intelligence Task Force",
            "secondary_agency": "State Mining & Pollution Enforcement Squad"
        },
        "explain_classification": {
            "evidence": [
                "34 overpass detections over 60 days (56% persistence) proving stationary combustion",
                "Land-use is designated scrubland (OSM: natural=scrub) with ZERO registered industrial zoning",
                "Absence of environmental clearance or factory license on state regulatory portals",
                "High thermal intensity characteristic of unpermitted brick kilns or clandestine metallurgy"
            ],
            "counter_evidence": [
                "Sub-surface coal seam smoldering cannot be fully ruled out without drone verification"
            ]
        },
        "local_baseline": {
            "location_history_passes": 34,
            "normal_seasonal_range": "0 passes (Natural scrubland)",
            "anomaly_ratio": "34× Unprecedented Thermal Baseline",
            "verdict": "Confirmed Clandestine Heat Source. High probability of illegal industrial activity."
        },
        "wind_corridor": {
            "speed_kmh": 8,
            "direction": "South-East (SE)",
            "potential_corridor_km": 1.5,
            "description": "Fugitive emissions localized within valley basin"
        },
        "assets_at_risk": [
            {"asset": "Dudhichua Forest Border", "type": "Natural Resource", "population": "Reserved Forest", "distance_km": 1.9, "risk_tier": "HIGH", "color": "orange"},
            {"asset": "Tribal Hamlet Basti", "type": "Habitation", "population": "320 Residents", "distance_km": 2.4, "risk_tier": "MODERATE", "color": "yellow"}
        ]
    }
}
