# Implementation Plan: Staff (Doctor) Management

**Branch**: `047-doctor-management` | **Date**: 2026-06-14 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/047-doctor-management/spec.md`

## Summary

Give center administrators a Staff Management screen to manage doctor accounts. It comprises (1) an admin-only roster table of every doctor showing name, assigned patient count, and account status; (2) an add/edit modal form (name, email, password, status); and (3) a per-row deactivate/reactivate toggle. The backend exposes three admin-only endpoints under `/api/admin/doctors/` (list with `patient_count` annotation, create, and partial-update/toggle), implemented in `authentication/views.py`. No new Django app, model, or migration — the feature reads/writes the existing `CustomUser` (`role='doctor'`, `is_active`) and derives counts from `DoctorPatientAssignment`.

## Technical Context

**Backend Stack**: Django 5.x + Django REST Framework (SimpleJWT)
**Frontend Stack**: React 18 + Vite + Tailwind CSS
**Database**: Supabase PostgreSQL (remote) — no schema change
**Authentication**: JWT (SimpleJWT); new `IsAdmin` permission for admin-only access
**Testing**: Manual via `quickstart.md` (no automated tests requested)
**Project Type**: monorepo (`backend/`, `frontend/`)
**Performance Goals**: Roster loads < 2s for ≤200 doctors (SC-001); single annotated query, no N+1
**Constraints**: Local development only; admin-only feature; no hard delete (status lifecycle only)
**Scale/Scope**: Single center; tens to low-hundreds of doctor accounts

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Monorepo Architecture**: Backend changes in `backend/authentication/`; frontend in `frontend/src/`. ✅
- [x] **Tech Stack Immutability**: Only Django/DRF + React/Tailwind. No new frameworks. ✅
- [x] **Database Strategy**: Supabase PostgreSQL only; no new tables, no migration. ✅
- [x] **Authentication**: JWT via SimpleJWT; new `IsAdmin` permission enforces admin role. ✅
- [x] **Security-First**: No secrets added; passwords hashed via `set_password`/`create_user`, never returned. ✅
- [x] **Real-time Requirements**: None — CRUD over REST; no WebSocket needed. ✅ (N/A)
- [x] **MQTT Integration**: None — no glove/hardware involvement. ✅ (N/A)
- [x] **AI Model Serving**: None — no inference. ✅ (N/A)
- [x] **API Standards**: REST + JSON, snake_case, standard codes (200/201/400/401/403/404), `{ "error": ... }` format. ✅
- [x] **Development Scope**: Local dev only; no Docker/CI/CD. ✅

**Result**: ✅ PASS — no violations, no Complexity Tracking required.

*Post-Phase-1 re-check*: Design adds two generic views, two serializers, one permission class, one `admin_urls.py`, and one main-urls include on the backend; one service, one hook, one page, two components, one route, and an admin-nav update on the frontend. No new apps, models, migrations, or frameworks. **Still ✅ PASS.**

## Project Structure

### Documentation (this feature)

```text
specs/047-doctor-management/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 — 11 technical decisions
├── data-model.md        # Phase 1 — existing-entity usage, API shapes
├── quickstart.md        # Phase 1 — 13 integration scenarios
├── contracts/
│   └── admin-doctors.yaml   # OpenAPI 3.0.3 for the 3 endpoints
└── tasks.md             # Phase 2 — created by /speckit.tasks (NOT here)
```

### Source Code (repository root)

**Backend** (`backend/`):

```text
authentication/
├── serializers.py   # MODIFY: add DoctorListSerializer (read) + DoctorWriteSerializer (create/update)
├── views.py         # MODIFY: add AdminDoctorListCreateView + AdminDoctorDetailView
├── permissions.py   # MODIFY: add IsAdmin permission class
└── admin_urls.py    # CREATE: routes for /admin/doctors/ and /admin/doctors/<id>/

tremoai_backend/
└── urls.py          # MODIFY: add path('api/admin/', include('authentication.admin_urls'))
```

**Frontend** (`frontend/src/`):

```text
services/
└── doctorService.js              # CREATE: listDoctors, createDoctor, updateDoctor
hooks/
└── useDoctors.js                 # CREATE: roster fetch + refresh + pagination/search state
pages/
└── StaffManagementPage.jsx       # CREATE: /admin/doctors page (table + modal host)
components/admin/
├── DoctorManagementTable.jsx     # CREATE: roster table + per-row Edit/toggle actions (6.1, 6.3)
└── DoctorFormModal.jsx           # CREATE: add/edit modal form (6.2)
routes/
└── AppRoutes.jsx                 # MODIFY: lazy import + /admin/doctors ProtectedRoute
utils/
└── roleHelpers.js                # MODIFY: admin menu → Dashboard + Staff(/admin/doctors)
```

**Structure Decision**: TremoAI monorepo. Backend work is confined to the existing `authentication` app (views per the user's instruction); the `/api/admin/` URL prefix is added via a new `admin_urls.py` included from the project urls. Frontend follows the established service → hook → page → component layering, with a new `components/admin/` folder for admin-only UI. See `research.md` Decisions 1, 6, 7, 10.

## Implementation Detail by Component

### Backend

**1. `authentication/permissions.py` — add `IsAdmin`**
```python
class IsAdmin(permissions.BasePermission):
    """Permission class that only allows admins."""
    message = "Only admins can perform this action."

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'admin'
        )
