# Tasks: Patient List & Detail Pages

**Input**: Design documents from `/specs/033-patient-list-detail/`
**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅ | quickstart.md ✅

**Tests**: Not requested — no test tasks generated.

**Organization**: Feature is ~90% frontend. Phase 2 (Foundational) covers two minor backend serializer additions and shared frontend infrastructure that all user story phases depend on. Each user story phase is independently deployable and testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (no shared file conflicts)
- **[Story]**: Which user story this task belongs to (US1–US4)

---

## Phase 1: Setup

**Purpose**: No dedicated setup needed — all directories already exist in the monorepo. `backend/patients/`, `backend/biometrics/`, and `frontend/src/{services,hooks,components,pages}` are in place.

*No tasks — proceed directly to Phase 2.*

---

## Phase 2: Foundational — Backend Enhancements + Shared Frontend Infrastructure

**Purpose**: Two backend serializer additions required by all frontend user stories, plus the shared `patientService.js` and `Pagination.jsx` used across all pages.

**⚠️ CRITICAL**: All user story phases depend on this phase completing first.

- [x] T001 [P] Add `last_session_date` computed field to `PatientListSerializer` in `backend/patients/serializers.py`. Add `last_session_date = serializers.SerializerMethodField()` to the class and `last_session_date` to the `Meta.fields` list. Implement `get_last_session_date(self, obj)` that calls `obj.biometric_sessions.order_by('-session_start').values('session_start').first()` and returns `result['session_start'].isoformat()` if a session exists, otherwise `None`.

- [x] T002 [P] Add `prefetch_related('biometric_sessions')` to the doctor queryset in `PatientViewSet.get_queryset()` in `backend/patients/views.py`. Chain it after the existing `.prefetch_related('doctor_assignments__doctor')` so it reads: `.prefetch_related('doctor_assignments__doctor', 'biometric_sessions')`. Apply the same addition to the admin queryset on line with `Patient.objects.all()`.

- [x] T003 [P] Add `ml_prediction_severity` computed field to `BiometricSessionListSerializer` in `backend/biometrics/serializers.py`. Add `ml_prediction_severity = serializers.SerializerMethodField()` to the class and `'ml_prediction_severity'` to the `Meta.fields` list. Implement `get_ml_prediction_severity(self, obj)` that returns `obj.ml_prediction.get('severity')` if `obj.ml_prediction` is not None, otherwise `None`.

- [x] T004 [P] Create `frontend/src/services/patientService.js`. Export five functions using the `api` Axios instance from `./api.js`: (1) `getPatients(params)` → `GET /patients/` with `params` spread as query string (supports `name`, `page`, `page_size`); (2) `getPatient(id)` → `GET /patients/{id}/`; (3) `createPatient(data)` → `POST /patients/` with JSON body; (4) `updatePatient(id, data)` → `PATCH /patients/{id}/` with JSON body; (5) `getSessions(patientId, params)` → `GET /biometric-sessions/` with `{ patient: patientId, ...params }` as query string. Each function returns `response.data`.

- [x] T005 [P] Create `frontend/src/components/common/Pagination.jsx`. Accept props: `currentPage` (int), `totalPages` (int), `onPageChange` (fn). Render a row of controls: a "Previous" button (disabled when `currentPage === 1`), a "Next" button (disabled when `currentPage === totalPages`), and a "Page X of Y" label. Call `onPageChange(currentPage - 1)` / `onPageChange(currentPage + 1)` on button click. Style with Tailwind (neutral border buttons, disabled state opacity).

**Checkpoint**: Backend serializers extended. Frontend service and pagination component ready. All user story phases can now begin.

---

## Phase 3: User Story 1 — Browse and Search Patient List (Priority: P1) 🎯 MVP

**Goal**: A doctor can navigate to `/doctor/patients`, see a paginated table of their assigned patients, type in a search field to filter by name, and click a patient to navigate to their detail page.

