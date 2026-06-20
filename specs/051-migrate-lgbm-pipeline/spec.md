# Feature Specification: Migrate LGBM Tremor Classification Pipeline to Backend

**Feature Branch**: `051-migrate-lgbm-pipeline`
**Created**: 2026-06-20
**Status**: Draft
**Input**: User description: "Migrate LGBM pipeline to backend, save processed data, and set up live testing. 1. Read `LGBM.ipynb` for preprocessing, feature extraction, and LightGBM configuration. 2. Implement this logic in `backend/ml_models/train.py`: Load data from `Clean Dataset – Control Group`, `Clean Dataset – Parkinson's Group`, `Clean Dataset – Voluntary Group`. Apply preprocessing and combine the datasets. SAVE DATA: Export this combined, preprocessed dataset to `backend/ml_data/combined_processed_data.csv` BEFORE initializing any model training. Train the LightGBM model and save the `.pkl` file directly inside `backend/ml_models/`. 3. Delete all other unrelated model files and scripts in `backend/ml_models/`. 4. Create `backend/test_AI_live.py` to evaluate live sensor data. Output format must strictly match: \"Sample, Prediction, Confidence, Precision, Non-Tremor %, Tremor %, Voluntary %\". Review `LGBM.ipynb` first before writing code to ensure exact feature matching."

## Clarifications

### Session 2026-06-20

- Q: Should the new training script reproduce the notebook's `RandomizedSearchCV` hyperparameter search, or train with a fixed configuration? → A: Pin the best validated configuration from the notebook and train with fixed hyperparameters; do NOT run `RandomizedSearchCV` in the new script, so training is fast and reproducible.
- Q: The notebook never persists the winning hyperparameters — how should the pinned values be obtained? → A: Run the notebook's search once during development to discover the actual best-performing hyperparameters, then hardcode exactly those values into the training script.
- Q: How should live sensor input be processed so it matches the trained model's expectations? → A: The live stream rate is ground truth from the ESP32 firmware (must be read/confirmed from the firmware source; suspected ~100 Hz). Each live window MUST be resampled (fast vectorized resampling, e.g. SciPy/NumPy) to the 66.67 Hz / 1-second / ~66-sample shape the model expects, then have the 0.5–20 Hz bandpass and the 66-feature extraction applied on the resampled data (no scaler — the notebook's LightGBM uses none).
- Q: What latency/cadence must live evaluation meet? → A: Output drives real-time hardware stabilization, so extreme low latency is required. Maintain a 1-second rolling buffer (e.g. `deque`) but slide the window and emit a prediction every 100 ms rather than waiting a full second per prediction; keep the resample → filter → feature pipeline fully vectorized (avoid Python `for` loops).
- Q: Where should the new model artifact live and how are consumers wired? → A: Save the single new model directly in `backend/ml_models/` with a descriptive name (e.g. `lgbm_tremor_model.pkl`). Completely delete the old `backend/ml_models/models/` subdirectory and obsolete files (e.g. `rf_model_v3.pkl`). Update `backend/inference/services.py` and every other consumer to load the new path, removing outdated old-model-specific logic.
- Q: What is the canonical name/location of the live-evaluation script? → A: `backend/test_AI_live.py` (backend root), as in the original feature description.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reproducible, audit-ready training dataset (Priority: P1)

As the engineer maintaining TremoAI's tremor-classification pipeline, I need the three clinical recording groups (Non-Tremor/Control, Parkinsonian Tremor, Voluntary movement) cleaned, combined, and saved as a single dataset before any model is trained, so that the exact data behind any trained model can be inspected, audited, or reused later without re-running raw preprocessing from the original recordings every time.

**Why this priority**: This is the foundation everything else depends on. Without a trustworthy, persisted combined dataset, neither training nor any future re-validation of the model is reproducible or auditable — a critical property for a clinical-adjacent ML pipeline.

**Independent Test**: Run only the data-preparation step and verify a single combined dataset file is produced containing correctly labeled samples drawn from all three recording groups, with no model training required for this step to be considered complete and valuable.

**Acceptance Scenarios**:

