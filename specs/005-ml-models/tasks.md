# Tasks: Machine Learning Models Training

**Input**: Design documents from `/specs/005-ml-models/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Not explicitly requested in specification - test tasks omitted per template guidelines.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Path Conventions

- **ML pipeline structure**: `backend/ml_models/` for model training scripts
- All tasks reference Python project structure from plan.md

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, directory structure, and dependency management

- [X] T001 Create backend/ml_models/ directory structure: scripts/, scripts/utils/, models/
- [X] T002 Create backend/ml_models/__init__.py as Python package marker
- [X] T003 Create backend/ml_models/scripts/__init__.py
- [X] T004 Create backend/ml_models/scripts/utils/__init__.py
- [X] T005 Create backend/ml_models/models/.gitkeep to preserve empty directory
- [X] T006 Add backend/ml_models/models/*.pkl to .gitignore (exclude model files from git)
- [X] T007 Add backend/ml_models/models/*.json to .gitignore (exclude metadata from git if desired) OR keep .json for documentation
- [X] T008 Verify scikit-learn ≥1.3.0 in backend/requirements.txt (should be present from Feature 004)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core utilities that both Random Forest and SVM training scripts depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T009 [P] Implement model I/O utilities in backend/ml_models/scripts/utils/model_io.py (save_model, load_model functions using joblib and json)
- [X] T010 [P] Implement evaluation utilities in backend/ml_models/scripts/utils/evaluation.py (evaluate_model function returning accuracy, precision, recall, F1, confusion matrix)
- [X] T011 [P] Implement data loading utility in backend/ml_models/scripts/utils/model_io.py (load_feature_data function to read train/test_features.csv)
- [X] T012 [P] Implement metadata generation utility in backend/ml_models/scripts/utils/model_io.py (create_metadata function assembling hyperparameters, metrics, training info)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Random Forest Classifier Training (Priority: P1) 🎯 MVP

**Goal**: Train Random Forest classifier with GridSearchCV, achieve ≥95% accuracy, export .pkl and .json files

**Independent Test**: Run `python backend/ml_models/scripts/train_random_forest.py`, verify random_forest.pkl and random_forest.json created, model achieves ≥95% accuracy, can be loaded for predictions

### Implementation for User Story 1

- [X] T013 [US1] Create backend/ml_models/scripts/train_random_forest.py script skeleton with main() function and command-line argument parsing
- [X] T014 [US1] Implement data loading step in train_random_forest.py: load train_features.csv and test_features.csv from backend/ml_data/processed/, split into X_train, y_train, X_test, y_test
- [X] T015 [US1] Implement input validation in train_random_forest.py: verify files exist, correct shape (30 features), no NaN/Inf, labels are binary (0 or 1)
- [X] T016 [US1] Define hyperparameter search space in train_random_forest.py: n_estimators=[50, 100, 200, 300], max_depth=[10, 20, 30, None]
- [X] T017 [US1] Implement GridSearchCV setup in train_random_forest.py: RandomForestClassifier base estimator, param_grid, cv=StratifiedKFold(5, random_state=42), scoring='accuracy', n_jobs=-1
- [X] T018 [US1] Implement GridSearchCV execution in train_random_forest.py: fit on X_train, y_train, log progress for each parameter combination tested
- [X] T019 [US1] Extract best model and parameters in train_random_forest.py: best_estimator_, best_params_, best_score_ from GridSearchCV
- [X] T020 [US1] Implement test set evaluation in train_random_forest.py: predict on X_test, compute metrics using evaluation utility (accuracy, precision, recall, F1, confusion matrix)
- [X] T021 [US1] Implement success threshold check in train_random_forest.py: if accuracy ≥0.95 set meets_threshold=true, else log warning and set false
- [X] T022 [US1] Assemble model metadata in train_random_forest.py: hyperparameters, performance_metrics (accuracy, precision, recall, f1_score, confusion_matrix, meets_threshold), cross_validation (cv_scores, cv_mean, cv_std), training_info (timestamp, training_time_seconds, sklearn_version, python_version, random_state=42)
- [X] T023 [US1] Implement model export in train_random_forest.py: save model to backend/ml_models/models/random_forest.pkl using joblib, save metadata to random_forest.json using json module
- [X] T024 [US1] Implement model loading validation in train_random_forest.py: reload saved model, test prediction on small sample to verify it works
- [X] T025 [US1] Add comprehensive logging to train_random_forest.py: log data loading, GridSearchCV progress, best params, test metrics, file paths, training time
- [X] T026 [US1] Add error handling in train_random_forest.py: catch missing files, validation failures, GridSearchCV errors, provide clear error messages with guidance

**Checkpoint**: At this point, User Story 1 should be fully functional - Random Forest model trained, evaluated, and exported

---

## Phase 4: User Story 2 - SVM Classifier Training (Priority: P2)

**Goal**: Train SVM classifier with RBF kernel, achieve ≥95% accuracy, enable model comparison

**Independent Test**: Run `python backend/ml_models/scripts/train_svm.py`, verify svm_rbf.pkl and svm_rbf.json created, model achieves ≥95% accuracy, can run independently of User Story 1

### Implementation for User Story 2

- [X] T027 [US2] Create backend/ml_models/scripts/train_svm.py script skeleton with main() function and command-line argument parsing
- [X] T028 [US2] Implement data loading step in train_svm.py: load train_features.csv and test_features.csv, split into X_train, y_train, X_test, y_test (reuse data loading utility)
- [X] T029 [US2] Implement input validation in train_svm.py: verify files exist, correct shape, no NaN/Inf, labels are binary (same validation as US1)
- [X] T030 [US2] Define hyperparameter search space in train_svm.py: C=[0.1, 1, 10, 100], gamma=[0.001, 0.01, 0.1, 1], kernel='rbf' (fixed)
- [X] T031 [US2] Implement GridSearchCV setup in train_svm.py: SVC base estimator with kernel='rbf', param_grid, cv=StratifiedKFold(5, random_state=42), scoring='accuracy', n_jobs=-1
- [X] T032 [US2] Implement GridSearchCV execution in train_svm.py: fit on X_train, y_train, log progress for each parameter combination tested
- [X] T033 [US2] Extract best model and parameters in train_svm.py: best_estimator_, best_params_, best_score_ from GridSearchCV
- [X] T034 [US2] Implement test set evaluation in train_svm.py: predict on X_test, compute metrics using evaluation utility
- [X] T035 [US2] Implement success threshold check in train_svm.py: if accuracy ≥0.95 set meets_threshold=true, else log warning
- [X] T036 [US2] Assemble model metadata in train_svm.py: hyperparameters (C, gamma, kernel='rbf'), performance_metrics, cross_validation, training_info
- [X] T037 [US2] Implement model export in train_svm.py: save model to backend/ml_models/models/svm_rbf.pkl, save metadata to svm_rbf.json
- [X] T038 [US2] Implement model loading validation in train_svm.py: reload saved model, test prediction to verify it works
- [X] T039 [US2] Add comprehensive logging to train_svm.py: log data loading, GridSearchCV progress, best params, test metrics, file paths
- [X] T040 [US2] Add error handling in train_svm.py: catch errors, provide clear error messages

**Checkpoint**: At this point, User Story 2 should be fully functional - SVM model trained, evaluated, and exported independently

---

## Phase 5: Integration & Polish

**Purpose**: Model comparison, documentation, and comprehensive validation

- [X] T041 Create backend/ml_models/scripts/compare_models.py script to generate model comparison report (FR-012)
- [X] T042 Implement model loading in compare_models.py: load both random_forest.json and svm_rbf.json metadata files
- [X] T043 Implement comparison logic in compare_models.py: extract accuracy, precision, recall, F1-score, training time for both models
- [X] T044 Implement best model identification in compare_models.py: determine which model has higher accuracy, provide recommendation
- [X] T045 Implement report generation in compare_models.py: create comparison_report.txt with side-by-side metrics table, save to backend/ml_models/models/
- [X] T046 Add error handling in compare_models.py: check both model files exist, provide clear error if one or both missing
- [X] T047 [P] Create backend/ml_models/README.md with comprehensive documentation: usage instructions, model overview, hyperparameter tuning details, quickstart examples
- [X] T048 [P] Add usage examples to README.md: how to run each training script, how to generate comparison report, expected outputs
- [X] T049 [P] Add troubleshooting section to README.md: common issues (memory errors, training time, low accuracy), solutions
- [X] T050 [P] Document model file structure in README.md: .pkl and .json file formats, metadata fields, file naming conventions
- [X] T051 Validate Scenario 1 from quickstart.md: train Random Forest, verify ≥95% accuracy, confirm .pkl and .json files created
- [X] T052 Validate Scenario 2 from quickstart.md: train SVM, verify ≥95% accuracy, confirm model files created
- [X] T053 Validate Scenario 3 from quickstart.md: generate comparison report, verify both models loaded, report shows all metrics
- [X] T054 Validate Scenario 4 from quickstart.md: run Random Forest training twice with same random_state=42, verify identical accuracy scores (reproducibility)
- [X] T055 Validate Scenario 5 from quickstart.md: benchmark model loading and inference time, verify both <1 second
- [X] T056 Validate Scenario 6 from quickstart.md: check model file sizes, verify .pkl files <10 MB, .json files <10 KB
- [X] T057 Validate combined training time: run both train_random_forest.py and train_svm.py, verify total time <10 minutes (SC-002)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion (T001-T008) - BLOCKS all user stories
- **User Stories (Phase 3-4)**: Both depend on Foundational phase completion (T009-T012)
  - User Story 1 and 2 can proceed in parallel (if staffed) - no dependencies between them
  - Or sequentially in priority order (P1 → P2)
- **Integration & Polish (Phase 5)**: Depends on both user stories being complete (T013-T040)

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **Both stories are independent**: Can be trained in parallel, both read same input files (train/test_features.csv) but write to different output files

### Within Each User Story

- Script skeleton before implementation
- Data loading before GridSearchCV
- GridSearchCV before evaluation
- Evaluation before export
- Export before validation
- Core implementation before logging/error handling

### Parallel Opportunities

- **Phase 1 Setup**: T001-T008 can all run in parallel (independent file/directory operations)
- **Phase 2 Foundational**: T009-T012 can all run in parallel (different utility files, no dependencies)
- **Once Foundational completes**: User Stories 1 and 2 can be worked on in parallel by different developers
  - Both stories read same inputs (Feature 004 outputs) but write to different files
  - No conflicts between stories
- **Phase 5 Polish**: T047-T050 documentation tasks can run in parallel, T051-T057 validation tasks run sequentially

---

## Parallel Example: Phase 2 Foundational

```bash
# Launch all foundational utilities together:
Task: "Implement model I/O utilities in backend/ml_models/scripts/utils/model_io.py"
Task: "Implement evaluation utilities in backend/ml_models/scripts/utils/evaluation.py"
Task: "Implement data loading utility in backend/ml_models/scripts/utils/model_io.py"
Task: "Implement metadata generation in backend/ml_models/scripts/utils/model_io.py"
```

## Parallel Example: User Stories 1 and 2

```bash
# After Phase 2 complete, launch both user stories in parallel:
Task: "Implement Random Forest training script (US1)"
Task: "Implement SVM training script (US2)"
# Both stories are independent and write to different output files
```

## Parallel Example: Phase 5 Documentation

```bash
# Launch all documentation tasks together:
Task: "Create backend/ml_models/README.md with comprehensive documentation"
Task: "Add usage examples to README.md"
Task: "Add troubleshooting section to README.md"
Task: "Document model file structure in README.md"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T008) - ~5 minutes
2. Complete Phase 2: Foundational (T009-T012) - ~20 minutes, CRITICAL
3. Complete Phase 3: User Story 1 (T013-T026) - ~1-1.5 hours
4. **STOP and VALIDATE**: Run train_random_forest.py, verify outputs, test with Scenarios 1, 4, 5, 6 from quickstart.md
5. Checkpoint: Random Forest model trained and ready for deployment

