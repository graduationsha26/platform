# Tasks: Staff (Doctor) Management

**Input**: Design documents from `/specs/047-doctor-management/`
**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅

**Tests**: Not requested — no test tasks generated. Validation is manual via `quickstart.md`.

**Organization**: Tasks are grouped by user story (US1 → US2 → US3) to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1 (roster), US2 (add/edit), US3 (toggle)

## Path Conventions

- **Backend (Django)**: `backend/authentication/`, `backend/tremoai_backend/`
- **Frontend (React)**: `frontend/src/`

## Sub-item Traceability

| User input | Covered by |
|------------|-----------|
| 6.6 `GET /api/admin/doctors/` (patient_count) | US1 — T006, T007, T008 |
| 6.1 `DoctorManagementTable` (name, count, status) | US1 — T010, T011 |
| 6.4 `POST /api/admin/doctors/` (create) | US1 backend (T006) + US2 UI (T015, T016) |
| 6.5 `PATCH /api/admin/doctors/<id>/` (update/toggle) | US2 — T013, T014 |
| 6.2 `DoctorFormModal` (name, email, password, status) | US2 — T015, T016, T017 |
| 6.3 deactivate/reactivate toggle per row | US3 — T018, T019 |

---

## Phase 1: Setup

> **No action required.** No new dependencies. Backend uses existing DRF generics + Django ORM; frontend uses the existing Axios `api` client, React hooks, `AppLayout`, and lucide-react icons. No database migration (no schema change — see research.md Decision 11).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared backend authz/serialization + frontend service/nav that ALL stories depend on. None of these touch URL routing, so the server stays runnable after this phase.

- [X] T001 [P] Add `IsAdmin` permission class to `backend/authentication/permissions.py`: returns `True` only when `request.user` is authenticated and `request.user.role == 'admin'`; set `message = "Only admins can perform this action."` (mirrors the existing `IsDoctor` class style).
- [X] T002 [P] Add `DoctorListSerializer` (read) to `backend/authentication/serializers.py`: `Meta.model = CustomUser`; fields `id`, `name`, `email`, `is_active`, `patient_count`, `date_joined`. `name` = `SerializerMethodField` returning `obj.get_full_name()`. `patient_count` = `serializers.SerializerMethodField` returning `getattr(obj, 'patient_count', 0)` (defaults to 0 when the annotation is absent, e.g. on the create response). All fields read-only.
- [X] T003 [US-shared] Add `DoctorWriteSerializer` (create/update) to `backend/authentication/serializers.py`: fields `name` (CharField, write), `email`, `password` (`write_only`, `required=False`, `validators=[validate_password]`), `is_active` (BooleanField, `required=False`). Implement: `validate_email` (reject if another `CustomUser` has it, excluding `self.instance`); `validate` (require `name` and `password` when `self.instance is None`); a `_split_name(name)` helper (first token → `first_name`, remainder → `last_name`); `create()` using `CustomUser.objects.create_user(email, password, first_name, last_name, role='doctor', is_active=...)`; `update()` applying provided name/email/is_active and calling `set_password` only when a non-empty `password` is supplied; `to_representation()` delegating to `DoctorListSerializer(instance).data`. (Depends on T002.)
- [X] T004 [P] Create `frontend/src/services/doctorService.js`: import the shared `api` client; export `listDoctors(params = {})` (GET `/admin/doctors/`, return `response.data`), `createDoctor(data)` (POST `/admin/doctors/`), `updateDoctor(id, data)` (PATCH `/admin/doctors/${id}/`). Each returns `response.data`.
- [X] T005 [P] Update `getMenuItems('admin')` in `frontend/src/utils/roleHelpers.js` to return a dedicated admin menu instead of mirroring the doctor menu: `Dashboard → /admin/dashboard` (icon `LayoutDashboard`) and `Staff → /admin/doctors` (icon `Users` or `UserCog` from lucide-react). Add the icon import if needed.

**Checkpoint**: Permission, both serializers, the frontend service, and the admin sidebar link exist. No endpoints wired yet — server still runs.

---

## Phase 3: User Story 1 — View the doctor roster (Priority: P1) 🎯 MVP

