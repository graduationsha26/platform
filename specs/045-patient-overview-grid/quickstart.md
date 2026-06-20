# Quickstart: Patient Overview Grid

**Branch**: `045-patient-overview-grid` | **Date**: 2026-06-14

Integration scenarios for verifying the full feature end-to-end after implementation.

---

## Scenario 1 — Doctor with patients (primary happy path)

**Setup**: Doctor user with 3 assigned patients:
- Patient A: avatar on file, device last_seen 30 seconds ago
- Patient B: no avatar, device last_seen 5 minutes ago
- Patient C: no avatar, no device assigned

**Action**: Authenticate as doctor → load `/doctor/dashboard`.

**Expected**:
- `GET /api/patients/overview/` returns `{ "count": 3, "results": [...] }` with HTTP 200
- Patient A's card: shows avatar photo, "Online" badge
- Patient B's card: shows "SA" initials placeholder, "Offline" badge
- Patient C's card: shows "PC" initials placeholder, "Offline" badge
- All 3 cards appear below the 3 summary cards in the dashboard

---

## Scenario 2 — Clicking "View Profile" navigates correctly

**Setup**: Doctor is on the dashboard, patient grid is visible.

**Action**: Click "View Profile" on Patient A's card (id=5).

**Expected**: App navigates to `/doctor/patients/5` (PatientDetailPage). No 404, no error.

---

## Scenario 3 — Clicking "Live Monitor" navigates correctly

**Setup**: Doctor is on the dashboard, patient grid is visible.

**Action**: Click "Live Monitor" on Patient A's card (id=5).

**Expected**: App navigates to `/doctor/patients/5/monitor` (LiveTremorPage). No 404, no error.

---

## Scenario 4 — Doctor with no assigned patients (empty state)

**Setup**: Doctor user with zero assigned patients.

**Action**: Load `/doctor/dashboard`.

**Expected**:
- `GET /api/patients/overview/` returns `{ "count": 0, "results": [] }` with HTTP 200
- Grid area shows an empty-state message (e.g., "No patients assigned yet")
- No blank space, no JavaScript error in console

---

## Scenario 5 — Unauthenticated request returns 401

**Setup**: No Authorization header.

**Action**: `GET /api/patients/overview/` without a token.

**Expected**: HTTP 401 with `{ "error": "Authentication credentials were not provided." }` (or DRF default 401 body).

---

## Scenario 6 — Admin user returns 403

**Setup**: Admin user (role='admin') authenticated with valid JWT.

**Action**: `GET /api/patients/overview/` with admin token.

**Expected**: HTTP 403 with `{ "error": "Only doctors can access the patients overview." }`.

---

## Scenario 7 — Avatar URL empty → initials rendered

**Setup**: Patient named "Leila Bouzid Hassan" has `avatar_url = ""`.

**Action**: Load dashboard.

**Expected**: Card shows "LB" as initials (first letter of first two words). No broken image icon.

---

## Scenario 8 — Single-word patient name → single initial

**Setup**: Patient named "Amina" (one word) has `avatar_url = ""`.

**Action**: Load dashboard.

**Expected**: Card shows "A" as the initials fallback. No crash, no empty circle.

---

## Scenario 9 — Doctor isolation (cannot see other doctors' patients)

**Setup**: Doctor A has patients P1, P2. Doctor B has patients P3, P4. Both logged in separately.

**Action**: Doctor A calls `GET /api/patients/overview/`.

**Expected**: Response contains only P1 and P2 (count=2). P3 and P4 are NOT returned.

---

## Scenario 10 — Grid section error state does not break dashboard

**Setup**: Backend is temporarily unreachable for the `/api/patients/overview/` endpoint only.

**Action**: Load `/doctor/dashboard`.

**Expected**: The 3 summary cards (Patients, Active Devices, Critical Alerts) still load and display their values. The grid section shows a non-blocking error message. No full-page crash.
