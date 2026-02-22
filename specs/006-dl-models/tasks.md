# Tasks: Deep Learning Models Training

**Input**: Design documents from `specs/006-dl-models/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, quickstart.md ✓

**Tests**: Not explicitly requested in specification - test tasks omitted per guidelines.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Path Conventions

This is a backend-only feature in `backend/dl_models/` (monorepo structure per constitution).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and directory structure for deep learning models training

- [X] T001 Create `backend/dl_models/` directory structure with subdirectories: `scripts/`, `scripts/utils/`, `models/`
- [X] T002 [P] Create `backend/dl_models/__init__.py` package initializer
- [X] T003 [P] Create `backend/dl_models/scripts/__init__.py` package initializer
- [X] T004 [P] Create `backend/dl_models/scripts/utils/__init__.py` package initializer
- [X] T005 [P] Create `.gitkeep` file in `backend/dl_models/models/` to preserve directory in git
- [X] T006 [P] Update `.gitignore` to exclude trained model files: add `backend/dl_models/models/*.h5`, `backend/dl_models/models/*.keras`, `backend/dl_models/models/*.json`, `backend/dl_models/models/*.txt`
- [X] T007 [P] Add exception to `.gitignore` to keep .gitkeep file: add `!backend/dl_models/models/.gitkeep`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core utility modules that BOTH user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T008 [P] Create `backend/dl_models/scripts/utils/model_io.py` with function `load_sequence_data(train_path, test_path)` to load .npy sequence files and return (X_train, y_train, X_test, y_test)
- [X] T009 [P] Add function `save_model(model, metadata, output_dir, model_name)` to `model_io.py` for saving .h5 model + .json metadata
- [X] T010 [P] Add function `load_model(model_path, metadata_path)` to `model_io.py` for loading .h5 model + .json metadata
- [X] T011 [P] Add function `create_metadata(model_type, architecture_summary, hyperparameters, performance_metrics, training_history, training_info)` to `model_io.py` for generating metadata dictionary
- [X] T012 [P] Create `backend/dl_models/scripts/utils/evaluation.py` with function `evaluate_model(model, X_test, y_test)` that returns dict with accuracy, precision, recall, f1_score, confusion_matrix, meets_threshold (≥95%)
- [X] T013 [P] Add function `format_metrics_string(metrics)` to `evaluation.py` for logging-friendly metrics formatting
- [X] T014 [P] Create `backend/dl_models/scripts/utils/architectures.py` with function `build_lstm_model(input_shape, lstm_units_1, lstm_units_2, dropout_rate, random_state)` returning compiled LSTM model
- [X] T015 [P] Add function `build_cnn_1d_model(input_shape, filters, kernel_size, pool_size, dense_units, dropout_rate, random_state)` to `architectures.py` returning compiled 1D-CNN model

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - LSTM Model Training (Priority: P1-MVP) 🎯 MVP

**Goal**: Train LSTM model (2 layers: 64/32 units, dropout 0.3) on sequence data, achieve ≥95% accuracy, export as .h5 + .json

**Independent Test**: Run `python backend/dl_models/scripts/train_lstm.py`, verify test accuracy ≥95%, confirm `lstm_model.h5` and `lstm_model.json` created in `backend/dl_models/models/`, load model and perform inference

### Implementation for User Story 1

- [X] T016 [US1] Create `backend/dl_models/scripts/train_lstm.py` with main() function, argument parser (--input-dir, --output-dir, --random-state), and logging configuration
- [X] T017 [US1] Add data loading to `train_lstm.py`: load train/test sequences from `backend/ml_data/processed/` (files: `train_sequences.npy`, `test_sequences.npy`, `train_seq_labels.npy`, `test_seq_labels.npy`), validate shapes (N, timesteps, 6 features)
- [X] T018 [US1] Add data validation function to `train_lstm.py`: check for NaN/Inf values, verify binary labels (0 or 1), confirm 6 features (aX, aY, aZ, gX, gY, gZ)
- [X] T019 [US1] Add train/validation split to `train_lstm.py`: split training data 80/20 using `train_test_split` with `stratify=y_train`, `random_state=42`
- [X] T020 [US1] Add LSTM model building to `train_lstm.py`: call `build_lstm_model()` with input_shape=(timesteps, 6), lstm_units_1=64, lstm_units_2=32, dropout_rate=0.3
- [X] T021 [US1] Add early stopping setup to `train_lstm.py`: create `EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True, mode='min')` callback
- [X] T022 [US1] Add model training to `train_lstm.py`: call `model.fit()` with train/validation data, batch_size=32, epochs=100, callbacks=[early_stopping], verbose=2
- [X] T023 [US1] Add test evaluation to `train_lstm.py`: call `evaluate_model()` on test set, log all metrics (accuracy, precision, recall, F1, confusion matrix)
- [X] T024 [US1] Add threshold check to `train_lstm.py`: log `[OK]` if accuracy ≥95%, log `[WARNING]` if below threshold but continue (don't exit with error)
- [X] T025 [US1] Add metadata assembly to `train_lstm.py`: call `create_metadata()` with model_type="LSTM", architecture_summary=`model.summary()`, hyperparameters dict, performance metrics, training history from `model.history`, training_info dict
- [X] T026 [US1] Add model saving to `train_lstm.py`: call `save_model()` to export `backend/dl_models/models/lstm_model.h5` and `lstm_model.json`
- [X] T027 [US1] Add model loading validation to `train_lstm.py`: reload saved model, test prediction on 5 sample sequences, log predictions
- [X] T028 [US1] Add reproducibility setup to `train_lstm.py`: set `tf.random.set_seed(42)`, `np.random.seed(42)`, `random.seed(42)` at script start
- [X] T029 [US1] Add TensorFlow version and GPU detection to `train_lstm.py`: log TensorFlow version, log GPU availability using `tf.config.list_physical_devices('GPU')`

**Checkpoint**: At this point, User Story 1 should be fully functional - LSTM model can be trained, evaluated, and exported

---

## Phase 4: User Story 2 - 1D-CNN Model Training (Priority: P2)

**Goal**: Train 1D-CNN model (3 Conv1D layers + BatchNorm + MaxPool) on sequence data, achieve ≥95% accuracy, export as .h5 + .json

**Independent Test**: Run `python backend/dl_models/scripts/train_cnn_1d.py`, verify test accuracy ≥95%, confirm `cnn_1d_model.h5` and `cnn_1d_model.json` created, compare against LSTM model

### Implementation for User Story 2

- [X] T030 [US2] Create `backend/dl_models/scripts/train_cnn_1d.py` with main() function, argument parser (--input-dir, --output-dir, --random-state), and logging configuration
- [X] T031 [US2] Add data loading to `train_cnn_1d.py`: load train/test sequences from `backend/ml_data/processed/` (files: `train_sequences.npy`, `test_sequences.npy`, `train_seq_labels.npy`, `test_seq_labels.npy`), validate shapes (N, timesteps, 6 features)
- [X] T032 [US2] Add data validation function to `train_cnn_1d.py`: check for NaN/Inf values, verify binary labels (0 or 1), confirm 6 features
- [X] T033 [US2] Add train/validation split to `train_cnn_1d.py`: split training data 80/20 using `train_test_split` with `stratify=y_train`, `random_state=42`
- [X] T034 [US2] Add 1D-CNN model building to `train_cnn_1d.py`: call `build_cnn_1d_model()` with input_shape=(timesteps, 6), filters=[64, 128, 256], kernel_size=3, pool_size=2, dense_units=128, dropout_rate=0.5
- [X] T035 [US2] Add early stopping setup to `train_cnn_1d.py`: create `EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True, mode='min')` callback
- [X] T036 [US2] Add model training to `train_cnn_1d.py`: call `model.fit()` with train/validation data, batch_size=32, epochs=100, callbacks=[early_stopping], verbose=2
- [X] T037 [US2] Add test evaluation to `train_cnn_1d.py`: call `evaluate_model()` on test set, log all metrics (accuracy, precision, recall, F1, confusion matrix)
- [X] T038 [US2] Add threshold check to `train_cnn_1d.py`: log `[OK]` if accuracy ≥95%, log `[WARNING]` if below threshold but continue
- [X] T039 [US2] Add metadata assembly to `train_cnn_1d.py`: call `create_metadata()` with model_type="CNN1D", architecture_summary, hyperparameters dict, performance metrics, training history, training_info dict
- [X] T040 [US2] Add model saving to `train_cnn_1d.py`: call `save_model()` to export `backend/dl_models/models/cnn_1d_model.h5` and `cnn_1d_model.json`
- [X] T041 [US2] Add model loading validation to `train_cnn_1d.py`: reload saved model, test prediction on 5 sample sequences, log predictions
- [X] T042 [US2] Add reproducibility setup to `train_cnn_1d.py`: set `tf.random.set_seed(42)`, `np.random.seed(42)`, `random.seed(42)` at script start
- [X] T043 [US2] Add TensorFlow version and GPU detection to `train_cnn_1d.py`: log TensorFlow version, log GPU availability

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently - both models trained and exported

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Model comparison, documentation, and validation across both user stories

- [X] T044 [P] Create `backend/dl_models/scripts/compare_models.py` with main() function and argument parser (--models-dir)
- [X] T045 Add function `load_model_metadata(models_dir, model_name)` to `compare_models.py` for loading .json metadata files
- [X] T046 Add function `format_comparison_report(lstm_metadata, cnn_metadata)` to `compare_models.py` that generates side-by-side comparison table with accuracy, precision, recall, F1, training time, and deployment recommendation
- [X] T047 Add metadata loading to `compare_models.py`: load `lstm_model.json` and `cnn_1d_model.json`, handle FileNotFoundError if models not trained yet
- [X] T048 Add report generation to `compare_models.py`: call `format_comparison_report()`, print to console, save to `backend/dl_models/models/comparison_report.txt`
- [X] T049 Add best model identification to `compare_models.py`: compare accuracy values, determine best model, include in recommendation text
- [X] T050 [P] Create `backend/dl_models/README.md` with overview section describing LSTM and 1D-CNN models, accuracy targets, and export formats
- [X] T051 [P] Add Quick Start section to README: commands to train LSTM (`python backend/dl_models/scripts/train_lstm.py`), train 1D-CNN, and compare models
- [X] T052 [P] Add Usage Examples section to README: custom paths (--input-dir, --output-dir), loading trained models in Python (`tf.keras.models.load_model()`), making predictions on new sequences
- [X] T053 [P] Add Model Architecture Details section to README: LSTM layer configuration (64→32 units, dropout 0.3), 1D-CNN layer configuration (Conv1D 64→128→256, BatchNorm, MaxPool), hyperparameters (batch_size=32, lr=0.001, patience=10)
- [X] T054 [P] Add Troubleshooting section to README: TensorFlow not installed, sequence data not found (run Feature 004 first), training too slow (GPU suggestions), out of memory (reduce batch size), accuracy below 95% (analysis steps)
- [X] T055 [P] Add Performance Benchmarks section to README: table showing LSTM vs 1D-CNN training time, test accuracy, inference time, model size
- [X] T056 [P] Add Next Steps section to README: links to Feature 007 (model serving), Feature 008 (ensemble methods), Feature 009 (explainability)
- [X] T057 Validate Scenario 1 from `quickstart.md`: run `python backend/dl_models/scripts/train_lstm.py`, verify accuracy ≥95%, check file sizes (~50-100 MB for .h5, ~10 KB for .json)
- [X] T058 Validate Scenario 2 from `quickstart.md`: run `python backend/dl_models/scripts/train_cnn_1d.py`, verify accuracy ≥95%, check file sizes (~150-300 MB for .h5, ~12 KB for .json)
- [X] T059 Validate Scenario 3 from `quickstart.md`: run `python backend/dl_models/scripts/compare_models.py`, verify comparison report generated with all metrics and recommendation
- [X] T060 Validate model export format from Scenario 8: verify .h5 files exist (not .keras or SavedModel directories), test loading with `tf.keras.models.load_model()`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion (T001-T007) - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational phase completion (T008-T015)
- **User Story 2 (Phase 4)**: Depends on Foundational phase completion (T008-T015) - Can run in parallel with User Story 1 if desired
- **Polish (Phase 5)**: Depends on both User Story 1 AND User Story 2 completion (for comparison script to work)

### User Story Dependencies

- **User Story 1 (P1-MVP)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - No dependencies on User Story 1 (both are independent)

**Key Independence**: User Stories 1 and 2 are completely independent:
- They read the same input data (Feature 004 outputs)
- They write to different output files (`lstm_model.*` vs `cnn_1d_model.*`)
- They use the same utility modules but don't depend on each other's outputs
- Either story can be completed first, or both can be developed in parallel

### Within Each User Story

**User Story 1 (LSTM)**:
- T016 (script creation) MUST come first
- T017-T019 (data loading and validation) before T020 (model building)
- T020 (model building) before T021-T022 (training)
- T022 (training) before T023-T024 (evaluation)
- T023-T024 (evaluation) before T025-T026 (metadata and saving)
- T027-T029 (validation and reproducibility) can run after T026

**User Story 2 (1D-CNN)** - same structure as User Story 1

### Parallel Opportunities

**Setup Phase (Phase 1)**:
- T002, T003, T004, T005, T006, T007 can all run in parallel after T001 completes

**Foundational Phase (Phase 2)**:
- All tasks (T008-T015) can run in parallel - they create different files

**User Stories (Phase 3-4)**:
- User Story 1 (T016-T029) and User Story 2 (T030-T043) can run completely in parallel by different developers

**Polish Phase (Phase 5)**:
- T044-T049 (comparison script) MUST run after both user stories complete
- T050-T056 (README sections) can run in parallel with each other
- T057-T060 (validation scenarios) MUST run after both user stories complete

---

## Parallel Example: User Story 1

```bash
# Foundational phase (all utilities in parallel):
Task: "Create model_io.py with load_sequence_data()"
Task: "Create evaluation.py with evaluate_model()"
Task: "Create architectures.py with build_lstm_model()"

# User Story 1 can run in parallel with User Story 2:
Developer A: Train LSTM model (T016-T029)
Developer B: Train 1D-CNN model (T030-T043)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T007)
2. Complete Phase 2: Foundational (T008-T015) - **CRITICAL** blocks all stories
3. Complete Phase 3: User Story 1 - LSTM Training (T016-T029)
4. **STOP and VALIDATE**: Run `python backend/dl_models/scripts/train_lstm.py`, verify accuracy ≥95%, test model loading
5. Deploy/demo if ready - **You now have a working MVP!**

### Incremental Delivery

1. Complete Setup (Phase 1) → Directory structure ready
2. Complete Foundational (Phase 2) → Utilities ready for both stories
3. Add User Story 1 (Phase 3) → Test independently with quickstart Scenario 1 → **Deploy/Demo MVP (LSTM model)**
4. Add User Story 2 (Phase 4) → Test independently with quickstart Scenario 2 → **Deploy/Demo (both models available)**
5. Add Polish (Phase 5) → Comparison report and full documentation → **Deploy/Demo (complete feature)**

Each increment adds value without breaking previous increments.

### Parallel Team Strategy

With two developers:

1. Team completes Setup + Foundational together (T001-T015)
2. Once Foundational is done:
   - **Developer A**: User Story 1 (T016-T029) - LSTM training
   - **Developer B**: User Story 2 (T030-T043) - 1D-CNN training
3. Team completes Polish together (T044-T060) after both stories done

**Time Savings**: With parallel development, both models can be implemented simultaneously instead of sequentially.

---

## Task Count Summary

- **Phase 1 (Setup)**: 7 tasks
- **Phase 2 (Foundational)**: 8 tasks
- **Phase 3 (User Story 1 - LSTM)**: 14 tasks
- **Phase 4 (User Story 2 - 1D-CNN)**: 14 tasks
- **Phase 5 (Polish)**: 17 tasks

**Total**: 60 tasks

**Parallel Opportunities**:
- Setup: 6 tasks can run in parallel (after T001)
- Foundational: 8 tasks can run in parallel
- User Stories: 28 tasks can run in parallel (14 from US1 + 14 from US2)
- Polish: 6 README tasks can run in parallel

**MVP Scope**: 29 tasks (Setup + Foundational + User Story 1)

---

## Notes

- **[P]** tasks = different files, no dependencies, can run in parallel
- **[Story]** label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Foundational phase is CRITICAL - blocks all user stories until complete
- User Stories 1 and 2 are fully independent - can be developed in any order or in parallel
- Tests not included per specification guidelines (not explicitly requested)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Feature 004 (ML/DL Data Preparation) must be complete before this feature - ✅ VERIFIED: All sequence data files exist in `backend/ml_data/processed/` (train_sequences.npy, test_sequences.npy, train_seq_labels.npy, test_seq_labels.npy)
