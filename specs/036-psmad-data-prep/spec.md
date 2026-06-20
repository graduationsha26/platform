# Feature Specification: PSMAD Dataset Preprocessing Pipeline

**Feature Branch**: `036-psmad-data-prep`  
**Created**: 2026-04-07  
**Status**: Draft  
**Input**: User description: "PSMAD dataset preprocessing: filter, format-align, window, extract features, output ready_for_training_features.csv"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Filter and Format-Align PSMAD Raw Data (Priority: P1)

A data engineer runs the pipeline against the PSMAD dataset folders. The pipeline reads the metadata file to identify valid test recordings (excluding invalid and functional-validation entries), loads each valid CSV file, and renames columns from the PSMAD convention (`T`, `AX`, `AY`, `AZ`, `GX`, `GY`, `GZ`) to the project's ESP32 convention (`Timestamp`, `aX`, `aY`, `aZ`, `gX`, `gY`, `gZ`) so all downstream processing uses a single consistent format.

**Why this priority**: Without clean, consistently-formatted input data, all downstream windowing and feature extraction steps are impossible. Filtering prevents corrupted or irrelevant test sessions from polluting the dataset.

**Independent Test**: Can be tested by running only the loading/filtering step and verifying that only valid recordings are loaded and that column names match the ESP32 format exactly.

**Acceptance Scenarios**:

1. **Given** the Parkinson and Control group CSV folders and the metadata file exist, **When** the pipeline loader runs, **Then** every loaded dataframe has columns named exactly `Timestamp`, `aX`, `aY`, `aZ`, `gX`, `gY`, `gZ` and no other sensor columns.
2. **Given** the metadata file contains entries marked as invalid or "functional validation", **When** the pipeline loader runs, **Then** those files are skipped and a log entry records each skipped file with its reason.
3. **Given** a CSV file listed in metadata is missing from disk, **When** the pipeline runs, **Then** that file is skipped with a warning and processing continues for remaining files.

---

### User Story 2 - Segment Data into Fixed-Size Windows (Priority: P2)

The pipeline segments each loaded recording into non-overlapping windows of exactly 100 consecutive records. Any trailing records at the end of a recording that do not form a complete 100-record window are discarded, ensuring every window fed to feature extraction is a complete, uniform slice.

**Why this priority**: Consistent window size is a hard requirement for the feature extraction step. Incomplete windows would produce features with different dimensionality and corrupt the training dataset.

**Independent Test**: Can be tested by passing a recording of known length (e.g., 250 records) and verifying exactly 2 complete windows are produced (records 1-100, 101-200) with the final 50 records discarded.

**Acceptance Scenarios**:

1. **Given** a recording with N records, **When** the windowing step runs, **Then** exactly `floor(N / 100)` windows are produced, each containing exactly 100 records.
2. **Given** a recording with fewer than 100 records, **When** the windowing step runs, **Then** zero windows are produced for that recording and a warning is logged.
3. **Given** multiple recordings, **When** windowing runs, **Then** windows from different recordings are never merged together.

---

### User Story 3 - Extract Time-Domain and Frequency-Domain Features per Window (Priority: P3)

For each 100-record window, the pipeline computes a fixed set of statistical features across all 6 sensor axes. Time-domain features include mean, standard deviation, minimum, maximum, and range. Frequency-domain features are derived from FFT and target the 3 Hz-12 Hz tremor band, capturing the dominant frequency component and the spectral energy within that band for each axis.

**Why this priority**: Feature extraction transforms raw sensor windows into numeric vectors suitable for machine learning. Without this step, the output CSV cannot be used for model training.

**Independent Test**: Can be tested by passing a single synthetic 100-record window with known values and verifying that every expected feature column is present in the output row and contains a finite numeric value.

**Acceptance Scenarios**:

1. **Given** a 100-record window with 6 sensor axes, **When** feature extraction runs, **Then** the output row contains time-domain features (mean, std, min, max, range) for each of the 6 axes (30 features total).
2. **Given** a 100-record window sampled at a known rate, **When** feature extraction runs, **Then** the output row contains FFT-derived features (dominant tremor-band frequency, tremor-band spectral energy) for each of the 6 axes (12 additional features).
3. **Given** a window where all accelerometer values are constant (zero tremor), **When** feature extraction runs, **Then** tremor-band energy features return zero or near-zero values, not errors.

---

### User Story 4 - Compile and Save Final Training-Ready CSV (Priority: P1)

