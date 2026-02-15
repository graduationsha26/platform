# Data Model: Analytics and Reporting

**Feature**: Analytics and Reporting (003)
**Created**: 2026-02-15
**Purpose**: Define data structures for tremor statistics and PDF reports

---

## Overview

This feature does **NOT introduce new database models**. All analytics are computed on-demand from existing `BiometricSession` records. This document defines the **computed entities** (response schemas) and their relationships to existing models.

---

## Existing Models (Dependencies)

### BiometricSession
**Location**: `backend/biometrics/models.py` (from Feature 002)

**Key Fields** (used by analytics):
```python
class BiometricSession(models.Model):
    patient = ForeignKey(Patient)               # Link to patient
    device = ForeignKey(Device)                 # Link to device
    session_start = DateTimeField()             # Session timestamp
    session_duration = DurationField()          # How long session lasted
    sensor_data = JSONField()                   # Raw sensor data
        # Contains: tremor_intensity (list), frequency (float), timestamps (list)
    ml_prediction = JSONField(null=True)        # ML prediction results
        # Contains: severity (str), confidence (float)
    ml_predicted_at = DateTimeField(null=True)  # When prediction was made
    received_via_mqtt = BooleanField()          # Data source flag
```

**Relationships**:
- Belongs to one `Patient`
- Belongs to one `Device`
- Many sessions per patient (historical data)

---

## Computed Entities (Response Schemas)

### TremorStatistics

**Purpose**: Aggregated tremor metrics for a time period (session or day)

**Type**: Computed entity (not stored in database)

**Attributes**:

| Field | Type | Description | Calculation |
|-------|------|-------------|-------------|
| `period` | string | Time period identifier | Session ID (session level) or Date YYYY-MM-DD (daily level) |
| `period_start` | datetime | Start of period | Session start timestamp or midnight of date |
| `period_end` | datetime | End of period | Session end or 23:59:59 of date |
| `session_count` | integer | Number of sessions in period | Count of BiometricSession records |
| `avg_amplitude` | float | Average tremor intensity | Mean of all `sensor_data.tremor_intensity` values |
| `dominant_frequency` | float | Dominant tremor frequency (Hz) | Mean of `sensor_data.frequency` across sessions |
| `tremor_reduction_pct` | float (nullable) | Tremor reduction vs baseline (%) | `((baseline - current) / baseline) * 100` |
| `ml_severity_summary` | object (nullable) | ML prediction distribution | Count of mild/moderate/severe across sessions |

**Example JSON**:
```json
{
  "period": "2026-02-15",
  "period_start": "2026-02-15T00:00:00Z",
  "period_end": "2026-02-15T23:59:59Z",
  "session_count": 3,
  "avg_amplitude": 0.42,
  "dominant_frequency": 4.8,
  "tremor_reduction_pct": 18.5,
  "ml_severity_summary": {
    "mild": 1,
    "moderate": 2,
    "severe": 0
  }
}
```

**Validation Rules**:
- `avg_amplitude`: 0.0 ≤ value ≤ 1.0 (normalized tremor intensity)
- `dominant_frequency`: value ≥ 0 (Hz, cannot be negative)
- `tremor_reduction_pct`: -100 ≤ value ≤ 100 (can be negative if worsened)
- `session_count`: value ≥ 1 (at least one session to have statistics)
- `ml_severity_summary`: Sum of mild + moderate + severe = session_count

**Null Handling**:
- `tremor_reduction_pct`: Null if baseline cannot be calculated (< 1 session total) or baseline = 0
- `ml_severity_summary`: Null if no ML predictions available for any session in period

---

### Baseline

**Purpose**: Reference point for calculating tremor reduction

**Type**: Computed value (not stored)

**Calculation Method**: Average of first 3 sessions (or all sessions if < 3 total)

**Attributes**:

| Field | Type | Description |
|-------|------|-------------|
| `baseline_amplitude` | float | Average tremor amplitude from baseline sessions |
| `baseline_sessions` | list[int] | Session IDs used for baseline calculation |
| `baseline_period_start` | datetime | Timestamp of earliest baseline session |
| `baseline_period_end` | datetime | Timestamp of latest baseline session |

**Example JSON**:
```json
{
  "baseline_amplitude": 0.52,
  "baseline_sessions": [101, 102, 103],
  "baseline_period_start": "2026-01-10T09:00:00Z",
  "baseline_period_end": "2026-01-10T18:30:00Z"
}
```

