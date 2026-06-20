---
description: "Task list for Patient Distribution (Admin)"
---

# Tasks: Patient Distribution (Admin)

**Input**: Design documents from `/specs/048-patient-distribution/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/admin-patients.yaml, quickstart.md

**Tests**: Not requested in the spec — no automated test tasks generated. Verification is via `py manage.py check`, a read-only API smoke check, and the manual `quickstart.md` walkthrough.

**Organization**: Tasks are grouped by user story (US1 roster, US2 register, US3 assign/reassign) so each can be implemented and demoed independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1 / US2 / US3
- Exact file paths included.

## Path Conventions

- **Backend (Django)**: `backend/patients/`, `backend/tremoai_backend/`
- **Frontend (React)**: `frontend/src/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm the reuse-only baseline. No new dependencies, no migration.

- [X] T001 Verify on branch `048-patient-distribution` and confirm no model/schema change is needed — `backend/patients/models.py` (`Patient`, `DoctorPatientAssignment`) and `authentication.permissions.IsAdmin` are reused as-is (per research.md decisions 1, 3, 7). No migration will be created.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared routing, pagination, frontend service, and navigation that every story builds on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T002 [P] Add `AdminPatientPagination(PageNumberPagination)` (page_size=50, page_size_query_param='page_size', max_page_size=100) in `backend/patients/pagination.py` (research.md decision 9).
- [X] T003 [P] Create `frontend/src/services/adminPatientService.js` exporting `listAdminPatients(params)` (GET `/admin/patients/`), `registerPatient(data)` (POST `/admin/patients/`), and `assignPatient(id, doctorId)` (POST `/admin/patients/${id}/assign/`) — all returning `response.data`, using the shared `api` Axios instance (mirror `doctorService.js`).
- [X] T004 Create `backend/patients/admin_urls.py` with an `urlpatterns` list (initially empty, routes added per story) and register it in `backend/tremoai_backend/urls.py` as `path('api/admin/patients/', include('patients.admin_urls'))` placed **immediately before** the existing `path('api/admin/', include('authentication.admin_urls'))` line (research.md decision 2).
- [X] T005 [P] Add a "Patients" item (icon `Users` from `lucide-react`, path `/admin/patients`) to the `admin` menu returned by `getMenuItems` in `frontend/src/utils/roleHelpers.js`, after the "Staff" item.

**Checkpoint**: Routing prefix, pagination, API client, and admin nav exist — user stories can begin.

---

## Phase 3: User Story 1 - Center-wide patient roster (Priority: P1) 🎯 MVP

**Goal**: Admin sees a single table of every center patient with their assigned doctor (or "Unassigned"), paginated.

**Independent Test**: Log in as admin, open `/admin/patients`; verify all patients across all doctors are listed with the assigned doctor column and an "Unassigned" indicator where applicable, plus total count and pagination.

### Implementation for User Story 1

- [X] T006 [P] [US1] Add `AdminPatientListSerializer` in `backend/patients/serializers.py` with fields `id, full_name, date_of_birth, contact_email, created_at, assigned_doctor`; `assigned_doctor` is a `SerializerMethodField` returning `{id, name (doctor.get_full_name()), email}` from the patient's most-recent `doctor_assignments` (ordered `-assigned_at`), or `None` when unassigned (research.md decision 5).
- [X] T007 [US1] Add `AdminPatientListCreateView(generics.ListCreateAPIView)` in `backend/patients/views.py` with `permission_classes=[IsAuthenticated, IsAdmin]`, `pagination_class=AdminPatientPagination`; `get_queryset()` returns `Patient.objects.all().select_related('created_by').prefetch_related('doctor_assignments__doctor').order_by('full_name')` with optional `?search=` over `full_name`/`contact_email` (Q-filter); `get_serializer_class()` returns `AdminPatientListSerializer` for GET (POST branch added in US2). Import `IsAdmin`, `Count`/`Q` as needed.
- [X] T008 [US1] Register the list route `path('', AdminPatientListCreateView.as_view(), name='admin-patients')` in `backend/patients/admin_urls.py`.
- [X] T009 [P] [US1] Create `frontend/src/hooks/useAdminPatients.js` (mirror `useDoctors.js`): PAGE_SIZE=50, debounced (300ms) search, `reloadKey`/`refresh()`, returns `{patients, totalCount, currentPage, totalPages, loading, error, search, setSearch, setPage, refresh}` from `listAdminPatients`.
- [X] T010 [P] [US1] Create `frontend/src/components/admin/AdminPatientTable.jsx`: search input; loading skeleton; error + empty states (with/without search); columns Name (+email subtext), Assigned Doctor (doctor name or an "Unassigned" badge), Registered (created_at); pagination when totalPages>1. Accepts props for data + a `onReassign(patient)` callback (wired in US3).
- [X] T011 [US1] Create `frontend/src/pages/PatientDistributionPage.jsx` using `AppLayout`: header "Patient Distribution" + total count, renders `AdminPatientTable` driven by `useAdminPatients` (Register button + reassign modal added in US2/US3).
- [X] T012 [US1] Add a lazy import for `PatientDistributionPage` and a `<Route path="/admin/patients" element={<ProtectedRoute><PatientDistributionPage /></ProtectedRoute>} />` after the `/admin/doctors` route in `frontend/src/routes/AppRoutes.jsx`.

