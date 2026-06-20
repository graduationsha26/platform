"""
monitor_edge_live.py — Live monitor for the ESP32's ON-DEVICE tremor predictions (Feature 052).

Unlike backend/test_AI_live.py (which classifies in Python from raw telemetry), this script does
NO inference: it simply subscribes to the glove's MQTT telemetry and prints the prediction the
**ESP32 computed locally**, in the exact same 7-field format used before:

  Sample, Prediction, Confidence, Precision, Non-Tremor %, Tremor %

The firmware appends these fields to its telemetry payload (see firmware/src/mqtt_publisher.cpp):
  prediction (0/1/2 or -1 warming up), predicted_class, confidence, probabilities{...}.
'Precision' is the model's validated window-level macro precision, read from the model metadata
(constant per run) — identical meaning to test_AI_live.py.

Usage:
  python backend/monitor_edge_live.py --broker 192.168.137.1 --port 1883 --topic "tremo/sensors/+"
  (broker credentials via --username/--password or MQTT_USERNAME/MQTT_PASSWORD env vars)
"""

import os
import sys
import json
import argparse
import logging

import paho.mqtt.client as mqtt

CLASS_NAMES = {0: "Non-Tremor", 1: "Tremor"}   # Feature 053: binary

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_META = os.path.join(SCRIPT_DIR, "ml_models", "lgbm_tremor_model.json")

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def parse_args():
    p = argparse.ArgumentParser(description="Monitor ESP32 on-device tremor predictions over MQTT")
    p.add_argument("--broker", default="192.168.137.1", help="MQTT broker host")
    p.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    p.add_argument("--topic", default="tremo/sensors/+", help="MQTT topic to subscribe to")
    p.add_argument("--username", default=os.environ.get("MQTT_USERNAME", ""),
                   help="MQTT username (or MQTT_USERNAME env var)")
    p.add_argument("--password", default=os.environ.get("MQTT_PASSWORD", ""),
                   help="MQTT password (or MQTT_PASSWORD env var)")
    p.add_argument("--meta", default=DEFAULT_META, help="Path to lgbm_tremor_model.json")
    return p.parse_args()


class Monitor:
    def __init__(self, precision_pct):
        self.precision_pct = precision_pct
        self.sample_idx = 0
        self.header_printed = False
        self.warned_warmup = False

    def _print_header(self):
        if not self.header_printed:
            print("Sample, Prediction, Confidence, Precision, Non-Tremor %, Tremor %")
            self.header_printed = True

    def handle(self, data):
        pred = data.get("prediction", -1)
        # Warm-up / not-ready: firmware sends prediction == -1 until its first valid window.
        if pred is None or pred == -1:
            if not self.warned_warmup:
                logger.info("Device warming up (no valid prediction yet)...")
                self.warned_warmup = True
            return

        probs = data.get("probabilities", {}) or {}
        p_non = float(probs.get("non_tremor", 0.0))
        p_tre = float(probs.get("tremor", 0.0))
        conf = data.get("confidence")
        if conf is None:
            conf = max(p_non, p_tre)
        name = data.get("predicted_class") or CLASS_NAMES.get(int(pred), str(pred))

        self._print_header()
        self.sample_idx += 1
        print(
            f"{self.sample_idx}, "
            f"{name}, "
            f"{float(conf) * 100:.1f}, "
            f"{self.precision_pct:.1f}, "
            f"{p_non * 100:.1f}, "
            f"{p_tre * 100:.1f}"
        )


def on_connect(client, userdata, flags, reason_code, properties):
    if not reason_code.is_failure:
        logger.info(f"[OK] Connected to {userdata['broker']}:{userdata['port']}")
        client.subscribe(userdata["topic"])
        logger.info(f"[OK] Subscribed to {userdata['topic']} — showing ESP32 on-device decisions.")
        logger.info("Press Ctrl+C to stop.")
    else:
        logger.error(f"[ERROR] MQTT connection failed: {reason_code}")
        sys.exit(1)


def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.warning(f"Skipping malformed message: {e}")
        return
    userdata["monitor"].handle(data)


def main():
    args = parse_args()

    precision_pct = 0.0
    try:
        with open(args.meta, "r", encoding="utf-8") as f:
            meta = json.load(f)
        precision_pct = float(meta.get("metrics", {}).get("window_macro_precision", 0.0)) * 100.0
        logger.info(f"[OK] Metadata loaded: precision={precision_pct:.1f}%")
    except FileNotFoundError:
        logger.warning(f"Metadata not found ({args.meta}); Precision column will show 0.0")

    monitor = Monitor(precision_pct)
    userdata = {"broker": args.broker, "port": args.port, "topic": args.topic, "monitor": monitor}

    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, userdata=userdata)
    client.on_connect = on_connect
    client.on_message = on_message
    if args.username:
        client.username_pw_set(args.username, args.password)

    try:
        client.connect(args.broker, args.port, keepalive=60)
    except (ConnectionRefusedError, OSError) as e:
        logger.error(f"[ERROR] Cannot connect to {args.broker}:{args.port} — is the broker running?")
        logger.error(f"Details: {e}")
        sys.exit(1)

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        logger.info("Stopping monitor. Goodbye.")


if __name__ == "__main__":
    main()
