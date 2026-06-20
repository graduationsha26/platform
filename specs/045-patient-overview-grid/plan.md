# Implementation Plan: Patient Overview Grid

**Branch**: `045-patient-overview-grid` | **Date**: 2026-06-14 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/045-patient-overview-grid/spec.md`

## Summary

Replace the vacated dashboard section (left by the removed TremorTrendChart) with a Patient Overview Grid. The grid displays one card per assigned patient, showing their avatar photo (or initials fallback), full name, and an online/offline badge derived from device telemetry recency (last_seen < 60 s = online). Each card provides "View Profile" and "Live Monitor" quick-action links. The backend adds a new `GET /api/patients/overview/` endpoint in the existing patients app, and a `avatar_url` field is added to the Patient model.

## Technical Context

**Backend Stack**: Django 5.x + Django REST Framework
**Frontend Stack**: React 18+ + Vite + Tailwind CSS
**Database**: Supabase PostgreSQL (remote) — migrations required for avatar_url field
**Authentication**: JWT (SimpleJWT) — doctor role enforced at endpoint level
**Testing**: Not requested — no test tasks generated
**Project Type**: monorepo (backend/, frontend/)
**Real-time**: Not required — grid reflects state at page load, no WebSocket
**MQTT**: Not involved — this feature reads stored data only
**AI/ML**: Not involved
**Performance Goals**: Patient list loads within 2 seconds; single DB query using ORM annotation
**Constraints**: Local development only; Supabase PostgreSQL remote connection required

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Monorepo Architecture**: Backend changes in `backend/patients/`, frontend changes in `frontend/src/`
- [x] **Tech Stack Immutability**: No new frameworks — uses DRF APIView, React, Tailwind (all existing)
- [x] **Database Strategy**: Uses Supabase PostgreSQL; migration adds nullable URLField to existing Patient table
- [x] **Authentication**: `IsAuthenticated` + doctor role check (403 for admin); JWT via SimpleJWT
- [x] **Security-First**: No new secrets; no hardcoded credentials; existing `.env` config unchanged
- [x] **Real-time Requirements**: Feature explicitly does NOT require real-time (page-load snapshot per spec assumption)
- [x] **MQTT Integration**: Not involved — read-only patient/device data endpoint
- [x] **AI Model Serving**: Not involved
- [x] **API Standards**: REST GET, JSON response, snake_case keys, standard HTTP codes (200/401/403)
- [x] **Development Scope**: Local dev only — `python manage.py runserver` + `npm run dev`

**Result**: ✅ PASS — all 10 gates clear

## Project Structure

### Documentation (this feature)

```text
specs/045-patient-overview-grid/
├── plan.md              ← this file
├── research.md          ← Phase 0 (complete)
├── data-model.md        ← Phase 1 (complete)
├── quickstart.md        ← Phase 1 (complete)
├── contracts/
│   └── patients-overview.yaml   ← Phase 1 (complete)
└── tasks.md             ← Phase 2 (via /speckit.tasks — not yet created)
```

### Source Code Changes

```text
backend/
└── patients/
    ├── models.py            MODIFY — add avatar_url URLField to Patient
    ├── migrations/
    │   └── 000X_patient_avatar_url.py   CREATE — Django migration for avatar_url
    ├── serializers.py       MODIFY — add PatientOverviewItemSerializer
    └── views.py             MODIFY — add PatientsOverviewView(APIView)
    └── urls.py              MODIFY — add path('overview/', ...)

frontend/
└── src/
    ├── services/
    │   └── patientService.js       MODIFY — add fetchPatientsOverview()
    ├── hooks/
    │   └── usePatientsOverview.js  CREATE — new hook (mirrors useCriticalAlerts pattern)
    ├── components/
    │   └── dashboard/
    │       ├── PatientCard.jsx         CREATE — avatar/initials, name, badge, 2 buttons
    │       └── PatientOverviewGrid.jsx CREATE — grid layout + empty/error states
    └── pages/
        └── DoctorDashboard.jsx     MODIFY — import and render PatientOverviewGrid below cards
