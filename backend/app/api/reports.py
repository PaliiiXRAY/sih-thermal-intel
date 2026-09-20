"""
Reports API Router for FireSense FastAPI Layer.
Handles citizen report submissions and verification against FIRMS context.

Submit stays public (citizen input). Reads and verification are authenticated:
fire-safety operations must not be triggered by anonymous callers.
"""
import os
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from backend import store
from backend.app.core.auth import get_current_user
from backend.app.models.user import User
from backend.app.schemas.report import CitizenReportCreate, CitizenReportVerify

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("")
@router.get("/")
def get_reports(current_user: User = Depends(get_current_user)):
    """Retrieve citizen reports stored on server. Requires authentication."""
    return {"reports": store.get_reports()}


@router.post("/submit")
def submit_report(payload: CitizenReportCreate):
    """Submit a new citizen report. Public."""
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
def verify_report(payload: CitizenReportVerify, current_user: User = Depends(get_current_user)):
    """Verify citizen report against satellite & OSM evidence. Requires authentication."""
    ok, report = store.verify_report(payload.id or "")
    if ok:
        return {
            "success": True,
            "report": report,
            "note": "Cross-checked against NASA FIRMS detections and OSM land-use context."
        }
    return JSONResponse(status_code=404, content={"error": "Report not found"})