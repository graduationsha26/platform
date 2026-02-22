# Research: Retrain SVM on 6 Active Sensor Axes (Feature 023)

**Branch**: `023-retrain-svm-6axis` | **Date**: 2026-02-18
**Phase**: 0 — Research & Technical Unknowns Resolution

---

## Research Questions & Decisions

### Q1: Which training script to update?

**Decision**: `backend/apps/ml/train.py` (Feature 011 Raw Feature Pipeline script).

**Rationale**: There are two SVM-related scripts in the repository:
- `backend/apps/ml/train.py` — the active training script for the raw 6-axis pipeline (introduced in Feature 011). This is the correct target.
- `backend/ml_models/scripts/train_random_forest.py` — a deprecated script from Feature 005 that trained on 30 engineered features. Contains SVM training but expects a different feature space. Must not be touched.

**Evidence**: `backend/apps/ml/train.py` contains `train_svm()` at line 121 and calls `save_model(svm_model, 'svm.pkl', ...)` at line 267. This is the correct file.

---

### Q2: Does `train_svm()` already use exactly 6 features?

**Decision**: Yes — no feature selection changes needed.

**Rationale**: `train_svm()` receives `X_train` and `X_test` which originate from `load_training_data(args.dataset)` in `main()`. That function (from `feature_utils.py`) extracts only `FEATURE_COLUMNS = ['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']`. The SVM sees the same 6-column array as the RF. No changes to `train_svm()` internals are needed for feature scope.

---

### Q3: What hyperparameters does the current SVM use?

**Decision**: Keep existing fixed hyperparameters (RBF kernel, C=1.0, gamma='scale'). No grid search in scope.

**Current configuration** (train.py lines 140–146):
```python
svm = SVC(
    kernel='rbf',
    C=1.0,
    gamma='scale',
    random_state=42,
    verbose=True
)
```

**Rationale**: The feature specification explicitly requests "RBF kernel" with no mention of hyperparameter search. Unlike Feature 022 (RF), which required GridSearchCV, the SVM feature is scoped to retrain with fixed params and rename the artifact. SVC with RBF kernel + C=1.0 + gamma='scale' is a sound default for sensor classification tasks.

**Alternatives considered**:
- GridSearchCV for SVM: Not requested in spec; also significantly slower than RF grid search due to SVM's O(n²–n³) training cost. Feature 023 is intentionally a simpler companion to Feature 022.
- LinearSVC: Not appropriate — RBF kernel is explicitly specified in the feature description.

---

### Q4: What changes are required in `train.py`?

**Decision**: Two changes only.

| Location | Old Value | New Value |
|----------|-----------|-----------|
| Line 12 (module docstring) | `- SVM (svm.pkl)` | `- SVM (svm_model.pkl)` |
| Line 267 (`main()`) | `save_model(svm_model, 'svm.pkl', args.output, svm_metrics)` | `save_model(svm_model, 'svm_model.pkl', args.output, svm_metrics)` |

No changes to `train_svm()` function body, no new imports, no new hyperparameters.

---

### Q5: What changes are required in `predict.py`?

**Decision**: One line change in the `model_files` dict.

| Location | Old Value | New Value |
|----------|-----------|-----------|
| Line 91 (`_load_models()`) | `'svm': 'svm.pkl'` | `'svm': 'svm_model.pkl'` |

The RF entry is already `'rf': 'rf_model.pkl'` (updated in Feature 022). This change makes SVM consistent.

---

### Q6: What metrics does `train_svm()` record?

**Confirmed**: `train_svm()` returns a metrics dict with:
- `model_type`: 'SVM'
- `accuracy`: float
- `f1_score`: float
- `n_features`: int (will be 6)
- `feature_names`: list (FEATURE_COLUMNS)
- `kernel`: str ('rbf')
- `trained_date`: ISO timestamp

The saved metrics file will be named `svm_model_metrics.json` (because `save_model()` derives the metrics filename from the model filename by replacing `.pkl` with `_metrics.json`).

---

### Q7: Will `validate_models.py` work with `svm_model.pkl`?

**Decision**: Yes — no changes to `validate_models.py` needed.

**Rationale**: The validation script is generic; it accepts any `.pkl` path and an expected feature count. Running `python apps/ml/validate_models.py ml_models/svm_model.pkl 6` will work correctly once the artifact is created.

---

### Q8: What is the F1 performance expectation?

**Decision**: F1 ≥ 0.85 on held-out test set (20% of Dataset.csv).

**Rationale**: Same threshold as RF (Feature 022). The RF achieved F1 = 0.9968 on this dataset. The SVM with RBF kernel should achieve similar results, as SVM with RBF is effective for well-separated classification tasks. Previous experiments with this dataset showed SVM performance in the 0.85–0.99 range.

---

### Q9: Is the old `svm.pkl` preserved?

**Decision**: Yes — `svm.pkl` is not deleted.

**Rationale**: The train.py change only modifies the output filename for new training runs. The existing `svm.pkl` file on disk is not touched. Both artifacts coexist. This is consistent with how `random_forest.pkl` was preserved when `rf_model.pkl` was introduced in Feature 022.

---

## Summary of Changes

| File | Lines Changed | Nature of Change |
|------|--------------|-----------------|
| `backend/apps/ml/train.py` | 2 lines | Rename export: `svm.pkl` → `svm_model.pkl` (docstring + save_model call) |
| `backend/apps/ml/predict.py` | 1 line | Update model_files dict: `'svm': 'svm.pkl'` → `'svm': 'svm_model.pkl'` |

**Total source code changes**: 3 lines across 2 files. No new imports. No migrations. No schema changes.
