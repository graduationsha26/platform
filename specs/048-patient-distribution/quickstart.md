# Quickstart: Patient Distribution (Admin)

**Feature**: 048-patient-distribution
**Date**: 2026-06-14
**Phase**: 1 (Design)

Manual integration scenarios validating the spec's user stories end-to-end. Run after `/speckit.implement`.

## Prerequisites

1. Backend running: from `backend/` → `py manage.py runserver`
2. Frontend running: from `frontend/` → `npm run dev`
3. Test users seeded (`py manage.py shell < create_test_users.py` or equivalent):
   - **Admin**: `admin@test.com` / `admin123`
   - **Doctor**: `doctor@test.com` / `doctor123` (Dr. John Smith, has assigned patients)
4. Optionally create a 2nd doctor via the Staff Management page (feature 047) so reassignment has two targets.

Log in as the **admin** and open the sidebar → **Patients** (`/admin/patients`).

---

## US1 — Center-wide roster

| # | Scenario | Steps | Expected |
|---|----------|-------|----------|
| 1 | Roster renders all patients | Open `/admin/patients` | Table lists every center patient (not just one doctor's), each with name + assigned doctor. Total count shown. |
| 2 | Assigned doctor column | Inspect a patient assigned to Dr. John Smith | Row shows "Dr. John Smith" in the doctor column. |
| 3 | Unassigned indicator | Register a patient without a doctor (US2 #7), return to roster | That patient shows an "Unassigned" badge, not a doctor name. |
| 4 | Pagination | If >50 patients exist | Pagination control appears; navigating pages keeps the count correct. |
| 5 | Empty state | (Fresh DB) with no patients | Roster shows a clear empty state, not an error. |

---

## US2 — Register patient

| # | Scenario | Steps | Expected |
|---|----------|-------|----------|
| 6 | Doctor dropdown lists active doctors | Click **Register Patient**, open the doctor dropdown | Dropdown lists active doctor accounts (deactivated doctors absent). |
| 7 | Register unassigned | Fill name + DOB, leave doctor blank, submit | Patient created; appears on roster as **Unassigned**. |
| 8 | Register with doctor | Fill name + DOB, pick a doctor, submit | Patient created and assigned; appears on roster under that doctor; also visible in that doctor's own patient list. |
| 9 | Missing required field | Submit with empty name | Field-level validation error; no patient created. |
| 10 | Future date of birth | Pick a DOB in the future, submit | Validation error ("Date of birth cannot be in the future."); no patient created. |

---

## US3 — Assign / reassign

| # | Scenario | Steps | Expected |
|---|----------|-------|----------|
| 11 | Reassign A→B | On a patient assigned to Doctor A, click **Reassign**, pick Doctor B, confirm | Roster now shows Doctor B; the patient leaves Doctor A's own patient list and joins Doctor B's. |
| 12 | Assign an unassigned patient | On an Unassigned patient, click **Reassign/Assign**, pick a doctor | Patient now shows that doctor; no duplicate row. |
| 13 | Reassign to same doctor | Reassign a patient to the doctor they already have | Success, no error, still exactly one assignment. |
| 14 | Patient data preserved | After any reassignment, open the patient detail | Name, DOB, notes, and history unchanged — only the doctor changed. |

---

## Authorization & errors

| # | Scenario | Steps | Expected |
|---|----------|-------|----------|
| 15 | Doctor blocked (UI) | Log in as `doctor@test.com`; there is no Patients item in the doctor menu; visit `/admin/patients` directly | Access denied / redirected; no center-wide roster shown. |
| 16 | Doctor blocked (API) | `GET /api/admin/patients/` with a doctor JWT | `403` with admin-only message. |
| 17 | Anonymous blocked (API) | `GET /api/admin/patients/` with no token | `401`. |
| 18 | Invalid doctor on assign | `POST /api/admin/patients/<id>/assign/` with a `doctor_id` that is an admin or nonexistent | `400` with a clear error; existing assignment unchanged. |
| 19 | Reassign nonexistent patient | `POST /api/admin/patients/999999/assign/` | `404`. |
| 20 | Backend unreachable | Stop backend, open `/admin/patients` | Roster shows a load-error state, not a blank/crash. |

---

## API-level smoke (read-only, safe against remote DB)

Using DRF `APIRequestFactory` (no DB mutation) or `curl` with an admin JWT:

```text
GET /api/admin/patients/        anon   → 401
GET /api/admin/patients/        doctor → 403
GET /api/admin/patients/        admin  → 200, results[] each with assigned_doctor (object|null)
```

> Avoid running create/assign smoke tests against the **remote Supabase** DB unless you intend to persist test rows. Prefer the browser walkthrough (scenarios 7–14) for write paths, or a disposable local fixture.

---

## Acceptance summary

All US1–US3 acceptance scenarios and edge cases from `spec.md` are covered above:
roster completeness (1–2), Unassigned (3, 7), pagination/empty (4–5), dropdown (6),
registration validation (9–10), reassignment replace + idempotency + preservation (11–14),
and admin-only access across UI + API (15–20).
