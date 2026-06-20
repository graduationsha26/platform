# Implementation Plan: Personalized Doctor Dashboard Greeting

**Branch**: `001-doctor-greeting` | **Date**: 2026-06-14 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/001-doctor-greeting/spec.md`

## Summary

Add a personalized greeting to the doctor dashboard header by (1) fixing a broken field reference in `TopBar.jsx` that references `user?.name` instead of the stored `user.first_name`/`user.last_name`, and (2) adding a missing `GET /api/auth/me/` endpoint to `backend/authentication/` that returns the authenticated doctor's profile. The frontend already has the name data in the auth context from the login response; only two files require changes — one backend and one frontend.

## Technical Context

**Backend Stack**: Django 5.x + Django REST Framework  
**Frontend Stack**: React 18+ + Vite + Tailwind CSS  
**Database**: Supabase PostgreSQL (remote) — no migrations required  
**Authentication**: JWT (SimpleJWT) with `IsAuthenticated` permission  
**Testing**: pytest (backend), Jest/Vitest (frontend)  
**Project Type**: monorepo (backend/, frontend/, firmware/)  
**Real-time**: Not applicable — no WebSocket usage for this feature  
**Integration**: Not applicable — no MQTT/hardware interaction  
**AI/ML**: Not applicable  
**Performance Goals**: Greeting must appear within the same page load as the dashboard (no secondary network request required for the greeting itself)  
**Constraints**: Local development only  
**Scale/Scope**: Affects all doctor accounts; tiny scope — 2 files changed, no new models or migrations

## Constitution Check

- [x] **Monorepo Architecture**: Changes confined to `backend/authentication/` and `frontend/src/components/layout/` — within the monorepo structure
- [x] **Tech Stack Immutability**: No new frameworks or libraries; DRF `APIView` and React are already in use
- [x] **Database Strategy**: No new database access patterns; `UserSerializer` reads the already-existing `CustomUser` via the ORM
- [x] **Authentication**: New endpoint uses `IsAuthenticated` (JWT); TopBar reads from existing auth context
- [x] **Security-First**: No secrets introduced; endpoint is protected by JWT token; no hardcoded values
- [x] **Real-time Requirements**: N/A — feature does not require real-time data
- [x] **MQTT Integration**: N/A — no hardware interaction
- [x] **AI Model Serving**: N/A — no ML models
- [x] **API Standards**: GET /api/auth/me/ follows REST + JSON, snake_case keys, standard HTTP codes (200/401)
- [x] **Development Scope**: Local development only — no Docker, CI/CD, or production config changes

**Result**: ✅ PASS — no violations

## Project Structure

### Documentation (this feature)

```text
specs/001-doctor-greeting/
├── plan.md              # This file
├── research.md          # Phase 0 — research findings
├── data-model.md        # Phase 1 — entity definitions
├── quickstart.md        # Phase 1 — integration scenarios
├── contracts/
│   └── auth-me.yaml     # Phase 1 — OpenAPI contract for GET /api/auth/me/
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (from /speckit.tasks — not yet created)
```

### Source Code (files to create or modify)

```text
backend/
└── authentication/
    ├── views.py          # MODIFY: add MeView class
    └── urls.py           # MODIFY: add path('me/', MeView.as_view(), name='auth-me')

frontend/
└── src/
    └── components/
        └── layout/
            └── TopBar.jsx  # MODIFY: fix user?.name → formatted name from first_name + last_name; add greeting
```

**No new files** need to be created in the source tree. No database migrations. No new packages.

## Implementation Detail

### Backend: Add GET /api/auth/me/ endpoint

**File**: `backend/authentication/views.py`

Add a new `MeView` class after the existing views:

```python
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)
```

**File**: `backend/authentication/urls.py`

Add the route:

```python
from .views import RegisterView, CustomTokenObtainPairView, MeView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='auth-register'),
    path('login/', CustomTokenObtainPairView.as_view(), name='auth-login'),
    path('refresh/', TokenRefreshView.as_view(), name='auth-refresh'),
    path('me/', MeView.as_view(), name='auth-me'),
]
```

### Frontend: Fix TopBar personalized greeting

**File**: `frontend/src/components/layout/TopBar.jsx`

Current broken line (line 40):
```jsx
<p className="text-sm font-medium text-neutral-900">{user?.name}</p>
```

Replace with a computed full name and add greeting context:
```jsx
const fullName = user ? `Dr. ${user.first_name} ${user.last_name}`.trim() : 'Doctor';
// ...
<p className="text-sm font-medium text-neutral-900">{fullName}</p>
```

The role sub-label (line 41) already reads `user?.role` and remains unchanged.

## Complexity Tracking

> No constitution violations — this section is not applicable.
