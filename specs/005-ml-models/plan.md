# Implementation Plan: Machine Learning Models Training

**Branch**: `005-ml-models` | **Date**: 2026-02-15 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/005-ml-models/spec.md`

## Summary

Train Random Forest and SVM classifiers for Parkinson's tremor detection using feature matrices prepared in Feature 004. Implement GridSearchCV hyperparameter tuning to achieve ≥95% accuracy. Export trained models as .pkl files (scikit-learn serialized objects) and .json metadata files (hyperparameters, performance metrics, training info). Create comparison report showing performance metrics for both models.

**Technical Approach**: Implement offline training scripts using scikit-learn's GridSearchCV with stratified 5-fold cross-validation. Random Forest tuning focuses on n_estimators and max_depth; SVM with RBF kernel tunes C and gamma. Evaluation uses held-out test set from Feature 004 with comprehensive metrics (accuracy, precision, recall, F1-score, confusion matrix). Model persistence via joblib, metadata export via json module.

## Technical Context

**Backend Stack**: Python 3.8+ with scikit-learn ≥1.3.0 (no Django/web framework needed for training scripts)
**ML Libraries**: scikit-learn ≥1.3.0, joblib (bundled with scikit-learn), json (standard library)
**Data Dependencies**: Feature 004 outputs (train_features.csv, test_features.csv from backend/ml_data/processed/)
**Model Storage**: backend/ml_models/ directory for trained .pkl and .json files
**Testing**: Manual validation scripts to verify model loading and prediction
**Project Type**: ML pipeline (backend/ml_models/ - offline batch training, not web API)
**Performance Goals**:
- Model training completes within 10 minutes for both models combined
- ≥95% accuracy on test set for both Random Forest and SVM
- Inference time <1 second per prediction when models are loaded
**Constraints**:
- Local development only (no deployment infrastructure)
- Models trained offline (batch processing), not real-time training
- 8 GB RAM minimum for GridSearchCV parallel processing
**Scale/Scope**:
- Binary classification (2 classes: no tremor, tremor)
- ~446 training windows, ~110 test windows (from Feature 004)
- GridSearchCV explores 12-16 hyperparameter combinations per model
- 5-fold cross-validation for robust evaluation

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Validate this feature against `.specify/memory/constitution.md` principles:

- [X] **Monorepo Architecture**: Feature fits in `backend/ml_models/` structure (within backend/ directory)
- [X] **Tech Stack Immutability**: Uses scikit-learn (already approved in Feature 004), joblib (bundled with scikit-learn), no new frameworks
- [X] **Database Strategy**: No database needed for offline training scripts (loads CSV files, writes .pkl/.json files)
- [X] **Authentication**: No authentication needed (offline batch processing, not web API)
- [X] **Security-First**: No credentials needed for training scripts (loads local files)
- [X] **Real-time Requirements**: Not applicable (offline training, not live data streaming)
- [X] **MQTT Integration**: Not applicable (uses pre-processed feature files, not raw sensor data)
- [X] **AI Model Serving**: Produces .pkl model files that WILL be served via Django in future features (Feature 007+)
- [X] **API Standards**: Not applicable (training scripts, not REST API endpoints)
- [X] **Development Scope**: Local development only (training on local machine, no Docker/CI/CD)

**Result**: ✅ PASS - All principles satisfied. Feature 005 trains models offline, future features (007+) will serve them via Django REST API.

**Note**: This feature focuses on MODEL TRAINING (offline batch processing). Model DEPLOYMENT (serving predictions via Django REST API) is explicitly out of scope and will be addressed in Feature 007+.

## Project Structure

### Documentation (this feature)

```text
specs/005-ml-models/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output - minimal (standard ML practices)
├── data-model.md        # Phase 1 output - entities (Trained Model, Metadata, etc.)
├── quickstart.md        # Phase 1 output - training and validation scenarios
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

**Note**: No contracts/ directory needed - this feature has no API endpoints (offline training scripts).

### Source Code (repository root)

```text
backend/
├── ml_models/                      # ML model training pipeline (NEW - created by this feature)
│   ├── scripts/
│   │   ├── train_random_forest.py  # US1: Train RF with GridSearchCV, export .pkl/.json
│   │   ├── train_svm.py            # US2: Train SVM with GridSearchCV, export .pkl/.json
│   │   ├── compare_models.py       # Generate comparison report for RF vs SVM
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── model_io.py         # Save/load .pkl (joblib) and .json (metadata)
│   │       └── evaluation.py       # Compute metrics (accuracy, precision, recall, F1, confusion matrix)
│   ├── models/                     # Output: trained model files (gitignored)
│   │   ├── .gitkeep                # Preserve empty directory in git
│   │   ├── random_forest.pkl       # Trained RF model (created by train_random_forest.py)
│   │   ├── random_forest.json      # RF metadata (hyperparams, metrics, timestamp)
│   │   ├── svm_rbf.pkl             # Trained SVM model (created by train_svm.py)
│   │   ├── svm_rbf.json            # SVM metadata
│   │   └── comparison_report.txt   # Performance comparison (created by compare_models.py)
│   └── README.md                   # Usage instructions, model overview
│
├── ml_data/                        # From Feature 004 (data dependency)
│   └── processed/
│       ├── train_features.csv      # Input: 30 features + label (446 windows)
│       └── test_features.csv       # Input: 30 features + label (110 windows)
│
└── requirements.txt                # Add joblib if not already present (usually bundled with sklearn)

.gitignore                          # Add backend/ml_models/models/*.pkl and *.json (exclude large model files)
```

