# API Contracts: Reports Page & PDF Download (Feature 035)

> Both endpoints already exist in the backend (Feature 003: Analytics and Reporting).
> This document describes how the frontend consumes them.

---

## Endpoint 1: Fetch Patient Statistics

### `GET /api/analytics/stats/`

Fetches daily aggregated tremor statistics for a patient over a date range. Used to populate the **Stats Preview** panel.

**Authentication**: Bearer JWT token (doctor role required; patient must be assigned)

### Query Parameters

| Parameter    | Type    | Required | Description                                            |
|--------------|---------|----------|--------------------------------------------------------|
| `patient_id` | integer | Yes      | Patient ID from URL param                              |
| `start_date` | string  | No       | ISO date `YYYY-MM-DD`; defaults to earliest session    |
| `end_date`   | string  | No       | ISO date `YYYY-MM-DD`; defaults to today               |
| `group_by`   | string  | No       | Always `day` for this feature                          |
| `page_size`  | integer | No       | Send `365` to cover a full year in one request         |

### Response: 200 OK

```json
{
  "count": 30,
  "next": null,
  "previous": null,
  "baseline": {
    "baseline_amplitude": 0.72,
    "baseline_sessions": [1, 2, 3],
    "baseline_period_start": "2025-10-01T09:00:00Z",
    "baseline_period_end": "2025-10-03T09:30:00Z"
  },
  "results": [
    {
      "period": "2026-01-22",
      "period_start": "2026-01-22T00:00:00Z",
      "period_end": "2026-01-22T23:59:59Z",
      "session_count": 2,
      "avg_amplitude": 0.45,
      "dominant_frequency": 4.8,
      "tremor_reduction_pct": 37.5,
      "ml_severity_summary": {
        "mild": 1,
        "moderate": 1,
        "severe": 0
      }
    }
  ]
}
```

### Empty Range Response: 200 OK with Empty Results

```json
{
  "count": 0,
  "next": null,
  "previous": null,
  "baseline": null,
  "results": []
}
```

### Error Responses

| Status | Code                     | When                                                  |
|--------|--------------------------|-------------------------------------------------------|
| 400    | `MISSING_PATIENT_ID`     | `patient_id` not provided                             |
| 400    | `INVALID_DATE_RANGE`     | `end_date` < `start_date`                             |
| 400    | `FUTURE_DATE`            | Either date is in the future                          |
| 403    | `PATIENT_ACCESS_FORBIDDEN` | Doctor not assigned to this patient                 |
| 404    | `PATIENT_NOT_FOUND`      | Patient ID does not exist                             |

---

## Endpoint 2: Generate & Download PDF Report

### `POST /api/analytics/reports/`

Generates a PDF report and returns it as a binary file attachment. Used by the **Download PDF** button.

**Authentication**: Bearer JWT token (doctor role required; patient must be assigned)

**Request Headers**:
```
Content-Type: application/json
Authorization: Bearer <jwt_token>
```

### Request Body

```json
{
  "patient_id": 1,
  "start_date": "2026-01-22",
  "end_date": "2026-02-21",
  "include_charts": true,
  "include_ml_summary": true
}
```

| Field               | Type    | Required | Default |
|---------------------|---------|----------|---------|
| `patient_id`        | integer | Yes      | —       |
| `start_date`        | string  | No       | earliest session |
| `end_date`          | string  | No       | today   |
| `include_charts`    | boolean | No       | `true`  |
| `include_ml_summary`| boolean | No       | `true`  |

### Response: 200 OK (Binary PDF)

```
Content-Type: application/pdf
Content-Disposition: attachment; filename="report_patient1_20260221_143022.pdf"

<binary PDF data>
```

**Frontend handling**: Axios with `responseType: 'blob'` → `URL.createObjectURL` → anchor click → `URL.revokeObjectURL`.

### Error Responses

| Status | Code                       | Frontend Message                                                    |
|--------|----------------------------|---------------------------------------------------------------------|
| 400    | `NO_DATA_FOR_REPORT`       | "No data available for this period — try a different date range."   |
| 400    | `PDF_SIZE_LIMIT_EXCEEDED`  | "Report too large — try a smaller date range (max ~90 days)."       |
| 400    | `REPORT_GENERATION_ERROR`  | "Report generation failed — please try again."                      |
| 403    | `PATIENT_ACCESS_FORBIDDEN` | Not reached (page itself is access-controlled)                      |
| 500    | `PDF_GENERATION_ERROR`     | "Report generation failed — please try again."                      |

---

## Frontend API Service Functions

To be added to `frontend/src/services/analyticsService.js`:

### `fetchPatientStats(patientId, startDate, endDate)`

```js
// GET /api/analytics/stats/?patient_id=X&start_date=X&end_date=X&group_by=day&page_size=365
export const fetchPatientStats = async (patientId, startDate, endDate) => {
  const response = await api.get('/analytics/stats/', {
    params: {
      patient_id: patientId,
      start_date: startDate,
      end_date: endDate,
      group_by: 'day',
      page_size: 365,
    },
  });
  return response.data; // { count, baseline, results }
};
```

### `downloadPatientReport(patientId, startDate, endDate)`

```js
// POST /api/analytics/reports/ — returns Blob
export const downloadPatientReport = async (patientId, startDate, endDate) => {
  const response = await api.post(
    '/analytics/reports/',
    { patient_id: patientId, start_date: startDate, end_date: endDate },
    { responseType: 'blob' }
  );
  return response.data; // Blob
};
```
