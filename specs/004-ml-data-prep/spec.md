# Feature Specification: ML/DL Data Preparation

**Feature Branch**: `004-ml-data-prep`
**Created**: 2026-02-15
**Status**: Draft
**Input**: User description: "2.1 Data Preparation - Dataset preprocessing, feature engineering for ML, and sequence preparation for DL models"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Dataset Preprocessing (Priority: P1) 🎯 MVP

Data scientists need clean, normalized, and properly split data before training any ML/DL models. This story ensures the raw Kaggle dataset is ready for model development.

**Why this priority**: Foundational requirement - all ML/DL work depends on having clean, preprocessed data. Without this, no models can be trained.

**Independent Test**: Load Dataset.csv, run preprocessing pipeline, verify output contains clean train/test sets with 80/20 split, normalized sensor values, and no missing data. Can be validated by checking output shapes, value ranges, and data integrity.

**Acceptance Scenarios**:

1. **Given** Dataset.csv with 27,995 samples, **When** preprocessing pipeline runs, **Then** system loads all data successfully, drops magnetometer columns (all -1 values), and creates clean dataset with 6 sensor axes (aX, aY, aZ, gX, gY, gZ) + Result column
2. **Given** clean dataset with potential null values, **When** null handling executes, **Then** system identifies null count per column, drops rows if nulls < 5%, or imputes with column median if nulls >= 5%
3. **Given** cleaned data with raw sensor values, **When** normalization applies, **Then** system scales each sensor axis independently using standardization (z-score: mean=0, std=1) fitted on training set only
4. **Given** normalized dataset, **When** train/test split executes, **Then** system randomly splits data 80/20 (22,396 train / 5,599 test samples) with stratification to preserve class balance, using fixed random seed for reproducibility
5. **Given** split datasets, **When** validation checks run, **Then** system confirms no data leakage (train/test separation), class distribution preserved in both sets (~45% class 0, ~55% class 1), and all values normalized

---

### User Story 2 - Feature Engineering for ML Models (Priority: P2)

Data scientists need extracted statistical features from time-windowed sensor data to train traditional ML models (Random Forest, SVM, XGBoost) that don't process raw sequences.

**Why this priority**: Enables traditional ML model development, which is faster to train and often provides good baseline performance for comparison with DL models.

**Independent Test**: Take preprocessed train/test data from Story 1, apply sliding window feature extraction, verify output feature matrices contain RMS, mean, std, skewness, and kurtosis per axis (30 features total) for each window. Can be validated by checking feature matrix dimensions and feature value distributions.

**Acceptance Scenarios**:

