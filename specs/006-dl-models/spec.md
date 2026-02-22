# Feature Specification: Deep Learning Models Training

**Feature Branch**: `006-dl-models`
**Created**: 2026-02-15
**Status**: Draft
**Input**: User description: "2.3 Deep Learning Models - 2.3.1 LSTM Model: Build LSTM with 2 layers (64, 32 units), dropout 0.3, binary output. Train with early stopping. Export .h5/.keras. 2.3.2 1D-CNN Model: Build 1D-CNN with 3 Conv1D layers + BatchNorm + MaxPool + Dense classifier. Train with early stopping. Export .h5/.keras."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - LSTM Model Training (Priority: P1-MVP)

As a data scientist working on the TremoAI platform, I need to train an LSTM (Long Short-Term Memory) model on sequential tremor sensor data to classify tremor vs. no tremor patterns with high accuracy, so that the platform can leverage temporal dependencies in the time-series data for more accurate predictions.

**Why this priority**: LSTM models are the foundation for sequence-based deep learning. They excel at capturing temporal patterns and dependencies in time-series data, which is critical for tremor detection where the sequence of sensor readings matters. This is the MVP because it establishes the deep learning training pipeline and validates that sequence data can achieve the required accuracy threshold (≥95%).

**Independent Test**: Can be fully tested by running the LSTM training script on the sequence data produced by Feature 004, evaluating the trained model on the test set, verifying accuracy ≥95%, and confirming the model exports correctly as .h5/.keras format with accompanying metadata JSON.

**Acceptance Scenarios**:

1. **Given** sequence training data exists at `backend/ml_data/processed/train_sequences.npy` and `train_seq_labels.npy`, **When** the LSTM training script is executed, **Then** the model trains for multiple epochs with early stopping monitoring validation loss, achieves ≥95% test accuracy, and exports `lstm_model.h5` + `lstm_model.json` to `backend/dl_models/models/`

2. **Given** a trained LSTM model file exists, **When** the model is loaded using `tf.keras.models.load_model()`, **Then** the model successfully loads, accepts 3D sequence input (batch, timesteps, features), and produces binary predictions (0 or 1)

3. **Given** training completes, **When** the metadata JSON is examined, **Then** it contains architecture details (2 LSTM layers with 64/32 units, dropout 0.3), training history (loss curves, accuracy curves), performance metrics (accuracy, precision, recall, F1), and early stopping info (stopped epoch, best epoch)

---

### User Story 2 - 1D-CNN Model Training (Priority: P2)

As a data scientist, I need to train a 1D Convolutional Neural Network (1D-CNN) model on sequential tremor data to classify tremor patterns using convolutional feature extraction, so that I can compare CNN-based approaches against LSTM and potentially achieve faster inference times.

**Why this priority**: 1D-CNNs provide an alternative deep learning approach for sequence data. They use convolutional filters to extract local patterns and are often faster to train and infer compared to LSTMs. This is P2 because it builds on the training pipeline established in US1, providing a second model for ensemble methods (Feature 008) and enabling performance comparisons to select the best model for deployment.

**Independent Test**: Can be fully tested by running the 1D-CNN training script on the same sequence data, evaluating on the test set, verifying ≥95% accuracy, and confirming correct export of model files and metadata.

**Acceptance Scenarios**:

1. **Given** sequence training data exists, **When** the 1D-CNN training script is executed, **Then** the model trains with 3 Conv1D layers + BatchNormalization + MaxPooling + Dense classifier, achieves ≥95% test accuracy, and exports `cnn_1d_model.h5` + `cnn_1d_model.json`

2. **Given** both LSTM and 1D-CNN models are trained, **When** the comparison script is run, **Then** it generates a report showing side-by-side metrics (accuracy, precision, recall, F1, training time, inference time) and recommends the best model for deployment

3. **Given** a trained 1D-CNN model, **When** inference is performed on 10 test sequences, **Then** predictions complete in <1 second total and match the expected labels with ≥95% accuracy

---

### Edge Cases

- **Training fails to converge**: What happens when the model doesn't reach 95% accuracy after maximum epochs? System should log warning, export model with `meets_threshold: false` flag, and continue (not crash).

- **Early stopping triggers too early**: What if validation loss plateaus at 90% accuracy and early stopping halts training prematurely? System should use reasonable patience (e.g., 10-15 epochs) and restore best weights from the best epoch.

- **GPU not available**: How does training proceed if TensorFlow cannot access GPU? System should automatically fall back to CPU training (with warning logged) and still complete successfully, though training time will increase.

- **Model export fails**: What if model.save() fails due to disk space or permissions? System should catch the exception, log clear error message with path and reason, and exit with non-zero code.

- **Sequence data shape mismatch**: What if sequence data has unexpected dimensions (e.g., wrong number of timesteps)? System should validate input shapes before training and raise clear ValueError with expected vs. actual shapes.

- **Overfitting detected**: What if training accuracy is 99% but validation accuracy is 60%? Early stopping based on validation loss should prevent this, but system should also log a warning if train-val accuracy gap exceeds 10%.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST load sequence data from Feature 004 outputs (`train_sequences.npy`, `test_sequences.npy`, `train_labels.npy`, `test_labels.npy`)

- **FR-002**: System MUST build an LSTM model with exactly 2 LSTM layers (64 units, 32 units), dropout rate 0.3, and a Dense output layer with sigmoid activation for binary classification

- **FR-003**: System MUST build a 1D-CNN model with exactly 3 Conv1D layers (with appropriate filters), BatchNormalization layers after each Conv1D, MaxPooling1D layers, Flatten layer, and Dense output layer with sigmoid activation

- **FR-004**: System MUST compile both models with binary cross-entropy loss, Adam optimizer, and accuracy metric

