# Quickstart: Smart Medical Alerts & Dashboard Layout Simplification

**Branch**: `044-smart-alerts-dashboard` | **Date**: 2026-06-14

Start both servers before running any scenario:
```
# Terminal 1
cd backend && python manage.py runserver

# Terminal 2
cd frontend && npm run dev
```

---

## Scenario 1: Critical Alerts count appears correctly for a doctor with qualifying patients

**Setup**: At least one patient in the doctor's cohort has BiometricSessions with `ml_prediction.severity = "severe"` on each of the 5 calendar days ending today.

**Test**:
1. Log in as a doctor.
2. Call `GET /api/analytics/critical-alerts/` with the doctor's JWT token.
3. Verify response: `{ "count": N }` where N ≥ 1.
4. Navigate to the doctor dashboard.
5. Verify the "Alerts" metric card displays the same N value.
6. Verify the card subtitle reads something like "Patients with 5+ consecutive severe days" (not the old "last 24h" text).

**Expected**: Count is non-zero and matches between the API and the UI card.

---

## Scenario 2: Critical Alerts count is 0 when no patients qualify

**Setup**: No patient in the doctor's cohort has severe sessions on all 5 consecutive days (e.g., a patient has 4 consecutive days but not 5, or has no severe sessions at all).

**Test**:
1. Log in as a doctor with such a patient cohort.
2. Navigate to the dashboard.
3. Verify the Alerts metric card shows "0".
4. Verify no error state or blank value is displayed.

**Expected**: Card shows exactly "0" without error UI.

---

## Scenario 3: 7-day tremor trend chart is absent from the dashboard

**Test**:
1. Log in as any doctor.
2. Navigate to `/doctor/dashboard`.
3. Inspect the page — verify no chart titled "7-Day Tremor Trend" is rendered.
4. Open browser DevTools → Network tab, filter by `/analytics/dashboard/`.
5. Verify the response does NOT contain a `tremor_trend` field.
6. Verify the response does NOT contain an `alerts_count` field.
7. Verify the response still contains `total_patients` and `active_devices`.

**Expected**: Dashboard renders without the chart. API response has only `total_patients` and `active_devices`.

---

## Scenario 4: Endpoint rejects unauthenticated requests

**Test**:
```bash
curl -X GET http://localhost:8000/api/analytics/critical-alerts/
```

**Expected**: `401 Unauthorized` with `{ "error": "..." }`.

---

## Scenario 5: Endpoint rejects non-doctor users

**Test**:
1. Obtain a JWT token for an admin user.
2. Call `GET /api/analytics/critical-alerts/` with the admin token.

**Expected**: `403 Forbidden` with `{ "error": "Only doctors can access critical alerts." }`.

---

## Scenario 6: Boundary — patient with exactly 4 consecutive severe days is NOT counted

**Setup**: One patient has severe sessions on days T-3, T-2, T-1, T (4 days) but NOT on T-4. No other qualifying patient exists.

**Test**:
1. Call `GET /api/analytics/critical-alerts/`.
2. Verify response: `{ "count": 0 }`.

**Expected**: Count is 0 — the 4-day patient does not meet the 5-day threshold.
