# Research: Staff (Doctor) Management

**Feature**: 047-doctor-management
**Date**: 2026-06-14
**Phase**: 0 (Outline & Research)

This document records the technical decisions resolving how the staff-management feature integrates with the existing TremoAI codebase. All unknowns from the spec are resolved here.

---

## Decision 1: Endpoint URL placement — honor `/api/admin/doctors/`

**Decision**: Expose the endpoints exactly as the user specified — `GET/POST /api/admin/doctors/` and `PATCH /api/admin/doctors/<id>/` — by adding a new URL include `path('api/admin/', include('authentication.admin_urls'))` to `backend/tremoai_backend/urls.py`. The views live in `backend/authentication/views.py` (per user instruction); the routes live in a new `backend/authentication/admin_urls.py`.

**Rationale**:
- The user was explicit and consistent about both the URL (`/api/admin/doctors/`) and the view location (`authentication/views.py`). Honoring it avoids surprise.
- The managed resource is a *user account* (doctor), which is owned by the `authentication` app — placing the views there is the natural home.
- Adding a URL prefix that includes an existing app's routes is **not** a new Django app and is constitution-compliant.
- A dedicated `admin_urls.py` keeps the public auth routes (`/api/auth/...`) cleanly separated from admin-only management routes.

**Alternatives considered**:
- *Mount under `/api/auth/doctors/`*: rejected — contradicts the user's explicit `/api/admin/` path and conflates public auth with admin management.
- *Reuse the analytics app (as Feature 046 did for admin-stats)*: rejected — doctor accounts are an authentication concern, not analytics; the user named `authentication/views.py`.
- *Create a brand-new `admin` Django app*: rejected — unnecessary; would add an app for two views. Constitution favors minimal structure.

---

## Decision 2: Doctor list query with `patient_count` annotation

**Decision**: Build the roster with a single annotated queryset:
```python
from django.db.models import Count
CustomUser.objects.filter(role='doctor') \
    .annotate(patient_count=Count('patient_assignments', distinct=True)) \
    .order_by('first_name', 'last_name', 'id')
```

**Rationale**:
- `DoctorPatientAssignment.doctor` declares `related_name='patient_assignments'`, so `Count('patient_assignments')` counts each doctor's current assignments in one SQL `GROUP BY` — no N+1 queries.
- `distinct=True` guards against any future join-induced double counting.
- Doctors with zero assignments correctly annotate to `0` (LEFT JOIN + COUNT), satisfying FR-013 / Acceptance US1-2.

**Alternatives considered**:
- *Python-side counting per doctor*: rejected — N+1 queries, fails SC-001 at 200 doctors.
- *Count via `created_patients`*: rejected — `created_by` is the patient's creator, not the assignment relation; the spec defines patient count as assignment-based (Assumptions).

---

## Decision 3: Single `name` field mapped to `first_name` / `last_name`

**Decision**: The API exposes a single `name` field. On **read**, `name` is a `SerializerMethodField` returning `user.get_full_name()`. On **write**, an incoming `name` string is split on the first space — first token → `first_name`, remainder → `last_name` (empty string if only one token).

**Rationale**:
- The form and table specify a single "name" field; the `CustomUser` model stores `first_name`/`last_name` (Django `AbstractUser`).
- `get_full_name()` already concatenates the two with a space — consistent with how the rest of the app shows names.
- First-space split is the least surprising mapping for "FirstName LastName" entry and round-trips cleanly for the common case.

**Alternatives considered**:
- *Add a `name` column to the model*: rejected — requires a migration and duplicates data already in `first_name`/`last_name`.
- *Expose `first_name`/`last_name` separately in the form*: rejected — the user's form spec (6.2) lists a single "name" field.

---

## Decision 4: Account status via Django's built-in `is_active`

**Decision**: "Status" maps to the existing `is_active` boolean on `CustomUser` (inherited from `AbstractUser`). The API field is `is_active` (snake_case). Deactivation = `is_active=False`.

**Rationale**:
- Django's authentication backend and SimpleJWT both refuse to authenticate a user with `is_active=False`, so FR-007 (deactivated doctor cannot sign in) is satisfied for free with no extra logic.
- Deactivation flips a flag — the account row and all `DoctorPatientAssignment` rows are untouched (FR-007, US3-4: data preserved).
- No new field, no migration.

