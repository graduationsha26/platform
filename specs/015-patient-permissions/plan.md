# Implementation Plan: Update Patient API Permissions (E-1.4)

**Branch**: `015-patient-permissions` | **Date**: 2026-02-18 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/015-patient-permissions/spec.md`

## Summary

Add admin-role access to the Patient CRUD API. Currently, only `doctor`-role users can access patient endpoints; `admin`-role users are incorrectly blocked. The fix requires: (1) a new `IsDoctorOrAdmin` permission class, (2) updating `PatientViewSet` to use it, (3) updating `get_queryset()` to return all patients for admins, and (4) removing the dead `IsPatient` class. No migrations required — this is a pure Python permission-layer change touching 2 files.

## Technical Context

**Backend Stack**: Django 5.x + Django REST Framework
**Frontend Stack**: React 18+ + Vite + Tailwind CSS (no frontend changes for this feature)
**Database**: Supabase PostgreSQL (remote) — no schema changes
**Authentication**: JWT (SimpleJWT) with roles: `doctor` and `admin`
**Testing**: pytest (backend)
**Project Type**: web (monorepo: `backend/` and `frontend/`)
**Real-time**: N/A — no WebSocket changes
**Integration**: N/A — no MQTT changes
**AI/ML**: N/A — no model changes
**Performance Goals**: No new performance requirements; existing pagination/filtering unchanged
**Constraints**: Local development only; no migrations needed
**Scale/Scope**: 2 files modified; no new endpoints; no schema changes

## Constitution Check

- [x] **Monorepo Architecture**: Feature modifies only `backend/` files — fits monorepo structure
- [x] **Tech Stack Immutability**: No new frameworks; new permission class is plain DRF `BasePermission`
- [x] **Database Strategy**: No database changes — pure code change
- [x] **Authentication**: Still JWT via SimpleJWT; roles remain `doctor` and `admin` per constitution
- [x] **Security-First**: Tightens permissions (adds admin access explicitly); removes dead code; no secrets touched
- [x] **Real-time Requirements**: N/A — no real-time features involved
- [x] **MQTT Integration**: N/A — no sensor data involved
- [x] **AI Model Serving**: N/A — no ML inference involved
- [x] **API Standards**: Same REST endpoints, JSON responses, standard HTTP codes — no changes to API contract shape
- [x] **Development Scope**: Local development only — no deployment config changes

**Result**: ✅ PASS — no violations

## Project Structure

### Documentation (this feature)

```text
specs/015-patient-permissions/
├── spec.md                         ✅ Created
├── plan.md                         ✅ This file
├── research.md                     ✅ Created
├── data-model.md                   ✅ Created
├── quickstart.md                   ✅ Created
├── contracts/
│   └── patient-permissions.yaml   ✅ Created
└── checklists/
    └── requirements.md             ✅ Created
```

### Source Code (files to modify)

```text
backend/
└── authentication/
│   └── permissions.py              MODIFY: add IsDoctorOrAdmin; remove IsPatient
└── patients/
    └── views.py                    MODIFY: import IsDoctorOrAdmin; update permission_classes; update get_queryset()
```

**No other files are modified.** `devices/views.py` keeps `IsDoctor` unchanged — admin device access is a separate concern.

## Implementation Details

### Change 1: `backend/authentication/permissions.py`

**Add** `IsDoctorOrAdmin` class after `IsDoctor`:

```python
class IsDoctorOrAdmin(permissions.BasePermission):
    """Permission class that allows doctors or admins."""
    message = "Only doctors or admins can perform this action."

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role in ('doctor', 'admin')
        )
```

**Remove** `IsPatient` class entirely (lines 19–28). It checks `role == 'patient'`, which no longer exists.

### Change 2: `backend/patients/views.py`

**Update import line**:
```python
# Before:
from authentication.permissions import IsDoctor
# After:
from authentication.permissions import IsDoctorOrAdmin
```

**Update `permission_classes`**:
```python
# Before:
permission_classes = [IsAuthenticated, IsDoctor]
# After:
permission_classes = [IsAuthenticated, IsDoctorOrAdmin]
```

**Update `get_queryset()`** — add admin branch before the doctor branch:
```python
def get_queryset(self):
    user = self.request.user

    if user.role == 'admin':
        return Patient.objects.all().select_related('created_by').prefetch_related('doctor_assignments__doctor')

    if user.role != 'doctor':
        return Patient.objects.none()

    return Patient.objects.filter(
        Q(created_by=user) | Q(doctor_assignments__doctor=user)
    ).distinct().select_related('created_by').prefetch_related('doctor_assignments__doctor')
```

## Dependencies & Execution Order

```
T001 → T002 → T003
```

- **T001**: Add `IsDoctorOrAdmin` + remove `IsPatient` in `permissions.py`
- **T002**: Update `patients/views.py` — import, `permission_classes`, `get_queryset()` (depends on T001 for the new class)
- **T003**: Run `python manage.py check` to confirm zero errors

All tasks are sequential (T001 defines the class; T002 uses it). Total: 3 tasks.
