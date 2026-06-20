# Implementation Plan: ML/DL Data Preparation

**Branch**: `004-ml-data-prep` | **Date**: 2026-02-15 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-ml-data-prep/spec.md`

## Summary

Implement a data preparation pipeline to transform the raw Kaggle tremor detection dataset (Dataset.csv with 27,995 samples of 6-axis IMU sensor data) into three consumable formats: (1) clean normalized train/test split (80/20), (2) statistical feature matrices for traditional ML models (Random Forest, SVM, XGBoost), and (3) fixed-length sequence tensors for deep learning models (LSTM, CNN). The pipeline ensures data integrity, reproducibility, and independence between the three preparation stages, enabling both ML and DL model development for tremor classification.

## Technical Context

**Backend Stack**: Python 3.8+ with data science libraries (numpy, pandas, scipy, scikit-learn)
**Frontend Stack**: N/A (data preprocessing only)
**Database**: N/A (works with local CSV file, no database interaction)
**Authentication**: N/A (offline batch processing)
**Testing**: pytest for data pipeline validation
**Project Type**: Data processing pipeline within backend/ directory
**Real-time**: N/A (batch processing)
**Integration**: Reads Dataset.csv, outputs processed data files
**AI/ML**: Prepares data FOR model training (models will be served via Django in future features)
**Performance Goals**: Process full dataset (<28K samples) in under 5 minutes on standard laptop
**Constraints**: Local development only, no Docker, outputs stored in backend/ml_data/processed/
**Scale/Scope**: Single dataset (Dataset.csv), three output formats, supports both ML and DL workflows

**Libraries Required**:
- **numpy**: Array operations, tensor manipulation, binary file I/O
- **pandas**: CSV loading, dataframe operations, feature matrix creation
- **scipy**: Statistical calculations (skewness, kurtosis)
- **scikit-learn**: Train/test splitting, standardization (StandardScaler)
- **matplotlib** (optional): Data validation visualizations during development

**Input Data**:
- Dataset.csv: 27,995 samples × 10 columns (6 active sensor axes + 3 disabled magnetometer + 1 label)
- Sampling rate: 100 Hz (confirmed in spec clarifications)
- Binary classification: 0 (no tremor, 45.4%) vs 1 (tremor detected, 54.6%)

**Output Data**:
- **Preprocessed**: train_normalized.npy, test_normalized.npy, train_labels.npy, test_labels.npy
- **Feature Matrices**: train_features.csv, test_features.csv (30 features per window)
- **Sequence Tensors**: train_sequences.npy, test_sequences.npy, train_seq_labels.npy, test_seq_labels.npy
- **Metadata**: normalization_params.json, preprocessing_report.txt

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Validate this feature against `.specify/memory/constitution.md` principles:

- [X] **Monorepo Architecture**: Feature fits in `backend/` structure (backend/ml_data/)
- [X] **Tech Stack Immutability**: Uses Python data science libraries, compatible with Django backend ecosystem
- [X] **Database Strategy**: N/A - works with CSV file, no database interaction
- [X] **Authentication**: N/A - offline batch processing, no user authentication required
- [X] **Security-First**: N/A - no secrets or credentials involved in data processing
- [X] **Real-time Requirements**: N/A - batch offline preprocessing
- [X] **MQTT Integration**: N/A - works with static dataset, not live sensor data
- [X] **AI Model Serving**: Prepares data FOR future model training (models will be served via Django in Feature 005/006)
- [X] **API Standards**: N/A - no API endpoints, pure data pipeline
- [X] **Development Scope**: Local development only, no Docker/CI/CD

**Result**: ✅ **PASS** - No constitutional violations. Feature is a foundational data pipeline that enables future ML/DL features while respecting all architectural constraints.

## Project Structure

### Documentation (this feature)

```text
specs/004-ml-data-prep/
├── spec.md              # Feature specification
├── plan.md              # This file (implementation plan)
├── research.md          # Library selection, best practices
├── data-model.md        # Data entities (preprocessed data, features, sequences)
├── quickstart.md        # Usage examples, validation scenarios
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── contracts/           # (Not applicable - no API endpoints)
```

### Source Code (repository root)

```text
backend/
├── ml_data/                          # ML data processing directory (NEW)
│   ├── __init__.py
│   ├── scripts/                      # Preprocessing scripts
│   │   ├── __init__.py
│   │   ├── 1_preprocess.py          # Story 1: Dataset cleaning, normalization, splitting
│   │   ├── 2_feature_engineering.py # Story 2: Extract statistical features for ML
│   │   ├── 3_sequence_preparation.py# Story 3: Create DL sequence tensors
│   │   └── run_all.py               # Master script to run all 3 stages
│   ├── utils/                        # Shared utilities
│   │   ├── __init__.py
│   │   ├── data_loader.py           # CSV loading, validation
│   │   ├── windowing.py             # Sliding window utilities
│   │   ├── feature_extractors.py    # RMS, mean, std, skewness, kurtosis
│   │   └── validators.py            # Data integrity checks
│   ├── processed/                    # Output directory (GITIGNORED)
│   │   ├── .gitkeep
│   │   ├── train_normalized.npy     # Story 1 output
│   │   ├── test_normalized.npy
│   │   ├── train_labels.npy
│   │   ├── test_labels.npy
│   │   ├── normalization_params.json
│   │   ├── preprocessing_report.txt
│   │   ├── train_features.csv        # Story 2 output
│   │   ├── test_features.csv
│   │   ├── train_sequences.npy       # Story 3 output
│   │   ├── test_sequences.npy
│   │   ├── train_seq_labels.npy
│   │   └── test_seq_labels.npy
│   └── README.md                     # Pipeline documentation
├── tests/
│   └── test_ml_data/
│       ├── test_preprocessing.py     # Test Story 1
│       ├── test_feature_engineering.py # Test Story 2
│       ├── test_sequence_preparation.py # Test Story 3
│       └── fixtures/                 # Small test dataset
│           └── sample_data.csv
├── Dataset.csv                       # Raw Kaggle dataset (project root)
└── requirements.txt                  # Add: numpy, pandas, scipy, scikit-learn

