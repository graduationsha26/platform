# Implementation Plan: Live Inference Pipeline (Sliding Window)

**Branch**: `038-live-inference-pipeline` | **Date**: 2026-04-07 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/038-live-inference-pipeline/spec.md`

## Summary

Create `backend/live_glove_test.py` — a standalone Python script that subscribes to the ESP32's MQTT sensor stream, maintains a 100-sample sliding window deque, extracts 42 features per window using `feature_extractors.py`, classifies each window with `rf_model_v1.pkl`, and prints TREMOR/NORMAL to the console at ~30Hz after the initial 3.3s warm-up period.

## Technical Context

**Stack**: Python (standalone script) — no Django, no frontend involved  
**Libraries**: `paho-mqtt` (MQTT client), `collections.deque` (sliding buffer), `numpy` (array operations), `joblib` (model loading), `scipy` (FFT features via feature_extractors.py)  
**Execution**: `py backend/live_glove_test.py` (from repo root)  
**Input data**: Live MQTT stream from ESP32 at `tremo/sensors/+`, 30Hz, JSON `{"aX","aY","aZ","gX","gY","gZ"}`  
**Model**: `backend/ml_models/models/rf_model_v1.pkl` (42-feature RF trained in Feature 037)  
**Feature extractor**: `backend/ml_data/utils/feature_extractors.py` (same functions used in PSMAD pipeline)  
**Constraints**: Local development only; no Docker/CI/CD  
**Scale**: 30 messages/sec continuous stream; inference must complete in < 33ms per window

## Constitution Check

*GATE: Must pass before Phase 0 research.*

- [x] **Monorepo Architecture**: Script lives at `backend/live_glove_test.py` — inside monorepo `backend/` ✅
- [x] **Tech Stack Immutability**: paho-mqtt (constitutional MQTT stack), scikit-learn/joblib (constitutional AI/ML stack), numpy/scipy — all already in constitutional stack ✅
- [x] **Database Strategy**: N/A — no database involved ✅
- [x] **Authentication**: N/A — standalone local script, no user-facing endpoints ✅
- [x] **Security-First**: No secrets involved; MQTT broker is local (192.168.137.1) with no auth. Broker address is a CLI argument, not hardcoded. ✅
- [x] **Real-time Requirements**: This script does NOT use Django Channels — it is a standalone test tool, not the production WebSocket pipeline. The constitution's WebSocket rule applies to the Django backend serving the frontend, not standalone test scripts. ✅
- [x] **MQTT Integration**: Uses paho-mqtt per constitutional MQTT integration requirements ✅
- [x] **AI Model Serving**: Inference performed locally (server-side). Model loaded from `backend/ml_models/models/` per constitution. ✅
- [x] **API Standards**: N/A — no API endpoints created or modified ✅
- [x] **Development Scope**: Local standalone script only — no Docker/CI/CD/production configs ✅

**Result**: ✅ PASS — No constitutional violations.

## Project Structure

### Documentation (this feature)

```text
specs/038-live-inference-pipeline/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code Changes

```text
backend/
└── live_glove_test.py           [CREATE] — sliding window live inference script
```

**Files NOT modified**:
- `backend/ml_data/utils/feature_extractors.py` — imported, not changed
- `backend/ml_models/models/rf_model_v1.pkl` — loaded, not changed
- All Django files, all frontend files

## Implementation Design

### 1. Script Structure

```python
# backend/live_glove_test.py
"""
Live Glove Inference Pipeline — Sliding Window

Subscribes to ESP32 MQTT stream, maintains a 100-sample rolling window,
extracts 42 features, and classifies each window as TREMOR or NORMAL.

Usage:
    py backend/live_glove_test.py
    py backend/live_glove_test.py --broker 192.168.137.1 --port 1883

Prerequisites:
    - rf_model_v1.pkl in backend/ml_models/models/
    - MQTT broker running at specified address
    - ESP32 publishing to tremo/sensors/+
"""
```

### 2. MQTT + Sliding Window Core Logic

```python
from collections import deque
import numpy as np
import json
import joblib
import paho.mqtt.client as mqtt
import sys
import os

# Sliding window buffer — maxlen=100 ensures auto-eviction of oldest sample
window = deque(maxlen=100)

# Sensor axes (must match training order)
AXIS_NAMES = ['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']
WINDOW_SIZE = 100
SAMPLING_RATE_HZ = 30.0   # ESP32 publishes at 30Hz

def on_message(client, userdata, msg):
    """Called by paho-mqtt for every incoming message (runs in MQTT thread)."""
    try:
        data = json.loads(msg.payload.decode('utf-8'))
        row = [data['aX'], data['aY'], data['aZ'],
               data['gX'], data['gY'], data['gZ']]
        window.append(row)
    except (json.JSONDecodeError, KeyError) as e:
        print(f"[WARN] Skipping malformed message: {e}")
        return

    if len(window) == WINDOW_SIZE:
        # Convert deque to (100, 6) numpy array
        win_array = np.array(window)  # shape: (100, 6)

        # Extract 42 features — same pipeline as PSMAD training
        time_feats = extract_features_all_axes(win_array, AXIS_NAMES)
        fft_feats  = extract_fft_features_all_axes(
            win_array, AXIS_NAMES,
            sampling_rate_hz=SAMPLING_RATE_HZ,
            low_hz=3.0, high_hz=12.0
        )
        feature_vector = np.array(
            list(time_feats.values()) + list(fft_feats.values())
        ).reshape(1, -1)  # shape: (1, 42)

        # Predict
        pred = model.predict(feature_vector)[0]
        if pred == 1:
            print("⚠️  TREMOR DETECTED (1)")
        else:
            print("✅  NORMAL (0)")
```

