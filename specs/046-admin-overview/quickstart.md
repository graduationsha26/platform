# Quickstart: Admin Global Overview

**Branch**: `046-admin-overview`

Integration scenarios to verify after implementation. Run both dev servers:
- `py manage.py runserver` (in `backend/`)
- `npm run dev` (in `frontend/`)

---

## Scenario 1: Happy path — admin sees correct counts

**Setup**: At least 2 doctors and 3 patients exist in the database.

1. Log in as an admin-role user.
2. Navigate to `/admin/dashboard`.
3. **Verify**: Two summary cards appear — "Total Doctors" and "Total Center Patients".
4. **Verify**: The numbers on the cards match the actual counts in the database.

---

## Scenario 2: Endpoint returns correct JSON

**Setup**: Admin JWT token obtained via login.

```
GET /api/analytics/admin-stats/
Authorization: Bearer <admin_token>
```

**Expected**: HTTP 200

```json
{
  "total_doctors": <N>,
  "total_patients": <M>
}
```

Both values are non-negative integers. N and M match the actual database counts.

---

## Scenario 3: Unauthenticated request → 401

```
GET /api/analytics/admin-stats/
(no Authorization header)
```

**Expected**: HTTP 401

```json
{ "detail": "Authentication credentials were not provided." }
```

---

## Scenario 4: Doctor token → 403

**Setup**: Doctor JWT token from login.

```
GET /api/analytics/admin-stats/
Authorization: Bearer <doctor_token>
```

**Expected**: HTTP 403

```json
{ "error": "Only admins can access the admin stats." }
```

---

## Scenario 5: Zero doctors or patients

**Setup**: Database has no doctors and no patients (or test with counts at 0).

1. Log in as admin and navigate to `/admin/dashboard`.
2. **Verify**: "Total Doctors" card shows **0**, not blank or an error dash.
3. **Verify**: "Total Center Patients" card shows **0**, not blank or an error dash.

---

## Scenario 6: Loading state visible

1. Open browser DevTools → Network tab → set throttling to "Slow 3G".
2. Navigate to `/admin/dashboard`.
3. **Verify**: Both cards show a skeleton/pulse animation before the numbers appear.

---

## Scenario 7: Error state — endpoint unreachable

1. Stop the Django dev server.
2. Navigate to `/admin/dashboard` (frontend still running).
3. **Verify**: Both cards show an error indicator (`—` dash) rather than crashing the page.
4. **Verify**: No JavaScript console error crashes the app.

---

## Scenario 8: Page isolation — admin cannot access doctor stats endpoint

```
GET /api/analytics/dashboard/
Authorization: Bearer <admin_token>
```

**Expected**: HTTP 403 (existing `DashboardStatsView` already enforces `role == 'doctor'`)

---

## Scenario 9: Route protection — unauthenticated user redirected

1. Clear all auth tokens from browser storage.
2. Navigate directly to `/admin/dashboard`.
3. **Verify**: Redirected to `/login`.

---

## Scenario 10: New doctor added → count updates on refresh

1. Log in as admin, view dashboard. Note "Total Doctors" = N.
2. Create a new doctor account via `POST /api/auth/register/` (or admin panel).
3. Refresh `/admin/dashboard`.
4. **Verify**: "Total Doctors" card now shows N+1.
