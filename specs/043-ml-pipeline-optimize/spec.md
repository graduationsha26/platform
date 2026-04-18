# Feature Specification: ML Pipeline Optimization & Confidence Scoring

**Feature Branch**: `043-ml-pipeline-optimize`  
**Created**: 2026-04-18  
**Status**: Draft  
**Input**: User description: "We need to optimize the machine learning pipeline for lower latency and implement confidence scoring in the live test."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reduce Window Memory & Retrain (Priority: P1)

A machine learning engineer needs to reduce the size of the data window used during feature extraction in order to halve the memory buffer, which in turn allows the classification system to switch between tremor states faster. After reconfiguring the window parameters, they re-run the full data pipeline — from raw sensor data aggregation through feature extraction and model training — producing a new v3 model. The inference service is then updated to load this lighter, faster model so that all real-time predictions benefit from the reduced latency.

**Why this priority**: Smaller windows reduce the buffering delay between a real tremor event and a detected state change. This directly impacts the responsiveness of the CMG suppression system and is foundational — the v3 model produced here is a prerequisite for Story 2's confidence-scored live output.

**Independent Test**: Run the feature extraction script with Window=100 and Stride=15, confirm it produces feature files, then run the training script and confirm a v3 model artifact is saved. Update the inference service configuration to point at v3. Send a batch of test sensor samples to the inference service and confirm predictions are returned without error.

**Acceptance Scenarios**:

1. **Given** the feature extraction script is configured with Window=100 and Stride=15, **When** it is executed against the raw training data, **Then** it produces a new set of feature files that are smaller in row count than the previous Window=200 configuration.

2. **Given** the new feature files are available, **When** the training script is executed, **Then** it saves a new model artifact labeled v3 (and its corresponding scaler) without error.

3. **Given** the v3 model and scaler are saved, **When** the inference service configuration is updated to reference them, **Then** the inference service loads them successfully on startup and serves predictions for incoming sensor windows.

4. **Given** the inference service is running with the v3 model, **When** a test sensor window is submitted, **Then** a classification result is returned with no errors related to feature shape mismatch.

---

### User Story 2 - Implement Confidence Scoring in Live Test (Priority: P1)

An engineer running the live glove test needs to see not just the predicted tremor state but also how certain the model is about each prediction. The terminal output must be clearly formatted, human-readable, and include a timestamp, a visual state indicator, the state label and class index, and the confidence percentage — so that the engineer can immediately assess whether the classifier is operating reliably on real hardware data.

**Why this priority**: A binary predict/no-predict output gives no signal about model reliability during hardware testing. Confidence scores enable engineers to identify ambiguous predictions, catch distribution shift between training and live data, and decide when the model needs retraining — all in real time, at a glance.

**Independent Test**: Run the live test script against a hardware glove or a replay of recorded MQTT sensor data. Observe the terminal. Confirm every prediction line includes a timestamp in `[HH:MM:SS.mmm]` format, a state emoji (✅ for NORMAL, ⚠️ for TREMOR), the state name and class index, and a confidence percentage rounded to one decimal place.

**Acceptance Scenarios**:

1. **Given** the live test script is running and receives sensor data, **When** a NORMAL state is classified, **Then** the terminal prints a line exactly matching the format: `[HH:MM:SS.mmm] ✅ NORMAL (0) | Confidence: XX.X%`.

2. **Given** the live test script is running and receives sensor data, **When** a TREMOR state is classified, **Then** the terminal prints a line exactly matching the format: `[HH:MM:SS.mmm] ⚠️ TREMOR (1) | Confidence: XX.X%`.

3. **Given** the live test script is running, **When** predictions are produced in rapid succession, **Then** each line is printed independently with its own timestamp and confidence — no output lines are merged or truncated.

4. **Given** a prediction has low confidence (e.g., below 60%), **When** it is printed to the terminal, **Then** it still follows the same format — confidence scoring does not suppress or alter the output structure.

---

### Edge Cases

- What happens if the v3 model's feature shape does not match the live window size used during testing? (The system should raise a clear, descriptive error rather than silently producing wrong predictions.)
- What if the confidence returned by the classifier is exactly 50% for both classes? (The higher-probability class is still selected and displayed; the output format is unchanged.)
- What happens if raw training data is insufficient after reducing the window? (The pipeline should fail fast with a count-too-low error before producing a corrupt model.)
- What if the live test script cannot connect to the MQTT broker or the glove device? (Confidence scoring output format does not affect the connection error handling — existing error paths remain unchanged.)

## Clarifications

### Session 2026-04-18

