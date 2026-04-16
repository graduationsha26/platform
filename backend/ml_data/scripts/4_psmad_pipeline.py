#!/usr/bin/env python
"""
PSMAD Dataset Preprocessing Pipeline

Loads the PSMAD (Parkinson's Screening and Motor Assessment Dataset) from two group folders,
filters functional validation recordings, renames columns to the project's ESP32 format,
segments into non-overlapping 100-sample windows, extracts time-domain and FFT tremor-band
features for each window, and writes a single ready_for_training_features.csv to ml_data/processed/.

Usage:
    python 4_psmad_pipeline.py [OPTIONS]

Options:
    --parkinson-dir PATH   Path to Parkinson's Group folder
                           (default: ../../../DataParkinson/Clean Dataset - Parkinson's Group)
    --control-dir   PATH   Path to Control Group folder
                           (default: ../../../DataParkinson/Clean Dataset - Control Group)
    --metadata      PATH   Path to AdditionalData.xlsx
                           (default: ../../../DataParkinson/AdditionalData.xlsx)
    --output        PATH   Path for output CSV
                           (default: ../processed/ready_for_training_features.csv)

Output:
    backend/ml_data/processed/ready_for_training_features.csv
"""

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Add parent directory to path so utils imports work
sys.path.append(str(Path(__file__).parent.parent))

