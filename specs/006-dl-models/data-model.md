# Data Model: Deep Learning Models Training

**Feature**: 006-dl-models | **Date**: 2026-02-15
**Purpose**: Define entities and data structures for deep learning model training pipeline

## Entity Definitions

### 1. Deep Learning Model

**Description**: A trained neural network (LSTM or 1D-CNN) with learned weights for tremor classification.

**Attributes**:
- `model_type`: String - Model architecture type ("LSTM" or "CNN1D")
- `architecture`: Dictionary - Layer configuration (layer types, units/filters, activations, dropout rates)
- `compiled_config`: Dictionary - Compilation settings (optimizer, learning rate, loss function, metrics)
- `weights`: Binary blob - Trained model parameters (stored in .h5 file)
- `input_shape`: Tuple - Expected input dimensions (timesteps, features)
- `output_shape`: Tuple - Output dimensions (1 for binary classification)

**Serialization**:
- **File format**: .h5 (HDF5) format via `model.save()`
- **Location**: `backend/dl_models/models/[model_name].h5`
- **Size**: 50-500 MB depending on architecture complexity

**Relationships**:
- Associated with exactly one **TrainingHistory** (1:1)
- Associated with exactly one **ModelMetadata** (1:1)

**Validation Rules**:
- Model must accept 3D input: (batch_size, timesteps, 6 features)
- Model must output 2D shape: (batch_size, 1) with sigmoid activation
- Model must be loadable via `tf.keras.models.load_model()`

**State Transitions**:
```
[Untrained] --fit()--> [Training] --early_stop/max_epochs--> [Trained] --save()--> [Serialized]
                                         |
                                         v
                                    [Restored to Best Weights]
```

**Example** (LSTM):
```python
{
    "model_type": "LSTM",
    "architecture": {
        "layers": [
            {"type": "LSTM", "units": 64, "return_sequences": true, "dropout": 0.0, "recurrent_dropout": 0.0},
            {"type": "Dropout", "rate": 0.3},
            {"type": "LSTM", "units": 32, "return_sequences": false, "dropout": 0.0, "recurrent_dropout": 0.0},
            {"type": "Dropout", "rate": 0.3},
            {"type": "Dense", "units": 1, "activation": "sigmoid"}
        ]
    },
    "compiled_config": {
        "optimizer": "adam",
        "learning_rate": 0.001,
        "loss": "binary_crossentropy",
        "metrics": ["accuracy"]
    },
    "input_shape": [50, 6],
    "output_shape": [1]
}
```

---

### 2. Training History

**Description**: Records the training process including per-epoch metrics and early stopping decisions.

**Attributes**:
- `epochs_completed`: Integer - Number of epochs actually trained (may be less than max_epochs due to early stopping)
- `stopped_early`: Boolean - Whether early stopping triggered
- `stopped_epoch`: Integer - Epoch at which early stopping halted training (0 if trained to max_epochs)
- `best_epoch`: Integer - Epoch with best validation loss (weights restored to this state)
- `loss_history`: Array[Float] - Training loss per epoch
- `accuracy_history`: Array[Float] - Training accuracy per epoch
- `val_loss_history`: Array[Float] - Validation loss per epoch
- `val_accuracy_history`: Array[Float] - Validation accuracy per epoch
- `training_time_seconds`: Float - Total training duration

**Serialization**:
- Embedded in ModelMetadata JSON file
- Used for plotting loss/accuracy curves during analysis

**Relationships**:
- Belongs to exactly one **Deep Learning Model** (1:1)

**Validation Rules**:
- All history arrays must have same length (epochs_completed)
- Loss values must be non-negative
- Accuracy values must be in range [0.0, 1.0]
- stopped_epoch <= epochs_completed

**Example**:
```python
{
    "epochs_completed": 23,
    "stopped_early": true,
    "stopped_epoch": 23,
    "best_epoch": 13,
    "loss_history": [0.693, 0.512, 0.387, ..., 0.156],
    "accuracy_history": [0.52, 0.74, 0.83, ..., 0.94],
    "val_loss_history": [0.701, 0.489, 0.423, ..., 0.201],
    "val_accuracy_history": [0.49, 0.73, 0.81, ..., 0.91],
    "training_time_seconds": 342.5
}
```

---

### 3. Model Metadata

**Description**: Human-readable record of model properties, performance, and training configuration.

**Attributes**:
- `model_type`: String - Model architecture identifier
- `architecture_summary`: String - Output of `model.summary()` as text
- `hyperparameters`: Dictionary - All training configuration (learning rate, batch size, dropout rates, etc.)
- `performance_metrics`: Dictionary - Test set evaluation results (accuracy, precision, recall, F1, confusion matrix)
- `training_info`: Dictionary - Training details (timestamp, dataset sizes, TensorFlow version, Python version, GPU availability)
- `early_stopping_config`: Dictionary - Early stopping parameters (patience, monitor, restore_best_weights)
- `training_history`: **TrainingHistory** object - Embedded training history
- `meets_threshold`: Boolean - Flag indicating if test accuracy >= 95%

