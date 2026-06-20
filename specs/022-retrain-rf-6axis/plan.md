# Implementation Plan: Retrain Random Forest on 6 Active Sensor Axes

**Branch**: `022-retrain-rf-6axis` | **Date**: 2026-02-18 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/022-retrain-rf-6axis/spec.md`

---

## Summary

Feature 022 updates the Random Forest training pipeline (`backend/apps/ml/train.py`) to use GridSearchCV for hyperparameter optimization instead of fixed parameters, and renames the exported model artifact from `random_forest.pkl` to `rf_model.pkl`. A one-line update to `predict.py` aligns the inference pipeline with the new artifact name. Feature selection is already correct — `train.py` already uses `feature_utils.load_training_data()` which extracts only the 6 active axes (aX, aY, aZ, gX, gY, gZ).

**Total code changes**: 2 files. No new files, no migrations, no schema changes.

---

## Technical Context

**Backend Stack**: Django 5.x + Django REST Framework + Django Channels
**Frontend Stack**: React 18+ + Vite + Tailwind CSS + Recharts
**Database**: Supabase PostgreSQL (remote)
**Authentication**: JWT (SimpleJWT) with roles (patient/doctor)
**Testing**: pytest (backend), Jest/Vitest (frontend)
**Project Type**: web (monorepo: backend/ and frontend/)
**Real-time**: Django Channels WebSocket for live tremor data
**Integration**: MQTT subscription for glove sensor data (paho-mqtt)
**AI/ML**: scikit-learn (.pkl) and TensorFlow/Keras (.h5) — both use params.json for normalization
**Performance Goals**: Training completes in reasonable time for local dev; inference latency <70ms
**Constraints**: Local development only; no Docker/CI/CD
**Scale/Scope**: ~10 doctors, ~100 patients; 27,995 training samples in Dataset.csv

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Monorepo Architecture**: Changes in `backend/apps/ml/` — within monorepo
- [x] **Tech Stack Immutability**: scikit-learn is already in the stack; GridSearchCV is a scikit-learn feature, not a new library
- [x] **Database Strategy**: No database changes; no new entities
- [x] **Authentication**: Feature does not affect auth
- [x] **Security-First**: No secrets or credentials involved; no hardcoded values
- [x] **Real-time Requirements**: Feature does not affect real-time pipeline
- [x] **MQTT Integration**: Feature does not affect MQTT subscription
- [x] **AI Model Serving**: Model artifact `.pkl` served via Django backend — matches constitution requirement
- [x] **API Standards**: No new endpoints; internal pipeline change only
- [x] **Development Scope**: Offline training script; local development only

**Result**: ✅ PASS — no constitution violations

---

## Project Structure

### Documentation (this feature)

```text
specs/022-retrain-rf-6axis/
├── plan.md                          # This file
├── research.md                      # Phase 0 output
├── data-model.md                    # Phase 1 output
├── quickstart.md                    # Phase 1 output
├── contracts/
│   └── training-pipeline-schema.yaml   # Phase 1 output
└── tasks.md                         # Phase 2 output (/speckit.tasks)
```

### Source Code (files touched by this feature)

```text
backend/
├── apps/
│   └── ml/
│       ├── train.py                # [MODIFY] Add GridSearchCV to train_random_forest();
│       │                           #          rename export: 'random_forest.pkl' → 'rf_model.pkl';
│       │                           #          add best_params + best_cv_score to metrics dict
│       └── predict.py              # [MODIFY] model_files: 'rf': 'random_forest.pkl' → 'rf': 'rf_model.pkl'
└── ml_models/
    └── rf_model.pkl                # [GENERATED] New model artifact (runtime output, gitignored)
    └── rf_model_metrics.json       # [GENERATED] New metrics file (runtime output)
