# Technical Research: Deep Learning Models Training

**Feature**: 006-dl-models | **Date**: 2026-02-15
**Purpose**: Document technical decisions for LSTM and 1D-CNN training implementation

## Research Summary

This feature builds on Feature 005 (ML Models) by adding deep learning approaches. Research focused on TensorFlow/Keras best practices for time-series classification, model architecture design for tremor detection, and training strategies to achieve ≥95% accuracy.

---

## Decision 1: Early Stopping Configuration

**Decision**: Use EarlyStopping with `monitor='val_loss'`, `patience=10`, `restore_best_weights=True`, `mode='min'`

**Rationale**:
- **Monitor validation loss** (not accuracy): Loss is a smoother metric that detects overfitting earlier. Validation accuracy can plateau while loss continues to decrease, giving false signals.
- **Patience of 10 epochs**: Balances training time vs. convergence. Too low (e.g., 3) risks stopping before model converges, too high (e.g., 20) wastes computation. 10 epochs allows ~3-5 minutes of patience on our dataset.
- **Restore best weights**: Critical for recovering the best model state. Without this, final model could be from an overfit epoch after validation performance degraded.
- **Mode='min'**: Validation loss should minimize (lower is better).

**Alternatives Considered**:
- **Monitor='val_accuracy'**: Rejected because accuracy plateaus can hide overfitting visible in loss curves.
- **Patience=5**: Too aggressive for small datasets where validation metrics are noisy.
- **Patience=15**: Wastes ~5 minutes per model on convergence that's unlikely to happen.

**References**:
- Keras EarlyStopping docs: https://keras.io/api/callbacks/early_stopping/
- Best practices: Goodfellow et al., "Deep Learning" (2016), Chapter 7 (Regularization)

---

## Decision 2: LSTM Architecture Details

**Decision**:
```python
model = Sequential([
    LSTM(64, return_sequences=True, input_shape=(timesteps, 6)),
    Dropout(0.3),
    LSTM(32, return_sequences=False),
    Dropout(0.3),
    Dense(1, activation='sigmoid')
])
model.compile(optimizer=Adam(learning_rate=0.001), loss='binary_crossentropy', metrics=['accuracy'])
```

**Rationale**:
- **Layer 1: LSTM(64, return_sequences=True)**: First layer has more units (64) to learn rich temporal representations. `return_sequences=True` feeds full sequence to second LSTM.
- **Layer 2: LSTM(32, return_sequences=False)**: Second layer has fewer units (32) to distill learned features. `return_sequences=False` outputs final hidden state only.
- **Dropout(0.3)**: Applied after each LSTM to prevent overfitting. 0.3 (30% dropout) is standard for recurrent networks - high enough to regularize, low enough to preserve information.
- **Dense(1, sigmoid)**: Single output neuron with sigmoid for binary classification (0 = no tremor, 1 = tremor).
- **Adam optimizer**: Adaptive learning rate algorithm, default lr=0.001 works well for most problems.
- **Binary crossentropy**: Standard loss function for binary classification.

**Alternatives Considered**:
- **Single LSTM layer**: Rejected because 2 layers achieve better temporal abstraction (first layer learns low-level patterns, second learns high-level patterns).
- **GRU instead of LSTM**: Similar performance but LSTM is more widely adopted and provides better interpretability with cell state.
- **Bidirectional LSTM**: Rejected because tremor detection doesn't require future context (we're classifying windows, not sequences where future helps).

**References**:
- Graves, A. (2012). "Supervised Sequence Labelling with Recurrent Neural Networks"
- LSTM for time-series: https://colah.github.io/posts/2015-08-Understanding-LSTMs/

---

## Decision 3: 1D-CNN Architecture Details

**Decision**:
```python
model = Sequential([
    Conv1D(filters=64, kernel_size=3, activation='relu', input_shape=(timesteps, 6)),
    BatchNormalization(),
    MaxPooling1D(pool_size=2),

    Conv1D(filters=128, kernel_size=3, activation='relu'),
    BatchNormalization(),
    MaxPooling1D(pool_size=2),

    Conv1D(filters=256, kernel_size=3, activation='relu'),
    BatchNormalization(),
    MaxPooling1D(pool_size=2),

    Flatten(),
    Dense(128, activation='relu'),
    Dropout(0.5),
    Dense(1, activation='sigmoid')
])
model.compile(optimizer=Adam(learning_rate=0.001), loss='binary_crossentropy', metrics=['accuracy'])
```

