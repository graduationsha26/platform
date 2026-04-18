"""
Live Glove Inference Pipeline — v3 Sliding Window

Subscribes to ESP32 MQTT sensor stream, maintains a 100-sample rolling window,
extracts 42 features per window using the shared extract_window_features() pipeline
(identical to training), scales with the saved StandardScaler, and classifies each
window as TREMOR (1) or NORMAL (0) using rf_model_v3.pkl with confidence scoring.

After the initial ~6.7-second warm-up (200 samples @ 30Hz), a new prediction is
produced with every incoming MQTT message — 30 predictions per second.

Feature set (v2): 7 features × 6 axes = 42
  mean, std, max, min, RMS, median, dominant_freq (via FFT in 3-12 Hz band)

Usage:
    py backend/live_glove_test.py
    py backend/live_glove_test.py --broker 192.168.137.1 --port 1883

Prerequisites:
    - backend/ml_models/models/rf_model_v3.pkl    (run train_random_forest.py first)
    - backend/ml_models/models/rf_model_v3_scaler.pkl
    - MQTT broker running at specified address
    - ESP32 publishing JSON to tremo/sensors/+ at 30Hz
      Expected JSON: {"aX": ..., "aY": ..., "aZ": ..., "gX": ..., "gY": ..., "gZ": ...}
      Values must be in physical units: m/s² (accel), °/s (gyro)
"""

import os
import sys
import json
import logging
import argparse
from collections import deque
from datetime import datetime

import numpy as np
import joblib
import paho.mqtt.client as mqtt

# ---------------------------------------------------------------------------
# Path setup — add backend/ to sys.path so ml_data imports resolve correctly
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ml_data.utils.feature_extractors import extract_window_features

# ---------------------------------------------------------------------------
# Constants — must match the v2 training pipeline (5_aggregate_and_extract.py)
# ---------------------------------------------------------------------------
AXIS_NAMES    = ['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']  # order must match training
WINDOW_SIZE   = 100                                       # 100 samples per window (v3)
TREMOR_LOW_HZ = 3.0                                       # Parkinson's tremor band lower bound
TREMOR_HIGH_HZ = 12.0                                     # Parkinson's tremor band upper bound

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CLI Arguments
# ---------------------------------------------------------------------------

