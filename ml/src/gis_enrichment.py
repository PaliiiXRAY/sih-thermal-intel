import pandas as pd
import numpy as np
from scipy.spatial import cKDTree
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def enrich_with_gis(incidents_df, facility_df=None, landcover_df=None):
    """
    Enriches incident data with GIS features: facility proximity and land cover.

    Args:
        incidents_df: DataFrame with ['latitude', 'longitude']
        facility_df: DataFrame with ['latitude', 'longitude', 'type']
        landcover_df: DataFrame with ['latitude', 'longitude', 'class']
    """
    if incidents_df.empty:
        return incidents_df

    # 1. Facility Proximity (e.g., Industrial Plants, Refineries)
    if facility_df is not None and not facility_df.empty:
        # Use cKDTree for fast nearest neighbor search
        # Note: For small areas, Euclidean approximation on deg is okay;
        # for global, we should convert to 3D Cartesian coords.
        facility_coords = facility_df[['latitude', 'longitude']].values
        tree = cKDTree(facility_coords)

        incident_coords = incidents_df[['latitude', 'longitude']].values
        dist, idx = tree.query(incident_coords, k=1)

        # Convert degree distance to approx km (1 deg ~ 111km)
        incidents_df['dist_to_industrial'] = dist * 111.0
        incidents_df['nearest_facility_type'] = facility_df.iloc[idx]['type'].values
    else:
        incidents_df['dist_to_industrial'] = 1e6
        incidents_df['nearest_facility_type'] = 'none'

    # 2. Land Cover Integration
    if landcover_df is not None and not landcover_df.empty:
        # Simplified: find nearest landcover pixel/point
        lc_coords = landcover_df[['latitude', 'longitude']].values
        lc_tree = cKDTree(lc_coords)

        incident_coords = incidents_df[['latitude', 'longitude']].values
        _, lc_idx = lc_tree.query(incident_coords, k=1)

        incidents_df['land_cover'] = landcover_df.iloc[lc_idx]['class'].values
    else:
        incidents_df['land_cover'] = 'unknown'

    return incidents_df

if __name__ == "__main__":
    # Mock Incidents
    incidents = pd.DataFrame({
        'latitude': [23.12, 28.51, 12.0],
        'longitude': [72.51, 77.11, 76.0]
    })

    # Mock Facilities (e.g., a refinery near the first incident)
    facilities = pd.DataFrame({
        'latitude': [23.13, 10.0],
        'longitude': [72.52, 80.0],
        'type': ['refinery', 'factory']
    })

    # Mock Landcover (e.g., forest near the second incident)
    landcover = pd.DataFrame({
        'latitude': [23.10, 28.50, 12.0],
        'longitude': [72.50, 77.10, 76.0],
        'class': ['industrial', 'forest', 'cropland']
    })

    logger.info("Enriching incidents with GIS data...")
    enriched = enrich_with_gis(incidents, facilities, landcover)
    print("\nEnriched Incidents:\n", enriched)
