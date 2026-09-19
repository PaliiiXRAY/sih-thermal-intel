"""
Stats API Router for FireSense FastAPI Layer.
Exposes platform-wide statistical metrics.
"""
from fastapi import APIRouter, HTTPException

from backend.stats import compute_stats

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("")
@router.get("/")
def get_stats():
    """Compute and return platform statistics."""
    try:
        return compute_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
