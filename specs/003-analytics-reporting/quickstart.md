# Quickstart: Analytics and Reporting Integration Tests

**Feature**: 003-analytics-reporting
**Purpose**: End-to-end integration test scenarios for analytics endpoints
**Prerequisites**: Django server running, test users created, biometric sessions with historical data

---

## Prerequisites Setup

### 1. Test Data Requirements

**Minimum Data**:
- 1 patient with doctor assignment
- 1 device paired to patient
- At least 10 biometric sessions spanning 5+ days
- Some sessions should have ML predictions

**Create Test Data** (if not exists):
```bash
cd backend
python manage.py shell

# In Django shell:
from biometrics.models import BiometricSession
from patients.models import Patient
from devices.models import Device
from datetime import datetime, timedelta
import json

patient = Patient.objects.get(id=4)  # Use existing test patient
device = Device.objects.first()

# Create 10 test sessions over 5 days
for i in range(10):
    BiometricSession.objects.create(
        patient=patient,
        device=device,
        session_start=datetime.now() - timedelta(days=5-i//2, hours=i),
        session_duration=timedelta(minutes=15),
        sensor_data={
            'tremor_intensity': [0.45 - (i*0.02), 0.48 - (i*0.02), 0.42 - (i*0.02)],
            'frequency': 4.5 + (i * 0.1),
            'timestamps': ['2026-02-10T10:00:00Z', '2026-02-10T10:00:01Z', '2026-02-10T10:00:02Z']
        },
        ml_prediction={'severity': 'moderate' if i < 7 else 'mild', 'confidence': 0.85},
        ml_predicted_at=datetime.now(),
        received_via_mqtt=True
    )
```

### 2. Authentication

**Get JWT Token**:
```bash
# Login as doctor
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"doctor@test.com","password":"doctor123"}'

# Save access token from response
export TOKEN="<access_token_here>"
```

---

## Scenario 1: Query Daily Statistics (MVP - User Story 1)

**Goal**: Retrieve aggregated tremor statistics grouped by day

**Setup**:
- Patient ID: 4 (or use your test patient ID)
- Date range: Last 30 days
- Grouping: By day

**Execute**:
```bash
curl -X GET "http://localhost:8000/api/analytics/stats/?patient_id=4&group_by=day&start_date=2026-01-15&end_date=2026-02-15" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

**Expected Result**:
```json
{
  "count": 5,
  "next": null,
  "previous": null,
  "baseline": {
    "baseline_amplitude": 0.45,
    "baseline_sessions": [1, 2, 3],
    "baseline_period_start": "2026-02-10T08:00:00Z",
    "baseline_period_end": "2026-02-10T12:00:00Z"
  },
  "results": [
    {
      "period": "2026-02-11",
      "period_start": "2026-02-11T00:00:00Z",
      "period_end": "2026-02-11T23:59:59Z",
      "session_count": 2,
      "avg_amplitude": 0.42,
      "dominant_frequency": 4.7,
      "tremor_reduction_pct": 6.7,
      "ml_severity_summary": {
        "mild": 0,
        "moderate": 2,
        "severe": 0
      }
    },
    {
      "period": "2026-02-12",
      "period_start": "2026-02-12T00:00:00Z",
      "period_end": "2026-02-12T23:59:59Z",
      "session_count": 2,
      "avg_amplitude": 0.38,
      "dominant_frequency": 4.9,
      "tremor_reduction_pct": 15.6,
      "ml_severity_summary": {
        "mild": 1,
        "moderate": 1,
        "severe": 0
      }
    }
  ]
}
```

**Validation**:
- ✅ Response status 200
- ✅ Baseline calculated from first 3 sessions
- ✅ Statistics grouped by day (multiple sessions per day aggregated)
- ✅ `tremor_reduction_pct` shows positive values (improvement)
- ✅ `ml_severity_summary` counts match session_count
- ✅ Results ordered chronologically (oldest first)

---

## Scenario 2: Query Session-Level Statistics

**Goal**: Retrieve statistics for each individual session

**Setup**:
- Same patient as Scenario 1
- Grouping: By session

**Execute**:
```bash
curl -X GET "http://localhost:8000/api/analytics/stats/?patient_id=4&group_by=session&start_date=2026-02-10&end_date=2026-02-15" \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Result**:
```json
{
  "count": 10,
  "next": null,
  "previous": null,
  "baseline": {
    "baseline_amplitude": 0.45,
    "baseline_sessions": [1, 2, 3],
    "baseline_period_start": "2026-02-10T08:00:00Z",
    "baseline_period_end": "2026-02-10T12:00:00Z"
  },
  "results": [
    {
      "period": "4",
      "period_start": "2026-02-11T08:00:00Z",
      "period_end": "2026-02-11T08:15:00Z",
      "session_count": 1,
      "avg_amplitude": 0.39,
      "dominant_frequency": 4.8,
      "tremor_reduction_pct": 13.3,
      "ml_severity_summary": {
        "mild": 0,
        "moderate": 1,
        "severe": 0
      }
    }
  ]
}
```

