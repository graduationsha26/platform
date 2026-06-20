# Tasks: ML/DL Data Preparation

**Input**: Design documents from `/specs/004-ml-data-prep/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Not explicitly requested in specification - test tasks omitted per template guidelines.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **ML data pipeline structure**: `backend/ml_data/` for data processing
- All tasks reference Python project structure from plan.md

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and dependency installation

- [X] T001 Add Python ML libraries to backend/requirements.txt: numpy>=1.24.0, pandas>=2.0.0, scipy>=1.10.0, scikit-learn>=1.3.0
- [X] T002 Create backend/ml_data/ directory structure: scripts/, utils/, processed/
- [X] T003 Create backend/ml_data/__init__.py as Python package marker
- [X] T004 Create backend/ml_data/scripts/__init__.py
- [X] T005 Create backend/ml_data/utils/__init__.py
- [X] T006 Create backend/ml_data/processed/.gitkeep to preserve empty directory
- [X] T007 Add backend/ml_data/processed/* to .gitignore (exclude output files from git)
- [X] T008 Create backend/ml_data/README.md with pipeline overview and usage instructions

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core utilities that all three user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T009 [P] Implement CSV loader with validation in backend/ml_data/utils/data_loader.py (load_dataset, validate_structure, drop_magnetometer_columns)
- [X] T010 [P] Implement sliding window utility in backend/ml_data/utils/windowing.py (create_windows function with configurable size and stride)
- [X] T011 [P] Implement statistical feature extractors in backend/ml_data/utils/feature_extractors.py (RMS, mean, std, skewness, kurtosis functions)
- [X] T012 [P] Implement data validators in backend/ml_data/utils/validators.py (check_no_nulls, check_shapes, check_class_distribution, check_normalization)
- [X] T013 [P] Implement majority voting label assignment in backend/ml_data/utils/windowing.py (assign_window_label function)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Dataset Preprocessing (Priority: P1) 🎯 MVP

**Goal**: Clean, normalize, and split raw dataset into train/test sets ready for windowing

**Independent Test**: Run 1_preprocess.py, verify outputs exist (train/test .npy files, normalization params JSON, preprocessing report), validate shapes and distributions per Scenario 1-4 in quickstart.md

### Implementation for User Story 1

- [X] T014 [US1] Create backend/ml_data/scripts/1_preprocess.py script skeleton with main() function and command-line argument parsing
- [X] T015 [US1] Implement load and validate step in 1_preprocess.py: load Dataset.csv, drop magnetometer columns (mX, mY, mZ), separate features from labels
- [X] T016 [US1] Implement null handling in 1_preprocess.py: detect nulls per column, drop rows if <5% affected, impute with median if >=5%
- [X] T017 [US1] Implement stratified train/test split in 1_preprocess.py: 80/20 split using sklearn.model_selection.train_test_split with stratify=y and random_state=42
- [X] T018 [US1] Implement normalization in 1_preprocess.py: fit StandardScaler on train set only, transform both train and test sets (z-score per axis)
- [X] T019 [US1] Implement data validation checks in 1_preprocess.py: verify no NaN/Inf, check shapes, validate class distribution (±2% tolerance)
- [X] T020 [US1] Implement file output in 1_preprocess.py: save train_normalized.npy, test_normalized.npy, train_labels.npy, test_labels.npy using np.save
- [X] T021 [US1] Implement normalization parameters export in 1_preprocess.py: save mean and std per axis to normalization_params.json with metadata
- [X] T022 [US1] Implement preprocessing report generation in 1_preprocess.py: create preprocessing_report.txt with sample counts, class distributions, null handling summary
- [X] T023 [US1] Add logging and progress indicators to 1_preprocess.py for all major steps
- [X] T024 [US1] Add error handling in 1_preprocess.py for file not found, invalid data, and validation failures

**Checkpoint**: At this point, User Story 1 should be fully functional - run script and verify all outputs created correctly

---

## Phase 4: User Story 2 - Feature Engineering (Priority: P2)

**Goal**: Extract statistical features from time windows for traditional ML models (Random Forest, SVM, XGBoost)

**Independent Test**: Run 2_feature_engineering.py, verify train_features.csv and test_features.csv created with 30 features + label, validate feature matrix dimensions and distributions per Scenario 5 in quickstart.md

### Implementation for User Story 2

- [X] T025 [US2] Create backend/ml_data/scripts/2_feature_engineering.py script skeleton with main() function
- [X] T026 [US2] Implement data loading in 2_feature_engineering.py: load train/test_normalized.npy and train/test_labels.npy from Story 1 outputs
- [X] T027 [US2] Implement sliding window segmentation in 2_feature_engineering.py: create 100-sample windows with 50-sample stride (50% overlap) using windowing utility
- [X] T028 [US2] Implement feature extraction loop in 2_feature_engineering.py: for each window, extract 5 features per axis (RMS, mean, std, skewness, kurtosis) → 30 features total
- [X] T029 [US2] Implement window label assignment in 2_feature_engineering.py: assign label to each window using majority voting (dominant class in window)
- [X] T030 [US2] Implement feature matrix assembly in 2_feature_engineering.py: create pandas DataFrame with 30 feature columns + 1 label column, proper column names (RMS_aX, mean_aX, etc.)
- [X] T031 [US2] Implement validation checks in 2_feature_engineering.py: verify no NaN/Inf in features, check expected dimensions (~447 train windows, ~111 test windows)
- [X] T032 [US2] Implement CSV export in 2_feature_engineering.py: save train_features.csv and test_features.csv with header row
- [X] T033 [US2] Add logging and progress indicators to 2_feature_engineering.py (window processing, feature extraction progress)
- [X] T034 [US2] Add error handling in 2_feature_engineering.py for missing input files, invalid window sizes, feature extraction failures

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently - feature matrices ready for ML model training

---

## Phase 5: User Story 3 - Sequence Preparation (Priority: P3)

**Goal**: Create fixed-length sequence tensors for deep learning models (LSTM, CNN, hybrid)

**Independent Test**: Run 3_sequence_preparation.py, verify train/test_sequences.npy and labels created with shape (N, 128, 6), validate tensor dimensions and compatibility per Scenario 6 in quickstart.md

### Implementation for User Story 3

- [X] T035 [US3] Create backend/ml_data/scripts/3_sequence_preparation.py script skeleton with main() function
- [X] T036 [US3] Implement data loading in 3_sequence_preparation.py: load train/test_normalized.npy and train/test_labels.npy from Story 1 outputs
- [X] T037 [US3] Implement sliding window sequencing in 3_sequence_preparation.py: create 128-sample sequences with 64-sample stride (50% overlap)
- [X] T038 [US3] Implement 3D tensor reshaping in 3_sequence_preparation.py: reshape windows to (num_windows, 128, 6) format suitable for LSTM/CNN input
- [X] T039 [US3] Implement sequence label assignment in 3_sequence_preparation.py: assign label to each sequence using majority voting
- [X] T040 [US3] Implement edge padding logic in 3_sequence_preparation.py: zero-pad incomplete sequences at dataset boundaries, flag padded sequences
- [X] T041 [US3] Implement validation checks in 3_sequence_preparation.py: verify 3D shape (N, 128, 6), check no NaN/Inf, validate label count matches sequence count
- [X] T042 [US3] Implement numpy export in 3_sequence_preparation.py: save train_sequences.npy, test_sequences.npy, train_seq_labels.npy, test_seq_labels.npy
- [X] T043 [US3] Add logging and progress indicators to 3_sequence_preparation.py (sequence processing, tensor reshaping)
- [X] T044 [US3] Add error handling in 3_sequence_preparation.py for missing inputs, invalid sequence lengths, tensor shape mismatches

**Checkpoint**: All user stories should now be independently functional - three different data formats ready for ML/DL experiments

---

## Phase 6: Integration & Polish

**Purpose**: Master script, documentation, and cross-cutting improvements

- [X] T045 Create backend/ml_data/scripts/run_all.py master script that runs all 3 stages sequentially with single command
- [X] T046 Implement stage orchestration in run_all.py: import and execute 1_preprocess.py, 2_feature_engineering.py, 3_sequence_preparation.py in order
- [X] T047 Add error handling and early exit in run_all.py: if any stage fails, report error and stop (don't continue to next stage)
- [X] T048 Add timing and summary report in run_all.py: log elapsed time per stage, total time, output file summary
- [X] T049 [P] Add comprehensive docstrings to all utility functions in backend/ml_data/utils/ (NumPy documentation format)
- [X] T050 [P] Add comprehensive docstrings to all main scripts in backend/ml_data/scripts/ (purpose, usage, outputs)
- [X] T051 [P] Update backend/ml_data/README.md with detailed usage instructions, quickstart examples, troubleshooting tips
- [X] T052 [P] Add input validation examples to backend/ml_data/README.md (verify Dataset.csv exists, check dependencies installed)
- [X] T053 Run all validation scenarios from quickstart.md: Scenarios 1-7 (data integrity, class distribution, normalization, reproducibility, compatibility)
- [X] T054 Verify pipeline performance meets SC-003: full pipeline completes in < 5 minutes on standard laptop

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion (T001-T008) - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion (T009-T013)
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Integration & Polish (Phase 6)**: Depends on all three user stories being complete (T014-T044)

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Uses Story 1 outputs but independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Uses Story 1 outputs but independently testable

### Within Each User Story

- Script skeleton before implementation
- Data loading before processing
- Processing before validation
- Validation before output
- Core implementation before logging/error handling
- Story complete before moving to next priority

### Parallel Opportunities

- **Phase 1 Setup**: T001-T008 can all run in parallel (independent file/directory creation)
- **Phase 2 Foundational**: T009-T013 can all run in parallel (different utility files, no dependencies)
- **Once Foundational completes**: User Stories 1, 2, 3 can be worked on in parallel by different developers
  - Story 2 and 3 both read Story 1 outputs, but don't modify them
  - Each story writes to different files, no conflicts
- **Phase 6 Polish**: T049-T052 documentation tasks can run in parallel

---

## Parallel Example: Phase 2 Foundational

```bash
# Launch all foundational utilities together:
Task: "Implement CSV loader in backend/ml_data/utils/data_loader.py"
Task: "Implement sliding window utility in backend/ml_data/utils/windowing.py"
Task: "Implement statistical feature extractors in backend/ml_data/utils/feature_extractors.py"
Task: "Implement data validators in backend/ml_data/utils/validators.py"
Task: "Implement majority voting in backend/ml_data/utils/windowing.py"
```

## Parallel Example: User Story 1

```bash
# After T014 skeleton created, these can run in parallel if using placeholders:
# (In practice, T015-T024 are sequential since they build on each other)
# But logging (T023) and error handling (T024) can be added in parallel after core logic done
```

## Parallel Example: Phase 6 Documentation

```bash
# Launch all documentation tasks together:
Task: "Add docstrings to all utility functions in backend/ml_data/utils/"
Task: "Add docstrings to all main scripts in backend/ml_data/scripts/"
Task: "Update backend/ml_data/README.md with detailed usage"
Task: "Add input validation examples to backend/ml_data/README.md"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T008) - ~10 minutes
2. Complete Phase 2: Foundational (T009-T013) - ~30 minutes, CRITICAL
3. Complete Phase 3: User Story 1 (T014-T024) - ~1.5 hours
4. **STOP and VALIDATE**: Run 1_preprocess.py, verify all outputs, test with Scenarios 1-4 from quickstart.md
5. Checkpoint: Preprocessed data ready for any ML/DL work