```

**2. `authentication/serializers.py` — two serializers**

- `DoctorListSerializer` (read): fields `id`, `name` (`SerializerMethodField` → `get_full_name()`), `email`, `is_active`, `patient_count` (`IntegerField(read_only=True)` — populated by the view's annotation), `date_joined`.
- `DoctorWriteSerializer` (create/update):
  - Fields: `name` (CharField, write), `email`, `password` (`write_only`, `required=False`, `validators=[validate_password]`), `is_active` (BooleanField, `required=False`).
  - `validate_email`: reject if another `CustomUser` (excluding `self.instance`) has it.
  - `validate`: on create (no `self.instance`), require `name` and `password`.
  - `_split_name(name)`: first token → `first_name`, remainder → `last_name`.
  - `create()`: split name; `CustomUser.objects.create_user(email, password, first_name, last_name, role='doctor', is_active=...)`.
  - `update()`: apply provided name (split), email, `is_active`; if a non-empty `password` is provided, `instance.set_password(password)`; `instance.save()`.
  - Represent the saved instance with `DoctorListSerializer` (re-annotate `patient_count` or default 0 on create).

**3. `authentication/views.py` — two views**
```python
from django.db.models import Count
from .permissions import IsAdmin
# ...
class AdminDoctorListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_queryset(self):
        return (CustomUser.objects.filter(role='doctor')
                .annotate(patient_count=Count('patient_assignments', distinct=True))
                .order_by('first_name', 'last_name', 'id'))

    def get_serializer_class(self):
        return DoctorWriteSerializer if self.request.method == 'POST' else DoctorListSerializer

class AdminDoctorDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    http_method_names = ['get', 'patch']  # no PUT/DELETE

    def get_queryset(self):
        return (CustomUser.objects.filter(role='doctor')
                .annotate(patient_count=Count('patient_assignments', distinct=True)))

    def get_serializer_class(self):
        return DoctorWriteSerializer if self.request.method == 'PATCH' else DoctorListSerializer
```
On create/update, return the read representation (override `create`/`perform_update` or have the write serializer's `to_representation` delegate to `DoctorListSerializer`).

**4. `authentication/admin_urls.py` — new**
```python
from django.urls import path
from .views import AdminDoctorListCreateView, AdminDoctorDetailView

urlpatterns = [
    path('doctors/', AdminDoctorListCreateView.as_view(), name='admin-doctors'),
    path('doctors/<int:pk>/', AdminDoctorDetailView.as_view(), name='admin-doctor-detail'),
]
```

**5. `tremoai_backend/urls.py` — add include**
```python
path('api/admin/', include('authentication.admin_urls')),  # Feature 047: Staff Management
```

### Frontend

**6. `services/doctorService.js`**
```js
import api from './api';
export const listDoctors = async (params = {}) => (await api.get('/admin/doctors/', { params })).data;
export const createDoctor = async (data) => (await api.post('/admin/doctors/', data)).data;
export const updateDoctor = async (id, data) => (await api.patch(`/admin/doctors/${id}/`, data)).data;
```

**7. `hooks/useDoctors.js`** — mirror `usePatients`: state for `doctors`, `totalCount`, `currentPage`, `totalPages`, `loading`, `error`, `search`; a `refresh()` that re-fetches; expose setters. Used by the page to re-render after create/edit/toggle (FR-011).

**8. `components/admin/DoctorManagementTable.jsx`** — props: `doctors`, `loading`, `error`, search + pagination handlers, `onEdit(doctor)`, `onToggleActive(doctor)`. Columns: Name, Patient Count, Status (badge), Actions (Edit + Deactivate/Reactivate). Renders skeleton while loading, empty-state when no doctors (FR-012), error banner on failure (FR-013/Scenario 13).

**9. `components/admin/DoctorFormModal.jsx`** — props: `open`, `mode` (`'add'`/`'edit'`), `initialValues`, `onSubmit`, `onClose`, `loading`, `submitError`. Fixed overlay + centered panel. Fields: name, email, password (placeholder "Leave blank to keep current" in edit mode), status (Active/Inactive select). Client-side validation: required name/email always; required password only in add mode. Maps status select → `is_active` boolean on submit.

**10. `pages/StaffManagementPage.jsx`** — `AppLayout` wrapper; header with doctor count and an **Add Doctor** button; renders `DoctorManagementTable`; manages modal open state and the create/edit/toggle handlers that call `doctorService` then `refresh()`.

**11. `routes/AppRoutes.jsx`** — `const StaffManagementPage = lazy(() => import('../pages/StaffManagementPage'))`; add `<Route path="/admin/doctors" element={<ProtectedRoute><StaffManagementPage /></ProtectedRoute>} />` near the existing `/admin/dashboard` route.

**12. `utils/roleHelpers.js`** — replace `getMenuItems('admin')` mirror with a dedicated admin menu: `Dashboard → /admin/dashboard`, `Staff → /admin/doctors` (icon `Users` / `UserCog` from lucide-react).

## Complexity Tracking

No constitution violations — section intentionally empty.

## Phase Summary

- **Phase 0 (Research)**: ✅ `research.md` — 11 decisions, all unknowns resolved.
- **Phase 1 (Design)**: ✅ `data-model.md`, `contracts/admin-doctors.yaml`, `quickstart.md`, agent context updated.
- **Phase 2 (Tasks)**: ⏭️ Run `/speckit.tasks` to generate `tasks.md`.
