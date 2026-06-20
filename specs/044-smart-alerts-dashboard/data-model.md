# Data Model: Smart Medical Alerts & Dashboard Layout Simplification

**Branch**: `044-smart-alerts-dashboard` | **Date**: 2026-06-14

## New Entities

**None.** This feature introduces no new database tables, models, or migrations. All data already exists in the `BiometricSession` model.

---

## Existing Entities Used

### BiometricSession (READ ONLY)

**Location**: `backend/biometrics/models.py`

| Field | Type | Role in this feature |
|-------|------|----------------------|
| `id` | AutoField | Primary key |
| `patient_id` | ForeignKey → Patient | Used to scope query to doctor's patients |
| `session_start` | DateTimeField | Truncated to date for per-day grouping |
| `ml_prediction` | JSONField | `ml_prediction['severity']` checked for value `'severe'` |

**How the feature reads this model**:

```
BiometricSession.objects
  .filter(
      patient__in=<doctor's_patients>,
      session_start__date__gte=<today - 4 days>,
      session_start__date__lte=<today>,
      ml_prediction__severity='severe'
  )
  .annotate(day=TruncDate('session_start'))
  .values('patient_id', 'day')
  .distinct()
```

The result is a flat list of `(patient_id, day)` pairs. Each pair represents one calendar day on which that patient had at least one severe session. Python-side logic then checks whether all 5 required days are present for each patient.

---

### Patient (READ ONLY)

**Location**: `backend/patients/models.py`

Used only to scope the BiometricSession query to the authenticated doctor's patients:

```
Patient.objects.filter(doctor_assignments__doctor=<request.user>)
```

No new fields or relationships are introduced.

---

## Derived Metric (API-level, not persisted)

### CriticalAlertsCount

This is a computed aggregate returned by `GET /api/analytics/critical-alerts/`. It is **not stored** in the database.

| Attribute | Description |
|-----------|-------------|
| `count` | Integer. Number of patients (in the doctor's cohort) who had at least one severe BiometricSession on each of the 5 consecutive calendar days ending today. |

**Business rule**: A patient is counted if and only if `required_days ⊆ patient_severe_days`, where `required_days = {today, today-1, today-2, today-3, today-4}` and `patient_severe_days` is the set of dates with ≥1 severe session.

---

## Impact on Existing Serializers

| Serializer | Change |
|------------|--------|
| `TremorTrendPointSerializer` | REMOVED — no longer needed (chart deleted) |
| `DashboardStatsSerializer` | Remove `tremor_trend` and `alerts_count` fields; keep `total_patients` and `active_devices` |
| `CriticalAlertsSerializer` | ADDED — `{ "count": integer }` |
