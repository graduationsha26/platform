# Feature Specification: Gravity Filter Fix for ML Pipeline

**Feature Branch**: `040-gravity-filter-fix`  
**Created**: 2026-04-13  
**Status**: Draft  
**Input**: User description: "Fix ML models predicting on gravity instead of tremor - implement signal processing filter in data pipeline, retrain models, and sync filter to live inference"

## User Scenarios & Testing

### User Story 1 - Gravity-Removed Training Data Pipeline (Priority: P1)

A data engineer runs the training data preparation pipeline and the output dataset contains sensor features computed only from the dynamic (tremor) component of accelerometer signals, with all static gravity bias removed before feature extraction.

**Why this priority**: This is the foundational fix. Without gravity-free training data, no downstream model can distinguish tremor from hand orientation. Every other story depends on this corrected data existing.

**Independent Test**: Run the data preparation script on the existing dataset. Compare the accelerometer signal statistics before and after filtering: the filtered signal should have near-zero mean on each accelerometer axis (gravity removed), while gyroscope axes remain unchanged. Verify that a static, motionless hand produces near-zero feature values instead of large gravity-dependent values.

**Acceptance Scenarios**:

1. **Given** a raw sensor recording of a motionless hand in any orientation, **When** the gravity filter is applied, **Then** the resulting accelerometer signal has a mean within 0.05 g of zero on all three axes.
2. **Given** a raw sensor recording containing Parkinson's tremor, **When** the gravity filter is applied, **Then** the tremor oscillation pattern is preserved in the filtered signal while the static offset is removed.
3. **Given** the existing training dataset, **When** the updated pipeline runs end-to-end, **Then** a new feature file is produced with gravity-filtered features and the filter parameters (cutoff frequency, filter order, sampling rate) are saved to a metadata file.
4. **Given** gyroscope data in the same recording, **When** the pipeline runs, **Then** gyroscope channels pass through unmodified (gyroscopes do not measure gravity).

---

### User Story 2 - Retrained Models with Gravity-Filtered Data (Priority: P2)

A data scientist retrains all ML and DL models using the gravity-filtered training data from Story 1. The retrained models achieve improved classification accuracy on tremor vs. no-tremor, and each model's metadata file records the exact filter parameters used during training so the live system can reproduce the same preprocessing.

**Why this priority**: Retrained models are the direct product of the corrected data. Without retraining, the fix has no effect on predictions. This depends on Story 1 being complete.

**Independent Test**: Retrain models on gravity-filtered data and compare classification metrics (accuracy, F1-score, confusion matrix) against the previously trained models on the same test set. The retrained models should show improvement, particularly in reducing false positives caused by hand orientation changes. Verify that each model's JSON metadata file contains the filter parameters.

**Acceptance Scenarios**:

1. **Given** gravity-filtered training features, **When** the ML models (Random Forest, SVM) are retrained, **Then** the new models achieve equal or better F1-score compared to the previous models.
2. **Given** gravity-filtered training sequences, **When** the DL models (LSTM, CNN-1D) are retrained, **Then** the new models achieve equal or better F1-score compared to the previous models.
3. **Given** a retrained model, **When** its metadata JSON file is inspected, **Then** it contains a `filter_params` section with the exact cutoff frequency, filter order, filter type, and sampling rate used during training.
4. **Given** a test recording where a user slowly rotates their hand without tremor, **When** the retrained model predicts on gravity-filtered input, **Then** the model correctly predicts "no tremor" (severity 0) instead of falsely detecting tremor from orientation change.

---

### User Story 3 - Synchronized Live Inference Filter (Priority: P3)

A doctor monitors a patient wearing the smart glove through the live dashboard. The real-time sensor data streaming through the WebSocket is preprocessed with the exact same gravity filter used during training before being fed to the model, ensuring prediction consistency between training and live environments.

**Why this priority**: This is the final integration step that makes the fix visible to end users. Without live sync, retrained models receive differently-preprocessed data at inference time, producing unreliable predictions. This depends on Stories 1 and 2.

**Independent Test**: Send a known sensor payload through the live inference API. Capture the preprocessed values just before model input and compare them with the output of running the same raw data through the training pipeline's filter. The values must match within floating-point tolerance. Additionally, verify that slowly rotating the glove without tremor does not trigger false tremor alerts on the dashboard.

**Acceptance Scenarios**:

