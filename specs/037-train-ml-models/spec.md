# Feature Specification: Train ML Models on PSMAD Feature Dataset

**Feature Branch**: `037-train-ml-models`  
**Created**: 2026-04-07  
**Status**: Draft  
**Input**: User description: "Training the Machine Learning models on the new PSMAD feature dataset, retrain RF and SVM, export versioned artifacts."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Retrain Random Forest on 42-Feature PSMAD Data (Priority: P1)

A data scientist updates the Random Forest training pipeline to use the newly generated PSMAD feature dataset (`ready_for_training_features.csv`, 42 features × 6,110 windows) and trains a new versioned model. The resulting model file and evaluation metrics are saved with the `_v1` suffix, and superseded model files are removed.

**Why this priority**: The Random Forest is the primary lightweight classifier used in real-time inference on the CMG control path. Getting it trained on the PSMAD dataset is the highest-value deliverable.

**Independent Test**: Can be fully tested by running the RF training script alone and verifying that `rf_model_v1.pkl` is produced in `ml_models/models/` and `rf_model_metrics_v1.json` is produced in `ml_models/`, with accuracy and F1-score reported.

**Acceptance Scenarios**:

1. **Given** `ready_for_training_features.csv` exists with 42 feature columns and a `label` column, **When** the RF training script is run, **Then** `rf_model_v1.pkl` is saved to `backend/ml_models/models/`
2. **Given** the RF model has been trained, **When** evaluated on the held-out test split, **Then** `rf_model_metrics_v1.json` is saved containing accuracy, F1-score, precision, recall, and best hyperparameters
3. **Given** old model files (`rf_model.pkl`, `rf_model.json`, `random_forest.pkl`, `random_forest.json`) exist, **When** the new training completes successfully, **Then** the old files are removed from `backend/ml_models/models/`
4. **Given** a training run is complete, **When** the metrics file is inspected, **Then** it records `feature_count: 42` confirming the model was trained on PSMAD 42-feature data

---

### User Story 2 — Retrain SVM on 42-Feature PSMAD Data (Priority: P2)

A data scientist updates the SVM training pipeline to accept 42 features and trains a new versioned SVM model on the same PSMAD dataset. The versioned artifacts are saved and old SVM files are removed.

**Why this priority**: SVM is the secondary classifier; it must also be retrained on the same dataset for consistency. Lower priority than RF because the real-time inference pipeline primarily uses RF.

**Independent Test**: Can be fully tested by running the SVM training script alone and verifying `svm_model_v1.pkl` in `ml_models/models/` and `svm_model_metrics_v1.json` in `ml_models/`, with the model accepting 42-feature input.

**Acceptance Scenarios**:

1. **Given** `ready_for_training_features.csv` exists, **When** the SVM training script is run, **Then** `svm_model_v1.pkl` is saved to `backend/ml_models/models/`
2. **Given** the SVM model has been trained, **When** evaluated on the test split, **Then** `svm_model_metrics_v1.json` is saved containing accuracy, F1-score, precision, recall, and best hyperparameters
3. **Given** old SVM files (`svm_model.pkl`, `svm_model.json`, `svm_rbf.pkl`, `svm_rbf.json`) exist, **When** new training completes successfully, **Then** old files are removed from `backend/ml_models/models/`
4. **Given** old metrics files (`svm_model_metrics.json`) exist, **When** new training completes successfully, **Then** old metrics files are removed from `backend/ml_models/`

---

### Edge Cases

