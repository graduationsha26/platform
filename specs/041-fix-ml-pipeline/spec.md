# Feature Specification: Fix ML Pipeline Unit Mismatch

**Feature Branch**: `041-fix-ml-pipeline`  
**Created**: 2026-04-16  
**Status**: Draft  
**Input**: User description: "Rebuild the ML pipeline to fix a critical unit mismatch between training data (raw 16-bit ADC values) and live ESP32 sensor data (physical units m/s², rad/s). Unify scales, apply FFT-based feature extraction, and update live test scripts."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Data Aggregation, Normalization & Feature Extraction (Priority: P1)

A data scientist prepares the training dataset from Excel files located in `Data v2/Normal/` (label 0) and `Data v2/Parkinson/` (label 1). The system reads all `.xlsx` files, extracts the 6 sensor columns (`AcX, AcY, AcZ, GyX, GyY, GyZ`), and converts the raw 16-bit ADC values to physical units by dividing accelerometer values by 16384.0 (yielding g-force, then ×9.81 for m/s²) and gyroscope values by 131.0 (yielding °/s). This ensures training data matches the scale of live ESP32 sensor output.

After conversion, the system applies a sliding window (window size = 200 samples, stride = 30 samples) across each file's time series. For each window and each of the 6 axes, exactly 7 features are extracted: mean, standard deviation, max, min, RMS, median, and dominant frequency (via FFT). This produces 42 features per window (7 features × 6 axes).

The resulting feature matrix X and label vector y are saved to disk for downstream model training.

**Why this priority**: This is the foundational step — without correctly scaled and feature-extracted training data, all downstream models and inference will be invalid. The unit mismatch is the root cause of the current pipeline bug.

**Independent Test**: Run the aggregation script on the `Data v2/` directories and verify: (1) output matrices exist, (2) X has 42 feature columns, (3) accelerometer values after conversion fall within physical ranges (±2g × 9.81 ≈ ±19.6 m/s² for typical resting data), (4) gyroscope values fall within physical ranges (±250 °/s), (5) feature values are within expected statistical bounds.

**Acceptance Scenarios**:

1. **Given** Excel files in `Data v2/Normal/` and `Data v2/Parkinson/`, **When** the aggregation script is run, **Then** it reads all `.xlsx` files, converts ADC values to physical units, applies sliding windows, extracts 42 features per window, and saves X matrix and y vector to the processed output directory.
2. **Given** a single Excel file with known raw ADC values, **When** conversion is applied, **Then** accelerometer values are divided by 16384.0 (×9.81 for m/s²) and gyroscope values are divided by 131.0, producing values consistent with physical units.
3. **Given** a time series shorter than the window size (< 200 samples), **When** the sliding window is applied, **Then** the file is skipped with a warning logged, and processing continues with remaining files.

---

### User Story 2 - Train Model & Export Metadata (Priority: P1)

A data scientist trains a Random Forest classifier on the prepared feature matrices. The system loads the X and y matrices from Story 1, fits a StandardScaler on the training data, transforms the features, and trains a RandomForestClassifier. The trained model, fitted scaler, and a metadata file are all saved.

The metadata file captures the exact feature order (42 features: 7 per axis × 6 axes), the MPU6050 sensitivity scaling factors used during data preparation, and any other parameters needed for the live inference pipeline to replicate the exact same preprocessing.

**Why this priority**: The model and its metadata are the bridge between offline training and live inference. Without correct metadata, the live pipeline cannot replicate the training preprocessing.

**Independent Test**: Load the saved model, scaler, and metadata. Verify: (1) model makes predictions on a sample of the training data with reasonable accuracy, (2) scaler transform produces the same output as during training, (3) metadata JSON contains the complete feature order list and scaling factors, (4) a fresh Python session can load all three artifacts and produce a prediction.

**Acceptance Scenarios**:

1. **Given** X and y matrices from Story 1, **When** the training script is run, **Then** a StandardScaler is fit on training data, a RandomForestClassifier is trained, and both are saved as `.pkl` files.
2. **Given** the training is complete, **When** the metadata file is generated, **Then** it contains: feature names in exact order, MPU6050 sensitivity factors (accel: 16384.0, gyro: 131.0), window size, stride, and sampling rate.
3. **Given** saved model artifacts, **When** loaded in a new session and used to predict on the training data subset, **Then** predictions achieve classification accuracy above 80%.

---

### User Story 3 - Synchronize Live Inference & Test Scripts (Priority: P1)

A developer updates the live inference pipeline so that incoming real-time sensor data undergoes the exact same feature extraction and scaling as the training data. The PreprocessingService is updated to: (1) collect sensor readings into a sliding window buffer, (2) extract the same 42 features using the identical extraction function from Story 1, (3) apply the saved StandardScaler transform, and (4) pass the result to the model for prediction.

Additionally, the standalone live test script (used for MQTT-based glove testing) is updated to load the new model, load the new scaler, and apply the same feature extraction pipeline to incoming MQTT sensor data.

**Why this priority**: This closes the loop — ensuring the live system uses the exact same preprocessing as training, eliminating the unit mismatch bug that motivated this entire rebuild.

