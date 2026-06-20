# Tasks: Smart Medical Alerts & Dashboard Layout Simplification

**Input**: Design documents from `/specs/044-smart-alerts-dashboard/`
**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅

**Tests**: Not requested — no test tasks generated.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)

## Path Conventions

- **Backend (Django)**: `backend/analytics/`
- **Frontend (React)**: `frontend/src/`

---

## Phase 1: Setup

> **No action required.** All infrastructure is in place: DRF `APIView`, Django ORM, React hooks, and the `analyticsService.js` Axios client already exist. No new packages or initialization needed.

---

## Phase 2: Foundational

> **No action required.** US1 (smart alerts) and US2 (layout removal) touch entirely different layers and have no shared blocking prerequisites. Both can start immediately after planning.

---

## Phase 3: User Story 1 — Smart Critical Alerts on Dashboard (Priority: P1) 🎯 MVP

**Goal**: Add `GET /api/analytics/critical-alerts/` (count of patients with 5 consecutive severe days) and rewire the dashboard Alerts card to display it.

**Independent Test**: Call `GET /api/analytics/critical-alerts/` with a doctor JWT → verify `{ "count": N }`. Navigate to `/doctor/dashboard` → verify the Alerts card shows the same N with subtitle "Patients with 5+ consecutive severe days". Test without a token → verify 401.

### Implementation

- [x] T001 [P] [US1] Add `get_critical_alerts_count(doctor)` method to `DashboardService` and remove the `alerts_count` BiometricSession filter + its return-dict entry from `get_dashboard_stats()` in `backend/analytics/services/dashboard.py`. The new method queries `(patient_id, date)` distinct pairs for severe BiometricSessions in the last 5 days, then counts patients whose set of severe days contains all 5 required dates.
- [x] T002 [P] [US1] Add `CriticalAlertsSerializer` (single `count` IntegerField, min_value=0) to `backend/analytics/serializers.py` and remove the `alerts_count` field from `DashboardStatsSerializer`.
- [x] T003 [P] [US1] Add `fetchCriticalAlerts()` async function (GET `/analytics/critical-alerts/`, returns `response.data`) to `frontend/src/services/analyticsService.js`.
- [x] T004 [US1] Add `CriticalAlertsView(APIView)` class to `backend/analytics/views.py`: `permission_classes = [IsAuthenticated]`; doctor role check returning 403; calls `DashboardService().get_critical_alerts_count(doctor=request.user)`; serializes with `CriticalAlertsSerializer`; returns 200. Add `CriticalAlertsSerializer` to the serializers import line. (Depends on T001, T002)
- [x] T005 [US1] Add `path('critical-alerts/', views.CriticalAlertsView.as_view(), name='critical-alerts')` to `urlpatterns` in `backend/analytics/urls.py`. (Depends on T004)
- [x] T006 [US1] Create `frontend/src/hooks/useCriticalAlerts.js`: mirror `useDashboardStats` exactly — `useState` for `data/loading/error`, `useEffect` with cancellation flag calling `fetchCriticalAlerts()`, return `{ data, loading, error }`. (Depends on T003)
- [x] T007 [US1] Update `frontend/src/pages/DoctorDashboard.jsx`: (a) add `import { useCriticalAlerts } from '../hooks/useCriticalAlerts'`; (b) add `const { data: alertsData, loading: alertsLoading, error: alertsError } = useCriticalAlerts()` inside the component; (c) update the Alerts `SummaryCard` props: `value={alertsData?.count}`, `subtitle="Patients with 5+ consecutive severe days"`, `loading={alertsLoading}`, `error={Boolean(alertsError)}`. (Depends on T006)

**Checkpoint**: After T007 — restart Django dev server, reload frontend, navigate to dashboard. Alerts card should show the count from the new endpoint. Call `GET /api/analytics/critical-alerts/` directly in Postman/curl to verify the backend independently.

---

## Phase 4: User Story 2 — Simplified Dashboard Layout (Priority: P2)

**Goal**: Remove the 7-day global tremor trend chart and all its associated dead code (backend service method, serializer class, frontend component file, and remaining jsdoc references).

**Independent Test**: Load `/doctor/dashboard` — verify no "7-Day Tremor Trend" heading or chart renders. Open DevTools Network → confirm no request fetches `tremor_trend` data. Verify `GET /api/analytics/dashboard/` response no longer contains `tremor_trend` or `alerts_count` fields (only `total_patients` and `active_devices`).

### Implementation

- [x] T008 [P] [US2] Remove the entire `_build_tremor_trend()` method and the `tremor_trend = self._build_tremor_trend(patients)` call + its return-dict key from `get_dashboard_stats()` in `backend/analytics/services/dashboard.py`. Also remove `Avg` from the `django.db.models` import and remove `TremorMetrics` from the `biometrics.models` import (both are only used by `_build_tremor_trend`). Remove `from django.db.models.functions import TruncDate` if no longer used.
- [x] T009 [P] [US2] Remove `TremorTrendPointSerializer` class entirely and remove the `tremor_trend` field from `DashboardStatsSerializer` in `backend/analytics/serializers.py`.
- [x] T010 [P] [US2] In `frontend/src/pages/DoctorDashboard.jsx`: remove `import TremorTrendChart from '../components/dashboard/TremorTrendChart'` (line 13) and the entire `{/* 7-day tremor trend chart */}` section (the `<div className="mt-8">` block containing the `<h2>` heading and `<TremorTrendChart ... />` element). In `frontend/src/hooks/useDashboardStats.js`: update the `@returns` jsdoc to remove `tremor_trend` and `alerts_count` from the listed data fields.
- [x] T011 [US2] Delete the file `frontend/src/components/dashboard/TremorTrendChart.jsx` — it has no importers after T010 and constitutes dead code per FR-007. (Depends on T010)

