# Implementation Plan: Retrain SVM on 6 Active Sensor Axes

**Branch**: `023-retrain-svm-6axis` | **Date**: 2026-02-18 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/023-retrain-svm-6axis/spec.md`

---

## Summary

Feature 023 updates the SVM training pipeline (`backend/apps/ml/train.py`) to export the SVM artifact as `svm_model.pkl` instead of `svm.pkl`, and updates the inference pipeline (`backend/apps/ml/predict.py`) to reference the new filename. The SVM already trains on exactly 6 active sensor axes (aX, aY, aZ, gX, gY, gZ) via `feature_utils.load_training_data()`, uses an RBF kernel with fixed hyperparameters, and produces correct metrics — the only gap is the artifact filename. This is a 3-line change across 2 files plus a training run.

**Total code changes**: 2 files, 3 lines. No new files, no migrations, no schema changes.

This is the direct SVM companion to Feature 022 (retrain-rf-6axis), completing the artifact naming alignment for both ML models.

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
**Performance Goals**: Training completes in reasonable time for local dev; SVM inference latency <70ms
**Constraints**: Local development only; no Docker/CI/CD
**Scale/Scope**: ~10 doctors, ~100 patients; 27,995 training samples in Dataset.csv

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Monorepo Architecture**: Changes in `backend/apps/ml/` — within monorepo
- [x] **Tech Stack Immutability**: scikit-learn is already in the stack; SVC (SVM) is a scikit-learn class, not a new library
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
specs/023-retrain-svm-6axis/
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
│       ├── train.py                # [MODIFY] 2 lines:
│       │                           #   (1) module docstring: 'svm.pkl' → 'svm_model.pkl'
│       │                           #   (2) main(): save_model(svm_model, 'svm.pkl', ...) →
│       │                           #              save_model(svm_model, 'svm_model.pkl', ...)
│       └── predict.py              # [MODIFY] 1 line:
│                                   #   model_files: 'svm': 'svm.pkl' → 'svm': 'svm_model.pkl'
└── ml_models/
    └── svm_model.pkl               # [GENERATED] New artifact (runtime output, gitignored)
    └── svm_model_metrics.json      # [GENERATED] New metrics file (runtime output)
```

**Files explicitly NOT touched**:
- `backend/apps/ml/feature_utils.py` — `FEATURE_COLUMNS` already = `['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']`
- `backend/apps/ml/train_svm()` function body — already uses RBF kernel, fixed hyperparameters
- `backend/apps/ml/normalize.py` — Normalization config correct; no change in scope
- `backend/apps/ml/validate_models.py` — Already validates `n_features_in_=6` generically
- `backend/ml_models/svm.pkl` — Legacy artifact preserved (not deleted)
- All Django views, URLs, consumers, migrations — No API layer changes needed

---

## Phase 0: Research Findings

See [research.md](research.md) for full details. Summary:

| Question | Answer |
|---|---|
| Which training script to update? | `backend/apps/ml/train.py` (Feature 011 script). NOT the deprecated `ml_models/scripts/train_random_forest.py`. |
| Does `train_svm()` already use 6 features? | Yes — via `load_training_data()` → `feature_utils.FEATURE_COLUMNS`. No feature selection changes needed. |
| What hyperparameters does current SVM use? | `SVC(kernel='rbf', C=1.0, gamma='scale', random_state=42)` — fixed, no grid search needed. |
| What changes in `train.py`? | 2 lines: module docstring + `save_model()` filename argument. |
| What changes in `predict.py`? | 1 line: `'svm': 'svm.pkl'` → `'svm': 'svm_model.pkl'` in `model_files` dict. |
| Is `validate_models.py` generic enough? | Yes — already accepts any `.pkl` path and expected feature count. No changes needed. |
| Is old `svm.pkl` preserved? | Yes — training only writes a new artifact; old file untouched. |

---

## Phase 1: Design & Contracts

### Data Model

See [data-model.md](data-model.md) for full entity definitions. No new database entities.

**Training pipeline flow**: Dataset.csv → `load_training_data()` (6 columns selected) → `train_test_split` (80/20 stratified) → `SVC(kernel='rbf', C=1.0, gamma='scale')` → `save_model('svm_model.pkl')` + metrics JSON → `validate_sklearn_model(expected_features=6)`.

### Schemas / Contracts

See [contracts/training-pipeline-schema.yaml](contracts/training-pipeline-schema.yaml).

Documents:
- CLI interface: `python apps/ml/train.py --models svm` invocation
- Model artifact contract: `svm_model.pkl` with `n_features_in_=6`, `kernel='rbf'`
- Metrics JSON schema: model_type, accuracy, f1_score, n_features, kernel, trained_date
- Inference integration: `predict.py` model_files update

### Integration Scenarios

See [quickstart.md](quickstart.md) for 6 verification scenarios covering:
1. Training runs end-to-end, exports `svm_model.pkl`
2. Model accepts 6-axis input and returns prediction without error
3. Inference pipeline (`predict.py`) loads `svm_model.pkl` cleanly
4. `validate_models.py` validates artifact
5. Metrics JSON contains all required fields (F1 ≥ 0.85, n_features=6, kernel='rbf')
6. Legacy artifacts (`svm.pkl`, `rf_model.pkl`) unaffected

---

## Implementation Tasks

Feature 023 has exactly **2 code edits** and verification steps.

### Task 1: Update module docstring in `backend/apps/ml/train.py`

**Change** (line 12):
```python
# Old:
    - SVM (svm.pkl)

# New:
    - SVM (svm_model.pkl)
```

### Task 2: Update `save_model()` call in `main()` in `backend/apps/ml/train.py`

**Change** (line 267):
```python
# Old:
save_model(svm_model, 'svm.pkl', args.output, svm_metrics)

# New:
save_model(svm_model, 'svm_model.pkl', args.output, svm_metrics)
```

### Task 3: Update `model_files` in `backend/apps/ml/predict.py`

**Change** (line ~91):
```python
# Old:
model_files = {
    'rf': 'rf_model.pkl',
    'svm': 'svm.pkl'
}

# New:
model_files = {
    'rf': 'rf_model.pkl',
    'svm': 'svm_model.pkl'
}
```

### Task 4: Run Training

```bash
cd backend
python apps/ml/train.py --dataset ../Dataset.csv --output ml_models --models svm
```

Verify: `ml_models/svm_model.pkl` exists; metrics show F1 ≥ 0.85; kernel='rbf' in JSON.

### Task 5: Verify Inference Compatibility

```bash
python apps/ml/predict.py --model-dir ml_models --params ml_data/params.json --model-type svm
```

Verify: No `FileNotFoundError`; `n_features_in_=6`; test prediction succeeds; latency <70ms.

---

## Complexity Tracking

No constitution violations. No new complexity added — `SVC` is already in the constitutional scikit-learn stack.