**Independent Test**: (1) Feed synthetic sensor data (known physical-unit values) through the updated PreprocessingService and verify the 42-feature output matches what the training script would produce for the same input. (2) Run the live test script with a mock MQTT payload and verify it loads the correct model/scaler and produces a valid prediction.

**Acceptance Scenarios**:

1. **Given** a stream of live sensor data in physical units, **When** processed by the updated PreprocessingService, **Then** the system extracts the same 42 features in the same order as the training pipeline and applies the saved StandardScaler before prediction.
2. **Given** the updated live test script, **When** it receives MQTT sensor data, **Then** it loads the new model and scaler from their saved paths, applies the same feature extraction function, and outputs a tremor/normal prediction.
3. **Given** identical numeric input values, **When** processed through both the training feature extraction and the live inference feature extraction, **Then** the resulting 42-feature vectors are numerically identical.

---

### Edge Cases

- What happens when an Excel file contains fewer than 200 rows (less than one full window)? The file is skipped with a warning.
- What happens when an Excel file has missing or corrupt sensor columns? The file is skipped with an error logged, and processing continues.
- What happens when the live sensor stream has gaps or missing samples in the sliding window buffer? The system waits until the buffer is full before extracting features; partial windows are not processed.
- What happens when the saved model/scaler files are missing at inference time? The system raises a clear error indicating which artifact file is missing and its expected path.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST convert raw 16-bit ADC accelerometer values to physical units by dividing by 16384.0 (and multiplying by 9.81 for m/s²) during training data preparation.
- **FR-002**: System MUST convert raw 16-bit ADC gyroscope values to physical units by dividing by 131.0 (yielding °/s) during training data preparation.
- **FR-003**: System MUST apply a sliding window of size 200 with stride 30 to the converted time-series data.
- **FR-004**: System MUST extract exactly 7 features per axis (mean, std, max, min, RMS, median, dominant_freq via FFT) for each of the 6 sensor axes, producing 42 features per window.
- **FR-005**: System MUST read Excel files from `Data v2/Normal/` (label 0) and `Data v2/Parkinson/` (label 1) as the training data source.
- **FR-006**: System MUST fit a StandardScaler on training features and save both the scaler and trained RandomForestClassifier as serialized artifacts.
- **FR-007**: System MUST generate a metadata file containing the exact feature order, MPU6050 scaling factors, window size, stride, and any parameters needed to reproduce the preprocessing.
- **FR-008**: System MUST ensure the live inference pipeline applies the identical feature extraction function and saved StandardScaler as used during training.
- **FR-009**: System MUST update the live test script to load the new model, scaler, and apply the same feature extraction on MQTT data.
- **FR-010**: System MUST share a single feature extraction function between training, inference, and test scripts to guarantee consistency.

### Key Entities

- **SensorReading**: A single timestamped 6-axis measurement (AcX, AcY, AcZ, GyX, GyY, GyZ) in physical units after conversion.
- **FeatureWindow**: A sliding window of 200 consecutive SensorReadings, from which 42 features are extracted.
- **TrainingArtifacts**: The set of saved files (model `.pkl`, scaler `.pkl`, metadata `.json`) produced by the training pipeline and consumed by inference.
- **PipelineMetadata**: Configuration record detailing feature order, scaling factors, window parameters — the contract between training and inference.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Training data accelerometer values after conversion fall within ±20 m/s² (consistent with MPU6050 ±2g range), and gyroscope values fall within ±250 °/s.
- **SC-002**: Feature extraction produces exactly 42 features per window for all processed files, with no NaN or infinite values.
- **SC-003**: Trained model achieves classification accuracy above 80% on a held-out test split of the prepared data.
- **SC-004**: Given identical numeric input, the training feature extraction and live inference feature extraction produce numerically identical 42-feature vectors (within floating-point tolerance of 1e-10).
- **SC-005**: The live test script successfully loads the new model and scaler, processes a sample MQTT payload, and produces a valid prediction (0 or 1) without errors.

## Assumptions

- MPU6050 is configured with ±2g accelerometer sensitivity (sensitivity factor: 16384.0 LSB/g) and ±250°/s gyroscope sensitivity (sensitivity factor: 131.0 LSB/°/s). These are the default full-scale ranges.
- The Excel files in `Data v2/` use the same MPU6050 configuration as the live ESP32 device.
- The live ESP32 sensor outputs accelerometer data in m/s² and gyroscope data in °/s (i.e., the firmware already applies the sensitivity conversion).
- Magnetometer columns (if present) are ignored as they are disabled on the hardware (all values = -1).
- The `Hora` and `miliseg` timestamp columns in the Excel files are not used as features but may be used for ordering.
- A sampling rate of approximately 250 Hz is assumed for FFT dominant frequency calculation (to be validated against actual Excel file timing data).
- The gravity component is handled by the FFT-based dominant frequency feature (which captures tremor-band oscillations) rather than by an explicit high-pass gravity filter on the raw signal.

## Constraints

- The feature extraction function must be defined in a single shared location and imported by all three consumers (training script, inference service, live test script) — no code duplication.
- All saved artifacts (model, scaler, metadata) must be loadable by standard Python libraries (joblib/pickle for `.pkl`, json for `.json`) without custom dependencies.
- The pipeline must work with the existing Excel file format (columns: Hora, miliseg, AcX, AcY, AcZ, GyX, GyY, GyZ).
