# Implementation Plan: Smart Medical Alerts & Dashboard Layout Simplification

**Branch**: `044-smart-alerts-dashboard` | **Date**: 2026-06-14 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/044-smart-alerts-dashboard/spec.md`

## Summary

Two coordinated changes to the doctor dashboard: (1) remove the 7-day global tremor trend chart and all its associated backend/frontend dead code, and (2) replace the old "alerts_count" (24h severe sessions) with a new dedicated `GET /api/analytics/critical-alerts/` endpoint that counts patients whose BiometricSessions carry `ml_prediction.severity = "severe"` on each of the 5 consecutive calendar days ending today. The frontend Alerts metric card is rewired to call the new endpoint via a new `useCriticalAlerts()` hook.

No new models, no migrations, no new packages. 8 files change (4 backend, 4 frontend), 1 file is created (frontend hook), and 1 file is deleted (TremorTrendChart component).

## Technical Context

**Backend Stack**: Django 5.x + Django REST Framework
**Frontend Stack**: React 18+ + Vite + Tailwind CSS
**Database**: Supabase PostgreSQL (remote) — read-only, no migrations needed
**Authentication**: JWT (SimpleJWT) with `IsAuthenticated` + doctor role check
**Testing**: pytest (backend), Jest/Vitest (frontend) — not requested for this feature
**Project Type**: monorepo (backend/, frontend/, firmware/)
**Real-time**: N/A — no WebSocket usage for this feature
**Integration**: N/A — no MQTT/hardware interaction
**AI/ML**: N/A — reads existing `ml_prediction` results; no new inference
**Performance Goals**: API response under 500ms; Python-side aggregation over bounded patient cohort
**Constraints**: Local development only
**Scale/Scope**: Bounded patient cohort per doctor; 2 DB queries for the new endpoint

## Constitution Check

- [x] **Monorepo Architecture**: All changes in `backend/analytics/` and `frontend/src/` — within monorepo
- [x] **Tech Stack Immutability**: No new frameworks or libraries; DRF `APIView` and React hooks already constitutional
- [x] **Database Strategy**: Reads from Supabase PostgreSQL via existing Django ORM; no new DB systems, no migrations
- [x] **Authentication**: New endpoint uses `IsAuthenticated` + doctor role check — same pattern as `DashboardStatsView`
- [x] **Security-First**: No secrets introduced; endpoint protected by JWT; no hardcoded credentials
- [x] **Real-time Requirements**: N/A — feature is a synchronous REST endpoint and a layout removal
- [x] **MQTT Integration**: N/A — no hardware interaction
- [x] **AI Model Serving**: N/A — reads existing ML predictions, does not perform new inference
- [x] **API Standards**: `GET /api/analytics/critical-alerts/` follows REST + JSON, snake_case, standard HTTP codes (200/401/403)
- [x] **Development Scope**: Local development only — no Docker, CI/CD, or production config

**Result**: ✅ PASS — no violations

## Project Structure

### Documentation (this feature)

```text
specs/044-smart-alerts-dashboard/
├── plan.md              # This file
├── research.md          # Phase 0 — 7 decisions documented
├── data-model.md        # Phase 1 — existing entities, no new models
├── quickstart.md        # Phase 1 — 6 integration scenarios
├── contracts/
│   └── critical-alerts.yaml  # OpenAPI spec for GET /api/analytics/critical-alerts/
└── checklists/
    └── requirements.md  # Spec quality checklist (already complete)
```

### Source Code — Files to Modify or Delete

```text
backend/
└── analytics/
    ├── services/
    │   └── dashboard.py       # MODIFY: remove _build_tremor_trend + alerts_count; add get_critical_alerts_count()
    ├── views.py               # MODIFY: add CriticalAlertsView; update DashboardStatsView docstring
    ├── urls.py                # MODIFY: add path('critical-alerts/', ...)
    └── serializers.py         # MODIFY: remove TremorTrendPointSerializer + tremor_trend/alerts_count fields; add CriticalAlertsSerializer

frontend/
└── src/
    ├── services/
    │   └── analyticsService.js        # MODIFY: add fetchCriticalAlerts()
    ├── hooks/
    │   ├── useDashboardStats.js       # MODIFY: update jsdoc (remove tremor_trend/alerts_count mentions)
    │   └── useCriticalAlerts.js       # CREATE: new hook
    ├── pages/
    │   └── DoctorDashboard.jsx        # MODIFY: remove chart; wire Alerts card to useCriticalAlerts()
    └── components/
        └── dashboard/
            └── TremorTrendChart.jsx   # DELETE: no importers after dashboard change
```

**No firmware changes. No new packages. No database migrations.**

## Implementation Detail

### Backend: New service method — `get_critical_alerts_count(doctor)`

**File**: `backend/analytics/services/dashboard.py`

Add to `DashboardService` class after the existing `get_dashboard_stats` method:

```python
def get_critical_alerts_count(self, doctor):
    """
    Count patients with severe tremor sessions on all 5 consecutive days ending today.
    """
    today = timezone.now().date()
    five_days_ago = today - timedelta(days=4)
    patients = Patient.objects.filter(doctor_assignments__doctor=doctor)

    severe_days_qs = (
        BiometricSession.objects
        .filter(
            patient__in=patients,
            session_start__date__gte=five_days_ago,
            session_start__date__lte=today,
            ml_prediction__severity='severe',
        )
        .annotate(day=TruncDate('session_start'))
        .values('patient_id', 'day')
        .distinct()
    )

    patient_severe_days = {}
    for entry in severe_days_qs:
        pid = entry['patient_id']
        patient_severe_days.setdefault(pid, set()).add(entry['day'])

    required_days = {today - timedelta(days=i) for i in range(5)}
    return sum(
        1 for days in patient_severe_days.values()
        if required_days.issubset(days)
    )