**Independent Test**: Log in as a doctor, navigate to `/doctor/patients`. Verify a table renders with patient rows including name, DOB, and last session date. Type a partial name in the search field and confirm the table updates within 1 second. Verify pagination appears when there are >20 patients.

### Implementation for User Story 1

- [x] T006 [P] [US1] Create `frontend/src/hooks/usePatients.js` (depends on T004). Export `usePatients()` hook. State: `patients` (array), `totalCount`, `currentPage` (1), `totalPages`, `loading` (true initially), `error` (null), `search` (string ''), `setSearch` (fn), `setPage` (fn). On mount and whenever `search` or `currentPage` change, call `patientService.getPatients({ name: search || undefined, page: currentPage, page_size: 20 })`. Debounce the `search` change by 300ms (use a `useEffect` with a `setTimeout`/`clearTimeout` pattern). On success set `patients = response.results`, `totalCount = response.count`, `totalPages = Math.ceil(response.count / 20)`. On error set `error = 'Failed to load patients.'`. Reset to page 1 whenever `search` changes.

- [x] T007 [P] [US1] Create `frontend/src/components/patients/PatientTable.jsx` (depends on T005). Accept props: `patients` (array), `loading` (bool), `error` (string|null), `search` (string), `onSearchChange` (fn), `currentPage`, `totalPages`, `onPageChange`. Render: (1) a search `<input>` with value=`search` and onChange=`onSearchChange`, placeholder "Search by name…"; (2) when `loading` render skeleton rows; (3) when `error` render error message; (4) when `patients.length === 0` and no search, render "No patients yet. Add your first patient."; (5) when `patients.length === 0` and search is set, render "No patients match your search."; (6) otherwise render a `<table>` with columns: Full Name, Date of Birth, Last Session, and an arrow icon. Each row is clickable (use `<Link to="/doctor/patients/{patient.id}">`) and displays the patient data. Format `date_of_birth` as locale date string. Format `last_session_date` as "Feb 18, 2026 14:22" or "No sessions" if null. (7) Render `<Pagination>` below the table.

- [x] T008 [US1] Create `frontend/src/pages/PatientListPage.jsx` (depends on T006, T007). Import `usePatients`, `PatientTable`, and `AppLayout`. In the page body: render a header row with an "Add Patient" button (`<Link to="/doctor/patients/new">`) on the right. Pass all state and handlers from the `usePatients()` hook down to `<PatientTable>`. Wrap in `<AppLayout>`.

- [x] T009 [US1] Add `/doctor/patients` route to `frontend/src/routes/AppRoutes.jsx` (depends on T008). Add lazy import: `const PatientListPage = lazy(() => import('../pages/PatientListPage'))`. Add a new `<Route>` inside the existing `<Routes>`, wrapped in `<ProtectedRoute>`, at path `/doctor/patients`, rendering `<PatientListPage />`. Place it after the `/doctor/dashboard` route.

**Checkpoint**: US1 complete. Doctor can browse, search, and paginate their patient list. Navigate to `/doctor/patients` to verify independently.

---

## Phase 4: User Story 2 — View Patient Detail Page (Priority: P2)

**Goal**: A doctor clicks a patient row and lands on `/doctor/patients/:id`, seeing the patient's complete profile card plus a paginated session history list with ML severity badges.

**Independent Test**: Navigate directly to `/doctor/patients/1` (with a known patient ID). Verify the profile card shows all profile fields. Verify the session history table shows sessions with date, duration, and ML severity. Verify empty state renders when no sessions exist.

### Implementation for User Story 2