**Structure Decision**:

- **backend/ml_models/**: New directory parallel to ml_data/ for model training pipeline
- **scripts/**: Training scripts - each user story gets its own script for independent execution
  - `train_random_forest.py`: Implements US1 (RF training with GridSearchCV)
  - `train_svm.py`: Implements US2 (SVM training with GridSearchCV)
  - `compare_models.py`: Implements model comparison functionality (FR-012)
- **utils/**: Shared utilities for model I/O and evaluation (reused across training scripts)
  - `model_io.py`: save_model(model, metadata, name), load_model(name) - abstracts joblib and json operations
  - `evaluation.py`: evaluate_model(model, X_test, y_test) - returns all metrics (accuracy, precision, recall, F1, confusion matrix)
- **models/**: Output directory for trained models - gitignored to avoid committing large .pkl files
- **README.md**: Documents usage (python backend/ml_models/scripts/train_random_forest.py), model overview, hyperparameter tuning details

**Data Flow**:
1. Load train_features.csv and test_features.csv from backend/ml_data/processed/
2. Split features (X) and labels (y)
3. GridSearchCV with 5-fold cross-validation on training set
4. Evaluate best model on test set
5. Export model to backend/ml_models/models/<model_name>.pkl
6. Export metadata to backend/ml_models/models/<model_name>.json

**File Naming Convention**: Timestamp-based versioning for model files (e.g., random_forest_20260215_143022.pkl) to enable model history tracking (edge case: same model trained multiple times).

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations - Constitution Check passed all items.

## Phase 0: Research & Unknowns

**Status**: ✅ Complete - No significant unknowns requiring research

All technical decisions are straightforward applications of standard scikit-learn practices:

- **GridSearchCV**: Standard scikit-learn tool for hyperparameter tuning
- **Random Forest hyperparameters**: n_estimators (tree count), max_depth (tree depth) - well-established defaults
- **SVM with RBF kernel**: C (regularization), gamma (kernel coefficient) - standard tuning approach
- **Model serialization**: joblib (scikit-learn recommended) for .pkl files
- **Cross-validation**: 5-fold stratified (standard for classification)
- **Performance metrics**: sklearn.metrics module (accuracy_score, precision_recall_fscore_support, confusion_matrix)

See [research.md](./research.md) for detailed decisions and rationale.

## Phase 1: Design Artifacts

**Status**: ✅ Complete

Generated artifacts:
- [data-model.md](./data-model.md) - Entities: Trained Model, Model Metadata, GridSearch Results, Confusion Matrix
- [quickstart.md](./quickstart.md) - Training scenarios, model validation tests, comparison workflows

**Note**: No contracts/ directory - this feature has no API endpoints (offline training scripts, not web API).

## Implementation Notes

### User Story 1: Random Forest Classifier (Priority P1 - MVP)

**Hyperparameter Search Space**:
- n_estimators: [50, 100, 200, 300] (number of trees in the forest)
- max_depth: [10, 20, 30, None] (maximum depth of trees, None = unlimited)
- **GridSearchCV**: 4 × 4 = 16 combinations
- **Cross-validation**: 5-fold stratified (preserves class distribution)
- **Scoring metric**: accuracy (aligns with ≥95% success criterion)
- **Parallel processing**: n_jobs=-1 (use all CPU cores)

**Output Files**:
- `random_forest.pkl`: Serialized RandomForestClassifier object (joblib.dump)
- `random_forest.json`: Metadata including:
  ```json
  {
    "model_type": "RandomForestClassifier",
    "hyperparameters": {"n_estimators": 200, "max_depth": 20, ...},
    "performance_metrics": {
      "accuracy": 0.964,
      "precision": 0.957,
      "recall": 0.971,
      "f1_score": 0.964,
      "confusion_matrix": [[53, 3], [2, 52]]
    },
    "cross_validation": {
      "cv_scores": [0.95, 0.96, 0.97, 0.94, 0.96],
      "cv_mean": 0.956,
      "cv_std": 0.010
    },
    "training_info": {
      "timestamp": "2026-02-15T14:30:22",
      "training_time_seconds": 127.3,
      "sklearn_version": "1.3.2",
      "python_version": "3.11.5",
      "random_state": 42
    }
  }
  ```

**Success Validation**: Model achieves ≥95% accuracy on test set. If not, log warning and still export model with flag indicating threshold not met.

### User Story 2: SVM Classifier (Priority P2)

**Hyperparameter Search Space**:
- C: [0.1, 1, 10, 100] (regularization parameter)
- gamma: [0.001, 0.01, 0.1, 1] (kernel coefficient for RBF)
- kernel: 'rbf' (fixed - Radial Basis Function)
- **GridSearchCV**: 4 × 4 = 16 combinations
- **Cross-validation**: 5-fold stratified
- **Scoring metric**: accuracy
- **Parallel processing**: n_jobs=-1

**Output Files**:
- `svm_rbf.pkl`: Serialized SVC object
- `svm_rbf.json`: Metadata (same structure as RF, includes kernel type)

**Success Validation**: Model achieves ≥95% accuracy on test set.

### Model Comparison (FR-012)

**Script**: `compare_models.py`

**Output**: `comparison_report.txt` with side-by-side comparison:

```text
======================================================================
MODEL COMPARISON REPORT
======================================================================
Generated: 2026-02-15 14:35:10

Random Forest Classifier:
  Accuracy:   96.4%
  Precision:  95.7%
  Recall:     97.1%
  F1-Score:   96.4%
  Training Time: 127.3 seconds

SVM (RBF kernel):
  Accuracy:   97.3%
  Precision:  96.8%
  Recall:     97.8%
  F1-Score:   97.3%
  Training Time: 89.7 seconds

Best Model: SVM (RBF kernel) [97.3% accuracy]

Recommendation: SVM achieves higher accuracy with faster training time.
Consider Random Forest if interpretability (feature importance) is needed.
======================================================================
```

**Usage**: After both models are trained, run `python backend/ml_models/scripts/compare_models.py` to generate the comparison report.

### Reproducibility (FR-009)

All scripts must use `random_state=42` for:
- train_test_split (already done in Feature 004)
- GridSearchCV (cv parameter uses StratifiedKFold with random_state=42)
- RandomForestClassifier(random_state=42)
- SVC (deterministic when random_state not needed for RBF kernel)

### Error Handling

Each training script must validate:
1. Input files exist (train_features.csv, test_features.csv)
2. Files have expected shape (30 feature columns + 1 label column)
3. No NaN/Inf values in features
4. Labels are binary (0 or 1)
5. Output directory exists (backend/ml_models/models/)

If validation fails, script should:
- Print clear error message indicating which check failed
- Provide guidance on how to fix (e.g., "Run Feature 004 data preparation pipeline first")
- Exit with non-zero status code

### Logging

Each training script should log:
- Start time
- Data loading progress (file paths, shapes)
- GridSearchCV progress (parameter combinations tested)
- Best parameters found
- Cross-validation scores (mean ± std)
- Test set evaluation metrics
- Model export paths
- Total training time
- Success/failure status

**Log Level**: INFO for normal operation, WARNING if ≥95% threshold not met, ERROR for validation failures.

## Next Steps

After implementation (`/speckit.tasks` → `/speckit.implement`):

1. **Immediate**: Test both models independently (run training scripts, verify outputs)
2. **Validation**: Run comparison report, confirm both models meet ≥95% accuracy
3. **Future Feature 006**: Train deep learning models (LSTM, CNN) on sequence data from Feature 004
4. **Future Feature 007**: Deploy trained models via Django REST API for real-time prediction
5. **Future Feature 008**: Ensemble methods (voting, stacking) using RF + SVM + DL models

## Dependencies

- **Feature 004 (ML/DL Data Preparation)**: MUST be complete - requires train_features.csv and test_features.csv
- **Python 3.8+**: Already installed
- **scikit-learn ≥1.3.0**: Already added to requirements.txt in Feature 004
- **joblib**: Usually bundled with scikit-learn, verify availability or add to requirements.txt

## Risk Assessment

**Low Risk**:
- Standard scikit-learn operations (well-documented, stable)
- No external APIs or network dependencies
- No database dependencies
- Deterministic with random_state=42

**Potential Issues**:
- **Insufficient memory for GridSearchCV**: Mitigated by limiting parameter search space, reducing cv folds if needed
- **Training time exceeds 10 minutes**: Mitigated by parallel processing (n_jobs=-1), reasonable search space
- **Models don't reach ≥95% accuracy**: Acceptable if logged and documented - may indicate feature engineering improvements needed

**Mitigation Strategy**: If training takes too long or memory issues occur, reduce search space (fewer parameter values) or use RandomizedSearchCV instead of GridSearchCV.