1. **Given** a live sensor data payload, **When** it passes through the PreprocessingService, **Then** the accelerometer channels are filtered using the exact same filter parameters (cutoff, order, type, sampling rate) stored in the model's metadata file.
2. **Given** identical raw sensor data, **When** processed through both the training pipeline filter and the live PreprocessingService filter, **Then** the output values match within a tolerance of 1e-6.
3. **Given** a patient slowly rotating their hand without tremor during a live session, **When** the filtered data is fed to the model, **Then** the system reports severity 0 (no tremor) consistently.
4. **Given** a patient experiencing Parkinson's tremor during a live session, **When** the filtered data is fed to the model, **Then** the system correctly detects and reports the appropriate tremor severity level.

---

### Edge Cases

- What happens when the sensor sampling rate varies or is inconsistent across recordings? The filter must handle the configured sampling rate; recordings with significantly different rates should be flagged or resampled.
- What happens if the filter introduces phase delay that shifts tremor oscillation timing? The filter design must minimize phase distortion to preserve temporal characteristics of tremor signals.
- What happens when the live inference buffer has fewer samples than the filter requires to initialize? The system must handle the warm-up period gracefully, either buffering until enough samples arrive or using a zero-phase initialization.
- What happens if the gravity component changes rapidly (e.g., patient drops hand suddenly)? The filter must track orientation changes without introducing artifacts that mimic tremor.

## Requirements

### Functional Requirements

- **FR-001**: System MUST apply a high-pass filter to accelerometer channels (aX, aY, aZ) to remove the static gravity component before any feature extraction or model inference.
- **FR-002**: System MUST NOT apply the gravity filter to gyroscope channels (gX, gY, gZ), as gyroscopes measure angular velocity and are not affected by gravity.
- **FR-003**: System MUST use a filter with a cutoff frequency below the Parkinson's tremor band (3-12 Hz) to preserve all tremor-related signal content while removing the near-DC gravity component.
- **FR-004**: System MUST save the filter parameters (type, cutoff frequency, order, sampling rate) to each model's metadata JSON file during training.
- **FR-005**: System MUST load filter parameters from the model's metadata JSON file during live inference and apply the identical filter to incoming sensor data.
- **FR-006**: System MUST implement the gravity filter in the data preparation pipeline scripts located in `backend/ml_data/scripts/`.
- **FR-007**: System MUST implement the identical gravity filter in the PreprocessingService located in `backend/inference/services.py`.
- **FR-008**: System MUST ensure mathematical equivalence between the training filter and the live inference filter, producing identical outputs for identical inputs within floating-point tolerance.
- **FR-009**: System MUST retrain all ML models (Random Forest, SVM) and DL models (LSTM, CNN-1D) on the gravity-filtered data.
- **FR-010**: System MUST handle the filter warm-up period during live inference when insufficient samples are available for full filter initialization.

### Key Entities

- **Filter Parameters**: The mathematical configuration of the gravity-removal filter (type, cutoff frequency, order, sampling rate). Stored in model metadata and shared between training and inference.
- **Filtered Sensor Data**: Accelerometer data with gravity removed, retaining only the dynamic tremor component. The primary input to all downstream feature extraction and model prediction.
- **Model Metadata**: Extended JSON files for each trained model, now including filter parameters alongside existing normalization/scaler parameters.

## Success Criteria

### Measurable Outcomes

- **SC-001**: A motionless hand held in any orientation produces a predicted tremor severity of 0 (no tremor) at least 95% of the time, compared to the current baseline where orientation changes cause false positives.
- **SC-002**: Retrained models achieve equal or better F1-score on the existing test dataset compared to the pre-filter models.
- **SC-003**: The numerical output of the training pipeline filter and the live inference filter, given identical input data, differs by no more than 1e-6 on any sample.
- **SC-004**: The end-to-end latency of live inference (including the new filtering step) remains under 5 seconds per prediction, consistent with the existing timeout constraint.
- **SC-005**: Filter parameters are fully recoverable from any trained model's metadata file, enabling reproducible preprocessing without access to source code constants.

## Assumptions

- The sensor sampling rate is approximately 37 Hz (as detected from the PSMAD dataset Timestamp column) and is consistent enough for the filter to operate correctly.
- A high-pass Butterworth filter with a cutoff around 0.5-1.0 Hz is the appropriate signal processing approach, as Parkinson's tremor occurs in the 3-12 Hz band and gravity is a near-DC (0 Hz) component.
- The existing gyroscope data does not require gravity filtering and can continue to be processed as-is.
- The PSMAD dataset used for training is representative of the live sensor data the glove produces.

## Dependencies

- Existing training dataset must be available and accessible at the expected paths.
- Existing model training scripts and inference services must be functional as a baseline.
- The scipy library (or equivalent) must be available for implementing the Butterworth filter in Python.