**Serialization**:
- **File format**: JSON
- **Location**: `backend/dl_models/models/[model_name].json`
- **Size**: 5-20 KB

**Relationships**:
- Belongs to exactly one **Deep Learning Model** (1:1)
- Contains exactly one **TrainingHistory** (1:1)
- Contains exactly one **PerformanceMetrics** (1:1)
- Contains exactly one **ConfusionMatrix** (1:1)

**Validation Rules**:
- `model_type` must be in ["LSTM", "CNN1D"]
- `performance_metrics.accuracy` must be in range [0.0, 1.0]
- `meets_threshold` must equal (performance_metrics.accuracy >= 0.95)
- `training_info.timestamp` must be ISO 8601 format

**Example** (LSTM):
```json
{
    "model_type": "LSTM",
    "architecture_summary": "Model: \"sequential\"\n_________________________________________________________________\nLayer (type)                 Output Shape              Param #\n=================================================================\nlstm (LSTM)                  (None, 50, 64)            18176\ndropout (Dropout)            (None, 50, 64)            0\nlstm_1 (LSTM)                (None, 32)                12416\ndropout_1 (Dropout)          (None, 32)                0\ndense (Dense)                (None, 1)                 33\n=================================================================\nTotal params: 30,625\nTrainable params: 30,625\nNon-trainable params: 0\n_________________________________________________________________",
    "hyperparameters": {
        "lstm_units_layer1": 64,
        "lstm_units_layer2": 32,
        "dropout_rate": 0.3,
        "optimizer": "adam",
        "learning_rate": 0.001,
        "batch_size": 32,
        "max_epochs": 100,
        "early_stopping_patience": 10,
        "random_state": 42
    },
    "performance_metrics": {
        "accuracy": 0.964,
        "precision": 0.957,
        "recall": 0.971,
        "f1_score": 0.964,
        "confusion_matrix": [[53, 3], [2, 52]],
        "meets_threshold": true
    },
    "early_stopping_config": {
        "monitor": "val_loss",
        "patience": 10,
        "restore_best_weights": true,
        "mode": "min"
    },
    "training_history": {
        "epochs_completed": 23,
        "stopped_early": true,
        "stopped_epoch": 23,
        "best_epoch": 13,
        "loss_history": [0.693, 0.512, ..., 0.156],
        "accuracy_history": [0.52, 0.74, ..., 0.94],
        "val_loss_history": [0.701, 0.489, ..., 0.201],
        "val_accuracy_history": [0.49, 0.73, ..., 0.91],
        "training_time_seconds": 342.5
    },
    "training_info": {
        "timestamp": "2026-02-15T14:30:22",
        "training_samples": 357,
        "validation_samples": 89,
        "test_samples": 110,
        "sequence_length": 50,
        "num_features": 6,
        "tensorflow_version": "2.13.0",
        "python_version": "3.11.5",
        "gpu_available": false,
        "random_state": 42,
        "data_source": "backend/ml_data/processed/train_sequences.npy, test_sequences.npy, train_seq_labels.npy, test_seq_labels.npy"
    }
}
```

---

### 4. Sequence Data

**Description**: 3D NumPy arrays representing time-series IMU sensor readings for model input.

**Attributes**:
- `sequences`: NumPy ndarray - Shape (num_samples, timesteps, num_features)
- `labels`: NumPy ndarray - Shape (num_samples,) with binary values (0 or 1)
- `num_samples`: Integer - Number of sequences in the dataset
- `timesteps`: Integer - Number of time steps per sequence (e.g., 50, 100)
- `num_features`: Integer - Number of sensor channels per timestep (6: aX, aY, aZ, gX, gY, gZ)

**Serialization**:
- **File format**: .npy (NumPy binary format)
- **Location**: `backend/ml_data/processed/` (produced by Feature 004)
- **Files**:
  - `train_sequences.npy`: Training sequences
  - `train_labels.npy`: Training labels
  - `test_sequences.npy`: Test sequences
  - `test_labels.npy`: Test labels

**Relationships**:
- Input to **Deep Learning Model** training and evaluation
- Produced by Feature 004 (ML/DL Data Preparation)

**Validation Rules**:
- sequences.shape[0] == labels.shape[0] (same number of samples)
- sequences.shape[2] == 6 (accelerometer + gyroscope, 3 axes each)
- labels must contain only 0 or 1 (binary classification)
- No NaN or Inf values in sequences or labels

**Example**:
```python
# Load sequence data
train_sequences = np.load('backend/ml_data/processed/train_sequences.npy')
train_labels = np.load('backend/ml_data/processed/train_seq_labels.npy')

# Shape validation
assert train_sequences.shape == (446, 50, 6)  # 446 samples, 50 timesteps, 6 features
assert train_labels.shape == (446,)           # 446 binary labels
assert set(train_labels) <= {0, 1}            # Only 0 and 1
```

---

### 5. Performance Metrics

**Description**: Evaluation results measuring model's classification performance on test set.

