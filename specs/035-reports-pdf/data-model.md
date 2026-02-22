# Data Model: Reports Page & PDF Download (Feature 035)

> **Note**: This feature is entirely frontend. No new database models or migrations are required.
> All data is read from existing backend endpoints. This document describes the data shapes
> flowing between the API and the frontend.

---

## Frontend Data Shapes

### DateRange

The user-selected time window for the report.

| Field        | Type   | Constraints                              | Default              |
|--------------|--------|------------------------------------------|----------------------|
| `startDate`  | string | ISO date `YYYY-MM-DD`; not after today   | Today minus 29 days  |
| `endDate`    | string | ISO date `YYYY-MM-DD`; not after today   | Today                |

**Validation rules**:
- `startDate` must be ≤ `endDate` (inline error if violated)
- Neither date may be in the future (`max` attribute = today)
- Range must not exceed 365 days (UI warning)

---

### StatsResult

One item from the `GET /api/analytics/stats/` response `results` array.

| Field                | Type          | Description                                          |
|----------------------|---------------|------------------------------------------------------|
| `period`             | string        | ISO date `YYYY-MM-DD` (daily group_by)               |
| `period_start`       | ISO datetime  | Start of the day                                     |
| `period_end`         | ISO datetime  | End of the day                                       |
| `session_count`      | integer       | Sessions recorded that day                           |
| `avg_amplitude`      | float 0–1     | Mean tremor amplitude for the day (normalized)       |
| `dominant_frequency` | float Hz      | Dominant tremor frequency for the day                |
| `tremor_reduction_pct` | float\|null | Reduction vs patient baseline; positive = improvement |
| `ml_severity_summary` | object\|null | `{ mild, moderate, severe }` session counts          |

---

### StatsSummary

Aggregated from all `StatsResult` items in the selected date range, computed client-side.

| Field                      | Type        | Derivation                                                |
|----------------------------|-------------|-----------------------------------------------------------|
| `avgAmplitude`             | float 0–1   | Mean of all `avg_amplitude` values across the period      |
| `maxAmplitude`             | float 0–1   | Maximum of all `avg_amplitude` values across the period   |
| `dominantFrequency`        | float Hz    | Mean of all `dominant_frequency` values across the period |
| `tremorReductionPct`       | float\|null | Mean of all non-null `tremor_reduction_pct` values; null if no baseline |
| `sessionCount`             | integer     | Sum of all `session_count` values                         |
| `hasData`                  | boolean     | True if at least one `StatsResult` exists                 |

---

### ReportRequest

Sent as JSON body in `POST /api/analytics/reports/` to trigger PDF generation.

| Field               | Type    | Required | Description                                  |
|---------------------|---------|----------|----------------------------------------------|
| `patient_id`        | integer | Yes      | Patient to generate the report for           |
| `start_date`        | string  | No       | ISO date; defaults to patient's first session|
| `end_date`          | string  | No       | ISO date; defaults to today                  |
| `include_charts`    | boolean | No       | Default `true` — include trend charts        |
| `include_ml_summary`| boolean | No       | Default `true` — include ML severity section |

---

## Existing Backend Entities (Reference — Not Modified)

### BiometricSession (existing)
Represents one tremor monitoring session for a patient. The `StatisticsService` aggregates sessions into daily `StatsResult` records.

### TremorMetrics (existing)
Per-2.56-second FFT window result. Contains `dominant_amplitude` and `dominant_freq_hz`. Not directly used by this feature (stats API provides the aggregated values).

### Patient (existing)
Patient profile. The report is scoped to a single patient. `patient_id` from the URL param (`/doctor/patients/:id/reports`) identifies the target.

### PatientBaseline (derived, not a model)
The first 1–3 sessions of a patient. Used server-side to compute `tremor_reduction_pct`. Returned as `baseline.baseline_amplitude` in the stats API response. No new model needed.
