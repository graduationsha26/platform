# Quickstart & Integration Scenarios: Reports Page & PDF Download (Feature 035)

## Prerequisites

- Backend running: `python manage.py runserver` (or `daphne`)
- Frontend running: `npm run dev`
- At least one patient with recorded `BiometricSession` data
- Doctor account assigned to that patient

---

## Scenario 1: Happy Path — Stats Preview + PDF Download

**Goal**: Verify the complete flow: open reports page, see stats, download PDF.

### Steps

1. Log in as a doctor at `http://localhost:5173/login`
2. Navigate to Patients → select a patient with session history
3. On the patient detail page, click **"Reports"** button (next to "Live Monitor" and "Edit")
4. URL changes to `/doctor/patients/{id}/reports`

### Expected: Page Loads with Default Range (Last 30 Days)

- Date range picker shows start = today minus 29 days, end = today
- Stats preview loads automatically:
  - **Avg Amplitude**: e.g. `0.423`
  - **Max Amplitude**: e.g. `0.681` (highest daily avg in the period)
  - **Dominant Frequency**: e.g. `4.8 Hz`
  - **Tremor Reduction**: e.g. `+38.5%` (green) or `−12.1%` (red)
- "Download PDF" button is enabled

### Change the Date Range

5. Change start date to 60 days ago
6. Click **"Apply"** (or dates are applied on change)

### Expected: Stats Update

- Loading spinner briefly appears on the metric cards
- Values update to reflect the new period

### Download PDF

7. Click **"Download PDF"**

### Expected: PDF Downloads

- Button shows "Generating..." with spinner
- Within ~5 seconds: browser prompts to save `report_patient{id}_{startDate}_{endDate}.pdf`
- Button returns to "Download PDF"
- PDF file opens correctly, contains patient name, report period, all four metrics, and trend charts

---

## Scenario 2: No Data for Selected Range

**Goal**: Verify empty-state handling.

### Steps

1. Open Reports page for a patient with sessions
2. Set date range to a period with no data (e.g., one year ago before the patient was created)
3. Click **"Apply"**

### Expected

- Metric cards hide (not shown)
- "No sessions recorded for this period. Try adjusting the date range." message displays
- "Download PDF" button is disabled
- Clicking "Download PDF" while disabled shows a tooltip: "No data available"

---

## Scenario 3: Invalid Date Range (Client-Side Validation)

**Goal**: Verify inline validation prevents bad requests.

### Steps

1. Open Reports page
2. Set start date to **tomorrow** (future date)

### Expected

- Date picker's `max` attribute prevents selecting tomorrow → cannot select
- (Alternatively) if somehow selected, validation error shown immediately

3. Set end date to a date **before** the start date

### Expected

- Inline error below the date range: "End date must be on or after start date."
- "Apply" button disabled while error is active
- No API request is sent

---

## Scenario 4: PDF Too Large

**Goal**: Verify user-friendly error when PDF exceeds 5MB limit.

### Steps

1. Open Reports page for a patient with many sessions
2. Set date range to 365 days
3. Click "Download PDF"

### Expected

- If backend returns `PDF_SIZE_LIMIT_EXCEEDED` error:
  - Error message appears: "Report too large — try a smaller date range (max ~90 days recommended)."
  - No broken file is downloaded
  - Button returns to enabled state

---

## Scenario 5: No Baseline (Tremor Reduction Unavailable)

**Goal**: Verify graceful display when tremor reduction % cannot be computed.

### Steps

1. Open Reports page for a patient with only one session in their entire history

### Expected

- Avg Amplitude, Max Amplitude, Dominant Frequency display numeric values
- Tremor Reduction card shows: "—" or "Unavailable" with a note "Insufficient baseline data"

---

## Scenario 6: Unauthorized Access

**Goal**: Verify access control.

### Steps

1. Log in as Doctor A (not assigned to Patient 42)
2. Manually navigate to `/doctor/patients/42/reports`

### Expected

- API call returns 403
- Page shows error: "You do not have access to this patient's reports."
- "Back to patients" link visible

---

## Development Notes

### Manually Seeding Stats Data (if no sessions exist)

To create a BiometricSession for testing via the Django shell:
```python
# In backend/ directory:
python manage.py shell

from biometrics.models import BiometricSession
from django.utils import timezone
import datetime

BiometricSession.objects.create(
    patient_id=1,
    session_start=timezone.now() - datetime.timedelta(days=5),
    session_end=timezone.now() - datetime.timedelta(days=5) + datetime.timedelta(hours=1),
    dominant_amplitude=0.45,
    dominant_frequency=4.8,
    sensor_data={"tremor_intensity": [0.4, 0.5, 0.45]}
)
```

### Checking the Stats API Directly

```bash
# Get JWT token from browser localStorage, then:
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/analytics/stats/?patient_id=1&start_date=2026-01-01&end_date=2026-02-21&group_by=day&page_size=365"
```

### Testing PDF Download via curl

```bash
curl -X POST http://localhost:8000/api/analytics/reports/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"patient_id": 1, "start_date": "2026-01-01", "end_date": "2026-02-21"}' \
  -o report.pdf

# Open the file
open report.pdf   # macOS
xdg-open report.pdf  # Linux
```
