import json
import os

# Test environment is deterministic and never falls back to a known secret.
# pytest imports this file before any test module, so these variables are in
# place before backend.app.core.config (or anything that imports it) is loaded.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/firesense",
)
os.environ.setdefault(
    "JWT_SECRET_KEY",
    "test-only-firesense-jwt-secret-not-for-production",
)
os.environ.setdefault(
    "FIRESENSE_BOOTSTRAP_USERS",
    json.dumps([
        {"email": "analyst@firesense.org", "password": "firesense-test-pass", "role": "analyst", "full_name": "Analyst User"},
        {"email": "authority@firesense.org", "password": "firesense-test-pass", "role": "authority", "full_name": "Authority User"},
        {"email": "responder@firesense.org", "password": "firesense-test-pass", "role": "responder", "full_name": "Responder User"},
        {"email": "admin@firesense.org", "password": "firesense-test-pass", "role": "admin", "full_name": "Admin User"},
    ]),
)