.gitignore                            # Add: backend/ml_data/processed/*
```

**Structure Decision**:
- **backend/ml_data/**: New directory for ML data processing, separate from Django apps
- **scripts/**: Three independent scripts (1_preprocess.py, 2_feature_engineering.py, 3_sequence_preparation.py) matching the three user stories
- **utils/**: Shared utilities to avoid code duplication (windowing logic used in both Story 2 and 3)
- **processed/**: Gitignored output directory for all processed data files
- **Dataset.csv**: Raw data stays at project root for easy access
- **No Django app**: This is a data pipeline, not a web API feature, so no models/views/serializers needed

## Complexity Tracking

No constitutional violations - table not applicable.

---

## Phase 0: Research (Completed Inline)

### Data Processing Libraries

**Decision**: Use standard Python data science stack (numpy, pandas, scipy, scikit-learn)

**Rationale**:
- **numpy**: Industry standard for array operations, efficient binary I/O (.npy format), tensor manipulation
- **pandas**: Best tool for CSV handling, dataframe operations, easy column-wise operations
- **scipy**: Provides statistical functions (skewness, kurtosis) not in numpy
- **scikit-learn**: StandardScaler for normalization, train_test_split with stratification

**Alternatives Considered**:
- **Pure numpy**: Would require manual implementation of statistical features, train/test split logic
- **PyTorch/TensorFlow for preprocessing**: Overkill for simple data preparation, adds heavy dependencies
- **Polars**: Faster than pandas but less mature ecosystem, unnecessary for 28K sample dataset

### Windowing Strategy

**Decision**: Sliding window with 50% overlap for both feature engineering and sequence preparation

**Rationale**:
- **50% overlap**: Standard data augmentation technique, doubles training samples while maintaining temporal diversity
- **Fixed window sizes**: 100 samples (1s at 100 Hz) for features, 128 samples (~1.28s) for DL sequences
- **Stride calculation**: window_size // 2 (50 samples for features, 64 for sequences)

**Alternatives Considered**:
- **No overlap (100% stride)**: Fewer samples, less data augmentation, worse model performance
- **75% overlap (25% stride)**: More samples but high temporal correlation, diminishing returns
- **Variable window sizes**: Adds complexity without clear benefit for fixed sampling rate data

### File Format Selection

**Decision**:
- **numpy binary (.npy)** for large arrays (preprocessed data, sequences)
- **CSV** for feature matrices (human-readable, ML library compatible)
- **JSON** for metadata (normalization_params.json)

**Rationale**:
- **.npy**: Fast loading, preserves exact float precision, space-efficient for large arrays
- **CSV**: Pandas/scikit-learn can read directly, easy to inspect, good for 2D feature matrices
- **JSON**: Human-readable config file, easy to load in any language, perfect for normalization params

**Alternatives Considered**:
- **HDF5**: More complex, overkill for our dataset size
- **Pickle**: Python-only, security concerns, less portable than .npy
- **Parquet**: Overkill for 28K samples, adds Apache Arrow dependency

### Label Assignment for Windows

**Decision**: Majority voting - assign window label based on dominant class within window

**Rationale**:
- **Simple and interpretable**: Window with 60% class 1 samples → labeled as class 1
- **Handles class transitions**: Windows spanning tremor onset/offset get single label
- **Standard approach**: Used in time-series classification literature

**Alternatives Considered**:
- **First sample label**: Ignores temporal context, poor for transition windows
- **Multi-label**: Adds complexity, not needed for binary classification
- **Discard mixed windows**: Throws away valuable transition data

---

## Phase 1: Design

See generated artifacts:
- **data-model.md**: Entities (Raw Dataset, Preprocessed Dataset, Feature Matrix, Sequence Tensor, Normalization Parameters)
- **quickstart.md**: Usage examples and validation scenarios
- **contracts/**: Not applicable (no API endpoints for data pipeline)

---

## Phase 2: Task Breakdown

**Next Command**: `/speckit.tasks` - Generate dependency-ordered task list from this plan

**Expected Task Structure** (preview):
- **Phase 1: Setup** (5-7 tasks): Create directories, add dependencies, setup .gitignore
- **Phase 2: Core Utilities** (8-10 tasks): Implement data_loader, windowing, feature_extractors, validators
- **Phase 3: Story 1 - Preprocessing** (6-8 tasks): Clean, normalize, split, validate, save
- **Phase 4: Story 2 - Feature Engineering** (6-8 tasks): Window, extract features, create matrix, save
- **Phase 5: Story 3 - Sequence Preparation** (6-8 tasks): Window, reshape tensors, assign labels, save
- **Phase 6: Integration & Testing** (5-7 tasks): Master script, tests, documentation

**Estimated Total**: 36-48 tasks

---

## Implementation Notes

### Story 1: Dataset Preprocessing (Priority P1 - MVP)

**Script**: `backend/ml_data/scripts/1_preprocess.py`

**Input**: Dataset.csv (27,995 samples)
**Output**:
- train_normalized.npy (22,396 samples × 6 axes)
- test_normalized.npy (5,599 samples × 6 axes)
- train_labels.npy (22,396 labels)
- test_labels.npy (5,599 labels)
- normalization_params.json (mean, std per axis)
- preprocessing_report.txt (statistics)

**Key Functions**:
- `load_and_validate_csv()`: Read CSV, check structure, drop magnetometer columns
- `handle_missing_values()`: Detect nulls, drop/impute based on threshold
- `split_stratified()`: 80/20 split with stratification, fixed random_state=42
- `fit_normalization()`: Fit StandardScaler on train set only
- `apply_normalization()`: Transform train and test sets
- `save_preprocessed_data()`: Write .npy files and JSON params

### Story 2: Feature Engineering (Priority P2)

**Script**: `backend/ml_data/scripts/2_feature_engineering.py`

**Input**: train_normalized.npy, test_normalized.npy from Story 1
**Output**:
- train_features.csv (N_windows × 30 features + 1 label)
- test_features.csv (M_windows × 30 features + 1 label)

**Key Functions**:
- `sliding_window()`: Create overlapping windows (size=100, stride=50)
- `extract_features_per_axis()`: Compute RMS, mean, std, skewness, kurtosis
- `assign_window_labels()`: Majority voting for label assignment
- `create_feature_matrix()`: Assemble into pandas DataFrame with column names
- `save_feature_csv()`: Write to CSV with proper headers

**Feature Columns** (30 total):
- aX: RMS_aX, mean_aX, std_aX, skew_aX, kurt_aX
- aY: RMS_aY, mean_aY, std_aY, skew_aY, kurt_aY
- aZ: RMS_aZ, mean_aZ, std_aZ, skew_aZ, kurt_aZ
- gX: RMS_gX, mean_gX, std_gX, skew_gX, kurt_gX
- gY: RMS_gY, mean_gY, std_gY, skew_gY, kurt_gY
- gZ: RMS_gZ, mean_gZ, std_gZ, skew_gZ, kurt_gZ
- Plus: label (0 or 1)

### Story 3: Sequence Preparation (Priority P3)

**Script**: `backend/ml_data/scripts/3_sequence_preparation.py`

**Input**: train_normalized.npy, test_normalized.npy from Story 1
**Output**:
- train_sequences.npy (N_windows, 128, 6)
- test_sequences.npy (M_windows, 128, 6)
- train_seq_labels.npy (N_windows,)
- test_seq_labels.npy (M_windows,)

**Key Functions**:
- `sliding_window_sequences()`: Create overlapping sequences (size=128, stride=64)
- `assign_sequence_labels()`: Majority voting for label assignment
- `handle_edge_padding()`: Zero-pad incomplete sequences at dataset end
- `validate_sequence_shapes()`: Check 3D tensor dimensions
- `save_sequence_tensors()`: Write .npy files

**Tensor Format**:
- Axis 0: Window index (sample dimension)
- Axis 1: Time steps (128 samples = ~1.28 seconds)
- Axis 2: Sensor channels (6: aX, aY, aZ, gX, gY, gZ)

### Master Script

**Script**: `backend/ml_data/scripts/run_all.py`

**Purpose**: Run all three preprocessing stages in sequence with single command

```python
# Pseudocode
if __name__ == "__main__":
    print("Stage 1: Dataset Preprocessing...")
    run_preprocessing()  # From 1_preprocess.py

    print("Stage 2: Feature Engineering...")
    run_feature_engineering()  # From 2_feature_engineering.py

    print("Stage 3: Sequence Preparation...")
    run_sequence_preparation()  # From 3_sequence_preparation.py

    print("Pipeline complete! Check backend/ml_data/processed/")
