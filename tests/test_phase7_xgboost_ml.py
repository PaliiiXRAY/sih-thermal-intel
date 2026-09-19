"""
Unit & Integration tests for Phase 7: XGBoost ML Classification Layer with Deterministic Fallback.
"""
import uuid
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from geoalchemy2 import WKTElement

from backend.app.main import app
from backend.app.core.config import DATABASE_URL
from backend.app.core.security import create_access_token
from backend.app.models.incident import Incident
from backend.app.models.incident_log import IncidentLog
from backend.app.models.user import User
from backend.app.services.ml.classifier import classify, CANONICAL_CLASSES
from backend.app.services.ml.features import extract_features, FEATURE_NAMES
from backend.app.services.ml.model import load_model, predict_xgboost, MODEL_VERSION

client = TestClient(app)
engine = create_engine(DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    """Provides clean database session for test setup and cleanup."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_users(db_session):
    """Seed test users for each role."""
    users = {}
    roles = ["analyst", "authority", "responder", "admin"]
    for role in roles:
        user_id = f"usr_p7_{role}_{uuid.uuid4().hex[:6]}"
        email = f"p7_{role}_{uuid.uuid4().hex[:6]}@firesense.org"
        u = User(
            id=user_id,
            email=email,
            hashed_password="hash",
            full_name=f"Phase7 Test {role.capitalize()}",
            role=role,
            is_active=True,
        )
        db_session.add(u)
        users[role] = u
    db_session.commit()

    tokens = {
        role: create_access_token({"sub": users[role].id, "email": users[role].email, "role": role})
        for role in roles
    }

    yield {"users": users, "tokens": tokens}

    # Cleanup
    for u in users.values():
        db_session.delete(u)
    db_session.commit()


@pytest.fixture
def phase7_test_incident(db_session):
    """Fixture to create a test incident in PostgreSQL."""
    inc_id = f"inc_p7_{uuid.uuid4().hex[:8]}"
    inc = Incident(
        id=inc_id,
        status="DETECTED",
        severity="HIGH",
        classification=None,
        persistence_score=75.0,
        latitude=21.1458,
        longitude=79.0882,
        geometry=WKTElement("POINT(79.0882 21.1458)", srid=4326),
        explanation={"frp": 65.0, "tags": ["industrial", "refinery"]},
    )
    db_session.add(inc)
    db_session.commit()

    yield inc

    # Cleanup
    db_session.query(IncidentLog).filter(IncidentLog.incident_id == inc_id).delete()
    db_session.query(Incident).filter(Incident.id == inc_id).delete()
    db_session.commit()


# =====================================================================
# FEATURE EXTRACTION & MODEL TESTS (1–7)
# =====================================================================

def test_feature_extraction_deterministic():
    """1. Verify feature extraction produces exact same output for identical inputs."""
    inc_dict = {"frp": 50.0, "persistence_score": 60.0, "latitude": 21.14, "longitude": 79.08, "tags": ["industrial"]}
    f1 = extract_features(inc_dict)
    f2 = extract_features(inc_dict)
    assert f1 == f2


def test_feature_vector_shape_stable():
    """2. Verify feature vector shape is stable (8 numerical features)."""
    f = extract_features({})
    assert len(f) == len(FEATURE_NAMES) == 8
    assert list(f.keys()) == FEATURE_NAMES


def test_canonical_class_set():
    """3. Verify output classes belong strictly to canonical vocabulary."""
    model = load_model()
    assert model is not None
    f = extract_features({"frp": 80.0, "tags": ["industrial"]})
    res = predict_xgboost(f)
    assert res is not None
    assert res["class"] in CANONICAL_CLASSES


def test_model_interface_and_version():
    """4, 5. Verify model interface returns required fields and model version."""
    f = extract_features({"frp": 80.0, "tags": ["industrial"]})
    res = predict_xgboost(f)
    assert res is not None
    assert "class" in res
    assert "confidence" in res
    assert "evidence" in res
    assert "probabilities" in res
    assert res["model_version"] == MODEL_VERSION
    assert res["label_source"] == "XGBOOST"


def test_valid_confidence_range():
    """6. Verify confidence is strictly within range [0.0, 1.0]."""
    f = extract_features({"frp": 30.0, "tags": ["wildfire"]})
    res = predict_xgboost(f)
    assert res is not None
    assert 0.0 <= res["confidence"] <= 1.0
    for prob in res["probabilities"].values():
        assert 0.0 <= prob <= 1.0


def test_no_fabricated_features():
    """7. Verify features handle missing data safely without fabricating data."""
    f = extract_features({})
    assert f["frp"] == 0.0
    assert f["persistence_score"] == 0.0
    assert f["nearest_asset_dist_km"] == 999.0
    assert f["is_industrial_zone"] == 0.0


# =====================================================================
# FALLBACK BEHAVIOR TESTS (8–11)
# =====================================================================

def test_missing_model_artifact_fallback():
    """8. Verify missing model artifact falls back gracefully to deterministic classifier."""
    inc_dict = {"frp": 60.0, "persistence_score": 75.0, "tags": ["industrial"]}
    with patch("backend.app.services.ml.model.load_model", return_value=None):
        res = classify(inc_dict)
        assert res["class"] == "INDUSTRIAL_FIRE"
        assert res["label_source"] == "DETERMINISTIC_RULES"
        assert res["rule_version"] == "v1"


def test_missing_model_artifact_no_runtime_autotrain():
    """9. Verify missing model artifact returns None without auto-training, triggering deterministic fallback."""
    import os
    inc_dict = {"frp": 60.0, "persistence_score": 75.0, "tags": ["industrial"]}
    fake_artifact_path = os.path.join(os.path.dirname(__file__), "nonexistent_xgboost_v1.json")

    with patch("backend.app.services.ml.model._get_artifact_path", return_value=fake_artifact_path), \
         patch("backend.app.services.ml.model._XGB_MODEL", None), \
         patch("backend.app.services.ml.model.train_baseline_model") as mock_train:

        # 1. Call load_model directly when artifact is missing
        model = load_model()
        assert model is None

        # 2. Verify train_baseline_model was NEVER called silently during inference
        mock_train.assert_not_called()

        # 3. Verify classify() invokes deterministic fallback
        res = classify(inc_dict)
        assert res["class"] == "INDUSTRIAL_FIRE"
        assert res["label_source"] == "DETERMINISTIC_RULES"
        assert res["rule_version"] == "v1"

        # 4. Verify fake artifact path was NOT created on disk
        assert not os.path.exists(fake_artifact_path)



def test_model_load_failure_fallback():
    """9. Verify model load exception falls back to deterministic rules."""
    inc_dict = {"frp": 85.0, "landcover": "forest"}
    with patch("backend.app.services.ml.model.load_model", side_effect=Exception("Corrupted model file")):
        res = classify(inc_dict)
        assert res["class"] == "WILDFIRE"
        assert res["label_source"] == "DETERMINISTIC_RULES"


def test_inference_failure_fallback():
    """10. Verify inference exception falls back to deterministic rules."""
    inc_dict = {"frp": 20.0, "landcover": "cropland"}
    with patch("backend.app.services.ml.classifier.predict_xgboost", side_effect=Exception("Feature type mismatch")):
        res = classify(inc_dict)
        assert res["class"] == "CROP_BURNING"
        assert res["label_source"] == "DETERMINISTIC_RULES"



def test_forced_fallback_explanation_source():
    """11. Verify forced fallback correctly identifies label_source as DETERMINISTIC_RULES."""
    inc_dict = {"frp": 60.0, "tags": ["industrial"]}
    res = classify(inc_dict, force_fallback=True)
    assert res["label_source"] == "DETERMINISTIC_RULES"
    assert "rule_version" in res


# =====================================================================
# API INTEGRATION TESTS (12–20)
# =====================================================================

def test_classify_endpoint_with_xgboost_and_db_persistence(test_users, phase7_test_incident, db_session):
    """12, 13, 14, 15, 16. Verify POST /api/incidents/{id}/classify executes XGBoost, updates DB, and writes log."""
    token = test_users["tokens"]["analyst"]
    user_id = test_users["users"]["analyst"].id
    inc_id = phase7_test_incident.id

    res = client.post(f"/api/incidents/{inc_id}/classify", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()

    # Verify classification fields & response shape
    assert data["classification"] in CANONICAL_CLASSES
    assert 0.0 <= data["classification_confidence"] <= 1.0
    assert data["status"] == "CLASSIFIED"

    # Verify explanation metadata
    expl = data["explanation"]
    assert "evidence" in expl
    assert expl["label_source"] in ["XGBOOST", "DETERMINISTIC_RULES"]

    # Verify DB persistence
    db_session.expire_all()
    inc_db = db_session.query(Incident).filter(Incident.id == inc_id).first()
    assert inc_db.classification == data["classification"]
    assert inc_db.status == "CLASSIFIED"

    # Verify Audit log
    log_db = db_session.query(IncidentLog).filter(
        IncidentLog.incident_id == inc_id,
        IncidentLog.action == "CLASSIFY"
    ).first()
    assert log_db is not None
    assert log_db.changed_by == user_id


def test_classification_does_not_move_later_statuses_backward(test_users, phase7_test_incident, db_session):
    """17. Verify re-classifying an incident in ASSESSED status does not move lifecycle backward."""
    token = test_users["tokens"]["analyst"]
    inc_id = phase7_test_incident.id

    # Update status to ASSESSED
    db_session.expire_all()
    inc = db_session.query(Incident).filter(Incident.id == inc_id).first()
    inc.status = "ASSESSED"
    db_session.commit()

    res = client.post(f"/api/incidents/{inc_id}/classify", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["status"] == "ASSESSED"


def test_nonexistent_incident_classify_returns_404(test_users):
    """18. Verify non-existent incident ID returns 404."""
    token = test_users["tokens"]["analyst"]
    res = client.post("/api/incidents/NON_EXISTENT_INC_9999/classify", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 404


def test_unauthorized_role_classify_returns_403(test_users, phase7_test_incident):
    """19. Verify unauthorized role (responder) returns 403."""
    token = test_users["tokens"]["responder"]
    inc_id = phase7_test_incident.id
    res = client.post(f"/api/incidents/{inc_id}/classify", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403


def test_api_v2_classify_compatibility(test_users, phase7_test_incident):
    """20. Verify /api/v2/incidents/{id}/classify compatibility route."""
    token = test_users["tokens"]["analyst"]
    inc_id = phase7_test_incident.id
    res = client.post(f"/api/v2/incidents/{inc_id}/classify", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["id"] == inc_id
