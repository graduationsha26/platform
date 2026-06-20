# Research: Train ML Models on PSMAD Feature Dataset

**Branch**: `037-train-ml-models` | **Date**: 2026-04-07 | **Phase**: Phase 0

---

## R-001: Input Data Format Change

**Decision**: Load `ready_for_training_features.csv` as a single file and perform train/test split in-script using `sklearn.model_selection.train_test_split` (80/20, stratified by label).

**Rationale**: The existing scripts load two pre-split files (`train_features.csv`, `test_features.csv`) produced by the legacy `1_preprocess.py` pipeline. The new PSMAD output is a single unsplit CSV. Adding an inline split is simpler than pre-splitting the file separately.

**Alternatives considered**:
- Pre-split `ready_for_training_features.csv` into two files using a separate script — rejected (unnecessary complexity, extra file management)
- Add a new `load_and_split_csv()` function to `model_io.py` — considered, but inline split in the training scripts is cleaner since both scripts need identical logic

**Impact**: `--input-dir` CLI argument replaced by `--input` pointing directly to the single CSV file. Default: `backend/ml_data/processed/ready_for_training_features.csv`.

---

## R-002: Feature Count Validation

**Decision**: Update `validate_data()` in both training scripts to assert `X_train.shape[1] == 42` (not 30).

**Rationale**: The PSMAD pipeline produces 42 features per window (30 time-domain + 12 FFT tremor-band). Both training scripts currently hardcode `!= 30` validation. This check exists to catch data pipeline mistakes — it must be updated to 42 or training will fail immediately.

**No alternatives**: Hard validation on feature count is a correctness safeguard that must be kept and updated.

---

## R-003: Model Output Filenames and Locations

**Decision**:
- RF model → `backend/ml_models/models/rf_model_v1.pkl`
- SVM model → `backend/ml_models/models/svm_model_v1.pkl`
- RF metrics → `backend/ml_models/rf_model_metrics_v1.json`
- SVM metrics → `backend/ml_models/svm_model_metrics_v1.json`

**Rationale**: The `_v1` suffix follows versioning convention from the user request. The `.pkl` model files go into `models/` (where the inference API loads from). The metrics JSONs go into `backend/ml_models/` (where existing `rf_model_metrics.json` and `svm_model_metrics.json` live).

**Impact on `save_model()` in `model_io.py`**: The current function saves both `.pkl` and `.json` to the same `output_dir`. Since we need the metrics JSON one level up from the model file, the training scripts will save the `.pkl` via `save_model()` but write the metrics JSON separately to the parent directory. No changes needed to `model_io.py`.

---

## R-004: Old File Cleanup Scope

**Decision**: After each training script succeeds, delete the following old files:

From `backend/ml_models/models/`:
- `random_forest.pkl`, `random_forest.json`
- `rf_model.pkl`, `rf_model.json`
- `svm_model.pkl`, `svm_model.json`
- `svm_rbf.pkl`, `svm_rbf.json`

From `backend/ml_models/` (root):
- `random_forest.pkl`, `random_forest.json`
- `rf_model.pkl`, `rf_model.json`
- `svm_model.pkl`, `svm_model.json`
- `svm_rbf.pkl`, `svm_rbf.json`
- `rf_model_metrics.json`
- `svm_model_metrics.json`

**Rationale**: Inspection shows model files exist in both `ml_models/models/` AND `ml_models/` (root) — both sets must be cleaned. Deletion must occur only after new files are confirmed written. Missing files are silently skipped (no error). Each script only deletes its own model type (RF script deletes RF files, SVM script deletes SVM files), to avoid the RF script accidentally deleting the SVM model and vice versa.

---

## R-005: Metadata `feature_count` Field

**Decision**: Add `feature_count: 42` to the `training_info` dict passed to `create_metadata()`.

**Rationale**: The spec requires metrics files to record the feature count to distinguish PSMAD-trained models (42 features) from legacy-trained models (30 features). The `create_metadata()` function in `model_io.py` accepts a free-form `training_info` dict, so no signature changes are needed.

---

## R-006: Modifying Existing Scripts vs Creating New Ones

**Decision**: Modify the existing `train_random_forest.py` and `train_svm.py` in-place.

**Rationale**: The user explicitly requests updating the existing training scripts. The changes are minimal and self-contained:
- Replace data loading with single-CSV + split
- Update feature count validation
- Change model name and metrics output path
- Add cleanup step

Creating new scripts would duplicate ~80% of the code.

**Files NOT modified**: `model_io.py`, `evaluation.py` — their existing APIs are sufficient.

---

## R-007: SVM Scaling

**Decision**: Add `StandardScaler` to the SVM training pipeline (applied after train/test split, fitted only on training data).

**Rationale**: SVM with RBF kernel is sensitive to feature scale. The PSMAD dataset mixes raw integer IMU values (gyroscope: values like -2648, 7796) and computed floating-point features (FFT energy values like 0.001 – 500,000). Without scaling, features with large magnitudes will dominate the RBF kernel and performance will be poor. The Random Forest is scale-invariant and does not need scaling.

**Implementation**: `StandardScaler` fitted on `X_train` only, then `X_test` transformed (no data leakage).

---

## R-008: `run_all.py` and Pipeline Orchestrator

**Decision**: Leave `backend/ml_data/scripts/run_all.py` and `backend/ml_models/` orchestration scripts untouched.

**Rationale**: `run_all.py` chains stages 1→2→3 (preprocess → feature engineer → sequence prep) — it does not include model training. Training is run separately by invoking each training script. No changes needed.
