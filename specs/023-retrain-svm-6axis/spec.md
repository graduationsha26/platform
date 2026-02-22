# Feature Specification: Retrain SVM on 6 Active Sensor Axes

**Feature Branch**: `023-retrain-svm-6axis`
**Created**: 2026-02-18
**Status**: Draft
**Input**: User description: "E-4.2 Retrain SVM on 6 Features — Update train_ml.py SVM section for 6 features. Retrain SVM with RBF kernel. Export svm_model.pkl."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Retrain SVM on 6 Active Sensor Axes and Export Named Artifact (Priority: P1) 🎯 MVP

A developer retrains the SVM classifier using only the 6 active glove sensor axes (accelerometer XYZ + gyroscope XYZ). The training run completes without error and exports the model as a clearly-named artifact (`svm_model.pkl`) alongside a metrics file. The artifact name is consistent with the naming convention established by the RF model (`rf_model.pkl`).

**Why this priority**: Without a retrained artifact under the correct filename, the inference pipeline cannot load the SVM model, blocking prediction capability. This is the core deliverable.

**Independent Test**: Run the training script targeting the SVM model; confirm `svm_model.pkl` exists, metrics JSON reports F1 ≥ 0.85, and loading the artifact confirms it accepts exactly 6 input values.

**Acceptance Scenarios**:

1. **Given** the training dataset and training script are available, **When** the developer runs training with the SVM option, **Then** the script completes without error and produces `svm_model.pkl` and `svm_model_metrics.json` in the model output directory.

2. **Given** `svm_model.pkl` has been produced, **When** the artifact is loaded and passed a 6-value sensor reading, **Then** it returns a valid class label with no shape or feature mismatch errors, and the model reports `n_features_in_ = 6`.

3. **Given** `svm_model.pkl` has been produced, **When** the metrics JSON is inspected, **Then** it contains accuracy, F1 score, feature count (= 6), kernel type, and training date — and F1 ≥ 0.85.

---

### User Story 2 — Inference Pipeline Loads svm_model.pkl Without Errors (Priority: P2)

The prediction service that serves tremor severity classifications is updated to look for `svm_model.pkl` instead of the old `svm.pkl` filename. After the one-line filename update, the prediction service initializes cleanly, confirms `n_features_in_ = 6`, and correctly classifies a test 6-axis reading.

**Why this priority**: The filename change from `svm.pkl` to `svm_model.pkl` must be reflected in the inference pipeline to avoid a `FileNotFoundError` at startup. This is a small follow-on change that makes the retrained artifact immediately usable.

**Independent Test**: Start the inference pipeline; confirm it loads `svm_model.pkl` with `n_features_in_ = 6` reported, and that a test prediction completes in under 70 ms with no errors.

**Acceptance Scenarios**:

1. **Given** `svm_model.pkl` exists and the inference pipeline's model filename reference has been updated, **When** the inference pipeline initializes, **Then** it reports `[OK] SVM: n_features_in_=6` and `[OK] ML Predictor ready` with no `FileNotFoundError`.

2. **Given** the inference pipeline is running with `svm_model.pkl` loaded, **When** a test reading of 6 sensor values is submitted, **Then** a valid prediction result is returned with latency under 70 ms and no input shape errors.

3. **Given** the old artifact `svm.pkl` still exists on disk, **When** the inference pipeline loads, **Then** it ignores `svm.pkl` and loads only `svm_model.pkl` — both files coexist without conflict.

---

### Edge Cases

- What happens when `svm_model.pkl` does not yet exist when the inference pipeline starts? → Pipeline logs a warning and continues without the SVM model (no crash); retraining is required.
- What happens if training is run with the old `svm.pkl` also present? → Both `svm.pkl` (legacy) and `svm_model.pkl` (new) coexist without conflict; neither overwrites the other.
- What happens if the input to the model has fewer or more than 6 values? → A validation error is raised before inference is attempted; the error message identifies the expected shape.
- What happens if the Dataset.csv file is missing? → Training exits with a clear `FileNotFoundError` message; no partial artifact is written.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST train the SVM classifier using exactly 6 sensor input dimensions (aX, aY, aZ, gX, gY, gZ) — no legacy fields (flex sensors, magnetometer axes) are included.
- **FR-002**: System MUST use an RBF (radial basis function) kernel for SVM training.
- **FR-003**: System MUST export the trained SVM model as `svm_model.pkl` to the configured output directory.
- **FR-004**: System MUST write a metrics file (`svm_model_metrics.json`) alongside the model artifact, containing: accuracy, F1 score, feature count, kernel type, and training timestamp.
- **FR-005**: The trained SVM model MUST achieve a weighted F1 score of ≥ 0.85 on the held-out test set (20% of Dataset.csv, stratified split).
- **FR-006**: The inference pipeline MUST be updated to load `svm_model.pkl` in place of the previous `svm.pkl` filename, with no other changes to inference logic.

### Key Entities

- **TrainedSVMModel**: The exported model artifact; accepts a 6-element sensor reading and returns a tremor severity class label; characterized by kernel type (RBF), C (regularization), gamma, and `n_features_in_ = 6`.
- **ModelMetricsRecord**: The JSON sidecar file recording accuracy, F1 score, feature count, kernel, and training date for audit and comparison purposes.
- **InferencePipeline**: The prediction service that loads `svm_model.pkl` at startup, validates `n_features_in_ = 6`, and serves real-time tremor severity predictions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Training run completes without error and produces both `svm_model.pkl` and `svm_model_metrics.json` in the output directory.
- **SC-002**: Trained SVM model achieves a weighted F1 score ≥ 0.85 on the 20% held-out test partition of Dataset.csv.
- **SC-003**: Loading `svm_model.pkl` and calling predict on a single 6-value sample returns a valid class label with no errors, and `n_features_in_` equals 6.
- **SC-004**: Inference pipeline initializes cleanly, logging `[OK] SVM: n_features_in_=6`, when `svm_model.pkl` is present.
- **SC-005**: A single-sample SVM prediction via the inference pipeline completes in under 70 ms.

## Assumptions

- The training dataset (`Dataset.csv`) is available at the repo root and contains labeled samples with the 6 required sensor columns plus a label column.
- The 6-axis feature extraction logic (`FEATURE_COLUMNS = ['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']`) is already correct in the training script — no feature selection changes are needed.
- The SVM will use fixed hyperparameters (RBF kernel, C=1.0, gamma='scale') consistent with the existing configuration; no hyperparameter grid search is in scope for this feature (that is a potential future enhancement).
- The old `svm.pkl` artifact is preserved as a legacy backup and is not deleted.
- Only two files change: the training script (export filename) and the inference pipeline (model filename reference).

## Scope Boundary

**In scope**:
- Renaming the SVM export from `svm.pkl` to `svm_model.pkl` in the training script
- Running the training to produce the new artifact
- Updating the inference pipeline's model filename reference
- Verifying artifact quality (6 features, F1 ≥ 0.85)

**Out of scope**:
- Hyperparameter tuning or grid search for SVM (RBF kernel with fixed C/gamma is sufficient)
- Normalization changes (current pipeline trains on raw features; normalization is a future enhancement)
- Any Django views, REST endpoints, migrations, or WebSocket changes
- Removing or replacing the legacy `svm.pkl` artifact
