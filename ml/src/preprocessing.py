import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cluster_incidents(df, eps_km=2.0, min_samples=1):
    """
    Clusters FIRMS detections into incidents using DBSCAN.

    Args:
        df: DataFrame with ['latitude', 'longitude']
        eps_km: Distance threshold in kilometers.
        min_samples: Minimum samples to form a cluster.
    """
    if df.empty:
        return df

    # Convert lat/lon to radians for haversine
    coords = np.radians(df[['latitude', 'longitude']].values)

    # Earth radius in km
    kms_per_radian = 6371.0088
    epsilon = eps_km / kms_per_radian

    db = DBSCAN(eps=epsilon, min_samples=min_samples, algorithm='ball_tree', metric='haversine').fit(coords)
    df['incident_id'] = db.labels_

    # Handle noise (-1) by assigning unique IDs
    noise_mask = df['incident_id'] == -1
    df.loc[noise_mask, 'incident_id'] = range(max(df['incident_id'].max(), 0) + 1,
                                            max(df['incident_id'].max(), 0) + 1 + noise_mask.sum())

    return df

def aggregate_incidents(df):
    """
    Aggregates clustered detections into single incident summaries.
    """
    if df.empty:
        return pd.DataFrame()

    agg_funcs = {
        'frp': 'max',
        'bright_temp': 'mean',
        'confidence': 'mean',
        'latitude': 'mean',
        'longitude': 'mean',
        'acquisition_date': 'first' # Simplified temporal grouping
    }

    # Temporal duration: difference between first and last observation
    # Assuming 'acquisition_date' is datetime
    df['acquisition_date'] = pd.to_datetime(df['acquisition_date'])

    grouped = df.groupby('incident_id').agg(agg_funcs)

    # Calculate persistence and duration
    counts = df.groupby('incident_id').size()
    durations = df.groupby('incident_id')['acquisition_date'].agg(lambda x: (x.max() - x.min()).total_seconds() / 3600)

    grouped['persistence_count'] = counts
    grouped['duration_hours'] = durations

    return grouped.reset_index()

def load_firms_history(file_path):
    """
    Loads raw FIRMS data from CSV.
    """
    try:
        df = pd.read_csv(file_path)
        logger.info(f"Loaded {len(df)} FIRMS detections from {file_path}")
        return df
    except Exception as e:
        logger.error(f"Failed to load FIRMS data: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    # Mock data for testing
    data = {
        'latitude': [23.1, 23.11, 23.12, 28.5, 28.51, 12.0],
        'longitude': [72.5, 72.51, 72.52, 77.1, 77.11, 76.0],
        'frp': [50, 60, 55, 100, 110, 20],
        'bright_temp': [310, 312, 311, 320, 322, 300],
        'confidence': [0.8, 0.9, 0.8, 0.9, 0.9, 0.7],
        'acquisition_date': ['2023-01-01 10:00', '2023-01-01 11:00', '2023-01-01 12:00',
                             '2023-01-01 10:00', '2023-01-01 11:00', '2023-01-01 10:00']
    }
    df_raw = pd.DataFrame(data)

    logger.info("Testing clustering...")
    clustered = cluster_incidents(df_raw)
    print("Clustered Data:\n", clustered[['latitude', 'longitude', 'incident_id']])

    logger.info("Testing aggregation...")
    aggregated = aggregate_incidents(clustered)
    print("\nAggregated Incidents:\n", aggregated)