**Validation**:
- ✅ Each result has `session_count = 1`
- ✅ `period` is session ID (e.g., "4", "5", "6")
- ✅ `period_start` and `period_end` match individual session times
- ✅ Individual session statistics calculated correctly

---

## Scenario 3: Statistics with No Data

**Goal**: Handle request for date range with no biometric sessions

**Setup**:
- Date range: Future dates or range with no data

**Execute**:
```bash
curl -X GET "http://localhost:8000/api/analytics/stats/?patient_id=4&start_date=2025-01-01&end_date=2025-01-31" \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Result**:
```json
{
  "count": 0,
  "next": null,
  "previous": null,
  "baseline": null,
  "results": []
}
```

**Validation**:
- ✅ Response status 200 (not 404)
- ✅ Empty results array
- ✅ Baseline is null (no sessions to calculate from)
- ✅ Count is 0

---

## Scenario 4: Invalid Date Range Error

**Goal**: Validate date range validation works

**Setup**:
- End date before start date

**Execute**:
```bash
curl -X GET "http://localhost:8000/api/analytics/stats/?patient_id=4&start_date=2026-02-15&end_date=2026-02-10" \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Result**:
```json
{
  "error": "Invalid date range",
  "detail": "end_date must be greater than or equal to start_date",
  "code": "INVALID_DATE_RANGE",
  "field": "end_date"
}
```

**Validation**:
- ✅ Response status 400 Bad Request
- ✅ Clear error message
- ✅ Error code provided for programmatic handling

---

## Scenario 5: Unauthorized Access (Patient Trying to Access Another Patient)

**Goal**: Verify access control prevents unauthorized data access

**Setup**:
- Login as patient (not doctor)
- Try to access different patient's statistics

**Execute**:
```bash
# Login as patient
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"patient@test.com","password":"patient123"}'

export PATIENT_TOKEN="<patient_access_token>"

# Try to access another patient's data (patient ID 1 instead of 4)
curl -X GET "http://localhost:8000/api/analytics/stats/?patient_id=1" \
  -H "Authorization: Bearer $PATIENT_TOKEN"
```

**Expected Result**:
```json
{
  "error": "Access forbidden",
  "detail": "You do not have permission to access this patient's data",
  "code": "PATIENT_ACCESS_FORBIDDEN"
}
```

