# Tasks: Dashboard Overview Page

**Input**: Design documents from `/specs/032-dashboard-overview/`
**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅ | quickstart.md ✅

**Tests**: Not requested — no test tasks generated.

**Organization**: Tasks are grouped by user story. The backend API (Phase 2) is foundational — both US1 and US2 consume the same `GET /api/analytics/dashboard/` endpoint, so it must be complete before either frontend story begins.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (no shared file conflicts)
- **[Story]**: Which user story this task belongs to (US1, US2)

---

## Phase 1: Setup

**Purpose**: No dedicated setup needed — the existing monorepo structure accommodates all new files. `backend/analytics/services/` and `frontend/src/{services,hooks,components}` directories already exist.

*No tasks — proceed directly to Phase 2.*

---

## Phase 2: Foundational — Backend API (Blocking Prerequisite)

**Purpose**: Implement `GET /api/analytics/dashboard/` endpoint that returns all four metrics (`total_patients`, `active_devices`, `alerts_count`, `tremor_trend`). Both US1 and US2 depend on this endpoint.

**⚠️ CRITICAL**: No frontend user story work can begin until this phase is complete.

- [x] T001 Implement `DashboardService` class with `get_dashboard_stats(doctor)` method in `backend/analytics/services/dashboard.py`. Method must: (1) query `Patient` objects via `doctor_assignments__doctor=doctor`; (2) count patients; (3) count `Device` objects with `patient__in=patients, status='online'`; (4) count `BiometricSession` objects with `patient__in=patients`, `session_start__gte=now()-24h`, `ml_prediction__severity='severe'`; (5) aggregate `TremorMetrics.dominant_amplitude` grouped by `TruncDate('window_start')` over last 7 days; (6) build a fixed-length 7-entry list (D-6 to D+0) filling missing days with `avg_amplitude: None`.

- [x] T002 Add `TremorTrendPointSerializer` (fields: `date`, `avg_amplitude`) and `DashboardStatsSerializer` (fields: `total_patients`, `active_devices`, `alerts_count`, `tremor_trend`) to `backend/analytics/serializers.py`. `avg_amplitude` must allow `null`. Serializers are read-only (no `create`/`update` needed).

- [x] T003 Add `DashboardStatsView(APIView)` to `backend/analytics/views.py`. Apply `IsAuthenticated` + `IsDoctor` permissions. In `get()`, call `DashboardService().get_dashboard_stats(request.user)`, serialize with `DashboardStatsSerializer`, return `Response(serializer.data)`. Return 403 with `{"error": "..."}` if permission fails.

- [x] T004 Register the dashboard route in `backend/analytics/urls.py`: add `path('dashboard/', DashboardStatsView.as_view(), name='dashboard-stats')`.

**Checkpoint**: Backend is complete. Verify with `curl -H "Authorization: Bearer <token>" http://localhost:8000/api/analytics/dashboard/` — expect 200 with all four fields and exactly 7 tremor_trend entries. US1 and US2 frontend work can now begin in parallel.

---

## Phase 3: User Story 1 — View System Summary at a Glance (Priority: P1) 🎯 MVP

**Goal**: Replace the three "--" placeholder cards in `DoctorDashboard.jsx` with live data fetched from the dashboard endpoint. Doctor sees total patients, active devices, and alerts count immediately on page load.

**Independent Test**: Log in as a doctor, navigate to `/doctor/dashboard`. All three summary cards render with numeric values (or "0" when no data). Cards show a loading spinner while data is fetching and an error indicator if the request fails — without crashing the page.

### Implementation for User Story 1

- [x] T005 [P] Create `frontend/src/services/analyticsService.js`. Export a single function `fetchDashboardStats()` that calls `GET /api/analytics/dashboard/` via the existing `api` Axios instance (imported from `./api.js`). Returns the response data object directly. No params needed — the backend scopes to the authenticated doctor automatically.

- [x] T006 [P] Create `frontend/src/components/dashboard/SummaryCard.jsx`. Accept props: `label` (string), `value` (number | null), `loading` (bool), `error` (bool). When `loading=true` render a skeleton/spinner placeholder in place of the value. When `error=true` render "—" with a muted error indicator. Otherwise render the numeric value. Style with Tailwind (white card, rounded, shadow, centered value, muted label beneath). No onClick or interactivity needed.

- [x] T007 Create `frontend/src/hooks/useDashboardStats.js` (depends on T005). Export `useDashboardStats()` hook. On mount, call `fetchDashboardStats()`. Return `{ data, loading, error }` where `data` is the full response object (`total_patients`, `active_devices`, `alerts_count`, `tremor_trend`), `loading` starts true and becomes false after fetch resolves, and `error` is a string message or null. Handle both network errors and non-2xx HTTP responses. No polling or refresh mechanism needed.

- [x] T008 Update `frontend/src/pages/DoctorDashboard.jsx` (depends on T006, T007). Import `useDashboardStats` and `SummaryCard`. Replace the three existing placeholder stat cards with three `<SummaryCard>` instances wired to `data.total_patients`, `data.active_devices`, and `data.alerts_count`. Pass `loading` and `error` props from the hook state. Preserve the existing 3-column responsive Tailwind grid layout.

**Checkpoint**: User Story 1 is complete and independently testable. The summary cards section works end-to-end. US2 (chart) can now begin.