### Incremental Delivery

1. Complete Setup + Foundational (T001-T012) → Foundation ready
2. Add User Story 1 (T013-T026) → Test with quickstart Scenarios 1, 4, 5, 6 → **MVP Complete!** (RF model trained)
3. Add User Story 2 (T027-T040) → Test with quickstart Scenario 2 → SVM model trained
4. Add Integration & Polish (T041-T057) → Comparison report, documentation, full validation
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (T001-T012)
2. Once Foundational is done:
   - Developer A: User Story 1 (T013-T026) - Random Forest
   - Developer B: User Story 2 (T027-T040) - SVM (can start immediately in parallel with A)
3. Both developers can work simultaneously - no conflicts, different output files
4. Developer C: Integration & Polish (T041-T057) after both stories done

---

## Notes

- [P] tasks = different files, no dependencies, safe to run in parallel
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- User Story 1 and 2 are fully independent - can run in parallel
- Use `python backend/ml_models/scripts/train_random_forest.py` to run RF training
- Use `python backend/ml_models/scripts/train_svm.py` to run SVM training
- Use `python backend/ml_models/scripts/compare_models.py` to generate comparison report
- Commit after each completed story for incremental progress tracking
- Stop at any checkpoint to validate story independently
- Success criteria validation:
  - SC-001: Both models achieve ≥95% accuracy (T051, T052)
  - SC-002: Combined training time <10 minutes (T057)
  - SC-003: Inference time <1 second (T055)
  - SC-004: Reproducibility - identical accuracy with same seed (T054)
  - SC-005: All metrics ≥0.90 for both classes (validated in T051, T052)
  - SC-006: Metadata complete (T022, T036 - create metadata)
  - SC-007: ≥95/100 test samples correct (same as SC-001, validated in T051, T052)