After all windows across both groups are processed, the pipeline assembles every feature row together with its binary label (`1` for Parkinson's group, `0` for Control group) and writes a single file named `ready_for_training_features.csv` into `ml_data/processed/`. The output file contains a header row followed by one data row per window.

**Why this priority**: The entire preprocessing pipeline's value is this single output file. Without it, no model training can begin.

**Independent Test**: Can be tested by running the full pipeline on a small synthetic dataset and verifying the output file exists at the correct path, contains a `label` column, has the correct number of rows, and all feature columns contain finite numeric values with no NaN or infinite entries.

**Acceptance Scenarios**:

1. **Given** the pipeline completes without fatal errors, **When** the output step runs, **Then** `ml_data/processed/ready_for_training_features.csv` is created and non-empty.
2. **Given** windows from both Parkinson and Control groups are processed, **When** the output file is opened, **Then** it contains a `label` column where Parkinson windows have value `1` and Control windows have value `0`.
3. **Given** the output file is generated, **When** it is inspected, **Then** no row contains NaN, infinite, or missing values in any feature column.
4. **Given** the output file is generated, **When** it is inspected, **Then** the header row matches exactly the expected feature column names plus a `label` column.

---

### Edge Cases

- What happens when a CSV file contains non-numeric or corrupted sensor values?
- How does the system handle recordings where the sampling rate is not explicitly encoded in the file (needed for FFT frequency bin calculation)?
- What happens if the metadata file is malformed or missing required columns?
- What happens if one of the two dataset folders is empty or missing entirely?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The pipeline MUST read the PSMAD metadata file to determine which recording files are valid before loading any sensor CSV.
- **FR-002**: The pipeline MUST skip any recording marked as invalid or as a "functional validation" test in the metadata file and log each skipped entry.
- **FR-003**: The pipeline MUST load CSV files from both `DataParkinson/Clean Dataset - Parkinson's Group` and `DataParkinson/Clean Dataset - Control Group` and assign labels `1` and `0` respectively.
- **FR-004**: The pipeline MUST rename sensor columns from PSMAD format (`T`, `AX`, `AY`, `AZ`, `GX`, `GY`, `GZ`) to ESP32 format (`Timestamp`, `aX`, `aY`, `aZ`, `gX`, `gY`, `gZ`) during the loading phase.
- **FR-005**: The windowing module MUST segment each recording into non-overlapping windows of exactly 100 records, discarding any incomplete trailing window.
- **FR-006**: The feature extraction module MUST compute the following time-domain features for each of the 6 sensor axes per window: mean, standard deviation, minimum, maximum, and range.
- **FR-007**: The feature extraction module MUST compute FFT-based frequency-domain features per axis per window, targeting the 3 Hz-12 Hz tremor band, including at minimum: dominant frequency within the band and spectral energy within the band.
- **FR-008**: The pipeline MUST compile all feature rows and labels into a single CSV file named `ready_for_training_features.csv` saved in `ml_data/processed/`.
- **FR-009**: The output CSV MUST have a header row and contain no NaN, infinite, or missing values.
- **FR-010**: The pipeline MUST use and update the existing `ml_data/` module structure without replacing it wholesale, preserving existing interfaces where compatible.
- **FR-011**: The pipeline MUST log a summary upon completion stating total files processed, total windows generated, label distribution (count per class), and output file path.

### Key Entities

- **Recording**: A single CSV file containing one sensor session, identified by a filename referenced in the metadata. Belongs to either the Parkinson or Control group.
- **Metadata Entry**: A row in the tabular metadata file describing a recording's validity status, subject identifier, and group label.
- **Window**: A contiguous slice of exactly 100 records from a single recording, never spanning two recordings.
- **Feature Vector**: A fixed-length numeric row computed from one window, containing time-domain and frequency-domain features for all 6 axes plus a binary label.
- **Output Dataset**: The collection of all feature vectors written as `ready_for_training_features.csv`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The pipeline completes without fatal errors when run against the full PSMAD dataset.
- **SC-002**: `ml_data/processed/ready_for_training_features.csv` exists and is non-empty after a successful run.
- **SC-003**: Every row in the output file contains exactly the expected number of feature columns plus one `label` column, with zero NaN or infinite values.
- **SC-004**: The output file contains windows from both class labels (`0` and `1`), confirming both dataset groups were processed.
- **SC-005**: All windows are exactly 100 records; no partial windows appear in the output.
- **SC-006**: The feature set includes both time-domain statistics (at minimum 5 stats x 6 axes = 30 features) and frequency-domain tremor-band features (at minimum 2 FFT features x 6 axes = 12 features).
- **SC-007**: The pipeline run produces a console/log summary confirming file count, window count, and label distribution.

## Assumptions

- The PSMAD sensor data was captured at a fixed, consistent sampling rate. The sampling rate required for FFT frequency-bin calculation is assumed to be derivable from the metadata file or from the `T`/`Timestamp` column in the CSV files.
- The metadata file is a tabular CSV or Excel file located within `DataParkinson/` at the root level (adjacent to the two group folders).
- "Invalid" and "functional validation" entries in the metadata are distinguishable by a specific column value (e.g., a `Type` or `Status` column); the exact column name will be confirmed by reading the metadata file before implementation.
- The existing `ml_data/` pipeline code is functional for prior datasets and only requires targeted updates (not a full rewrite) to support PSMAD column naming and the two new data paths.
- No model training, evaluation, or inference code is in scope for this feature.

## Out of Scope

- Model training, validation, or hyperparameter tuning.
- Inference or prediction scripts.
- Data augmentation or synthetic data generation.
- Any frontend or API changes.
- Deployment or containerization of the pipeline.