- [x] T010 [P] [US2] Create `frontend/src/hooks/usePatient.js` (depends on T004). Export `usePatient(patientId)` hook. On mount (when `patientId` is set), fire two parallel requests: `patientService.getPatient(patientId)` and `patientService.getSessions(patientId, { page: 1, page_size: 10 })`. State: `patient` (object|null), `sessions` (array), `sessionCount`, `sessionPage` (1), `sessionTotalPages`, `loading` (true), `sessionsLoading` (bool), `error` (null), `setSessionPage` (fn). When `sessionPage` changes, refetch sessions. On patient fetch error, set `error = 'Patient not found or access denied.'`. On sessions fetch error, sessions show empty with an error note.

- [x] T011 [P] [US2] Create `frontend/src/components/patients/SessionHistoryList.jsx` (depends on T005). Accept props: `sessions` (array), `loading` (bool), `error` (string|null), `currentPage`, `totalPages`, `onPageChange`. Render: (1) when `loading`, skeleton rows; (2) when `error`, error message; (3) when `sessions.length === 0`, "No monitoring sessions recorded yet."; (4) otherwise a `<table>` with columns: Date & Time, Duration, ML Severity. Format `session_start` as locale date-time string. Format `session_duration` (e.g., "00:15:30") as human-readable (e.g., "15m 30s") using string splitting. Render `ml_prediction_severity` as a colour-coded badge: mild=green, moderate=amber, severe=red, null="No prediction" in grey. (5) Render `<Pagination>` below table.

- [x] T012 [US2] Create `frontend/src/pages/PatientDetailPage.jsx` (depends on T010, T011). Import `usePatient`, `SessionHistoryList`, `AppLayout`. Get `:id` from `useParams()`. Call `usePatient(id)`. Render: (1) when `loading`, a profile skeleton; (2) when `error`, show the error message with a "Back to patients" link; (3) when `patient` is loaded, show a profile card with all fields (full_name as heading, DOB, contact_phone if set, contact_email if set, medical_notes if set, paired device status if set). Include an "Edit" button (`<Link to="/doctor/patients/{id}/edit">`) in the header row. Below the profile card, render `<SessionHistoryList>` with sessions state and handlers from the hook.

- [x] T013 [US2] Add `/doctor/patients/:id` route to `frontend/src/routes/AppRoutes.jsx` (depends on T012, must come after T009). Add lazy import: `const PatientDetailPage = lazy(() => import('../pages/PatientDetailPage'))`. Add `<Route path="/doctor/patients/:id" element={<ProtectedRoute><PatientDetailPage /></ProtectedRoute>} />` after the `/doctor/patients` route.

**Checkpoint**: US2 complete. Doctor can view a patient's full profile and session history. Navigate to `/doctor/patients/:id` to verify independently.

---

## Phase 5: User Story 3 — Create a New Patient (Priority: P3)

**Goal**: A doctor clicks "Add Patient", fills a form, and saves — creating a new patient record. They are redirected to the new patient's detail page and the patient appears in their list.

**Independent Test**: Navigate to `/doctor/patients/new`. Fill in full_name and date_of_birth, submit. Verify navigation to the new patient's detail page. Check that leaving full_name blank shows an inline validation error without submitting.

### Implementation for User Story 3

- [x] T014 [US3] Create `frontend/src/components/patients/PatientForm.jsx`. Accept props: `initialValues` (object, optional), `onSubmit` (fn receiving form data), `loading` (bool), `submitError` (string|null). Render a form with fields: `full_name` (text input, required), `date_of_birth` (date input, required), `contact_phone` (text input, optional), `contact_email` (email input, optional), `medical_notes` (textarea, optional). Pre-populate each field from `initialValues` if provided. Client-side validation on submit: (1) `full_name` must not be empty or whitespace-only → "Full name is required"; (2) `date_of_birth` must not be in the future → "Date of birth cannot be in the future"; (3) `contact_phone` if provided must match `^\+?[\d\s\-\(\)]{7,20}$` → "Enter a valid phone number"; (4) `contact_email` if provided must be a valid email format → "Enter a valid email address". Display inline error messages beneath each invalid field. Do not call `onSubmit` if any field fails. Show `submitError` as a top-level error banner. Render a "Save" button with loading spinner when `loading=true`. Render a "Cancel" button that calls browser history back.