**Alternatives considered**:
- *A custom `status` enum field*: rejected — duplicates `is_active`, needs a migration, and would require custom login-blocking logic.

---

## Decision 5: Password handling — required on create, optional on edit

**Decision**: A single write-only `password` field on the write serializer, run through Django's `validate_password`. Required on `POST` (create); optional and blank-allowed on `PATCH`. On create, use `CustomUser.objects.create_user(...)` (hashes + sets `is_active`). On update, only call `user.set_password(password)` when a non-empty password is supplied; otherwise the existing hash is left unchanged.

**Rationale**:
- Mirrors the existing `RegisterSerializer` (uses `validate_password`, `create_user`) for consistency (Assumptions: reuse platform password standards).
- Optional-on-edit satisfies FR-005 / US2-5 (blank password leaves the password unchanged).
- `set_password` guarantees the password is hashed, never stored in plaintext (constitution: Security-First).

**Alternatives considered**:
- *Require a `password_confirm` like registration*: rejected — admin-driven creation; the form spec (6.2) lists only a single `password` field. Confirmation is a UX nicety, not required by the spec.

---

## Decision 6: Two serializers, two generic views

**Decision**:
- `DoctorListSerializer` (read): `id`, `name`, `email`, `is_active`, `patient_count`, `date_joined`.
- `DoctorWriteSerializer` (create/update): accepts `name`, `email`, `password` (write-only), `is_active`; validates email uniqueness (excluding self on update); implements `create()` and `update()`.
- `AdminDoctorListCreateView(generics.ListCreateAPIView)` — `GET` lists annotated doctors, `POST` creates. Returns the read serializer's representation on create.
- `AdminDoctorDetailView(generics.RetrieveUpdateAPIView)` — `PATCH` updates details and/or toggles `is_active`; queryset filtered to `role='doctor'`.

**Rationale**:
- DRF generics give pagination, 404 handling, and method routing for free.
- Separate read/write serializers keep `patient_count` (read-only, annotated) out of write validation and keep `password` write-only.
- `RetrieveUpdateAPIView` cleanly serves both "edit details" and "toggle status" through the same `PATCH` (FR-005, FR-006) — a status toggle is just `PATCH {"is_active": false}`.

**Alternatives considered**:
- *Single `APIView` with manual method handling* (as `AdminStatsView` does): rejected — generics reduce boilerplate and provide pagination required by the constitution.
- *A `ModelViewSet` + router*: rejected — would also expose `DELETE`/`PUT`, which the spec excludes (no hard delete); explicit generic views bound the surface precisely.

---

## Decision 7: Admin-only access via a new `IsAdmin` permission

**Decision**: Add an `IsAdmin` permission class to `backend/authentication/permissions.py` (the file currently has `IsDoctor`, `IsDoctorOrAdmin`, `IsOwnerOrDoctor` but no admin-only class). Apply `permission_classes = [IsAuthenticated, IsAdmin]` to both views.

**Rationale**:
- FR-008 / SC-005 require every capability to be admin-only; a reusable permission class is the idiomatic DRF enforcement point and returns 403 for authenticated non-admins, 401 for anonymous.
- Centralizing the check (vs. inline `if request.user.role != 'admin'`) is cleaner for two views and matches the existing permission-class pattern in the app.

**Alternatives considered**:
- *Inline role check in each view* (as `AdminStatsView` does): rejected — duplicated across two views; a named permission class is more maintainable and self-documenting.

---

## Decision 8: Email uniqueness enforcement

**Decision**: `DoctorWriteSerializer.validate_email` rejects an email already used by any `CustomUser`, **excluding the instance being edited** (`CustomUser.objects.filter(email=value).exclude(pk=self.instance.pk if self.instance else None).exists()`). Backed by the model's `unique=True` on `email` as a final guard.

**Rationale**:
- FR-004 requires uniqueness across all accounts on both create and edit; excluding self lets an editor save without changing their email (US2 edit flow).
- The serializer check yields a clean `{ "email": ["..."] }` 400 (API standard) instead of an opaque DB IntegrityError.

**Alternatives considered**:
- *Rely solely on the DB unique constraint*: rejected — produces a 500-style IntegrityError rather than a field-level 400 message.

