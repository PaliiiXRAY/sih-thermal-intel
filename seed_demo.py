"""
FireSense Demo Seeding & Scenario Management (SIH26162).
Provides idempotent, deterministic database seeding for curated offline demonstration scenarios.
Maintains complete provenance metadata (DATA_SOURCE=CURATED_DEMO).
Preserves the frozen PostgreSQL/PostGIS database schema.
"""
import argparse
import datetime
import sys
from geoalchemy2.elements import WKTElement
from sqlalchemy.orm import Session

from backend.app.core.security import seed_demo_users_if_needed
from backend.app.db.session import SessionLocal
from backend.app.models.alert import Alert
from backend.app.models.asset import Asset
from backend.app.models.hotspot import Hotspot
from backend.app.models.incident import Incident
from backend.app.models.incident_log import IncidentLog
from backend.app.models.responder import Responder
from backend.app.services.geospatial.context import get_incident_context
from backend.app.services.risk.engine import calculate_risk

CURATED_SCENARIOS = {
    "angul_thermal_plant": {
        "scenario_id": "angul_thermal_plant",
        "alias": "industrial_fire",
        "title": "Angul Thermal Power Plant & Coal Stockyard Fire",
        "incident_id": "inc_angul_thermal_01",
        "region": "Angul Industrial District, Odisha",
        "latitude": 20.8420,
        "longitude": 85.1020,
        "initial_status": "ALERTED",
        "classification": "INDUSTRIAL_FIRE",
        "classification_confidence": 0.94,
        "detection_confidence": "HIGH",
        "persistence_score": 88.5,
        "severity": "CRITICAL",
        "frp": 96.7,
        "brightness": 355.0,
        "assets": [
            {
                "id": "ast_angul_power_plant",
                "name": "NTPC Talcher Thermal Power Station",
                "type": "power_plant",
                "category": "critical_infrastructure",
                "lat": 20.8450,
                "lon": 85.1050,
            },
            {
                "id": "ast_angul_substation",
                "name": "Angul 400kV Grid Substation",
                "type": "electrical_substation",
                "category": "power_transmission",
                "lat": 20.8520,
                "lon": 85.0980,
            },
            {
                "id": "ast_angul_school",
                "name": "Govt High School Angul Relief Shelter",
                "type": "shelter",
                "category": "human_settlement",
                "lat": 20.8580,
                "lon": 85.0930,
            },
        ],
        "responders": [
            {
                "id": "resp_angul_fire_station",
                "name": "Angul Central Fire Brigade Unit 1",
                "type": "fire_brigade",
                "status": "AVAILABLE",
                "organization": "Odisha Fire & Emergency Services",
                "contact_info": "Radio VHF Ch-4 / Synth +91-6764-230101",
                "lat": 20.8400,
                "lon": 85.0950,
            },
            {
                "id": "resp_talcher_hazmat",
                "name": "Talcher Industrial Hazmat & Rescue Team",
                "type": "hazmat_unit",
                "status": "AVAILABLE",
                "organization": "Odisha State Disaster Management Authority",
                "contact_info": "Radio VHF Ch-7 / Synth +91-6764-230102",
                "lat": 20.8500,
                "lon": 85.1100,
            },
        ],
    },
    "jamnagar_refinery": {
        "scenario_id": "jamnagar_refinery",
        "alias": "gas_flare",
        "title": "Jamnagar Petrochemical Complex Stationary Gas Flare",
        "incident_id": "inc_jamnagar_flare_02",
        "region": "Jamnagar Industrial Corridor, Gujarat",
        "latitude": 22.3585,
        "longitude": 69.8310,
        "initial_status": "CLASSIFIED",
        "classification": "GAS_FLARE",
        "classification_confidence": 0.98,
        "detection_confidence": "HIGH",
        "persistence_score": 94.0,
        "severity": "LOW",
        "frp": 88.4,
        "brightness": 358.2,
        "assets": [
            {
                "id": "ast_jamnagar_cracker",
                "name": "Ethylene Cracker Unit Flare Stack",
                "type": "flare_stack",
                "category": "industrial_facility",
                "lat": 22.3600,
                "lon": 69.8320,
            },
            {
                "id": "ast_jamnagar_storage",
                "name": "Crude Oil Tank Farm A",
                "type": "fuel_storage",
                "category": "industrial_facility",
                "lat": 22.3520,
                "lon": 69.8280,
            },
        ],
        "responders": [
            {
                "id": "resp_jamnagar_refinery_fire",
                "name": "Refinery On-Site Fire Safety Squadron",
                "type": "fire_brigade",
                "status": "AVAILABLE",
                "organization": "Industrial Mutual Aid Scheme",
                "contact_info": "Radio VHF Ch-2",
                "lat": 22.3550,
                "lon": 69.8350,
            },
        ],
    },
    "similipal_wildfire": {
        "scenario_id": "similipal_wildfire",
        "alias": "wildfire",
        "title": "Similipal Biosphere Reserve Forest Wildfire",
        "incident_id": "inc_similipal_wild_03",
        "region": "Similipal National Park, Mayurbhanj, Odisha",
        "latitude": 21.8540,
        "longitude": 86.3520,
        "initial_status": "ASSESSED",
        "classification": "WILDFIRE",
        "classification_confidence": 0.92,
        "detection_confidence": "HIGH",
        "persistence_score": 45.0,
        "severity": "HIGH",
        "frp": 142.6,
        "brightness": 369.4,
        "assets": [
            {
                "id": "ast_similipal_core_reserve",
                "name": "Similipal Tiger Reserve Core Zone",
                "type": "protected_forest",
                "category": "biodiversity_reserve",
                "lat": 21.8600,
                "lon": 86.3600,
            },
            {
                "id": "ast_forest_village_jashipur",
                "name": "Jashipur Forest Settlement",
                "type": "village",
                "category": "human_settlement",
                "lat": 21.8750,
                "lon": 86.3400,
            },
        ],
        "responders": [
            {
                "id": "resp_similipal_forest_rangers",
                "name": "Similipal Rapid Action Forest Fire Squad",
                "type": "forest_ranger",
                "status": "AVAILABLE",
                "organization": "Odisha Forest Department",
                "contact_info": "Radio Forest Net Ch-1",
                "lat": 21.8480,
                "lon": 86.3300,
            },
        ],
    },
    "punjab_stubble": {
        "scenario_id": "punjab_stubble",
        "alias": "crop_burning",
        "title": "Sangrur Agricultural Farmland Stubble Burning",
        "incident_id": "inc_punjab_stubble_04",
        "region": "Sangrur Agricultural District, Punjab",
        "latitude": 30.2480,
        "longitude": 75.8390,
        "initial_status": "CLASSIFIED",
        "classification": "CROP_BURNING",
        "classification_confidence": 0.89,
        "detection_confidence": "NOMINAL",
        "persistence_score": 12.0,
        "severity": "MEDIUM",
        "frp": 24.5,
        "brightness": 332.0,
        "assets": [
            {
                "id": "ast_sangrur_highway",
                "name": "NH-7 Sangrur-Patiala Highway Corridor",
                "type": "highway",
                "category": "transportation",
                "lat": 30.2520,
                "lon": 75.8450,
            },
            {
                "id": "ast_sangrur_grain_market",
                "name": "Sangrur Grain Market (Anaaj Mandi)",
                "type": "commercial",
                "category": "agriculture_logistics",
                "lat": 30.2400,
                "lon": 75.8300,
            },
        ],
        "responders": [
            {
                "id": "resp_sangrur_fire_brigade",
                "name": "Sangrur District Fire Station",
                "type": "fire_brigade",
                "status": "AVAILABLE",
                "organization": "Punjab Municipal Fire Service",
                "contact_info": "Radio VHF Ch-5",
                "lat": 30.2450,
                "lon": 75.8420,
            },
        ],
    },
    "clandestine_thermal_anomaly": {
        "scenario_id": "clandestine_thermal_anomaly",
        "alias": "unknown",
        "title": "Singrauli Hinterland Unregistered Thermal Anomaly",
        "incident_id": "inc_singrauli_unknown_05",
        "region": "Singrauli Hinterland, MP/UP Border",
        "latitude": 24.1840,
        "longitude": 82.6530,
        "initial_status": "DETECTED",
        "classification": "UNKNOWN",
        "classification_confidence": 0.55,
        "detection_confidence": "HIGH",
        "persistence_score": 68.0,
        "severity": "HIGH",
        "frp": 52.3,
        "brightness": 344.0,
        "assets": [
            {
                "id": "ast_singrauli_rail_link",
                "name": "Singrauli Freight Rail Siding",
                "type": "railway",
                "category": "transportation",
                "lat": 24.1900,
                "lon": 82.6600,
            },
        ],
        "responders": [
            {
                "id": "resp_singrauli_police",
                "name": "Singrauli District Emergency Response Patrol",
                "type": "medical_team",
                "status": "AVAILABLE",
                "organization": "District Disaster Cell",
                "contact_info": "Radio Ch-9",
                "lat": 24.1800,
                "lon": 82.6450,
            },
        ],
    },
}