- [x] T015 [US3] Create `frontend/src/pages/PatientCreatePage.jsx` (depends on T014). Import `PatientForm`, `AppLayout`, `patientService`, `useNavigate`. State: `loading` (false), `error` (null). Implement `handleSubmit(formData)`: call `patientService.createPatient(formData)`, on success navigate to `/doctor/patients/${response.id}`, on error set `error` to the API error message. Render `<PatientForm onSubmit={handleSubmit} loading={loading} submitError={error} />` inside `<AppLayout>` with a page heading "Add New Patient".

- [x] T016 [US3] Add `/doctor/patients/new` route to `frontend/src/routes/AppRoutes.jsx` (depends on T015, must come after T013 and must be placed BEFORE the `/doctor/patients/:id` route to prevent "new" being parsed as an ID). Add lazy import: `const PatientCreatePage = lazy(() => import('../pages/PatientCreatePage'))`. Insert route `<Route path="/doctor/patients/new" element={<ProtectedRoute><PatientCreatePage /></ProtectedRoute>} />` between the `/doctor/patients` route and the `/doctor/patients/:id` route.

**Checkpoint**: US3 complete. Doctor can create a new patient end-to-end. Navigate to `/doctor/patients/new` to verify independently.

---

## Phase 6: User Story 4 — Edit Patient Profile (Priority: P4)

**Goal**: A doctor clicks "Edit" on a patient's detail page, modifies profile fields, and saves. They are returned to the detail page with updated data.

**Independent Test**: Navigate to `/doctor/patients/:id/edit` for a known patient. Verify the form is pre-populated with existing values. Change the medical notes, save, and confirm the detail page shows the updated value.

### Implementation for User Story 4

- [x] T017 [US4] Create `frontend/src/pages/PatientEditPage.jsx` (depends on T014, T004). Import `PatientForm`, `AppLayout`, `patientService`, `useNavigate`, `useParams`. On mount, fetch `patientService.getPatient(id)` to get current values. State: `initialValues` (null while loading), `loading` (false for form submit), `fetchError` (null), `submitError` (null). While fetching, show a loading skeleton. If fetch fails, show error with "Back" link. Implement `handleSubmit(formData)`: call `patientService.updatePatient(id, formData)`, on success navigate to `/doctor/patients/${id}`, on error set `submitError`. Render `<PatientForm initialValues={initialValues} onSubmit={handleSubmit} loading={loading} submitError={submitError} />` inside `<AppLayout>` with heading "Edit Patient".

- [x] T018 [US4] Add `/doctor/patients/:id/edit` route to `frontend/src/routes/AppRoutes.jsx` (depends on T017, must come after T016). Add lazy import: `const PatientEditPage = lazy(() => import('../pages/PatientEditPage'))`. Add `<Route path="/doctor/patients/:id/edit" element={<ProtectedRoute><PatientEditPage /></ProtectedRoute>} />` after the `/doctor/patients/:id` route.

**Checkpoint**: US4 complete. All four user stories are independently functional.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [x] T019 [P] Validate all four quickstart scenarios from `specs/033-patient-list-detail/quickstart.md`: (1) search flow, (2) detail page with sessions, (3) create patient, (4) edit patient, (5) validation errors, (6) access denied (navigate to /doctor/patients/999 as a doctor and confirm error state renders).

- [x] T020 [P] Verify the `last_session_date` field appears in `GET /api/patients/` responses and `ml_prediction_severity` appears in `GET /api/biometric-sessions/?patient={id}` responses (manual curl or browser DevTools check against the OpenAPI contract in `specs/033-patient-list-detail/contracts/patients.yaml`).

