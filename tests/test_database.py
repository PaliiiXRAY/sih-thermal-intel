"""
Database Layer Tests for FireSense Backend.
Verifies SQLAlchemy models, connectivity, PostGIS presence, and all 7 core tables.
"""
import pytest
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import OperationalError
from backend.app.core.config import DATABASE_URL
from backend.app.models.user import User
from backend.app.models.hotspot import Hotspot
from backend.app.models.incident import Incident
from backend.app.models.asset import Asset
from backend.app.models.responder import Responder
from backend.app.models.incident_log import IncidentLog
from backend.app.models.alert import Alert
from backend.app.db.base import Base

engine = create_engine(DATABASE_URL)

def is_db_available():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except OperationalError:
        return False

pytestmark = pytest.mark.skipif(not is_db_available(), reason="Database is not available")

def test_database_connection():
    """Verify that SQLAlchemy can connect to the database."""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1")).scalar()
        assert result == 1

def test_postgis_extension_exists():
    """Verify that PostGIS extension is installed and enabled."""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT extname FROM pg_extension WHERE extname = 'postgis'")).scalar()
        assert result == 'postgis'

def test_tables_exist():
    """Verify that all 7 required tables are created by migrations."""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "users" in tables
    assert "hotspots" in tables
    assert "incidents" in tables
    assert "assets" in tables
    assert "responders" in tables
    assert "alerts" in tables
    assert "incident_logs" in tables

def test_spatial_columns():
    """Verify that Hotspot, Incident, Asset, and Responder geometry columns exist."""
    inspector = inspect(engine)
    
    for tbl in ["hotspots", "incidents", "assets", "responders"]:
        cols = [c["name"] for c in inspector.get_columns(tbl)]
        assert "geometry" in cols, f"geometry column missing in {tbl}"

def test_vertical_slice_columns_and_foreign_keys():
    """Verify newly added columns, foreign keys, and renamed fields."""
    inspector = inspect(engine)
    
    incident_cols = [c["name"] for c in inspector.get_columns("incidents")]
    assert "assigned_responder_id" in incident_cols
    
    alert_cols = [c["name"] for c in inspector.get_columns("alerts")]
    assert "target_role" in alert_cols
    assert "recommended_responder_id" in alert_cols
    assert "is_simulated" in alert_cols
    assert "payload" in alert_cols
    
    log_cols = [c["name"] for c in inspector.get_columns("incident_logs")]
    assert "changed_by" in log_cols
    assert "changed_at" in log_cols
    assert "note" in log_cols
    
    # Check foreign keys on incidents and alerts
    inc_fks = [fk["constrained_columns"] for fk in inspector.get_foreign_keys("incidents")]
    assert ["assigned_responder_id"] in inc_fks
    
    alert_fks = [fk["constrained_columns"] for fk in inspector.get_foreign_keys("alerts")]
    assert ["recommended_responder_id"] in alert_fks
    assert ["incident_id"] in alert_fks
