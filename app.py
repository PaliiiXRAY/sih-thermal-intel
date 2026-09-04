"""
AeroThermal Core Server (SIH26162)
NASA FIRMS & OSM Incident Response Platform - NTRO
Supports Control Room & First Responder Dashboards with State Machine.
"""
import os
import sys
import json
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.incident_engine import INCIDENTS

PORT = 5002
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")


class AeroThermalHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self.serve_file(os.path.join(STATIC_DIR, "index.html"), "text/html")
            return

        if path.startswith("/static/"):
            file_name = path.replace("/static/", "")
            file_path = os.path.join(STATIC_DIR, file_name)
            if os.path.isfile(file_path):
                ctype = "text/css" if file_name.endswith(".css") else \
                        "application/javascript" if file_name.endswith(".js") else \
                        "text/html"
                self.serve_file(file_path, ctype)
                return

        if path == "/api/incidents":
            self.send_json({"incidents": list(INCIDENTS.values())})
            return

        if path.startswith("/api/incident/"):
            inc_id = path.replace("/api/incident/", "").strip()
            if inc_id in INCIDENTS:
                self.send_json(INCIDENTS[inc_id])
            else:
                self.send_json({"error": "Incident not found"}, 404)
            return

        self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # Update Incident Status (First Responder / Control Room State Machine)
        if "/status" in path:
            try:
                parts = path.split("/")
                inc_id = parts[3]
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length).decode("utf-8"))
                new_status = body.get("status", "NEW").upper()

                if inc_id in INCIDENTS:
                    INCIDENTS[inc_id]["status"] = new_status
                    self.send_json({
                        "success": True,
                        "incident_id": inc_id,
                        "status": new_status,
                        "message": f"Incident {inc_id} updated to {new_status}"
                    })
                else:
                    self.send_json({"error": "Incident not found"}, 404)
            except Exception as e:
                self.send_json({"error": str(e)}, 500)
            return

        # Simulate Dispatch to Authority
        if "/dispatch" in path:
            try:
                parts = path.split("/")
                inc_id = parts[3]
                if inc_id in INCIDENTS:
                    INCIDENTS[inc_id]["status"] = "DISPATCHED"
                    authority = INCIDENTS[inc_id]["assigned_authority"]
                    self.send_json({
                        "success": True,
                        "incident_id": inc_id,
                        "status": "DISPATCHED",
                        "dispatched_to": authority["name"],
                        "eta": f"{authority['eta_mins']} mins",
                        "alert_log": f"ENCRYPTED SOS TRANSMITTED to {authority['name']} (Simulated Emergency Channel)"
                    })
                else:
                    self.send_json({"error": "Incident not found"}, 404)
            except Exception as e:
                self.send_json({"error": str(e)}, 500)
            return

        self.send_error(404, "Not Found")

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
    httpd = HTTPServer(("", PORT), AeroThermalHandler)
    print(f"\n=======================================================")
    print(f" [*] AeroThermal Incident & Responder Platform Online!")
    print(f" [*] SIH26162 NTRO Satellite-to-Ground Disaster Response")
    print(f" [*] URL: http://localhost:{PORT}")
    print(f"=======================================================\n")
    httpd.serve_forever()


if __name__ == "__main__":
    run()
