# Feature Specification: Raw Feature Pipeline Refactoring

**Feature Branch**: `011-raw-feature-pipeline`
**Created**: 2026-02-16
**Status**: Draft
**Input**: User description: "Refactor the feature engineering and model inference pipeline to match the Dataset.csv schema by using only raw sensor features (aX, aY, aZ, gX, gY, gZ) instead of calculated statistics, while maintaining inference latency under 70ms"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Simplified Model Input Schema (Priority: P1) 🎯 MVP

The ML/DL inference pipeline receives raw sensor readings (accelerometer X/Y/Z and gyroscope X/Y/Z) from IoT devices and produces tremor predictions without performing statistical feature calculations (RMS, Mean, Std, Skewness, Kurtosis). This aligns the pipeline with the actual training data schema and eliminates computational overhead from real-time inference.

**Why this priority**: This is the foundation for correct model operation. The current pipeline has a mismatch between training data (6 raw features) and inference pipeline (calculated statistical features), which will cause model failures or incorrect predictions. Fixing this mismatch is critical before any other improvements.

**Independent Test**: Can be fully tested by sending a single sensor reading with 6 values (aX, aY, aZ, gX, gY, gZ) to the inference endpoint and verifying the model produces valid tremor predictions. Success is measured by: (1) prediction completes without errors, (2) latency remains under 70ms, (3) prediction accuracy matches training validation accuracy.

**Acceptance Scenarios**:

1. **Given** the system receives a sensor reading with 6 raw values, **When** the inference pipeline processes it, **Then** the model receives exactly 6 input features (no calculated statistics)
2. **Given** the ML model expects 6-dimensional input, **When** training data is loaded, **Then** only raw sensor columns (aX, aY, aZ, gX, gY, gZ) are extracted
3. **Given** the inference pipeline processes a sensor reading, **When** timing is measured, **Then** total latency is under 70ms
4. **Given** models are retrained with 6 raw features, **When** validation is performed, **Then** model accuracy meets or exceeds previous performance benchmarks

---

### User Story 2 - Consistent Normalization Parameters (Priority: P2)

The normalization parameters (mean and standard deviation) used for scaling input features are calculated from the same 6 raw sensor axes that the model receives during inference. This ensures consistent data preprocessing between training and deployment.

**Why this priority**: After fixing the input schema (P1), we need to ensure the normalization is correct. Incorrect normalization will cause model predictions to drift or fail, even with the correct input dimensions. This is the second most critical fix.

**Independent Test**: Can be tested by comparing normalization parameters file (params.json) to the training dataset statistics. Success means: (1) params.json contains exactly 6 features (aX-gZ), (2) mean/std values match dataset statistics, (3) inference applies same normalization as training.

**Acceptance Scenarios**:

1. **Given** the training dataset (Dataset.csv), **When** normalization parameters are calculated, **Then** params.json contains mean and std for exactly 6 features
2. **Given** the inference pipeline receives raw sensor data, **When** normalization is applied, **Then** it uses the same mean/std values as training
3. **Given** a sensor reading is normalized, **When** compared to manual calculation, **Then** normalized values match expected results within floating-point precision

---

### User Story 3 - Model Retraining with Simplified Features (Priority: P3)

All machine learning models (Random Forest, SVM) and deep learning models (LSTM, CNN) are retrained using only the 6 raw sensor features, ensuring model architecture input layers match the new feature schema.

**Why this priority**: With correct input schema (P1) and normalization (P2) in place, models need to be retrained to work with this simplified feature set. This is lower priority because models can be retrained offline without impacting the running system.

**Independent Test**: Can be tested by training models on Dataset.csv using only 6 features, then validating accuracy against the test set. Success means: (1) models train without errors, (2) validation accuracy is within 5% of original models, (3) model files reflect correct input shape (6 features).

**Acceptance Scenarios**:

1. **Given** the training script loads Dataset.csv, **When** features are selected, **Then** only 6 raw sensor columns are used
2. **Given** a model is trained with 6 features, **When** model architecture is inspected, **Then** input layer expects 6-dimensional vectors
3. **Given** trained models are saved, **When** inference loads them, **Then** model input shape matches inference data shape (6 features)
4. **Given** models are validated on test data, **When** accuracy is measured, **Then** performance meets minimum thresholds (F1 score ≥ 0.85 for tremor detection)

---

### User Story 4 - Real-time Data Flow Alignment (Priority: P4)

The MQTT client and biometric data storage system pass only the 6 raw sensor axes through the pipeline without computing or storing calculated statistical features, reducing storage requirements and processing time.

**Why this priority**: This is an optimization that removes unnecessary data storage and computation. It's lower priority because the system can function correctly even if extra data is stored temporarily, as long as inference uses only the 6 raw features.

**Independent Test**: Can be tested by sending MQTT messages and verifying database records contain only 6 sensor values. Success means: (1) BiometricReading model stores only 6 fields, (2) MQTT messages contain only necessary data, (3) database storage per reading is reduced.

**Acceptance Scenarios**:

1. **Given** the MQTT client receives sensor data, **When** it processes the message, **Then** only 6 raw sensor values are extracted and passed forward
2. **Given** a biometric reading is stored, **When** database is queried, **Then** record contains only 6 sensor fields (no statistical features)
3. **Given** 1000 sensor readings are stored, **When** storage size is measured, **Then** total size is reduced compared to storing 15+ fields

---

### Edge Cases

- **What happens when sensor readings have missing values**: System should reject invalid readings with clear error messages, preventing partial data from corrupting model predictions
- **What happens when model files don't match the 6-feature schema**: System should detect dimension mismatch on startup and fail gracefully with diagnostic error message, preventing silent prediction errors
- **What happens when inference latency exceeds 70ms threshold**: System should log warning but continue processing, alerting operators to performance degradation while maintaining service availability
- **What happens when normalization parameters are missing or corrupted**: System should fail startup validation and refuse to process data until params.json is regenerated correctly
- **What happens when retraining produces lower accuracy than expected**: Training script should halt and report metrics, requiring manual review before deploying degraded models

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept sensor readings with exactly 6 numeric values (aX, aY, aZ, gX, gY, gZ) as model input
- **FR-002**: System MUST NOT calculate or use statistical features (RMS, Mean, Std, Skewness, Kurtosis) during inference
- **FR-003**: Training scripts MUST extract only 6 raw sensor columns from Dataset.csv when loading training data
- **FR-004**: System MUST generate normalization parameters (mean, std) for exactly 6 features and store them in params.json
- **FR-005**: System MUST apply the same normalization during inference as was used during training
- **FR-006**: ML models (Random Forest, SVM) MUST have input shape configured for 6-dimensional feature vectors
- **FR-007**: DL models (LSTM, CNN) MUST have input layers configured for 6-dimensional feature vectors
- **FR-008**: System MUST complete inference (from sensor reading to prediction) in under 70ms
- **FR-009**: MQTT client MUST parse and forward only 6 raw sensor values from incoming messages
- **FR-010**: BiometricReading database model MUST store only 6 sensor fields per reading
- **FR-011**: System MUST validate model input shape on startup and fail if mismatch detected
- **FR-012**: Training script MUST log feature count and names for verification
- **FR-013**: Inference pipeline MUST log actual feature count received for monitoring
- **FR-014**: System MUST maintain prediction accuracy within 5% of previous performance after refactoring
- **FR-015**: System MUST provide clear error messages when receiving data with incorrect feature count

### Key Entities