- What happens when `ready_for_training_features.csv` is missing or empty? Training must fail fast with a clear error message, not silently produce a corrupt model.
- What happens when the input CSV does not have exactly 43 columns (42 features + label)? The script must validate column count and exit with a descriptive error.
- What happens if `backend/ml_models/models/` directory does not exist? It must be created automatically before saving model files.
- How does the script handle old model files that do not exist (first run or already deleted)? Deletion of non-existent files must be handled gracefully without errors.
- What happens if training produces a model but saving fails (disk full, permissions)? Old files must NOT be deleted until the new files are confirmed written successfully.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The training pipeline MUST accept `backend/ml_data/processed/ready_for_training_features.csv` as the input dataset (42 feature columns + 1 `label` column, 43 total)
- **FR-002**: The pipeline MUST validate that the input CSV has exactly 43 columns and contains a `label` column before any model fitting begins
- **FR-003**: The pipeline MUST split the dataset into a training set and a held-out test set using stratified sampling before any model fitting
- **FR-004**: The Random Forest training script MUST perform hyperparameter search with cross-validation and save the best model to `backend/ml_models/models/rf_model_v1.pkl`
- **FR-005**: The SVM training script MUST perform hyperparameter search with cross-validation and save the best model to `backend/ml_models/models/svm_model_v1.pkl`
- **FR-006**: Each training script MUST save evaluation metrics (accuracy, F1-score, precision, recall, confusion matrix, best hyperparameters, feature count, dataset size, training timestamp) to `backend/ml_models/rf_model_metrics_v1.json` or `backend/ml_models/svm_model_metrics_v1.json` respectively
- **FR-007**: After new model and metrics files are successfully written, the RF training script MUST delete: `rf_model.pkl`, `rf_model.json`, `random_forest.pkl`, `random_forest.json` from `backend/ml_models/models/` and `rf_model_metrics.json` from `backend/ml_models/`
- **FR-008**: After new model and metrics files are successfully written, the SVM training script MUST delete: `svm_model.pkl`, `svm_model.json`, `svm_rbf.pkl`, `svm_rbf.json` from `backend/ml_models/models/` and `svm_model_metrics.json` from `backend/ml_models/`
- **FR-009**: Each training script MUST print a completion summary to the console showing: dataset size, train/test split sizes, label distribution, best hyperparameters, test accuracy, test F1-score, and paths of saved model and metrics files

### Key Entities

- **TrainedModel**: A serialized classifier (Random Forest or SVM) trained on PSMAD 42-feature windows; identified by versioned filename (`rf_model_v1.pkl`, `svm_model_v1.pkl`); stored in `backend/ml_models/models/`
- **ModelMetrics**: A JSON document recording evaluation results for one trained model; includes accuracy, F1, precision, recall, confusion matrix, feature count (42), best hyperparameters, dataset info, and training timestamp; stored in `backend/ml_models/`
- **FeatureDataset**: The input CSV produced by the PSMAD pipeline; 6,110 rows × 43 columns; located at `backend/ml_data/processed/ready_for_training_features.csv`
- **SupersededArtifacts**: Old model `.pkl`/`.json` files from previous training runs to be removed after successful retraining

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Both `rf_model_v1.pkl` and `svm_model_v1.pkl` exist in `backend/ml_models/models/` after running the respective scripts
- **SC-002**: Both `rf_model_metrics_v1.json` and `svm_model_metrics_v1.json` exist in `backend/ml_models/` and contain non-empty accuracy, F1-score, precision, recall, and hyperparameter fields
- **SC-003**: All 8 superseded model files are absent from `backend/ml_models/models/` after training: `rf_model.pkl`, `rf_model.json`, `random_forest.pkl`, `random_forest.json`, `svm_model.pkl`, `svm_model.json`, `svm_rbf.pkl`, `svm_rbf.json`
- **SC-004**: Superseded metrics files `rf_model_metrics.json` and `svm_model_metrics.json` are absent from `backend/ml_models/` after training
- **SC-005**: The Random Forest model achieves at least 85% test accuracy on the PSMAD held-out test set
- **SC-006**: The SVM model achieves at least 75% test accuracy on the PSMAD held-out test set
- **SC-007**: Both metrics JSON files record `feature_count: 42`, confirming models were trained on the 42-feature PSMAD dataset

## Dependencies

- `backend/ml_data/processed/ready_for_training_features.csv` must exist (generated by feature 036-psmad-data-prep)
- Existing training scripts in `backend/ml_models/scripts/` (`train_random_forest.py`, `train_svm.py`) are the base to be updated — they currently expect 30-feature input

## Assumptions

- The `label` column contains only values 0 (Control) and 1 (Parkinson)
- The existing 80/20 stratified train/test split strategy is appropriate for the PSMAD dataset
- Existing cross-validation strategy (StratifiedKFold, k=5) and hyperparameter search grids are retained
- Metrics JSON files are saved to `backend/ml_models/` (same location as the current `rf_model_metrics.json`)
- "Root directory" in the user request refers to `backend/ml_models/` (where current metrics files live)

## Out of Scope

- Training deep learning models (LSTM, CNN, Transformer)
- Updating the real-time inference endpoint (`/api/predict/`) to load `v1` models
- Model comparison reports or ensemble methods
- Frontend or API changes of any kind
- Hyperparameter range modifications