1. **Given** the three raw recording groups are available on disk, **When** the data-preparation step runs, **Then** a single combined, preprocessed dataset file containing labeled samples from all three groups is saved to a known backend location before any training step starts.
2. **Given** the combined dataset has already been produced once, **When** the data-preparation step is re-run against the same raw recordings, **Then** the regenerated dataset has the same row count and class distribution as before, confirming the process is deterministic and repeatable.
3. **Given** the combined dataset file exists, **When** someone inspects it, **Then** every row is traceable to one of the three recording groups and carries the correct class label (Non-Tremor, Parkinsonian Tremor, or Voluntary).

---

### User Story 2 - Single trusted classification model (Priority: P1)

As the engineer, I need one trained, validated tremor-classification model that distinguishes the three movement classes, replacing the scattered legacy model experiments currently in the backend, so there is no ambiguity about which model file is the current, supported one going forward.

**Why this priority**: Delivering the validated model is the core purpose of this migration. Today's backend mixes several experimental model versions and comparison scripts; consolidating to one supported artifact removes confusion about which model reflects the latest validated research.

**Independent Test**: After the data-preparation step has produced the combined dataset, run only the training step and confirm exactly one new classification model artifact exists in the designated backend location, and that files belonging to superseded experiments are no longer present — independent of whether live testing has been built yet.

**Acceptance Scenarios**:

1. **Given** the combined dataset exists, **When** training completes, **Then** a single trained classification model artifact, capable of distinguishing Non-Tremor, Parkinsonian Tremor, and Voluntary movement, is saved to the designated backend model location.
2. **Given** the new model artifact has been produced, **When** the model directory is inspected, **Then** scripts and artifacts belonging to superseded experiments are no longer present, leaving a single, clearly identifiable supported pipeline.
3. **Given** the new model has been trained, **When** its validated performance is compared against the results observed during research, **Then** the results are consistent with what was validated in research (no unexplained regression).

---

### User Story 3 - Live validation against real sensor data (Priority: P2)

As the engineer, I need to run the trained model against real-time sensor data and see, for each processed sample, the predicted movement class along with confidence, precision, and a per-class probability breakdown in one consistent reporting format, so I can confirm the model behaves correctly before it is relied upon for patient monitoring.

**Why this priority**: This is the validation gate before the new model can be trusted operationally. It depends on User Story 2 producing a trained model first, so it is sequenced after the core training capability, but it remains independently testable and valuable on its own as a confidence-building step.

**Independent Test**: With a trained model already available, start the live-evaluation capability against a real sensor feed and verify that each processed sample produces one correctly formatted result line, independent of any other in-progress work.

**Acceptance Scenarios**:

1. **Given** a trained model is available and a sensor feed is active, **When** the 1-second rolling buffer has filled and the sliding window advances (every ~100 ms), **Then** one result line is produced reporting the sample number, predicted class, confidence, the model's overall precision, and the probability for each of the three classes.
2. **Given** live evaluation is running, **When** results are reviewed, **Then** every line follows the exact same field order: Sample, Prediction, Confidence, Precision, Non-Tremor %, Tremor %, Voluntary %.
3. **Given** live evaluation is running, **When** the sensor feed is interrupted or sends malformed data, **Then** the evaluation does not crash and clearly indicates that a sample could not be classified rather than printing an incorrect or partial result line.

---

### Edge Cases

