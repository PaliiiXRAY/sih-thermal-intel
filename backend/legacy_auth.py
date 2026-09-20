"""
Stateless HMAC-signed token auth for the legacy AeroThermalHandler (app.py).
Stdlib-only so the serverless path stays dependency-free.

Closed by default: with FIRESENSE_DEMO_PASSWORD or FIRESENSE_TOKEN_SECRET unset,
login refuses (503) and every auth-gated call returns 401. There is no
hardcoded or default credential anywhere.
"""
import base64
import hashlib
import hmac
import os
import time
from typing import Dict, Optional

# The only accounts the legacy demo server recognizes. The role is derived from
# an exact address match — a substring like "admin" inside an arbitrary email
# no longer grants anything.
DEMO_ACCOUNTS: Dict[str, str] = {
    "admin@firesense.org": "admin",
    "authority@firesense.org": "authority",
    "responder@firesense.org": "responder",
    "analyst@firesense.org": "analyst",
}

LOGIN_MAX_ATTEMPTS = 5
LOGIN_WINDOW_SECONDS = 60

# ponytail: in-memory per-instance limiter. On a multi-instance deployment
# (Vercel lambdas) each instance keeps its own bucket, so the global limit is
# instances * 5/min. Upgrade path: edge middleware or a shared Redis counter.
_LOGIN_BUCKETS: Dict[str, list] = {}

_now = time.time


def demo_password() -> Optional[str]:
    return os.environ.get("FIRESENSE_DEMO_PASSWORD")


def token_secret() -> Optional[str]:
    return os.environ.get("FIRESENSE_TOKEN_SECRET")


def is_auth_configured() -> bool:
    return bool(demo_password() and token_secret())


def verify_demo_credentials(email: str, password: str) -> Optional[str]:
    """Return the role for a known demo account + configured password, else None."""
    if not is_auth_configured():
        return None
    role = DEMO_ACCOUNTS.get((email or "").strip().lower())
    if role is None:
        return None
    expected = demo_password() or ""
    if not hmac.compare_digest(password or "", expected):
        return None
    return role


def _hmac_digest(payload_b64: str) -> bytes:
    secret = token_secret()
    if not secret:
        raise RuntimeError("FIRESENSE_TOKEN_SECRET not configured")
    return hmac.new(secret.encode("utf-8"), payload_b64.encode("ascii"), hashlib.sha256).digest()


def sign_token(email: str, role: str, ttl_seconds: int = 3600) -> str:
    """Mint a stateless token: base64(email|role|exp).base64(hmac)."""
    exp = int(_now()) + ttl_seconds
    payload_b64 = base64.urlsafe_b64encode(f"{email}|{role}|{exp}".encode("utf-8")).decode("ascii")
    sig_b64 = base64.urlsafe_b64encode(_hmac_digest(payload_b64)).decode("ascii")
    return f"{payload_b64}.{sig_b64}"


def verify_token(token: str) -> Optional[Dict[str, str]]:
    """Return {email, role} for a valid, unexpired token; None otherwise."""
    if not token_secret():
        return None
    try:
        payload_b64, sig_b64 = token.split(".", 1)
        expected = base64.urlsafe_b64encode(_hmac_digest(payload_b64)).decode("ascii")
        if not hmac.compare_digest(expected, sig_b64):
            return None
        payload = base64.urlsafe_b64decode(payload_b64.encode("ascii")).decode("utf-8")
        email, role, exp = payload.split("|")
        if int(exp) <= int(_now()):
            return None
        if role not in DEMO_ACCOUNTS.values():
            return None
        return {"email": email, "role": role}
    except Exception:
        return None


def authenticated_role(auth_header: str) -> Optional[str]:
    """Parse 'Bearer <token>', verify it, return the role; None on any failure."""
    if not auth_header:
        return None
    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    info = verify_token(token.strip())
    return info["role"] if info else None


def login_attempt_allowed(ip: str) -> bool:
    """True if this IP may attempt another login (≤ LOGIN_MAX_ATTEMPTS / window)."""
    now = _now()
    attempts = [t for t in _LOGIN_BUCKETS.get(ip, []) if now - t < LOGIN_WINDOW_SECONDS]
    if len(attempts) >= LOGIN_MAX_ATTEMPTS:
        _LOGIN_BUCKETS[ip] = attempts
        return False
    attempts.append(now)
    _LOGIN_BUCKETS[ip] = attempts
    return True


def login_succeeded(ip: str) -> None:
    """Clear the attempt bucket for an IP after a successful login."""
    _LOGIN_BUCKETS.pop(ip, None)