# Tasks: Retrain SVM on 6 Active Sensor Axes

**Input**: Design documents from `/specs/023-retrain-svm-6axis/`
**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅ | quickstart.md ✅

**Tests**: Not requested — no test tasks generated.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)

---

## Phase 1: Setup

**Purpose**: Confirm environment is ready before any code changes.

- [X] T001 Verify prerequisites: (a) `backend/apps/ml/train.py` exists and contains `train_svm()` and `save_model(svm_model, 'svm.pkl', ...)`; (b) `Dataset.csv` exists at repo root (`../Dataset.csv` relative to `backend/`); (c) `backend/apps/ml/feature_utils.py` defines `FEATURE_COLUMNS = ['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']`; (d) `backend/apps/ml/predict.py` contains `model_files = {..., 'svm': 'svm.pkl'}`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No foundational blocking tasks for this feature — it requires no migrations, no new packages, and no new Django apps. Both user stories can begin immediately after Setup.

*(Phase intentionally empty — proceed directly to user story phases.)*

---

## Phase 3: User Story 1 — Retrain SVM on 6 Active Sensor Axes and Export Named Artifact (Priority: P1) 🎯 MVP

**Goal**: Update `backend/apps/ml/train.py` to export the SVM as `svm_model.pkl` instead of `svm.pkl` (module docstring + `save_model` call); run training to produce the artifact.

**Independent Test**: Run `python apps/ml/train.py --dataset ../Dataset.csv --output ml_models --models svm` from `backend/`; confirm `ml_models/svm_model.pkl` is created, F1 score ≥ 0.85 is reported, and `ml_models/svm_model_metrics.json` contains `"kernel": "rbf"` and `"n_features": 6`.

### Implementation for User Story 1

- [X] T002 [US1] Update module docstring in `backend/apps/ml/train.py` (line 12): change `- SVM (svm.pkl)` to `- SVM (svm_model.pkl)`

- [X] T003 [US1] Update the `save_model` call in `main()` in `backend/apps/ml/train.py` (line 267): change `save_model(svm_model, 'svm.pkl', args.output, svm_metrics)` to `save_model(svm_model, 'svm_model.pkl', args.output, svm_metrics)`

- [X] T004 [US1] Run the updated training script from `backend/`: `python apps/ml/train.py --dataset ../Dataset.csv --output ml_models --models svm` — confirm it completes without error and creates `backend/ml_models/svm_model.pkl` and `backend/ml_models/svm_model_metrics.json`

- [X] T005 [US1] Verify US1 acceptance (quickstart Scenario 1 + 2): load `ml_models/svm_model.pkl` with joblib, assert `model.n_features_in_ == 6` and `model.kernel == 'rbf'`, call `model.predict([[0.5, -0.3, 10.2, 0.05, -0.02, 0.01]])` and confirm a valid class label is returned without error; confirm F1 score reported by training run meets ≥ 0.85 threshold

**Checkpoint**: US1 complete — `svm_model.pkl` exported with RBF kernel; model accepts 6-axis input; metrics JSON records kernel type, n_features=6, F1 ≥ 0.85.

---

## Phase 4: User Story 2 — Exported Model is Immediately Compatible with the Inference Pipeline (Priority: P2)

**Goal**: Update `predict.py` to look for `svm_model.pkl` instead of `svm.pkl`; verify the inference pipeline loads and uses the retrained model without errors within the 70ms latency requirement.

**Independent Test**: Run `python apps/ml/predict.py --model-dir ml_models --params ml_data/params.json --model-type svm` from `backend/`; confirm `svm_model.pkl` loads cleanly (`n_features_in_=6`), and a test prediction returns a valid class label with no shape or schema errors, and latency <70ms.

**Note**: T006 can be done in parallel with T002–T003 (different file: `predict.py` vs `train.py`). T007 verification requires T004 to complete first (needs `svm_model.pkl` on disk).

### Implementation for User Story 2

- [X] T006 [P] [US2] Update `model_files` dict in `backend/apps/ml/predict.py` (line ~91): change `'svm': 'svm.pkl'` to `'svm': 'svm_model.pkl'`

- [X] T007 [US2] Verify US2 acceptance (quickstart Scenario 3): run `python apps/ml/predict.py --model-dir ml_models --params ml_data/params.json --model-type svm` from `backend/`; confirm output shows `[OK] SVM: n_features_in_=6` and `[OK] ML Predictor ready`; confirm test prediction returns a class label with no `FileNotFoundError` or shape mismatch errors, and latency is reported as <70ms

