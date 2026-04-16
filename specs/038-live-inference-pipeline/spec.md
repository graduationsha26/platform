# Feature Specification: Live Inference Pipeline (Sliding Window)

**Feature**: 038-live-inference-pipeline  
**Branch**: `038-live-inference-pipeline`  
**Date**: 2026-04-07  
**Priority**: P1  
**Status**: Draft

---

## Problem Statement

Currently, the system only produces a tremor prediction every 3.3 seconds — the time required to collect 100 sensor samples at 30Hz before running inference. This batch-mode delay makes real-time clinical monitoring impractical. After the initial fill period, the system should produce a new prediction with every arriving sensor sample (30 per second), giving clinicians and researchers continuous, near-instantaneous feedback on tremor presence.

---

## User Stories

### US1 (P1): Continuous Real-Time Tremor Detection

**As a** researcher or clinician running a live glove test session,  
**I want** the system to output a new tremor prediction with every incoming sensor reading (after an initial 3.3-second warm-up),  
**So that** I can observe tremor state changes in real time without multi-second lag between outputs.

**Acceptance Criteria:**
- After startup, predictions begin appearing within 3.5 seconds (100 samples × 33ms + overhead)
- Once the window is full, a new prediction is printed for every sensor sample received
- Each prediction clearly indicates either TREMOR DETECTED or NORMAL state
- The system runs continuously until manually stopped (Ctrl+C)
- A missed or malformed sensor message is skipped without crashing

---

## Functional Requirements

### FR1 — Sensor Data Ingestion
The system must subscribe to the wearable glove's MQTT data stream and receive 6-axis IMU samples (accelerometer X/Y/Z and gyroscope X/Y/Z) at approximately 30 samples per second.

### FR2 — Sliding Window Buffer
The system must maintain a rolling buffer of the 100 most recent sensor samples. When a new sample arrives, it is appended to the buffer. The oldest sample is automatically discarded when the buffer is full (no manual clearing required).

### FR3 — Feature Extraction
When the buffer contains exactly 100 samples, the system must extract the same feature set used during model training (42 features: 30 statistical + 12 FFT tremor-band features) from the current window contents.

### FR4 — Tremor Classification
The extracted features must be passed to the trained Random Forest model (`rf_model_v1.pkl`), which outputs a binary prediction: 0 (normal) or 1 (tremor detected).

### FR5 — Prediction Output
The system must print the classification result to the console after each prediction:
- Label 1: "⚠️ TREMOR DETECTED (1)"
- Label 0: "✅ NORMAL (0)"

### FR6 — Graceful Error Handling
The system must handle the following gracefully without crashing:
- Malformed or incomplete JSON in a sensor message (log warning, skip sample)
- Missing expected JSON fields (log warning, skip sample)
- MQTT connection loss (log error, attempt reconnection or exit cleanly)

### FR7 — Startup Indication
The system must log startup status including the MQTT broker address, subscribed topic, and model file loaded, so the operator knows the system is ready before the first prediction appears.

---

## User Scenarios & Testing

### Scenario 1: Normal warm-up and prediction flow
1. Operator starts the script
2. Script logs: connected to broker, subscribed to topic, model loaded
3. Script logs: "Waiting for 100 samples..." (buffer filling)
4. At 100 samples: first prediction prints (NORMAL or TREMOR)
5. Every subsequent sample triggers a new prediction line
6. Operator stops with Ctrl+C

**Expected**: Predictions print at ~30Hz after warm-up. No errors.

### Scenario 2: Malformed MQTT message
1. System is running and receiving predictions normally
2. One message arrives with invalid JSON (e.g., corrupted payload)
3. System logs a warning: "Skipping malformed message"
4. System continues receiving and predicting normally

**Expected**: One skipped sample, no crash, stream continues.

### Scenario 3: Missing field in message
1. A message arrives with `aX`, `aY`, `aZ` but missing `gX`
2. System logs a warning: "Missing field in message"
3. Prediction stream continues with the next valid message

**Expected**: One skipped sample, no crash.

### Scenario 4: Model file not found
1. Operator starts the script but model file path is wrong
2. System logs an error: "Model file not found: <path>"
3. System exits with a non-zero exit code

**Expected**: Clean failure with informative error message.

---

## Success Criteria

1. **Prediction latency**: After the initial 100-sample warm-up (~3.3 seconds at 30Hz), a new prediction is output within 50ms of each incoming sensor sample.
2. **Throughput**: The system sustains 30 predictions per second continuously without dropping samples or accumulating lag.
3. **Accuracy consistency**: Predictions from the live pipeline for the same 100-sample window must match the offline model's prediction for that window 100% of the time (no feature extraction divergence).
4. **Fault tolerance**: A single malformed MQTT message does not interrupt the prediction stream; the system automatically recovers with the next valid message.
5. **Startup reliability**: The system reaches a ready state (model loaded, MQTT connected, awaiting data) within 5 seconds of launch.

---

## Scope

**In scope:**
- Standalone script that subscribes to the glove's MQTT topic and runs inference locally
- Sliding window logic with a 100-sample rolling buffer
- Console output of binary tremor/normal prediction for each sample
- Basic error handling for malformed messages and missing model file

**Out of scope:**
- Saving prediction history to a database or file
- Sending predictions over MQTT or to a web API
- Running as a persistent service or daemon
- Supporting multiple simultaneous glove devices
- Any frontend or dashboard integration

---

## Dependencies

- Feature 037 (`037-train-ml-models`): Provides `rf_model_v1.pkl` — must be complete before this feature can be tested end-to-end
- Feature 036 (`036-psmad-data-prep`): Provides `feature_extractors.py` — the same extraction logic used in training must be reused here to ensure feature consistency

---

## Assumptions

1. The ESP32 publishes at a stable 30Hz; brief rate variations (±5Hz) are acceptable and will not break the sliding window logic.
2. The MQTT broker is running at 192.168.137.1:1883 (local network) with no authentication required.
3. The topic pattern is `tremo/sensors/+` (single-level wildcard to support multiple glove devices or hands).
4. The model was trained on 42 features (30 time-domain statistical + 12 FFT tremor-band); the live script must extract the same 42 features in the same order.
5. The script is run manually by a developer or researcher from the command line; no GUI or background service is required.
6. `feature_extractors.py` is importable from the script's working directory or Python path.
