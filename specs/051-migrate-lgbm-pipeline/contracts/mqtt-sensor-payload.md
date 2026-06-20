# Contract: Inbound ESP32 MQTT Sensor Payload

**Feature**: 051-migrate-lgbm-pipeline
**Source of truth**: `firmware/src/mqtt_publisher.cpp`, `firmware/include/config.h`,
`firmware/src/task_scheduler.cpp` (read during Phase 0).

## Topic

```
tremo/sensors/{DEVICE_SERIAL}      e.g. tremo/sensors/GLOVE001A
```

`test_AI_live.py` subscribes with wildcard `tremo/sensors/+`.

## Transport

- Broker: Mosquitto (host/port/credentials via `.env` / CLI args — NEVER hardcoded).
- QoS 1 (at-least-once).
- **Transmitted rate ≈ 30 Hz** (`MQTT_PUBLISH_RATE_HZ = 33`, MqttTask period 33 ms ≈ 30.3 Hz).
  The IMU samples at 100 Hz internally but only ~30 Hz is published. **This ~30 Hz is the
  rate `test_AI_live.py` must treat as ground truth.**

## Payload (JSON)

```json
{
  "device_id": "GLOVE001A",
  "timestamp": "2026-02-18T10:30:00.123Z",
  "aX": 0.42, "aY": -0.15, "aZ": 9.75,
  "gX": 12.3, "gY": -5.6,  "gZ": 0.8,
  "battery_level": 87.5
}
```

| Field | Type | Unit | Used by live test? |
|-------|------|------|--------------------|
| `device_id` | string | — | optional (label/source) |
| `timestamp` | string (ISO 8601) | — | optional |
| `aX, aY, aZ` | number | m/s² | YES (accel axes) |
| `gX, gY, gZ` | number | °/s | YES (gyro axes) |
| `battery_level` | number | % | ignored by classifier |

## Consumption rules

- Parse the six axes in order `[aX, aY, aZ, gX, gY, gZ]` → append to the rolling buffer.
- Skip (warn + continue) on JSON decode error or missing axis key (spec US3.3).
- Values are already in physical units; no ADC conversion needed.