- **Sensor Reading**: A single timestamped measurement containing 6 numeric values (aX, aY, aZ, gX, gY, gZ) representing raw accelerometer and gyroscope data from the wearable device
- **Normalization Parameters**: Statistical metadata (mean, standard deviation) for each of the 6 sensor axes, calculated from training data and used to scale input features consistently
- **Model Input Vector**: A 6-dimensional numeric array passed to ML/DL models after normalization, representing one sensor reading
- **Trained Model**: Serialized ML (Random Forest, SVM) or DL (LSTM, CNN) model with input layer expecting exactly 6 features

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Inference latency (sensor reading to prediction) remains under 70ms for 95% of requests
- **SC-002**: Model validation accuracy (F1 score) is within 5% of previous performance (target: F1 ≥ 0.85 for tremor detection)
- **SC-003**: System processes 100 consecutive sensor readings without dimension mismatch errors
- **SC-004**: Database storage per biometric reading is reduced by at least 60% (from 15+ fields to 6 fields)
- **SC-005**: Training script completes successfully with 6-feature input and produces valid model files
- **SC-006**: Normalization parameters file (params.json) contains exactly 6 entries (one per feature axis)
- **SC-007**: All four model types (RF, SVM, LSTM, CNN) accept 6-dimensional input without errors
- **SC-008**: System startup validation detects and rejects models with incorrect input dimensions
- **SC-009**: Zero prediction errors due to feature dimension mismatch in 24 hours of continuous operation
- **SC-010**: MQTT message processing extracts exactly 6 sensor values from each message

## Assumptions *(mandatory)*

- **Dataset Schema**: Dataset.csv contains columns named aX, aY, aZ, gX, gY, gZ with numeric sensor data (assumption: column names are standardized)
- **Model Performance**: Models trained with 6 raw features can achieve similar or better accuracy than models with calculated features (assumption: statistical features were not critical for model performance)
- **Latency Budget**: Removing feature calculation logic will reduce inference time by 10-20ms, contributing to meeting the 70ms target (assumption: feature calculation currently consumes measurable time)
- **MQTT Message Format**: MQTT messages contain sensor readings in a consistent format that can be parsed to extract 6 numeric values (assumption: message structure is documented)
- **Model Retraining**: Retraining models is acceptable during this refactoring, and historical predictions will not be invalidated (assumption: model versioning is managed)
- **No Data Loss**: Existing stored biometric readings with 15+ fields can coexist with new 6-field format, or migration is planned separately (assumption: backwards compatibility or migration strategy exists)
- **Normalization Method**: Z-score normalization (x - mean) / std is the appropriate method for this sensor data (assumption: this is industry standard for IMU data)

## Dependencies

### Internal Dependencies

- **Dataset.csv**: Training data file must be available with standardized column names (aX, aY, aZ, gX, gY, gZ)
- **Existing ML/DL Training Infrastructure**: Training scripts and model architectures must be modifiable without breaking downstream systems
- **MQTT Message Schema**: Must be documented and consistent to reliably extract 6 sensor values

### External Dependencies

- **Model Performance Baseline**: Need existing model validation metrics to compare against after refactoring (to verify SC-002)
- **Hardware Constraints**: IoT device sensor sampling rates and data transmission format must support 6-axis data streaming

## Out of Scope

- Changing the types of models used (Random Forest, SVM, LSTM, CNN remain the same architectures)
- Adding new calculated features or feature engineering logic (explicitly removing this, not adding)
- Modifying MQTT broker infrastructure or protocol
- Changing database technology or schema beyond BiometricReading model fields
- Updating frontend UI to reflect simplified data model (frontend changes are separate)
- Historical data migration (converting old 15-field records to 6-field format)
- Real-time model retraining or online learning
- Adding model explainability or interpretability features
- Changing inference API endpoints or response formats (only internal processing changes)

## Constraints

- **Performance**: Inference latency must remain under 70ms (hard requirement for real-time tremor suppression)
- **Accuracy**: Model prediction performance must not degrade by more than 5% (F1 score tolerance)
- **Data**: Only 6 raw sensor axes available (aX, aY, aZ, gX, gY, gZ) - no additional data sources
- **Compatibility**: Changes must not break existing MQTT client integration with IoT devices
- **Storage**: Database schema changes must be backward-compatible or include migration plan
- **Deployment**: Model retraining and deployment must be completed without service downtime
- **Validation**: All changes must be verified against test dataset before production deployment
