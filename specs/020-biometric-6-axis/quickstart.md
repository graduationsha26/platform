# Quickstart: Biometric 6-Axis API (Feature 020)

**Branch**: `020-biometric-6-axis` | **Date**: 2026-02-18

This guide shows how to interact with the `BiometricReading` API after migrations are applied.

---

## Prerequisites

- Backend running: `python manage.py runserver`
- Migrations applied: `python manage.py migrate`
- Valid JWT token for a doctor account
- At least one patient with recorded biometric readings

---

## Scenario 1: List Raw Sensor Readings for a Patient

```http
GET /api/biometric-readings/?patient=7
Authorization: Bearer <doctor_jwt_token>
```

**Response** (200 OK):

```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 42,
      "patient_id": 7,
      "timestamp": "2026-02-18T10:30:05Z",
      "aX": 0.12,
      "aY": -0.05,
      "aZ": 9.81,
      "gX": 1.23,
      "gY": -0.44,
      "gZ": 0.09
    },
    {
      "id": 41,
      "patient_id": 7,
      "timestamp": "2026-02-18T10:30:00Z",
      "aX": 0.10,
      "aY": -0.03,
      "aZ": 9.79,
      "gX": 1.20,
      "gY": -0.41,
      "gZ": 0.07
    }
  ]
}
```

**What to verify**:
- Response contains exactly: `id`, `patient_id`, `timestamp`, `aX`, `aY`, `aZ`, `gX`, `gY`, `gZ`
- No `mX`, `mY`, `mZ`, `flex_1` through `flex_5`, or any other sensor fields appear

---

## Scenario 2: Retrieve a Single Reading

```http
GET /api/biometric-readings/42/
Authorization: Bearer <doctor_jwt_token>
```

**Response** (200 OK):

```json
{
  "id": 42,
  "patient_id": 7,
  "timestamp": "2026-02-18T10:30:05Z",
  "aX": 0.12,
  "aY": -0.05,
  "aZ": 9.81,
  "gX": 1.23,
  "gY": -0.44,
  "gZ": 0.09
}
```

---

## Scenario 3: Access Control — Unauthorized Patient

```http
GET /api/biometric-readings/?patient=99
Authorization: Bearer <doctor_jwt_token>
```

**Response** (200 OK, empty results — doctor has no access to patient 99):

```json
{
  "count": 0,
  "next": null,
  "previous": null,
  "results": []
}
```

---

## Scenario 4: Verify MQTT Creates Readings with 6 Axes Only

When the MQTT client receives a reading message, it creates a `BiometricReading` record.
The validator (`validate_biometric_reading_message`) accepts exactly this payload format:

```json
{
  "serial_number": "DEVICEABC123",
  "timestamp": "2026-02-18T10:30:05Z",
  "aX": 0.12,
  "aY": -0.05,
  "aZ": 9.81,
  "gX": 1.23,
  "gY": -0.44,
  "gZ": 0.09
}
```

Extra fields (e.g., legacy `flex_1` through `flex_5`) are silently ignored.
Magnetometer fields (mX, mY, mZ) are not expected and would also be ignored.

---

## Verify Migration State

```bash
python manage.py showmigrations biometrics
```

Expected output:
```
biometrics
 [X] 0001_initial
 [X] 0002_add_biometricreading
 [X] 0003_remove_flex_fields
```

Verify the table schema:
```bash
python manage.py dbshell
```

```sql
\d biometric_readings
```

Expected columns: `id`, `patient_id`, `timestamp`, `aX`, `aY`, `aZ`, `gX`, `gY`, `gZ`.
No `mX`, `mY`, `mZ`, or `flex_*` columns should appear.
