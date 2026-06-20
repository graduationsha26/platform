# Research: Admin Global Overview

**Branch**: `046-admin-overview` | **Phase**: 0 — Technical Research

---

## Decision 1: Endpoint URL path

**Decision**: `/api/analytics/admin-stats/` (inside the existing `analytics` app)

**Rationale**: The main `tremoai_backend/urls.py` has no `api/admin/` prefix — there is only `api/analytics/`. Adding a new top-level URL prefix solely for a single endpoint would require modifying `tremoai_backend/urls.py` and creating a new URL file. The existing `analytics` app already owns all dashboard and stats views (`DashboardStatsView`, `CriticalAlertsView`, `StatisticsView`). Adding `AdminStatsView` to `analytics/views.py` and routing it at `admin-stats/` inside `analytics/urls.py` follows the existing pattern with zero new infrastructure.

**Alternatives considered**:
- `api/admin/stats/` — requires new prefix in `tremoai_backend/urls.py` and would be served from analytics/views.py anyway; no benefit
- New `admin` Django app — overkill for one endpoint returning two integers

---

## Decision 2: How to count total doctors

**Decision**: `CustomUser.objects.filter(role='doctor').count()`

**Rationale**: The `CustomUser` model in `backend/authentication/models.py` has a `role` CharField with choices `('doctor', 'Doctor')` and `('admin', 'Admin')`. A simple ORM filter on role is a single SQL COUNT query with no joins — the cheapest possible query.

**Alternatives considered**:
- Counting `DoctorPatientAssignment` entries — would return assignment count, not doctor count; duplicates if a doctor has multiple patients
- Using Django's `User.groups` — no groups are configured in this project

---

## Decision 3: How to count total patients

**Decision**: `Patient.objects.count()`

**Rationale**: The spec requires "total patients enrolled in the center." The `Patient` model in `backend/patients/models.py` represents all enrolled patients. A `COUNT(*)` on the full table (no filter) matches the business requirement. Admin sees all patients, not a doctor-scoped subset.

**Alternatives considered**:
- Counting only assigned patients — would miss patients not yet assigned to any doctor
- Counting `DoctorPatientAssignment` entries — duplicates patients assigned to multiple doctors

---

## Decision 4: View placement — no new serializer class

**Decision**: Return a plain dict directly from the view without a custom serializer class

**Rationale**: The response is two integers: `{ "total_doctors": N, "total_patients": N }`. DRF's `Response()` accepts plain dicts and serializes them to JSON natively. Adding a dedicated `AdminStatsSerializer` class provides no validation or transformation benefit for a read-only endpoint returning computed integers. The existing `DashboardStatsSerializer` sets the pattern for simple stats objects, but a dict is even simpler here.

**Alternatives considered**:
- Dedicated serializer — acceptable but unnecessary for two integers
- `DashboardService` extension — DashboardService already handles doctor-scoped stats; admin stats are global and unrelated in logic

---

## Decision 5: Frontend hook and service placement

**Decision**: Add `fetchAdminStats()` to the existing `frontend/src/services/analyticsService.js`; create `frontend/src/hooks/useAdminStats.js` as a standalone hook

**Rationale**: `analyticsService.js` is the natural home for all analytics-family API calls (`fetchDashboardStats`, `fetchCriticalAlerts`, `fetchPatientStats`). The admin stats endpoint is in the `analytics` app — naming consistency is preserved. The hook pattern (`useAdminStats`) mirrors `useDashboardStats` exactly: `useState` for data/loading/error, `useEffect` with cancellation flag.

**Alternatives considered**:
- New `adminService.js` — unnecessary fragmentation for one function
- Inline fetch inside `AdminDashboard.jsx` — violates the hook/service separation pattern used throughout the project

---

## Decision 6: Admin Dashboard page route

**Decision**: Route: `/admin/dashboard` | File: `frontend/src/pages/AdminDashboard.jsx`

**Rationale**: All current doctor pages use `/doctor/*` prefix. An `/admin/dashboard` prefix is the natural mirror. The page file lives alongside `DoctorDashboard.jsx` in `frontend/src/pages/`. The `AppRoutes.jsx` currently has no admin routes — adding the route follows the identical pattern as the doctor dashboard route (lazy import + `ProtectedRoute` wrapper).

**Alternatives considered**:
- `/admin/` redirect — requires a separate home page; overkill for one page
- `/dashboard` shared route — does not support role-based redirects without extra logic

---

## Decision 7: Role enforcement strategy

**Decision**: Backend role check inside the view (`request.user.role != 'admin'` → 403). Frontend `ProtectedRoute` wraps the page (handles 401 redirect).

**Rationale**: The existing pattern in `DashboardStatsView` and `CriticalAlertsView` performs an explicit role check at the top of the view method and returns `HTTP_403_FORBIDDEN`. No change to `ProtectedRoute` is needed — it already redirects unauthenticated users to login. An admin visiting a doctor page (or vice versa) would get a 403 from the backend; the frontend simply shows an error state.

**Alternatives considered**:
- Role-aware `ProtectedRoute` — would require passing a `requiredRole` prop and updating the component; adds frontend complexity for no security benefit (backend enforces it)
- DRF permission class — a custom `IsAdmin` permission class is cleaner at scale but adds a new file for a single endpoint; inline check is consistent with all existing views

---

## Decision 8: No migration required

**Decision**: No database migration needed for this feature.

**Rationale**: No new model fields or tables are created. The counts are derived from existing `CustomUser` (role='doctor') and `Patient` tables. Both are already present in Supabase PostgreSQL.
