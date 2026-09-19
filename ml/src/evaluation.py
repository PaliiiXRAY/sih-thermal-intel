import pandas as pd
import numpy as np
import pickle
import logging
from sklearn.metrics import confusion_matrix, classification_report
from sklearn.preprocessing import LabelEncoder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def evaluate_pipeline(df, model_path='ml/models/classifier.pkl'):
    """
    Performs a final sanity check on the pipeline.

    Args:
        df: DataFrame containing the same features as training, plus the 'label' (pseudo-labels).
        model_path: Path to the saved model.
    """
    try:
        with open(model_path, 'rb') as f:
            artifacts = pickle.load(f)
            model = artifacts['model']
            le = artifacts['le']
    except FileNotFoundError:
        logger.error(f"Model file not found at {model_path}")
        return

    # Prepare features
    exclude_cols = ['label', 'label_source', 'label_rule_version', 'label_conflict',
                    'latitude', 'longitude', 'nearest_facility_type']
    X = df.drop(columns=[c for c in exclude_cols if c in df.columns])
    y_true = df['label']
    y_encoded = le.transform(y_true)

    # Predict
    y_pred_encoded = model.predict(X)
    y_pred = le.inverse_transform(y_pred_encoded)

    # 1. Class Counts
    logger.info("\n--- Class Distribution (Pseudo-Labels) ---")
    print(y_true.value_counts())

    # 2. Confusion Matrix
    logger.info("\n--- Confusion Matrix ---")
    cm = confusion_matrix(y_encoded, y_pred_encoded)
    cm_df = pd.DataFrame(cm, index=le.classes_, columns=le.classes_)
    print(cm_df)

    # 3. Classification Report
    logger.info("\n--- Final Classification Report ---")
    print(classification_report(y_encoded, y_pred_encoded, target_names=le.classes_))

if __name__ == "__main__":
    # Create a synthetic dataset that mimics real-world distribution
    np.random.seed(42)
    n_samples = 1000

    # Generate features (complete set to match model training)
    data = {
        'thermal_frp': np.random.exponential(40, n_samples),
        'thermal_bright_temp': np.random.uniform(300, 350, n_samples),
        'thermal_confidence': np.random.uniform(0, 1, n_samples),
        'temp_obs_count': np.random.randint(1, 20, n_samples),
        'temp_duration': np.random.uniform(0, 10, n_samples),
        'temp_recurrence': np.random.randint(0, 2, n_samples),
        'temp_growth_rate': np.random.uniform(-10, 10, n_samples),
        'spatial_dist_industrial': np.random.uniform(0, 10000, n_samples),
        'spatial_is_forest': np.random.choice([0, 1], n_samples, p=[0.7, 0.3]),
        'spatial_is_industrial': np.random.choice([0, 1], n_samples, p=[0.8, 0.2]),
        'spatial_is_cropland': np.random.choice([0, 1], n_samples, p=[0.7, 0.3]),
        'spatial_dist_settlement': np.random.uniform(0, 10000, n_samples),
        'context_nearby_assets': np.random.randint(0, 5, n_samples),
        'context_baseline_deviation': np.random.uniform(-20, 20, n_samples),
    }
    df = pd.DataFrame(data)

    # Pseudo-labeling logic (simple version of weak_supervision)
    def pseudo_label(row):
        if row['spatial_dist_industrial'] < 1000 and row['thermal_frp'] > 50: return 'INDUSTRIAL_FIRE'
        if row['temp_obs_count'] > 10 and row['spatial_is_industrial']: return 'GAS_FLARE'
        if row['spatial_is_forest'] and row['thermal_frp'] > 30: return 'WILDFIRE'
        if row['spatial_is_cropland'] and row['temp_obs_count'] < 3: return 'CROP_BURNING'
        return 'UNKNOWN'

    df['label'] = df.apply(pseudo_label, axis=1)

    logger.info("Running final pipeline evaluation...")
    evaluate_pipeline(df)
