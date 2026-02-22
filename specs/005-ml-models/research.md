# Research: Machine Learning Models Training

**Feature**: 005-ml-models
**Date**: 2026-02-15
**Status**: Complete - No significant unknowns

## Overview

This feature implements standard scikit-learn model training practices. All technical decisions follow well-established ML conventions with no novel or experimental approaches.

## Decisions

### Decision 1: Hyperparameter Tuning Method

**Chosen**: GridSearchCV (scikit-learn)

**Rationale**:
- Exhaustive search over specified parameter grid
- Guaranteed to find best combination within search space
- Built-in cross-validation for robust evaluation
- Parallel processing support (n_jobs=-1) for faster execution
- Widely used industry standard for model tuning

**Alternatives Considered**:
- **RandomizedSearchCV**: Samples random parameter combinations, faster but less thorough. Rejected because our search space is small (12-16 combinations) and GridSearchCV can explore it completely within time constraints.
- **Manual tuning**: Train multiple models with different parameters manually. Rejected because GridSearchCV automates this and provides better cross-validation infrastructure.
- **Bayesian Optimization** (Optuna, Hyperopt): More efficient for large search spaces. Rejected because it adds dependency complexity for minimal benefit given our small search space.

**References**:
- scikit-learn GridSearchCV documentation: https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GridSearchCV.html
- "Hyperparameter tuning best practices" (scikit-learn user guide)

---

### Decision 2: Random Forest Hyperparameters

**Chosen**: n_estimators [50, 100, 200, 300], max_depth [10, 20, 30, None]

**Rationale**:
- **n_estimators**: Number of trees in the forest. More trees generally improve performance but increase training time. Range covers typical values from small (50) to large (300).
- **max_depth**: Maximum depth of trees. None allows unlimited depth (trees grow until pure leaves). Limited depths (10, 20, 30) prevent overfitting.
- **Search space**: 4 × 4 = 16 combinations, reasonable for GridSearchCV
- These are the two most impactful hyperparameters for Random Forest performance

**Alternatives Considered**:
- **Additional parameters** (min_samples_split, min_samples_leaf, max_features): Would increase search space to 64+ combinations, exceeding 10-minute training time target. These secondary parameters have less impact than n_estimators and max_depth.
- **Larger ranges**: e.g., n_estimators up to 500. Rejected because training time grows linearly with tree count, and 300 trees typically sufficient for small datasets (~446 training samples).

**References**:
- Breiman, L. (2001). "Random Forests". Machine Learning 45(1): 5-32.
- scikit-learn RandomForestClassifier documentation

---

### Decision 3: SVM Hyperparameters

**Chosen**: kernel='rbf', C [0.1, 1, 10, 100], gamma [0.001, 0.01, 0.1, 1]

**Rationale**:
- **kernel='rbf'**: Radial Basis Function kernel handles non-linear decision boundaries well, suitable for complex sensor data patterns
- **C**: Regularization parameter. Low C (0.1) = soft margin, high C (100) = hard margin. Range covers full spectrum from underfitting to overfitting.
- **gamma**: Kernel coefficient. Low gamma (0.001) = large influence radius, high gamma (1) = tight influence radius. Range spans typical values for normalized features.
- **Search space**: 4 × 4 = 16 combinations
- RBF kernel is most commonly used for non-linear classification

**Alternatives Considered**:
- **Linear kernel**: Faster but assumes linear separability. Rejected because tremor patterns likely have non-linear decision boundaries.
- **Polynomial kernel**: Can model complex boundaries but has additional hyperparameters (degree, coef0). Rejected for simplicity and RBF generally performs as well or better.
- **Auto gamma**: gamma='scale' or 'auto'. Rejected because we want to explore range explicitly via GridSearchCV rather than relying on heuristics.

**References**:
- Hsu, C.-W., Chang, C.-C., & Lin, C.-J. (2003). "A Practical Guide to Support Vector Classification"
- scikit-learn SVC documentation

---

### Decision 4: Cross-Validation Strategy

**Chosen**: Stratified 5-fold cross-validation

**Rationale**:
- **Stratified**: Preserves class distribution in each fold, critical for binary classification with potential class imbalance
- **5 folds**: Industry standard, balances validation robustness (not too few folds) with training time (not too many folds)
- With 446 training samples, each fold has ~89 samples, sufficient for reliable evaluation
- Matches stratification approach from Feature 004 (train/test split)

**Alternatives Considered**:
- **10-fold CV**: More robust but doubles training time. Rejected because 5-fold provides sufficient validation given our dataset size.
- **Leave-One-Out CV**: Maximum training data per iteration but computationally expensive (446 iterations). Rejected due to time constraints.
- **Non-stratified CV**: Simpler but risks class imbalance in folds. Rejected because stratification is critical for binary classification.

**References**:
- Kohavi, R. (1995). "A study of cross-validation and bootstrap for accuracy estimation and model selection"
- scikit-learn StratifiedKFold documentation

