# Tasks: Retrain Random Forest on 6 Active Sensor Axes

**Input**: Design documents from `/specs/022-retrain-rf-6axis/`
**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅ | quickstart.md ✅

**Tests**: Not requested — no test tasks generated.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)

---

## Phase 1: Setup

**Purpose**: Confirm environment is ready before any code changes.

- [X] T001 Verify prerequisites: (a) `backend/apps/ml/train.py` exists and contains `train_random_forest()`; (b) `Dataset.csv` exists at repo root (`../Dataset.csv` relative to `backend/`); (c) `backend/ml_data/params.json` exists and has 6 features; (d) `backend/apps/ml/feature_utils.py` defines `FEATURE_COLUMNS = ['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No foundational blocking tasks for this feature — it requires no migrations, no new packages, and no new Django apps. Both user stories can begin immediately after Setup.

*(Phase intentionally empty — proceed directly to user story phases.)*

---

## Phase 3: User Story 1 — Train Model on 6 Active Sensor Axes with Hyperparameter Optimization (Priority: P1) 🎯 MVP

**Goal**: Update `backend/apps/ml/train.py` to use `GridSearchCV` with `StratifiedKFold` for RF hyperparameter search; rename the RF export from `random_forest.pkl` to `rf_model.pkl`; run training to produce the artifact.

**Independent Test**: Run `python apps/ml/train.py --dataset ../Dataset.csv --output ml_models --models rf` from `backend/`; confirm `ml_models/rf_model.pkl` is created, F1 score ≥ 0.85 is reported, and `best_params` appears in `ml_models/rf_model_metrics.json`.

### Implementation for User Story 1

- [X] T002 [US1] Update imports in `backend/apps/ml/train.py`: add `GridSearchCV` and `StratifiedKFold` to the `from sklearn.model_selection import train_test_split` import line so it reads `from sklearn.model_selection import train_test_split, GridSearchCV, StratifiedKFold`

- [X] T003 [US1] Replace the fixed-parameter `RandomForestClassifier(...)` block in `train_random_forest()` in `backend/apps/ml/train.py` with a `GridSearchCV` search: define `param_grid = {'n_estimators': [100, 200, 300], 'max_depth': [10, 20, None]}`; create `base_rf = RandomForestClassifier(min_samples_split=10, min_samples_leaf=4, random_state=42, n_jobs=-1)`; create `cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)`; create `grid_search = GridSearchCV(estimator=base_rf, param_grid=param_grid, cv=cv, scoring='accuracy', n_jobs=-1, verbose=2)`; call `grid_search.fit(X_train, y_train)`; set `rf = grid_search.best_estimator_`

- [X] T004 [US1] Add `best_params` and `best_cv_score` fields to the `metrics` dict returned by `train_random_forest()` in `backend/apps/ml/train.py`: `'best_params': grid_search.best_params_` and `'best_cv_score': float(grid_search.best_score_)`

- [X] T005 [US1] Update the `save_model` call in `main()` in `backend/apps/ml/train.py`: change `save_model(rf_model, 'random_forest.pkl', args.output, rf_metrics)` to `save_model(rf_model, 'rf_model.pkl', args.output, rf_metrics)`

- [X] T006 [US1] Run the updated training script from `backend/`: `python apps/ml/train.py --dataset ../Dataset.csv --output ml_models --models rf` — confirm it completes without error and creates `backend/ml_models/rf_model.pkl` and `backend/ml_models/rf_model_metrics.json`

- [X] T007 [US1] Verify US1 acceptance (quickstart Scenario 1 + 2): load `ml_models/rf_model.pkl` with joblib, assert `model.n_features_in_ == 6`, call `model.predict([[0.5, -0.3, 10.2, 0.05, -0.02, 0.01]])` and confirm a valid class label is returned without error; confirm F1 score reported by training run meets ≥ 0.85 threshold

**Checkpoint**: US1 complete — `rf_model.pkl` exported with GridSearchCV-tuned hyperparameters; model accepts 6-axis input; metrics include `best_params`.

---

## Phase 4: User Story 2 — Exported Model is Immediately Compatible with the Inference Pipeline (Priority: P2)

**Goal**: Update `predict.py` to look for `rf_model.pkl` instead of `random_forest.pkl`; verify the inference pipeline loads and uses the retrained model without errors.

**Independent Test**: Run `python apps/ml/predict.py --model-dir ml_models --params ml_data/params.json` from `backend/`; confirm `rf_model.pkl` loads cleanly (`n_features_in_=6`), and a test prediction returns a valid class label with no shape or schema errors.

**Note**: T008 can be done in parallel with T003–T005 (different file: `predict.py` vs `train.py`). T009 verification requires T006 to complete first (needs `rf_model.pkl` on disk).

### Implementation for User Story 2

- [X] T008 [P] [US2] Update `model_files` dict in `backend/apps/ml/predict.py` (line ~90): change `'rf': 'random_forest.pkl'` to `'rf': 'rf_model.pkl'`

- [X] T009 [US2] Verify US2 acceptance (quickstart Scenario 3): run `python apps/ml/predict.py --model-dir ml_models --params ml_data/params.json` from `backend/`; confirm output shows `[OK] RF: n_features_in_=6` and `[OK] ML Predictor ready`; confirm test prediction returns a class label with no `FileNotFoundError` or shape mismatch errors

**Checkpoint**: US2 complete — inference pipeline loads `rf_model.pkl` and produces predictions from 6-axis input with no code changes beyond `predict.py`.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: End-to-end validation and backward-compatibility confirmation.

- [X] T010 Verify metrics JSON (quickstart Scenario 5): load `backend/ml_models/rf_model_metrics.json`; assert `n_features == 6`, `'best_params' in metrics`, `'best_cv_score' in metrics`, and `f1_score >= 0.85`

- [X] T011 [P] Validate artifact with `validate_models.py` (quickstart Scenario 4): run `python apps/ml/validate_models.py ml_models/rf_model.pkl 6` from `backend/`; confirm output is `✓ Model validated: n_features_in_ = 6`

- [X] T012 [P] Verify backward compatibility (quickstart Scenario 6): confirm `backend/ml_models/random_forest.pkl` still exists (was not deleted), `backend/ml_models/svm.pkl` still exists and is unchanged, and only `predict.py`'s `model_files` dict was modified (not SVM loading logic)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **US1 (Phase 3)**: Depends on Setup (T001) — can start immediately after
- **US2 (Phase 4)**: T008 can start immediately after T001 (different file from train.py); T009 depends on T006 (needs rf_model.pkl on disk)
- **Polish (Phase 5)**: T010, T011, T012 all depend on T006 (needs rf_model.pkl); can run in parallel once T006 is complete

### User Story Dependencies

- **US1 (P1)**: Independent — all tasks in `train.py` and training run
- **US2 (P2)**: T008 fully independent of US1 code tasks (different file); T009 depends on T006 (artifact must exist)

### Within Each User Story

- T002 → T003 → T004 → T005 are sequential (all edits to `train.py`)
- T006 depends on T002–T005 (all code changes in `train.py` must be complete before running training)
- T007 depends on T006 (artifact must exist)
- T008 [P] is independent of T002–T005 (different file)
- T009 depends on T006 (artifact must exist)
- T010, T011, T012 all depend on T006; can run in parallel

### Parallel Opportunities

- T008 [P] runs simultaneously with T002–T005 (predict.py vs train.py — different files)
- T010, T011, T012 all run in parallel after T006

---

## Parallel Example: US1 + US2 Code Changes

```bash
# T002–T005 and T008 have no shared files — run them together:
Task: "Update train.py imports + add GridSearchCV + rename export"   # T002–T005
Task: "Update predict.py model_files dict: 'rf': 'rf_model.pkl'"    # T008
```

## Parallel Example: Polish Phase

```bash
# T010, T011, T012 all independent — run them together after T006:
Task: "Verify metrics JSON has best_params"                           # T010
Task: "Run validate_models.py ml_models/rf_model.pkl 6"              # T011
Task: "Verify random_forest.pkl and svm.pkl still exist"             # T012
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 3: US1 (T002 → T003 → T004 → T005 → T006 → T007)
3. **STOP and VALIDATE**: `rf_model.pkl` exported; F1 ≥ 0.85; `best_params` in metrics; model predicts from 6-axis input
4. Demonstrate: GridSearchCV-trained RF model with 6-axis-only feature scope

### Incremental Delivery

1. Phase 1 (T001) → Environment confirmed
2. Phase 3 US1 (T002–T007) → Trained model artifact ✅
3. Phase 4 US2 (T008–T009) → Inference pipeline updated ✅
4. Phase 5 Polish (T010–T012) → Full validation ✅

### Notes

- **Only 2 source files** change: `train.py` (GridSearchCV + filename) and `predict.py` (model_files dict)
- **Training takes several minutes** (GridSearchCV: 3×3×5 = 45 fits on 22,396 samples)
- **No new migrations, packages, or Django apps** required
- **Legacy artifacts** (`random_forest.pkl`, `svm.pkl`) are preserved — only `predict.py`'s `model_files['rf']` changes
- **T008 is the only parallel task** during the implementation phase — run it while train.py edits (T002–T005) are in progress