**Rationale**:
- **3 Conv1D layers with increasing filters (64→128→256)**: Standard CNN pattern - deeper layers learn more abstract features. More filters capture richer representations.
- **Kernel size 3**: Small kernels (3 timesteps) capture local temporal patterns. Larger kernels (5, 7) would smooth too much detail for tremor detection.
- **BatchNormalization after each Conv1D**: Stabilizes training by normalizing activations, enables higher learning rates, reduces internal covariate shift.
- **MaxPooling1D(2) after each conv block**: Downsamples by 2x, reduces sequence length, provides translation invariance for tremor patterns.
- **ReLU activation**: Standard for CNNs, prevents vanishing gradients.
- **Dense(128)**: Fully connected layer for classification after convolutional feature extraction.
- **Dropout(0.5)**: Aggressive dropout on dense layer (50%) prevents overfitting common in fully connected layers.

**Alternatives Considered**:
- **2 Conv1D layers**: Rejected because 3 layers provide better hierarchical feature learning for complex temporal patterns.
- **GlobalAveragePooling instead of Flatten**: Rejected because Flatten preserves more spatial information needed for tremor classification.
- **Residual connections**: Rejected for MVP - adds complexity without proven benefit on small datasets.

**References**:
- Krizhevsky et al. (2012). "ImageNet Classification with Deep Convolutional Neural Networks" (AlexNet)
- 1D-CNN for time-series: Wang et al. (2017). "Time Series Classification from Scratch with Deep Neural Networks"

---

## Decision 4: Data Preprocessing and Splitting

**Decision**: Load sequences from Feature 004, split train set into train/validation (80/20), use original test set for final evaluation.

**Rationale**:
- **No additional preprocessing**: Feature 004 already normalized and windowed the data. Deep learning models work directly on these sequences.
- **80/20 train/validation split**: Standard split ratio. With ~446 training samples, this gives ~357 train / ~89 validation, sufficient for early stopping.
- **Stratified split**: Preserve class distribution in train/validation splits (use `train_test_split` with `stratify=y_train`).
- **Held-out test set**: Original test set from Feature 004 (~110 samples) used only for final evaluation, never for early stopping or hyperparameter tuning.

**Alternatives Considered**:
- **K-fold cross-validation**: Rejected because early stopping needs a fixed validation set. K-fold is incompatible with EarlyStopping callback.
- **90/10 split**: Rejected because validation set would be too small (~45 samples) for reliable early stopping signals.

**Implementation**:
```python
from sklearn.model_selection import train_test_split

X_train, y_train = np.load('train_sequences.npy'), np.load('train_labels.npy')
X_test, y_test = np.load('test_sequences.npy'), np.load('test_labels.npy')

X_train_split, X_val, y_train_split, y_val = train_test_split(
    X_train, y_train, test_size=0.2, stratify=y_train, random_state=42
)
```

---

## Decision 5: Model Export Format (.h5 vs .keras)

**Decision**: Use `.h5` format (HDF5) for model export.

**Rationale**:
- **Wider compatibility**: .h5 format is supported by TensorFlow 2.x and older versions, enabling broader model reuse.
- **Tooling support**: More visualization and analysis tools support .h5 (e.g., Netron, TensorBoard).
- **Proven stability**: .h5 has been the standard Keras format since 2015, mature and battle-tested.
- **Size**: .h5 and .keras have similar file sizes (both use compression).

**Alternatives Considered**:
- **.keras format**: Newer native format (TensorFlow 2.13+). Rejected because it's less mature and has limited tooling support. Potential benefits (better future compatibility) don't outweigh current stability risks.
- **.pb format (SavedModel)**: TensorFlow's serving format. Rejected because it's more complex (directory structure) and overkill for local model storage. Better suited for production serving (Feature 007).

**Implementation**:
```python
model.save('backend/dl_models/models/lstm_model.h5')  # Save as .h5
loaded_model = tf.keras.models.load_model('backend/dl_models/models/lstm_model.h5')  # Load
```

---

## Decision 6: Training Hyperparameters

**Decision**:
- **Batch size**: 32
- **Epochs**: 100 (max, early stopping will halt earlier)
- **Validation split**: 20% of training data
- **Learning rate**: 0.001 (Adam default)
- **Random seed**: 42 (for reproducibility)

