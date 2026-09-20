"""
P0: legacy AeroThermalHandler authentication.

Unit tests for backend.legacy_auth (stateless HMAC tokens, demo-credential check,
per-IP rate limiter) plus in-process integration tests that boot the real
AeroThermalHandler over HTTP and assert the auth boundary on every write route.
"""
import http.client
import os
import threading
import urllib.parse
from http.server import ThreadingHTTPServer

import pytest

import backend.legacy_auth as auth
from app import AeroThermalHandler


# ── unit: backend.legacy_auth ───────────────────────────────────────────────

@pytest.fixture
def config(monkeypatch):
    monkeypatch.setenv("FIRESENSE_DEMO_PASSWORD", "demo-pw-123")
    monkeypatch.setenv("FIRESENSE_TOKEN_SECRET", "unit-test-token-secret")
    monkeypatch.setattr(auth, "_LOGIN_BUCKETS", {})
    return auth


def test_demo_credentials_accept_known_accounts(config):
    assert auth.verify_demo_credentials("analyst@firesense.org", "demo-pw-123") == "analyst"
    assert auth.verify_demo_credentials("ADMIN@firesense.org", "demo-pw-123") == "admin"


def test_demo_credentials_reject_unknown(config):
    assert auth.verify_demo_credentials("analyst@firesense.org", "wrong-pw") is None
    assert auth.verify_demo_credentials("totally.admin@evil.com", "demo-pw-123") is None
    assert auth.verify_demo_credentials("root@firesense.org", "demo-pw-123") is None


def test_demo_credentials_denied_when_unconfigured(monkeypatch):
    monkeypatch.delenv("FIRESENSE_DEMO_PASSWORD", raising=False)
    monkeypatch.delenv("FIRESENSE_TOKEN_SECRET", raising=False)
    assert auth.verify_demo_credentials("admin@firesense.org", "demo-pw-123") is None


def test_token_roundtrip(config):
    tok = auth.sign_token("analyst@firesense.org", "analyst")
    assert auth.verify_token(tok) == {"email": "analyst@firesense.org", "role": "analyst"}


def test_token_rejects_tampering(config):
    tok = auth.sign_token("admin@firesense.org", "admin")
    tampered = ("a" if tok[0] != "a" else "b") + tok[1:]
    assert auth.verify_token(tampered) is None


def test_token_rejects_wrong_secret(config, monkeypatch):
    tok = auth.sign_token("admin@firesense.org", "admin")
    monkeypatch.setenv("FIRESENSE_TOKEN_SECRET", "different-secret")
    assert auth.verify_token(tok) is None


def test_token_rejects_expired(config):
    tok = auth.sign_token("admin@firesense.org", "admin", ttl_seconds=0)
    assert auth.verify_token(tok) is None


def test_token_rejected_when_unconfigured(config, monkeypatch):
    tok = auth.sign_token("admin@firesense.org", "admin")
    monkeypatch.delenv("FIRESENSE_TOKEN_SECRET", raising=False)
    assert auth.verify_token(tok) is None


def test_authenticated_role(config):
    tok = auth.sign_token("authority@firesense.org", "authority")
    assert auth.authenticated_role(f"Bearer {tok}") == "authority"
    assert auth.authenticated_role("Bearer bogus") is None
    assert auth.authenticated_role("") is None
    assert auth.authenticated_role("Basic dXNlcjpwYXNz") is None


def test_rate_limit_blocks_sixth_attempt(config):
    ip = "10.0.0.1"
    assert all(auth.login_attempt_allowed(ip) for _ in range(5))
    assert auth.login_attempt_allowed(ip) is False
    assert auth.login_attempt_allowed(ip) is False


def test_rate_limit_window_expires(config, monkeypatch):
    clock = {"t": 1_000_000.0}
    monkeypatch.setattr(auth, "_now", lambda: clock["t"])
    ip = "10.0.0.2"
    for _ in range(5):
        assert auth.login_attempt_allowed(ip)
    assert auth.login_attempt_allowed(ip) is False
    clock["t"] += auth.LOGIN_WINDOW_SECONDS + 1
    assert auth.login_attempt_allowed(ip) is True


def test_rate_limit_cleared_on_success(config):
    ip = "10.0.0.3"
    for _ in range(4):
        auth.login_attempt_allowed(ip)
    auth.login_succeeded(ip)
    assert auth.login_attempt_allowed(ip) is True


# ── integration: real AeroThermalHandler over HTTP ──────────────────────────

