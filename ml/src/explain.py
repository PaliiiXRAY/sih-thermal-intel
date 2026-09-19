import numpy as np
import pandas as pd
import pickle
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_evidence_strings(model, features_df, incident_idx):
    """
    Generates human-readable evidence strings based on feature values
    and model importance.
    """
    row = features_df.iloc[incident_idx]
    evidence = []

    # Define thresholds/rules for evidence mapping
    # These mirror the weak supervision logic but are applied to feature vectors
    if row.get('spatial_dist_industrial', 1e6) < 1000:
        evidence.append("industrial_proximity")
    if row.get('thermal_frp', 0) > 50:
        evidence.append("high_frp")
    if row.get('temp_obs_count', 0) > 10:
        evidence.append("persistence_5_obs")
    if row.get('spatial_is_forest', 0) == 1:
        evidence.append("forest_landcover")
    if row.get('spatial_is_industrial', 0) == 1:
        evidence.append("industrial_landcover")
    if row.get('spatial_is_cropland', 0) == 1:
        evidence.append("cropland_landcover")
    if row.get('temp_duration', 0) < 3:
        evidence.append("short_duration")

    return evidence

def explain_prediction(incident_features, model_path='ml/models/classifier.pkl'):
    """
    Combines model prediction with evidence generation.
    """
    try:
        with open(model_path, 'rb') as f:
            artifacts = pickle.load(f)
            model = artifacts['model']
            le = artifacts['le']
    except FileNotFoundError:
        logger.error(f"Model file not found at {model_path}")
        return None

    # Convert features to DataFrame for consistency
    features_df = pd.DataFrame([incident_features])

    # Prediction
    probs = model.predict_proba(features_df)[0]
    best_class_idx = np.argmax(probs)
    confidence = probs[best_class_idx]
    label = le.inverse_transform([best_class_idx])[0]

    # Evidence
    evidence = get_evidence_strings(model, features_df, 0)

    return {
        "class": label,
        "confidence": float(confidence),
        "evidence": evidence
    }

if __name__ == "__main__":
    # Mock feature vector (similar to output of feature_engineering.py)
    mock_features = {
        'thermal_frp': 120.0,
        'thermal_bright_temp': 315.0,
        'thermal_confidence': 0.9,
        'temp_obs_count': 15,
        'temp_duration': 2.5,
        'temp_recurrence': 1,
        'temp_growth_rate': 5.0,
        'spatial_dist_industrial': 400.0,
        'spatial_is_forest': 0,
        'spatial_is_industrial': 1,
        'spatial_is_cropland': 0,
        'spatial_dist_settlement': 1000.0,
        'context_nearby_assets': 2,
        'context_baseline_deviation': 10.0
    }

    logger.info("Generating explanation for mock incident...")
    result = explain_prediction(mock_features)
    print("\nExplanation Result:\n", result)
