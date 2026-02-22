# Data Model: Machine Learning Models Training

**Feature**: 005-ml-models
**Date**: 2026-02-15
**Context**: Entities for ML model training, evaluation, and persistence

## Entity Overview

This feature deals with **trained models as data artifacts**, not database entities. All entities are serialized to files (.pkl and .json) rather than stored in PostgreSQL.

**Storage Location**: `backend/ml_models/models/`
**Persistence Format**: Binary (.pkl via joblib) + Text (.json via json module)

## Entities

### 1. Trained Model

**Description**: A scikit-learn classifier (RandomForestClassifier or SVC) that has been trained on feature data, evaluated, and serialized for deployment.

**Attributes**:
- **model_object**: The actual scikit-learn estimator instance (RandomForestClassifier or SVC)
- **model_type**: String identifier ("RandomForestClassifier" or "SVC")
- **best_parameters**: Dict of optimal hyperparameters found by GridSearchCV
  - Random Forest: `{"n_estimators": int, "max_depth": int or None, ...}`
  - SVM: `{"C": float, "gamma": float, "kernel": "rbf", ...}`
- **feature_names**: List of 30 feature column names (from Feature 004: RMS_aX, mean_aX, etc.)
- **n_features**: Integer = 30 (expected number of features)
- **classes**: Array [0, 1] (binary classification: no tremor, tremor)

**Persistence**:
- **File**: `<model_name>.pkl` (e.g., `random_forest.pkl`, `svm_rbf.pkl`)
- **Format**: Joblib-serialized binary
- **Size**: Expected <10 MB per model
- **Loading**: `model = joblib.load(file_path)`
- **Usage**: `predictions = model.predict(X_new)` where X_new has shape (n_samples, 30)

**Relationships**:
- **Has one** Model Metadata (stored separately in .json file)
- **Produced by** GridSearch Results (search process that identified best_parameters)
- **Trained on** Feature Matrix (from Feature 004: train_features.csv)
- **Evaluated with** Confusion Matrix (test set evaluation)

**Validation Rules**:
- Must be a fitted scikit-learn estimator (has `predict` method)
- Must accept input shape (*, 30) - 30 features
- Must output binary predictions {0, 1}
- Must be serializable via joblib.dump

**State Transitions**:
1. **Untrained** → GridSearchCV fits on training data → **Trained**
2. **Trained** → Evaluated on test set → **Validated** (if metrics meet thresholds)
3. **Validated** → Serialized to .pkl → **Persisted**
4. **Persisted** → Loaded from .pkl → **Deployed** (in memory, ready for predictions)

---

### 2. Model Metadata

**Description**: A JSON document containing all information about the trained model except the model object itself - hyperparameters, performance metrics, training environment, and timestamps.

**Attributes**:

**Identification**:
- **model_name**: String (e.g., "random_forest", "svm_rbf")
- **model_type**: String (e.g., "RandomForestClassifier", "SVC")

**Hyperparameters** (Dict):
- Random Forest: `{"n_estimators": int, "max_depth": int or None, "random_state": 42, ...}`
- SVM: `{"C": float, "gamma": float, "kernel": "rbf", "random_state": 42 (if applicable), ...}`

**Performance Metrics** (Dict):
- **accuracy**: Float (e.g., 0.964 = 96.4%)
- **precision**: Float (macro average for binary classification)
- **recall**: Float (macro average)
- **f1_score**: Float (macro average)
- **confusion_matrix**: 2D array [[TN, FP], [FN, TP]]
  - TN = True Negatives (predicted no tremor, actual no tremor)
  - FP = False Positives (predicted tremor, actual no tremor)
  - FN = False Negatives (predicted no tremor, actual tremor)
  - TP = True Positives (predicted tremor, actual tremor)
- **meets_threshold**: Boolean (True if accuracy ≥ 0.95, False otherwise)

**Cross-Validation Results** (Dict):
- **cv_scores**: Array of 5 floats (accuracy for each fold)
- **cv_mean**: Float (mean of cv_scores)
- **cv_std**: Float (standard deviation of cv_scores)