---

## Decision 9: Pagination — use the global default

**Decision**: The list endpoint inherits the project's global `PageNumberPagination` (`PAGE_SIZE = 50`), returning `{ count, next, previous, results }`. The frontend reads `results` and supports the standard pagination controls already used by `PatientTable`.

**Rationale**:
- The constitution mandates pagination for list endpoints; `ListCreateAPIView` applies the global class automatically — zero extra code.
- 50/page comfortably renders a center's doctors; `count` drives the "N doctors" header and pagination is available if a center exceeds one page (SC-001 covers up to 200).

**Alternatives considered**:
- *Return an unpaginated list* (as `AdminStatsView`/overview endpoints do): rejected — violates the pagination standard for list endpoints; the doctor roster is a genuine list.

---

## Decision 10: Frontend structure — service, hook, page, two components, nav

**Decision**:
- `frontend/src/services/doctorService.js` — `listDoctors(params)`, `createDoctor(data)`, `updateDoctor(id, data)` (also used for the toggle).
- `frontend/src/hooks/useDoctors.js` — fetches the roster, exposes `{ doctors, loading, error, refresh }` plus pagination/search state (mirrors `usePatients`).
- `frontend/src/pages/StaffManagementPage.jsx` — admin page at `/admin/doctors`, wraps `AppLayout`, renders the table and hosts the modal.
- `frontend/src/components/admin/DoctorManagementTable.jsx` — the roster table (name, patient count, status) with per-row Edit + deactivate/reactivate actions (6.1, 6.3).
- `frontend/src/components/admin/DoctorFormModal.jsx` — the add/edit modal form (name, email, password, status) (6.2).
- Route registration in `frontend/src/routes/AppRoutes.jsx` (`/admin/doctors`, lazy-loaded, `ProtectedRoute`).
- Admin navigation: give `getMenuItems('admin')` in `frontend/src/utils/roleHelpers.js` a dedicated admin menu (Dashboard → `/admin/dashboard`, Staff → `/admin/doctors`) so the page is reachable from the sidebar.

**Rationale**:
- Mirrors the established service → hook → page → component layering already used for patients, minimizing cognitive load and review risk.
- No generic Modal component exists yet, so `DoctorFormModal` is self-contained (fixed-overlay + panel) — the user named the component explicitly.
- A new `components/admin/` folder groups admin-only UI, parallel to `components/patients/`.
- The admin sidebar currently just mirrors the doctor menu (pointing at `/doctor/*`); adding admin entries makes Staff Management discoverable without breaking existing admin dashboard access.

**Alternatives considered**:
- *Render the form inline on the page instead of a modal*: rejected — the user specified a `DoctorFormModal` component and a modal keeps the roster as the stable backdrop (US2 launch-from-roster flow).
- *Reuse `PatientForm`*: rejected — different fields (email/password/status vs. medical fields) and different submit semantics.

---

## Decision 11: No database migration required

**Decision**: No migration is generated for this feature.

**Rationale**:
- All data comes from existing tables: `CustomUser` (`first_name`, `last_name`, `email`, `is_active`, `role`) and `DoctorPatientAssignment` (for the annotated count). No new columns, models, or constraints are introduced.

**Alternatives considered**:
- *Add a status/audit field*: rejected — out of scope; `is_active` already models the active/inactive lifecycle.

---

## Summary of resolved unknowns

| Topic | Resolution |
|-------|-----------|
| Endpoint URLs | `/api/admin/doctors/` + `/api/admin/doctors/<id>/` via `authentication/admin_urls.py` |
| Patient count | `Count('patient_assignments', distinct=True)` annotation |
| Name field | Single `name`; read = `get_full_name()`, write = split into first/last |
| Status | Built-in `is_active`; deactivation blocks login automatically |
| Password | write-only, `validate_password`; required on POST, optional on PATCH |
| Access control | New `IsAdmin` permission class, applied to both views |
| Email uniqueness | Serializer `validate_email` excluding self + model `unique=True` |
| Pagination | Global `PageNumberPagination` (PAGE_SIZE 50) |
| Frontend | service + hook + page + `DoctorManagementTable` + `DoctorFormModal` + route + admin nav |
| Migration | None required |