```

### Validation Strategy

Each script includes validation checks:
- **Data integrity**: No NaN/Inf values in outputs
- **Shape validation**: Expected dimensions for all arrays
- **Class distribution**: Preserved in train/test splits
- **Value ranges**: Normalized data has reasonable bounds
- **Label consistency**: Labels match corresponding data samples

### Testing Approach

**Unit Tests** (pytest):
- Test each utility function with small synthetic data
- Test windowing logic (boundary conditions, overlap calculation)
- Test feature extraction (verify formulas with known inputs)
- Test normalization (check mean=0, std=1 after transform)

**Integration Tests**:
- Use small sample_data.csv (100 samples) in test fixtures
- Run full pipeline, validate all outputs created
- Check file formats (loadable .npy, valid CSV structure)

**Validation Tests**:
- Load processed data into scikit-learn, verify compatible
- Load sequence tensors into TensorFlow/PyTorch, verify shapes
- Verify reproducibility (same random seed → identical output)

---

## Dependencies

### Python Libraries (add to requirements.txt)

```text
# ML Data Preparation (Feature 004)
numpy>=1.24.0
pandas>=2.0.0
scipy>=1.10.0
scikit-learn>=1.3.0
```

### System Requirements

- Python 3.8+
- ~500 MB free disk space for processed data
- ~2 GB RAM for processing (holds full dataset in memory)

### Data Dependencies

- Dataset.csv must be present at project root (C:\Data from HDD\Graduation Project\Platform\Dataset.csv)
- File validated: 27,995 rows, 10 columns, no corruption

---

## Success Metrics

**From spec.md Success Criteria** (validation targets):

- **SC-001**: Data integrity - Zero data leakage verified by checking no sample overlap between train/test
- **SC-002**: Class distribution - Train/test both have 45% ± 2% class 0, 55% ± 2% class 1
- **SC-003**: Processing time - Complete pipeline < 5 minutes on standard laptop
- **SC-004**: Tensor validation - 100% of sequences pass shape checks, no NaN values
- **SC-005**: Reproducibility - Multiple runs with same seed produce identical splits
- **SC-006**: ML/DL compatibility - Outputs load successfully into scikit-learn and TensorFlow/PyTorch
- **SC-007**: Documentation - Report includes sample counts, normalization params, shapes

---

## Risk Assessment

**Low Risk** (mitigations in place):

- **Memory issues with large windows**: Mitigated by processing in batches, ~28K samples is manageable
- **Incorrect window calculations**: Mitigated by comprehensive unit tests on windowing logic
- **Data leakage**: Mitigated by fitting normalization on train set only, strict train/test separation
- **File corruption**: Mitigated by validation checks before saving, checksums in report

**No High Risks Identified**: Standard data processing task with well-established libraries and patterns.
