"""
Step 5: Data Aggregation & Feature Extraction (v2 Pipeline)

Reads all Excel files from:
  - Data v2/Normal/    → label 0 (Control / no Parkinson's)
  - Data v2/Parkinson/ → label 1 (Parkinson's tremor)

For each file:
  1. Read raw 16-bit ADC columns: AcX, AcY, AcZ, GyX, GyY, GyZ
  2. Convert to physical units:
       Accelerometer: raw / 16384.0 * 9.81  → m/s²
       Gyroscope:     raw / 131.0            → °/s
  3. Apply sliding window (window_size=100, stride=15)
  4. Extract 42 features per window via shared extract_window_features()

Saves:
  backend/ml_data/processed/X_features.npy  — shape (N_windows, 42)
  backend/ml_data/processed/y_labels.npy    — shape (N_windows,) values {0, 1}

Usage:
    py backend/ml_data/scripts/5_aggregate_and_extract.py
    py backend/ml_data/scripts/5_aggregate_and_extract.py --data-dir "Data v2" --output-dir backend/ml_data/processed
"""

import argparse
import logging
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Path setup — resolve backend/ so ml_data imports work when run from repo root
# Script location: backend/ml_data/scripts/5_aggregate_and_extract.py
#   .parent        → backend/ml_data/scripts/
#   .parent.parent → backend/ml_data/
#   .parent.parent.parent → backend/
# ---------------------------------------------------------------------------
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_BACKEND_DIR))

from ml_data.utils.feature_extractors import extract_window_features, get_feature_names

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
AXIS_NAMES = ['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']

# MPU6050 default full-scale sensitivity factors
ACCEL_SENSITIVITY = 16384.0   # LSB/g  (±2g range)
GYRO_SENSITIVITY  = 131.0     # LSB/(°/s)  (±250°/s range)
GRAVITY_MS2       = 9.81      # m/s² per g

WINDOW_SIZE = 100
STRIDE      = 15
SAMPLING_RATE_HZ = 250.0  # Approximate rate of the Data v2 Excel files

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description='Aggregate Excel sensor data and extract 42 features per window'
    )
    # Default data dir is two levels above backend/ (repo root / "Data v2")
    default_data_dir = str(_BACKEND_DIR.parent / 'Data v2')
    default_output_dir = str(_BACKEND_DIR / 'ml_data' / 'processed')

    parser.add_argument(
        '--data-dir',
        default=default_data_dir,
        help=f'Path to "Data v2" directory (default: {default_data_dir})'
    )
    parser.add_argument(
        '--output-dir',
        default=default_output_dir,
        help=f'Output directory for .npy files (default: {default_output_dir})'
    )
    parser.add_argument(
        '--sampling-rate',
        type=float,
        default=SAMPLING_RATE_HZ,
        help=f'Sampling rate in Hz for FFT features (default: {SAMPLING_RATE_HZ})'
    )
    return parser.parse_args()


def load_excel_file(filepath: Path) -> np.ndarray | None:
    """
    Load a single Excel file and return a (N_rows, 6) float64 array in
    physical units, or None if the file should be skipped.

    Column mapping (Excel → physical):
      AcX, AcY, AcZ  → raw / 16384.0 * 9.81  (m/s²)
      GyX, GyY, GyZ  → raw / 131.0             (°/s)
    """
    try:
        df = pd.read_excel(filepath, usecols=['AcX', 'AcY', 'AcZ', 'GyX', 'GyY', 'GyZ'])
    except Exception as e:
        logger.error(f'  Cannot read {filepath.name}: {e}')
        return None

    if len(df) < WINDOW_SIZE:
        logger.warning(
            f'  Skipping {filepath.name}: only {len(df)} rows '
            f'(minimum {WINDOW_SIZE} required for one window)'
        )
        return None

    # Convert to float64 first to guard against integer overflow during math
    data = df.values.astype(np.float64)

    # ADC → physical units
    data[:, 0:3] = data[:, 0:3] / ACCEL_SENSITIVITY * GRAVITY_MS2  # aX, aY, aZ → m/s²
    data[:, 3:6] = data[:, 3:6] / GYRO_SENSITIVITY                 # gX, gY, gZ → °/s

    return data


def extract_windows(data: np.ndarray, label: int, sampling_rate_hz: float):
    """
    Apply sliding window and extract features from a single file's data.

    Returns (features_list, labels_list) where each element corresponds to
    one window.
    """
    features_list = []
    labels_list = []

    n_samples = data.shape[0]
    start = 0
    while start + WINDOW_SIZE <= n_samples:
        window = data[start : start + WINDOW_SIZE]
        feat_vec = extract_window_features(window, AXIS_NAMES, sampling_rate_hz)
        features_list.append(feat_vec)
        labels_list.append(label)
        start += STRIDE

    return features_list, labels_list


