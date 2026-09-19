from typing import Any, Dict, Optional
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse


class AppException(HTTPException):
    """Custom application exception with structured error payload."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(status_code=status_code, detail=message)
        self.code = code
        self.message = message
        self.details = details or {}


def make_error_response(
    status_code: int,
    code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
) -> JSONResponse:
    """Helper to generate standard JSON error responses."""
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
            }
        },
    )


# Standard HTTP exception helpers
def bad_request_error(message: str = "Bad Request", code: str = "BAD_REQUEST", details: Optional[Dict[str, Any]] = None) -> AppException:
    return AppException(status.HTTP_400_BAD_REQUEST, code, message, details)


def unauthenticated_error(message: str = "Authentication credentials were missing or invalid", code: str = "UNAUTHENTICATED", details: Optional[Dict[str, Any]] = None) -> AppException:
    return AppException(status.HTTP_401_UNAUTHORIZED, code, message, details)


def forbidden_error(message: str = "Access forbidden for current user role", code: str = "FORBIDDEN", details: Optional[Dict[str, Any]] = None) -> AppException:
    return AppException(status.HTTP_403_FORBIDDEN, code, message, details)


def not_found_error(message: str = "Resource not found", code: str = "NOT_FOUND", details: Optional[Dict[str, Any]] = None) -> AppException:
    return AppException(status.HTTP_404_NOT_FOUND, code, message, details)


def conflict_error(message: str = "Resource conflict or invalid state transition", code: str = "CONFLICT", details: Optional[Dict[str, Any]] = None) -> AppException:
    return AppException(status.HTTP_409_CONFLICT, code, message, details)


def validation_error(message: str = "Request validation failed", code: str = "VALIDATION_ERROR", details: Optional[Dict[str, Any]] = None) -> AppException:
    return AppException(status.HTTP_422_UNPROCESSABLE_ENTITY, code, message, details)