- Q: Should v3 model artifacts, scalers, and JSON metadata be tracked in version control so they can be shared and deployed without requiring a local retraining step? → A: Yes — all `.pkl`, `.h5`, and JSON metadata files under `backend/ml_models/models/` must be committed to git. The `.gitignore` rules that previously excluded these files have been commented out. (Source: user clarification 2026-04-18)
- Q: Should the v3 model be required to meet a minimum accuracy threshold before the inference service switches to it — or is producing a trained v3 artifact sufficient? → A: No accuracy gate required. v3 is deployed as soon as it is produced; the engineer reviews training metrics manually after the fact.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The feature extraction script MUST support configurable Window and Stride parameters, and be re-run with Window=100 and Stride=15 to produce a new set of training-ready feature files.

- **FR-002**: The model training script MUST be re-executed against the new feature files and MUST save the resulting model and scaler as versioned artifacts (v3), distinct from prior versions.

- **FR-003**: The inference service MUST be updated to load the v3 model and v3 scaler as its active classification assets, replacing the previous version.

- **FR-004**: The inference service MUST accept incoming sensor windows and return classification results without feature shape errors after the v3 update.

- **FR-005**: The live test script MUST use probability-based prediction (returning a confidence score per class) instead of hard-label-only prediction.

- **FR-006**: The live test terminal output MUST include, on every prediction line: a wall-clock timestamp (millisecond precision), a state-specific emoji indicator (✅ for NORMAL, ⚠️ for TREMOR), the state label and numeric class index, and the confidence percentage rounded to one decimal place.

- **FR-007**: The output format MUST match exactly: `[HH:MM:SS.mmm] ✅ NORMAL (0) | Confidence: XX.X%` or `[HH:MM:SS.mmm] ⚠️ TREMOR (1) | Confidence: XX.X%`.

- **FR-008**: The live test script MUST determine the predicted class as the one with the highest probability, and display that class's probability as the confidence score.

- **FR-009**: The v3 model artifacts, scalers, and JSON metadata MUST be committed to version control so they can be shared across team members and deployed without requiring a local retraining step. Any version control ignore rules that previously excluded these file types from the model directories MUST be removed or disabled.

### Key Entities

- **Feature Window**: A fixed-length segment of sensor readings used as input to the classifier. Defined by two parameters — Window (number of samples) and Stride (step size between windows). Reducing Window reduces memory and latency.
- **Model Artifact (v3)**: The trained classifier file produced after retraining on the new feature files. Paired with a matching scaler artifact. Both must be versioned and stored alongside prior versions.
- **Confidence Score**: The probability assigned by the classifier to the predicted class, expressed as a percentage (0.0–100.0). Derived from a probability distribution across all classes.
- **Live Prediction Line**: A single terminal output entry per inference call, containing timestamp, state indicator, state label + index, and confidence score.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The feature buffer size is reduced by at least 50% compared to the previous Window=200 configuration — verified by comparing output row counts of the feature extraction script before and after.

- **SC-002**: The v3 model and its scaler are saved as distinct artifacts from v2 and can be loaded by the inference service without errors.

- **SC-003**: The inference service serves predictions from the v3 model within the same response-time envelope as the prior version (no measurable regression in throughput).

- **SC-004**: Every live test terminal output line includes a confidence percentage, with no prediction lines lacking a confidence value.

- **SC-005**: The terminal output format is 100% consistent — all NORMAL predictions display ✅ and all TREMOR predictions display ⚠️, with no format variations across a 60-second live test run.

## Assumptions

- The raw training dataset is already collected and available in the expected location under `backend/ml_data/`. No new data collection is required for this feature.
- The previous model was trained with Window=200; Window=100 and Stride=15 are the target parameters. Exact prior Stride value is assumed to be larger (e.g., 20–50).
- The classification task is binary: class 0 = NORMAL, class 1 = TREMOR. No additional classes exist.
- The v3 model is a retrained version of the same algorithm used for v2 (no algorithm change), only the training data window configuration changes. No accuracy gate is required before deployment — the engineer reviews training metrics manually and decides whether to keep v3 in production.
- The live test script currently runs locally, consuming MQTT sensor data from the glove hardware or a replay source. No changes to the MQTT subscription or data source are required.
- Model files use a naming convention that allows versioning (e.g., `model_v3`, `scaler_v3`) without breaking the directory structure.

## Scope

**In scope**:
- Reconfiguring and re-running the feature extraction script (Window=100, Stride=15)
- Re-running the training script to produce v3 model and scaler artifacts
- Updating the inference service to load v3 assets
- Updating the live test script to use probability-based prediction and formatted output
- Updating version control ignore rules to allow model artifacts (`.pkl`, `.h5`, JSON metadata) to be committed

**Out of scope**:
- Collecting new training data
- Changing the classification algorithm or model architecture
- Changes to the Django REST API, WebSocket pipeline, or React dashboard
- Changes to ESP32 firmware or MQTT topic structure
- Automated retraining pipelines or model registry systems
