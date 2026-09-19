import pandas as pd
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Label Versions
VERSION = "1.0.0"

def label_gas_flare(row):
    """
    Labeling Function for GAS_FLARE.
    Guardrail: Persistence alone is insufficient. Requires industrial context.
    """
    # Logic: High persistence AND (Industrial landcover OR proximity to refinery)
    if row.get('persistence_count', 0) > 10 and \
       (row.get('land_cover') == 'industrial' or row.get('nearest_facility_type') == 'refinery'):
        return "GAS_FLARE", "rule_flare_persistence_industrial"
    return None, None

def label_industrial_fire(row):
    """
    Labeling Function for INDUSTRIAL_FIRE.
    Logic: High thermal signal AND very close to industrial facility.
    """
    if row.get('dist_to_industrial', 1e6) < 1000 and row.get('frp', 0) > 50:
        return "INDUSTRIAL_FIRE", "rule_ind_proximity_thermal"
    return None, None

def label_wildfire(row):
    """
    Labeling Function for WILDFIRE.
    Guardrail: Land cover alone cannot label wildfire. Requires thermal signal.
    """
    if row.get('land_cover') in ['forest', 'shrubland'] and row.get('frp', 0) > 30:
        return "WILDFIRE", "rule_wild_forest_thermal"
    return None, None

def label_crop_burning(row):
    """
    Labeling Function for CROP_BURNING.
    Logic: Cropland AND low persistence.
    """
    if row.get('land_cover') == 'cropland' and row.get('persistence_count', 0) < 3:
        return "CROP_BURNING", "rule_crop_land_low_persist"
    return None, None

def label_mining_other(row):
    """
    Labeling Function for MINING/OTHER.
    Logic: Industrial context but not meeting flare/fire criteria.
    """
    if row.get('land_cover') == 'industrial' or row.get('nearest_facility_type') == 'mine':
        return "MINING/OTHER", "rule_industrial_generic"
    return None, None

# Registry of labeling functions
LABELING_FUNCTIONS = [
    label_gas_flare,
    label_industrial_fire,
    label_wildfire,
    label_crop_burning,
    label_mining_other
]

def apply_weak_supervision(df):
    """
    Applies versioned labeling functions to the dataset.

    Returns:
        df with [label, label_source, label_rule_version, label_conflict]
    """
    labels = []
    sources = []
    conflicts = []

    for _, row in df.iterrows():
        matched_labels = []
        matched_sources = []

        for func in LABELING_FUNCTIONS:
            label, source = func(row)
            if label:
                matched_labels.append(label)
                matched_sources.append(source)

        if not matched_labels:
            labels.append("UNKNOWN")
            sources.append("default")
            conflicts.append(False)
        elif len(matched_labels) > 1:
            # Conflict: Multiple rules triggered
            # Simple resolution: Pick the first one, but mark conflict
            labels.append(matched_labels[0])
            sources.append(matched_sources[0])
            conflicts.append(True)
        else:
            labels.append(matched_labels[0])
            sources.append(matched_sources[0])
            conflicts.append(False)

    df['label'] = labels
    df['label_source'] = sources
    df['label_rule_version'] = VERSION
    df['label_conflict'] = conflicts

    return df

if __name__ == "__main__":
    # Test cases
    test_data = pd.DataFrame([
        # Gas Flare: High persistence + industrial
        {'persistence_count': 15, 'land_cover': 'industrial', 'dist_to_industrial': 100, 'frp': 20, 'nearest_facility_type': 'refinery'},
        # Industrial Fire: High FRP + Proximity
        {'persistence_count': 2, 'land_cover': 'industrial', 'dist_to_industrial': 200, 'frp': 100, 'nearest_facility_type': 'refinery'},
        # Wildfire: Forest + Thermal
        {'persistence_count': 2, 'land_cover': 'forest', 'dist_to_industrial': 5000, 'frp': 60, 'nearest_facility_type': 'none'},
        # Crop Burning: Cropland + Low persistence
        {'persistence_count': 1, 'land_cover': 'cropland', 'dist_to_industrial': 5000, 'frp': 10, 'nearest_facility_type': 'none'},
        # Unknown: No rules match
        {'persistence_count': 1, 'land_cover': 'unknown', 'dist_to_industrial': 10000, 'frp': 5, 'nearest_facility_type': 'none'},
        # Conflict: Both Industrial Fire and Flare (simulated)
        {'persistence_count': 20, 'land_cover': 'industrial', 'dist_to_industrial': 100, 'frp': 100, 'nearest_facility_type': 'refinery'},
    ])

    logger.info("Applying weak supervision labels...")
    labeled_df = apply_weak_supervision(test_data)
    print("\nLabeled Dataset:\n", labeled_df[['label', 'label_source', 'label_conflict']])