---

## Phase 4: User Story 2 — View 7-Day Tremor Trend (Priority: P2)

**Goal**: Add a 7-day tremor trend line chart below the summary cards in `DoctorDashboard.jsx`. The chart renders daily average tremor amplitude for the past 7 days, with an empty state when no data exists and an error state when the fetch fails.

**Independent Test**: With tremor data in the database, navigate to `/doctor/dashboard`. A line chart renders below the cards with labeled x-axis dates and a plotted amplitude line. With no data, a "No tremor data available" message appears in the chart area. This story can be tested independently of US1 by commenting out the card section.

### Implementation for User Story 2

- [x] T009 Create `frontend/src/components/dashboard/TremorTrendChart.jsx`. Accept props: `data` (array of `{date, avg_amplitude}` | null), `loading` (bool), `error` (bool). Use Recharts `ResponsiveContainer`, `LineChart`, `XAxis`, `YAxis`, `Tooltip`, and `Line` — follow the pattern in `frontend/src/components/CMG/SuppressionEffectivenessChart.jsx` for import style and component structure. Format `date` values on the x-axis as short date strings (e.g., "Feb 14"). When `loading=true` render a skeleton placeholder. When `error=true` render "Unable to load trend data. Please refresh." in the chart area. When `data` is present but all `avg_amplitude` values are `null`, render "No tremor data available." in the chart area. Otherwise render the line chart, connecting only non-null data points (use `connectNulls={false}`).

- [x] T010 Update `frontend/src/pages/DoctorDashboard.jsx` (depends on T009). Import `TremorTrendChart`. Add a section below the summary cards grid containing a heading (e.g., "7-Day Tremor Trend") and the `<TremorTrendChart>` component. Pass `data={data?.tremor_trend}`, `loading`, and `error` from the already-imported `useDashboardStats` hook. No additional API call needed — the same hook instance provides the trend data.

**Checkpoint**: User Story 2 is complete. Both summary cards and the 7-day trend chart render with live data, loading states, and error states. Full dashboard overview is functional.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [x] T011 [P] Validate the dashboard page against all four scenarios in `specs/032-dashboard-overview/quickstart.md`: full data, no patients, endpoint unavailable, and unauthenticated access. Fix any deviations from the specified behaviour.

- [x] T012 [P] Verify the `GET /api/analytics/dashboard/` response structure matches the OpenAPI contract in `specs/032-dashboard-overview/contracts/dashboard-stats.yaml`: correct field names (snake_case), correct types, `tremor_trend` always has exactly 7 entries, `avg_amplitude` can be null.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Foundational (Phase 2)**: No dependencies — start immediately
- **US1 (Phase 3)**: Depends on Phase 2 completion (needs the real API to validate)
- **US2 (Phase 4)**: Depends on Phase 2 completion AND Phase 3 completion (shares the same `DoctorDashboard.jsx` — avoid merge conflicts)
- **Polish (Phase 5)**: Depends on Phase 3 + Phase 4 completion

### Within Phase 2 (Backend — sequential)

```
T001 (Service) → T002 (Serializer) → T003 (View) → T004 (URL)
```

### Within Phase 3 (US1 — partial parallel)

```
T005 [P] ─┐
           ├─→ T007 (Hook) → T008 (Page wiring)
T006 [P] ─┘
```

### Within Phase 4 (US2 — sequential)

```
T009 (Chart component) → T010 (Page wiring)
```

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2 — no dependency on US2
- **US2 (P2)**: Can start after Phase 2 — no dependency on US1 (uses same hook, different component). Editing `DoctorDashboard.jsx` in T010 must happen after T008 to avoid conflicts

---

## Parallel Execution Examples

### Phase 2 (Backend — fully sequential, no parallel opportunities)
```
Run in order: T001 → T002 → T003 → T004
```

### Phase 3 (US1 — two parallel tracks merge at T007)
```
Track A: T005 (analyticsService.js)  ─┐
                                        ├→ T007 (hook) → T008 (page)
Track B: T006 (SummaryCard.jsx)      ─┘
```

### Polish (Phase 5 — both tasks parallel)
```
T011 [P] (quickstart validation)
T012 [P] (contract validation)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 2: Backend API (T001–T004)
2. Complete Phase 3: US1 Summary Cards (T005–T008)
3. **STOP and VALIDATE**: Log in as doctor, confirm three live cards render with correct counts
4. Deliver MVP — dashboard is operational with summary metrics

### Incremental Delivery

1. Phase 2 complete → API ready
2. Phase 3 complete → Summary cards live (MVP ✅)
3. Phase 4 complete → Trend chart added ✅
4. Phase 5 complete → All edge cases validated ✅

---

## Notes

- [P] tasks = different files, no dependencies — safe to implement concurrently
- No new DB models — all queries use existing `Patient`, `Device`, `BiometricSession`, `TremorMetrics`
- `useDashboardStats` hook is shared between US1 and US2 — instantiate it once in `DoctorDashboard.jsx`
- `TremorTrendChart` receives `null` avg_amplitude values gracefully — chart must not crash on nulls
- The `api.js` Axios instance already handles JWT injection and 401 redirects — no auth logic needed in `analyticsService.js`
- `DoctorPatientAssignment` is the scoping mechanism — doctors only see their own patients' data