```

**Files explicitly NOT touched**:
- `backend/apps/ml/feature_utils.py` — `FEATURE_COLUMNS` already = `['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']`
- `backend/apps/ml/normalize.py` — Normalization config correct; no change in scope
- `backend/apps/ml/generate_params.py` — Already generates 6-axis-only params
- `backend/apps/ml/validate_models.py` — Already validates `n_features_in_=6`
- `backend/ml_models/scripts/train_random_forest.py` — Deprecated (expects 30 features from old pipeline)
- All Django views, URLs, consumers, migrations — No API layer changes needed

---

## Phase 0: Research Findings

See [research.md](research.md) for full details. Summary:

| Question | Answer |
|---|---|
| Which training script to update? | `backend/apps/ml/train.py` (Feature 011 script). NOT `ml_models/scripts/train_random_forest.py` (deprecated, expects 30 features). |
| Does `train.py` already use 6 features? | Yes — via `load_training_data()` → `feature_utils.FEATURE_COLUMNS`. No feature selection changes needed. |
| Does GridSearchCV currently exist in `train.py`? | No — RF uses fixed params. GridSearchCV is the gap to fill. |
| What is the export path? | `ml_models/rf_model.pkl` (renamed from `random_forest.pkl`). |
| Does `predict.py` need changes? | Yes — one line: `'rf': 'random_forest.pkl'` → `'rf': 'rf_model.pkl'`. |
| Use raw or normalized features? | Raw — consistent with current pipeline; normalization switch is out of scope. |
| GridSearchCV param grid? | `{'n_estimators': [100, 200, 300], 'max_depth': [10, 20, None]}` with 5-fold StratifiedKFold. |

---

## Phase 1: Design & Contracts

### Data Model

See [data-model.md](data-model.md) for full entity definitions. No new database entities.

**Training pipeline flow**: Dataset.csv → `load_training_data()` (6 columns selected) → `train_test_split` (80/20 stratified) → `GridSearchCV(RandomForestClassifier, param_grid, cv=StratifiedKFold(5))` → best model → `save_model('rf_model.pkl')` + metrics JSON → `validate_sklearn_model(expected_features=6)`.

### Schemas / Contracts

See [contracts/training-pipeline-schema.yaml](contracts/training-pipeline-schema.yaml).

Documents:
- CLI interface: `python apps/ml/train.py --models rf` invocation
- Model artifact contract: `rf_model.pkl` with `n_features_in_=6`
- Metrics JSON schema: includes new `best_params` and `best_cv_score` fields
- Inference integration: `predict.py` model_files update

### Integration Scenarios

See [quickstart.md](quickstart.md) for 6 verification scenarios covering:
1. Training runs end-to-end with GridSearchCV, exports `rf_model.pkl`
2. Model accepts 6-axis input and returns prediction without error
3. Inference pipeline (`predict.py`) loads `rf_model.pkl` cleanly
4. `validate_models.py` validates artifact
5. Metrics JSON contains `best_params` from GridSearchCV
6. Legacy artifacts (`random_forest.pkl`, `svm.pkl`) unaffected

---

## Implementation Tasks

Feature 022 has exactly **2 code edits** and several verification steps.

### Task 1: Update `train_random_forest()` in `backend/apps/ml/train.py`

**Changes**:

1. Add `GridSearchCV` and `StratifiedKFold` imports
2. Replace the fixed-parameter `RandomForestClassifier(n_estimators=100, ...)` block with a `GridSearchCV` setup:

   ```python
   param_grid = {
       'n_estimators': [100, 200, 300],
       'max_depth':    [10, 20, None],
   }
   base_rf = RandomForestClassifier(
       min_samples_split=10,
       min_samples_leaf=4,
       random_state=42,
       n_jobs=-1,
   )
   cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
   grid_search = GridSearchCV(
       estimator=base_rf,
       param_grid=param_grid,
       cv=cv,
       scoring='accuracy',
       n_jobs=-1,
       verbose=2,
   )
   grid_search.fit(X_train, y_train)
   rf = grid_search.best_estimator_
   ```

3. Add `best_params` and `best_cv_score` to the `metrics` dict
4. Change `save_model(rf_model, 'random_forest.pkl', ...)` → `save_model(rf_model, 'rf_model.pkl', ...)`

### Task 2: Update `model_files` in `backend/apps/ml/predict.py`

```python
# Old:
model_files = {'rf': 'random_forest.pkl', 'svm': 'svm.pkl'}

# New:
model_files = {'rf': 'rf_model.pkl', 'svm': 'svm.pkl'}
```

### Task 3: Run Training

```bash
cd backend
python apps/ml/train.py --dataset ../Dataset.csv --output ml_models --models rf
```

Verify: `ml_models/rf_model.pkl` exists; metrics show F1 ≥ 0.85; `best_params` in JSON.

### Task 4: Verify Inference Compatibility

```bash
python apps/ml/predict.py --model-dir ml_models --params ml_data/params.json
```

Verify: No `FileNotFoundError`; `n_features_in_=6`; test prediction succeeds.

---

## Complexity Tracking

No constitution violations. No new complexity added — GridSearchCV is a standard scikit-learn feature already in the stack.
