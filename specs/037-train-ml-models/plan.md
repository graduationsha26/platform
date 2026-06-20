# Implementation Plan: Train ML Models on PSMAD Feature Dataset

**Branch**: `037-train-ml-models` | **Date**: 2026-04-07 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/037-train-ml-models/spec.md`

## Summary

Update the existing Random Forest and SVM training scripts to consume the newly generated PSMAD feature dataset (`ready_for_training_features.csv`, 42 features × 6,110 windows). Key changes: replace two-file data loading with single-CSV + stratified split, update feature count validation from 30 → 42, add `StandardScaler` to the SVM pipeline, save versioned output files (`rf_model_v1.pkl`, `svm_model_v1.pkl`, metrics JSONs), and delete all superseded model/metrics files after successful training.

## Technical Context

**Stack**: Python (standalone scripts) — no Django, no frontend involved  
**Libraries**: scikit-learn, pandas, numpy, joblib (all already in `backend/requirements.txt`)  
**Execution**: `py backend/ml_models/scripts/train_random_forest.py` (from repo root)  
**Input data**: `backend/ml_data/processed/ready_for_training_features.csv` (6,110 × 43)  
**Output models**: `backend/ml_models/models/rf_model_v1.pkl`, `svm_model_v1.pkl`  
**Output metrics**: `backend/ml_models/rf_model_metrics_v1.json`, `svm_model_metrics_v1.json`  
**Constraints**: Local development only; no Docker/CI/CD  
**Scale**: 6,110 training windows; RF GridSearch ~16 combos × 5 folds; SVM ~16 combos × 5 folds  

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Monorepo Architecture**: All changes within `backend/ml_models/scripts/` — inside monorepo `backend/` ✅
- [x] **Tech Stack Immutability**: scikit-learn, pandas, numpy, joblib — all already in constitutional stack ✅
- [x] **Database Strategy**: N/A — no database involved in this batch pipeline ✅
- [x] **Authentication**: N/A — standalone script, no user-facing endpoints ✅
- [x] **Security-First**: N/A — no secrets or credentials; reads/writes local files only ✅
- [x] **Real-time Requirements**: N/A — batch training script, not real-time ✅
- [x] **MQTT Integration**: N/A — no sensor data streaming ✅
- [x] **AI Model Serving**: Output `.pkl` files go to `backend/ml_models/models/` where the Django inference endpoint loads them ✅
- [x] **API Standards**: N/A — no API endpoints created or modified ✅
- [x] **Development Scope**: Local batch script only — no Docker/CI/CD/production configs ✅

**Result**: ✅ PASS — No constitutional violations.

## Project Structure

### Documentation (this feature)

```text
specs/037-train-ml-models/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code Changes

```text
backend/
└── ml_models/
    ├── scripts/
    │   ├── train_random_forest.py    [MODIFY] — new data loading, feature count, output name, cleanup
    │   └── train_svm.py              [MODIFY] — same + add StandardScaler
    ├── models/
    │   ├── rf_model_v1.pkl           [GENERATED OUTPUT]
    │   └── svm_model_v1.pkl          [GENERATED OUTPUT]
    ├── rf_model_metrics_v1.json      [GENERATED OUTPUT]
    └── svm_model_metrics_v1.json     [GENERATED OUTPUT]
```

**Files NOT modified**:
- `backend/ml_models/scripts/utils/model_io.py`
- `backend/ml_models/scripts/utils/evaluation.py`
- `backend/ml_models/scripts/compare_models.py`
- All `backend/ml_data/` scripts

## Implementation Design

### Changes to `train_random_forest.py`

#### 1. CLI argument: `--input` (replaces `--input-dir`)

```python
parser.add_argument(
    '--input',
    type=str,
    default='backend/ml_data/processed/ready_for_training_features.csv',
    help='Path to ready_for_training_features.csv'
)
```

#### 2. Data loading with stratified split

```python
from sklearn.model_selection import train_test_split

df = pd.read_csv(args.input)
# Validate: 43 columns, 'label' present
X = df.drop('label', axis=1).values   # shape: (6110, 42)
y = df['label'].values

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=args.random_state, stratify=y
)
```

#### 3. Feature count validation

```python
if X_train.shape[1] != 42:
    raise ValueError(f"Expected 42 features, got {X_train.shape[1]}")
```

#### 4. Model name and output paths

```python
MODEL_NAME = "rf_model_v1"
OUTPUT_DIR = "backend/ml_models/models"
METRICS_DIR = "backend/ml_models"  # parent directory, not models/
```

#### 5. Metadata includes `feature_count`

```python
training_info = {
    ...
    "feature_count": int(X_train.shape[1]),   # 42
    "dataset_source": "ready_for_training_features.csv",
    ...
}
```

#### 6. Cleanup function

```python
def cleanup_superseded_files():
    """Delete old model and metrics files after successful training."""
    # Files in backend/ml_models/models/
    models_dir_files = [
        "random_forest.pkl", "random_forest.json",
        "rf_model.pkl",       "rf_model.json",
    ]
    # Files in backend/ml_models/ (root-level)
    root_files = [
        "random_forest.pkl", "random_forest.json",
        "rf_model.pkl",       "rf_model.json",
        "rf_model_metrics.json",
    ]
    for fname in models_dir_files:
        path = os.path.join("backend/ml_models/models", fname)
        if os.path.exists(path):
            os.remove(path)
            logger.info(f"Removed: {path}")
    for fname in root_files:
        path = os.path.join("backend/ml_models", fname)
        if os.path.exists(path):
            os.remove(path)
            logger.info(f"Removed: {path}")
```

---

### Changes to `train_svm.py`

All changes from RF above, plus:

#### StandardScaler (SVM-specific)

```python
from sklearn.preprocessing import StandardScaler

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)   # fit on train only
X_test_scaled = scaler.transform(X_test)          # transform test (no leakage)
# Use X_train_scaled / X_test_scaled for training/evaluation
```

SVM cleanup targets: `svm_model.pkl`, `svm_model.json`, `svm_rbf.pkl`, `svm_rbf.json` (both in `models/` and root).

## Complexity Tracking

No constitutional violations — no complexity justification needed.
