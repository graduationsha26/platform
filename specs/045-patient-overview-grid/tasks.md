# Tasks: Patient Overview Grid

**Input**: Design documents from `/specs/045-patient-overview-grid/`
**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅

**Tests**: Not requested — no test tasks generated.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)

## Path Conventions

- **Backend (Django)**: `backend/patients/`
- **Frontend (React)**: `frontend/src/`

---

## Phase 1: Setup

> **No action required.** All infrastructure is in place: DRF `APIView`, Django ORM, React hooks, and the `patientService.js` Axios client already exist in their respective apps.

---

## Phase 2: Foundational (Blocking Prerequisite)

**Purpose**: Add the `avatar_url` field to the Patient model. This is a blocking prerequisite because the backend endpoint (US1) reads this field. Frontend tasks can proceed in parallel since they rely on the API contract, not the migration.

**⚠️ CRITICAL**: The Django migration MUST be applied to Supabase PostgreSQL before starting the Django dev server for US1 endpoint testing.

- [x] T001 Add `avatar_url = models.URLField(max_length=500, blank=True, default='')` to the `Patient` class in `backend/patients/models.py`
- [x] T002 Run `python manage.py makemigrations patients --name patient_avatar_url` then `python manage.py migrate` to create and apply the migration in `backend/patients/migrations/` (depends on T001)

**Checkpoint**: `Patient.avatar_url` field exists in the database. Existing patient rows have `avatar_url = ''`.

---

## Phase 3: User Story 1 — Patient Overview Grid with Live Device Status (Priority: P1) 🎯 MVP

**Goal**: Add `GET /api/patients/overview/` returning `{count, results[]}` with `id`, `full_name`, `avatar_url`, `device_online` per patient. Render a responsive grid on the dashboard where each card shows avatar (or initials fallback), full name, and an online/offline badge.

**Independent Test**: Call `GET /api/patients/overview/` with a doctor JWT → verify `{ "count": N, "results": [...] }` with HTTP 200. Navigate to `/doctor/dashboard` → verify a grid of patient cards appears below the 3 summary cards, each showing the correct name, avatar or initials, and online/offline badge. Call the endpoint without a token → verify HTTP 401. Call with admin token → verify HTTP 403.

### Implementation

- [x] T003 [P] [US1] Add `PatientOverviewItemSerializer` class (fields: `id` IntegerField, `full_name` CharField, `avatar_url` CharField with `default=''`, `device_online` BooleanField) to `backend/patients/serializers.py`
- [x] T004 [US1] Add `PatientsOverviewView(APIView)` to `backend/patients/views.py`: `permission_classes = [IsAuthenticated]`; doctor role check returning 403; query `Patient.objects.filter(doctor_assignments__doctor=request.user).annotate(latest_device_seen=Max('devices__last_seen')).order_by('full_name')`; compute `device_online = latest_device_seen is not None and latest_device_seen >= timezone.now() - timedelta(seconds=60)`; serialize with `PatientOverviewItemSerializer(results, many=True)`; return `{ 'count': len(results), 'results': serializer.data }` with HTTP 200. Add required imports: `Max` from `django.db.models`, `timedelta` from `datetime`, `timezone` from `django.utils`. (Depends on T001, T003)
- [x] T005 [US1] Add `path('overview/', views.PatientsOverviewView.as_view(), name='patients-overview')` to `urlpatterns` in `backend/patients/urls.py`. (Depends on T004)
- [x] T006 [P] [US1] Add `fetchPatientsOverview()` async function (GET `/patients/overview/`, returns `response.data`) to `frontend/src/services/patientService.js`
- [x] T007 [US1] Create `frontend/src/hooks/usePatientsOverview.js`: mirror `useCriticalAlerts` exactly — `useState` for `data/loading/error`, `useEffect` with cancellation flag calling `fetchPatientsOverview()`, return `{ data, loading, error }`. (Depends on T006)
- [x] T008 [P] [US1] Create `frontend/src/components/dashboard/PatientCard.jsx`: accepts `patient` prop (`{ id, full_name, avatar_url, device_online }`). Render (a) a circular avatar — if `avatar_url` is truthy, render `<img src={avatar_url} onError={fallbackToInitials}>`, otherwise render a div with initials computed as `full_name.trim().split(/\s+/).slice(0,2).map(w=>w[0]?.toUpperCase()||'').join('')`; (b) `full_name` text; (c) an "Online" badge (green pill) if `device_online`, otherwise an "Offline" badge (grey pill). Do NOT include navigation buttons yet — those are added in US2 (T011). Style with Tailwind CSS.
- [x] T009 [US1] Create `frontend/src/components/dashboard/PatientOverviewGrid.jsx`: internally calls `usePatientsOverview()`; renders (a) loading state (spinner or skeleton) while `loading=true`; (b) error message div when `error` is set; (c) empty-state message "No patients assigned yet." when `data?.count === 0`; (d) responsive grid `grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4` mapping `data.results` to `<PatientCard key={p.id} patient={p} />`. (Depends on T007, T008)
- [x] T010 [US1] Update `frontend/src/pages/DoctorDashboard.jsx`: (a) add `import PatientOverviewGrid from '../components/dashboard/PatientOverviewGrid'`; (b) add a `<div className="mt-8">` block with `<h2 className="text-xl font-semibold text-neutral-900 mb-4">Your Patients</h2>` and `<PatientOverviewGrid />` immediately after the existing summary cards `<div className="grid ...">` closing tag. (Depends on T009)

