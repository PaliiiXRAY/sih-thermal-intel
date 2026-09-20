"""
P0: env-driven demo-user bootstrap.

Replaces the hardcoded password123 seeding with FIRESENSE_BOOTSTRAP_USERS.
Closed by default: with the env var unset no users are created and login fails.
"""
import json
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.core.config import DATABASE_URL
from backend.app.core.security import bootstrap_demo_users_if_needed, verify_password
from backend.app.main import app
from backend.app.models.user import User

client = TestClient(app)
engine = create_engine(DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def _count(db):
    return db.query(User).count()


def test_bootstrap_noop_without_env(db_session, monkeypatch):
    monkeypatch.delenv("FIRESENSE_BOOTSTRAP_USERS", raising=False)
    before = _count(db_session)
    bootstrap_demo_users_if_needed(db_session)
    assert _count(db_session) == before


def test_bootstrap_creates_users_from_env(db_session):
    db_session.query(User).delete()
    db_session.commit()
    spec = json.loads(os.environ["FIRESENSE_BOOTSTRAP_USERS"])
    assert spec, "conftest must define bootstrap users"
    assert _count(db_session) == 0

    bootstrap_demo_users_if_needed(db_session)

    for uinfo in spec:
        u = db_session.query(User).filter(User.email == uinfo["email"]).one()
        assert u.role == uinfo["role"]
        assert u.is_active is True
        assert verify_password(uinfo["password"], u.hashed_password)


def test_bootstrap_does_not_duplicate(db_session):
    bootstrap_demo_users_if_needed(db_session)
    after_first = _count(db_session)
    bootstrap_demo_users_if_needed(db_session)
    assert _count(db_session) == after_first


def test_login_uses_bootstrapped_credentials():
    """End-to-end: the conftest env password authenticates."""
    res = client.post("/auth/login", json={"email": "admin@firesense.org", "password": "firesense-test-pass"})
    assert res.status_code == 200
    assert res.json()["user"]["role"] == "admin"


def test_login_rejects_legacy_default_password():
    """password123 must no longer authenticate anywhere."""
    res = client.post("/auth/login", json={"email": "admin@firesense.org", "password": "password123"})
    assert res.status_code == 401