**Checkpoint**: After T011 — reload the dashboard. No chart should appear. No `TremorTrendChart` file should exist. `GET /api/analytics/dashboard/` should return only `{ total_patients, active_devices }`.

---

## Phase 5: Polish & Integration Verification

**Purpose**: Confirm both user stories work together end-to-end.

- [x] T012 Verify all 6 quickstart scenarios in `specs/044-smart-alerts-dashboard/quickstart.md` pass: (1) critical alerts count visible on dashboard, (2) count is 0 when no patients qualify, (3) 7-day chart absent and network request eliminated, (4) unauthenticated request returns 401, (5) admin token returns 403, (6) boundary check — 4-day patient returns count 0.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No action — skip
- **Foundational (Phase 2)**: No action — skip
- **US1 (Phase 3)**: No dependencies — can start immediately
- **US2 (Phase 4)**: No dependency on US1 for backend tasks (T008, T009 are independent). T010 and T011 can run after T007 if doing DoctorDashboard in a single pass, or independently since they touch different sections of the file.
- **Polish (Phase 5)**: Depends on Phase 3 AND Phase 4 completion

### User Story Dependencies

- **US1 (Backend service + view + URL, Frontend hook + service + dashboard)**: Fully independent — no dependency on US2
- **US2 (Backend service cleanup, serializer cleanup, frontend component deletion)**: Independent from US1 at the file level. Minor coordination needed for `DoctorDashboard.jsx` — T010 (US2) modifies a different section of the file than T007 (US1), so they can proceed sequentially without conflict.

### Within Phase 3 (US1)

- T001, T002, T003 can run **in parallel** (three different files: services.py, serializers.py, analyticsService.js)
- T004 depends on T001 and T002 (view needs the service method and serializer)
- T005 depends on T004 (URL references the view)
- T006 depends on T003 (hook calls fetchCriticalAlerts)
- T007 depends on T005 and T006 (dashboard card needs both the URL live and the hook ready)

### Within Phase 4 (US2)

- T008, T009, T010 can run **in parallel** (different files: services.py, serializers.py, DoctorDashboard.jsx + useDashboardStats.js)
- T011 depends on T010 (file deletion must follow import removal)

---

## Parallel Execution Examples

### Phase 3 (US1) — 3-way parallel start, then converge

```
# Start simultaneously (3 different files):
T001: Add get_critical_alerts_count() in backend/analytics/services/dashboard.py
T002: Add CriticalAlertsSerializer in backend/analytics/serializers.py
T003: Add fetchCriticalAlerts() in frontend/src/services/analyticsService.js

# After T001 + T002:
T004: Add CriticalAlertsView in backend/analytics/views.py

# After T004:
T005: Add critical-alerts/ URL in backend/analytics/urls.py

# After T003:
T006: Create frontend/src/hooks/useCriticalAlerts.js

# After T005 + T006:
T007: Update DoctorDashboard.jsx — wire Alerts card to useCriticalAlerts()
```

### Phase 4 (US2) — 3-way parallel, then 1 sequential

```
# Start simultaneously (3 different files):
T008: Remove _build_tremor_trend in backend/analytics/services/dashboard.py
T009: Remove TremorTrendPointSerializer in backend/analytics/serializers.py
T010: Remove TremorTrendChart import/JSX in DoctorDashboard.jsx + update useDashboardStats.js jsdoc

# After T010:
T011: Delete frontend/src/components/dashboard/TremorTrendChart.jsx
```

---

## Implementation Strategy

### MVP (User Story 1 Only — Critical Alerts Endpoint + Card)

1. Complete T001–T003 in parallel
2. Complete T004 after T001+T002
3. Complete T005 after T004
4. Complete T006 after T003
5. Complete T007 after T005+T006
6. **STOP and VALIDATE**: Call `/api/analytics/critical-alerts/`, check dashboard card

### Full Feature (Both Stories)

1. Complete Phase 3 (US1) — all 7 tasks
2. Complete Phase 4 (US2) — all 4 tasks in parallel/sequential order
3. T012 — verify all 6 quickstart scenarios

### Total Task Count: 12

| Story | Tasks | Parallelizable |
|-------|-------|----------------|
| US1 — Smart Critical Alerts | 7 (T001–T007) | T001, T002, T003 fully parallel; T004–T007 sequential chain |
| US2 — Layout Simplification | 4 (T008–T011) | T008, T009, T010 fully parallel; T011 sequential after T010 |
| Polish | 1 (T012) | No — requires both stories complete |

---

## Notes

- T001 and T008 both edit `backend/analytics/services/dashboard.py` — done sequentially in different phases, no conflict
- T002 and T009 both edit `backend/analytics/serializers.py` — done sequentially in different phases, no conflict
- T007 and T010 both edit `frontend/src/pages/DoctorDashboard.jsx` — done sequentially (T007 in Phase 3, T010 in Phase 4), no conflict
- No database migrations needed — reads existing `BiometricSession.ml_prediction` JSONField
- No new packages required — DRF `APIView`, `IsAuthenticated`, and React `useState`/`useEffect` are already in use
- `TruncDate` import in `dashboard.py` may be removed in T008 only if `get_critical_alerts_count()` (added in T001) does not also use it — check: T001 uses `TruncDate` in the new method, so the import must be kept