def seed_scenario(db: Session, scenario: dict) -> Incident:
    """Seed assets, responders, hotspots, and incident for a scenario idempotently."""
    lat = scenario["latitude"]
    lon = scenario["longitude"]
    inc_id = scenario["incident_id"]

    # 1. Seed Assets
    for ast_data in scenario.get("assets", []):
        existing_ast = db.query(Asset).filter(Asset.id == ast_data["id"]).first()
        point_geom = WKTElement(f"POINT({ast_data['lon']} {ast_data['lat']})", srid=4326)
        if not existing_ast:
            asset = Asset(
                id=ast_data["id"],
                name=ast_data["name"],
                type=ast_data["type"],
                category=ast_data["category"],
                latitude=ast_data["lat"],
                longitude=ast_data["lon"],
                geometry=point_geom,
            )
            db.add(asset)
        else:
            existing_ast.name = ast_data["name"]
            existing_ast.latitude = ast_data["lat"]
            existing_ast.longitude = ast_data["lon"]
            existing_ast.geometry = point_geom

    # 2. Seed Responders
    for resp_data in scenario.get("responders", []):
        existing_resp = db.query(Responder).filter(Responder.id == resp_data["id"]).first()
        point_geom = WKTElement(f"POINT({resp_data['lon']} {resp_data['lat']})", srid=4326)
        if not existing_resp:
            resp = Responder(
                id=resp_data["id"],
                name=resp_data["name"],
                type=resp_data["type"],
                status=resp_data["status"],
                organization=resp_data["organization"],
                contact_info=resp_data["contact_info"],
                latitude=resp_data["lat"],
                longitude=resp_data["lon"],
                geometry=point_geom,
            )
            db.add(resp)
        else:
            existing_resp.name = resp_data["name"]
            existing_resp.status = resp_data["status"]
            existing_resp.latitude = resp_data["lat"]
            existing_resp.longitude = resp_data["lon"]
            existing_resp.geometry = point_geom

    db.commit()

    # 3. Seed Hotspot
    hs_id = f"hs_{inc_id}"
    existing_hs = db.query(Hotspot).filter(Hotspot.id == hs_id).first()
    point_geom = WKTElement(f"POINT({lon} {lat})", srid=4326)
    if not existing_hs:
        hotspot = Hotspot(
            id=hs_id,
            latitude=lat,
            longitude=lon,
            geometry=point_geom,
            frp=scenario["frp"],
            bright_ti4=scenario["brightness"],
            detection_confidence=scenario["detection_confidence"],
            satellite="VIIRS_SNPP",
            source="demo",
            acquisition_time=datetime.datetime.now(datetime.timezone.utc),
        )
        db.add(hotspot)
        db.commit()

    # 4. Seed Incident
    existing_inc = db.query(Incident).filter(Incident.id == inc_id).first()
    assigned_resp_id = scenario["responders"][0]["id"] if scenario.get("responders") else None

    # Calculate initial risk
    temp_inc = Incident(
        id=inc_id,
        latitude=lat,
        longitude=lon,
        geometry=point_geom,
        severity=scenario["severity"],
        classification=scenario["classification"],
        classification_confidence=scenario["classification_confidence"],
        detection_confidence=scenario["detection_confidence"],
        persistence_score=scenario["persistence_score"],
    )
    try:
        ctx = get_incident_context(db, temp_inc)
        risk_result = calculate_risk(temp_inc, ctx)
        calc_risk_score = risk_result.get("risk_score", 65.0)
    except Exception:
        calc_risk_score = 65.0
        risk_result = {"reasons": ["Demonstration priority baseline"]}

    explanation_payload = {
        "title": scenario["title"],
        "region": scenario["region"],
        "data_source": "CURATED_DEMO",
        "scenario_id": scenario["scenario_id"],
        "scenario_version": "1.0",
        "evidence": {
            "frp": scenario["frp"],
            "brightness_k": scenario["brightness"],
            "persistence_score": scenario["persistence_score"],
        },
        "risk_reasons": risk_result.get("reasons", []),
    }

    if not existing_inc:
        inc = Incident(
            id=inc_id,
            latitude=lat,
            longitude=lon,
            geometry=point_geom,
            status=scenario["initial_status"],
            classification=scenario["classification"],
            classification_confidence=scenario["classification_confidence"],
            detection_confidence=scenario["detection_confidence"],
            persistence_score=scenario["persistence_score"],
            risk_score=calc_risk_score,
            severity=scenario["severity"],
            assigned_responder_id=assigned_resp_id,
            explanation=explanation_payload,
        )
        db.add(inc)
        db.commit()

        # Add initial audit logs
        log_create = IncidentLog(
            incident_id=inc_id,
            action="DETECTED",
            old_status=None,
            new_status="DETECTED",
            changed_by="SYSTEM",
            note=f"Curated demo detection ingested: {scenario['title']}",
            metadata_={"data_source": "CURATED_DEMO", "scenario_id": scenario["scenario_id"]},
        )
        db.add(log_create)

        if scenario["initial_status"] != "DETECTED":
            log_advance = IncidentLog(
                incident_id=inc_id,
                action="INITIALIZE_DEMO_STATE",
                old_status="DETECTED",
                new_status=scenario["initial_status"],
                changed_by="SYSTEM",
                note=f"Demo state initialized to {scenario['initial_status']}",
                metadata_={"data_source": "CURATED_DEMO"},
            )
            db.add(log_advance)

        # If ALERTED or later, also seed simulated alert record
        if scenario["initial_status"] in ["ALERTED", "ACKNOWLEDGED", "EN_ROUTE", "ARRIVED", "CONTAINED", "RESOLVED"]:
            alert = Alert(
                incident_id=inc_id,
                alert_type="INCIDENT_PRIORITY_ALERT",
                target_role="authority",
                recommended_responder_id=assigned_resp_id,
                is_simulated=True,
                status="SENT",
                message=f"Simulated priority alert for {scenario['title']}",
                payload={
                    "incident_id": inc_id,
                    "is_simulated": True,
                    "classification": scenario["classification"],
                    "severity": scenario["severity"],
                    "risk_score": calc_risk_score,
                    "data_source": "CURATED_DEMO",
                },
                sent_at=datetime.datetime.now(datetime.timezone.utc),
            )
            db.add(alert)

        db.commit()
        db.refresh(inc)
        return inc
    else:
        existing_inc.status = scenario["initial_status"]
        existing_inc.classification = scenario["classification"]
        existing_inc.classification_confidence = scenario["classification_confidence"]
        existing_inc.detection_confidence = scenario["detection_confidence"]
        existing_inc.persistence_score = scenario["persistence_score"]
        existing_inc.risk_score = calc_risk_score
        existing_inc.severity = scenario["severity"]
        existing_inc.explanation = explanation_payload
        db.commit()
        db.refresh(existing_inc)
        return existing_inc


