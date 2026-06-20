# Research: Smart Medical Alerts & Dashboard Layout Simplification

**Branch**: `044-smart-alerts-dashboard` | **Date**: 2026-06-14 | **Phase**: 0 — Technical Research

## Decision 1: Severity field to query for consecutive-day detection

**Decision**: Use `BiometricSession.ml_prediction__severity='severe'` — the existing JSON field lookup on `BiometricSession.ml_prediction` (a JSONField storing `{"severity": "...", "confidence": ...}`).

**Rationale**: The existing `DashboardService.get_dashboard_stats()` (line 49-53, `backend/analytics/services/dashboard.py`) already filters `ml_prediction__severity='severe'` successfully against Supabase PostgreSQL. The lookup syntax is proven and stable — no new field or model change is required.

**Alternatives considered**: Using `TremorMetrics.dominant_amplitude` as a proxy for severity was rejected — amplitude is a raw measurement, not a classification. Only `BiometricSession.ml_prediction['severity']` carries the ML severity label.

---

## Decision 2: New dedicated endpoint vs enriching the existing dashboard endpoint

**Decision**: Add a new `GET /api/analytics/critical-alerts/` endpoint (new `CriticalAlertsView` in `views.py`) rather than adding `critical_alerts_count` as a new field to the existing dashboard endpoint.

**Rationale**: The user's spec explicitly requests "consume the new 5-day consecutive severe tremor endpoint." A dedicated endpoint separates concerns, allows the frontend to cache/refetch independently, and avoids expanding the already multi-metric dashboard payload. This also matches the existing pattern where `stats/` and `reports/` are separate endpoints despite sharing the same router.

**Alternatives considered**: Adding the count to `DashboardStatsSerializer` was simpler but conflates two different metric concepts and keeps the chart cleanup entangled with the alerts logic.

---

## Decision 3: Clean removal of alerts_count from dashboard endpoint

**Decision**: Remove `alerts_count` (24h severe sessions count) from `GET /api/analytics/dashboard/` since no frontend component will consume it after this feature. Remove `tremor_trend` for the same reason. This keeps the API surface clean and avoids dead fields.

**Rationale**: After this feature, `DoctorDashboard.jsx` will source the alerts metric from the new `/critical-alerts/` endpoint. The old `alerts_count` would have no consumer. Dead API fields create false contracts for future developers.

**Alternatives considered**: Keeping `alerts_count` for "potential future use" — rejected because unused fields are silent misleads, and the field can always be re-added if needed.

---

## Decision 4: Python-side vs DB-side consecutive-day check

**Decision**: Fetch `(patient_id, date)` distinct pairs for the 5-day window in a single query, then evaluate the consecutive-day constraint in Python.

**Rationale**: PostgreSQL window functions (LAG, RANK over dense date grouping) are the theoretically optimal approach, but they would require raw SQL or a complex ORM expression that is hard to maintain. The patient cohort per doctor is bounded (typically dozens, not millions), so a Python-side aggregation over a small result set is practical and readable. Total queries: 2 (one for patients, one for severe session days).

**Algorithm**:
```
today = current date
required_days = {today, today-1, today-2, today-3, today-4}  # all 5 days must be present

severe_days_qs = BiometricSession
    .filter(patient__in=doctor_patients, session_start__date in [today-4 .. today], ml_prediction.severity == 'severe')
    .annotate(day = TruncDate(session_start))
    .values(patient_id, day)
    .distinct()

patient_severe_days = {patient_id: set(days)}  # built from queryset

count = number of patients where required_days ⊆ patient_severe_days[patient_id]
```

**Alternatives considered**: A raw SQL subquery using `DISTINCT ON (patient_id, DATE(session_start))` followed by a HAVING COUNT = 5 filter was considered but rejected for readability and ORM compatibility.

---

## Decision 5: Frontend hook pattern for critical alerts

**Decision**: Create a new `useCriticalAlerts()` hook in `frontend/src/hooks/useCriticalAlerts.js` mirroring the `useDashboardStats` pattern exactly — fetch on mount, return `{data, loading, error}`.

**Rationale**: `DoctorDashboard.jsx` already uses `useDashboardStats()` for two cards (Patients, Active Devices). Adding a second hook for the third card is consistent with the established pattern and keeps the page component clean. The alternative — calling the API inside `SummaryCard` directly — would make the card stateful and break its pure-presentational contract.

---

## Decision 6: Delete TremorTrendChart.jsx vs just stop importing it

**Decision**: Delete `frontend/src/components/dashboard/TremorTrendChart.jsx` entirely, since it will have no importers after the dashboard change.

**Rationale**: FR-007 explicitly states "leaving no unused dead code." A component file with no importers is dead code. Deleting it prevents confusion for future contributors who might wonder if it's still used somewhere.

**Alternatives considered**: Keeping the file with a "// deprecated" comment — rejected as a dead-code workaround rather than a solution.

---

## Decision 7: Remove TremorTrendPointSerializer and update DashboardStatsSerializer

**Decision**: Remove `TremorTrendPointSerializer` (only used by `DashboardStatsSerializer.tremor_trend`) and update `DashboardStatsSerializer` to remove both `tremor_trend` and `alerts_count` fields.

**Rationale**: Consistent with Decision 3. Serializers that describe non-existent API fields are misleading. The serializer cleanup is part of the dead-code removal required by FR-007's spirit.

---

## Summary: Files Affected

| Layer | File | Change Type |
|-------|------|-------------|
| Backend | `backend/analytics/services/dashboard.py` | MODIFY: remove `_build_tremor_trend` + `alerts_count`; add `get_critical_alerts_count()` |
| Backend | `backend/analytics/views.py` | MODIFY: add `CriticalAlertsView`; update `DashboardStatsView` |
| Backend | `backend/analytics/urls.py` | MODIFY: add `critical-alerts/` route |
| Backend | `backend/analytics/serializers.py` | MODIFY: remove `TremorTrendPointSerializer`, update `DashboardStatsSerializer`, add `CriticalAlertsSerializer` |
| Frontend | `frontend/src/services/analyticsService.js` | MODIFY: add `fetchCriticalAlerts()` |
| Frontend | `frontend/src/hooks/useCriticalAlerts.js` | CREATE: new hook |
| Frontend | `frontend/src/pages/DoctorDashboard.jsx` | MODIFY: remove chart, wire critical alerts card |
| Frontend | `frontend/src/components/dashboard/TremorTrendChart.jsx` | DELETE |
