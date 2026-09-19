import numpy as np

def build_features(incident):
    """
    Transforms a raw FIRMS incident and its metadata into a feature vector.

    Input: incident (dict)
    Output: features (dict) - a mapping of feature names to numeric values.
    """

    # Default values for missing data
    features = {}

    # --- Thermal Group ---
    # FRP (Fire Radiative Power)
    features['thermal_frp'] = float(incident.get('frp', 0))
    # Brightness Temperature
    features['thermal_bright_temp'] = float(incident.get('bright_temp', 0))
    # Satellite Confidence (assuming 0-1 scale)
    features['thermal_confidence'] = float(incident.get('confidence', 0))

    # --- Temporal Group ---
    # Observation count (number of times this cluster was seen)
    features['temp_obs_count'] = int(incident.get('persistence_count', 1))
    # Duration (days/hours)
    features['temp_duration'] = float(incident.get('duration', 0))
    # Recurrence (has this location fired before in history?)
    features['temp_recurrence'] = int(incident.get('historic_recurrence', 0))
    # Growth (change in FRP over time)
    features['temp_growth_rate'] = float(incident.get('frp_growth', 0))

    # --- Spatial Group ---
    # Distance to nearest industrial facility
    features['spatial_dist_industrial'] = float(incident.get('dist_to_industrial', 1e6))
    # Land cover encoding (simplified: 1 if forest, 0 otherwise)
    # In production, this will be a proper one-hot encoding
    lc = incident.get('land_cover', 'unknown').lower()
    features['spatial_is_forest'] = 1 if lc in ['forest', 'shrubland'] else 0
    features['spatial_is_industrial'] = 1 if lc == 'industrial' else 0
    features['spatial_is_cropland'] = 1 if lc == 'cropland' else 0
    # Distance to settlement
    features['spatial_dist_settlement'] = float(incident.get('dist_to_settlement', 1e6))

    # --- Context Group ---
    # Presence of nearby high-value assets
    features['context_nearby_assets'] = int(incident.get('nearby_assets_count', 0))
    # Baseline thermal anomaly for this region/season
    features['context_baseline_deviation'] = float(incident.get('baseline_deviation', 0))

    return features

if __name__ == "__main__":
    # Mock incident
    mock_incident = {
        'frp': 120.5,
        'bright_temp': 315.2,
        'confidence': 0.9,
        'persistence_count': 5,
        'duration': 2.5,
        'historic_recurrence': 1,
        'frp_growth': 12.0,
        'dist_to_industrial': 450.0,
        'land_cover': 'forest',
        'dist_to_settlement': 1200.0,
        'nearby_assets_count': 2,
        'baseline_deviation': 15.0
    }

    feats = build_features(mock_incident)
    for k, v in feats.items():
        print(f"{k}: {v}")
