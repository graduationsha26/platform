"""
test_AI_live.py — Live tremor-classification validator (Feature 051).

Subscribes to the ESP32 MQTT telemetry stream, maintains a 1-second sliding buffer, resamples
each window UP to the model's 66.67 Hz / 67-sample shape, applies the same 0.5-20 Hz band-pass
and 66-feature extraction used in training (shared ml_models.features_lgbm — no scaler), and
emits a 3-class prediction every ~100 ms using the LightGBM model.

Sampling-rate ground truth (confirmed from firmware):
  - firmware/include/config.h: IMU_SAMPLE_RATE_HZ 100 (internal), MQTT_PUBLISH_RATE_HZ 33
  - firmware/src/task_scheduler.cpp: MqttTask period = pdMS_TO_TICKS(33) -> ~30.3 Hz transmitted
  The live stream we receive is the *transmitted* ~30.3 Hz, NOT 100 Hz. We resample up to 66.67 Hz.

Output (exact, one line per prediction):
  Sample, Prediction, Confidence, Precision, Non-Tremor %, Tremor %, Voluntary %

Usage:
  python backend/test_AI_live.py --broker 192.168.137.1 --port 1883 --topic "tremo/sensors/+"
  (broker credentials via --username/--password or MQTT_USERNAME/MQTT_PASSWORD env vars)
"""

import os
import sys
import json
import time
import argparse
import logging
import warnings
from collections import deque

import numpy as np
import joblib
import paho.mqtt.client as mqtt

# LightGBM was fit on a NumPy array (positional names); predicting on NumPy is correct, so
# silence the cosmetic sklearn "X does not have valid feature names" warning.
warnings.filterwarnings(
    "ignore", message="X does not have valid feature names", category=UserWarning
)

# Make ml_models.features_lgbm importable (add backend/ to path).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ml_models.features_lgbm import (  # noqa: E402
    bandpass_2d, resample_window, extract_features_66, WINDOW_SIZE,
)

# ── Ground-truth constants (from firmware) ───────────────────────────────────
LIVE_STREAM_RATE_HZ = 1000.0 / 33.0          # ≈ 30.3 Hz — MqttTask 33 ms publish period
WINDOW_SECONDS = 1.0
BUFFER_LEN = max(1, int(round(LIVE_STREAM_RATE_HZ * WINDOW_SECONDS)))   # ≈ 30 samples
PREDICT_EVERY_S = 0.100                        # emit a prediction every ~100 ms
AXIS_KEYS = ['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']
CLASS_NAMES = {0: 'Non-Tremor', 1: 'Tremor', 2: 'Voluntary'}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MODEL = os.path.join(SCRIPT_DIR, 'ml_models', 'lgbm_tremor_model.pkl')
DEFAULT_META = os.path.join(SCRIPT_DIR, 'ml_models', 'lgbm_tremor_model.json')

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def parse_args():
    p = argparse.ArgumentParser(description='Live LightGBM tremor classification over MQTT')
    p.add_argument('--broker', default='192.168.137.1', help='MQTT broker host')
    p.add_argument('--port', type=int, default=1883, help='MQTT broker port')
    p.add_argument('--topic', default='tremo/sensors/+', help='MQTT topic to subscribe to')
    p.add_argument('--username', default=os.environ.get('MQTT_USERNAME', ''),
                   help='MQTT username (or MQTT_USERNAME env var)')
    p.add_argument('--password', default=os.environ.get('MQTT_PASSWORD', ''),
                   help='MQTT password (or MQTT_PASSWORD env var)')
    p.add_argument('--model', default=DEFAULT_MODEL, help='Path to lgbm_tremor_model.pkl')
    p.add_argument('--meta', default=DEFAULT_META, help='Path to lgbm_tremor_model.json')
    return p.parse_args()