1. **Given** preprocessed train data (22,396 samples × 6 axes), **When** sliding window segmentation applies, **Then** system creates overlapping windows of 100 samples (1 second at 100 Hz sampling rate) with 50% overlap (50 sample stride)
2. **Given** segmented windows, **When** feature extraction executes per window, **Then** system calculates 5 statistical features (RMS, mean, standard deviation, skewness, kurtosis) for each of 6 sensor axes, producing 30 features per window
3. **Given** extracted features, **When** feature matrix assembly completes, **Then** system creates structured feature matrix where each row represents one time window with 30 feature columns + 1 label column (window's majority class)
4. **Given** feature matrices for train and test sets, **When** validation runs, **Then** system confirms feature matrix shapes match expected dimensions, no NaN/Inf values present, and labels correctly assigned based on window majority vote
5. **Given** complete feature matrices, **When** data persistence executes, **Then** system saves train_features.csv and test_features.csv with proper column names for ML model consumption

---

### User Story 3 - Sequence Preparation for DL Models (Priority: P3)

Data scientists need properly shaped time-series sequences to train deep learning models (LSTM, CNN, hybrid architectures) that process raw sensor data directly without manual feature engineering.

**Why this priority**: Enables deep learning model development, which can automatically learn features from raw data but requires specific input format (3D tensors). Lower priority than ML prep since DL models take longer to train and tune.

**Independent Test**: Take preprocessed train/test data from Story 1, reshape into fixed-length sequences, verify output tensors have shape (num_samples, sequence_length, num_features) ready for DL model input. Can be validated by checking tensor dimensions and data continuity.

**Acceptance Scenarios**:

1. **Given** preprocessed train data (22,396 samples × 6 axes), **When** sequence windowing applies, **Then** system creates fixed-length sequences of 128 consecutive samples (~1.28 seconds at 100 Hz) with 50% overlap (64 sample stride)
2. **Given** raw sensor sequences, **When** sequence reshaping executes, **Then** system structures data into 3D tensor format: (num_windows, sequence_length, 6) where axis 0 = window index, axis 1 = time steps, axis 2 = sensor channels (aX, aY, aZ, gX, gY, gZ)
3. **Given** sequence tensors, **When** label assignment completes, **Then** system assigns each sequence window a single label based on majority class within that window (handles windows spanning class transitions)
4. **Given** sequence data for train and test sets, **When** padding strategy applies for edge cases, **Then** system handles sequences at dataset boundaries by zero-padding incomplete windows at the end, marking padded sequences for potential exclusion
5. **Given** complete sequence tensors, **When** data persistence executes, **Then** system saves train_sequences.npy and test_sequences.npy in numpy format with corresponding train_labels.npy and test_labels.npy, ready for DL model loading

---

### Edge Cases

- **Insufficient data for window**: What happens when remaining samples < window size at dataset end? → Zero-pad and flag for potential exclusion
- **Class imbalance within window**: How to assign label when window contains mixed classes (e.g., 60% class 0, 40% class 1)? → Use majority voting, assign label of dominant class
- **All nulls in a column**: What if entire sensor axis has missing data? → Drop that feature column entirely and document in preprocessing report
- **Memory constraints with large windows**: How to handle if windowing creates arrays too large for RAM? → Implement batch processing with generator functions to process windows in chunks
- **Non-standard sampling rate**: What if actual sampling rate differs from assumption? → Make sampling rate a configurable parameter, validate against dataset metadata if available

## Requirements *(mandatory)*

### Functional Requirements

**Data Loading & Cleaning (Story 1)**:

- **FR-001**: System MUST load Dataset.csv (27,995 samples) and validate structure contains 9 sensor columns (aX, aY, aZ, gX, gY, gZ, mX, mY, mZ) plus Result column
- **FR-002**: System MUST drop magnetometer columns (mX, mY, mZ) as all values are -1 (sensor disabled)
- **FR-003**: System MUST detect and report null values per column with counts and percentages
- **FR-004**: System MUST handle nulls by dropping rows if < 5% affected, or imputing with column median if >= 5% affected
- **FR-005**: System MUST validate data types (numeric values for sensors, binary 0/1 for Result)

**Normalization & Splitting (Story 1)**:

- **FR-006**: System MUST normalize each of 6 sensor axes independently using standardization (z-score normalization: subtract mean, divide by std)
- **FR-007**: System MUST fit normalization parameters (mean, std) on training set ONLY to prevent data leakage
- **FR-008**: System MUST split data 80/20 (training: 22,396 samples, testing: 5,599 samples) using stratified random sampling
- **FR-009**: System MUST use fixed random seed (e.g., seed=42) for reproducible splits across runs
- **FR-010**: System MUST validate class distribution preservation in train/test sets (both maintain ~45% class 0, ~55% class 1)

**Feature Engineering (Story 2)**:

- **FR-011**: System MUST segment continuous sensor data into overlapping time windows using sliding window approach with 50% overlap
- **FR-012**: System MUST extract 5 statistical features per sensor axis per window: Root Mean Square (RMS), Mean, Standard Deviation, Skewness, Kurtosis
- **FR-013**: System MUST create feature matrix with 30 columns (6 axes × 5 features) plus 1 label column per window
- **FR-014**: System MUST assign window labels using majority voting (label = dominant class within window samples)
- **FR-015**: System MUST validate feature matrices contain no NaN or Inf values before saving

**Sequence Preparation (Story 3)**:

- **FR-016**: System MUST create fixed-length sequences from continuous sensor data using sliding window with 50% overlap
- **FR-017**: System MUST reshape sequences into 3D tensor format (num_windows, sequence_length, 6) suitable for LSTM/CNN input layers
- **FR-018**: System MUST assign each sequence a single label based on majority class within window
- **FR-019**: System MUST handle edge cases at dataset boundaries by zero-padding incomplete sequences and flagging them
- **FR-020**: System MUST save sequence data in numpy binary format (.npy) for efficient loading during DL training

**Data Persistence & Validation (All Stories)**:

- **FR-021**: System MUST save all processed data with clear naming convention: train_X.ext, test_X.ext, train_y.ext, test_y.ext
- **FR-022**: System MUST generate preprocessing report with statistics: original/final sample counts, null handling summary, normalization parameters, class distribution, feature/sequence shapes
- **FR-023**: System MUST validate data integrity: no leakage between train/test, consistent shapes, valid value ranges
- **FR-024**: System MUST store normalization parameters (mean, std per axis) in JSON format (normalization_params.json) for human-readable, portable inference-time preprocessing

### Key Entities

- **Raw Dataset**: Kaggle-sourced CSV with 27,995 samples of 6-axis IMU sensor data (accelerometer + gyroscope) and binary tremor labels (0=healthy, 1=tremor)
- **Preprocessed Dataset**: Cleaned, normalized sensor data split into stratified train/test sets (80/20), ready for windowing
- **Feature Matrix**: 2D table where rows = time windows, columns = 30 statistical features (5 metrics × 6 axes) + label, used for traditional ML models
- **Sequence Tensor**: 3D array (num_windows, sequence_length, 6) of raw normalized sensor readings, used for deep learning models
- **Normalization Parameters**: Mean and standard deviation values per sensor axis, fitted on training data, applied to test/inference data

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Preprocessed data maintains high integrity - zero data leakage between train/test sets verified by checking no sample ID overlap
- **SC-002**: Class distribution preserved - train and test sets both contain 45% ± 2% class 0 and 55% ± 2% class 1 (within 2% tolerance of original distribution)
- **SC-003**: Feature extraction completes efficiently - processing 22,396 training samples into feature matrix completes in under 5 minutes on standard laptop (Intel i5 or equivalent)
- **SC-004**: Sequence preparation produces valid tensors - 100% of generated sequences pass shape validation (correct 3D dimensions) with no NaN values
- **SC-005**: Reproducibility guaranteed - running preprocessing pipeline multiple times with same random seed produces bit-identical train/test splits
- **SC-006**: Data scientists can immediately use outputs - generated feature matrices and sequence tensors load successfully into scikit-learn and TensorFlow/PyTorch without additional transformation
- **SC-007**: Preprocessing documentation is complete - generated report includes all critical information: sample counts at each stage, null handling decisions, normalization parameters, window counts, and data shapes

## Assumptions *(mandatory)*

- **Sampling Rate**: Assuming standard IMU sampling rate of 100 Hz (100 samples per second). This means 1-second windows contain 100 samples. If actual rate differs, window size must be adjusted accordingly.
- **Window Duration**: 1-second windows chosen for feature engineering and sequence preparation based on typical tremor frequency range (4-7 Hz) - 1 second captures multiple tremor cycles.
- **Sequence Length**: Example of 128 samples (~1.28 seconds at 100 Hz) suggested for DL models, provides good context window while keeping computational cost reasonable.
- **Normalization Method**: Using z-score standardization (mean=0, std=1) as it's standard for sensor data and works well with gradient-based optimization in neural networks.
- **Overlap Strategy**: 50% overlap between windows provides good data augmentation (increases training samples) while maintaining temporal diversity.
- **Label Assignment**: For windows spanning class transitions, majority voting assigns label (e.g., 60% class 1 samples → window labeled as class 1).
- **Data Storage**: Processed data stored in local filesystem (backend/ml_data/processed/) in CSV for features and numpy binary format for sequences.
- **Random Seed**: Fixed seed (42) used for all randomization (train/test split, window sampling if stochastic) to ensure reproducibility.
- **No outlier removal**: Keeping all data points unless they're null, assuming sensor calibration was correct during data collection.
- **Binary classification**: Dataset is for binary tremor detection (0/1), not severity classification (mild/moderate/severe).

## Dependencies *(mandatory)*

- **Dataset Availability**: Requires Dataset.csv present at project root (C:\Data from HDD\Graduation Project\Platform\Dataset.csv)
- **Python Environment**: Requires Python 3.8+ with data science libraries installed (numpy, pandas, scipy, scikit-learn)
- **Storage Space**: Requires ~500 MB free space for processed data (raw data ~8 MB, windowed data significantly larger due to overlap)
- **Computational Resources**: Feature extraction and sequence preparation are CPU-intensive - recommend multi-core processor for reasonable processing times

## Out of Scope *(mandatory)*

- **Model Training**: This feature only prepares data; actual ML/DL model training, evaluation, and hyperparameter tuning are separate features
- **Real-time Preprocessing**: Pipeline is designed for batch offline processing; real-time streaming data preprocessing is out of scope
- **Data Augmentation**: Advanced augmentation techniques (synthetic sample generation, noise injection, SMOTE) not included - only sliding window overlap
- **Feature Selection**: No automated feature selection or dimensionality reduction (PCA, feature importance analysis) - all 30 engineered features are kept
- **Cross-validation Splits**: Only single 80/20 train/test split provided; k-fold cross-validation setup is out of scope
- **Data Versioning**: No integration with DVC (Data Version Control) or MLflow for tracking data versions - manual versioning only
- **Automated Hyperparameter Selection**: Window size, overlap, sequence length are fixed parameters - no automated search for optimal values
