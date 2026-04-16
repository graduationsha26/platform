# Data Model: Backend Architecture Alignment

**Branch**: `039-backend-arch-align` | **Date**: 2026-04-12

## Overview

This feature makes no changes to the database schema or Django models. All changes are confined to:
- Permission layer (`InferenceAPIView.permission_classes`)
- Settings configuration (`settings.py` — MQTT entries + LOGGING loggers)
- MQTT client initialization (`MQTTClient.__init__` — reads from settings)

## Entities Affected (Configuration, not Data)

### Permission: IsDoctorOrAdmin

**Location**: `backend/authentication/permissions.py` (existing, unmodified)

| Attribute     | Value                        |
|---------------|------------------------------|
| Type          | DRF `BasePermission` subclass |
| Allowed roles | `doctor`, `admin`             |
| Rejection     | 403 Forbidden                 |
| Auth check    | Implicit (`is_authenticated`) |

**Applied to**: `backend/inference/views.py → InferenceAPIView.permission_classes`

---

### Settings: MQTT Configuration Entries

**Location**: `backend/tremoai_backend/settings.py` (new entries)

| Setting Name      | Source Env Var     | Default                  | Type   |
|-------------------|--------------------|--------------------------|--------|
| `MQTT_BROKER_URL` | `MQTT_BROKER_URL`  | `mqtt://localhost:1883`  | string |
| `MQTT_USERNAME`   | `MQTT_USERNAME`    | `''` (empty)             | string |
| `MQTT_PASSWORD`   | `MQTT_PASSWORD`    | `''` (empty)             | string |

**Consumed by**: `backend/realtime/mqtt_client.py → MQTTClient.__init__`

---

### Settings: LOGGING Named Loggers

**Location**: `backend/tremoai_backend/settings.py → LOGGING['loggers']` (new entries)

| Logger Name | Level | Handlers          | Propagate |
|-------------|-------|-------------------|-----------|
| `inference` | DEBUG | console, file     | False     |
| `cmg`       | DEBUG | console, file     | False     |
| `realtime`  | DEBUG | console, file     | False     |

**Used by**:
- `backend/inference/views.py` → `logging.getLogger(__name__)` resolves to `inference.views` (child of `inference`)
- `backend/realtime/mqtt_client.py` → `logging.getLogger(__name__)` resolves to `realtime.mqtt_client` (child of `realtime`)
- `backend/cmg/` modules → any `logging.getLogger(__name__)` call resolves under `cmg`

## Existing Models (Unchanged)

No `InferenceLog`, `BiometricReading`, `MotorTelemetry`, or other model schemas change as part of this feature.
