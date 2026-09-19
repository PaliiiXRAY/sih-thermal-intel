"""
Reports API Router for FireSense FastAPI Layer.
Handles citizen report submissions and verification against FIRMS context.
"""
import os
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend import store
from backend.app.schemas.report import CitizenReportCreate, CitizenReportVerify

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("")
@router.get("/")
def get_reports():
    """Retrieve citizen reports stored on server."""
    return {"reports": store.get_reports()}


@router.post("/submit")
def submit_report(payload: CitizenReportCreate):
    """Submit a new citizen report."""
    if not payload.location:
        return JSONResponse(status_code=400, content={"error": "location is required"})

    report = {
        "id": f"RPT-{os.urandom(3).hex().upper()}",
        "type": payload.type or "Smoke plume",
        "location": payload.location,
        "notes": payload.notes or "",
        "gps": payload.gps,
        "time": payload.time or "",
        "status": "SUBMITTED"
    }
    store.add_report(report)
    return {"success": True, "report": report}


@router.post("/verify")
def verify_report(payload: CitizenReportVerify):
    """Verify citizen report against satellite & OSM evidence."""
    ok, report = store.verify_report(payload.id or "")
    if ok:
        return {
            "success": True,
            "report": report,
            "note": "Cross-checked against NASA FIRMS detections and OSM land-use context."
        }
    return JSONResponse(status_code=404, content={"error": "Report not found"})
