# Feature Specification: Machine Learning Models Training

**Feature Branch**: `005-ml-models`
**Created**: 2026-02-15
**Status**: Draft
**Input**: User description: "2.2 Machine Learning Models - 2.2.1 Random Forest Classifier - Train RF with GridSearchCV (n_estimators, max_depth). Target ≥95% accuracy. Export .pkl&.json. 2.2.2 SVM Classifier - Train SVM (RBF kernel) with hyperparameter tuning. Export .pkl&.json."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Random Forest Classifier Training (Priority: P1) 🎯 MVP

A data scientist or ML engineer needs to train a Random Forest classifier on the prepared feature data to detect Parkinson's tremors with high accuracy. The trained model will be used for real-time tremor classification in the TremoAI platform.

**Why this priority**: Random Forest is the most robust and widely-used traditional ML algorithm for this type of classification task. It handles non-linear relationships well, is less prone to overfitting, and provides feature importance insights. This is the MVP model that must work before exploring other algorithms.

**Independent Test**: Can be fully tested by running the training script with the feature matrices from Feature 004, evaluating model performance on the test set, and verifying that the exported .pkl model can make predictions on new data. Delivers a production-ready tremor detection model achieving ≥95% accuracy.

**Acceptance Scenarios**:

1. **Given** train_features.csv and test_features.csv exist (outputs from Feature 004), **When** the Random Forest training script runs, **Then** it performs GridSearchCV across n_estimators and max_depth parameters and identifies the best hyperparameter combination
2. **Given** GridSearchCV completes, **When** the best model is evaluated on the test set, **Then** it achieves ≥95% accuracy along with detailed metrics (precision, recall, F1-score, confusion matrix)
3. **Given** model training succeeds, **When** the export process runs, **Then** it saves the trained model as random_forest.pkl and exports metadata (hyperparameters, performance metrics, training timestamp) to random_forest.json
4. **Given** a saved .pkl model exists, **When** it is loaded and used for prediction on new feature data, **Then** it produces tremor classifications (0 or 1) with consistent performance
5. **Given** multiple training runs execute, **When** the same random seed is used, **Then** results are reproducible with identical accuracy scores

---

### User Story 2 - SVM Classifier Training (Priority: P2)

A data scientist needs to train an SVM (Support Vector Machine) classifier with RBF kernel as an alternative model for tremor detection, enabling model comparison and ensemble opportunities.

**Why this priority**: SVM with RBF kernel is highly effective for high-dimensional feature spaces and can capture complex decision boundaries. Having multiple trained models allows for:
- Performance comparison to identify the best model
- Ensemble methods (voting, stacking) for improved accuracy
- Fallback options if one model fails in production

**Independent Test**: Can be fully tested by running the SVM training script with the same feature matrices, evaluating performance independently, and exporting the model. Does not depend on User Story 1 completing - both models can be trained in parallel. Delivers a second production-ready model with different strengths than Random Forest.

**Acceptance Scenarios**:

1. **Given** train_features.csv and test_features.csv exist, **When** the SVM training script runs, **Then** it performs GridSearchCV across C and gamma parameters for the RBF kernel and identifies the best hyperparameter combination
2. **Given** GridSearchCV completes, **When** the best SVM model is evaluated on the test set, **Then** it achieves ≥95% accuracy with detailed performance metrics
3. **Given** model training succeeds, **When** the export process runs, **Then** it saves the trained model as svm_rbf.pkl and exports metadata to svm_rbf.json including kernel type, hyperparameters, and performance metrics
4. **Given** both Random Forest and SVM models are trained, **When** their performance is compared, **Then** a comparison report shows accuracy, precision, recall, F1-score, and training time for both models
5. **Given** a saved SVM .pkl model exists, **When** it is loaded and used for prediction on new feature data, **Then** it produces tremor classifications with performance matching the test set evaluation

---

### Edge Cases

- **What happens when GridSearchCV finds multiple parameter combinations with identical performance?** System should select based on a tie-breaking rule (e.g., prefer simpler model with fewer parameters or faster inference time)
- **What happens when no hyperparameter combination achieves the ≥95% accuracy threshold?** Training script should report the best achieved accuracy, log a warning, and still export the model with a flag indicating it didn't meet the target
- **What happens when feature data is missing or corrupted?** Training script should validate input files exist, have expected shape and column names, and contain no NaN/Inf values before starting training
- **What happens when the same model is trained multiple times?** Each training run should generate timestamped output files to avoid overwriting previous models, enabling model versioning and history tracking
- **What happens when GridSearchCV runs out of memory?** System should provide clear error messages indicating insufficient memory and suggest reducing the parameter search space or using fewer cross-validation folds
- **What happens when models are loaded in a different environment?** Exported .json metadata should include scikit-learn version and Python version to detect compatibility issues when loading models

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST load training and test feature matrices from Feature 004 outputs (train_features.csv, test_features.csv) and validate data integrity before training
- **FR-002**: System MUST train a Random Forest classifier using scikit-learn with GridSearchCV for hyperparameter tuning across n_estimators and max_depth parameters
- **FR-003**: System MUST train an SVM classifier with RBF kernel using GridSearchCV for hyperparameter tuning across C (regularization) and gamma (kernel coefficient) parameters
- **FR-004**: System MUST use stratified k-fold cross-validation (k=5) during GridSearchCV to ensure robust model evaluation and prevent overfitting
- **FR-005**: System MUST evaluate trained models on the held-out test set and compute accuracy, precision, recall, F1-score, and confusion matrix
- **FR-006**: System MUST achieve ≥95% accuracy on the test set as the success threshold for both models
- **FR-007**: System MUST export trained models as .pkl files (pickled scikit-learn objects) for deployment
- **FR-008**: System MUST export model metadata as .json files including hyperparameters, performance metrics, training timestamp, scikit-learn version, and Python version
- **FR-009**: System MUST ensure reproducibility by using a fixed random seed (random_state=42) across train/test split, cross-validation, and model initialization
- **FR-010**: System MUST provide detailed logging showing GridSearchCV progress, best parameters found, and final model performance
- **FR-011**: System MUST validate that exported .pkl models can be successfully loaded and used for prediction on new data
- **FR-012**: System MUST generate a model comparison report showing performance metrics for both Random Forest and SVM models side-by-side

