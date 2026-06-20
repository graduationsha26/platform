# Quickstart & Integration Scenarios: Staff (Doctor) Management

**Feature**: 047-doctor-management
**Date**: 2026-06-14

How to run the feature locally and the integration scenarios that validate it end-to-end. Each scenario maps to a functional requirement / acceptance scenario in `spec.md`.

---

## Running locally

**Backend** (from `backend/`):
```powershell
py manage.py runserver
```
No migration is required for this feature (no schema changes).

**Frontend** (from `frontend/`):
```powershell
npm run dev
```

**Prerequisites**: at least one admin account and one doctor account exist (use `backend/create_test_users.py` or the Django admin). Log in as the admin in the browser to obtain a JWT.

---

## API smoke test (with an admin JWT)

```powershell
# List doctors with patient counts
curl http://localhost:8000/api/admin/doctors/ -H "Authorization: Bearer <ADMIN_ACCESS>"

# Create a doctor
curl -X POST http://localhost:8000/api/admin/doctors/ `
  -H "Authorization: Bearer <ADMIN_ACCESS>" -H "Content-Type: application/json" `
  -d '{"name":"Jane Smith","email":"jane.smith@example.com","password":"S0me-Strong-Pass","is_active":true}'

# Edit a doctor (id 12)
curl -X PATCH http://localhost:8000/api/admin/doctors/12/ `
  -H "Authorization: Bearer <ADMIN_ACCESS>" -H "Content-Type: application/json" `
  -d '{"name":"Jane A. Smith"}'

# Deactivate (toggle) a doctor
curl -X PATCH http://localhost:8000/api/admin/doctors/12/ `
  -H "Authorization: Bearer <ADMIN_ACCESS>" -H "Content-Type: application/json" `
  -d '{"is_active":false}'
```

---

## Integration scenarios

### Scenario 1 — Admin views the roster (US1, FR-001, FR-002)
1. Log in as admin, open `/admin/doctors`.
2. **Expect**: a table with one row per doctor showing **name**, **assigned patient count**, and **status** (Active/Inactive). The header shows the total doctor count.

### Scenario 2 — Zero-assignment doctor shows count 0 (US1-2, FR-013)
1. Ensure a doctor exists with no patient assignments.
2. **Expect**: that doctor's patient count cell reads `0`, not blank.

### Scenario 3 — Inactive doctors are distinguishable (US1-3)
1. Have at least one deactivated doctor.
2. **Expect**: their status renders as "Inactive" with a visually distinct badge from active rows.

### Scenario 4 — Empty state (US1-5, FR-012)
1. View the page in a center with no doctor accounts.
2. **Expect**: an empty-state message, not a bare empty table.

### Scenario 5 — Create a doctor (US2-1, FR-003)
1. Click **Add Doctor**, enter a unique email, name, password, status Active, submit.
2. **Expect**: 201; the new doctor appears in the roster with patient count `0`, without a manual full-page reload (FR-011).

### Scenario 6 — Edit pre-fills, password optional (US2-2, US2-5, FR-005)
1. Click **Edit** on a doctor.
2. **Expect**: form pre-filled with current name, email, status; password blank.
3. Change the name, leave password blank, save.
4. **Expect**: name updates in the row; the doctor can still sign in with the original password.

### Scenario 7 — Duplicate email rejected (US2-3, FR-004)
1. Add (or edit) a doctor using an email already owned by another account.
2. **Expect**: 400 with a clear "email already in use" message; no account created/changed.

### Scenario 8 — Missing required field rejected (US2-4, FR-010)
1. Submit the Add form with an empty name (or empty email, or empty password).
2. **Expect**: field-level validation messages; nothing saved.

### Scenario 9 — Deactivate / reactivate toggle (US3-1, US3-2, FR-006)
1. On an active doctor's row, trigger **Deactivate**.
2. **Expect**: status flips to Inactive, the action becomes **Reactivate**, no full-page reload.
3. Trigger **Reactivate**.
4. **Expect**: status returns to Active.

### Scenario 10 — Deactivated doctor cannot sign in, data preserved (US3-3, US3-4, FR-007)
1. Deactivate a doctor who has assigned patients.
2. Attempt to log in as that doctor.
3. **Expect**: login refused.
4. Reactivate and confirm their patient assignments are still intact.

### Scenario 11 — Non-admin denied (US1-4, FR-008, SC-005)
1. Call `GET /api/admin/doctors/` with a **doctor** token → **Expect** 403.
2. Call `POST` / `PATCH` with a doctor token → **Expect** 403.
3. Call any endpoint with **no** token → **Expect** 401.

### Scenario 12 — Route protection (frontend)
1. As an unauthenticated user, navigate directly to `/admin/doctors`.
2. **Expect**: redirected to `/login`.

### Scenario 13 — Backend unreachable (FR-012)
1. Stop the backend, reload `/admin/doctors`.
2. **Expect**: an error state is shown; the page does not crash.

---

## Done criteria
All 13 scenarios pass, the three endpoints behave per `contracts/admin-doctors.yaml`, and the sidebar (admin role) shows a **Staff** link to `/admin/doctors`.