```

Also in the same file:
- Remove the `tremor_trend = self._build_tremor_trend(patients)` line from `get_dashboard_stats()`
- Remove `'tremor_trend': tremor_trend` from the return dict
- Remove `alerts_count = BiometricSession.objects.filter(...)` block from `get_dashboard_stats()`
- Remove `'alerts_count': alerts_count` from the return dict
- Delete the entire `_build_tremor_trend()` method
- Remove unused `Avg` import and `TremorMetrics` import if no longer used

Updated `get_dashboard_stats()` return dict:
```python
return {
    'total_patients': total_patients,
    'active_devices': active_devices,
}
```

### Backend: New view — `CriticalAlertsView`

**File**: `backend/analytics/views.py`

Add after `DashboardStatsView`:

```python
class CriticalAlertsView(APIView):
    """
    GET /api/analytics/critical-alerts/

    Returns the count of the authenticated doctor's patients who have had
    at least one severe-classified BiometricSession on each of the 5
    consecutive calendar days ending today.

    Access Control: Doctors only.

    Returns:
        200: { "count": integer >= 0 }
        401: Authentication required
        403: Doctor role required
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'doctor':
            return Response(
                {'error': 'Only doctors can access critical alerts.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        count = DashboardService().get_critical_alerts_count(doctor=request.user)
        serializer = CriticalAlertsSerializer({'count': count})
        return Response(serializer.data, status=status.HTTP_200_OK)
```

Also update `DashboardStatsView` docstring to remove `alerts_count` and `tremor_trend` mentions, and add `CriticalAlertsSerializer` to the imports line.

### Backend: New URL route

**File**: `backend/analytics/urls.py`

Add to urlpatterns:
```python
path('critical-alerts/', views.CriticalAlertsView.as_view(), name='critical-alerts'),
```

### Backend: Serializer changes

**File**: `backend/analytics/serializers.py`

Add new serializer:
```python
class CriticalAlertsSerializer(serializers.Serializer):
    """Response for GET /api/analytics/critical-alerts/"""
    count = serializers.IntegerField(
        min_value=0,
        help_text="Patients with severe tremor readings on all 5 consecutive days ending today"
    )
```

Update `DashboardStatsSerializer` — remove `alerts_count` and `tremor_trend` fields; keep only:
```python
class DashboardStatsSerializer(serializers.Serializer):
    total_patients = serializers.IntegerField(min_value=0, ...)
    active_devices = serializers.IntegerField(min_value=0, ...)
```

Delete `TremorTrendPointSerializer` class entirely.

### Frontend: New service function

**File**: `frontend/src/services/analyticsService.js`

Add:
```js
/**
 * Fetch count of patients with severe tremors on all 5 consecutive days ending today.
 * GET /api/analytics/critical-alerts/
 *
 * @returns {Promise<{ count: number }>}
 */
export async function fetchCriticalAlerts() {
  const response = await api.get('/analytics/critical-alerts/');
  return response.data;
}
```

### Frontend: New hook

**File**: `frontend/src/hooks/useCriticalAlerts.js` (CREATE)

```js
import { useState, useEffect } from 'react';
import { fetchCriticalAlerts } from '../services/analyticsService';

export function useCriticalAlerts() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    fetchCriticalAlerts()
      .then((result) => {
        if (!cancelled) { setData(result); setError(null); }
      })
      .catch(() => {
        if (!cancelled) { setError('Failed to load critical alerts.'); }
      })
      .finally(() => {
        if (!cancelled) { setLoading(false); }
      });
    return () => { cancelled = true; };
  }, []);

  return { data, loading, error };
}
```

### Frontend: Update DoctorDashboard

**File**: `frontend/src/pages/DoctorDashboard.jsx`

Changes:
1. Remove `import TremorTrendChart from '../components/dashboard/TremorTrendChart';` (line 13)
2. Add `import { useCriticalAlerts } from '../hooks/useCriticalAlerts';`
3. Add `const { data: alertsData, loading: alertsLoading, error: alertsError } = useCriticalAlerts();` inside component
4. Update Alerts SummaryCard:
   - `value`: `alertsData?.count` (was `data?.alerts_count`)
   - `subtitle`: `"Patients with 5+ consecutive severe days"` (was `"Severe tremor events (last 24h)"`)
   - `loading`: `alertsLoading` (was `loading`)
   - `error`: `Boolean(alertsError)` (was `hasError`)
5. Remove the entire `{/* 7-day tremor trend chart */}` div block (lines 63-73)

### Frontend: Delete TremorTrendChart component

**File**: `frontend/src/components/dashboard/TremorTrendChart.jsx` — DELETE

After removing the import from DoctorDashboard, this file has no importers. Delete it to satisfy FR-007 (no unused dead code).

## Complexity Tracking

> No constitution violations — this section is not applicable.