```

## Implementation Details

### Backend: Patient model (backend/patients/models.py)

Add field to the Patient class:
```python
avatar_url = models.URLField(max_length=500, blank=True, default='')
```

### Backend: Migration

Run after model change:
```
python manage.py makemigrations patients --name patient_avatar_url
python manage.py migrate
```

### Backend: Serializer (backend/patients/serializers.py)

```python
class PatientOverviewItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    full_name = serializers.CharField()
    avatar_url = serializers.CharField(default='')
    device_online = serializers.BooleanField()
```

### Backend: View (backend/patients/views.py)

```python
from datetime import timedelta
from django.db.models import Max
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Patient
from .serializers import PatientOverviewItemSerializer

class PatientsOverviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'doctor':
            return Response(
                {'error': 'Only doctors can access the patients overview.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        threshold = timezone.now() - timedelta(seconds=60)
        patients = (
            Patient.objects
            .filter(doctor_assignments__doctor=request.user)
            .annotate(latest_device_seen=Max('devices__last_seen'))
            .order_by('full_name')
        )
        results = []
        for patient in patients:
            results.append({
                'id': patient.id,
                'full_name': patient.full_name,
                'avatar_url': patient.avatar_url or '',
                'device_online': (
                    patient.latest_device_seen is not None
                    and patient.latest_device_seen >= threshold
                ),
            })
        serializer = PatientOverviewItemSerializer(results, many=True)
        return Response(
            {'count': len(results), 'results': serializer.data},
            status=status.HTTP_200_OK,
        )
```

### Backend: URL (backend/patients/urls.py)

```python
path('overview/', views.PatientsOverviewView.as_view(), name='patients-overview'),
```

### Frontend: patientService.js

```js
export async function fetchPatientsOverview() {
  const response = await api.get('/patients/overview/');
  return response.data;
}
```

### Frontend: usePatientsOverview.js

```js
import { useState, useEffect } from 'react';
import { fetchPatientsOverview } from '../services/patientService';

export function usePatientsOverview() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    fetchPatientsOverview()
      .then((result) => { if (!cancelled) { setData(result); setError(null); } })
      .catch(() => { if (!cancelled) { setError('Failed to load patient overview.'); } })
      .finally(() => { if (!cancelled) { setLoading(false); } });
    return () => { cancelled = true; };
  }, []);

  return { data, loading, error };
}
```

### Frontend: PatientCard.jsx (frontend/src/components/dashboard/PatientCard.jsx)

Key logic — initials derivation:
```js
function getInitials(fullName) {
  const words = (fullName || '').trim().split(/\s+/);
  return words.slice(0, 2).map(w => w[0]?.toUpperCase() || '').join('');
}
```

Card renders:
- Avatar circle: `avatar_url` → `<img>` with `onError` fallback to initials div; or initials div directly if `avatar_url` is empty
- Full name text
- Online/offline badge: green "Online" pill or grey "Offline" pill based on `device_online`
- Two buttons: "View Profile" (`<Link to={`/doctor/patients/${patient.id}`}>`) and "Live Monitor" (`<Link to={`/doctor/patients/${patient.id}/monitor`}>`)

### Frontend: PatientOverviewGrid.jsx (frontend/src/components/dashboard/PatientOverviewGrid.jsx)

Renders:
- Loading state: skeleton/spinner while `loading=true`
- Error state: error message div when `error` is set
- Empty state: message "No patients assigned yet." when `data.count === 0`
- Grid: `grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4` wrapping one `PatientCard` per patient

### Frontend: DoctorDashboard.jsx

Add below the existing summary cards grid div:
```jsx
import PatientOverviewGrid from '../components/dashboard/PatientOverviewGrid';

// In JSX, after the grid of 3 summary cards:
<div className="mt-8">
  <h2 className="text-xl font-semibold text-neutral-900 mb-4">Your Patients</h2>
  <PatientOverviewGrid />
</div>
```

`PatientOverviewGrid` manages its own data fetching via `usePatientsOverview` internally.

## Complexity Tracking

No constitution violations. No complexity tracking required.
