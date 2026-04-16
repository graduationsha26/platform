# Research: PSMAD Dataset Preprocessing Pipeline

**Branch**: `036-psmad-data-prep`  
**Phase**: Phase 0 — Research  
**Date**: 2026-04-07

---

## R-001: Dataset Structure and Filtering Rules

**Decision**: Filter functional validation files by filename suffix `00` (last two digits before `.csv` extension are `00`). Use folder membership to assign binary labels.

**Rationale**: The README states functional validation test files "were used to verify that the acquisition device correctly stores sensor data" and should be filtered before analysis. Examination of the `DataParkinson/` directory confirms:
- `DataParkinson/Clean Dataset - Control Group/` contains 89 CSV files, of which 10 end in `00` (e.g., `ID01010100.csv`, `ID02010100.csv`)
- `DataParkinson/Clean Dataset - Parkinson's Group/` contains 29 CSV files, none ending in `00`
- After filtering: 79 valid Control recordings (label=0), 29 valid Parkinson recordings (label=1)

**Alternatives considered**:
- Use metadata `Condition` column as the label source — rejected because the metadata is participant-level (14 rows), not file-level, and the folders are already the authoritative source of labels
- Use only metadata IDs to select files — rejected because the README warns "the number of metadata entries may not exactly match the number of IMU recordings" and missing recordings should be handled gracefully

---

## R-002: Metadata File Structure

**Decision**: Parse `DataParkinson/AdditionalData.xlsx` as a participant-level reference table. Use only for validating that subject IDs from filenames exist in metadata (optional cross-check). Primary filtering is by folder + filename suffix.

**Findings from direct inspection**:
```
Columns: ['ID', 'Caregiver or Representative', 'Age', 'Sex', 'Age between 60–85',
          'Parkinson Diagnosis', 'Medical Certificate', 'Has Parkinson Medication',
          'Hand Tremors Present', 'Full Motor Capacity', 'Condition']
Rows: 14 participants
Condition values: 'FIT (without Parkinson)' or 'FIT (with Parkinson)'
```
The `Condition` column contains: `FIT (with Parkinson)` for Parkinson participants and `FIT (without Parkinson)` for Control participants. These align with folder assignments.

The metadata does NOT contain a per-file validity flag — only participant-level attributes. Therefore, functional validation test filtering must be done via the `00` filename suffix rule alone.

**Alternatives considered**:
- Parse metadata for a "valid recording" column — does not exist; this column is absent from the metadata
- Filter by participant `Medical Certificate` or `Parkinson Diagnosis` columns — inappropriate as these are clinical attributes, not recording validity markers

---

## R-003: Column Mapping (PSMAD → ESP32 Format)

**Decision**: Apply the following direct rename mapping during the CSV loading phase:

| PSMAD Column | ESP32 Column | Description |
|---|---|---|
| `T` | `Timestamp` | Time in milliseconds |
| `AX` | `aX` | Linear acceleration X |
| `AY` | `aY` | Linear acceleration Y |
| `AZ` | `aZ` | Linear acceleration Z |
| `GX` | `gX` | Angular velocity X |
| `GY` | `gY` | Angular velocity Y |
| `GZ` | `gZ` | Angular velocity Z |

**Rationale**: The ESP32 output format uses lowercase axis letters. This is the format expected by all existing `ml_data/` pipeline code (e.g., `axis_names = ['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']` in `2_feature_engineering.py`).

---

## R-004: Sampling Rate Determination

**Decision**: Compute the sampling rate dynamically per recording from the `Timestamp` column median interval. Use the computed rate for FFT frequency bin calculations.

**Findings from direct timestamp inspection**:
```
File: ID01010101.csv
T values: [46, 73, 100, 127, 154, 181, 208, 235, 262, ...]
Median T interval: 27 ms → sampling rate ≈ 37 Hz
```
All inspected files show a consistent 27ms interval between samples, giving **~37 Hz sampling rate**.

At 37 Hz with a 100-sample window:
- Window duration: 100 × 27ms = 2.7 seconds
- Frequency resolution: 1/2.7s ≈ 0.37 Hz
- Nyquist limit: 37/2 = 18.5 Hz
- Tremor band 3–12 Hz is fully within the Nyquist limit ✅
- FFT bins covering 3–12 Hz: approximately bins 8 to 32 (out of 50 positive-frequency bins)

**Alternatives considered**:
- Assume a fixed 100 Hz sampling rate — rejected; direct measurement shows ~37 Hz, not 100 Hz
- Use the first T value as an offset reference — the first T value (46ms) may represent the time since device startup, not a fixed interval; median diff is the reliable metric

---

## R-005: Raw Sensor Units vs SI Units

**Decision**: Process all files as-is without unit conversion. All feature computations (time-domain statistics, FFT energy bands) are scale-invariant relative metrics that remain meaningful regardless of whether values are in raw sensor units or SI units.

**Findings**: Direct inspection reveals two patterns:
- Validation file `ID01010100.csv`: Values like `0.907402, -8.767567` (SI units, m/s² and rad/s)
- Valid recording `ID01010101.csv`: Values like `-2648, 7796, -9768` (raw 16-bit ADC units)

The README confirms: "Some recordings could not be successfully converted from raw IMU data to International System (SI) units." Most valid recording files in the dataset appear to be in raw units.

**Key implication**: When mixing Parkinson and Control recordings, all should be in raw units. However, since the feature extraction computes statistics (mean, std) and relative spectral energy, the absolute scale does not affect the ability to classify tremor patterns. The classifier will learn from relative patterns, not absolute magnitudes.