---

## Task Summary

**Total Tasks**: 57

**By Phase**:
- Phase 1 (Setup): 8 tasks (T001-T008)
- Phase 2 (Foundational): 4 tasks (T009-T012) - **BLOCKING**
- Phase 3 (User Story 1 - P1 MVP): 14 tasks (T013-T026)
- Phase 4 (User Story 2 - P2): 14 tasks (T027-T040)
- Phase 5 (Integration & Polish): 17 tasks (T041-T057)

**By User Story**:
- User Story 1 (Random Forest): 14 tasks
- User Story 2 (SVM): 14 tasks
- Shared/Infrastructure: 29 tasks (Setup + Foundational + Integration & Polish)

**Parallelizable Tasks**: 16 tasks marked with [P]
- Setup phase: 8 parallel opportunities (T001-T008 all can run together)
- Foundational phase: 4 parallel opportunities (T009-T012 all can run together)
- Polish phase: 4 parallel documentation tasks (T047-T050)

**User Story Independence**:
- User Story 1 (RF) and User Story 2 (SVM) are fully independent
- Both can be implemented and tested in parallel after Foundational phase
- Both read same inputs but write to different output files
- No cross-dependencies between stories

**Estimated Time**:
- MVP (Setup + Foundational + US1): ~2 hours
- Full Feature (All 57 tasks): ~4-5 hours for single developer
- With 2 developers (parallel US1 and US2): ~3-4 hours
- Training time: ~5-10 minutes per model (actual model training, not task implementation)

**Critical Path**:
1. Setup (T001-T008) - required first
2. Foundational (T009-T012) - blocks user stories
3. User Story 1 or 2 (T013-T026 or T027-T040) - can run in parallel
4. Integration & Polish (T041-T057) - after both stories complete