### Incremental Delivery

1. Complete Setup + Foundational (T001-T013) → Foundation ready
2. Add User Story 1 (T014-T024) → Test with quickstart Scenarios 1-4 → **MVP Complete!** (preprocessed data)
3. Add User Story 2 (T025-T034) → Test with quickstart Scenario 5 → Feature matrices for ML
4. Add User Story 3 (T035-T044) → Test with quickstart Scenario 6 → Sequence tensors for DL
5. Add Integration & Polish (T045-T054) → Master script, documentation, full validation
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (T001-T013)
2. Once Foundational is done:
   - Developer A: User Story 1 (T014-T024) - Preprocessing
   - Developer B: User Story 2 (T025-T034) - Feature Engineering (waits for US1 outputs)
   - Developer C: User Story 3 (T035-T044) - Sequence Preparation (waits for US1 outputs)
3. Developers B and C start after A completes Story 1, or work in parallel with temporary test data
4. Developer D: Integration & Polish (T045-T054) after all stories done

---

## Notes

- [P] tasks = different files, no dependencies, safe to run in parallel
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Story 2 and 3 both depend on Story 1 outputs, but don't modify them - can run in parallel once Story 1 complete
- Use `python backend/ml_data/scripts/[script_name].py` to run individual stages
- Use `python backend/ml_data/scripts/run_all.py` to run complete pipeline
- Commit after each completed story for incremental progress tracking
- Stop at any checkpoint to validate story independently
- Success criteria validation:
  - SC-001: Data integrity (Scenario 1) - no leakage between train/test
  - SC-002: Class distribution (Scenario 2) - within ±2% tolerance
  - SC-003: Processing time - complete pipeline < 5 minutes (T054)
  - SC-004: Tensor validation (Scenario 6) - 100% pass shape checks
  - SC-005: Reproducibility (Scenario 4) - identical outputs with same seed
  - SC-006: ML/DL compatibility (Scenarios 5, 6) - load into scikit-learn and TensorFlow
  - SC-007: Documentation complete (T051-T052) - comprehensive README

---

## Task Summary

**Total Tasks**: 54

**By Phase**:
- Phase 1 (Setup): 8 tasks (T001-T008)
- Phase 2 (Foundational): 5 tasks (T009-T013) - **BLOCKING**
- Phase 3 (User Story 1 - P1 MVP): 11 tasks (T014-T024)
- Phase 4 (User Story 2 - P2): 10 tasks (T025-T034)
- Phase 5 (User Story 3 - P3): 10 tasks (T035-T044)
- Phase 6 (Integration & Polish): 10 tasks (T045-T054)

**By User Story**:
- User Story 1 (Preprocessing): 11 tasks
- User Story 2 (Feature Engineering): 10 tasks
- User Story 3 (Sequence Preparation): 10 tasks

**Parallelizable Tasks**: 13 tasks marked with [P]
- Setup phase: 8 parallel opportunities
- Foundational phase: 5 parallel opportunities
- Polish phase: 4 parallel documentation tasks

**Estimated Time**:
- MVP (Setup + Foundational + US1): ~2.5 hours
- Full Pipeline (All 54 tasks): ~6-8 hours for single developer
- With 3 developers (parallel stories): ~4-5 hours