from utils.windowing import create_windows
from utils.feature_extractors import (
    extract_features_all_axes,
    get_feature_names,
    extract_fft_features_all_axes,
    get_fft_feature_names,
)
from utils.gravity_filter import (
    design_gravity_filter,
    apply_gravity_filter,
    get_filter_params_dict,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WINDOW_SIZE = 100
AXIS_NAMES = ['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']
TREMOR_BAND_LOW_HZ = 3.0
TREMOR_BAND_HIGH_HZ = 12.0

COLUMN_RENAME_MAP = {
    'T': 'Timestamp',
    'AX': 'aX',
    'AY': 'aY',
    'AZ': 'aZ',
    'GX': 'gX',
    'GY': 'gY',
    'GZ': 'gZ',
}

# Labels
LABEL_PARKINSON = 1
LABEL_CONTROL = 0


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------

def _find_dataset_folder(data_root: Path, keyword: str) -> Path:
    """
    Locate a subfolder under data_root whose name contains keyword (case-insensitive).
    Returns the first match or raises FileNotFoundError.
    """
    for child in data_root.iterdir():
        if child.is_dir() and keyword.lower() in child.name.lower():
            return child
    raise FileNotFoundError(
        f"No subfolder containing '{keyword}' found under {data_root}"
    )


def parse_arguments():
    """Parse command-line arguments."""
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent.parent.parent  # backend/ml_data/scripts -> repo root
    data_root = repo_root / 'DataParkinson'

    # Auto-discover folder paths using keyword matching to handle Unicode in folder names
    try:
        default_parkinson_dir = str(_find_dataset_folder(data_root, "Parkinson"))
    except FileNotFoundError:
        default_parkinson_dir = str(data_root / "Clean Dataset - Parkinson's Group")

    try:
        default_control_dir = str(_find_dataset_folder(data_root, "Control"))
    except FileNotFoundError:
        default_control_dir = str(data_root / 'Clean Dataset - Control Group')

    default_metadata = str(data_root / 'AdditionalData.xlsx')
    default_output = str(script_dir.parent / 'processed' / 'ready_for_training_features.csv')

    parser = argparse.ArgumentParser(
        description='PSMAD dataset preprocessing pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        '--parkinson-dir',
        type=str,
        default=default_parkinson_dir,
        help="Path to Parkinson's Group CSV folder",
    )
    parser.add_argument(
        '--control-dir',
        type=str,
        default=default_control_dir,
        help='Path to Control Group CSV folder',
    )
    parser.add_argument(
        '--metadata',
        type=str,
        default=default_metadata,
        help='Path to AdditionalData.xlsx metadata file',
    )
    parser.add_argument(
        '--output',
        type=str,
        default=default_output,
        help='Output path for ready_for_training_features.csv',
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# US1 — Filter and Format-Align
# ---------------------------------------------------------------------------

def load_metadata(metadata_path: str) -> pd.DataFrame:
    """
    Load participant metadata from AdditionalData.xlsx.

    Parameters
    ----------
    metadata_path : str
        Path to AdditionalData.xlsx

    Returns
    -------
    pd.DataFrame
        Participant metadata table
    """
    if not os.path.exists(metadata_path):
        print(f'[WARNING] Metadata file not found: {metadata_path} — skipping metadata load')
        return pd.DataFrame()

    df = pd.read_excel(metadata_path, engine='openpyxl')
    print(f'[INFO] Metadata loaded: {len(df)} participants')
    return df


def discover_recordings(folder_path: str, label: int) -> list:
    """
    Discover valid CSV recordings in a group folder.

    Functional validation files are identified by their filename stem ending
    with '00' (e.g. ID01010100.csv) and are excluded from the result.

    Parameters
    ----------
    folder_path : str
        Path to the group's CSV folder
    label : int
        Binary class label for all recordings in this folder (0 or 1)

    Returns
    -------
    list of (Path, int)
        List of (filepath, label) tuples for valid recordings
    """
    folder = Path(folder_path)
    if not folder.exists():
        print(f'[WARNING] Folder not found: {folder_path}')
        return []

    all_csvs = sorted(folder.glob('*.csv'))
    valid = []
    skipped = []

    for csv_path in all_csvs:
        stem = csv_path.stem  # filename without extension
        if stem.endswith('00'):
            skipped.append(csv_path.name)
        else:
            valid.append((csv_path, label))

    group_name = 'Parkinson' if label == LABEL_PARKINSON else 'Control'
    print(f'[INFO] {group_name} Group: {len(all_csvs)} files found, '
          f'{len(skipped)} validation files skipped, {len(valid)} valid recordings')

    return valid


def load_recording(filepath: Path) -> tuple:
    """
    Load a PSMAD CSV file and rename columns to the ESP32 format.

    Parameters
    ----------
    filepath : Path
        Path to the CSV file

    Returns
    -------
    (pd.DataFrame, float)
        (DataFrame with renamed columns, sampling_rate_hz)
        Returns (None, None) if the file cannot be loaded.
    """
    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        print(f'[WARNING] Failed to read {filepath.name}: {e} — skipping')
        return None, None

    # Rename PSMAD columns to ESP32 format
    df.rename(columns=COLUMN_RENAME_MAP, inplace=True)

    # Verify required columns are present
    required = list(COLUMN_RENAME_MAP.values())
    missing = [c for c in required if c not in df.columns]
    if missing:
        print(f'[WARNING] {filepath.name}: missing columns {missing} after rename — skipping')
        return None, None

    # Compute sampling rate from Timestamp column (T is in milliseconds)
    timestamp_diffs = df['Timestamp'].diff().dropna()
    if len(timestamp_diffs) == 0 or timestamp_diffs.median() <= 0:
        print(f'[WARNING] {filepath.name}: cannot compute sampling rate from Timestamp — using 37 Hz default')
        sampling_rate_hz = 37.0
    else:
        sampling_rate_hz = 1000.0 / timestamp_diffs.median()

    return df, sampling_rate_hz


# ---------------------------------------------------------------------------
# US2 — Windowing
# ---------------------------------------------------------------------------

def window_recording(df: pd.DataFrame, sampling_rate_hz: float, label: int,
                     window_size: int = WINDOW_SIZE,
                     gravity_sos: np.ndarray = None) -> list:
    """
    Segment a recording into non-overlapping windows of exactly window_size records.

    Parameters
    ----------
    df : pd.DataFrame
        Loaded recording with ESP32 column names
    sampling_rate_hz : float
        Sampling rate (used to pass through to feature extraction)
    label : int
        Binary class label for this recording
    window_size : int
        Number of samples per window (default: 100)
    gravity_sos : np.ndarray, optional
        SOS filter coefficients for gravity removal. When provided, the full
        continuous accelerometer signal is high-pass filtered BEFORE windowing,
        isolating the dynamic tremor component from the static gravity offset.
        Only accelerometer columns (aX, aY, aZ) are filtered; gyroscope columns
        pass through unchanged. Defaults to None (no filtering).

    Returns
    -------
    list of (np.ndarray, int, float)
        List of (window_array shape (window_size, 6), label, sampling_rate_hz)
    """
    data = df[AXIS_NAMES].values  # shape: (N, 6) — drop Timestamp

    if len(data) < window_size:
        print(f'[WARNING] Recording has only {len(data)} samples (< {window_size}) — skipping')
        return []

    # Apply gravity high-pass filter to full signal before windowing.
    # Filtering on the full continuous signal (not individual windows) avoids
    # edge artifacts at window boundaries and allows proper filter initialisation.
    if gravity_sos is not None:
        data = apply_gravity_filter(data, gravity_sos)

    # Non-overlapping: stride == window_size
    windows_3d = create_windows(data, window_size=window_size, stride=window_size)
    # windows_3d shape: (n_windows, window_size, 6)

    result = []
    for i in range(windows_3d.shape[0]):
        result.append((windows_3d[i], label, sampling_rate_hz))

    return result


# ---------------------------------------------------------------------------
# US3 — Feature Extraction
# ---------------------------------------------------------------------------

def extract_window_features(window: np.ndarray, sampling_rate_hz: float) -> dict:
    """
    Extract all 42 features (30 time-domain + 12 FFT tremor-band) from a single window.

    Parameters
    ----------
    window : np.ndarray
        Shape (window_size, 6) — 6 sensor axes
    sampling_rate_hz : float
        Sampling rate in Hz (used for FFT bin frequency computation)

    Returns
    -------
    dict
        42-key feature dictionary
    """
    # Time-domain features: RMS, mean, std, skewness, kurtosis per axis (30 total)
    time_features = extract_features_all_axes(window, AXIS_NAMES)

    # FFT tremor-band features: dominant_freq, tremor_energy per axis (12 total)
    fft_features = extract_fft_features_all_axes(
        window,
        AXIS_NAMES,
        sampling_rate_hz=sampling_rate_hz,
        low_hz=TREMOR_BAND_LOW_HZ,
        high_hz=TREMOR_BAND_HIGH_HZ,
    )

    return {**time_features, **fft_features}


# ---------------------------------------------------------------------------
# US4 — Output Assembly & Save
# ---------------------------------------------------------------------------

def build_output_dataframe(rows: list) -> pd.DataFrame:
    """
    Build the output DataFrame from the list of feature-dict rows.

    Enforces column order: time-domain features → FFT features → label.

    Parameters
    ----------
    rows : list of dict
        Each dict has 42 feature keys + 'label'

    Returns
    -------
    pd.DataFrame
        Ordered DataFrame ready for CSV output
    """
    df = pd.DataFrame(rows)

    time_cols = get_feature_names(AXIS_NAMES)           # 30 columns
    fft_cols = get_fft_feature_names(AXIS_NAMES)        # 12 columns
    ordered_cols = time_cols + fft_cols + ['label']

    df = df[ordered_cols]
    df['label'] = df['label'].astype(int)

    # Replace NaN and Inf values with 0.0 — these arise from constant-value windows
    # (e.g. skewness/kurtosis undefined when all samples are identical).
    feature_cols = time_cols + fft_cols
    df[feature_cols] = df[feature_cols].replace([np.inf, -np.inf], 0.0)
    df[feature_cols] = df[feature_cols].fillna(0.0)

    return df


def validate_output(df: pd.DataFrame) -> None:
    """
    Assert the output DataFrame meets all quality requirements.

    Raises
    ------
    ValueError
        If any quality check fails
    """
    if df.isnull().any().any():
        nan_cols = df.columns[df.isnull().any()].tolist()
        raise ValueError(f'Output contains NaN values in columns: {nan_cols}')

    numeric_vals = df.select_dtypes(include=np.number).values
    if np.isinf(numeric_vals).any():
        raise ValueError('Output contains Inf values')

    label_values = set(df['label'].unique())
    if not label_values.issubset({0, 1}):
        raise ValueError(f'label column has invalid values: {label_values}')

    expected_cols = 43  # 30 time-domain + 12 FFT + 1 label
    if len(df.columns) != expected_cols:
        raise ValueError(f'Expected {expected_cols} columns, got {len(df.columns)}')


def save_output(df: pd.DataFrame, output_path: str) -> None:
    """
    Save the output DataFrame to CSV.

    Parameters
    ----------
    df : pd.DataFrame
        Validated output DataFrame
    output_path : str
        Destination file path
    """
    output_dir = os.path.dirname(os.path.abspath(output_path))
    os.makedirs(output_dir, exist_ok=True)
    df.to_csv(output_path, index=False)


def print_summary(files_processed: int, windows_generated: int,
                  label_distribution: dict, output_path: str, df: pd.DataFrame) -> None:
    """Print completion summary to stdout."""
    file_size_kb = os.path.getsize(output_path) / 1024
    print('\n' + '=' * 70)
    print('PSMAD PREPROCESSING PIPELINE — COMPLETE')
    print('=' * 70)
    print(f'  Files processed  : {files_processed}')
    print(f'  Windows generated: {windows_generated}')
    print(f'  Label distribution:')
    for lbl, count in sorted(label_distribution.items()):
        name = 'Parkinson' if lbl == LABEL_PARKINSON else 'Control'
        print(f'    label={lbl} ({name:10s}): {count} windows')
    print(f'  Features per row : {len(df.columns) - 1} (30 time-domain + 12 FFT tremor-band)')
    print(f'  Output path      : {output_path}')
    print(f'  Output size      : {file_size_kb:.1f} KB')
    print('=' * 70)


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------

def main():
    """Run the complete PSMAD preprocessing pipeline."""
    import time
    start_time = time.time()

    print('=' * 70)
    print('PSMAD PREPROCESSING PIPELINE')
    print('=' * 70)

    args = parse_arguments()

    print(f'\nConfiguration:')
    print(f'  Parkinson dir : {args.parkinson_dir}')
    print(f'  Control dir   : {args.control_dir}')
    print(f'  Metadata      : {args.metadata}')
    print(f'  Output        : {args.output}')

    # ------------------------------------------------------------------
    # US1: Filter and Format-Align
    # ------------------------------------------------------------------
    print('\n[STEP 1] Loading metadata...')
    load_metadata(args.metadata)

    print('\n[STEP 2] Discovering valid recordings...')
    parkinson_files = discover_recordings(args.parkinson_dir, LABEL_PARKINSON)
    control_files = discover_recordings(args.control_dir, LABEL_CONTROL)
    all_files = parkinson_files + control_files

    if not all_files:
        print('[ERROR] No valid recordings found. Check folder paths.')
        sys.exit(1)

    print(f'[INFO] Total valid recordings: {len(all_files)}')

    # ------------------------------------------------------------------
    # Gravity filter design
    # Design a single 2nd-order Butterworth high-pass filter (0.5 Hz cutoff)
    # to remove the static gravity component from accelerometer channels.
    # The same filter parameters are applied to ALL recordings and saved to
    # filter_params.json so the live inference service can reproduce them.
    # ------------------------------------------------------------------
    GRAVITY_CUTOFF_HZ = 0.5
    GRAVITY_FILTER_ORDER = 2
    DEFAULT_FS = 37.0  # PSMAD nominal sampling rate (millisecond timestamps → ~37 Hz)

    print(f'\n[GRAVITY FILTER] Designing {GRAVITY_FILTER_ORDER}-order Butterworth high-pass '
          f'filter at {GRAVITY_CUTOFF_HZ} Hz cutoff (fs={DEFAULT_FS} Hz)...')
    gravity_sos = design_gravity_filter(
        cutoff_hz=GRAVITY_CUTOFF_HZ,
        fs=DEFAULT_FS,
        order=GRAVITY_FILTER_ORDER,
    )
    filter_params = get_filter_params_dict(
        cutoff_hz=GRAVITY_CUTOFF_HZ,
        fs=DEFAULT_FS,
        order=GRAVITY_FILTER_ORDER,
        sos=gravity_sos,
    )
    print('[GRAVITY FILTER] Filter designed. Accelerometer axes will be filtered before windowing.')

    # Save filter params alongside the output CSV so training scripts can embed them
    filter_params_path = Path(args.output).parent / 'filter_params.json'
    filter_params_path.parent.mkdir(parents=True, exist_ok=True)
    with open(filter_params_path, 'w') as fp:
        json.dump(filter_params, fp, indent=2)
    print(f'[GRAVITY FILTER] Filter parameters saved to {filter_params_path}')

    # ------------------------------------------------------------------
    # US2 + US3: Load -> Filter -> Window -> Extract Features
    # ------------------------------------------------------------------
    print('\n[STEP 3] Processing recordings: load -> gravity filter -> window -> extract features...')

    rows = []
    files_processed = 0
    label_distribution = {LABEL_PARKINSON: 0, LABEL_CONTROL: 0}

    for filepath, label in all_files:
        df_rec, sampling_rate_hz = load_recording(filepath)

        if df_rec is None:
            continue  # skip corrupted/unreadable files

        windows = window_recording(df_rec, sampling_rate_hz, label, gravity_sos=gravity_sos)

        for window_arr, win_label, win_sr in windows:
            feature_dict = extract_window_features(window_arr, win_sr)
            feature_dict['label'] = win_label
            rows.append(feature_dict)
            label_distribution[win_label] = label_distribution.get(win_label, 0) + 1

        files_processed += 1

    if not rows:
        print('[ERROR] No windows generated. Check that recordings have >= 100 samples.')
        sys.exit(1)

    print(f'[INFO] Total windows extracted: {len(rows)}')

    # ------------------------------------------------------------------
    # US4: Compile, Validate, Save
    # ------------------------------------------------------------------
    print('\n[STEP 4] Assembling output DataFrame...')
    output_df = build_output_dataframe(rows)

    print('[STEP 5] Validating output (no NaN/Inf, correct columns)...')
    try:
        validate_output(output_df)
        print('[INFO] Validation passed.')
    except ValueError as e:
        print(f'[ERROR] Output validation failed: {e}')
        sys.exit(1)

    print(f'\n[STEP 6] Saving to {args.output}...')
    save_output(output_df, args.output)

    elapsed = time.time() - start_time
    print(f'[INFO] Total processing time: {elapsed:.2f}s')

    print_summary(files_processed, len(rows), label_distribution, args.output, output_df)


if __name__ == '__main__':
    main()