**Validation**:
- ✅ Response status 403 Forbidden
- ✅ Patient can only access their own data (patient_id matches user's patient record)
- ✅ Doctors can access all assigned patients

---

## Scenario 6: Generate PDF Report (User Story 2)

**Goal**: Generate comprehensive PDF report with charts and statistics

**Setup**:
- Patient with multiple sessions
- Date range covering at least 5 days

**Execute**:
```bash
curl -X POST http://localhost:8000/api/analytics/reports/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": 4,
    "start_date": "2026-02-10",
    "end_date": "2026-02-15",
    "include_charts": true,
    "include_ml_summary": true
  }' \
  --output report.pdf
```

**Expected Result**:
- PDF file downloaded as `report.pdf`
- File size < 5MB
- HTTP status 200
- Content-Type: application/pdf
- Content-Disposition header with filename

**Validation**:
- ✅ PDF file created successfully
- ✅ File size under 5MB (check with `ls -lh report.pdf`)
- ✅ PDF opens without errors
- ✅ Contains:
  - Patient information header
  - Statistics summary table
  - Line charts showing tremor trends
  - ML severity distribution
  - Date range and generation timestamp

**Manual Verification**:
```bash
# Check file size
ls -lh report.pdf

# Open PDF (platform-specific)
# Windows: start report.pdf
# Mac: open report.pdf
# Linux: xdg-open report.pdf
```

---

## Scenario 7: PDF Report with Large Dataset

**Goal**: Test PDF generation performance and file size with 100+ sessions

**Setup**:
- Patient with 100+ biometric sessions
- Date range: 6 months

**Execute**:
```bash
curl -X POST http://localhost:8000/api/analytics/reports/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": 4,
    "start_date": "2025-08-01",
    "end_date": "2026-02-15",
    "include_charts": true,
    "include_ml_summary": true
  }' \
  --output large_report.pdf \
  -w "\nTime: %{time_total}s\n"
```

**Expected Result**:
- PDF generated successfully
- Generation time < 10 seconds (per SC-003)
- File size < 5MB (per SC-004)

**Validation**:
- ✅ Response time under 10 seconds
- ✅ PDF file size under 5MB
- ✅ PDF contains all sessions (may be summarized in tables)
- ✅ Charts are readable (not too crowded)

---

## Scenario 8: Report Generation with No Data

**Goal**: Handle report request when no sessions exist

**Setup**:
- Date range with no biometric sessions

**Execute**:
```bash
curl -X POST http://localhost:8000/api/analytics/reports/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": 4,
    "start_date": "2025-01-01",
    "end_date": "2025-01-31"
  }'
```

**Expected Result**:
```json
{
  "error": "Insufficient data",
  "detail": "No biometric sessions found for patient in specified date range",
  "code": "NO_DATA_FOR_REPORT"
}
```

**Validation**:
- ✅ Response status 400 Bad Request
- ✅ Clear error message explaining why report cannot be generated
- ✅ No PDF file created

---

## Scenario 9: Pagination with Large Result Set

**Goal**: Test pagination when statistics query returns many data points

**Setup**:
- Patient with 100+ sessions
- Request page 2 with page_size=10

**Execute**:
```bash
# First page
curl -X GET "http://localhost:8000/api/analytics/stats/?patient_id=4&group_by=session&page=1&page_size=10" \
  -H "Authorization: Bearer $TOKEN"

# Second page
curl -X GET "http://localhost:8000/api/analytics/stats/?patient_id=4&group_by=session&page=2&page_size=10" \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Result**:
```json
{
  "count": 105,
  "next": "http://localhost:8000/api/analytics/stats/?page=3&patient_id=4&group_by=session&page_size=10",
  "previous": "http://localhost:8000/api/analytics/stats/?page=1&patient_id=4&group_by=session&page_size=10",
  "baseline": { ... },
  "results": [ /* 10 items */ ]
}
```

**Validation**:
- ✅ Results array contains exactly 10 items (page_size)
- ✅ `count` reflects total number of results
- ✅ `next` and `previous` URLs provided for navigation
- ✅ Baseline included on all pages (same baseline for all requests)

---

## Scenario 10: Performance Benchmark - 365 Days Query

**Goal**: Validate performance meets SC-001 (< 3 seconds for 1 year of data)

**Setup**:
- Patient with sessions spanning 365 days
- Query entire year with daily grouping

**Execute**:
```bash
curl -X GET "http://localhost:8000/api/analytics/stats/?patient_id=4&group_by=day&start_date=2025-02-15&end_date=2026-02-15" \
  -H "Authorization: Bearer $TOKEN" \
  -w "\nResponse Time: %{time_total}s\n" \
  -o /dev/null -s
```

**Expected Result**:
- Response time < 3 seconds

**Validation**:
- ✅ Query completes in under 3 seconds
- ✅ Results returned successfully
- ✅ No timeout errors

**Performance Debugging** (if fails):
```bash
# Check for missing database indexes
cd backend
python manage.py dbshell

# In PostgreSQL:
EXPLAIN ANALYZE SELECT * FROM biometrics_biometricsession
WHERE patient_id = 4
AND session_start >= '2025-02-15'
AND session_start <= '2026-02-15'
ORDER BY session_start;
```

---

## Cleanup

**Remove Test Data** (if needed):
```bash
cd backend
python manage.py shell

# Delete test sessions
from biometrics.models import BiometricSession
BiometricSession.objects.filter(patient_id=4).delete()
```

**Remove Test PDF Files**:
```bash
rm report.pdf large_report.pdf
```

---

## Summary Checklist

**Statistics Endpoint (User Story 1)**:
- ✅ Scenario 1: Daily statistics retrieval
- ✅ Scenario 2: Session-level statistics
- ✅ Scenario 3: Empty result handling
- ✅ Scenario 4: Date validation
- ✅ Scenario 5: Access control
- ✅ Scenario 9: Pagination
- ✅ Scenario 10: Performance (365 days)

**PDF Reports (User Story 2)**:
- ✅ Scenario 6: Basic PDF generation
- ✅ Scenario 7: Large dataset PDF (100+ sessions)
- ✅ Scenario 8: No data error handling

**Success Criteria Validation**:
- ✅ SC-001: Statistics queries < 3 seconds (Scenario 10)
- ✅ SC-003: PDF generation < 10 seconds (Scenario 7)
- ✅ SC-004: PDF files < 5MB (Scenario 6, 7)
- ✅ SC-006: Tremor reduction reflects actual trends (Scenario 1)

**All Scenarios Passed**: Feature ready for production ✅