**Alternatives considered**:
- Apply per-file calibration to convert to SI units — rejected; calibration factors are not provided in the metadata, and unit conversion is not required for the feature-based classification approach
- Normalize each recording before windowing — rejected; this is a step for model training, not preprocessing, and is out of scope for this feature

---

## R-006: Windowing Strategy

**Decision**: Use non-overlapping windows (stride = window_size = 100). This differs from the default in the existing pipeline (stride=50, 50% overlap).

**Rationale**: The spec explicitly requires "non-overlapping windows of exactly 100 consecutive records". Non-overlapping windows produce independent feature vectors, which is appropriate for building a clean training dataset without data leakage between samples.

**Implementation note**: The existing `create_windows()` function in `utils/windowing.py` already supports non-overlapping windows — simply pass `stride=window_size=100`. No code change needed to `windowing.py` for this behavior.

**Data volume estimate**:
- Each valid recording: approximately 150–500 rows (based on inspection of multiple files)
- At 100 records/window, each recording yields 1–5 windows
- Total estimate: 108 valid recordings × ~3 windows avg = ~300–400 windows
- Possible class imbalance: 79 Control recordings vs 29 Parkinson recordings → may yield more Control windows

---

## R-007: FFT Frequency-Domain Features

**Decision**: Add two FFT-derived features per axis targeting the 3–12 Hz Parkinson tremor band:
1. `dominant_freq_{axis}`: The frequency (Hz) of the highest-power spectral component within the 3–12 Hz band
2. `tremor_energy_{axis}`: The total spectral energy (sum of squared FFT magnitudes) within the 3–12 Hz band

**Rationale**: Parkinson's tremor is characterized by a resting tremor in the 3–6 Hz range (sometimes up to 12 Hz for essential tremor). FFT energy in this band is one of the most clinically meaningful features for Parkinson's detection from IMU data.

**Implementation approach**:
```python
import numpy as np

def extract_fft_features(window, sampling_rate_hz=37, low_hz=3.0, high_hz=12.0):
    N = len(window)
    fft_vals = np.fft.rfft(window)
    fft_magnitude = np.abs(fft_vals)
    freqs = np.fft.rfftfreq(N, d=1.0/sampling_rate_hz)
    
    # Identify bins within the tremor band
    band_mask = (freqs >= low_hz) & (freqs <= high_hz)
    band_freqs = freqs[band_mask]
    band_magnitudes = fft_magnitude[band_mask]
    
    if len(band_magnitudes) == 0:
        return 0.0, 0.0  # Edge case: no bins in band
    
    tremor_energy = np.sum(band_magnitudes ** 2)
    dominant_freq = band_freqs[np.argmax(band_magnitudes)]
    
    return dominant_freq, tremor_energy
```

**Feature count**: 2 FFT features × 6 axes = 12 new features  
**Total feature count**: 30 time-domain + 12 FFT = **42 features per window** (plus 1 label column)

**Alternatives considered**:
- Welch's method (power spectral density) — more stable for short signals but adds scipy dependency and complexity; standard FFT is sufficient for 100-sample windows
- Band-pass filtered signal energy — requires filter design; FFT energy in band is equivalent and simpler
- Peak frequency across all frequencies — not constrained to tremor band; less clinically meaningful

---

## R-008: New Pipeline Script Architecture

**Decision**: Create a new standalone script `backend/ml_data/scripts/4_psmad_pipeline.py` that orchestrates the full PSMAD preprocessing flow. Extend `utils/feature_extractors.py` with FFT feature functions. Do not modify the existing `1_preprocess.py`, `2_feature_engineering.py`, or `run_all.py` scripts.

**Rationale**: The PSMAD pipeline has a fundamentally different input format (multiple per-subject CSVs vs a single Dataset.csv). Creating a dedicated script isolates the new logic and preserves the existing pipeline for the original dataset.

**Files to create/modify**:
- **CREATE**: `backend/ml_data/scripts/4_psmad_pipeline.py` — main orchestrator
- **MODIFY**: `backend/ml_data/utils/feature_extractors.py` — add `extract_fft_features_single_axis()` and `extract_fft_features_all_axes()` functions
- **CREATE**: `backend/ml_data/processed/` directory (if not exists) — output location

**Files NOT modified**:
- `utils/windowing.py` — existing `create_windows()` supports non-overlapping mode as-is
- `utils/data_loader.py` — original loader is for single Dataset.csv; PSMAD loading is in new script
- `utils/validators.py` — existing validators usable for output validation
- `scripts/1_preprocess.py`, `2_feature_engineering.py`, `3_sequence_preparation.py`, `run_all.py` — untouched

---

## R-009: Output Format

**Decision**: Output a single CSV file `backend/ml_data/processed/ready_for_training_features.csv` with:
- One row per window
- 42 feature columns (30 time-domain + 12 FFT) using consistent naming
- 1 `label` column (int: 0=Control, 1=Parkinson)
- No index column, no NaN or Inf values

**Feature column naming convention**:
- Time-domain: `{stat}_{axis}` (e.g., `RMS_aX`, `mean_aX`, `std_aX`, `skewness_aX`, `kurtosis_aX`)
- FFT: `dominant_freq_{axis}`, `tremor_energy_{axis}` (e.g., `dominant_freq_aX`, `tremor_energy_aX`)

This naming aligns with the existing `get_feature_names()` function in `feature_extractors.py` for time-domain features.
