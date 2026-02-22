# Feature Specification: Retrain Random Forest on 6 Active Sensor Axes

**Feature Branch**: `022-retrain-rf-6axis`
**Created**: 2026-02-18
**Status**: Draft
**Input**: User description: "Retrain RF on 6 Features — Update train_ml.py to use only [aX,aY,aZ,gX,gY,gZ] columns. Retrain Random Forest with GridSearchCV. Export rf_model.pkl."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Train Model on 6 Active Sensor Axes with Hyperparameter Optimization (Priority: P1)

The ML engineer runs the training pipeline and it produces a Random Forest classifier trained exclusively on the 6 active IMU sensor axes (aX, aY, aZ, gX, gY, gZ). The pipeline systematically searches for the best model configuration, reports performance metrics, and exports the trained model as a deployable artifact.

Previously the model was trained on 9 features including 3 magnetometer channels that are permanently disabled on the glove hardware (always outputting a constant value). Removing these dead channels aligns the training data with what the live system actually collects, eliminating a source of noise and potential accuracy loss.

**Why this priority**: Without a correctly-scoped trained model, the inference pipeline cannot produce meaningful tremor severity predictions from live glove data. This is the core deliverable of the feature.

**Independent Test**: Run the training pipeline end-to-end; verify it loads exactly 6 feature columns from the dataset (no magnetometer columns), completes hyperparameter search, reports accuracy and classification metrics, and produces a model artifact file. Load the artifact and call predict with a 6-element input — confirm no error and a valid class label is returned.

**Acceptance Scenarios**:

1. **Given** a training dataset containing IMU sensor readings labeled with tremor severity classes, **When** the training pipeline is executed, **Then** it loads only the 6 active axis columns (aX, aY, aZ, gX, gY, gZ) and excludes magnetometer columns (mX, mY, mZ).

2. **Given** the 6-axis training data is loaded, **When** hyperparameter optimization runs, **Then** the pipeline evaluates multiple model configurations and selects the best-performing one based on cross-validation accuracy.

3. **Given** hyperparameter optimization completes, **When** the pipeline finishes, **Then** it reports classification performance metrics (overall accuracy and per-class precision, recall, F1) to the console and exports a model artifact file.

4. **Given** the model artifact has been exported, **When** it is loaded and given a 6-element numeric input, **Then** it returns a valid tremor severity class prediction without errors.

---

### User Story 2 — Exported Model is Immediately Compatible with the Inference Pipeline (Priority: P2)

The exported model artifact can be loaded by the existing inference system (which serves live predictions via the backend API) without any changes to the serving layer. The model's expected input shape matches the 6-axis normalization configuration already in place.

**Why this priority**: A model trained and exported in isolation is useless if the serving infrastructure rejects it. Verifying end-to-end compatibility ensures the retrained model slots directly into the live system.

**Independent Test**: Load the exported model artifact via the same code path used by the inference API. Pass a normalized 6-axis reading as input. Confirm the prediction output is a valid severity class and no shape or schema errors occur.

**Acceptance Scenarios**:

1. **Given** the exported model artifact exists at the expected path, **When** the inference system loads it, **Then** no loading errors occur and the model is ready to serve predictions.

2. **Given** the loaded model and a normalized 6-axis input (values produced by the existing normalization pipeline using params.json), **When** a prediction is requested, **Then** the model returns a tremor severity class label without raising any input-shape or type error.

3. **Given** the retrained model is in place, **When** a new prediction request arrives at the inference endpoint, **Then** the system serves a prediction using the new model without requiring any code changes to the serving layer.

---

### Edge Cases

- What happens if the training dataset contains rows with missing values in one of the 6 active axis columns? (Pipeline should report the issue, not silently produce a corrupted model.)
- What happens if hyperparameter search yields a model with accuracy below a meaningful threshold (e.g., below 70%)? (Pipeline should still report metrics; engineer can investigate before deploying.)
- What happens if a model artifact already exists at the export path? (New artifact must overwrite the previous file without error.)
- What happens if the dataset has severe class imbalance across tremor severity categories? (Per-class metrics must be reported so imbalance effects are visible, not masked by overall accuracy.)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The training pipeline MUST load feature columns aX, aY, aZ, gX, gY, gZ from the training dataset and MUST NOT include mX, mY, or mZ columns in the training data.
- **FR-002**: The training pipeline MUST perform systematic hyperparameter optimization across multiple model configurations and select the best-performing configuration based on cross-validated accuracy.
- **FR-003**: The training pipeline MUST report classification performance metrics — including overall accuracy and per-class precision, recall, and F1-score — upon completion.
- **FR-004**: The training pipeline MUST export the trained model as a reusable artifact to a fixed, known file path so the inference system can locate it without configuration changes.
- **FR-005**: The exported model artifact MUST accept exactly 6 numeric input values (one per active sensor axis) and return a tremor severity class label.
- **FR-006**: The exported model artifact MUST be loadable by the existing inference pipeline code without any changes to the serving layer.

### Key Entities

- **Training Dataset**: Labeled IMU sensor recordings; each sample contains 6 active axis measurements (aX, aY, aZ, gX, gY, gZ) and a tremor severity class label. Magnetometer columns (mX, mY, mZ) are present in the raw file but excluded during loading.
- **Random Forest Classifier**: The trained predictive model; maps a 6-axis sensor reading to a tremor severity class. Hyperparameters are selected via systematic cross-validated search over a predefined grid.
- **Model Artifact**: The serialized form of the trained classifier; stored at a fixed file path; consumed by the inference pipeline to serve live predictions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The training pipeline completes end-to-end without errors and produces a model artifact at the expected file path.
- **SC-002**: Training data fed to the model has exactly 6 columns — verified by inspecting the feature matrix shape before fitting (shape must be [N, 6] for N samples).
- **SC-003**: The exported model artifact produces a valid tremor severity prediction when given a 6-element input — no shape or schema errors from the inference pipeline.
- **SC-004**: The best model configuration found by hyperparameter search achieves at least 75% cross-validation accuracy on the training data.
- **SC-005**: Per-class metrics (precision, recall, F1) are reported for all tremor severity classes so class imbalance effects are visible to the engineer.

## Assumptions

- The training dataset (`Dataset.csv`) is already available in the repository and contains columns aX, aY, aZ, gX, gY, gZ, mX, mY, mZ plus a class label column. The pipeline must drop mX, mY, mZ before training.
- The existing normalization parameters (`params.json`) already cover exactly the 6 active axes and are compatible with the model input. No changes to the normalization configuration are needed.
- The inference pipeline loads the model artifact from a fixed file path. Replacing the file at that path is sufficient to deploy the retrained model — no code changes to the serving layer are required.
- Class labels in the training dataset represent distinct tremor severity levels and are already encoded appropriately for classification.
- Training runs offline (not in real time) and may take several minutes; no latency constraint applies to the training script itself.
- The model artifact serialization format must remain compatible with the existing inference code (same format as the current model file).