**Checkpoint**: US2 complete — inference pipeline loads `svm_model.pkl` and produces predictions from 6-axis input with no code changes beyond `predict.py`.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: End-to-end validation and backward-compatibility confirmation.

- [X] T008 [P] Verify metrics JSON (quickstart Scenario 5): load `backend/ml_models/svm_model_metrics.json`; assert `n_features == 6`, `kernel == 'rbf'`, and `f1_score >= 0.85`

- [X] T009 [P] Validate artifact with `validate_models.py` (quickstart Scenario 4): run `python apps/ml/validate_models.py ml_models/svm_model.pkl 6` from `backend/`; confirm output is `✓ Model validated: n_features_in_ = 6`

- [X] T010 [P] Verify backward compatibility (quickstart Scenario 6): confirm `backend/ml_models/svm.pkl` still exists (was not deleted), `backend/ml_models/rf_model.pkl` still exists and is unchanged, and only `predict.py`'s `model_files` dict was modified (not RF loading logic)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **US1 (Phase 3)**: Depends on Setup (T001) — can start immediately after
- **US2 (Phase 4)**: T006 can start immediately after T001 (different file from train.py); T007 depends on T004 (needs svm_model.pkl on disk)
- **Polish (Phase 5)**: T008, T009, T010 all depend on T004 (needs svm_model.pkl); can run in parallel once T004 is complete

### User Story Dependencies

- **US1 (P1)**: Independent — all tasks in `train.py` and training run
- **US2 (P2)**: T006 fully independent of US1 code tasks (different file); T007 depends on T004 (artifact must exist)

### Within Each User Story

- T002 → T003 are sequential (both edits to `train.py`, run in order to avoid conflicts)
- T004 depends on T002 and T003 (all code changes in `train.py` must be complete before running training)
- T005 depends on T004 (artifact must exist)
- T006 [P] is independent of T002–T003 (different file)
- T007 depends on T004 (artifact must exist)
- T008, T009, T010 all depend on T004; can run in parallel

### Parallel Opportunities

- T006 [P] runs simultaneously with T002–T003 (predict.py vs train.py — different files)
- T008, T009, T010 all run in parallel after T004

---

## Parallel Example: US1 + US2 Code Changes

```bash
# T002–T003 and T006 have no shared files — run them together:
Task: "Update train.py docstring + rename save_model export to svm_model.pkl"   # T002–T003
Task: "Update predict.py model_files dict: 'svm': 'svm_model.pkl'"              # T006
```

## Parallel Example: Polish Phase

```bash
# T008, T009, T010 all independent — run them together after T004:
Task: "Verify metrics JSON has kernel='rbf' and n_features=6"   # T008
Task: "Run validate_models.py ml_models/svm_model.pkl 6"        # T009
Task: "Verify svm.pkl and rf_model.pkl still exist"             # T010
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 3: US1 (T002 → T003 → T004 → T005)
3. **STOP and VALIDATE**: `svm_model.pkl` exported; F1 ≥ 0.85; kernel='rbf'; model predicts from 6-axis input
4. Demonstrate: SVM model with 6-axis-only feature scope, consistent naming with `rf_model.pkl`

### Incremental Delivery

1. Phase 1 (T001) → Environment confirmed
2. Phase 3 US1 (T002–T005) → Trained model artifact ✅
3. Phase 4 US2 (T006–T007) → Inference pipeline updated ✅
4. Phase 5 Polish (T008–T010) → Full validation ✅

### Notes

- **Only 2 source files** change: `train.py` (3 lines: docstring + filename) and `predict.py` (1 line: model_files dict)
- **Training time**: SVM is faster than RF GridSearchCV but still requires O(n²) kernel computations on 22,396 samples — expect several minutes
- **No grid search**: RBF kernel with fixed C=1.0, gamma='scale' is the full scope — no hyperparameter sweep
- **No new migrations, packages, or Django apps** required
- **Legacy artifacts** (`svm.pkl`, `random_forest.pkl`) are preserved — only `predict.py`'s `model_files['svm']` changes
- **T006 is the only parallel task** during the implementation phase — run it while train.py edits (T002–T003) are in progress
- **Companion to Feature 022**: Together, 022 + 023 complete the artifact naming alignment for both active ML models