**Goal**: Admin-only `GET /api/admin/doctors/` returning each doctor with a `patient_count` annotation, surfaced as a roster table (name, assigned patient count, status) on a Staff Management page at `/admin/doctors`.

**Independent Test**: Log in as admin → open `/admin/doctors` → table lists every doctor with name, patient count, and Active/Inactive status; a doctor with no patients shows `0`. `GET /api/admin/doctors/` returns 200 (admin), 403 (doctor token), 401 (no token).

### Implementation

- [X] T006 [US1] Add `AdminDoctorListCreateView(generics.ListCreateAPIView)` to `backend/authentication/views.py`: `permission_classes = [IsAuthenticated, IsAdmin]`; `get_queryset()` returns `CustomUser.objects.filter(role='doctor').annotate(patient_count=Count('patient_assignments', distinct=True)).order_by('first_name', 'last_name', 'id')`; `get_serializer_class()` returns `DoctorWriteSerializer` for POST else `DoctorListSerializer`. Add imports: `from django.db.models import Count`, `from .permissions import IsAdmin`, `from .serializers import DoctorListSerializer, DoctorWriteSerializer`. (Depends on T001, T002, T003.)
- [X] T007 [US1] Create `backend/authentication/admin_urls.py`: `from django.urls import path`; import `AdminDoctorListCreateView` from `.views`; `urlpatterns = [path('doctors/', AdminDoctorListCreateView.as_view(), name='admin-doctors')]`. (Depends on T006.)
- [X] T008 [US1] Add `path('api/admin/', include('authentication.admin_urls'))` to `urlpatterns` in `backend/tremoai_backend/urls.py` with a `# Feature 047: Staff Management` comment. Ensure `include` is imported (already is). (Depends on T007.)
- [X] T009 [P] [US1] Create `frontend/src/hooks/useDoctors.js`: mirror `usePatients` — state for `doctors`, `totalCount`, `currentPage`, `totalPages`, `loading`, `error`, `search`; a `fetchData`/`refresh()` callback that calls `listDoctors({ page, search })`, sets `doctors = data.results`, `totalCount = data.count`, derives `totalPages` from count and page size (50). Expose `{ doctors, totalCount, currentPage, totalPages, loading, error, search, setSearch, setPage, refresh }`. (Depends on T004.)
- [X] T010 [US1] Create `frontend/src/components/admin/DoctorManagementTable.jsx` (read-only roster for now): props `doctors`, `loading`, `error`, `search`, `onSearchChange`, `currentPage`, `totalPages`, `onPageChange`. Columns: **Name**, **Patient Count**, **Status** (Active = green badge / Inactive = neutral/red badge). Render a skeleton/loading row while `loading`, an empty-state message when `doctors` is empty (FR-012), and an error banner when `error` (Scenario 13). Reuse the existing `Pagination` common component.
- [X] T011 [US1] Create `frontend/src/pages/StaffManagementPage.jsx`: wrap `AppLayout`; header "Staff Management" with the doctor count (`{totalCount} doctor(s)`) and an **Add Doctor** button (button is a no-op placeholder until US2); call `useDoctors()` and pass its state/handlers to `<DoctorManagementTable />`. (Depends on T009, T010.)
- [X] T012 [US1] Register the route in `frontend/src/routes/AppRoutes.jsx`: add `const StaffManagementPage = lazy(() => import('../pages/StaffManagementPage'))` with the other admin lazy imports, and `<Route path="/admin/doctors" element={<ProtectedRoute><StaffManagementPage /></ProtectedRoute>} />` next to the existing `/admin/dashboard` route. (Depends on T011.)

**Checkpoint**: Restart Django, reload frontend. As admin, `/admin/doctors` shows the roster with name, patient count, and status. Endpoint returns 200/403/401 correctly. **MVP complete.**

---

## Phase 4: User Story 2 — Add and edit doctor accounts (Priority: P2)

**Goal**: A single modal form (name, email, password, status) to create a new doctor (`POST`) and edit an existing one (`PATCH`), launched from the roster, with email-uniqueness and required-field validation.

**Independent Test**: From the roster, **Add Doctor** → submit valid name/email/password/status → new doctor appears with count `0`. **Edit** a doctor → form pre-filled (password blank) → save name change → row updates; leaving password blank keeps the old password. Duplicate email and missing required fields are rejected.

