# Tasks: Admin Global Overview

**Input**: Design documents from `/specs/046-admin-overview/`
**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅

**Tests**: Not requested — no test tasks generated.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1)

## Path Conventions

- **Backend (Django)**: `backend/analytics/`
- **Frontend (React)**: `frontend/src/`

---

## Phase 1: Setup

> **No action required.** All infrastructure is in place: DRF `APIView`, Django ORM, React hooks, `SummaryCard` component, and the `analyticsService.js` Axios client already exist. No new Django app or database migration is needed.

---

## Phase 2: Foundational

> **No action required.** No new models or migrations — counts are derived from existing `CustomUser` (role='doctor') and `Patient` tables that are already in Supabase PostgreSQL.

---

## Phase 3: User Story 1 — Admin Dashboard Summary Cards (Priority: P1) 🎯 MVP

**Goal**: Add `GET /api/analytics/admin-stats/` (admin-only) returning `{ total_doctors, total_patients }`. Render an Admin Dashboard page at `/admin/dashboard` with two `SummaryCard` components showing those counts.

**Independent Test**: Log in as an admin-role user and navigate to `/admin/dashboard` → verify two metric cards appear ("Total Doctors" and "Total Center Patients") with correct non-negative integers. Call `GET /api/analytics/admin-stats/` with no token → 401. Call with doctor token → 403. Call with admin token → 200 with correct counts.

### Implementation

- [x] T001 [P] [US1] Add `AdminStatsView(APIView)` to `backend/analytics/views.py`: `permission_classes = [IsAuthenticated]`; role check `request.user.role != 'admin'` returning 403 with `{'error': 'Only admins can access the admin stats.'}`; query `CustomUser.objects.filter(role='doctor').count()` for `total_doctors` and `Patient.objects.count()` for `total_patients`; return `{'total_doctors': total_doctors, 'total_patients': total_patients}` with HTTP 200. Add required import: `from authentication.models import CustomUser`.
- [x] T002 [US1] Add `path('admin-stats/', views.AdminStatsView.as_view(), name='admin-stats')` to `urlpatterns` in `backend/analytics/urls.py` before the existing `stats/` route. Add import of `AdminStatsView`. (Depends on T001)
- [x] T003 [P] [US1] Add `fetchAdminStats()` async function (GET `/analytics/admin-stats/`, returns `response.data`) to `frontend/src/services/analyticsService.js` — append after the existing `fetchCriticalAlerts` function.
- [x] T004 [US1] Create `frontend/src/hooks/useAdminStats.js`: mirror `useDashboardStats` exactly — `useState` for `data/loading/error`, `useEffect` with cancellation flag calling `fetchAdminStats()`, return `{ data, loading, error }`. (Depends on T003)
- [x] T005 [US1] Create `frontend/src/pages/AdminDashboard.jsx`: import `useAuth` from `'../hooks/useAuth'`, `AppLayout` from `'../components/layout/AppLayout'`, `SummaryCard` from `'../components/dashboard/SummaryCard'`, `useAdminStats` from `'../hooks/useAdminStats'`; call `useAdminStats()` for `{ data, loading, error }`; render (a) `<AppLayout>` wrapper; (b) `<h1>Admin Dashboard</h1>` heading with welcome line; (c) a 2-column responsive grid `grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6` containing two `<SummaryCard>` components: one with `label="Total Doctors"` `subtitle="Doctors registered in the center"` `value={data?.total_doctors}` `variant="primary"` and one with `label="Total Center Patients"` `subtitle="Patients enrolled across all doctors"` `value={data?.total_patients}` `variant="success"`. Pass `loading={loading}` and `error={Boolean(error)}` to both cards. (Depends on T004)
- [x] T006 [US1] Update `frontend/src/routes/AppRoutes.jsx`: (a) add `const AdminDashboard = lazy(() => import('../pages/AdminDashboard'))` after the existing lazy imports; (b) add a `<Route path="/admin/dashboard" element={<ProtectedRoute><AdminDashboard /></ProtectedRoute>} />` inside `<Routes>` after the existing doctor routes and before the catch-all redirect. (Depends on T005)

**Checkpoint**: After T006 — restart Django dev server, reload frontend. Navigate to `/admin/dashboard` as admin → both cards display correct counts. `GET /api/analytics/admin-stats/` returns correct JSON. Cards show loading skeleton while fetching and error dash if fetch fails.

---

## Phase 4: Polish & Integration Verification

- [x] T007 Verify all 10 quickstart scenarios in `specs/046-admin-overview/quickstart.md` pass: (1) admin sees correct counts on dashboard, (2) endpoint returns correct JSON with admin token, (3) no token → 401, (4) doctor token → 403, (5) zero counts show 0 not blank, (6) loading skeleton visible, (7) API unavailable → error state without crash, (8) admin cannot access doctor stats endpoint, (9) unauthenticated user redirected to login, (10) new doctor added → count updates on refresh.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No action — skip
- **Foundational (Phase 2)**: No action — skip
- **US1 (Phase 3)**: T001 and T003 can start simultaneously (different files). T002 depends on T001. T004 depends on T003. T005 depends on T004. T006 depends on T005.
- **Polish (Phase 4)**: Depends on Phase 3 completion.

### Within Phase 3 (US1)

- T001 and T003 can run **in parallel** (different files: `views.py` vs `analyticsService.js`)
- T002 depends on T001
- T004 depends on T003
- T005 depends on T004
- T006 depends on T005

---

## Parallel Execution Examples

### Phase 3 (US1) — 2-way parallel start, then two converging chains

```
# Start simultaneously (2 different files):
T001: Add AdminStatsView in backend/analytics/views.py
T003: Add fetchAdminStats() in frontend/src/services/analyticsService.js

# After T001:
T002: Add admin-stats/ route in backend/analytics/urls.py

# After T003:
T004: Create useAdminStats.js in frontend/src/hooks/

# After T004:
T005: Create AdminDashboard.jsx in frontend/src/pages/

# After T005:
T006: Register /admin/dashboard route in frontend/src/routes/AppRoutes.jsx
```

---

## Implementation Strategy

### MVP (All tasks — single user story)

1. Run T001 and T003 in parallel
2. Complete T002 after T001
3. Complete T004 after T003
4. Complete T005 after T004
5. Complete T006 after T005
6. T007 — verify all 10 quickstart scenarios

### Total Task Count: 7

| Story | Tasks | Parallelizable |
|-------|-------|----------------|
| US1 — Admin Dashboard Summary Cards | 6 (T001–T006) | T001 and T003 fully parallel; T002→T001, T004→T003, T005→T004, T006→T005 |
| Polish | 1 (T007) | No — requires US1 complete |

---

## Notes

- T001 and T002 both touch `backend/analytics/` — sequential (T001 first)
- T003, T004, T005, T006 touch frontend files — all sequential chain
- T001 and T003 are the only parallel pair: backend view vs. frontend service function
- No Django migration required (Decision 8 in research.md)
- `CustomUser` is imported from `authentication.models` (not `accounts.models`) — the authentication app is at `backend/authentication/`
- URL path is `admin-stats/` (inside the `analytics` app) resolving to `/api/analytics/admin-stats/` — not `/api/admin/stats/` (Decision 1 in research.md)
