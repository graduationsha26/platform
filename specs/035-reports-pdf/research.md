# Research: Reports Page & PDF Download (Feature 035)

## R-001: PDF Download in the Browser

**Decision**: Use Axios with `responseType: 'blob'` + `URL.createObjectURL()` + a programmatic anchor click.

**Rationale**: Axios is already the project's HTTP client with JWT auth interceptors pre-wired. Setting `responseType: 'blob'` on the POST request to `/api/analytics/reports/` causes Axios to return the binary PDF response as a `Blob`. A temporary `<a>` element is created with `href = URL.createObjectURL(blob)` and `download = 'report.pdf'`, then `.click()` is called programmatically to trigger the browser's native file download dialog. The object URL is revoked after to free memory.

**Alternatives considered**:
- `window.open(url)` / iframe redirect: Does not work for POST requests without additional backend redirect logic.
- `fetch()` with manual blob: Functionally identical but bypasses the existing JWT interceptor — rejected because it would require duplicating auth logic.
- Server-side redirect to a temporary URL: More complex, requires a two-step handshake — out of scope for local dev.

**Pattern**:
```js
const response = await api.post('/analytics/reports/', payload, { responseType: 'blob' });
const url = URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
const a = document.createElement('a');
a.href = url;
a.download = `report_patient${patientId}_${startDate}_${endDate}.pdf`;
a.click();
URL.revokeObjectURL(url);
```

---

## R-002: Date Range Picker Component

**Decision**: Two native HTML5 `<input type="date">` fields with a `max` attribute set to today's date (ISO string) to prevent future date selection. Inline validation checks that `startDate <= endDate` before any fetch.

**Rationale**: The existing `PatientForm.jsx` already uses `<input type="date">` with `max={new Date().toISOString().split('T')[0]}` — matching this pattern maintains zero new dependencies and consistent UX.

**Alternatives considered**:
- `react-datepicker` library: Adds ~30 KB to bundle, no constitutional allowance. Rejected.
- `<input type="date">` + `date-fns`: Adds dependency for date formatting not needed here. Rejected.

**Default range**: "last 30 days" — start = `YYYY-MM-DD` for 29 days ago, end = today. Both computed client-side on page load using `Date` arithmetic.

---

## R-003: Max Amplitude Computation

**Decision**: Computed client-side by taking `Math.max(...results.map(r => r.avg_amplitude))` over all records returned by the stats API.

**Rationale**: The `GET /api/analytics/stats/` endpoint returns `avg_amplitude` (daily average) but no `max_amplitude` field. The per-day average IS the most meaningful "max amplitude" signal for a summary view — the maximum daily average amplitude across the period tells the doctor "what was the worst day". The computation is trivial and avoids adding a new backend field.

**Alternatives considered**:
- Add `max_amplitude` to the backend `StatisticsService`: Would require changes to `statistics.py`, `calculations.py`, and `serializers.py`. Rejected as disproportionate backend work for a derived metric computable in one line.
- Use `TremorMetrics.dominant_amplitude` (per-2.56s window): Would require a separate aggregation endpoint. Rejected — more complex, unnecessary.

---

## R-004: Stats Fetch Strategy

**Decision**: Single `GET /api/analytics/stats/?patient_id=X&start_date=X&end_date=X&group_by=day&page_size=365` request. `page_size=365` covers a full year's worth of daily data in one request.

**Rationale**: The max recommended date range for PDF generation is ~90 days (backend 5MB limit). Even for the stats preview, 365 days is a safe upper bound. Fetching all data in one request simplifies aggregation for the max amplitude calculation.

**Constraint**: If a doctor selects a date range > 365 days, a UI warning should limit the range ("Maximum range is 365 days"). This prevents both backend PDF size issues and excessive frontend aggregation.

---

## R-005: No New Backend Endpoints Required

**Decision**: Feature 035 is entirely a frontend addition. Both necessary backend endpoints already exist:
- `GET /api/analytics/stats/` — returns paginated daily statistics per patient
- `POST /api/analytics/reports/` — generates and returns a PDF as a binary attachment

**Existing backend behavior confirmed**:
- `tremor_reduction_pct`: `((baseline_amplitude - current_amplitude) / baseline_amplitude) * 100` vs the patient's first 1–3 sessions. Positive = improvement, negative = worsening. `null` if no baseline exists.
- `avg_amplitude`: normalized float 0.0–1.0 (daily average across all sessions in the day)
- `dominant_frequency`: Hz — dominant tremor frequency for that day
- PDF size limit: 5 MB (`PDF_SIZE_LIMIT_EXCEEDED` error code if exceeded)

---

## R-006: Error Handling

**Decision**: Surface three error states with user-friendly messages:

| Scenario | Backend Response | Frontend Message |
|----------|-----------------|------------------|
| No sessions in range | `400 NO_DATA_FOR_REPORT` | "No data available for this period — try a different date range." |
| PDF too large | `400 PDF_SIZE_LIMIT_EXCEEDED` | "Report too large — try a smaller date range (max ~90 days recommended)." |
| Unexpected error | `500 PDF_GENERATION_ERROR` | "Report generation failed — please try again." |
| No stats (empty results) | `200` with empty `results` array | Metric cards hidden, "No sessions recorded for this period." |

---

## R-007: Feature File Structure

**New files:**
- `frontend/src/pages/PatientReportsPage.jsx` — main page at `/doctor/patients/:id/reports`
- `frontend/src/hooks/usePatientReport.js` — manages date range, stats state, download state
- `frontend/src/components/reports/DateRangePicker.jsx` — two date inputs + validation
- `frontend/src/components/reports/StatsPreview.jsx` — four metric cards grid

**Modified files:**
- `frontend/src/services/analyticsService.js` — add `fetchPatientStats()` and `downloadPatientReport()`
- `frontend/src/routes/AppRoutes.jsx` — add `/doctor/patients/:id/reports` route
- `frontend/src/pages/PatientDetailPage.jsx` — add "Reports" navigation button