**Checkpoint**: Roster is fully functional and demoable on its own (MVP).

---

## Phase 4: User Story 2 - Register a new patient with doctor assignment (Priority: P2)

**Goal**: Admin registers a patient and optionally assigns a doctor from a dropdown in one step.

**Independent Test**: As admin, open the Register New Patient form, fill details, pick a doctor (or leave blank), submit; the patient appears on the roster assigned to that doctor (or "Unassigned").

### Implementation for User Story 2

- [X] T013 [US2] Add `AdminPatientRegisterSerializer` in `backend/patients/serializers.py`: writable fields `full_name, date_of_birth, contact_phone, contact_email, medical_notes` + write-only optional `doctor_id`; `validate_date_of_birth` (not future); `validate_doctor_id` (exists, role `doctor`, `is_active`); `create()` runs in `transaction.atomic()` — creates the `Patient` (`created_by=request.user`) and, if `doctor_id` given, a `DoctorPatientAssignment` (`assigned_by=None`); `to_representation` delegates to `AdminPatientListSerializer` (research.md decisions 3, 6, 11).
- [X] T014 [US2] Extend `AdminPatientListCreateView.get_serializer_class()` in `backend/patients/views.py` to return `AdminPatientRegisterSerializer` for POST, and override `create()` if needed to return the created row via `AdminPatientListSerializer` with HTTP 201.
- [X] T015 [P] [US2] Create `frontend/src/components/admin/RegisterPatientForm.jsx` (modal): fields full_name, date_of_birth, contact_phone, contact_email, medical_notes, and a doctor dropdown populated from `doctorService.listDoctors()` filtered to `is_active` (research.md decision 8); client validation (full_name + date_of_birth required); submit builds `{full_name, date_of_birth, ...optional, ...(doctor_id ? {doctor_id} : {})}`; props open/onSubmit/onClose/loading/submitError.
- [X] T016 [US2] Wire registration into `frontend/src/pages/PatientDistributionPage.jsx`: add "Register Patient" button, modal open/close + submitting/submitError state, `handleRegister` calling `registerPatient(...)` then `refresh()`, with a DRF-error flattening helper (mirror `StaffManagementPage.jsx`).

**Checkpoint**: Registration works end-to-end and new patients show on the roster.

---

## Phase 5: User Story 3 - Assign or reassign a patient to a doctor (Priority: P3)

**Goal**: Admin moves a patient to exactly one doctor (replace semantics), or assigns an unassigned patient.

**Independent Test**: As admin, reassign a patient from Doctor A to Doctor B; roster shows Doctor B, A no longer has them, and the patient's data is unchanged.

### Implementation for User Story 3

- [X] T017 [US3] Add `AdminPatientAssignSerializer` in `backend/patients/serializers.py`: required write-only `doctor_id` with the same validation as registration (exists, role `doctor`, `is_active`).
- [X] T018 [US3] Add `AdminPatientAssignView(APIView)` in `backend/patients/views.py` with `permission_classes=[IsAuthenticated, IsAdmin]`; `post(request, pk)` loads the patient (404 if missing), validates `AdminPatientAssignSerializer`, then in `transaction.atomic()` deletes the patient's existing `DoctorPatientAssignment` rows and creates one to the chosen doctor (`assigned_by=None`); returns the updated row via `AdminPatientListSerializer` (HTTP 200) (research.md decision 4).
- [X] T019 [US3] Register the assign route `path('<int:pk>/assign/', AdminPatientAssignView.as_view(), name='admin-patient-assign')` in `backend/patients/admin_urls.py`.
- [X] T020 [P] [US3] Create `frontend/src/components/admin/AssignDoctorModal.jsx`: shows the patient name + a doctor dropdown (active doctors via `doctorService.listDoctors()`), confirm/cancel; props open/patient/onSubmit/onClose/loading/submitError.
- [X] T021 [US3] Wire reassignment: add a "Reassign" action per row in `frontend/src/components/admin/AdminPatientTable.jsx` (calls `onReassign(patient)`), and in `frontend/src/pages/PatientDistributionPage.jsx` manage the `AssignDoctorModal` state + `handleAssign` calling `assignPatient(id, doctorId)` then `refresh()`.

