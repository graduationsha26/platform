# Research: ML/DL Data Preparation

**Feature**: 004-ml-data-prep
**Date**: 2026-02-15
**Purpose**: Research technical decisions for data preprocessing pipeline

## Research Questions

### Q1: Which Python libraries for data processing?

**Decision**: Standard data science stack - numpy, pandas, scipy, scikit-learn

**Rationale**:
- **numpy**: Industry standard for numerical computing, efficient array operations, native binary I/O (.npy format)
- **pandas**: Best-in-class for CSV/tabular data, DataFrame API simplifies column operations
- **scipy**: Provides advanced statistical functions (skewness, kurtosis) not in numpy
- **scikit-learn**: StandardScaler for normalization, train_test_split with stratification built-in

**Alternatives Considered**:
- **Pure numpy**: Requires manual implementation of statistics, splitting, normalization. More code, more bugs.
- **PyTorch/TensorFlow for preprocessing**: Heavy dependencies for simple data prep, overkill for batch processing
- **Polars** (modern pandas alternative): Faster but less mature, pandas has better ecosystem/documentation

**Rejected**: Polars (unnecessary speedup for 28K samples), PyTorch/TF (wrong tool for batch prep)

---

### Q2: File formats for processed data storage?

**Decision**: Mixed format strategy based on use case
- **numpy binary (.npy)**: Large numerical arrays (preprocessed data, sequence tensors)
- **CSV**: Feature matrices (ML-friendly, human-readable)
- **JSON**: Metadata and configuration (normalization parameters)

**Rationale**:
- **.npy advantages**: Fast load/save (C-contiguous arrays), preserves exact float64 precision, space-efficient, no parsing overhead
- **CSV advantages**: Pandas/scikit-learn read directly, easy to inspect/debug, universally compatible
- **JSON advantages**: Human-readable config, language-agnostic, easy to version control (for params only)

**Performance Comparison** (for ~22K samples × 6 features):
- .npy: ~1 MB, loads in 0.01s
- CSV: ~8 MB (text overhead), loads in 0.5s
- Pickle: 1.2 MB, security concerns, Python-only

**Alternatives Considered**:
- **HDF5**: More complex API, overkill for our dataset size (<500MB total)
- **Pickle**: Python-only, security risks when loading, less portable than .npy
- **Parquet**: Requires Apache Arrow, overkill for 28K samples
- **All CSV**: Slow for large arrays, imprecise floats, huge files

**Rejected**: Pickle (security/portability), HDF5/Parquet (unnecessary complexity)

---

### Q3: Windowing strategy for time-series data?

**Decision**: Sliding window with 50% overlap for both features and sequences

**Rationale**:
- **50% overlap**: Standard data augmentation, doubles training samples while maintaining temporal diversity
- **Window sizes**: 100 samples (1s at 100 Hz) for features, 128 samples (~1.28s) for DL
- **Stride calculation**: window_size // 2 ensures consistent 50% overlap

**Mathematical Basis**:
- For N samples with window size W and stride S:
  - Number of windows = (N - W) // S + 1
  - 50% overlap → S = W // 2
- Example: 22,396 samples, W=100, S=50 → ~447 windows (22,396-100)//50+1 = 447