- **FR-005**: System MUST train models with EarlyStopping callback monitoring validation loss with patience of 10 epochs (balances convergence time vs. overfitting prevention)

- **FR-006**: System MUST split training data into train/validation sets (80/20 split) for early stopping monitoring

- **FR-007**: System MUST evaluate trained models on held-out test set and compute accuracy, precision, recall, F1-score, and confusion matrix

- **FR-008**: System MUST export trained models in either .h5 or .keras format (TensorFlow/Keras native formats)

- **FR-009**: System MUST export model metadata as JSON containing: model architecture (layer types, units, hyperparameters), training history (loss/accuracy per epoch), performance metrics, early stopping info (stopped epoch, best epoch), training time, and TensorFlow version

- **FR-010**: System MUST validate that test accuracy meets ≥95% threshold and set `meets_threshold` boolean flag in metadata

- **FR-011**: System MUST create a comparison script that loads both model metadata files and generates a side-by-side report showing metrics and recommending the best model

- **FR-012**: System MUST provide comprehensive documentation (README.md) with usage examples, architecture diagrams, hyperparameter explanations, troubleshooting guide, and integration notes for Feature 007 (model serving)

- **FR-013**: System MUST use consistent random seed (e.g., `tf.random.set_seed(42)`, `np.random.seed(42)`) for reproducibility

- **FR-014**: System MUST log training progress with clear messages showing current epoch, loss, accuracy, and validation metrics

- **FR-015**: System MUST validate that exported models can be successfully loaded and used for inference on sample data

### Key Entities

- **Deep Learning Model**: Represents a trained neural network with architecture definition (layers, units, activations, dropout), compiled configuration (loss function, optimizer, metrics), and trained weights. Can be serialized to .h5/.keras format for persistence.

- **Training History**: Captures the training process including per-epoch metrics (loss, accuracy, val_loss, val_accuracy), early stopping decision (stopped epoch, best epoch restored), and training time. Used for analyzing convergence and diagnosing overfitting.

- **Model Metadata**: Human-readable record of model properties including architecture summary (model.summary() output), hyperparameters (learning rate, batch size, dropout), performance metrics (test accuracy, precision, recall, F1, confusion matrix), training configuration (epochs, early stopping patience), and environment info (TensorFlow version, Python version, GPU availability).

- **Sequence Data**: 3D NumPy arrays (samples, timesteps, features) representing time-series IMU sensor readings. Input to deep learning models. Produced by Feature 004 preprocessing pipeline.

- **Confusion Matrix**: 2x2 matrix showing true positives, false positives, true negatives, false negatives for binary classification. Used to compute precision, recall, and identify class-specific performance issues.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Both LSTM and 1D-CNN models achieve ≥95% accuracy on the held-out test set, demonstrating that deep learning models can match or exceed traditional ML performance from Feature 005

- **SC-002**: Training for both models completes in <15 minutes per model on standard laptop hardware (total <30 minutes), ensuring rapid iteration and experimentation during development

- **SC-003**: Trained models accept 3D sequence input (batch, timesteps, features) and produce binary predictions (0 or 1), validating correct architecture for time-series classification

- **SC-004**: Exported model files (.h5/.keras) can be loaded in a fresh Python session and used for inference without retraining, confirming successful model serialization

- **SC-005**: Early stopping successfully prevents overfitting by monitoring validation loss and restoring weights from the best epoch, ensuring generalization to unseen data

- **SC-006**: Model inference time for a single sequence is <100ms, enabling near real-time predictions for the TremoAI platform (Feature 007)

- **SC-007**: Comparison report clearly identifies the best-performing model (LSTM vs. 1D-CNN) based on accuracy and training/inference time, guiding deployment decisions

## Assumptions *(optional)*

- Feature 004 (ML/DL Data Preparation) has successfully generated sequence data files (`train_sequences.npy`, `test_sequences.npy`, `train_seq_labels.npy`, `test_seq_labels.npy`) in `backend/ml_data/processed/`

- Sequence data has shape (samples, timesteps, features) where timesteps is the window size (e.g., 50-100) and features is the number of sensor channels (6: aX, aY, aZ, gX, gY, gZ)

- TensorFlow ≥2.13.0 and Keras are installed and available in the backend Python environment (per constitution)

- NumPy and scikit-learn are available for data loading and metrics computation (already present from Feature 005)

- Training will use CPU by default, but if GPU is available (CUDA-enabled), TensorFlow will automatically use it for faster training

- Early stopping patience is set to 10 epochs (balances convergence time vs. overfitting prevention - can be adjusted via command-line argument if needed)

- Batch size for training will be 32 by default (standard for small datasets)

- Models will use Adam optimizer with default learning rate 0.001 (can be tuned if needed)

## Dependencies *(optional)*

- **Feature 004 (ML/DL Data Preparation)**: Provides sequence data files required for training. Must be completed before this feature.

- **Feature 005 (ML Models Training)**: Provides reference implementation patterns for training scripts, model I/O utilities, and evaluation metrics. No direct code dependency, but architectural patterns are reused.

## Out of Scope *(optional)*

- Hyperparameter optimization (grid search, random search, Bayesian optimization) - models use fixed architectures specified in requirements

- Model ensembling (combining LSTM + 1D-CNN predictions) - deferred to Feature 008

- Transfer learning from pre-trained models - not applicable for custom tremor detection

- Attention mechanisms or Transformer architectures - out of scope for MVP, can be explored in future iterations

- Model compression or quantization for edge deployment - deferred to mobile optimization feature

- Real-time training or online learning - models are trained offline on batch data

- Explainability tools (SHAP, Grad-CAM) for understanding model predictions - deferred to Feature 009
