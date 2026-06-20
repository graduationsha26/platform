# Research: Patient Distribution (Admin)

**Feature**: 048-patient-distribution
**Date**: 2026-06-14
**Phase**: 0 (Outline & Research)

This document records the technical decisions resolving how the spec's WHAT becomes a concrete HOW, grounded in the existing TremoAI codebase.

---

## Decision 1: Reuse existing models — no migration

**Decision**: Use the existing `patients.Patient` and `patients.DoctorPatientAssignment` models unchanged. No new model, no schema change, no migration.

**Rationale**:
- `Patient` already has every intake field needed: `full_name`, `date_of_birth`, `contact_phone`, `contact_email`, `medical_notes`, plus `created_by` (FK to `CustomUser`, `PROTECT`). Admin registration just sets `created_by = request.user` (the admin) — the model places no role restriction on `created_by`.
- `DoctorPatientAssignment` already links doctor↔patient with `assigned_at` and `assigned_by`, and `unique_together=[['doctor','patient']]` already prevents duplicate doctor-patient pairs.
- The roster's "assigned doctor" column derives entirely from existing relations (`patient.doctor_assignments → doctor`).

**Alternatives considered**:
- *Add an `assigned_doctor` FK directly on `Patient`*: rejected — duplicates the existing assignment relation, requires a migration and data backfill, and diverges from how the doctor-side patient list already computes assignment.

---

## Decision 2: Honor `/api/admin/patients/` URLs without a new Django app

**Decision**: Keep the views in `patients/views.py` (per user instruction) and create `patients/admin_urls.py` with:
- `''` → `AdminPatientListCreateView` (GET list, POST register), name `admin-patients`
- `'<int:pk>/assign/'` → `AdminPatientAssignView` (POST), name `admin-patient-assign`

Mount it in `tremoai_backend/urls.py` as `path('api/admin/patients/', include('patients.admin_urls'))`, placed **before** the existing `path('api/admin/', include('authentication.admin_urls'))` (feature 047).

**Rationale**:
- Django resolves URL patterns top-to-bottom. The existing `api/admin/` include would otherwise swallow `/api/admin/patients/`, strip it to `patients/`, and 404 inside `authentication.admin_urls`. Registering the more specific `api/admin/patients/` prefix first makes it match and dispatch into `patients.admin_urls`.
- Keeps patient logic inside the `patients` app (clean app boundaries) while still serving the exact `/api/admin/patients/` URLs the user specified.

**Alternatives considered**:
- *Nest patient routes inside `authentication/admin_urls.py`*: rejected — couples the `patients` domain to the `authentication` app.
- *Reuse the existing `PatientViewSet` at `/api/patients/`*: rejected — the user explicitly specified the `/api/admin/patients/` URL surface and admin-only semantics distinct from the doctor-scoped viewset.

---

## Decision 3: Admin-initiated assignment sets `assigned_by = None`

**Decision**: When the admin creates or reassigns an assignment, create the `DoctorPatientAssignment` with `assigned_by=None`.

**Rationale**:
- `DoctorPatientAssignment.clean()` raises `ValidationError` if `assigned_by` is set and its role is not `doctor`. The admin is **not** a doctor, so passing `assigned_by=request.user` (as the existing doctor-side `DoctorPatientAssignmentSerializer.create()` does) would fail validation.
- `assigned_by` is `null=True, blank=True, on_delete=SET_NULL`, so `None` is valid and `clean()` skips the role check when it is falsy.
- The `doctor` field's role is still validated by `clean()` (must be `doctor`), preserving data integrity for the meaningful relation.

**Alternatives considered**:
- *Set `assigned_by` to the assigned doctor*: rejected — misrepresents who made the assignment (the admin did), and is semantically wrong.
- *Relax/modify the model's `clean()`*: rejected — changing shared model validation for one feature risks regressions in the doctor-side flow; `assigned_by=None` is the minimal, correct choice.

---

## Decision 4: Reassignment uses replace semantics in a transaction

**Decision**: `POST /api/admin/patients/<id>/assign/` deletes all existing `DoctorPatientAssignment` rows for the patient, then creates one new assignment to the chosen doctor — all inside `transaction.atomic()`. Reassigning to the doctor the patient already has is a no-op success (delete + recreate yields the same single assignment).

**Rationale**:
- The spec treats a patient as having **at most one effective doctor** (Assumptions: "One effective doctor per patient"). Replace semantics guarantee FR-009 ("assigned to exactly one doctor — the newly chosen one — and no longer to any previous doctor").
- `transaction.atomic()` satisfies the concurrent-reassignment edge case: the patient never ends up assigned to two doctors.
- Distinct from the existing doctor-side `assign-doctor` action, which *adds* an assignment and *rejects* duplicates — that's additive M2M semantics, not the single-doctor distribution model this feature needs.

**Alternatives considered**:
- *Reuse the additive `assign_doctor` action*: rejected — it errors on an existing pairing and never removes the old doctor, so it cannot reassign.
- *Keep assignment history (soft replace)*: rejected as out of scope; the spec explicitly models a single current doctor and "No hard delete" refers to patients/doctors, not assignment rows.

---

## Decision 5: Roster "assigned doctor" = most-recent single assignment

**Decision**: The roster serializer exposes a single `assigned_doctor` object `{ id, name, email }` or `null`. It is computed from the patient's `doctor_assignments` ordered by `-assigned_at` (the model default), taking the first. Querysets use `prefetch_related('doctor_assignments__doctor')` to avoid N+1 queries.

**Rationale**:
- With replace semantics a patient normally has 0 or 1 assignment, but defaulting to "most recent" is robust if legacy data holds more than one (edge case: "Patient with multiple historical assignments" — show one row, one doctor, never duplicate the patient).
- `name` is the doctor's `get_full_name()`, matching the display convention used by feature 047.