**Edge Cases**:
- If only 1 session exists: Use that single session as baseline
- If only 2 sessions exist: Use both as baseline
- If 3+ sessions exist: Use first 3 chronologically
- If baseline_amplitude = 0: Cannot calculate tremor_reduction_pct (return None)

---

### PDFReport

**Purpose**: Metadata for generated PDF report

**Type**: Transient (temporary file, not stored in database)

**Attributes**:

| Field | Type | Description |
|-------|------|-------------|
| `filename` | string | Generated filename | Format: `report_patient{id}_{timestamp}.pdf` |
| `file_size_mb` | float | PDF file size in MB | Must be < 5MB per SC-004 |
| `generated_at` | datetime | Report generation timestamp | Server timestamp |
| `patient_id` | integer | Patient ID for this report | From request parameter |
| `date_range_start` | date | Report start date | From request parameter |
| `date_range_end` | date | Report end date | From request parameter |
| `total_sessions` | integer | Number of sessions included | Count of sessions in date range |
| `chart_count` | integer | Number of charts in PDF | Typically 2-3 charts |

**Example JSON** (metadata response):
```json
{
  "filename": "report_patient4_20260215_143022.pdf",
  "file_size_mb": 2.8,
  "generated_at": "2026-02-15T14:30:22Z",
  "patient_id": 4,
  "date_range_start": "2026-01-01",
  "date_range_end": "2026-02-15",
  "total_sessions": 42,
  "chart_count": 3
}
```

**File Lifecycle**:
1. **Generation**: Created in `media/reports/` directory
2. **Download**: Sent as HTTP response with `Content-Disposition: attachment`
3. **Cleanup**: Deleted immediately after download OR after 24 hours (whichever comes first)

---

## Relationships

```
Patient (existing)
  └─► BiometricSession (existing, many)
        └─► TremorStatistics (computed, many per patient)
              └─► Baseline (computed, 1 per patient)
                    └─► PDFReport (transient file)
```

**Flow**:
1. Patient has many BiometricSession records (historical data)
2. Analytics service queries BiometricSession records for patient
3. Calculates Baseline from first 3 sessions
4. Aggregates sessions into TremorStatistics (by day or session)
5. Generates PDFReport containing TremorStatistics and charts

---

## Statistics Calculation Formulas

### Average Amplitude

**Input**: `sensor_data.tremor_intensity` (array of floats, 0.0-1.0)

**Formula**:
```
avg_amplitude = mean(
  flatten([session.sensor_data.tremor_intensity for session in sessions])
)
```

**Example**:
- Session 1: `tremor_intensity = [0.25, 0.30, 0.28]`
- Session 2: `tremor_intensity = [0.35, 0.32]`
- Result: `avg_amplitude = mean([0.25, 0.30, 0.28, 0.35, 0.32]) = 0.30`

---

### Dominant Frequency

**Input**: `sensor_data.frequency` (float, Hz)

**Formula**:
```
dominant_frequency = mean([session.sensor_data.frequency for session in sessions])
```

**Example**:
- Session 1: `frequency = 4.5`
- Session 2: `frequency = 4.8`
- Session 3: `frequency = 5.1`
- Result: `dominant_frequency = mean([4.5, 4.8, 5.1]) = 4.8`

---

### Tremor Reduction Percentage

**Input**: `baseline_amplitude`, `current_avg_amplitude`

**Formula**:
```
tremor_reduction_pct = ((baseline_amplitude - current_avg_amplitude) / baseline_amplitude) * 100
```

**Example**:
- Baseline amplitude: 0.50
- Current amplitude (recent 7 days): 0.40
- Result: `tremor_reduction_pct = ((0.50 - 0.40) / 0.50) * 100 = 20.0%`

**Interpretation**:
- **Positive value**: Tremor improved (amplitude decreased)
- **Negative value**: Tremor worsened (amplitude increased)
- **Zero**: No change
- **Null**: Cannot calculate (no baseline or baseline = 0)

---

### ML Severity Summary

**Input**: `ml_prediction.severity` (string: "mild" | "moderate" | "severe")

**Formula**:
```
ml_severity_summary = {
  "mild": count(sessions where ml_prediction.severity == "mild"),
  "moderate": count(sessions where ml_prediction.severity == "moderate"),
  "severe": count(sessions where ml_prediction.severity == "severe")
}
```