class LivePredictor:
    """Holds model, metadata, rolling buffer and the per-100 ms prediction logic."""

    def __init__(self, model, precision_pct):
        self.model = model
        self.precision_pct = precision_pct
        self.buffer = deque(maxlen=BUFFER_LEN)
        self.sample_idx = 0
        self.last_emit = 0.0
        self.warned_warmup = False
        self.header_printed = False

    def add_sample(self, row):
        self.buffer.append(row)

    def _print_header(self):
        if not self.header_printed:
            print('Sample, Prediction, Confidence, Precision, Non-Tremor %, Tremor %, Voluntary %')
            self.header_printed = True

    def maybe_predict(self):
        # Throttle to ~100 ms cadence (monotonic clock).
        now = time.monotonic()
        if (now - self.last_emit) < PREDICT_EVERY_S:
            return

        # Warm-up: need a full 1-second buffer before the first prediction.
        if len(self.buffer) < BUFFER_LEN:
            if not self.warned_warmup:
                logger.info(
                    f'Warming up — collecting {BUFFER_LEN} samples '
                    f'(~{WINDOW_SECONDS:.0f}s at {LIVE_STREAM_RATE_HZ:.1f} Hz)...'
                )
                self.warned_warmup = True
            return

        self.last_emit = now
        try:
            buf = np.asarray(self.buffer, dtype=np.float64)        # (~30, 6)
            window = resample_window(buf, WINDOW_SIZE)             # (67, 6) @ 66.67 Hz
            window = bandpass_2d(window)                           # band-pass AFTER resample
            feats = extract_features_66(window).reshape(1, -1)     # (1, 66)
            proba = self.model.predict_proba(feats)[0]            # (3,)
        except Exception as e:
            print(f'# could not classify sample: {e}')
            return

        self._print_header()
        self.sample_idx += 1
        cls = int(np.argmax(proba))
        line = (
            f'{self.sample_idx}, '
            f'{CLASS_NAMES.get(cls, cls)}, '
            f'{proba[cls] * 100:.1f}, '
            f'{self.precision_pct:.1f}, '
            f'{proba[0] * 100:.1f}, '
            f'{proba[1] * 100:.1f}, '
            f'{proba[2] * 100:.1f}'
        )
        print(line)


# ── MQTT callbacks ───────────────────────────────────────────────────────────

def on_connect(client, userdata, flags, reason_code, properties):
    if not reason_code.is_failure:
        logger.info(f'[OK] Connected to {userdata["broker"]}:{userdata["port"]}')
        client.subscribe(userdata['topic'])
        logger.info(f'[OK] Subscribed to {userdata["topic"]}')
        logger.info('Press Ctrl+C to stop.')
    else:
        logger.error(f'[ERROR] MQTT connection failed: {reason_code}')
        sys.exit(1)


def on_message(client, userdata, msg):
    predictor = userdata['predictor']
    try:
        data = json.loads(msg.payload.decode('utf-8'))
        row = [float(data[k]) for k in AXIS_KEYS]
    except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
        logger.warning(f'Skipping malformed message: {e}')
        return
    predictor.add_sample(row)
    predictor.maybe_predict()


def main():
    args = parse_args()

    logger.info('=' * 60)
    logger.info('Live LightGBM Tremor Classifier (Feature 051)')
    logger.info('=' * 60)
    logger.info(f'Live stream rate : {LIVE_STREAM_RATE_HZ:.2f} Hz (firmware MQTT transmit)')
    logger.info(f'Buffer length    : {BUFFER_LEN} samples (~{WINDOW_SECONDS:.0f}s)')
    logger.info(f'Model window     : {WINDOW_SIZE} samples @ 66.67 Hz (resampled)')
    logger.info(f'Prediction cadence: every {PREDICT_EVERY_S * 1000:.0f} ms')

    # Load model + metadata (precision for the constant 'Precision' column).
    try:
        model = joblib.load(args.model)
        logger.info(f'[OK] Model loaded: {args.model}')
    except FileNotFoundError:
        logger.error(f'[ERROR] Model not found: {args.model}')
        logger.error("Run 'python backend/ml_models/train.py' first.")
        sys.exit(1)

    precision_pct = 0.0
    try:
        with open(args.meta, 'r', encoding='utf-8') as f:
            meta = json.load(f)
        precision_pct = float(meta.get('metrics', {}).get('window_macro_precision', 0.0)) * 100.0
        logger.info(f'[OK] Metadata loaded: precision={precision_pct:.1f}%')
    except FileNotFoundError:
        logger.warning(f'Metadata not found ({args.meta}); Precision column will show 0.0')

    predictor = LivePredictor(model, precision_pct)

    userdata = {
        'broker': args.broker, 'port': args.port, 'topic': args.topic,
        'predictor': predictor,
    }
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                         userdata=userdata)
    client.on_connect = on_connect
    client.on_message = on_message
    if args.username:
        client.username_pw_set(args.username, args.password)

    try:
        client.connect(args.broker, args.port, keepalive=60)
    except (ConnectionRefusedError, OSError) as e:
        logger.error(f'[ERROR] Cannot connect to {args.broker}:{args.port} — is the broker running?')
        logger.error(f'Details: {e}')
        sys.exit(1)

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        logger.info('Stopping live inference. Goodbye.')


if __name__ == '__main__':
    main()
