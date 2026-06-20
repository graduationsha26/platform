# Data Model: CMG Brushless Motor & ESC Initialization (027)

**Branch**: `027-cmg-esc-init`
**Date**: 2026-02-18

---

## Entities

### 1. MotorTelemetry

**Purpose**: Time-series record of CMG rotor motor state published by the glove at ~1 Hz. Provides the historical and live view of motor speed, current draw, and operational status.

**Django app**: `cmg`
**DB table**: `cmg_motor_telemetry`

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | BigAutoField | PK | Auto-generated primary key |
| `device` | FK → Device | NOT NULL, on_delete=CASCADE | Glove device that produced this reading |
| `patient` | FK → Patient | NOT NULL, on_delete=CASCADE | Denormalized from device.patient for fast patient-scoped queries |
| `timestamp` | DateTimeField | NOT NULL, indexed | UTC timestamp from glove (not server receipt time) |
| `rpm` | IntegerField | NOT NULL | Rotor speed in RPM (0 when idle/stopped) |
| `current_a` | FloatField | NOT NULL | Motor current draw in amperes |
| `status` | CharField(12) | NOT NULL, choices | Operational state: `idle` / `starting` / `running` / `fault` |
| `fault_type` | CharField(16) | NULL, blank | Active fault type if status=`fault`: `overcurrent` / `stall` / null |
| `received_at` | DateTimeField | auto_now_add | Server-side receipt timestamp (for latency monitoring) |

**Indexes**:
```python
indexes = [
    models.Index(fields=['device', '-timestamp']),   # latest-by-device + time-range queries
    models.Index(fields=['patient', '-timestamp']),  # patient-scoped history queries
]
```

**Status choices**:
```python
STATUS_CHOICES = [
    ('idle', 'Idle'),
    ('starting', 'Starting'),
    ('running', 'Running'),
    ('fault', 'Fault'),
]
```

**Validation rules**:
- `rpm` ≥ 0
- `current_a` ≥ 0.0
- If `status == 'fault'` then `fault_type` MUST be non-null
- If `status != 'fault'` then `fault_type` MUST be null

**Retention**: 30 days (older rows may be purged by a management command).

---

### 2. MotorFaultEvent

**Purpose**: Persistent record of each safety fault triggered during CMG operation. Includes acknowledgment state so doctors can explicitly clear faults before restarting the motor.

**Django app**: `cmg`
**DB table**: `cmg_motor_fault_events`

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | BigAutoField | PK | Auto-generated primary key |
| `device` | FK → Device | NOT NULL, on_delete=CASCADE | Glove device that generated the fault |
| `patient` | FK → Patient | NOT NULL, on_delete=CASCADE | Denormalized for patient-scoped queries |
| `occurred_at` | DateTimeField | NOT NULL, indexed | UTC timestamp of fault from glove |
| `fault_type` | CharField(16) | NOT NULL, choices | `overcurrent` or `stall` |
| `rpm_at_fault` | IntegerField | NULL | Rotor speed at time of fault (from payload) |
| `current_at_fault` | FloatField | NULL | Current draw at time of fault (from payload) |
| `acknowledged` | BooleanField | NOT NULL, default=False | Whether a doctor has acknowledged this fault |
| `acknowledged_at` | DateTimeField | NULL | Timestamp of acknowledgment |
| `acknowledged_by` | FK → CustomUser | NULL, on_delete=SET_NULL | Doctor who acknowledged |
| `created_at` | DateTimeField | auto_now_add | Server-side record creation time |

**Indexes**:
```python
indexes = [
    models.Index(fields=['device', '-occurred_at']),
    models.Index(fields=['patient', '-occurred_at']),
    models.Index(fields=['acknowledged', '-occurred_at']),  # unacknowledged fault queries
]
```

**Fault type choices**:
```python
FAULT_TYPE_CHOICES = [
    ('overcurrent', 'Overcurrent'),
    ('stall', 'Stall'),
]
```

**Retention**: Indefinite (fault events are part of device operational history).

---

## Entity Relationships

```
Device (1) ──< MotorTelemetry (*)        [one device → many telemetry rows]
Device (1) ──< MotorFaultEvent (*)       [one device → many fault events]

Patient (1) ──< MotorTelemetry (*)       [denormalized for direct patient-scope query]
Patient (1) ──< MotorFaultEvent (*)      [denormalized for direct patient-scope query]

CustomUser (0..1) ──< MotorFaultEvent (*) [doctor who acknowledged, nullable]

Device (N..1) → Patient                  [existing: device.patient FK]
```

---

## State Transitions

### MotorTelemetry.status

```
       [idle]
         │
         ▼  start command received by glove
      [starting]
         │
         ▼  target RPM reached
      [running]
         │
         ├──── overcurrent detected ──► [fault]  fault_type = 'overcurrent'
         │
         └──── stall detected ─────────► [fault]  fault_type = 'stall'

      [fault]
         │
         └──── acknowledged + stop ───► [idle]
```

### MotorFaultEvent.acknowledged

```
acknowledged = False  ──(POST /acknowledge/)──►  acknowledged = True
                                                  acknowledged_at = now()
                                                  acknowledged_by = request.user
```
Once acknowledged, cannot be un-acknowledged.

---

## Excluded Entities

- **MotorConfiguration** (target RPM, max current limit, ramp duration): Excluded from MVP. These parameters are stored in glove firmware. The platform does not need to store or push configuration for initial implementation.
- **MotorCommand** (audit log of commands sent): Excluded from MVP. Commands are fire-and-forward via MQTT; the resulting telemetry provides indirect confirmation. An audit table can be added in a future iteration.