### Key Entities

- **Trained Model**: A scikit-learn classifier (RandomForestClassifier or SVC) that has been fitted on training data, validated, and serialized. Contains learned decision boundaries and can predict tremor classes for new feature vectors.
- **Model Metadata**: A JSON document containing hyperparameters (e.g., n_estimators=100, max_depth=20), performance metrics (accuracy, precision, recall, F1-score), training timestamp, environment info (scikit-learn version, Python version), and cross-validation results.
- **Feature Matrix**: Input data from Feature 004 containing 30 statistical features per window (5 features × 6 axes) plus label column. Train set has ~446 windows, test set has ~110 windows.
- **GridSearch Results**: The complete hyperparameter search results including all tested combinations, their cross-validation scores, and the best parameter set identified.
- **Confusion Matrix**: A 2×2 matrix showing true positives, true negatives, false positives, and false negatives for tremor detection (classes 0 and 1).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Both Random Forest and SVM models achieve ≥95% accuracy on the held-out test set (matching or exceeding the performance target)
- **SC-002**: Model training completes within 10 minutes on a standard laptop (Random Forest and SVM combined), enabling rapid experimentation
- **SC-003**: Exported models can be loaded and used for predictions in under 1 second (inference time for a single prediction), ensuring real-time usability in the TremoAI platform
- **SC-004**: Training results are reproducible - running the same script twice with the same random seed produces identical accuracy scores (within 0.01% tolerance)
- **SC-005**: All model performance metrics (precision, recall, F1-score) are ≥0.90 for both classes (no tremor and tremor), ensuring balanced performance
- **SC-006**: Exported .json metadata contains all necessary information to reproduce the training process and understand model behavior without re-running training
- **SC-007**: Models successfully classify at least 95 out of 100 test samples correctly, demonstrating reliable tremor detection suitable for clinical use

### Performance Targets

- GridSearchCV explores at least 12 hyperparameter combinations for Random Forest (e.g., 3 values for n_estimators × 4 values for max_depth)
- GridSearchCV explores at least 16 hyperparameter combinations for SVM (e.g., 4 values for C × 4 values for gamma)
- Cross-validation uses 5 folds to balance validation robustness and training time
- Trained model files (.pkl) are under 10 MB each for efficient storage and deployment
- Metadata files (.json) are human-readable and under 10 KB each

## Assumptions

- **Data Availability**: Feature matrices from Feature 004 (train_features.csv, test_features.csv) are available and correctly formatted (30 feature columns + 1 label column)
- **Class Balance**: The training data has reasonable class balance (approximately 50/50 split between no tremor and tremor) enabling effective model training
- **Computational Resources**: Training environment has at least 8 GB RAM and 4 CPU cores to support GridSearchCV parallel processing
- **Python Environment**: Python 3.8+ with scikit-learn 1.3.0+ is available (from Feature 004 dependencies)
- **Model Persistence**: The .pkl serialization format is acceptable for deployment (no security concerns about unpickling in production)
- **Binary Classification**: The task remains binary classification (0=no tremor, 1=tremor) as defined in Feature 004
- **Hyperparameter Search Space**: Default search spaces are reasonable:
  - Random Forest: n_estimators in [50, 100, 200, 300], max_depth in [10, 20, 30, None]
  - SVM: C in [0.1, 1, 10, 100], gamma in [0.001, 0.01, 0.1, 1]
- **Cross-Validation Folds**: 5-fold cross-validation provides sufficient validation without excessive computation time
- **Random Seed**: Using random_state=42 (same as Feature 004) ensures consistency across the entire ML pipeline

## Dependencies

- **Feature 004 (ML/DL Data Preparation)**: MUST be complete before this feature can start. Requires train_features.csv and test_features.csv outputs.
- **Python ML Libraries**: Requires scikit-learn ≥1.3.0 (already added in Feature 004 requirements.txt)
- **Storage**: Requires backend/ml_models/ directory for storing trained models and metadata
- **Git Ignore**: Should exclude large .pkl files from version control (add to .gitignore)

## Out of Scope

- **Deep Learning Models**: LSTM, CNN, and hybrid models are covered in Feature 006, not this feature
- **Model Deployment**: Integration with Django REST API endpoints for real-time prediction is a separate feature (Feature 007+)
- **Model Monitoring**: Performance tracking, drift detection, and retraining triggers are future features
- **Feature Selection**: Advanced feature engineering, dimensionality reduction (PCA), and feature importance analysis beyond basic GridSearchCV
- **Ensemble Methods**: Voting classifiers, stacking, and boosting models (e.g., XGBoost) are separate features (Feature 008+)
- **Model Explainability**: SHAP values, LIME, and feature importance visualizations are separate features
- **Online Learning**: Incremental learning and model updates with new data are out of scope
- **Multi-class Classification**: Extension beyond binary classification (e.g., tremor severity levels) is not included
- **Model Compression**: Quantization, pruning, and other optimization techniques for edge deployment are future work
