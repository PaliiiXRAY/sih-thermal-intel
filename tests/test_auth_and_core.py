import pytest
from datetime import timedelta
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from backend.app.schemas.common import ErrorResponse, RoleEnum, ClassificationEnum, IncidentStatusEnum
from backend.app.schemas.incident import IncidentResponse

client = TestClient(app)


def test_password_hashing():
    """Verify password hashing and verification logic."""
    password = "secret_password123"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrong_password", hashed) is False


def test_jwt_token_creation_and_decoding():
    """Verify JWT access token encoding and decoding."""
    payload = {"sub": "usr_test123", "email": "analyst@firesense.org", "role": "analyst"}
    token = create_access_token(payload, expires_delta=timedelta(minutes=15))
    assert isinstance(token, str)
    assert len(token) > 20

    decoded = decode_access_token(token)
    assert decoded["sub"] == "usr_test123"
    assert decoded["email"] == "analyst@firesense.org"
    assert decoded["role"] == "analyst"


def test_login_flow():
    """Verify POST /auth/login with seed demo accounts."""
    # Test valid analyst login
    login_res = client.post(
        "/auth/login",
        json={"email": "analyst@firesense.org", "password": "password123"}
    )
    assert login_res.status_code == 200
    data = login_res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "analyst@firesense.org"
    assert data["user"]["role"] == "analyst"

    # Test invalid credentials
    invalid_res = client.post(
        "/auth/login",
        json={"email": "analyst@firesense.org", "password": "wrongpassword"}
    )
    assert invalid_res.status_code == 401
    err_data = invalid_res.json()
    assert "error" in err_data
    assert err_data["error"]["code"] == "INVALID_CREDENTIALS"


def test_auth_me_endpoint():
    """Verify GET /auth/me with valid, invalid, and missing tokens."""
    # Missing token -> 401
    r_missing = client.get("/auth/me")
    assert r_missing.status_code == 401
    assert r_missing.json()["error"]["code"] in ["UNAUTHENTICATED", "MISSING_TOKEN"]

    # Invalid token -> 401
    r_invalid = client.get("/auth/me", headers={"Authorization": "Bearer invalid_token_123"})
    assert r_invalid.status_code == 401
    assert r_invalid.json()["error"]["code"] in ["UNAUTHENTICATED", "INVALID_TOKEN"]

    # Valid token -> 200
    token = create_access_token({"sub": "usr_analyst", "email": "analyst@firesense.org", "role": "analyst"})
    r_valid = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r_valid.status_code == 200
    me_data = r_valid.json()
    assert me_data["email"] == "analyst@firesense.org"
    assert me_data["role"] == "analyst"


def test_cors_headers():
    """Verify CORS middleware headers on preflight requests."""
    response = client.options(
        "/auth/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        }
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_error_response_format():
    """Verify error responses adhere to standard shape."""
    res = client.get("/non_existent_route_999")
    assert res.status_code == 404
    data = res.json()
    assert "error" in data
    assert "code" in data["error"]
    assert "message" in data["error"]


def test_pydantic_schema_validation():
    """Verify Pydantic incident schema validation."""
    inc = IncidentResponse(
        id="inc_test_123",
        status="DETECTED",
        classification="INDUSTRIAL_FIRE",
        classification_confidence=0.95,
        risk_score=85.0,
        latitude=21.1458,
        longitude=79.0882,
        created_at="2026-09-19T10:00:00Z",
        updated_at="2026-09-19T10:00:00Z",
    )
    assert inc.classification_confidence == 0.95
    assert inc.risk_score == 85.0
