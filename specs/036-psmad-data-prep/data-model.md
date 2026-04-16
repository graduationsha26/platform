# Data Model: PSMAD Dataset Preprocessing Pipeline

**Branch**: `036-psmad-data-prep`  
**Phase**: Phase 1 — Design  
**Date**: 2026-04-07

---

## Overview

This feature is a pure data processing pipeline — it reads raw CSV files and writes a processed CSV file. There are no new database models, no API endpoints, and no persistent objects beyond the file system.

The entities below describe the in-memory data structures and file formats used by the pipeline.

---

## Entities

### 1. MetadataEntry

Represents a single row from `DataParkinson/AdditionalData.xlsx`.

| Field | Python Type | Source Column | Notes |
|---|---|---|---|
| `participant_id` | `int` | `ID` | 1–14, used to cross-reference filenames |
| `condition` | `str` | `Condition` | `"FIT (with Parkinson)"` or `"FIT (without Parkinson)"` |
| `parkinson_diagnosis` | `bool` | `Parkinson Diagnosis` | Clinical diagnosis flag |

*All other metadata columns (Age, Sex, etc.) are loaded but not used by the pipeline.*

**Derived label mapping**:
- Parkinson's Group folder → `label = 1`
- Control Group folder → `label = 0`

---

### 2. RecordingFile

Represents a single PSMAD CSV file on disk.

| Field | Python Type | Description |
|---|---|---|
| `filepath` | `Path` | Absolute path to the CSV file |
| `filename` | `str` | Filename without directory (e.g., `ID07010201.csv`) |
| `participant_id` | `int` | Extracted from filename digits 3–4 (e.g., `ID07...` → `7`) |
| `is_validation` | `bool` | True if filename ends with `00.csv` |
| `label` | `int` | `1` (Parkinson) or `0` (Control), based on source folder |
| `sampling_rate_hz` | `float` | Computed from median diff of `Timestamp` column |

**Validation rule**: `is_validation = True` if `filename[-6:-4] == '00'`  
**Filtering rule**: Only load files where `is_validation == False`

---

### 3. RawRecording

The loaded, column-renamed DataFrame for a single valid RecordingFile.

| Column | dtype | PSMAD Source | Description |
|---|---|---|---|
| `Timestamp` | `int64` | `T` | Time in milliseconds |
| `aX` | `float64` | `AX` | Linear acceleration X |
| `aY` | `float64` | `AY` | Linear acceleration Y |
| `aZ` | `float64` | `AZ` | Linear acceleration Z |
| `gX` | `float64` | `GX` | Angular velocity X |
| `gY` | `float64` | `GY` | Angular velocity Y |
| `gZ` | `float64` | `GZ` | Angular velocity Z |

**Invariant**: After loading, all column names must exactly match the ESP32 format above.  
**Shape**: `(N, 7)` where `N` = number of samples in the recording.  
**Minimum size**: Recordings with `N < 100` are skipped (no complete windows possible).

---

### 4. Window

A contiguous slice of exactly 100 rows from a single RawRecording.

| Attribute | Value |
|---|---|
| Size | Exactly 100 rows × 6 sensor axes |
| Source | Single RawRecording (never spans two recordings) |
| Stride | 100 (non-overlapping) |
| Columns | `aX, aY, aZ, gX, gY, gZ` (Timestamp excluded) |
| Label | Inherited from parent RecordingFile's `label` |

**Shape**: `(100, 6)` numpy array  
**Windowing formula**: `floor(N / 100)` complete windows per recording

---

### 5. FeatureVector

A single row in the output CSV, computed from one Window.

**Time-domain features** (30 total: 5 stats × 6 axes):

| Feature | Formula | Axes |
|---|---|---|
| `RMS_{axis}` | `sqrt(mean(x²))` | aX, aY, aZ, gX, gY, gZ |
| `mean_{axis}` | `mean(x)` | aX, aY, aZ, gX, gY, gZ |
| `std_{axis}` | `std(x)` | aX, aY, aZ, gX, gY, gZ |
| `skewness_{axis}` | scipy.stats.skew | aX, aY, aZ, gX, gY, gZ |
| `kurtosis_{axis}` | scipy.stats.kurtosis | aX, aY, aZ, gX, gY, gZ |

**FFT frequency-domain features** (12 total: 2 features × 6 axes):

| Feature | Description | Axes |
|---|---|---|
| `dominant_freq_{axis}` | Hz of highest-power bin in 3–12 Hz band | aX, aY, aZ, gX, gY, gZ |
| `tremor_energy_{axis}` | Sum of squared FFT magnitudes in 3–12 Hz band | aX, aY, aZ, gX, gY, gZ |

**FFT parameters**:
- Window size N = 100 samples
- Sampling rate derived per-recording from Timestamp median diff (~37 Hz)
- Tremor band: 3.0 Hz – 12.0 Hz
- Method: `numpy.fft.rfft`, positive frequencies only

**Label column**:

| Column | dtype | Values |
|---|---|---|
| `label` | `int` | `0` = Control (Non-Parkinson), `1` = Parkinson |

**Total columns**: 42 feature columns + 1 label column = **43 columns per row**

---

## Output File Schema

**File**: `backend/ml_data/processed/ready_for_training_features.csv`

```
RMS_aX, mean_aX, std_aX, skewness_aX, kurtosis_aX,
RMS_aY, mean_aY, std_aY, skewness_aY, kurtosis_aY,
RMS_aZ, mean_aZ, std_aZ, skewness_aZ, kurtosis_aZ,
RMS_gX, mean_gX, std_gX, skewness_gX, kurtosis_gX,
RMS_gY, mean_gY, std_gY, skewness_gY, kurtosis_gY,
RMS_gZ, mean_gZ, std_gZ, skewness_gZ, kurtosis_gZ,
dominant_freq_aX, tremor_energy_aX,
dominant_freq_aY, tremor_energy_aY,
dominant_freq_aZ, tremor_energy_aZ,
dominant_freq_gX, tremor_energy_gX,
dominant_freq_gY, tremor_energy_gY,
dominant_freq_gZ, tremor_energy_gZ,
label
```

**Invariants**:
- No NaN values in any column
- No Inf values in any column
- `label` is integer 0 or 1
- Each row corresponds to exactly one non-overlapping 100-sample window
- Rows are ordered: all Control-group windows first, then all Parkinson-group windows (within each group, ordered by filename)

---

## Pipeline State Transitions

```
DataParkinson/AdditionalData.xlsx
    ↓ [read metadata, reference only]
DataParkinson/Clean Dataset - Control Group/*.csv  (label=0)
DataParkinson/Clean Dataset - Parkinson's Group/*.csv (label=1)
    ↓ [filter: skip *00.csv files]
RecordingFile list (valid files only)
    ↓ [load CSV, rename columns T→Timestamp, AX→aX, etc.]
RawRecording DataFrames
    ↓ [window: non-overlapping, size=100, discard remainder]
Window arrays (100×6 numpy arrays) + labels
    ↓ [feature extraction: time-domain + FFT tremor-band]
FeatureVector rows (42 features + label)
    ↓ [assemble DataFrame, validate, drop NaN/Inf]
backend/ml_data/processed/ready_for_training_features.csv
```