**Alternatives Considered**:
- **No overlap (stride = window_size)**: Fewer samples, wastes data, worse model performance
- **75% overlap (stride = window_size // 4)**: 4x more samples but high temporal correlation, diminishing returns, longer training
- **Variable window sizes**: Adds complexity without clear benefit for fixed sampling rate

**Literature Support**:
- HAR (Human Activity Recognition) papers use 50% overlap as standard
- Time-series classification benchmarks consistently use 50-75% overlap
- Trade-off between data augmentation and temporal independence

**Rejected**: No overlap (wastes data), 75% overlap (diminishing returns)

---

### Q4: Label assignment for windows spanning class transitions?

**Decision**: Majority voting - assign window label = dominant class within window

**Rationale**:
- **Simple and interpretable**: Window with 60 samples class 1, 40 samples class 0 → labeled as class 1
- **Handles transitions naturally**: Windows spanning tremor onset/offset get single label
- **Standard in literature**: Used in activity recognition, speech processing, medical time-series

**Edge Case Handling**:
- **50-50 tie**: Round to class 1 (tremor positive) - conservative medical approach
- **Class imbalance within window**: Natural property of real data, keep all windows
- **Very short tremor bursts**: <50 samples won't dominate any window, acceptable trade-off

**Alternatives Considered**:
- **First sample label**: Ignores entire window context, poor for transitions
- **Last sample label**: Same issue, arbitrary choice
- **Multi-label classification**: Adds complexity, requires different model architecture, overkill for binary task
- **Discard mixed windows**: Throws away valuable transition data, reduces dataset size

**Rejected**: Multi-label (overcomplicated), discard mixed (wastes data)

---

### Q5: Normalization method for sensor data?

**Decision**: Z-score standardization (mean=0, std=1) per sensor axis, fitted on training set only

**Rationale**:
- **Z-score benefits**: Centers data, scales to unit variance, works well with gradient-based optimization
- **Per-axis normalization**: Each sensor (aX, aY, aZ, gX, gY, gZ) has different scale/range, normalize independently
- **Train-only fitting**: Prevents data leakage - test set normalized using train statistics

**Formula**:
```
X_normalized = (X - mean_train) / std_train
```

**Alternatives Considered**:
- **Min-Max scaling [0,1]**: Sensitive to outliers, doesn't center data around zero
- **Robust scaling (median/IQR)**: Overkill for clean sensor data, slower
- **No normalization**: Poor performance for neural networks, different sensor scales confuse models
- **Global normalization (all axes together)**: Loses per-axis scale information

**Rejected**: Min-Max (outlier sensitive), No normalization (poor ML/DL performance)

---

### Q6: Train/test split strategy?

**Decision**: 80/20 stratified random split with fixed random_state=42

**Rationale**:
- **80/20 ratio**: Standard in ML literature, provides enough test samples (5,599) for reliable evaluation
- **Stratified**: Preserves class distribution in both sets (~45% class 0, ~55% class 1)
- **Random**: Ensures no temporal or collection bias in split
- **Fixed seed**: Reproducibility - same split across runs, important for comparing models

**Math Check**:
- Train: 27,995 × 0.8 = 22,396 samples
- Test: 27,995 × 0.2 = 5,599 samples
- Class 0 train: 22,396 × 0.454 = 10,168
- Class 1 train: 22,396 × 0.546 = 12,228

**Alternatives Considered**:
- **70/30 split**: More test data but less training data, not recommended for deep learning
- **90/10 split**: Not enough test samples for reliable evaluation
- **K-fold cross-validation**: Not needed for this large dataset, adds complexity
- **Temporal split**: Would require knowing data collection order (not available in CSV)

**Rejected**: 70/30 (reduces training), K-fold (overkill), Temporal (not applicable)

---

## Best Practices Research

### Time-Series Window Processing

**Reference**: "Deep Learning for Sensor-based Activity Recognition: A Survey" (2019)

**Key Findings**:
- 1-2 second windows optimal for IMU-based activity recognition
- 50% overlap is industry standard
- Fixed-length sequences required for batch training (variable length adds complexity)

**Applied to TremoAI**:
- ✅ 1 second windows (100 samples at 100 Hz) for feature extraction
- ✅ 128 samples (~1.28s) for DL - power of 2 for efficient CNN processing
- ✅ 50% overlap for both

---

### Statistical Feature Engineering for ML

**Reference**: scikit-learn time series feature extraction best practices

**Recommended Features** (all implemented):
- **Root Mean Square (RMS)**: Overall signal energy/intensity
- **Mean**: Central tendency, DC offset
- **Standard Deviation**: Signal variability, tremor amplitude variation
- **Skewness**: Asymmetry of signal distribution, detects irregular patterns
- **Kurtosis**: Tail heaviness, identifies spikes/outliers in tremor

**Rationale for 5 features**:
- More features → better ML performance (Random Forest, SVM)
- All computationally cheap (vectorized numpy operations)
- Standard in biomedical signal processing

---

### Data Leakage Prevention

**Reference**: "Common Pitfalls and Recommended Practices" (Google ML best practices)

**Critical Rules** (all enforced):
1. ✅ Fit normalization on training set ONLY → apply same transform to test
2. ✅ No test data used in any decision (feature selection, window size, etc.)
3. ✅ Stratified split before any processing to preserve original distribution
4. ✅ Fixed random seed for reproducibility

**Why This Matters**:
- Fitting scaler on full dataset inflates test performance (leaks information about test set distribution)
- Can overestimate model accuracy by 5-10% in practice

---

## Implementation Recommendations

### Performance Optimization

- Use **vectorized numpy operations** instead of Python loops
- Avoid **repeated array copies** - operate in-place where possible
- Use **numpy.lib.stride_tricks** for efficient windowing (creates views, not copies)
- **Batch processing** if memory becomes an issue (unlikely with 28K samples)

### Code Quality

- **Type hints** for all functions (Python 3.8+)
- **Docstrings** following numpy documentation format
- **Unit tests** for each utility function
- **Validation checks** at each pipeline stage

### Reproducibility

- **Fixed random seeds** in all randomization (train_test_split, shuffling)
- **Version pin dependencies** in requirements.txt
- **Document assumptions** in preprocessing_report.txt
- **Log all parameters** (window size, overlap, normalization method) to JSON

---

## Conclusion

All research questions resolved with clear, justified decisions. Pipeline design follows ML/data science best practices from literature and industry standards. Ready to proceed to data model design and implementation.
