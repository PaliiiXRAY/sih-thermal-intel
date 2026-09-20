"""
Secrets-discipline guards (P0).

Refuses to let a known fallback secret silently back into the FastAPI config,
docker-compose, .env.example, or the legacy app.py query-param handling.
"""
import importlib
import os
import pathlib

import pytest

import backend.app.core.config as config

REPO = pathlib.Path(__file__).resolve().parent.parent


def test_config_reads_required_secret_from_env():
    assert config.JWT_SECRET_KEY == os.environ["JWT_SECRET_KEY"]


def test_config_refuses_to_run_without_jwt_secret(monkeypatch):
    # Empty string is treated as unset by the loader but survives python-dotenv.
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/test")
    monkeypatch.setenv("JWT_SECRET_KEY", "")
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        importlib.reload(config)


def test_config_refuses_to_run_without_database_url(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "some-secret")
    monkeypatch.setenv("DATABASE_URL", "")
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        importlib.reload(config)


def test_docker_compose_has_no_committed_secrets():
    text = (REPO / "docker-compose.yml").read_text(encoding="utf-8")
    assert "6cb2a1966681605e7843b31f1d248329" not in text  # NASA FIRMS key
    assert "firesense-docker-production-secret-key" not in text
    assert "password123" not in text
    # Real secrets must come from the environment, never from the file.
    assert "${JWT_SECRET_KEY:?JWT_SECRET_KEY" in text
    assert "${FIRMS_MAP_KEY:?FIRMS_MAP_KEY" in text
    assert "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD" in text


def test_env_example_has_no_committed_secrets():
    text = (REPO / ".env.example").read_text(encoding="utf-8")
    assert "6cb2a1966681605e7843b31f1d248329" not in text
    assert "password123" not in text
    assert "JWT_SECRET_KEY" in text
    assert "FIRESENSE_TOKEN_SECRET" in text
    assert "FIRESENSE_DEMO_PASSWORD" in text


def test_legacy_app_does_not_accept_map_key_query_param():
    text = (REPO / "app.py").read_text(encoding="utf-8")
    assert 'qs.get("map_key"' not in text