### Implementation

- [X] T013 [US2] Add `AdminDoctorDetailView(generics.RetrieveUpdateAPIView)` to `backend/authentication/views.py`: `permission_classes = [IsAuthenticated, IsAdmin]`; `http_method_names = ['get', 'patch']` (no PUT/DELETE — no hard delete); `get_queryset()` returns `CustomUser.objects.filter(role='doctor').annotate(patient_count=Count('patient_assignments', distinct=True))`; `get_serializer_class()` returns `DoctorWriteSerializer` for PATCH else `DoctorListSerializer`. (Depends on T003; reuses imports from T006.)
- [X] T014 [US2] Add `path('doctors/<int:pk>/', AdminDoctorDetailView.as_view(), name='admin-doctor-detail')` to `urlpatterns` in `backend/authentication/admin_urls.py` and import `AdminDoctorDetailView` from `.views`. (Depends on T013, T007.)
- [X] T015 [US2] Create `frontend/src/components/admin/DoctorFormModal.jsx`: props `open`, `mode` (`'add'`|`'edit'`), `initialValues`, `onSubmit`, `onClose`, `loading`, `submitError`. Fixed overlay + centered panel. Fields: `name` (text), `email` (email), `password` (password — placeholder "Leave blank to keep current" when `mode==='edit'`), `status` select (Active/Inactive). Pre-fill name/email/status from `initialValues` in edit mode via `useEffect`. Client-side validation: name and email required always; password required only when `mode==='add'`; show field-level errors and the top-level `submitError` banner. On submit, build payload `{ name, email, is_active: status==='active', ...(password ? { password } : {}) }` and call `onSubmit(payload)`.
- [X] T016 [US2] Wire create/edit into `frontend/src/pages/StaffManagementPage.jsx`: add modal state (`modalOpen`, `modalMode`, `editingDoctor`, `submitError`, `submitting`); make the **Add Doctor** button open the modal in `'add'` mode; implement `handleSubmit` that calls `createDoctor` (add) or `updateDoctor(editingDoctor.id, …)` (edit), then closes the modal and calls `refresh()` (FR-011); map a 400 response body to `submitError`/field messages. Render `<DoctorFormModal />`. (Depends on T011, T015.)
- [X] T017 [US2] Add a per-row **Edit** action to `frontend/src/components/admin/DoctorManagementTable.jsx`: new `onEdit(doctor)` prop and an Edit button in an Actions column; page passes a handler that opens the modal in `'edit'` mode with that doctor as `initialValues`. (Depends on T010; page wiring from T016.)

**Checkpoint**: Admin can create and edit doctors from the roster; validation and email-uniqueness errors surface; roster refreshes without a full reload. US1 + US2 both work.

---

## Phase 5: User Story 3 — Deactivate and reactivate doctors (Priority: P3)

**Goal**: A per-row toggle that flips a doctor between Active and Inactive via `PATCH {"is_active": …}`, preserving the account and assignments.

**Independent Test**: On an active doctor's row, click **Deactivate** → status flips to Inactive and the action becomes **Reactivate** (no full reload). Click **Reactivate** → back to Active. A deactivated doctor cannot sign in; their assignments remain intact.

> **Backend**: no new endpoint — the toggle reuses `AdminDoctorDetailView` PATCH from US2 (T013/T014).

### Implementation

- [X] T018 [US3] Add a **Deactivate/Reactivate** action to `frontend/src/components/admin/DoctorManagementTable.jsx`: new `onToggleActive(doctor)` prop; in the Actions column render "Deactivate" for active doctors and "Reactivate" for inactive ones, styled distinctly. (Depends on T010; coexists with the Edit action from T017.)
- [X] T019 [US3] Add `handleToggleActive(doctor)` to `frontend/src/pages/StaffManagementPage.jsx` that calls `updateDoctor(doctor.id, { is_active: !doctor.is_active })` then `refresh()`, and pass it as `onToggleActive` to the table. Handle/ignore the in-flight state to prevent double-clicks. (Depends on T016.)

