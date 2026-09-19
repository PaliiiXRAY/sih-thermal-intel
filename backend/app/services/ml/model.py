"""
XGBoost ML Classifier Model Service for FireSense.
Provides model artifact loading, feature vector mapping, and multi-class probability inference.
Model Version: xgboost-v1

MODEL SAFETY & CORRECTNESS DISCLOSURES:
1. Training Data Status:
   - xgboost-v1 was trained on a curated synthetic benchmark dataset (train_baseline_model).
   - It is a baseline/demonstration model artifact and NOT trained on a production satellite fire dataset.
   - No scientific operational accuracy claim is made. Real-world operational deployment requires representative
     labeled satellite fire datasets and rigorous statistical evaluation.
2. Confidence Semantics:
   - classification_confidence exposes the model's top-class output score (uncalibrated probability).
   - It is NOT a calibrated probability, NOT the probability of a physical fire, and NOT the calibrated probability
     that the model prediction is statistically correct.
   - Satellite detection confidence (detection_confidence) and risk index (risk_score) are kept completely separate.
3. Raw Coordinate Feature Limitation:
   - latitude and longitude coordinates are included as features in this baseline prototype demonstration.
   - Note: Raw coordinates may introduce geographic shortcut bias; production training should utilize spatial regional
     embeddings or contextual proximity features instead.
4. Model Artifact Loading & Fallback Safety:
   - If the xgboost-v1.json artifact is missing or corrupted, load_model() immediately returns None.
   - Silent runtime auto-training during inference requests is strictly forbidden; offline fallback to deterministic
     rules (classifier.py) is activated automatically.
"""
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from backend.app.services.ml.features import FEATURE_NAMES

logger = logging.getLogger("firesense.ml")

MODEL_VERSION = "xgboost-v1"

# Frozen Canonical Class Order
CLASS_INDEX_MAP = {
    0: "INDUSTRIAL_FIRE",
    1: "GAS_FLARE",
    2: "WILDFIRE",
    3: "CROP_BURNING",
    4: "MINING_OTHER",
    5: "UNKNOWN",
}
CLASS_NAME_MAP = {v: k for k, v in CLASS_INDEX_MAP.items()}

# Global cached XGBoost model instance
_XGB_MODEL: Optional[Any] = None