**Training Information** (Dict):
- **timestamp**: ISO 8601 string (e.g., "2026-02-15T14:30:22")
- **training_time_seconds**: Float (elapsed time for GridSearchCV + final fit)
- **training_samples**: Integer (e.g., 446)
- **test_samples**: Integer (e.g., 110)
- **sklearn_version**: String (e.g., "1.3.2")
- **python_version**: String (e.g., "3.11.5")
- **random_state**: Integer (42 for reproducibility)
- **data_source**: String ("Feature 004: train_features.csv, test_features.csv")

**Persistence**:
- **File**: `<model_name>.json` (same base name as .pkl file)
- **Format**: JSON (human-readable text)
- **Size**: Expected <10 KB
- **Encoding**: UTF-8

**Relationships**:
- **Belongs to** one Trained Model (1-to-1 relationship via filename)
- **Summarizes** GridSearch Results (best parameters from search)
- **Contains** Confusion Matrix (as nested array in performance_metrics)

**Validation Rules**:
- All required fields must be present (no missing keys)
- accuracy, precision, recall, f1_score must be in range [0.0, 1.0]
- confusion_matrix must be 2×2 array with non-negative integers
- timestamp must be valid ISO 8601 format
- sklearn_version and python_version must match training environment

**Example**:
```json
{
  "model_name": "random_forest",
  "model_type": "RandomForestClassifier",
  "hyperparameters": {
    "n_estimators": 200,
    "max_depth": 20,
    "random_state": 42,
    "min_samples_split": 2,
    "min_samples_leaf": 1,
    "max_features": "sqrt"
  },
  "performance_metrics": {
    "accuracy": 0.964,
    "precision": 0.957,
    "recall": 0.971,
    "f1_score": 0.964,
    "confusion_matrix": [[53, 3], [2, 52]],
    "meets_threshold": true
  },
  "cross_validation": {
    "cv_scores": [0.95, 0.96, 0.97, 0.94, 0.96],
    "cv_mean": 0.956,
    "cv_std": 0.010
  },
  "training_info": {
    "timestamp": "2026-02-15T14:30:22",
    "training_time_seconds": 127.3,
    "training_samples": 446,
    "test_samples": 110,
    "sklearn_version": "1.3.2",
    "python_version": "3.11.5",
    "random_state": 42,
    "data_source": "Feature 004: train_features.csv, test_features.csv"
  }
}
```

---

### 3. GridSearch Results

**Description**: The complete hyperparameter search results produced by GridSearchCV, including all tested parameter combinations and their cross-validation scores.

**Attributes**:
- **param_grid**: Dict defining search space (e.g., `{"n_estimators": [50, 100, 200, 300], "max_depth": [10, 20, 30, None]}`)
- **cv_results**: Dict containing arrays for each parameter combination:
  - **params**: List of dicts, each representing one parameter combination tested
  - **mean_test_score**: Array of mean CV scores for each combination
  - **std_test_score**: Array of standard deviations for each combination
  - **rank_test_score**: Array of rankings (1 = best)
- **best_params**: Dict of optimal parameters (highest mean_test_score)
- **best_score**: Float, the best mean CV score achieved
- **best_index**: Integer, index of best combination in cv_results arrays

**Persistence**:
- Not persisted separately - best_params included in Model Metadata
- Available during training for debugging/analysis via GridSearchCV.cv_results_ attribute
- Could be exported to separate .json file if detailed search history needed (future enhancement)

**Relationships**:
- **Produces** one Trained Model (the model trained with best_params)
- **Summarized in** Model Metadata (best_params and cross_validation fields)

**Usage**:
- Used internally by training scripts to identify optimal hyperparameters
- Best parameters extracted and stored in Model Metadata
- Full cv_results available for analysis if needed (e.g., plotting learning curves, analyzing parameter sensitivity)

---

### 4. Feature Matrix

**Description**: Input data for model training - 30 statistical features per window plus binary label.

**Attributes**:
- **X_train**: 2D numpy array, shape (446, 30) - training features
- **y_train**: 1D numpy array, shape (446,) - training labels (0 or 1)
- **X_test**: 2D numpy array, shape (110, 30) - test features
- **y_test**: 1D numpy array, shape (110,) - test labels (0 or 1)
- **feature_names**: List of 30 strings (column names from CSV: RMS_aX, mean_aX, std_aX, skewness_aX, kurtosis_aX, ..., RMS_gZ, mean_gZ, std_gZ, skewness_gZ, kurtosis_gZ)
- **label_name**: String ("label")

