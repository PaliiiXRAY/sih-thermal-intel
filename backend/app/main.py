"""
FastAPI parallel migration layer.
This runs on port 8000 as the primary entrypoint for the FireSense backend.
"""
import logging
import time
from typing import Any, Dict

import os
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy import text

from backend.app.api import auth, hotspots, incidents, public, reports, responders, stats
from backend.app.core.config import CORS_ORIGINS
from backend.app.core.errors import AppException, make_error_response
from backend.app.db.session import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("firesense.api")

app = FastAPI(
    title="FireSense API",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS if CORS_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request Logging Middleware (Omits secrets/passwords/headers)
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start_time) * 1000.0
    
    # Log sanitized request info
    logger.info(
        f"{request.method} {request.url.path} - {response.status_code} ({duration_ms:.2f}ms)"
    )
    return response


# P1: security headers on every FastAPI response (Docker path).
# Keep in sync with AeroThermalHandler.SECURITY_HEADERS in app.py.
SECURITY_HEADERS = {
    "content-security-policy": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com https://unpkg.com; "
        "style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://unpkg.com; "
        "img-src 'self' data: blob: https://*.tile.openstreetmap.org https://tile.openstreetmap.org; "
        "connect-src 'self'; "
        "frame-ancestors 'none'"
    ),
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "no-referrer",
    "permissions-policy": "camera=(), microphone=(), geolocation=(self)",
}


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    for name, value in SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    return response


# Global Exception Handlers for Centralized Error Format
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return make_error_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors_detail = exc.errors()
    first_msg = errors_detail[0]["msg"] if errors_detail else "Request validation failed"
    return make_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="VALIDATION_ERROR",
        message=f"Validation error: {first_msg}",
        details={"errors": errors_detail},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHENTICATED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
    }
    code = code_map.get(exc.status_code, "HTTP_ERROR")
    msg = str(exc.detail) if exc.detail else "HTTP request error"
    return make_error_response(
        status_code=exc.status_code,
        code=code,
        message=msg,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled server error on {request.url.path}: {exc}", exc_info=True)
    return make_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected server error occurred",
    )


# Health Endpoints
@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/v2/health")
def api_v2_health():
    return {
        "status": "ok",
        "service": "firesense-backend"
    }


@app.get("/api/v2/health/database")
def api_v2_health_database():
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "error", "database": "unavailable", "detail": str(e)}


# Include Auth and API Routers under /api and /api/v2 prefixes
app.include_router(auth.router)

app.include_router(hotspots.router, prefix="/api")
app.include_router(hotspots.router, prefix="/api/v2")

app.include_router(incidents.router, prefix="/api")
app.include_router(incidents.router, prefix="/api/v2")

app.include_router(reports.router, prefix="/api")
app.include_router(reports.router, prefix="/api/v2")

app.include_router(stats.router, prefix="/api")
app.include_router(stats.router, prefix="/api/v2")

app.include_router(public.router)
app.include_router(public.router, prefix="/api")
app.include_router(public.router, prefix="/api/v2")

app.include_router(responders.router, prefix="/api")
app.include_router(responders.router, prefix="/api/v2")

# Mount Static Assets and UI Routes
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "static")
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", response_class=FileResponse)
    @app.get("/landing", response_class=FileResponse)
    @app.get("/index.html", response_class=FileResponse)
    def serve_landing():
        landing_path = os.path.join(STATIC_DIR, "landing.html")
        if os.path.exists(landing_path):
            return FileResponse(landing_path)
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))

    @app.get("/app", response_class=FileResponse)
    @app.get("/dashboard", response_class=FileResponse)
    def serve_app():
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))

