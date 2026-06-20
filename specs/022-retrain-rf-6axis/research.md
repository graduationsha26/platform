# Research: Retrain Random Forest on 6 Active Sensor Axes (Feature 022)

**Branch**: `022-retrain-rf-6axis` | **Date**: 2026-02-18

---

## Phase 0 Research Findings

### Q1: Which training script is the canonical one to update?

**Decision**: Update `backend/apps/ml/train.py` (the Feature 011 raw-feature pipeline script).

**Rationale**:
- `backend/apps/ml/train.py` is the script that loads data via `feature_utils.load_training_data()`, which already applies the 6-axis-only `FEATURE_COLUMNS = ['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']` constraint.
- The spec refers to "train_ml.py" — the actual filename is `train.py` in `backend/apps/ml/`. This is the file to update.
- `backend/ml_models/scripts/train_random_forest.py` (from Feature 005) is outdated: its `validate_data()` hardcodes `X_train.shape[1] != 30` (expects 30 features from the old aggregated pipeline). It must NOT be used or modified.

**Alternatives considered**:
- Using `ml_models/scripts/train_random_forest.py`: Rejected — it expects 30 features (from the old Feature 004 processed CSV pipeline) and requires separate `train_features.csv`/`test_features.csv` files. Updating it would require a full refactor of a deprecated script.

---

### Q2: Does `train.py` already use 6 features?

**Decision**: Yes — no feature-selection changes needed.

**Rationale**:
`train.py` calls `load_training_data(dataset_path)` from `feature_utils.py`. That function calls `extract_features_from_dataframe(df)` which applies `df[FEATURE_COLUMNS].values` where `FEATURE_COLUMNS = ['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']`. Magnetometer columns (mX, mY, mZ) are never loaded. Feature-column enforcement is already correct.

**Audit**: The old `train_random_forest.py` (Feature 005) loaded pre-processed CSVs with 30 features (aggregated statistical features). `train.py` (Feature 011) loads raw 6-axis sensor readings directly from `Dataset.csv`. They are entirely separate pipelines.

---

### Q3: Does GridSearchCV currently exist in `train.py`?

**Decision**: No — GridSearchCV is the gap to fill.

**Rationale**:
`train.py` currently trains the Random Forest with fixed hardcoded hyperparameters:
```
n_estimators=100, max_depth=20, min_samples_split=10, min_samples_leaf=4
```
No cross-validated search is performed. The `ml_models/scripts/train_random_forest.py` (Feature 005) does have GridSearchCV with a param grid of `{n_estimators: [50,100,200,300], max_depth: [10,20,30,None]}`, but it is the wrong pipeline.

**Implementation approach**: Add GridSearchCV to `train_random_forest()` in `train.py`. A practical param grid for the 27,995-sample dataset:
```python
param_grid = {
    'n_estimators': [100, 200, 300],
    'max_depth':    [10, 20, None],
}
```
With 5-fold StratifiedKFold, this is 3×3×5 = 45 fits — fast enough for local development. Additional parameters (`min_samples_split`, `min_samples_leaf`) can be kept fixed at their proven values or added to the grid if training time allows.

---

### Q4: What is the correct export path for the new model artifact?

**Decision**: Export to `backend/ml_models/rf_model.pkl` (model name changed from `random_forest.pkl` to `rf_model.pkl`).

**Rationale**:
- `predict.py` (inference pipeline) loads models from `ml_models/` by resolving `os.path.join(self.model_dir, filename)` where `model_dir='ml_models'` (default, relative to `backend/`).
- It currently looks for `{'rf': 'random_forest.pkl', 'svm': 'svm.pkl'}`.
- Changing the exported filename to `rf_model.pkl` requires a one-line update in `predict.py`'s `model_files` dict.
- The spec explicitly names the artifact `rf_model.pkl`, so this rename is intentional.

**Alternatives considered**:
- Keep `random_forest.pkl` filename: Would avoid updating `predict.py`, but conflicts with the explicit spec requirement.
- Write to `ml_models/models/rf_model.pkl` (subdirectory): Rejected — `predict.py` reads from the root of `ml_models/`, not the `models/` subdirectory.

---

### Q5: Does `predict.py` need changes?

**Decision**: Yes — one line update to `model_files` dict.

**Rationale**:
`predict.py` line 90: `model_files = {'rf': 'random_forest.pkl', 'svm': 'svm.pkl'}`.
After renaming the export to `rf_model.pkl`, `predict.py` must be updated to `'rf': 'rf_model.pkl'` to avoid a `FileNotFoundError` at startup.

No other changes to `predict.py` are needed — the validation, normalization, and inference logic are all correct.

---

### Q6: Are there existing model artifacts that might conflict?

**Decision**: No conflict — `ml_models/rf_model.pkl` does not currently exist. `ml_models/random_forest.pkl` will remain as a backup but will no longer be loaded by the inference pipeline after the `predict.py` update.

**Existing artifacts**:
- `backend/ml_models/random_forest.pkl` — Old model (from Feature 011 training run); no longer referenced after this feature
- `backend/ml_models/svm.pkl` — SVM model; unchanged by this feature
- `backend/ml_models/models/random_forest.pkl` — Even older model (from Feature 005); not referenced by the current inference pipeline

---

### Q7: Should training use raw or normalized features?

**Decision**: Raw features (no normalization) — consistent with current `train.py` and `predict.py` behavior.

**Rationale**:
`predict.py` line 155–157 contains an explicit comment:
```python
# NOTE: Current models were trained on RAW data (not normalized)
# TODO: Retrain models with normalized data for better generalization
# For now, pass raw data directly to match training pipeline
```
Retraining with normalization would require updating both the training script AND the inference path in `predict.py`. That is a separate concern out of scope for Feature 022. The feature requirement is to add GridSearchCV and export `rf_model.pkl` — not to switch from raw to normalized features.

---

### Q8: What is the model metrics output format?

**Decision**: Keep existing JSON metrics file alongside the model artifact, with an additional `best_params` key added for the GridSearchCV-selected hyperparameters.

**Rationale**:
`train.py` already saves a `_metrics.json` file alongside each model (via `save_model()`). Adding `best_params` to the metrics dict provides a record of which hyperparameters GridSearchCV selected, enabling reproducibility audits.

---

## Summary: What Changes

| File | Change |
|------|--------|
| `backend/apps/ml/train.py` | Add GridSearchCV to `train_random_forest()`: replace fixed-param RF with GridSearchCV; add `best_params` to metrics; change export filename from `random_forest.pkl` to `rf_model.pkl` |
| `backend/apps/ml/predict.py` | Update `model_files` dict: `'rf': 'rf_model.pkl'` (one line) |

## What Does NOT Change

| File | Reason |
|------|--------|
| `backend/apps/ml/feature_utils.py` | Already uses 6-axis FEATURE_COLUMNS |
| `backend/apps/ml/normalize.py` | No normalization change in scope |
| `backend/apps/ml/generate_params.py` | Already generates 6-axis params.json |
| `backend/ml_data/params.json` | Already 6-axis-only |
| `backend/ml_models/scripts/train_random_forest.py` | Deprecated script (expects 30 features); leave untouched |
| `backend/apps/ml/validate_models.py` | Already validates n_features_in_=6 |
| Any Django views, URLs, consumers | No API changes needed |
