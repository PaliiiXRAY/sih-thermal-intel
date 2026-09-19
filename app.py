"""
AeroThermal Core Server (SIH26162)
NASA FIRMS & OSM Incident Response Platform - NTRO
Supports Control Room & First Responder Dashboards with State Machine.

Endpoints:
  GET  /api/incidents                          → list all incidents
  GET  /api/incidents/:id                      → single incident
  PATCH /api/incidents/:id/status              → update status (validates transitions)
  POST /api/incidents/:id/alert                → send simulated alert
  GET  /api/incidents/:id/responders           → nearby responders
  GET  /api/incidents/:id/status-log           → status change history
  GET  /api/export/:id/pdf                     → PDF export URL
"""
import os
import sys
import json
from http.server import HTTPServer, ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.incident_engine import INCIDENTS
from backend import store
from backend.pipeline import HotspotPipeline
from backend.alerts import dispatch_alert, get_approved_alerts
from backend.state_machine import can_transition, validate_and_transition, VALID_TRANSITIONS
from backend.incident_logger import log_transition, get_logs, get_all_logs
from backend.demo_loader import load_all_scenarios, load_facilities, get_responders_nearby
from urllib.parse import parse_qs

PORT = 5002
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

# ══════════════════════════════════════════════════════════════════════
# VALID TRANSITION TABLE (owned by Faizaan — schema changes via Aditya)
# ══════════════════════════════════════════════════════════════════════
VALID_TRANSITIONS = {
    "NEW":          ["INVESTIGATING"],
    "INVESTIGATING":["VERIFIED"],
    "VERIFIED":     ["DISPATCHED"],
    "DISPATCHED":   ["ACKNOWLEDGED", "INVESTIGATING"],
    "ACKNOWLEDGED": ["EN ROUTE"],
    "EN ROUTE":     ["ARRIVED"],
    "ARRIVED":      ["CONTAINED"],
    "CONTAINED":    ["RESOLVED"],
    "RESOLVED":     [],
}

# ══════════════════════════════════════════════════════════════════════
# MOCK RESPONDER DATA (simulated nearby units)
# ══════════════════════════════════════════════════════════════════════
MOCK_RESPONDERS = {
    "INC-2026-0042": [
        {"id": "UNIT-001", "name": "NDRF Team Alpha", "unit": "NDRF-OD-03",
         "type": "NDRF", "distance_km": 14.2, "eta_mins": 25, "status": "AVAILABLE",
         "gps": {"lat": 21.8320, "lon": 86.3200}},
        {"id": "UNIT-002", "name": "Odisha Fire Brigade", "unit": "OFB-BLP-12",
         "type": "Fire Brigade", "distance_km": 18.5, "eta_mins": 32, "status": "AVAILABLE",
         "gps": {"lat": 21.8100, "lon": 86.2800}},
        {"id": "UNIT-003", "name": "District Civil Defense", "unit": "DCD-MBR-04",
         "type": "Civil Defense", "distance_km": 22.1, "eta_mins": 40, "status": "EN_ROUTE_OTHER",
         "gps": {"lat": 21.7900, "lon": 86.2500}},
    ],
    "INC-2026-0043": [
        {"id": "UNIT-010", "name": "GPCB Rapid Response", "unit": "GPCB-JNG-01",
         "type": "Environmental", "distance_km": 3.8, "eta_mins": 10, "status": "AVAILABLE",
         "gps": {"lat": 22.3500, "lon": 69.8200}},
    ],
    "INC-2026-0044": [
        {"id": "UNIT-020", "name": "Punjab Pollution Squad", "unit": "PPCB-SNG-03",
         "type": "Environmental", "distance_km": 8.5, "eta_mins": 15, "status": "AVAILABLE",
         "gps": {"lat": 30.2400, "lon": 75.8300}},
        {"id": "UNIT-021", "name": "District Fire Service", "unit": "DFS-SNG-01",
         "type": "Fire Brigade", "distance_km": 12.0, "eta_mins": 20, "status": "AVAILABLE",
         "gps": {"lat": 30.2300, "lon": 75.8100}},
    ],
    "INC-2026-0045": [
        {"id": "UNIT-030", "name": "MP Task Force", "unit": "MPTF-SNG-02",
         "type": "NDRF", "distance_km": 11.2, "eta_mins": 30, "status": "AVAILABLE",
         "gps": {"lat": 24.1700, "lon": 82.6400}},
    ],
}


class AeroThermalHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # ── Static file serving ──
        if path == "/" or path == "/landing" or path == "/index.html":
            self.serve_file(os.path.join(STATIC_DIR, "landing.html"), "text/html")
            return
        if path == "/app" or path == "/dashboard":
            self.serve_file(os.path.join(STATIC_DIR, "index.html"), "text/html")
            return
        if path.startswith("/static/"):
            file_name = path.replace("/static/", "")
            file_path = os.path.join(STATIC_DIR, file_name)
            if os.path.isfile(file_path):
                ctype = ("text/css" if file_name.endswith(".css") else
                         "application/javascript" if file_name.endswith(".js") else
                         "text/html")
                self.serve_file(file_path, ctype)
                return

        # ── Pipeline ──
        if path == "/api/pipeline/scenario":
            qs = parse_qs(parsed.query)
            scenario_id = qs.get("id", ["jamnagar_refinery"])[0]
            use_live = qs.get("live_osm", ["0"])[0] == "1"
            try:
                self.send_json(HotspotPipeline.run_scenario(scenario_id, use_live_osm=use_live))
            except Exception as e:
                self.send_json({"error": str(e)}, 500)
            return

        if path == "/api/live":
            qs = parse_qs(parsed.query)
            map_key = qs.get("map_key", [""])[0] or os.environ.get("FIRMS_MAP_KEY", "")
            if not map_key:
                self.send_json({
                    "error": "Missing 'map_key'. Get one at https://firms.modap.eosdis.nasa.gov/api/map_key/",
                }, 400)
                return
            try:
                bbox = tuple(float(x) for x in qs.get("bbox", ["6,68,36,98"])[0].split(","))
                fc = HotspotPipeline.run_live(
                    map_key, bbox,
                    source=qs.get("source", ["viirs"])[0],
                    day_range=int(qs.get("days", ["1"])[0]),
                    use_live_osm=qs.get("live_osm", ["0"])[0] == "1")
                self.send_json(fc)
            except Exception as e:
                self.send_json({"error": str(e)}, 502)
            return

        # ── Stats ──
        if path == "/api/stats":
            try:
                from backend.stats import compute_stats
                self.send_json(compute_stats())
            except Exception as e:
                self.send_json({"error": str(e)}, 500)
            return

        # ── Citizen Reports ──
        if path == "/api/reports":
            self.send_json({"reports": store.get_reports()})
            return

        # ── GET /api/incidents ──
        if path == "/api/incidents":
            overrides = store.load_incident_overrides()
            incidents = []
            for inc in INCIDENTS.values():
                item = dict(inc)
                if inc["id"] in overrides:
                    item["status"] = overrides[inc["id"]]["status"]
                incidents.append(item)
            self.send_json({"incidents": incidents})
            return

        # ── GET /api/incidents/:id/responders ──
        if "/responders" in path and path.startswith("/api/incidents/"):
            inc_id = path.split("/")[3]
            if inc_id in INCIDENTS:
                responders = MOCK_RESPONDERS.get(inc_id, [])
                self.send_json({"incident_id": inc_id, "responders": responders})
            else:
                self.send_json({"error": "Incident not found"}, 404)
            return

        # ── GET /api/incidents/:id/status-log ──
        if "/status-log" in path and path.startswith("/api/incidents/"):
            inc_id = path.split("/")[3]
            if inc_id in INCIDENTS:
                log = store.get_status_log(inc_id)
                self.send_json({"incident_id": inc_id, "log": log})
            else:
                self.send_json({"error": "Incident not found"}, 404)
            return

        # ── GET /api/incidents/:id (single incident) ──
        if path.startswith("/api/incidents/") and "/responders" not in path and "/status-log" not in path:
            inc_id = path.replace("/api/incidents/", "").strip()
            if inc_id in INCIDENTS:
                item = dict(INCIDENTS[inc_id])
                overrides = store.load_incident_overrides()
                if inc_id in overrides:
                    item["status"] = overrides[inc_id]["status"]
                self.send_json(item)
            else:
                self.send_json({"error": "Incident not found"}, 404)
            return

        # ── GET /api/incident/:id (legacy alias) ──
        if path.startswith("/api/incident/") and "/status" not in path and "/dispatch" not in path:
            inc_id = path.replace("/api/incident/", "").strip()
            if inc_id in INCIDENTS:
                item = dict(INCIDENTS[inc_id])
                overrides = store.load_incident_overrides()
                if inc_id in overrides:
                    item["status"] = overrides[inc_id]["status"]
                self.send_json(item)
            else:
                self.send_json({"error": "Incident not found"}, 404)
            return

        # ── GET /api/export/:id/pdf ──
        if path.startswith("/api/export/") and path.endswith("/pdf"):
            parts = path.split("/")
            inc_id = parts[3]
            if inc_id in INCIDENTS:
                now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                filename = f"{inc_id}_Dossier_{now}.pdf"
                self.send_json({
                    "success": True,
                    "incident_id": inc_id,
                    "filename": filename,
                    "pdf_url": f"/exports/{filename}",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                })
            else:
                self.send_json({"error": "Incident not found"}, 404)
            return

        # --- New operational routes ---
        if path == "/public/alerts":
            self.send_json({"alerts": get_approved_alerts()})
            return

        if path.startswith("/api/responders/nearby"):
            qs = parse_qs(parsed.query)
            try:
                lat = float(qs.get("lat", [0])[0])
                lon = float(qs.get("lon", [0])[0])
                limit = int(qs.get("limit", [5])[0])
                self.send_json({"responders": get_responders_nearby(lat, lon, limit)})
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
            return

        if path.startswith("/api/incident/") and "/logs" in path:
            inc_id = path.replace("/api/incident/", "").replace("/logs", "").strip()
            self.send_json({"logs": get_logs(inc_id)})
            return

        if path.startswith("/api/export/") and path.endswith("/pdf"):
            inc_id = path.replace("/api/export/", "").replace("/pdf", "").strip()
            if inc_id in INCIDENTS:
                item = dict(INCIDENTS[inc_id])
                overrides = store.load_incident_overrides()
                if inc_id in overrides:
                    item["status"] = overrides[inc_id]["status"]
                self.send_json({"export": item, "format": "json_stub", "note": "PDF export stub -- full PDF generation deferred"})
            else:
                self.send_json({"error": "Incident not found"}, 404)
            return

        self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}

        # ── POST /api/incidents/:id/alert ──
        if path.startswith("/api/incidents/") and path.endswith("/alert"):
            inc_id = path.split("/")[3]
            if inc_id not in INCIDENTS:
                self.send_json({"error": "Incident not found"}, 404)
                return

            overrides = store.load_incident_overrides()
            current_status = overrides.get(inc_id, {}).get("status", INCIDENTS[inc_id]["status"])

            # Validate: can only alert from DISPATCHED or earlier
            allowed_alert_from = ["NEW", "INVESTIGATING", "VERIFIED", "DISPATCHED"]
            if current_status.upper() not in allowed_alert_from:
                self.send_json({
                    "success": False,
                    "error": f"Cannot send alert from status {current_status}. "
                             f"Alert is only allowed from: {', '.join(allowed_alert_from)}",
                    "current_status": current_status,
                }, 409)
                return

            # Set to DISPATCHED
            INCIDENTS[inc_id]["status"] = "DISPATCHED"
            store.save_incident_status(inc_id, "DISPATCHED")
            store.append_status_log(inc_id, "DISPATCHED",
                f"SIMULATED DISPATCH — Alert sent (training exercise)",
                body.get("responder_id", "GOV-CMD"))

            authority = INCIDENTS[inc_id]["assigned_authority"]
            now = datetime.now(timezone.utc).isoformat()

            self.send_json({
                "success": True,
                "incident_id": inc_id,
                "alert_id": f"ALERT-{os.urandom(3).hex().upper()}",
                "alert_type": "SIMULATED_DISPATCH",
                "status": "DISPATCHED",
                "dispatched_to": authority["name"],
                "eta": f"{authority['eta_mins']} mins",
                "alert_log": (
                    f"SIMULATED DISPATCH — Alert transmitted to {authority['name']} "
                    f"via simulated emergency channel. This is NOT a real government alert."
                ),
                "timestamp": now,
                "note": "Alert is a training simulation and does not reach any live government system.",
            })
            return

        # ── POST /api/reports/submit ──
        if path == "/api/reports/submit":
            try:
                if not body.get("location"):
                    self.send_json({"error": "location is required"}, 400)
                    return
                report = {
                    "id": f"RPT-{os.urandom(3).hex().upper()}",
                    "type": body.get("type", "Smoke plume"),
                    "location": body["location"],
                    "notes": body.get("notes", ""),
                    "gps": body.get("gps"),
                    "time": body.get("time", ""),
                    "status": "SUBMITTED"
                }
                store.add_report(report)
                self.send_json({"success": True, "report": report})
            except Exception as e:
                self.send_json({"error": str(e)}, 500)
            return

        # ── POST /api/reports/verify ──
        if path == "/api/reports/verify":
            try:
                ok, report = store.verify_report(body.get("id", ""))
                if ok:
                    self.send_json({"success": True, "report": report,
                                    "note": "Cross-checked against NASA FIRMS detections and OSM land-use context."})
                else:
                    self.send_json({"error": "Report not found"}, 404)
            except Exception as e:
                self.send_json({"error": str(e)}, 500)
            return

        # ── POST /api/incident/:id/dispatch (legacy) ──
        if "/dispatch" in path:
            try:
                parts = path.split("/")
                inc_id = parts[3]
                if inc_id in INCIDENTS:
                    INCIDENTS[inc_id]["status"] = "DISPATCHED"
                    store.save_incident_status(inc_id, "DISPATCHED")
                    authority = INCIDENTS[inc_id]["assigned_authority"]
                    self.send_json({
                        "success": True,
                        "incident_id": inc_id,
                        "status": "DISPATCHED",
                        "dispatched_to": authority["name"],
                        "eta": f"{authority['eta_mins']} mins",
                        "alert_log": f"SIMULATED DISPATCH to {authority['name']} (Simulated Emergency Channel)"
                    })
                else:
                    self.send_json({"error": "Incident not found"}, 404)
            except Exception as e:
                self.send_json({"error": str(e)}, 500)
            return
        # --- New operational routes ---
        if path.startswith("/api/incident/") and path.endswith("/alert"):
            parts = path.split("/")
            inc_id = parts[3]
            try:
                alert = dispatch_alert(inc_id)
                self.send_json({"success": True, "alert": alert})
            except ValueError as e:
                self.send_json({"error": str(e)}, 404)
            except Exception as e:
                self.send_json({"error": str(e)}, 500)
            return

        if path.startswith("/api/incident/") and "/status" in path:
            parts = path.split("/")
            inc_id = parts[3]
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length).decode("utf-8"))
                new_status = body.get("status", "").upper()
                note = body.get("note", "")
                current = INCIDENTS[inc_id]["status"]

                rec = validate_and_transition(inc_id, current, new_status, "api", note)
                log_transition(rec)
                INCIDENTS[inc_id]["status"] = new_status
                store.save_incident_status(inc_id, new_status)

                self.send_json({
                    "success": True,
                    "incident_id": inc_id,
                    "old_status": rec["old_status"],
                    "new_status": rec["new_status"],
                    "changed_by": rec["changed_by"],
                })
            except ValueError as e:
                self.send_json({"error": str(e)}, 400)
            except KeyError:
                self.send_json({"error": "Incident not found"}, 404)
            except Exception as e:
                self.send_json({"error": str(e)}, 500)
            return

        # ── POST /api/incidents/:id/status (legacy alias, same as PATCH) ──
        if path.startswith("/api/incidents/") and path.endswith("/status"):
            self._handle_status_update(path, body)
            return

        # ── POST /api/incident/:id/status (legacy alias) ──
        if path.startswith("/api/incident/") and "/status" in path:
            self._handle_status_update(path, body)
            return

        self.send_error(404, "Not Found")

    def do_PATCH(self):
        parsed = urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}

        # ── PATCH /api/incidents/:id/status ──
        if path.startswith("/api/incidents/") and path.endswith("/status"):
            self._handle_status_update(path, body)
            return

        self.send_error(404, "Not Found")

    def _handle_status_update(self, path, body):
        """Update incident status with transition validation. Returns 409 on invalid."""
        # Extract incident ID from either /api/incidents/:id/status or /api/incident/:id/status
        parts = path.split("/")
        # Find "incidents" or "incident" index
        try:
            idx = next(i for i, p in enumerate(parts) if p in ("incidents", "incident"))
            inc_id = parts[idx + 1]
        except (StopIteration, IndexError):
            self.send_json({"error": "Invalid path"}, 400)
            return

        new_status = body.get("status", "").upper()
        ground_note = body.get("ground_note", "")
        responder_id = body.get("responder_id", "UNKNOWN")

        if not new_status:
            self.send_json({"error": "status is required"}, 400)
            return

        if inc_id not in INCIDENTS:
            self.send_json({"error": "Incident not found"}, 404)
            return

        # Get current status
        overrides = store.load_incident_overrides()
        current_status = overrides.get(inc_id, {}).get("status", INCIDENTS[inc_id]["status"]).upper()

        # Validate transition
        allowed = VALID_TRANSITIONS.get(current_status, [])
        if new_status not in allowed:
            self.send_json({
                "success": False,
                "error": f"Invalid transition: {current_status} → {new_status}. "
                         f"Allowed: {allowed}",
                "current_status": current_status,
                "requested_status": new_status,
                "allowed_transitions": allowed,
                "transition_table": VALID_TRANSITIONS,
            }, 409)
            return

        # Apply transition
        INCIDENTS[inc_id]["status"] = new_status
        store.save_incident_status(inc_id, new_status)
        store.append_status_log(inc_id, new_status, ground_note, responder_id)

        self.send_json({
            "success": True,
            "incident_id": inc_id,
            "status": new_status,
            "previous_status": current_status,
            "ground_note": ground_note,
            "responder_id": responder_id,
            "message": f"Incident {inc_id} updated from {current_status} to {new_status}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def serve_file(self, filepath, content_type):
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.end_headers()
        with open(filepath, "rb") as f:
            self.wfile.write(f.read())

    def send_json(self, data, status=200):
        body = json.dumps(data, indent=2, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)


def run():
    load_all_scenarios()
    load_facilities()
    httpd = ThreadingHTTPServer(("", PORT), AeroThermalHandler)
    print(f"\n=======================================================")
    print(f" [*] AeroThermal Incident & Responder Platform Online!")
    print(f" [*] SIH26162 NTRO Satellite-to-Ground Disaster Response")
    print(f" [*] URL: http://localhost:{PORT}")
    print(f" [*] Transition validation: ENABLED (409 on invalid)")
    print(f" [*] Simulated alerts: TRAINING ONLY (never real)")
    print(f"=======================================================\n")
    httpd.serve_forever()


if __name__ == "__main__":
    run()