**Example**:
- 10 sessions total
- 3 sessions: severity = "mild"
- 6 sessions: severity = "moderate"
- 1 session: severity = "severe"
- Result: `{"mild": 3, "moderate": 6, "severe": 1}`

---

## Grouping Logic

### Session-Level Grouping

**Definition**: Each TremorStatistics entry represents one BiometricSession

**Use Case**: Detailed view of individual sessions

**Implementation**:
```python
for session in sessions:
    yield TremorStatistics(
        period=str(session.id),
        period_start=session.session_start,
        period_end=session.session_start + session.session_duration,
        session_count=1,
        avg_amplitude=mean(session.sensor_data['tremor_intensity']),
        dominant_frequency=session.sensor_data['frequency'],
        tremor_reduction_pct=calculate_reduction(session, baseline),
        ml_severity_summary={"mild": 1} if session.ml_prediction else None
    )
```

---

### Daily Grouping

**Definition**: Each TremorStatistics entry represents all sessions on a single day

**Use Case**: Trend analysis over days/weeks/months

**Implementation**:
```python
sessions_by_date = group_by(sessions, lambda s: s.session_start.date())

for date, day_sessions in sessions_by_date.items():
    all_intensities = flatten([s.sensor_data['tremor_intensity'] for s in day_sessions])
    all_frequencies = [s.sensor_data['frequency'] for s in day_sessions]

    yield TremorStatistics(
        period=str(date),
        period_start=datetime.combine(date, time.min),
        period_end=datetime.combine(date, time.max),
        session_count=len(day_sessions),
        avg_amplitude=mean(all_intensities),
        dominant_frequency=mean(all_frequencies),
        tremor_reduction_pct=calculate_reduction(day_sessions, baseline),
        ml_severity_summary=aggregate_ml_predictions(day_sessions)
    )
```

---

## Index Requirements (Database Optimization)

**Recommended Indexes** on `BiometricSession` table:

```sql
-- Composite index for date range queries on patient data
CREATE INDEX idx_biometric_patient_date
ON biometrics_biometricsession(patient_id, session_start);

-- Index for ordering by timestamp (baseline calculation)
CREATE INDEX idx_biometric_session_start
ON biometrics_biometricsession(session_start);
```

**Rationale**:
- Statistics queries always filter by `patient_id` and `session_start` range
- Baseline calculation orders by `session_start` and limits to 3
- These indexes support both use cases efficiently

---

## Data Retention

**No new data stored** - all analytics computed on-demand from existing BiometricSession records.

**Temporary Files** (PDFs):
- **Retention**: Maximum 24 hours
- **Cleanup**: Immediate deletion after download + daily cleanup task
- **Storage Location**: `media/reports/` (temporary directory)

---

## Validation Summary

**Input Validation** (API request parameters):
- `patient_id`: Must be valid integer, user must have access to patient
- `start_date`, `end_date`: Must be valid dates in ISO format (YYYY-MM-DD)
- `end_date` must be ≥ `start_date`
- Neither date can be in the future
- `group_by`: Must be "session" or "day"

**Output Validation** (computed values):
- `avg_amplitude`: Range [0.0, 1.0]
- `dominant_frequency`: Non-negative float
- `tremor_reduction_pct`: Range [-100, 100] or None
- `session_count`: Positive integer
- PDF `file_size_mb`: Must be ≤ 5.0

---

## Error Handling

**Common Error Scenarios**:

1. **No sessions found**: Return 200 with empty array `[]` and message
2. **Insufficient sessions for baseline**: Set `tremor_reduction_pct` to None
3. **Missing ML predictions**: Set `ml_severity_summary` to None
4. **Invalid date range**: Return 400 Bad Request with error message
5. **Unauthorized access**: Return 403 Forbidden
6. **PDF generation failure**: Return 500 Internal Server Error, log exception

---

## Summary

**Key Points**:
- No new database tables - all computed from existing BiometricSession data
- TremorStatistics is response schema, not a model
- Baseline calculated from first 3 sessions
- Statistics can be grouped by session or by day
- PDF reports are temporary files, deleted after use
- Indexes recommended for performance optimization

**Ready for**: API contract design (contracts/analytics-api.yaml)