### 3. Model Loading

```python
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'ml_models', 'models', 'rf_model_v1.pkl')

try:
    model = joblib.load(MODEL_PATH)
    print(f"[OK] Model loaded: {MODEL_PATH}")
except FileNotFoundError:
    print(f"[ERROR] Model file not found: {MODEL_PATH}")
    print("[ERROR] Run 'py backend/ml_models/scripts/train_random_forest.py' first")
    sys.exit(1)
```

### 4. MQTT Client Setup

```python
BROKER_HOST = args.broker   # default: '192.168.137.1'
BROKER_PORT = args.port     # default: 1883
TOPIC = 'tremo/sensors/+'

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)

print(f"[OK] Connected to MQTT broker {BROKER_HOST}:{BROKER_PORT}")
print(f"[OK] Subscribed to {TOPIC}")
print(f"[INFO] Waiting for {WINDOW_SIZE} samples to fill window (~{WINDOW_SIZE/SAMPLING_RATE_HZ:.1f}s)...")
print("[INFO] Press Ctrl+C to stop")

client.loop_forever()   # Blocking loop; on_message runs in this thread
```

### 5. Feature Import (sys.path setup)

```python
import sys, os
# Add backend/ to path so we can import ml_data.utils.feature_extractors
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from backend.ml_data.utils.feature_extractors import (
    extract_features_all_axes,
    extract_fft_features_all_axes,
)
```

**Note**: When run from repo root as `py backend/live_glove_test.py`, `__file__` = `backend/live_glove_test.py`, so `os.path.dirname(__file__)` = `backend/`. The `sys.path.insert` adds the repo root, making `backend.ml_data.utils.feature_extractors` importable.

Alternatively (simpler), insert `backend/` into sys.path and import as:
```python
sys.path.insert(0, os.path.dirname(__file__))  # adds backend/ to path
from ml_data.utils.feature_extractors import extract_features_all_axes, extract_fft_features_all_axes
```

Use the second form (matches how training scripts resolve imports from `backend/`).

### 6. CLI Arguments

```python
import argparse

def parse_args():
    parser = argparse.ArgumentParser(description='Live tremor inference using sliding window')
    parser.add_argument('--broker', default='192.168.137.1', help='MQTT broker host')
    parser.add_argument('--port',   default=1883, type=int,   help='MQTT broker port')
    parser.add_argument('--topic',  default='tremo/sensors/+', help='MQTT topic to subscribe to')
    parser.add_argument('--model',  default=None, help='Path to RF model .pkl (optional override)')
    return parser.parse_args()
```

### 7. Error Handling

| Condition | Behavior |
|---|---|
| Malformed JSON | Log `[WARN] Skipping malformed message`, continue |
| Missing field in JSON | `KeyError` caught, log warning, continue |
| Model file not found | Log `[ERROR]`, `sys.exit(1)` |
| MQTT connection failed | `ConnectionRefusedError` raised, log `[ERROR]`, `sys.exit(1)` |
| Ctrl+C | `KeyboardInterrupt`, log `[INFO] Stopping...`, clean exit |

## Complexity Tracking

No constitutional violations — no complexity justification needed.

## Key Technical Decision: Sampling Rate for FFT

The PSMAD dataset used `sampling_rate_hz=37.0` (derived from PSMAD Timestamp column intervals).  
The ESP32 publishes at `30Hz`.

**Decision**: Use `sampling_rate_hz=30.0` for live inference.

**Rationale**: The FFT bin calculation (`np.fft.rfftfreq(N, d=1/sampling_rate_hz)`) must use the **actual** rate of the data being analyzed. Using 37Hz for 30Hz data would shift all frequency bins upward by ~23%, potentially misidentifying the tremor band.

**Impact on model accuracy**: The model was trained on PSMAD features computed at 37Hz. The live features at 30Hz will have slightly different absolute frequency bin positions. However, Parkinson's tremor (3–12Hz) is well within Nyquist for both rates (15Hz at 30Hz, 18.5Hz at 37Hz), so the dominant_freq and tremor_energy features will still capture the relevant frequency content. Accuracy impact is expected to be minor but should be validated empirically.
