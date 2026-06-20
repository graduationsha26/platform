# Implementation Plan: Remove Flex Fields from MQTT Parser

**Branch**: `019-remove-flex-mqtt` | **Date**: 2026-02-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/019-remove-flex-mqtt/spec.md`

---

## Summary

The TremoAI glove device no longer transmits flex sensor readings (flex_1-flex_5). This feature ensures the MQTT parsing layer is clean of flex field expectations at every level:

1. **Audit (confirmed)**: The existing session-level MQTT validator (`realtime/validators.py`) and message handler (`realtime/mqtt_client.py`) contain zero references to flex fields. No changes needed there.

2. **New work**: Implement a raw sensor reading MQTT handler (`devices/+/reading` topic) that creates `BiometricReading` records using only the six accelerometer/gyroscope fields. This handler is built flex-free from the ground up, and silently discards any flex fields found in legacy payloads.

**Scope**: Backend only. No database migrations. No frontend changes.

---

## Technical Context

**Backend Stack**: Django 5.x + Django REST Framework + Django Channels
**Frontend Stack**: React 18+ + Vite + Tailwind CSS + Recharts *(unaffected)*
**Database**: Supabase PostgreSQL (remote) — `biometric_readings` table already has flex columns removed (Feature E-2.1)
**Authentication**: JWT (SimpleJWT) — not involved in MQTT handling
**Testing**: pytest (backend)
**Project Type**: web (monorepo: `backend/` and `frontend/`)
**Real-time**: Django Channels WebSocket — not affected by this feature
**Integration**: MQTT subscription (`paho-mqtt`). Existing topic `devices/+/data` unchanged. New topic `devices/+/reading` added.
**Performance Goals**: MQTT message handling under 50ms per reading (same latency budget as session messages)
**Constraints**: Local development only; no Docker/CI/CD
**Scale/Scope**: 10 concurrent doctors, up to 100 patients, sensor readings at ~10–50 Hz per device

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Monorepo Architecture**: All changes in `backend/realtime/`. No new apps, no new directories.
- [x] **Tech Stack Immutability**: Uses existing `paho-mqtt` (already in stack). No new libraries.
- [x] **Database Strategy**: Writes to existing Supabase PostgreSQL `biometric_readings` table. No schema changes.
- [x] **Authentication**: MQTT pipeline has no auth dependency. Device identity validated via serial number + `validate_device_pairing()`.
- [x] **Security-First**: No secrets introduced. MQTT broker credentials already in `.env`.
- [x] **Real-time Requirements**: No WebSocket changes. BiometricReading records are not broadcast over WebSocket in this feature.
- [x] **MQTT Integration**: This feature extends the existing MQTT subscriber. Uses `paho-mqtt` (constitutional).
- [x] **AI Model Serving**: No ML inference on raw readings in this feature. `feature_utils.py` is not called here.
- [x] **API Standards**: No new REST endpoints. `BiometricReadingViewSet` (read-only) surfaces the stored records via existing `/api/biometric-readings/` endpoint.
- [x] **Development Scope**: Local development only. No deployment config.

**Result**: ✅ PASS — No violations.

---

## Project Structure

### Documentation (this feature)

```text
specs/019-remove-flex-mqtt/
├── plan.md                          # This file
├── research.md                      # Phase 0: audit findings + decisions
├── data-model.md                    # Phase 1: MQTT message schemas
├── quickstart.md                    # Phase 1: integration scenarios
├── contracts/
│   └── mqtt-reading-message.yaml   # Phase 1: raw reading message schema
└── checklists/
    └── requirements.md             # Spec quality checklist (already passing)
```

### Source Code (repository root)

```text
backend/
└── realtime/
    ├── validators.py          # MODIFY: add validate_biometric_reading_message()
    ├── mqtt_client.py         # MODIFY: subscribe to devices/+/reading, add handler
    └── tests/
        └── test_mqtt_client.py  # MODIFY: add raw reading tests
```

No other files need modification. Specifically:
- `biometrics/models.py` — no change (model already clean)
- `biometrics/serializers.py` — no change (serializer already clean)
- `biometrics/views.py` — no change (ViewSet already clean)
- `biometrics/reading_urls.py` — no change (routing already in place)
- `tremoai_backend/urls.py` — no change

---

## Implementation Details

### Change 1: `backend/realtime/validators.py`

Add a new function `validate_biometric_reading_message(payload: dict) -> None` after the existing `validate_mqtt_message()`.

**Validation logic**:
1. Check required fields present: `serial_number`, `timestamp`, `aX`, `aY`, `aZ`, `gX`, `gY`, `gZ`
2. Validate `serial_number`: string, 8-20 chars, uppercase alphanumeric
3. Validate `timestamp`: string, valid ISO 8601
4. Validate each of `aX`, `aY`, `aZ`, `gX`, `gY`, `gZ`: must be numeric (int or float)
5. Warn (don't reject) if sensor values are outside physical ranges from `feature_utils.SENSOR_RANGES`
6. All other fields (including `flex_1`-`flex_5`) — silently ignored (no validation, no error)
7. Raises `django.core.exceptions.ValidationError` on failure

### Change 2: `backend/realtime/mqtt_client.py`

**Topic subscription** — modify `on_connect()`:
- Subscribe to `devices/+/reading` in addition to the existing `devices/+/data`

**Message dispatch** — modify `on_message()`:
- Detect topic type from the third segment:
  - `data` → existing session handler (unchanged)
  - `reading` → new `_handle_reading_message(payload, serial_number)` method
  - Other → log and discard

**New method** `_handle_reading_message(payload: dict, serial_number: str) -> BiometricReading`:
1. Call `validate_biometric_reading_message(payload)` — raises on invalid
2. Call `validate_device_pairing(serial_number)` — existing function
3. Parse timestamp from `payload['timestamp']`
4. Create and return `BiometricReading` record with the six sensor values

### Change 3: `backend/realtime/tests/test_mqtt_client.py`

Add a new test class `BiometricReadingMQTTValidationTest` with cases:

| Test | Input | Expected |
|------|-------|----------|
| `test_valid_6_field_payload` | 6 standard fields | Validation passes |
| `test_legacy_payload_with_flex_fields` | 6 fields + flex_1-5 | Validation passes (flex ignored) |
| `test_missing_required_sensor_field` | Missing `gZ` | ValidationError raised |
| `test_invalid_sensor_value_type` | `aX: "not_a_number"` | ValidationError raised |
| `test_invalid_timestamp_format` | `timestamp: "not-a-date"` | ValidationError raised |
| `test_out_of_range_sensor_value_warns_not_raises` | `aX: 999.9` | No exception; warning logged |

---

## Complexity Tracking

> No constitution violations. Table left blank.

---

## Artifacts Generated (Phase 1)

| Artifact | Path | Status |
|----------|------|--------|
| Research findings | `specs/019-remove-flex-mqtt/research.md` | ✅ Complete |
| MQTT message schemas | `specs/019-remove-flex-mqtt/data-model.md` | ✅ Complete |
| Raw reading message contract | `specs/019-remove-flex-mqtt/contracts/mqtt-reading-message.yaml` | ✅ Complete |
| Integration quickstart | `specs/019-remove-flex-mqtt/quickstart.md` | ✅ Complete |

**Next step**: Run `/speckit.tasks` to generate the implementation task list.