def process_directory(directory: Path, label: int, sampling_rate_hz: float):
    """Process all .xlsx files in a directory and return aggregated features/labels."""
    xlsx_files = sorted(directory.glob('*.xlsx'))

    if not xlsx_files:
        logger.warning(f'No .xlsx files found in {directory}')
        return [], [], 0

    all_features = []
    all_labels = []
    files_processed = 0

    for filepath in xlsx_files:
        logger.info(f'  Processing {filepath.name}...')
        data = load_excel_file(filepath)
        if data is None:
            continue

        feats, labs = extract_windows(data, label, sampling_rate_hz)
        all_features.extend(feats)
        all_labels.extend(labs)
        files_processed += 1
        logger.info(f'    → {len(feats)} windows extracted from {len(data)} rows')

    return all_features, all_labels, files_processed


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = parse_args()
    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)

    logger.info('=' * 65)
    logger.info('Data Aggregation & Feature Extraction — v2 Pipeline')
    logger.info('=' * 65)
    logger.info(f'Data directory : {data_dir}')
    logger.info(f'Output directory: {output_dir}')
    logger.info(f'Window size    : {WINDOW_SIZE}')
    logger.info(f'Stride         : {STRIDE}')
    logger.info(f'Sampling rate  : {args.sampling_rate} Hz')
    logger.info(f'ADC → physical : accel / {ACCEL_SENSITIVITY} × {GRAVITY_MS2}, gyro / {GYRO_SENSITIVITY}')

    # Verify data directories exist
    normal_dir = data_dir / 'Normal'
    parkinson_dir = data_dir / 'Parkinson'

    for d in (normal_dir, parkinson_dir):
        if not d.exists():
            logger.error(f'Directory not found: {d}')
            logger.error('Ensure "Data v2/Normal" and "Data v2/Parkinson" exist at repo root.')
            sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    # -----------------------------------------------------------------------
    # Process Normal (label 0)
    # -----------------------------------------------------------------------
    logger.info('')
    logger.info(f'Processing Normal (label 0) from {normal_dir}...')
    normal_features, normal_labels, normal_files = process_directory(
        normal_dir, label=0, sampling_rate_hz=args.sampling_rate
    )

    # -----------------------------------------------------------------------
    # Process Parkinson (label 1)
    # -----------------------------------------------------------------------
    logger.info('')
    logger.info(f'Processing Parkinson (label 1) from {parkinson_dir}...')
    parkinson_features, parkinson_labels, parkinson_files = process_directory(
        parkinson_dir, label=1, sampling_rate_hz=args.sampling_rate
    )

    # -----------------------------------------------------------------------
    # Combine and validate
    # -----------------------------------------------------------------------
    all_features = normal_features + parkinson_features
    all_labels = normal_labels + parkinson_labels

    if not all_features:
        logger.error('No windows were extracted. Check data directories and file contents.')
        sys.exit(1)

    X = np.array(all_features, dtype=np.float64)
    y = np.array(all_labels, dtype=np.int64)

    # Sanity checks
    assert X.shape[1] == 42, f'Expected 42 features, got {X.shape[1]}'
    assert X.shape[0] == y.shape[0], 'Feature/label count mismatch'
    assert not np.any(np.isnan(X)), 'NaN values found in feature matrix'
    assert not np.any(np.isinf(X)), 'Inf values found in feature matrix'

    # -----------------------------------------------------------------------
    # Save outputs
    # -----------------------------------------------------------------------
    x_path = output_dir / 'X_features.npy'
    y_path = output_dir / 'y_labels.npy'
    np.save(str(x_path), X)
    np.save(str(y_path), y)

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    logger.info('')
    logger.info('=' * 65)
    logger.info('Extraction Complete')
    logger.info('=' * 65)
    logger.info(f'Files processed  : {normal_files} Normal + {parkinson_files} Parkinson = {normal_files + parkinson_files} total')
    logger.info(f'Windows extracted: {len(normal_features)} Normal + {len(parkinson_features)} Parkinson = {X.shape[0]} total')
    logger.info(f'Feature matrix   : {X.shape}  (N_windows × 42 features)')
    logger.info(f'Label distribution: Normal(0)={int((y == 0).sum())}  Parkinson(1)={int((y == 1).sum())}')
    logger.info(f'NaN/Inf values   : None')
    logger.info(f'Saved X → {x_path}')
    logger.info(f'Saved y → {y_path}')

    # Sample statistics on first feature (mean_aX) to verify physical-unit ranges
    feat_names = get_feature_names(AXIS_NAMES)
    logger.info('')
    logger.info('Sample feature statistics (first 3 features):')
    for i in range(min(3, X.shape[1])):
        col = X[:, i]
        logger.info(
            f'  {feat_names[i]:25s}  mean={col.mean():+.4f}  std={col.std():.4f}'
            f'  min={col.min():+.4f}  max={col.max():+.4f}'
        )
    logger.info('')
    logger.info('[OK] Feature matrices ready for model training.')
    logger.info('Next step: py backend/ml_models/scripts/train_random_forest.py')


if __name__ == '__main__':
    main()