**Persistence**:
- **Source**: Feature 004 outputs (train_features.csv, test_features.csv)
- **Format**: CSV files with header row
- **Loading**: `df = pd.read_csv(file_path); X = df.drop('label', axis=1).values; y = df['label'].values`

**Relationships**:
- **Input to** Trained Model (training data)
- **Produced by** Feature 004 (data preparation pipeline)
- **Used by** Model Evaluation (X_test, y_test for performance metrics)

**Validation Rules**:
- X_train and X_test must have exactly 30 columns
- y_train and y_test must be binary (values in {0, 1})
- No NaN or Inf values allowed
- Feature names must match expected list from Feature 004

---

### 5. Confusion Matrix

**Description**: A 2×2 matrix showing the counts of true positives, true negatives, false positives, and false negatives for model predictions on the test set.

**Attributes**:
- **matrix**: 2D numpy array, shape (2, 2)
  - matrix[0, 0] = True Negatives (TN): predicted 0, actual 0
  - matrix[0, 1] = False Positives (FP): predicted 1, actual 0
  - matrix[1, 0] = False Negatives (FN): predicted 0, actual 1
  - matrix[1, 1] = True Positives (TP): predicted 1, actual 1
- **class_labels**: Array [0, 1] (class identifiers)
- **class_names**: Array ["no tremor", "tremor"] (human-readable labels)

**Derived Metrics** (computed from matrix):
- **accuracy**: (TP + TN) / (TP + TN + FP + FN)
- **precision**: TP / (TP + FP) - of predicted tremors, how many are correct
- **recall** (sensitivity): TP / (TP + FN) - of actual tremors, how many are detected
- **specificity**: TN / (TN + FP) - of actual no tremors, how many are correctly identified
- **f1_score**: 2 × (precision × recall) / (precision + recall)

**Persistence**:
- **Stored in**: Model Metadata JSON (as nested array in performance_metrics.confusion_matrix)
- **Format**: Serialized as 2D list: `[[TN, FP], [FN, TP]]`

**Relationships**:
- **Produced by** Model Evaluation (comparing predictions vs actual test labels)
- **Belongs to** one Trained Model (evaluation result)
- **Included in** Model Metadata (performance_metrics field)

**Validation Rules**:
- Must be 2×2 array (binary classification)
- All values must be non-negative integers
- Sum of all values must equal test set size (110 samples)
- Matrix[0, 0] + Matrix[0, 1] = count of actual class 0 (no tremor)
- Matrix[1, 0] + Matrix[1, 1] = count of actual class 1 (tremor)

**Example**:
```python
# Confusion Matrix for a model achieving 96.4% accuracy on 110 test samples
confusion_matrix = [
    [53, 3],   # Row 0: Actual class 0 (no tremor) - 53 correct, 3 false positives
    [2, 52]    # Row 1: Actual class 1 (tremor) - 2 false negatives, 52 correct
]

# Interpretation:
# - True Negatives (TN) = 53: Correctly identified 53 "no tremor" windows
# - False Positives (FP) = 3: Incorrectly predicted 3 "tremor" when actually "no tremor"
# - False Negatives (FN) = 2: Incorrectly predicted 2 "no tremor" when actually "tremor"
# - True Positives (TP) = 52: Correctly identified 52 "tremor" windows
# - Accuracy = (53 + 52) / 110 = 95.5%
```

**Clinical Significance**:
- **False Positives**: Patient sees tremor warning when not actually tremoring (over-sensitive, less critical)
- **False Negatives**: Patient doesn't get tremor warning when actually tremoring (under-sensitive, more critical - missed detection)
- For medical application, **minimizing False Negatives** is often more important than minimizing False Positives (better to have false alarms than missed detections)

---

## Entity Relationships Diagram

