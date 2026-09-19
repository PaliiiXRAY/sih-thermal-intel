import pandas as pd
import numpy as np
import xgboost as xgb
import pickle
import logging
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.preprocessing import LabelEncoder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def train_classifier(df):
    """
    Trains an XGBoost multi-class classifier on pseudo-labels.

    Args:
        df: DataFrame containing features and 'label'
    Returns:
        model, label_encoder
    """
    # 1. Prepare features and labels
    # Exclude metadata and target from features
    exclude_cols = ['label', 'label_source', 'label_rule_version', 'label_conflict',
                    'latitude', 'longitude', 'nearest_facility_type']
    X = df.drop(columns=[c for c in exclude_cols if c in df.columns])
    y_raw = df['label']

    # Encode labels (GAS_FLARE, etc.) to integers
    le = LabelEncoder()
    y = le.fit_transform(y_raw)

    # 2. Handle Class Imbalance
    # Calculate class weights
    class_counts = np.bincount(y)
    total_samples = len(y)
    # weight = total / (num_classes * count)
    weights = total_samples / (len(class_counts) * class_counts)
    sample_weights = np.array([weights[label] for label in y])

    # 3. Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Split sample weights separately
    sw_all = sample_weights
    # We need to index weights using the same split indices
    # To do this properly, let's get the indices
    indices = np.arange(len(y))
    idx_train, idx_test = train_test_split(
        indices, test_size=0.2, random_state=42, stratify=y
    )
    sw_train = sample_weights[idx_train]
    sw_test = sample_weights[idx_test]
    # Re-assign X and y using these indices to ensure consistency
    X_train, X_test = X.iloc[idx_train], X.iloc[idx_test]
    y_train, y_test = y[idx_train], y[idx_test]

    # 4. Train XGBoost
    # Using multi:softprob for confidence scores
    model = xgb.XGBClassifier(
        objective='multi:softprob',
        num_class=len(le.classes_),
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        random_state=42
    )

    model.fit(X_train, y_train, sample_weight=sw_train)

    # 5. Evaluation (Sanity Check)
    y_pred = model.predict(X_test)
    logger.info("\n--- Model Sanity Check ---")
    logger.info("\n" + classification_report(y_test, y_pred, target_names=le.classes_))

    return model, le

def save_model(model, le, path='ml/models/classifier.pkl'):
    """Saves the model and label encoder."""
    with open(path, 'wb') as f:
        pickle.dump({'model': model, 'le': le}, f)
    logger.info(f"Model saved to {path}")

if __name__ == "__main__":
    # Create a synthetic dataset for testing
    # Features based on feature_engineering.py
    np.random.seed(42)
    n_samples = 1000

    data = {
        'thermal_frp': np.random.uniform(0, 200, n_samples),
        'thermal_bright_temp': np.random.uniform(300, 350, n_samples),
        'thermal_confidence': np.random.uniform(0, 1, n_samples),
        'temp_obs_count': np.random.randint(1, 20, n_samples),
        'temp_duration': np.random.uniform(0, 10, n_samples),
        'temp_recurrence': np.random.randint(0, 2, n_samples),
        'temp_growth_rate': np.random.uniform(-10, 10, n_samples),
        'spatial_dist_industrial': np.random.uniform(0, 10000, n_samples),
        'spatial_is_forest': np.random.randint(0, 2, n_samples),
        'spatial_is_industrial': np.random.randint(0, 2, n_samples),
        'spatial_is_cropland': np.random.randint(0, 2, n_samples),
        'spatial_dist_settlement': np.random.uniform(0, 10000, n_samples),
        'context_nearby_assets': np.random.randint(0, 5, n_samples),
        'context_baseline_deviation': np.random.uniform(-20, 20, n_samples),
    }
    df = pd.DataFrame(data)

    # Simple synthetic labeling to simulate weak supervision output
    def synthetic_label(row):
        if row['spatial_dist_industrial'] < 500 and row['thermal_frp'] > 100: return 'INDUSTRIAL_FIRE'
        if row['temp_obs_count'] > 12 and row['spatial_is_industrial']: return 'GAS_FLARE'
        if row['spatial_is_forest'] and row['thermal_frp'] > 50: return 'WILDFIRE'
        if row['spatial_is_cropland'] and row['temp_obs_count'] < 3: return 'CROP_BURNING'
        return 'UNKNOWN'

    df['label'] = df.apply(synthetic_label, axis=1)

    logger.info("Training XGBoost classifier...")
    model, le = train_classifier(df)
    save_model(model, le)