**Checkpoint**: All three stories functional — view roster, add/edit, and toggle status, all admin-only.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T020 Run all 13 integration scenarios in `specs/047-doctor-management/quickstart.md`: roster render, zero-count, inactive badge, empty state, create, edit (password optional), duplicate-email rejection, missing-field rejection, toggle, deactivated-login-blocked + data preserved, non-admin 403 / anonymous 401, route protection redirect, and backend-unreachable error state.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: none — skip.
- **Foundational (Phase 2)**: blocks all stories. T001/T002/T004/T005 parallel; T003 after T002.
- **US1 (Phase 3)**: needs Phase 2. Backend chain T006 → T007 → T008. Frontend T009 (after T004) → T011; T010 → T011; T011 → T012.
- **US2 (Phase 4)**: needs US1 (extends `views.py`, `admin_urls.py`, the page and the table). T013 → T014; T015 → T016; T016 + T010 → T017.
- **US3 (Phase 5)**: needs US2 backend (PATCH) + US2 page wiring. T018 (table) and T019 (page) after T016/T017.
- **Polish (Phase 6)**: after all stories.

### Within Each User Story

- Backend: serializers/permission (Phase 2) → views → urls.
- Frontend: service (Phase 2) → hook → table/modal → page → route.

---

## Parallel Execution Examples

### Phase 2 (Foundational) — 4-way parallel start

```
# Different files, no dependencies — run together:
T001  IsAdmin permission        → backend/authentication/permissions.py
T002  DoctorListSerializer      → backend/authentication/serializers.py
T004  doctorService.js          → frontend/src/services/doctorService.js
T005  admin nav (roleHelpers)   → frontend/src/utils/roleHelpers.js
# Then:
T003  DoctorWriteSerializer (after T002 — same file)
```

### Phase 3 (US1) — backend and frontend in parallel

```
# Backend chain:
T006 view → T007 admin_urls → T008 main urls include
# Frontend (parallel with backend):
T009 useDoctors → ┐
T010 table ───────┴→ T011 page → T012 route
```

---

## Implementation Strategy

### MVP (User Story 1 only)

1. Phase 2 Foundational (T001–T005).
2. Phase 3 US1 (T006–T012).
3. **STOP and validate**: admin sees the roster with name/count/status; endpoint authz correct. Demo-ready MVP.

### Incremental Delivery

1. Foundational → US1 (roster, MVP) → validate.
2. US2 (add/edit modal) → validate independently.
3. US3 (status toggle) → validate independently.
4. Polish: run full quickstart.

### Total Task Count: 20

| Story | Tasks | Notes |
|-------|-------|-------|
| Foundational | 5 (T001–T005) | T001/T002/T004/T005 parallel; T003 after T002 |
| US1 — Roster (P1, MVP) | 7 (T006–T012) | backend chain + frontend chain run in parallel |
| US2 — Add/Edit (P2) | 5 (T013–T017) | extends US1 view/urls/page/table |
| US3 — Toggle (P3) | 2 (T018–T019) | frontend only; reuses US2 PATCH endpoint |
| Polish | 1 (T020) | quickstart verification |

---

## Notes

- No database migration (research.md Decision 11) — counts derive from existing `CustomUser` + `DoctorPatientAssignment`.
- `IsAdmin` is a **new** permission class — `authentication/permissions.py` previously had only `IsDoctor`, `IsDoctorOrAdmin`, `IsOwnerOrDoctor`.
- Endpoints are `/api/admin/doctors/` and `/api/admin/doctors/<id>/` (research.md Decision 1) — a new `authentication/admin_urls.py` included at `/api/admin/`, views in `authentication/views.py` per the user's instruction.
- The create endpoint (`POST`) becomes available at T006 (US1's `ListCreateAPIView`); the create *user flow* (modal) is delivered in US2. US1's independent test only exercises `GET`.
- `name` ↔ `first_name`/`last_name` split and `is_active` status mapping are handled entirely in `DoctorWriteSerializer`/`DoctorListSerializer` (Decisions 3, 4).
- Same-file evolution across stories (`views.py`, `admin_urls.py`, `StaffManagementPage.jsx`, `DoctorManagementTable.jsx`) is sequential by design — not parallelizable across those stories.