```text
Feature Matrix (from Feature 004)
    ↓ (input to training)
GridSearch Results
    ↓ (produces best_params)
Trained Model (.pkl)
    ↓ (evaluated on test set)
Confusion Matrix
    ↓ (summarized in)
Model Metadata (.json)
    ↓ (paired with)
Trained Model (.pkl)
    ↓ (deployed for)
Predictions (future Feature 007+)
```

## File Organization

```text
backend/ml_models/models/
├── .gitkeep                      # Preserve directory in git
├── random_forest.pkl             # Trained Model entity (US1)
├── random_forest.json            # Model Metadata entity (US1)
├── svm_rbf.pkl                   # Trained Model entity (US2)
├── svm_rbf.json                  # Model Metadata entity (US2)
└── comparison_report.txt         # Model comparison summary (not an entity, just report)
```

**Naming Convention**:
- Base name: lowercase_with_underscores (e.g., "random_forest", "svm_rbf")
- Extensions: .pkl for model object, .json for metadata
- Matched pairs: `<base_name>.pkl` and `<base_name>.json` always together

**Version Management** (Future Enhancement):
- Timestamp-based versioning: `random_forest_20260215_143022.pkl`
- Enables model history tracking without overwriting
- Comparison report can reference specific versions

## Data Integrity

**Load-Time Validation**:

When loading a persisted model, validate:
1. **Model file exists**: Check `<model_name>.pkl` exists
2. **Metadata file exists**: Check `<model_name>.json` exists
3. **Model is scikit-learn estimator**: `isinstance(model, (RandomForestClassifier, SVC))`
4. **Model is fitted**: Check `hasattr(model, 'classes_')`
5. **Feature count matches**: Model expects 30 features
6. **Environment compatibility**: Check sklearn version in metadata matches current environment (warn if mismatch)

**Save-Time Validation**:

Before saving a trained model, validate:
1. **Model is fitted**: Has `classes_` attribute and can predict
2. **Metadata is complete**: All required fields present in metadata dict
3. **Metrics are valid**: Accuracy, precision, recall, F1 in [0, 1]
4. **Output directory exists**: `backend/ml_models/models/` directory present
5. **No filename conflicts**: Warn if overwriting existing model (suggest timestamped naming)

## Usage Patterns

### Training Flow
```python
# 1. Load Feature Matrix from Feature 004
X_train, y_train = load_features("train_features.csv")
X_test, y_test = load_features("test_features.csv")

# 2. GridSearchCV produces GridSearch Results
grid_search = GridSearchCV(estimator, param_grid, cv=5)
grid_search.fit(X_train, y_train)

# 3. Extract best_params, create Trained Model
best_model = grid_search.best_estimator_

# 4. Evaluate on test set, create Confusion Matrix
y_pred = best_model.predict(X_test)
cm = confusion_matrix(y_test, y_pred)

# 5. Compute metrics, assemble Model Metadata
metadata = {
    "model_type": type(best_model).__name__,
    "hyperparameters": best_model.get_params(),
    "performance_metrics": {
        "accuracy": accuracy_score(y_test, y_pred),
        "confusion_matrix": cm.tolist(),
        # ...
    },
    # ...
}

# 6. Persist Trained Model + Model Metadata
joblib.dump(best_model, "random_forest.pkl")
json.dump(metadata, open("random_forest.json", "w"))
```

### Prediction Flow (Future Feature 007)
```python
# 1. Load Trained Model + Model Metadata
model = joblib.load("random_forest.pkl")
metadata = json.load(open("random_forest.json"))

# 2. Validate environment compatibility
assert sklearn.__version__ == metadata["training_info"]["sklearn_version"]

# 3. Prepare new data (30 features)
X_new = extract_features(new_sensor_data)  # shape (n, 30)

# 4. Predict
predictions = model.predict(X_new)  # shape (n,), values in {0, 1}

# 5. Return predictions to API/WebSocket
return {"predictions": predictions.tolist()}
```

## Notes

- **No Database**: All entities are file-based (not PostgreSQL) because this is offline ML training
- **Gitignore**: .pkl files should be gitignored (large, binary). .json metadata can be committed (small, text) for model documentation.
- **Future Integration**: Feature 007+ will load these models and serve predictions via Django REST API