**Checkpoint**: After T010 — restart Django dev server (migration must be applied), reload frontend. Patient grid appears on the dashboard with real data. Cards show correct avatar or initials and correct online/offline badge. `GET /api/patients/overview/` returns correct JSON in Postman/curl.

---

## Phase 4: User Story 2 — Quick Navigation to Patient Detail Pages (Priority: P2)

**Goal**: Add "View Profile" and "Live Monitor" link buttons to each patient card, routing to `/doctor/patients/:id` and `/doctor/patients/:id/monitor` respectively.

**Independent Test**: From the dashboard patient grid, click "View Profile" on any card — verify navigation to `/doctor/patients/{id}` (PatientDetailPage loads, no 404). Click "Live Monitor" — verify navigation to `/doctor/patients/{id}/monitor` (LiveTremorPage loads, no 404). Both buttons are visible on every card without scrolling.

### Implementation

- [x] T011 [US2] Add two navigation buttons to `frontend/src/components/dashboard/PatientCard.jsx`: import `{ Link }` from `'react-router-dom'`; add a button row below the badge containing `<Link to={`/doctor/patients/${patient.id}`} className="...">View Profile</Link>` and `<Link to={`/doctor/patients/${patient.id}/monitor`} className="...">Live Monitor</Link>`. Both links styled as small Tailwind buttons (e.g., text-sm, rounded, border or bg). (Depends on T008)

**Checkpoint**: After T011 — reload the dashboard. Both buttons appear on every card. Clicking each navigates correctly.

---

## Phase 5: Polish & Integration Verification

**Purpose**: Confirm both user stories work together end-to-end.

- [x] T012 Verify all 10 quickstart scenarios in `specs/045-patient-overview-grid/quickstart.md` pass: (1) doctor with patients sees correct grid, (2) "View Profile" navigates to patient profile, (3) "Live Monitor" navigates to monitor page, (4) empty state message when no patients, (5) unauthenticated → 401, (6) admin token → 403, (7) empty avatar_url → initials rendered, (8) single-word name → single initial, (9) doctor isolation, (10) grid error state does not break dashboard.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No action — skip
- **Foundational (Phase 2)**: No dependency — start immediately; BLOCKS T004 (backend view needs avatar_url in DB)
- **US1 (Phase 3)**: T003/T006/T008 can start immediately in parallel (different files). T004 depends on T001+T003. T005 depends on T004. T007 depends on T006. T009 depends on T007+T008. T010 depends on T009.
- **US2 (Phase 4)**: T011 depends on T008 (PatientCard already created). No backend dependency.
- **Polish (Phase 5)**: Depends on Phase 3 AND Phase 4 completion.