**Alternatives considered**:
- *Return a list of assigned doctors (like `PatientDetailSerializer.assigned_doctors`)*: rejected — the admin roster is a flat one-row-per-patient table; a list complicates the "Unassigned" indicator and could imply multiple doctors.

---

## Decision 6: Two views, three serializers (generics + APIView)

**Decision**:
- `AdminPatientListCreateView(generics.ListCreateAPIView)` — `get_serializer_class()` returns `AdminPatientRegisterSerializer` for POST, `AdminPatientListSerializer` for GET. `permission_classes = [IsAuthenticated, IsAdmin]`. Queryset filters all patients, prefetches assignments, orders by `full_name`. Supports `?search=` over `full_name`/`contact_email`.
- `AdminPatientAssignView(APIView)` — `post(request, pk)` validates `AdminPatientAssignSerializer`, performs the transactional replace, returns the updated patient via `AdminPatientListSerializer`. `permission_classes = [IsAuthenticated, IsAdmin]`.
- `AdminPatientListSerializer` (read): `id, full_name, date_of_birth, contact_email, created_at, assigned_doctor`.
- `AdminPatientRegisterSerializer` (write): `full_name, date_of_birth, contact_phone, contact_email, medical_notes, doctor_id` (optional, write-only). `validate_date_of_birth` (not future, mirrors existing). `validate_doctor_id` (exists, role `doctor`, active). `create()` makes the patient (`created_by=admin`) and, if `doctor_id` given, the assignment (`assigned_by=None`) in a transaction. `to_representation` delegates to `AdminPatientListSerializer`.
- `AdminPatientAssignSerializer`: `doctor_id` (required). Same doctor validation.

**Rationale**: Matches the DRF generics + per-method serializer pattern established by feature 047's `AdminDoctorListCreateView`. `APIView` for the custom `/assign/` action keeps the transactional replace explicit and readable.

**Alternatives considered**:
- *Single ViewSet with a `@action`*: rejected — the user named `patients/views.py` and distinct URLs; explicit generic views read more clearly and avoid router coupling at `/api/admin/patients/`.

---

## Decision 7: Reuse `IsAdmin` permission (feature 047)

**Decision**: Use the existing `authentication.permissions.IsAdmin` for all three capabilities. No new permission class.

**Rationale**: `IsAdmin` was added in feature 047 and already enforces `is_authenticated and role == 'admin'`, returning 403 for doctors and 401 for anonymous — exactly FR-003. DRY.

**Alternatives considered**: *New permission* — rejected, redundant.

---

## Decision 8: Doctor dropdown reuses feature 047's `doctorService`

**Decision**: The `RegisterPatientForm` and `AssignDoctorModal` dropdowns are populated by calling the existing `doctorService.listDoctors()` (feature 047 `GET /api/admin/doctors/`), filtering the results to `is_active === true` on the frontend.

**Rationale**:
- That endpoint already returns admin-visible doctors with `id`, `name`, `is_active`. Filtering to active satisfies FR-005 / the "Doctor dropdown contents" assumption (active doctors only) without a new endpoint.
- Avoids duplicating a doctor-listing endpoint.

**Alternatives considered**:
- *New lightweight `GET /api/admin/doctors/options/`*: rejected — unnecessary; the existing list endpoint is sufficient at this scale (tens of doctors; page_size 50).

---

## Decision 9: Pagination at 50/page (`AdminPatientPagination`)

**Decision**: Add `AdminPatientPagination(PageNumberPagination)` with `page_size=50, page_size_query_param='page_size', max_page_size=100` in `patients/pagination.py`, used by `AdminPatientListCreateView`. The frontend hook uses `PAGE_SIZE=50` to compute `totalPages`.

**Rationale**: Mirrors feature 047's roster page size (50), keeping admin roster UX consistent. Response shape is the standard DRF `{ count, next, previous, results }`, which `useAdminPatients` consumes exactly like `useDoctors`. (The doctor-scoped `PatientPagination` stays at 20 for the doctor views — unchanged.)

**Alternatives considered**: *Reuse `PatientPagination` (20)*: rejected — inconsistent with the sibling admin roster; *no pagination*: rejected — violates FR-012.

---

## Decision 10: Frontend structure mirrors feature 047

**Decision**: Layered `adminPatientService.js` → `useAdminPatients.js` → `PatientDistributionPage.jsx` → (`AdminPatientTable`, `RegisterPatientForm`, `AssignDoctorModal`). Add a protected `/admin/patients` route and a "Patients" item in the admin sidebar menu (`roleHelpers.js`), using a `lucide-react` icon (e.g. `Users`).

**Rationale**: Consistency with the established Staff Management feature (047) — same hook shape (`refresh()` after mutations, debounced search, pagination), same `components/admin/` location, same `ProtectedRoute` wrapping.

**Alternatives considered**: *Reuse the doctor-side patient pages* — rejected; those are doctor-scoped and lack the center-wide/assignment semantics.

---

## Decision 11: Registration without a doctor is allowed (Unassigned)

**Decision**: `doctor_id` is optional on `POST /api/admin/patients/`. If omitted/empty, the patient is created with no assignment and shows as "Unassigned" on the roster; the admin can assign later via `/assign/`.

**Rationale**: Implements the spec's "Registration without a doctor" assumption and the Unassigned roster indicator (FR-002). The form may still encourage selecting a doctor, but the backend does not force it.

**Alternatives considered**: *Require a doctor at registration*: documented in the spec as a possible stricter rule; not chosen as the default because it removes the legitimate "intake now, assign later" workflow and conflicts with the Unassigned indicator requirement.