**Attributes**:
- `accuracy`: Float - Overall classification accuracy (correct / total)
- `precision`: Float - Precision score (macro-averaged for binary classification)
- `recall`: Float - Recall score (macro-averaged for binary classification)
- `f1_score`: Float - F1 score (harmonic mean of precision and recall)
- `confusion_matrix`: **ConfusionMatrix** - 2x2 matrix of classification results
- `meets_threshold`: Boolean - Whether accuracy >= 95%

**Serialization**:
- Embedded in ModelMetadata JSON file

**Relationships**:
- Belongs to exactly one **ModelMetadata** (1:1)
- Contains exactly one **ConfusionMatrix** (1:1)

**Validation Rules**:
- All metric values must be in range [0.0, 1.0]
- meets_threshold == (accuracy >= 0.95)

**Example**:
```python
{
    "accuracy": 0.964,
    "precision": 0.957,
    "recall": 0.971,
    "f1_score": 0.964,
    "confusion_matrix": [[53, 3], [2, 52]],
    "meets_threshold": true
}
```

---

### 6. Confusion Matrix

**Description**: 2x2 matrix showing classification results for binary tremor detection.

**Attributes**:
- `true_negatives`: Integer - Correctly predicted no-tremor samples
- `false_positives`: Integer - No-tremor samples incorrectly predicted as tremor
- `false_negatives`: Integer - Tremor samples incorrectly predicted as no-tremor
- `true_positives`: Integer - Correctly predicted tremor samples

**Serialization**:
- Stored as nested array in ModelMetadata JSON: `[[TN, FP], [FN, TP]]`

**Relationships**:
- Belongs to exactly one **PerformanceMetrics** (1:1)

**Validation Rules**:
- All values must be non-negative integers
- Sum of all cells == total test samples

**Example**:
```python
# Confusion matrix format: [[TN, FP], [FN, TP]]
confusion_matrix = [[53, 3], [2, 52]]

# Interpretation:
# - True Negatives (TN): 53 no-tremor samples correctly classified
# - False Positives (FP): 3 no-tremor samples incorrectly classified as tremor
# - False Negatives (FN): 2 tremor samples incorrectly classified as no-tremor
# - True Positives (TP): 52 tremor samples correctly classified
# Total: 53 + 3 + 2 + 52 = 110 test samples
```

---

## Entity Relationships Diagram

```
┌─────────────────────────┐
│  Sequence Data          │
│  (Feature 004 output)   │
│  - train_sequences.npy  │
│  - train_labels.npy     │
│  - test_sequences.npy   │
│  - test_labels.npy      │
└────────────┬────────────┘
             │ input to
             ▼
┌─────────────────────────┐
│  Deep Learning Model    │──────┐
│  (.h5 file)             │      │ 1:1
│  - architecture         │      │
│  - weights              │      │
│  - compiled_config      │      │
└─────────────────────────┘      │
                                 ▼
                    ┌────────────────────────┐
                    │  Model Metadata        │
                    │  (.json file)          │
                    │  - model_type          │
                    │  - hyperparameters     │
                    │  - training_info       │
                    └───┬────────────────┬───┘
                        │ contains       │ contains
                        │ 1:1            │ 1:1
                        ▼                ▼
            ┌───────────────────┐   ┌──────────────────┐
            │ Training History  │   │ Performance      │
            │ - epochs          │   │ Metrics          │
            │ - loss_history    │   │ - accuracy       │
            │ - val_loss_history│   │ - precision      │
            │ - stopped_epoch   │   │ - recall         │
            │ - best_epoch      │   │ - f1_score       │
            └───────────────────┘   └────────┬─────────┘
                                             │ contains
                                             │ 1:1
                                             ▼
                                    ┌────────────────────┐
                                    │ Confusion Matrix   │
                                    │ - TN, FP, FN, TP   │
                                    └────────────────────┘
```

---

## Data Flow

**Training Flow**:
1. **Load** Sequence Data from Feature 004 outputs
2. **Split** training data into train/validation (80/20)
3. **Build** Deep Learning Model architecture
4. **Train** model with early stopping monitoring validation loss
5. **Restore** best weights from best epoch
6. **Evaluate** model on test set → Performance Metrics
7. **Create** Model Metadata with Training History and Performance Metrics
8. **Save** model as .h5 file and metadata as .json file

**Inference Flow** (for Feature 007 - Model Serving):
1. **Load** Deep Learning Model from .h5 file
2. **Load** Model Metadata from .json file (optional, for verification)
3. **Preprocess** incoming sensor data into sequence format
4. **Predict** using `model.predict(sequence)` → binary label (0 or 1)
5. **Return** prediction to API endpoint

---

## Implementation Notes

**File Naming Convention**:
- LSTM: `lstm_model.h5` (model) + `lstm_model.json` (metadata)
- 1D-CNN: `cnn_1d_model.h5` (model) + `cnn_1d_model.json` (metadata)

**Storage Locations**:
- Models: `backend/dl_models/models/` (gitignored)
- Sequence data: `backend/ml_data/processed/` (gitignored, from Feature 004)

**Metadata Schema Version**: 1.0.0 (matches Feature 005 ML Models schema for consistency)
