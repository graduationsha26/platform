# Quickstart: Update Patient API Permissions (E-1.4)

**Branch**: `015-patient-permissions`
**Date**: 2026-02-18

This document describes integration scenarios to validate the permission changes after implementation.

---

## Scenario 1: Admin User — List All Patients

**Goal**: Verify admin can see all patients, not just their own.

```
POST /api/auth/login/
Body: { "email": "admin@example.com", "password": "..." }
→ 200 OK, token with role: "admin"

GET /api/patients/
Headers: Authorization: Bearer <admin_token>
→ 200 OK, results contain ALL patients in the system (multiple doctors' patients visible)
```

**Expected**: Full patient list returned, not filtered by creator.

---

## Scenario 2: Admin User — Create, Update, Delete Any Patient

**Goal**: Verify admin has full CRUD on any patient.

```
POST /api/patients/
Headers: Authorization: Bearer <admin_token>
Body: { "full_name": "Test Patient", "date_of_birth": "1980-01-01" }
→ 201 Created

PUT /api/patients/{id}/
Headers: Authorization: Bearer <admin_token>
Body: { "full_name": "Updated Name", "date_of_birth": "1980-01-01" }
→ 200 OK

DELETE /api/patients/{id}/
Headers: Authorization: Bearer <admin_token>
→ 204 No Content
```

---

## Scenario 3: Doctor — Scoped Access Unchanged

**Goal**: Verify doctor access is not widened after the admin permission addition.

```
POST /api/auth/login/
Body: { "email": "doctor@example.com", "password": "..." }
→ 200 OK, token with role: "doctor"

GET /api/patients/
Headers: Authorization: Bearer <doctor_token>
→ 200 OK, results contain ONLY this doctor's patients
   (patients created by other doctors are NOT present)

GET /api/patients/{other_doctor_patient_id}/
Headers: Authorization: Bearer <doctor_token>
→ 404 Not Found (patient not in this doctor's queryset)
```

---

## Scenario 4: Unauthenticated Request — Rejected

**Goal**: Verify no token → 401.

```
GET /api/patients/
(no Authorization header)
→ 401 Unauthorized
{ "detail": "Authentication credentials were not provided." }
```

---

## Scenario 5: Wrong Role — Rejected (Future-proof)

**Goal**: Verify a user with an unrecognized or non-authorized role gets 403.

```
(If a user with role other than 'doctor'/'admin' could be created)
GET /api/patients/
Headers: Authorization: Bearer <other_role_token>
→ 403 Forbidden
```

---

## Scenario 6: Dead Code Verification — `IsPatient` Removed

**Goal**: Confirm the `IsPatient` class no longer exists in the codebase.

```
grep -r "IsPatient" backend/
→ (no output) — class fully removed
```

---

## Validation Checklist

- [ ] Admin token → `GET /api/patients/` returns all patients
- [ ] Admin token → `POST /api/patients/` creates a new patient
- [ ] Admin token → `DELETE /api/patients/{id}/` deletes any patient
- [ ] Doctor token → `GET /api/patients/` returns only their patients
- [ ] Doctor token → `GET /api/patients/{other_doctor_patient_id}/` returns 404
- [ ] No token → `GET /api/patients/` returns 401
- [ ] `python manage.py check` → 0 errors
- [ ] `grep -r "IsPatient" backend/` → no results