@pytest.fixture(scope="module")
def live_server():
    """Boot AeroThermalHandler with a known demo config; restore env afterwards."""
    old = {k: os.environ.get(k) for k in ("FIRESENSE_DEMO_PASSWORD", "FIRESENSE_TOKEN_SECRET")}
    os.environ["FIRESENSE_DEMO_PASSWORD"] = "demo-pw-123"
    os.environ["FIRESENSE_TOKEN_SECRET"] = "integration-token-secret"
    auth._LOGIN_BUCKETS.clear()

    server = ThreadingHTTPServer(("127.0.0.1", 0), AeroThermalHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


@pytest.fixture(autouse=True)
def _clear_buckets():
    auth._LOGIN_BUCKETS.clear()
    yield
    auth._LOGIN_BUCKETS.clear()


def _request(method, url, path, body=None, headers=None):
    parts = urllib.parse.urlsplit(url)
    conn = http.client.HTTPConnection(parts.hostname, parts.port, timeout=10)
    payload = None
    if body is not None:
        payload = json.dumps(body) if not isinstance(body, str) else body
    conn.request(method, path, body=payload, headers=headers or {})
    resp = conn.getresponse()
    data = resp.read().decode("utf-8")
    conn.close()
    return resp.status, data


import json  # noqa: E402  (bool: imported after helpers defined)


def _token(url, email="authority@firesense.org", password="demo-pw-123"):
    _, data = _request("POST", url, "/auth/login", {"email": email, "password": password})
    return json.loads(data)["access_token"]


def test_live_login_wrong_password_is_401(live_server):
    status, _ = _request("POST", live_server, "/auth/login", {"email": "admin@firesense.org", "password": "nope"})
    assert status == 401


def test_live_login_unknown_admin_email_is_401(live_server):
    status, _ = _request("POST", live_server, "/auth/login", {"email": "totally.admin@evil.com", "password": "demo-pw-123"})
    assert status == 401


def test_live_login_success_and_me_roundtrip(live_server):
    status, data = _request("POST", live_server, "/auth/login", {"email": "admin@firesense.org", "password": "demo-pw-123"})
    assert status == 200
    token = json.loads(data)["access_token"]
    assert token and token != "demo_token_admin"

    status, me = _request("GET", live_server, "/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert status == 200
    assert json.loads(me)["role"] == "admin"


def test_live_me_rejects_bogus_token(live_server):
    status, _ = _request("GET", live_server, "/auth/me", headers={"Authorization": "Bearer bogus"})
    assert status == 401


def test_live_login_closed_when_unconfigured(live_server, monkeypatch):
    monkeypatch.delenv("FIRESENSE_DEMO_PASSWORD", raising=False)
    monkeypatch.delenv("FIRESENSE_TOKEN_SECRET", raising=False)
    status, _ = _request("POST", live_server, "/auth/login", {"email": "admin@firesense.org", "password": "demo-pw-123"})
    assert status == 503


def test_live_write_routes_require_auth(live_server):
    unauth_actions = [
        ("POST", "/api/incidents/INC-2026-0042/alert", None),
        ("POST", "/api/incidents/INC-2026-0042/status", {"status": "CLOSED"}),
        ("POST", "/api/incident/INC-2026-0042/dispatch", None),
        ("PATCH", "/api/incidents/INC-2026-0042/status", {"status": "RESOLVED"}),
        ("POST", "/api/reports/verify", {"id": "RPT-ABC"}),
    ]
    for method, path, body in unauth_actions:
        status, _ = _request(method, live_server, path, body)
        assert status == 401, f"{method} {path} should be 401 without auth, got {status}"


def test_live_reports_submit_stays_public(live_server):
    status, data = _request("POST", live_server, "/api/reports/submit", {"location": "Test Road, Nagpur"})
    assert status == 200
    assert json.loads(data)["success"] is True


def test_live_role_gate_on_alert(live_server):
    analyst = _token(live_server, "analyst@firesense.org")
    status, _ = _request(
        "POST", live_server, "/api/incidents/INC-2026-0042/alert",
        None, {"Authorization": f"Bearer {analyst}"},
    )
    assert status == 403

    authority = _token(live_server, "authority@firesense.org")
    status, data = _request(
        "POST", live_server, "/api/incidents/INC-2026-0042/alert",
        {}, {"Authorization": f"Bearer {authority}"},
    )
    # Authority passes the role gate; 200 (alert dispatched) or 409 (incident
    # state not alertable e.g. seeded RESOLVED) both prove the gate let it through.
    assert status in (200, 409), data


def test_live_login_rate_limited(live_server):
    for _ in range(5):
        status, _ = _request("POST", live_server, "/auth/login", {"email": "admin@firesense.org", "password": "wrong"})
        assert status == 401
    status, _ = _request("POST", live_server, "/auth/login", {"email": "admin@firesense.org", "password": "wrong"})
    assert status == 429


# ── P1: security headers on every response (200, JSON error, 404) ────────────

EXPECTED_SECURITY_HEADERS = {
    "Content-Security-Policy",
    "X-Content-Type-Options",
    "X-Frame-Options",
    "Referrer-Policy",
    "Permissions-Policy",
}


def _headers(url, method, path, body=None, headers=None):
    parts = urllib.parse.urlsplit(url)
    conn = http.client.HTTPConnection(parts.hostname, parts.port, timeout=10)
    payload = None
    if body is not None:
        payload = json.dumps(body) if not isinstance(body, str) else body
    conn.request(method, path, body=payload, headers=headers or {})
    resp = conn.getresponse()
    resp.read()
    result = {k.lower(): v for k, v in resp.getheaders()}
    conn.close()
    return resp.status, result


def test_live_security_headers_on_html_page(live_server):
    status, h = _headers(live_server, "GET", "/app")
    assert status == 200
    assert h.get("x-frame-options") == "DENY"
    assert h.get("x-content-type-options") == "nosniff"
    assert h.get("referrer-policy") == "no-referrer"
    assert "frame-ancestors 'none'" in h.get("content-security-policy", "")
    assert "geolocation=(self)" in h.get("permissions-policy", "")


def test_live_security_headers_on_json_error(live_server):
    status, h = _headers(live_server, "POST", "/auth/login", {"email": "admin@firesense.org", "password": "nope"})
    assert status == 401
    for name in EXPECTED_SECURITY_HEADERS:
        assert name.lower() in h, f"missing {name} on JSON 401"


def test_live_security_headers_on_404(live_server):
    status, h = _headers(live_server, "GET", "/api/does-not-exist")
    assert status == 404
    for name in EXPECTED_SECURITY_HEADERS:
        assert name.lower() in h, f"missing {name} on 404"