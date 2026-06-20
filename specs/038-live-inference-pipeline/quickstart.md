# Quickstart: Live Inference Pipeline (Sliding Window)

**Branch**: `038-live-inference-pipeline` | **Date**: 2026-04-07

## Prerequisites

1. `backend/ml_models/models/rf_model_v1.pkl` must exist (Feature 037 complete)
2. ESP32 running firmware and publishing to `tremo/sensors/+` at 30Hz
3. MQTT broker running at `192.168.137.1:1883`
4. Python dependencies: `paho-mqtt`, `numpy`, `scipy`, `joblib` (all in `backend/requirements.txt`)

## Running the Script

From the **repository root**:

```bash
# Default (broker: 192.168.137.1:1883)
py backend/live_glove_test.py

# Custom broker
py backend/live_glove_test.py --broker 192.168.137.1 --port 1883

# Custom model path
py backend/live_glove_test.py --model backend/ml_models/models/rf_model_v1.pkl
```

## Expected Console Output

### Startup
```
[OK] Model loaded: backend/ml_models/models/rf_model_v1.pkl
[OK] Connected to MQTT broker 192.168.137.1:1883
[OK] Subscribed to tremo/sensors/+
[INFO] Waiting for 100 samples to fill window (~3.3s)...
[INFO] Press Ctrl+C to stop
```

### After warm-up (30 lines/second)
```
[14:32:01.033] ✅  NORMAL (0)
[14:32:01.067] ✅  NORMAL (0)
[14:32:01.100] ✅  NORMAL (0)
[14:32:01.133] ⚠️  TREMOR DETECTED (1)
[14:32:01.167] ⚠️  TREMOR DETECTED (1)
[14:32:01.200] ✅  NORMAL (0)
```

### Error cases
```
# Missing model file
[ERROR] Model file not found: backend/ml_models/models/rf_model_v1.pkl
[ERROR] Run 'py backend/ml_models/scripts/train_random_forest.py' first

# Broker unreachable
[ERROR] Cannot connect to MQTT broker 192.168.137.1:1883 — is the broker running?

# Malformed message
[WARN] Skipping malformed message: Expecting value: line 1 column 1 (char 0)

# Ctrl+C
[INFO] Stopping live inference. Goodbye.
```

## Expected Output Files

None — this script produces console output only. No files are written.

## Verification Checks

After the warm-up period:

1. **Prediction rate**: You should see approximately 30 lines per second printed to the console
2. **No deque clearing**: The window continues sliding — no pauses between prediction bursts
3. **Binary output**: All predictions are exactly `0` or `1` — no other values
4. **Malformed message recovery**: Send a bad MQTT message (e.g., `mosquitto_pub -t tremo/sensors/test -m "bad"`) — should see `[WARN]` but predictions continue

## MQTT Message Format (Expected from ESP32)

```json
{
  "aX": -1234,
  "aY": 456,
  "aZ": 9800,
  "gX": -123,
  "gY": 45,
  "gZ": 12
}
```

All 6 fields must be present. Values are raw IMU integers (accelerometer in mg units, gyroscope in mdps or raw ADC units depending on firmware scaling).

## Feature Extraction Details

The script extracts 42 features from each 100-sample window, in this exact order:

**Time-domain (30 features):** `RMS_aX, mean_aX, std_aX, skewness_aX, kurtosis_aX, RMS_aY, ...` (5 per axis × 6 axes)

**FFT tremor-band (12 features):** `dominant_freq_aX, tremor_energy_aX, dominant_freq_aY, ...` (2 per axis × 6 axes)

- Tremor band: 3–12 Hz (Parkinson's tremor frequency range)
- Sampling rate: 30.0 Hz (ESP32 actual rate)

This matches the column order of `backend/ml_data/processed/ready_for_training_features.csv`.