---

### Decision 5: Model Serialization Format

**Chosen**: joblib for .pkl files, json module for .json metadata

**Rationale**:
- **joblib**: Scikit-learn's recommended method for model persistence. More efficient than pickle for large numpy arrays. Standard library for model deployment.
- **.pkl extension**: Conventional for pickled Python objects, indicates binary serialization
- **json**: Human-readable text format for metadata. Easy to inspect, parse, and version control (if small).
- **Separate files**: Model (.pkl) and metadata (.json) separated for flexibility - can version/share metadata independently

**Alternatives Considered**:
- **pickle module**: Python's standard serialization. Rejected because joblib is faster and more efficient for scikit-learn models.
- **ONNX format**: Open Neural Network Exchange, enables cross-platform deployment. Rejected because it adds complexity and we're staying in Python/scikit-learn ecosystem.
- **PMML**: Predictive Model Markup Language, XML-based. Rejected because it's verbose and less commonly used than joblib in Python ML workflows.
- **Combined JSON file**: Store model parameters and metadata together in JSON (not binary model). Rejected because it would require manual reconstruction of model objects, losing scikit-learn's native persistence.

**References**:
- joblib documentation: https://joblib.readthedocs.io/
- scikit-learn model persistence guide

---

### Decision 6: Performance Metrics

**Chosen**: Accuracy, Precision, Recall, F1-score, Confusion Matrix

**Rationale**:
- **Accuracy**: Primary metric (≥95% success criterion), overall correctness
- **Precision**: Of predicted tremors, how many are actual tremors (minimizes false positives)
- **Recall**: Of actual tremors, how many are detected (minimizes false negatives)
- **F1-score**: Harmonic mean of precision and recall, balances both
- **Confusion Matrix**: Shows true positives, true negatives, false positives, false negatives - critical for medical applications to understand error types
- All metrics computed using sklearn.metrics module

**Alternatives Considered**:
- **ROC-AUC**: Receiver Operating Characteristic curve and Area Under Curve. Useful but not specified in success criteria. Could be added later for threshold tuning.
- **Cohen's Kappa**: Measures agreement beyond chance. Not needed for binary classification with balanced classes.
- **Matthews Correlation Coefficient**: Robust for imbalanced datasets. Not prioritized because our dataset is reasonably balanced (45/55 split).

**References**:
- Powers, D. M. W. (2011). "Evaluation: From Precision, Recall and F-Measure to ROC, Informedness, Markedness & Correlation"
- scikit-learn metrics documentation

---

### Decision 7: Reproducibility Strategy

**Chosen**: random_state=42 for all random operations

**Rationale**:
- **Fixed seed**: Ensures identical results across multiple runs (Success Criterion SC-004)
- **Value 42**: Arbitrary choice, commonly used in ML community (Hitchhiker's Guide reference)
- **Applied to**: RandomForestClassifier, StratifiedKFold, any future random operations
- **Consistency**: Same seed used in Feature 004 (train/test split), maintains reproducibility across entire pipeline

**Alternatives Considered**:
- **No seed**: Non-reproducible results. Rejected because SC-004 explicitly requires reproducibility.
- **Different seeds per run**: Enables ensemble diversity but violates reproducibility requirement. Rejected for this feature (could be separate ensemble feature).

**References**:
- scikit-learn documentation on reproducibility
- "Reproducible machine learning" best practices

---

## Summary of Key Choices

| Decision | Choice | Primary Reason |
|----------|--------|---------------|
| Tuning Method | GridSearchCV | Exhaustive search, small search space |
| Random Forest Params | n_estimators, max_depth | Most impactful parameters |
| SVM Params | C, gamma with RBF kernel | Non-linear decision boundaries |
| Cross-Validation | Stratified 5-fold | Standard for classification |
| Serialization | joblib (.pkl) + json | Efficient, standard, flexible |
| Metrics | Accuracy, P/R/F1, Confusion | Comprehensive evaluation |
| Reproducibility | random_state=42 | Deterministic results |

## Dependencies Confirmed

All required libraries are standard and already available:
- **scikit-learn ≥1.3.0**: Already added in Feature 004
- **joblib**: Bundled with scikit-learn installation
- **json**: Python standard library
- **pandas**: Already added in Feature 004 (for loading CSV files)

No new dependencies required.

## Risks & Mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| Training exceeds 10 min | Low | Parallel processing (n_jobs=-1), reasonable search space |
| Insufficient memory | Low | Small dataset (~446 samples), reduce cv folds if needed |
| <95% accuracy | Medium | Acceptable if documented; indicates feature engineering needed |
| Model files too large | Very Low | Expect <10 MB per model (Success Criterion) |

## Research Conclusion

**Status**: ✅ No unknowns requiring further investigation

All technical decisions follow standard scikit-learn best practices. Implementation can proceed directly to Phase 1 (design artifacts) and Phase 2 (task breakdown).