- [x] T021 [P] Verify the Sidebar navigation link to `/doctor/patients` (already configured in `frontend/src/utils/roleHelpers.js`) is active-highlighted when on any `/doctor/patients*` route. If not, update the active-route detection logic in `frontend/src/components/layout/Sidebar.jsx` to use `location.pathname.startsWith('/doctor/patients')` for the Patients menu item.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Foundational (Phase 2)**: No dependencies — all 5 tasks start immediately in parallel
- **US1 (Phase 3)**: Depends on Phase 2 (T004 for hook, T005 for table)
- **US2 (Phase 4)**: Depends on Phase 2 (T004 for hook, T005 for sessions list)
- **US3 (Phase 5)**: Depends on Phase 2 (T004 for create call); depends on US2 completion for AppRoutes ordering
- **US4 (Phase 6)**: Depends on Phase 5 (shares PatientForm from T014) and AppRoutes ordering
- **Polish (Phase 7)**: Depends on all user stories complete

### AppRoutes.jsx Editing Order (Sequential)

All AppRoutes.jsx edits touch the same file and must be done in this order:
```
T009 (add /doctor/patients)
  → T013 (add /doctor/patients/:id)
    → T016 (add /doctor/patients/new — BEFORE :id)
      → T018 (add /doctor/patients/:id/edit)
```

### Within Each Phase (partial parallel)

```
Phase 3:  T006 [P] ─┐
                     ├→ T008 → T009
          T007 [P] ─┘

Phase 4:  T010 [P] ─┐
                     ├→ T012 → T013
          T011 [P] ─┘

Phase 5:  T014 → T015 → T016

Phase 6:  T017 → T018
```

### User Story Dependencies

- **US1 (P1)**: Independent after Phase 2 ✅
- **US2 (P2)**: Independent after Phase 2 ✅ (AppRoutes editing serialised after US1's T009)
- **US3 (P3)**: Independent after Phase 2 ✅ (AppRoutes must come after US2's T013)
- **US4 (P4)**: Reuses `PatientForm` from US3 — T017 depends on T014

---

## Parallel Execution Examples

### Phase 2 (all 5 tasks in parallel)
```
T001 (PatientListSerializer)
T002 (PatientViewSet queryset)
T003 (BiometricSessionListSerializer)
T004 (patientService.js)
T005 (Pagination.jsx)
```

### Phase 3 (US1 — two parallel tracks)
```
Track A: T006 (usePatients.js)   ─┐
                                    ├→ T008 (PatientListPage) → T009 (Route)
Track B: T007 (PatientTable.jsx) ─┘
```

### Phase 7 (all Polish tasks parallel)
```
T019 [P]  T020 [P]  T021 [P]
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 2: Foundational (T001–T005)
2. Complete Phase 3: US1 Patient List (T006–T009)
3. **STOP and VALIDATE**: Navigate to `/doctor/patients`, confirm table + search + pagination work
4. Deliver MVP — doctors can find their patients

### Incremental Delivery

1. Phase 2 (Foundational) → Shared infrastructure ready
2. Phase 3 (US1) → Patient list live ✅ MVP
3. Phase 4 (US2) → Patient detail + session history ✅
4. Phase 5 (US3) → Create patient ✅
5. Phase 6 (US4) → Edit patient ✅
6. Phase 7 (Polish) → All edge cases validated ✅

---

## Notes

- [P] tasks = different files, no dependencies — safe to implement concurrently
- All AppRoutes.jsx edits (T009, T013, T016, T018) must be sequential — same file
- Route `/doctor/patients/new` MUST be registered BEFORE `/doctor/patients/:id` in React Router to prevent "new" being matched as a dynamic ID
- `PatientForm.jsx` is the only shared component across US phases (US3 creates it, US4 reuses it)
- `last_session_date` in `PatientListSerializer` uses a raw queryset call (not the prefetch cache) — acceptable for a graduation project at this scale
- The `api.js` Axios instance handles JWT injection and 401 redirects; no auth logic needed in `patientService.js`
