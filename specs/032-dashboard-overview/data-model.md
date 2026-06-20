# Data Model: Dashboard Overview Page

**Branch**: `032-dashboard-overview` | **Date**: 2026-02-20

---

## Overview

No new database models are introduced. This feature is purely read-only, computing aggregated metrics from four existing models.

---

## Entities Used (Read-Only)

### Patient
*Source model: `backend/patients/models.py`*

| Field | Type | Role in Dashboard |
|-------|------|-------------------|
| `id` | UUID/int | Join key |
| `created_by` | FK(CustomUser) | Scoping filter (direct creation) |
| `doctor_assignments` | reverse FK(DoctorPatientAssignment) | Primary scoping mechanism |

**Dashboard use**: Count all `Patient` records assigned to the logged-in doctor via `DoctorPatientAssignment.doctor = request.user`.

---

### Device
*Source model: `backend/devices/models.py`*

| Field | Type | Role in Dashboard |
|-------|------|-------------------|
| `patient` | FK(Patient) | Join to doctor's patients |
| `status` | choices: `online`/`offline` | Active device filter |

**Dashboard use**: Count `Device` records where `patient` is in the doctor's patient set AND `status = 'online'`.

---

### BiometricSession
*Source model: `backend/biometrics/models.py`*

| Field | Type | Role in Dashboard |
|-------|------|-------------------|
| `patient` | FK(Patient) | Join to doctor's patients |
| `session_start` | DateTimeField | 24-hour window filter for alerts |
| `ml_prediction` | JSONField `{severity, confidence}` | Alert detection (severity = 'severe') |

**Dashboard use**: Count `BiometricSession` records where `patient` is in the doctor's patient set, `session_start` is within the last 24 hours, and `ml_prediction__severity = 'severe'`.

---

### TremorMetrics
*Source model: `backend/biometrics/models.py`*

| Field | Type | Role in Dashboard |
|-------|------|-------------------|
| `patient` | FK(Patient) | Join to doctor's patients |
| `window_start` | DateTimeField | Date grouping and 7-day window filter |
| `dominant_amplitude` | FloatField | Tremor intensity value to average |

**Dashboard use**: Group by `window_start__date` over the last 7 calendar days, average `dominant_amplitude` per day, for all patients belonging to the doctor.

---

## API Response Shape

The new `GET /api/analytics/dashboard/` endpoint returns a single flat response object (no pagination). This is the "virtual entity" the frontend consumes:

### DashboardStats

| Field | Type | Description |
|-------|------|-------------|
| `total_patients` | integer ≥ 0 | Total patients assigned to the logged-in doctor |
| `active_devices` | integer ≥ 0 | Devices with `status = 'online'` across the doctor's patients |
| `alerts_count` | integer ≥ 0 | Severe ML predictions in the last 24 hours across the doctor's patients |
| `tremor_trend` | array[TremorTrendPoint] | 7 data points (one per day), ordered oldest to newest |

### TremorTrendPoint

| Field | Type | Description |
|-------|------|-------------|
| `date` | string (YYYY-MM-DD) | Calendar date of the data point |
| `avg_amplitude` | float \| null | Mean `dominant_amplitude` across all patients for that day; `null` if no data |

**Zero-data behaviour**:
- If no patients are assigned: all counts are 0, `tremor_trend` contains 7 entries with `avg_amplitude: null`
- If no TremorMetrics data exists for a day: that day's entry has `avg_amplitude: null`
- The `tremor_trend` array always contains exactly 7 entries (one per day from D-6 to D+0), even if some days have no data

---

## Frontend State Shape

```js
// useDashboardStats hook return value
{
  data: {
    total_patients: number,
    active_devices: number,
    alerts_count: number,
    tremor_trend: Array<{ date: string, avg_amplitude: number | null }>
  } | null,
  loading: boolean,
  error: string | null
}
```