def parse_args():
    """Parse command-line arguments."""
    _script_dir = os.path.dirname(os.path.abspath(__file__))
    _models_dir = os.path.join(_script_dir, 'ml_models', 'models')

    parser = argparse.ArgumentParser(
        description='Live tremor inference using v2 sliding window MQTT stream'
    )
    parser.add_argument(
        '--broker',
        default='192.168.137.1',
        help='MQTT broker host (default: 192.168.137.1)'
    )
    parser.add_argument(
        '--port',
        default=1883,
        type=int,
        help='MQTT broker port (default: 1883)'
    )
    parser.add_argument(
        '--topic',
        default='tremo/sensors/+',
        help='MQTT topic to subscribe to (default: tremo/sensors/+)'
    )
    parser.add_argument(
        '--model',
        default=os.path.join(_models_dir, 'rf_model_v3.pkl'),
        help='Path to RF model .pkl file (default: rf_model_v3.pkl)'
    )
    parser.add_argument(
        '--scaler',
        default=os.path.join(_models_dir, 'rf_model_v3_scaler.pkl'),
        help='Path to StandardScaler .pkl file (default: rf_model_v3_scaler.pkl)'
    )
    parser.add_argument(
        '--sampling-rate',
        default=30.0,
        type=float,
        help='Sensor sampling rate in Hz (default: 30.0 for ESP32)'
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# MQTT Callbacks
# ---------------------------------------------------------------------------

def on_connect(client, userdata, connect_flags, reason_code, properties):
    """
    Called by paho-mqtt when the client connects to the broker.
    Compatible with paho-mqtt >= 2.0 CallbackAPIVersion.VERSION2.
    """
    if not reason_code.is_failure:
        logger.info(f'[OK] Connected to MQTT broker {userdata["broker"]}:{userdata["port"]}')
        client.subscribe(userdata['topic'])
        logger.info(f'[OK] Subscribed to {userdata["topic"]}')
        logger.info(
            f'[INFO] Waiting for {WINDOW_SIZE} samples to fill window '
            f'(~{WINDOW_SIZE / userdata["sampling_rate"]:.1f}s warm-up at {userdata["sampling_rate"]}Hz)...'
        )
        logger.info('[INFO] Press Ctrl+C to stop')
    else:
        logger.error(f'[ERROR] MQTT connection failed: {reason_code}')
        sys.exit(1)


def on_message(client, userdata, msg):
    """
    Called by paho-mqtt for every incoming sensor message.

    Parses JSON payload, appends the 6-axis row to the sliding window
    (deque auto-evicts oldest sample), then runs v3 inference once the
    window is full (100 samples):
      1. Convert deque → numpy array (100, 6)
      2. Call extract_window_features() → 42-feature vector
      3. Apply StandardScaler.transform()
      4. model.predict_proba() → confidence-scored class
    """
    window  = userdata['window']
    model   = userdata['model']
    scaler  = userdata['scaler']
    sampling_rate = userdata['sampling_rate']

    # --- Step 1: Parse JSON payload ---
    try:
        data = json.loads(msg.payload.decode('utf-8'))
        row = [
            float(data['aX']),
            float(data['aY']),
            float(data['aZ']),
            float(data['gX']),
            float(data['gY']),
            float(data['gZ']),
        ]
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.warning(f'Skipping malformed message: {e}')
        return

    # --- Step 2: Append to sliding window ---
    window.append(row)

    # --- Step 3: Wait until window is full (warm-up period) ---
    if len(window) < WINDOW_SIZE:
        return

    # --- Step 4: Convert deque to numpy array: shape (200, 6) ---
    win_array = np.array(window, dtype=np.float64)  # (WINDOW_SIZE, 6)

    # --- Step 5: Extract 42 features — same function as v2 training ---
    feature_vector = extract_window_features(
        win_array,
        AXIS_NAMES,
        sampling_rate_hz=sampling_rate,
        low_hz=TREMOR_LOW_HZ,
        high_hz=TREMOR_HIGH_HZ,
    )  # shape: (42,)

    # Sanity check
    assert feature_vector.shape == (42,), (
        f'Feature vector has shape {feature_vector.shape}, expected (42,). '
        'Check AXIS_NAMES and feature_extractors import.'
    )

    # --- Step 6: Scale features using saved StandardScaler ---
    feature_scaled = scaler.transform(feature_vector.reshape(1, -1))  # (1, 42)

    # --- Step 7: Classify with Random Forest model (probability-based) ---
    probs = model.predict_proba(feature_scaled)[0]  # shape (2,): [P(NORMAL), P(TREMOR)]
    pred = int(probs.argmax())
    confidence = probs[pred] * 100

    # --- Step 8: Print result with timestamp and confidence score ---
    ts = datetime.now().strftime('%H:%M:%S.%f')[:12]
    if pred == 0:
        print(f'[{ts}] ✅ NORMAL (0) | Confidence: {confidence:.1f}%')
    else:
        print(f'[{ts}] ⚠️ TREMOR (1) | Confidence: {confidence:.1f}%')


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(args):
    """Main entry point: load model + scaler, create MQTT client, start loop."""

    logger.info('=' * 65)
    logger.info('Live Glove Inference Pipeline — v2 Sliding Window')
    logger.info('=' * 65)
    logger.info(f'Window size  : {WINDOW_SIZE} samples')
    logger.info(f'Warm-up time : ~{WINDOW_SIZE / args.sampling_rate:.1f}s at {args.sampling_rate}Hz')
    logger.info(f'Features     : 42 (7 per axis × 6 axes)')

    # --- Load model ---
    try:
        model = joblib.load(args.model)
        logger.info(f'[OK] Model loaded  : {args.model}')
        logger.info(f'[OK] Model expects : {model.n_features_in_} input features')
    except FileNotFoundError:
        logger.error(f'[ERROR] Model file not found: {args.model}')
        logger.error("[ERROR] Run 'py backend/ml_models/scripts/train_random_forest.py' first")
        sys.exit(1)

    # --- Load scaler ---
    try:
        scaler = joblib.load(args.scaler)
        logger.info(f'[OK] Scaler loaded : {args.scaler}')
    except FileNotFoundError:
        logger.error(f'[ERROR] Scaler file not found: {args.scaler}')
        logger.error("[ERROR] Run 'py backend/ml_models/scripts/train_random_forest.py' first")
        sys.exit(1)

    # --- Create sliding window buffer ---
    window = deque(maxlen=WINDOW_SIZE)

    # --- Create MQTT client ---
    userdata = {
        'broker': args.broker,
        'port': args.port,
        'topic': args.topic,
        'sampling_rate': args.sampling_rate,
        'model': model,
        'scaler': scaler,
        'window': window,
    }
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        userdata=userdata
    )
    client.on_connect = on_connect
    client.on_message = on_message

    # --- Connect to broker ---
    try:
        client.username_pw_set('ZIYAD_ASHRAF', 'ZIYAD_ASHRAF')
        client.connect(args.broker, args.port, keepalive=60)
    except (ConnectionRefusedError, OSError) as e:
        logger.error(f'[ERROR] Cannot connect to {args.broker}:{args.port} — is the broker running?')
        logger.error(f'[ERROR] Details: {e}')
        sys.exit(1)

    # --- Start blocking network loop ---
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        logger.info('[INFO] Stopping live inference. Goodbye.')


if __name__ == '__main__':
    args = parse_args()
    main(args)