def _get_artifact_path() -> str:
    """Return path to saved XGBoost model artifact."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    artifacts_dir = os.path.join(base_dir, "artifacts")
    os.makedirs(artifacts_dir, exist_ok=True)
    return os.path.join(artifacts_dir, f"{MODEL_VERSION}.json")


def load_model() -> Optional[Any]:
    """
    Load XGBoost model from versioned artifact file (xgboost-v1.json).
    Returns None if XGBoost module is missing, artifact is missing, or artifact fails to load.
    
    CRITICAL: Does NOT perform runtime auto-training if artifact is missing.
    Inference requests must never silently trigger model training; missing artifacts trigger deterministic fallback.
    """
    global _XGB_MODEL
    if _XGB_MODEL is not None:
        return _XGB_MODEL

    try:
        import xgboost as xgb
    except ImportError:
        logger.warning("XGBoost module not installed. ML inference disabled; fallback active.")
        return None

    artifact_path = _get_artifact_path()
    if not os.path.exists(artifact_path):
        logger.warning(f"XGBoost model artifact not found at {artifact_path}. Runtime auto-training is disabled; fallback active.")
        return None

    model = xgb.XGBClassifier()
    try:
        model.load_model(artifact_path)
        _XGB_MODEL = model
        logger.info(f"Loaded XGBoost model artifact successfully: {artifact_path}")
        return _XGB_MODEL
    except Exception as e:
        logger.warning(f"Failed to load XGBoost artifact {artifact_path}: {e}")
        return None



def train_baseline_model(save: bool = True) -> Any:
    """
    Train a baseline XGBoost multiclass model on a curated benchmark feature dataset.

    Returns:
        Trained XGBClassifier model.
    """
    import numpy as np
    import xgboost as xgb

    # Curated training feature vectors matching FEATURE_NAMES (8 features)
    # [frp, persistence, lat, lon, nearest_asset_dist, is_ind, is_forest, is_crop]
    base_samples = [
        # INDUSTRIAL_FIRE (class 0)
        ([75.0, 60.0, 0.0, 0.0, 1.2, 1.0, 0.0, 0.0], 0),
        ([65.0, 75.0, 0.0, 0.0, 1.0, 1.0, 0.0, 0.0], 0),
        ([90.0, 50.0, 22.30, 78.40, 2.5, 1.0, 0.0, 0.0], 0),
        # GAS_FLARE (class 1)
        ([35.0, 90.0, 0.0, 0.0, 0.5, 1.0, 0.0, 0.0], 1),
        ([30.0, 85.0, 0.0, 0.0, 0.8, 1.0, 0.0, 0.0], 1),
        ([40.0, 95.0, 21.14, 79.08, 0.4, 1.0, 0.0, 0.0], 1),
        # WILDFIRE (class 2)
        ([85.0, 30.0, 0.0, 0.0, 15.0, 0.0, 1.0, 0.0], 2),
        ([70.0, 25.0, 0.0, 0.0, 20.0, 0.0, 1.0, 0.0], 2),
        ([95.0, 40.0, 20.20, 84.10, 25.0, 0.0, 1.0, 0.0], 2),
        # CROP_BURNING (class 3)
        ([15.0, 20.0, 0.0, 0.0, 5.0, 0.0, 0.0, 1.0], 3),
        ([20.0, 15.0, 0.0, 0.0, 8.0, 0.0, 0.0, 1.0], 3),
        ([12.0, 10.0, 29.80, 76.20, 12.0, 0.0, 0.0, 1.0], 3),
        # MINING_OTHER (class 4)
        ([0.0, 50.0, 0.0, 0.0, 2.0, 0.0, 0.0, 0.0], 4),
        ([45.0, 55.0, 0.0, 0.0, 3.0, 0.0, 0.0, 0.0], 4),
        ([50.0, 60.0, 24.10, 85.90, 2.0, 0.0, 0.0, 0.0], 4),
        # UNKNOWN (class 5)
        ([0.0, 0.0, 0.0, 0.0, 999.0, 0.0, 0.0, 0.0], 5),
        ([5.0, 5.0, 0.0, 0.0, 50.0, 0.0, 0.0, 0.0], 5),
    ]

    X_list = []
    y_list = []
    # Replicate base samples 5 times to provide sufficient sample mass for decision boundary fitting
    for vec, cls in base_samples:
        for _ in range(5):
            X_list.append(vec)
            y_list.append(cls)

    X_sample = np.array(X_list, dtype=np.float32)
    y_sample = np.array(y_list, dtype=np.int32)

    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.2,
        objective="multi:softprob",
        num_class=6,
        random_state=42,
    )
    model.fit(X_sample, y_sample)

    if save:
        artifact_path = _get_artifact_path()
        model.save_model(artifact_path)
        logger.info(f"Trained and saved baseline XGBoost model artifact to {artifact_path}")

    return model


def predict_xgboost(
    feature_dict: Dict[str, float]
) -> Optional[Dict[str, Any]]:
    """
    Perform ML inference using XGBoost model.

    Args:
        feature_dict: Extracted numerical feature dictionary.

    Returns:
        Classification result dict or None if model unavailable/failed.
    """
    # Guardrail: If zero meaningful signals present, return None to trigger deterministic fallback
    has_signals = any(
        feature_dict.get(fn, 0.0) != 0.0 for fn in ["frp", "persistence_score", "is_industrial_zone", "is_forest_zone", "is_agricultural_zone"]
    )
    if not has_signals:
        return None

    model = load_model()
    if model is None:
        return None

    try:
        import numpy as np

        # Construct 8-element feature vector in exact order
        vector = [feature_dict.get(fn, 0.0) for fn in FEATURE_NAMES]
        X_in = np.array([vector], dtype=np.float32)

        probs = model.predict_proba(X_in)[0]  # Array of 6 probabilities
        best_idx = int(np.argmax(probs))
        best_class = CLASS_INDEX_MAP.get(best_idx, "UNKNOWN")
        confidence = round(float(probs[best_idx]), 4)

        # Probabilities map
        prob_dict = {
            CLASS_INDEX_MAP[i]: round(float(probs[i]), 4)
            for i in range(len(probs))
        }

        # Structured evidence explanations matching existing format
        evidence = [
            f"XGBoost multiclass inference prediction: {best_class} (model_version: {MODEL_VERSION})",
            f"Model prediction confidence score: {confidence:.4f}",
        ]
        if feature_dict.get("is_industrial_zone") == 1.0:
            evidence.append("Facility tag or landcover matches gas flare / refinery / industrial infrastructure signature")
        if feature_dict.get("is_forest_zone") == 1.0:
            evidence.append("Landcover or location tag indicates forest/wildland vegetation cover")
        if feature_dict.get("is_agricultural_zone") == 1.0:
            evidence.append("Agricultural or cropland landcover classification")
        if feature_dict.get("frp", 0.0) > 0.0:
            evidence.append(f"Thermal intensity FRP {feature_dict['frp']:.1f} MW")
        if feature_dict.get("persistence_score", 0.0) > 0.0:
            evidence.append(f"Thermal persistence score {feature_dict['persistence_score']:.1f}")

        return {
            "class": best_class,
            "confidence": confidence,
            "evidence": evidence,
            "probabilities": prob_dict,
            "label_source": "XGBOOST",
            "model_version": MODEL_VERSION,
        }
    except Exception as e:
        logger.warning(f"XGBoost inference failed ({e}); returning None for deterministic fallback.")
        return None