def seed_all_scenarios(db: Session):
    """Seed all 5 curated demo scenarios into database."""
    print("Seeding demo users...")
    seed_demo_users_if_needed(db)
    print("Seeding curated demo scenarios...")
    for key, scenario in CURATED_SCENARIOS.items():
        inc = seed_scenario(db, scenario)
        print(f"  [OK] {scenario['title']} -> ID: {inc.id} [{inc.status}]")


def reset_demo_data(db: Session):
    """
    Safely reset demo incidents and alerts without dropping database tables or volumes.
    Application-level reset strictly preserves schema and migrations.
    """
    print("Performing application-level demo data reset...")
    demo_inc_ids = [s["incident_id"] for s in CURATED_SCENARIOS.values()]
    # Delete test / demo alerts, logs, and incidents
    db.query(Alert).filter(Alert.incident_id.in_(demo_inc_ids)).delete(synchronize_session=False)
    db.query(IncidentLog).filter(IncidentLog.incident_id.in_(demo_inc_ids)).delete(synchronize_session=False)
    db.query(Incident).filter(Incident.id.in_(demo_inc_ids)).delete(synchronize_session=False)
    db.commit()
    print("Demo data reset complete. Re-seeding fresh baseline...")
    seed_all_scenarios(db)


def main():
    parser = argparse.ArgumentParser(description="FireSense Curated Demo Scenario Seeder")
    parser.add_argument(
        "--scenario",
        type=str,
        default="all",
        help="Scenario ID to seed (angul_thermal_plant, jamnagar_refinery, similipal_wildfire, punjab_stubble, clandestine_thermal_anomaly, or 'all')",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Perform controlled application-level demo reset and reseed (does NOT drop tables)",
    )

    args = parser.parse_args()
    db = SessionLocal()
    try:
        if args.reset:
            reset_demo_data(db)
            return

        if args.scenario == "all":
            seed_all_scenarios(db)
        else:
            # Check match by key or alias
            target = None
            for key, sc in CURATED_SCENARIOS.items():
                if args.scenario.lower() in [key.lower(), sc.get("alias", "").lower()]:
                    target = sc
                    break
            if not target:
                print(f"Error: Unknown scenario '{args.scenario}'. Available: {list(CURATED_SCENARIOS.keys())}")
                sys.exit(1)
            seed_demo_users_if_needed(db)
            inc = seed_scenario(db, target)
            print(f"[OK] Seeded {target['title']} -> {inc.id} [{inc.status}]")
    finally:
        db.close()


if __name__ == "__main__":
    main()