**Rationale**:
- **Batch size 32**: Standard for small datasets. Provides good gradient estimates without excessive memory usage. Powers of 2 optimize GPU computation (even on CPU).
- **Max epochs 100**: High ceiling to allow full convergence. Early stopping will halt training between 15-50 epochs typically.
- **Learning rate 0.001**: Adam's default, works well for most problems. No need to tune for MVP.
- **Random seed 42**: Ensures reproducibility across runs (TensorFlow random ops, NumPy splits).

**Alternatives Considered**:
- **Batch size 64**: Rejected because small dataset (357 train samples) would have only ~6 batches per epoch, making gradient estimates noisy.
- **Batch size 16**: More stable gradients but slower training (doubles number of weight updates per epoch).
- **Learning rate tuning**: Rejected for MVP - default works, tuning requires additional experiments.

---

## Decision 7: Evaluation Metrics

**Decision**: Compute accuracy, precision, recall, F1-score, and confusion matrix. Set `meets_threshold` flag based on accuracy ≥95%.

**Rationale**:
- **Accuracy**: Primary metric from spec (≥95% requirement). Simple, interpretable.
- **Precision**: Important for tremor detection - false positives could cause unnecessary medical concern.
- **Recall**: Critical for tremor detection - false negatives could miss real tremors requiring intervention.
- **F1-score**: Harmonic mean of precision/recall, useful for imbalanced datasets.
- **Confusion matrix**: Shows class-specific performance (true positives, false positives, etc.).
- **Meets threshold flag**: Boolean in metadata indicating if model passed 95% accuracy requirement.

**Alternatives Considered**:
- **AUC-ROC**: Rejected because binary classification with balanced classes doesn't require ROC analysis. Accuracy is sufficient.
- **MCC (Matthews Correlation Coefficient)**: More robust for imbalanced data, but our classes are balanced (~50/50 split).

**Implementation**: Reuse `evaluation.py` from Feature 005 (ML Models) - same metrics computation logic.

---

## Decision 8: Reproducibility Strategy

**Decision**: Set random seeds for TensorFlow, NumPy, and Python at script start. Document TensorFlow version in metadata.

**Rationale**:
- **Deterministic training**: Same data + same code + same seeds = identical results. Critical for debugging and validation.
- **Cross-platform reproducibility**: Caveat: GPU training introduces non-determinism (CUDA operations). CPU training is fully reproducible.
- **Version tracking**: TensorFlow version in metadata enables reproducing results if API changes in future versions.

**Implementation**:
```python
import numpy as np
import tensorflow as tf
import random

# Set seeds for reproducibility
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)
tf.random.set_seed(RANDOM_SEED)
random.seed(RANDOM_SEED)

# For full determinism on CPU (disables GPU non-deterministic ops)
import os
os.environ['TF_DETERMINISTIC_OPS'] = '1'
```

**Limitations**:
- GPU training: CUDA operations (cuDNN convolutions) are non-deterministic. Set `TF_DETERMINISTIC_OPS=1` to force determinism but with ~10-50% performance penalty.
- For MVP: Accept GPU non-determinism as acceptable variance. Document in README.

---

## Implementation Notes

**Training Pipeline** (both models follow same pattern):
1. Load sequence data from Feature 004 (`train_sequences.npy`, `test_sequences.npy`)
2. Validate data shapes: (samples, timesteps, 6 features)
3. Split training data into train/validation (80/20 stratified)
4. Build model architecture (LSTM or 1D-CNN)
5. Compile model (Adam, binary_crossentropy, accuracy)
6. Set up EarlyStopping callback (monitor='val_loss', patience=10)
7. Train model with validation data (batch_size=32, epochs=100)
8. Evaluate on test set (accuracy, precision, recall, F1, confusion matrix)
9. Save model as .h5 and metadata as .json
10. Log training history and final metrics

**Utility Modules**:
- `model_io.py`: Data loading, model save/load, metadata creation (similar to Feature 005)
- `evaluation.py`: Metrics computation (reuse from Feature 005)
- `architectures.py`: Model builder functions (`build_lstm_model()`, `build_cnn_1d_model()`)

**Next Steps**:
- Phase 1: Generate data-model.md (entities: Model, TrainingHistory, Metadata)
- Phase 1: Generate quickstart.md (validation scenarios for both models)
- Phase 2: Generate tasks.md with training scripts organized by user story