**Checkpoint**: All three stories independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Verify the full feature without mutating the remote DB unnecessarily.

- [X] T022 [P] Run `py manage.py check` in `backend/` and lint the new/changed frontend files; resolve any new errors (pre-existing baseline patterns excepted).
- [X] T023 Run a read-only API smoke check (DRF `APIRequestFactory`) confirming `GET /api/admin/patients/` returns 401 (anon) / 403 (doctor) / 200 (admin) and each result carries `assigned_doctor` (object or null); delete the temp script afterward.
- [X] T024 Execute the `quickstart.md` browser walkthrough (scenarios 1–20) with both dev servers running.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: none.
- **Foundational (Phase 2)**: after Setup — **blocks all stories** (routing, pagination, service, nav).
- **US1 (Phase 3)**: after Foundational. MVP.
- **US2 (Phase 4)**: after Foundational; extends the US1 view/page (shares `views.py`, `serializers.py`, `PatientDistributionPage.jsx`) → run after US1.
- **US3 (Phase 5)**: after Foundational; adds a separate view/route + wires into the US1 table/page → run after US1 (independent of US2).
- **Polish (Phase 6)**: after all desired stories.

### User Story Dependencies

- **US1 (P1)**: independent — delivers the roster alone.
- **US2 (P2)**: extends US1's `AdminPatientListCreateView` and page; independently testable (register → roster).
- **US3 (P3)**: independent of US2; reuses US1's table/page; independently testable (reassign → roster).

### Within Each User Story

- Backend serializer → view → URL route → frontend component → page wiring.
- Same-file tasks run sequentially: `serializers.py` (T006→T013→T017), `views.py` (T007→T014→T018), `admin_urls.py` (T004→T008→T019), `PatientDistributionPage.jsx` (T011→T016→T021), `AdminPatientTable.jsx` (T010→T021).

### Parallel Opportunities

- Phase 2: T002, T003, T005 in parallel (T004 separate as it edits shared `urls.py`).
- US1: T006 [P] (serializer) alongside T009 [P] (hook) and T010 [P] (table) — different files.
- US2: T015 [P] (form component) alongside backend T013/T014.
- US3: T020 [P] (modal) alongside backend T017–T019.

---

## Parallel Example: User Story 1

```text
# After Foundational, launch these US1 tasks together (different files):
Task T006: AdminPatientListSerializer in backend/patients/serializers.py
Task T009: useAdminPatients hook in frontend/src/hooks/useAdminPatients.js
Task T010: AdminPatientTable in frontend/src/components/admin/AdminPatientTable.jsx
```

---

## Implementation Strategy

### MVP First (US1 only)

1. Phase 1 Setup → Phase 2 Foundational → Phase 3 US1.
2. **STOP and VALIDATE**: roster renders all patients with assigned doctor / Unassigned. Demo.

### Incremental Delivery

1. Foundational ready.
2. US1 → roster (MVP) → demo.
3. US2 → registration → demo.
4. US3 → reassignment → demo.

---

## Notes

- No migration: `Patient` and `DoctorPatientAssignment` reused unchanged.
- The `assigned_by=None` choice (admin isn't a doctor) is the crux — see research.md decision 3; do not pass the admin as `assigned_by`.
- Reassignment is delete-then-create in a transaction (replace semantics), distinct from the additive doctor-side `assign-doctor` action.
- Honor the exact URLs: `/api/admin/patients/` and `/api/admin/patients/<id>/assign/`, with the include placed before `api/admin/` in `urls.py`.
- Doctor dropdown reuses feature 047's `doctorService.listDoctors()` (filter `is_active`).
- Commit after each story checkpoint.