- What happens when a raw recording file within one of the three groups is malformed, empty, or too short to form even one analysis window?
- What happens when one of the three recording group folders is missing, empty, or inaccessible at data-preparation time?
- How does the system handle heavy class imbalance across the three groups (e.g., far fewer Voluntary recordings than the other two)?
- What happens when the live sensor feed disconnects mid-evaluation, or resumes after a gap?
- What happens when the live stream's actual sampling rate differs from the rate confirmed in firmware (drift, dropped samples), affecting the resample-to-66.67 Hz step?
- What happens when the rolling buffer is not yet full (warm-up) at the start of live evaluation, before the first 1-second window is available?
- What happens when the model produces a low-confidence or near-tied prediction across the three classes during live evaluation?
- What happens when the data-preparation step is re-run after the combined dataset file already exists — is it overwritten, versioned, or rejected?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST load and clean sensor recordings from all three labeled recording groups (Control/Non-Tremor, Parkinson's, Voluntary), using the preprocessing approach validated in the research notebook.
- **FR-002**: System MUST combine the three cleaned recording groups into a single dataset, with every sample correctly labeled by its originating class (Non-Tremor, Parkinsonian Tremor, or Voluntary).
- **FR-003**: System MUST persist the combined, preprocessed dataset to a fixed, known backend location *before* any model training begins, so the dataset can be inspected or reused independently of training.
- **FR-004**: System MUST derive the same descriptive and frequency-domain characteristics per analysis window that were validated in the research notebook, so the trained model receives input consistent with the original research findings.
- **FR-005**: System MUST train a single tremor-classification model using a fixed, pinned configuration (preprocessing parameters, feature set, and model hyperparameters) drawn from the research notebook's validated best result, capable of distinguishing the three classes (Non-Tremor, Parkinsonian Tremor, Voluntary movement). The pinned hyperparameters MUST be those discovered by running the notebook's search once during development; the training script MUST NOT perform any hyperparameter search (e.g., RandomizedSearchCV) at run time, so each training run is fast and produces a deterministic, reproducible model.
- **FR-006**: System MUST save the trained model as a single artifact directly inside `backend/ml_models/`, under a descriptive name (e.g., `lgbm_tremor_model.pkl`).
- **FR-007**: System MUST remove model training scripts and model artifacts belonging to superseded experiments from `backend/ml_models/`, including completely deleting the `backend/ml_models/models/` subdirectory and its obsolete contents (e.g., `rf_model_v3.pkl` and related files), leaving only the new combined-data preparation step, the new training step, and the single new model artifact.
- **FR-008**: System MUST make the new tremor-classification model the model used by the backend's existing live tremor-monitoring/inference capability, replacing the previously used model so that real-time monitoring immediately reflects the migrated pipeline.
- **FR-009**: System MUST update every part of the backend that previously loaded or referenced a superseded model (including `backend/inference/services.py` and any other consumer scripts) so it instead loads the new model from `backend/ml_models/lgbm_tremor_model.pkl` and uses its three-class output, and MUST remove outdated logic specific to the old models, leaving no part of the system pointing at a removed or replaced model.
- **FR-010**: System MUST provide a live-evaluation capability (`backend/test_AI_live.py`) that classifies real-time sensor input using the new trained model.
- **FR-011**: System MUST treat the ESP32 firmware's transmitted sampling rate as ground truth for the incoming live stream. This has been CONFIRMED from the firmware source (`firmware/include/config.h`, `firmware/src/task_scheduler.cpp`): the IMU samples at 100 Hz internally but the MQTT-transmitted rate — what the live test actually receives — is **~30 Hz** (`MQTT_PUBLISH_RATE_HZ = 33`, throttled to a 33 ms publish period). The system MUST resample each live window from ~30 Hz up to the 66.67 Hz / 1-second (~67-sample) shape the model expects before applying the same 0.5–20 Hz bandpass filter (applied AFTER resampling) and the same 66-feature extraction used in training (no feature scaler).
- **FR-012**: System MUST perform live evaluation using a sliding 1-second rolling buffer, emitting a new prediction every 100 ms (rather than waiting a full second per prediction), with the resample → filter → feature-extraction pipeline implemented in a fully vectorized manner to minimize per-prediction latency, because the output drives real-time hardware stabilization.
- **FR-013**: System MUST report each processed live sample using exactly these fields, in this order: Sample, Prediction, Confidence, Precision, Non-Tremor %, Tremor %, Voluntary %.
- **FR-014**: System MUST be able to regenerate the combined dataset and the trained model end-to-end from the three raw recording groups in a single, repeatable run, without manual intervention steps in between.
- **FR-015**: System MUST use the same three-class label scheme (Non-Tremor, Parkinsonian Tremor, Voluntary movement) consistently across the combined dataset, the trained model's outputs, the live-evaluation report, and the live monitoring capability.

### Key Entities *(include if feature involves data)*

- **Recording Group**: One of the three labeled sources of clinical sensor recordings (Control, Parkinson's, Voluntary) used as ground truth for training.
- **Combined Processed Dataset**: The merged, cleaned, feature-extracted collection of labeled analysis windows drawn from all three recording groups; each row carries its extracted signal characteristics, a class label, and a reference back to its originating recording.
- **Tremor Classification Model**: The single trained artifact that maps a processed sensor window to one of the three movement classes, along with a probability for each class; tracked alongside its validated performance (e.g., overall precision).
- **Live Evaluation Sample**: One prediction emitted during live testing (one per 100 ms sliding-window step); carries a sequence number, predicted class, confidence, the model's overall precision, and the probability breakdown across the three classes.
- **Live Rolling Buffer**: The 1-second window of the most recent live sensor samples, captured at the firmware's transmitted rate and resampled to the model's expected 66.67 Hz / ~66-sample shape before feature extraction.

## Assumptions

- **Live data source**: "Live sensor data" means the real-time glove sensor stream (the same source the backend's existing live inference script already consumes), not a static recorded file. The stream's sampling rate is taken as ground truth from the ESP32 firmware. **Confirmed during planning**: the transmitted (MQTT) rate is ~30 Hz, not the ~100 Hz originally suspected (the 100 Hz is the IMU's internal rate; only ~30 Hz is published). Each 1-second live window (~30 samples) is resampled up to the model's 66.67 Hz / ~67-sample shape per window.
- **No feature scaler**: The notebook's LightGBM pipeline does not use a feature scaler (StandardScaler is commented out), so neither training nor live evaluation applies one — unlike the prior Random Forest path. Any old scaler files/logic are removed as part of the consumer cleanup.
- **Precision field**: The "Precision" value reported on every live-evaluation line is the model's overall validated precision score (established once during training/evaluation), shown alongside each sample as a reliability reference — not a value computed fresh per individual sample, since true per-sample precision cannot be known without ground truth at evaluation time.
- **Training configuration**: Training uses a fixed, pinned configuration (preprocessing parameters, feature set, and model hyperparameters) validated as best-performing in the research notebook. The new training script does NOT run an open-ended hyperparameter search (RandomizedSearchCV) on each execution; it trains directly with the pinned values for speed and reproducibility.
- **Success bar**: The migrated pipeline is judged against parity with the results already validated in the research notebook, rather than against a new, separately defined performance target.
- **Deletion scope**: "Unrelated model files and scripts" refers only to contents of the backend's model directory itself; other backend directories that may contain older, separate experiments are out of scope for *deletion*. However, code elsewhere in the backend that *references* a removed/replaced model is in scope for *updating* (not deleting), so live monitoring keeps working against the new model.
- **Live model replacement**: This migration replaces the model currently powering the backend's live tremor-monitoring/inference path with the new model (confirmed decision). The migrated model and the live monitoring path both adopt the three-class scheme; any prior assumptions of a different class scheme in that path are updated as part of this work.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The combined dataset is available as a single, retrievable file containing labeled samples from all three recording groups, before any trained model exists — allowing it to be reused without re-running raw preprocessing.
- **SC-002**: The retrained model's validated performance across the three classes is consistent with the results observed in the original research (no unexplained regression), confirming the migration preserved validated behavior rather than introducing a different outcome.
- **SC-003**: During live evaluation, a new prediction is emitted approximately every 100 ms from the sliding 1-second window, and each prediction's full processing (resample → filter → feature extraction → classification) completes within that 100 ms step so no backlog of unprocessed windows ever builds up.
- **SC-004**: After migration, `backend/ml_models/` contains a single, clearly identifiable supported classification pipeline (the new data-prep step, training step, and one model artifact), the `backend/ml_models/models/` subdirectory no longer exists, and no leftover files from superseded experiments remain.
- **SC-005**: 100% of live-evaluation result lines contain all seven required fields, in the specified order, with no missing or mislabeled values.
- **SC-006**: After migration, the backend's existing live tremor-monitoring/inference capability runs against the new model and produces predictions across the three classes, with no part of the backend still referencing a removed or replaced model (or its scaler).