### User Story Dependencies

- **US1 (P1)**: Backend starts after T001+T002 for API; frontend tasks (T006, T007, T008, T009, T010) are independent of migration and can start in parallel with backend.
- **US2 (P2)**: Depends only on PatientCard.jsx (T008) being created — can start immediately after T008 is done (no need to wait for T010).

### Within Phase 3 (US1)

- T003, T006, T008 can run **in parallel** (three different files: serializers.py, patientService.js, PatientCard.jsx)
- T004 depends on T001 (avatar_url field) and T003 (serializer class)
- T005 depends on T004
- T007 depends on T006
- T009 depends on T007 AND T008
- T010 depends on T009

### Within Phase 4 (US2)

- T011 is a single task modifying PatientCard.jsx; depends on T008

---

## Parallel Execution Examples

### Phase 3 (US1) — 3-way parallel start, then converge

```
# Start simultaneously (3 different files):
T003: Add PatientOverviewItemSerializer in backend/patients/serializers.py
T006: Add fetchPatientsOverview() in frontend/src/services/patientService.js
T008: Create PatientCard.jsx in frontend/src/components/dashboard/

# After T001 + T003:
T004: Add PatientsOverviewView in backend/patients/views.py

# After T004:
T005: Add overview/ route in backend/patients/urls.py

# After T006:
T007: Create usePatientsOverview.js in frontend/src/hooks/

# After T007 + T008:
T009: Create PatientOverviewGrid.jsx in frontend/src/components/dashboard/

# After T009:
T010: Integrate PatientOverviewGrid into frontend/src/pages/DoctorDashboard.jsx
```

---

## Implementation Strategy

### MVP (User Story 1 Only — Grid + Badge)

1. Complete T001 + T002 (migration)
2. Run T003, T006, T008 in parallel
3. Complete T004 after T001+T003
4. Complete T005 after T004
5. Complete T007 after T006
6. Complete T009 after T007+T008
7. Complete T010 after T009
8. **STOP and VALIDATE**: Grid appears on dashboard with data and correct badges. API returns correct JSON.

### Full Feature (Both Stories)

1. Complete US1 (T001–T010)
2. Complete T011 (US2 — add navigation buttons)
3. T012 — verify all 10 quickstart scenarios

### Total Task Count: 12

| Story | Tasks | Parallelizable |
|-------|-------|----------------|
| Foundational | 2 (T001–T002) | T001 then T002 (sequential — migration needs model change) |
| US1 — Patient Overview Grid + Status Badge | 8 (T003–T010) | T003, T006, T008 fully parallel; T004→T005 and T006→T007 chains; T009→T010 sequential |
| US2 — Quick Navigation Buttons | 1 (T011) | No — modifies PatientCard after T008 |
| Polish | 1 (T012) | No — requires both stories complete |

---

## Notes

- T001 and T004 both touch `backend/patients/` — done sequentially (T001 first as foundational, T004 in US1)
- T008 and T011 both touch `frontend/src/components/dashboard/PatientCard.jsx` — done sequentially (T008 in US1, T011 in US2)
- No new Django app needed — endpoint lives in the existing `patients` app at `/api/patients/overview/`
- Django migration (T002) must be applied before testing the backend endpoint (T005); frontend can be developed and visually tested with mock/empty data before this
- `TruncDate` is NOT needed by this feature — `Max('devices__last_seen')` uses a standard aggregate
- `device_online` uses `Device.last_seen` (not `Device.status`) per research Decision 3
- Initials logic is frontend-only per research Decision 4
