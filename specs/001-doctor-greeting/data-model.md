# Data Model: Personalized Doctor Dashboard Greeting

**Branch**: `001-doctor-greeting` | **Date**: 2026-06-14

## Overview

This feature introduces no new database entities. All required data already exists in the `CustomUser` model. This document describes the relevant existing entity and the client-side representation used by the frontend.

---

## Entity: CustomUser (existing)

**Table**: `authentication_customuser` (Django-managed via Supabase PostgreSQL)  
**File**: `backend/authentication/models.py`

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| id | UUID / int | AbstractUser | Primary key |
| email | CharField | CustomUser | Primary identifier (unique) |
| first_name | CharField | AbstractUser | Required at registration |
| last_name | CharField | AbstractUser | Required at registration |
| role | CharField | CustomUser | Choices: `doctor` \| `admin` |
| date_joined | DateTimeField | AbstractUser | Auto-set |
| last_login | DateTimeField | AbstractUser | Auto-updated |

**No schema migrations required.** All fields are already present.

---

## Serialization: UserSerializer (existing, no changes)

**File**: `backend/authentication/serializers.py`

The existing `UserSerializer` already serializes all required fields:

```
fields = ['id', 'email', 'first_name', 'last_name', 'role', 'date_joined', 'last_login']
```

The `/api/auth/me/` endpoint will reuse this serializer directly.

---

## Client-Side: Auth Context User Object

**File**: `frontend/src/contexts/AuthContext.jsx`

The `user` object stored in React state and `localStorage` after login already contains:

```json
{
  "id": 1,
  "email": "doctor@example.com",
  "first_name": "Ahmed",
  "last_name": "Hassan",
  "role": "doctor",
  "date_joined": "2026-01-01T00:00:00Z",
  "last_login": "2026-06-14T10:00:00Z"
}
```

The TopBar will read `user.first_name` and `user.last_name` from the `useAuth()` hook to construct the displayed name — no new context fields or provider changes are needed.

---

## No New Entities

| Considered | Decision | Reason |
|------------|----------|--------|
| `display_name` computed field on User | Rejected | `first_name` + `last_name` concatenation sufficient; no storage needed |
| Separate `DoctorProfile` model | Rejected | Out of scope; all needed data lives on `CustomUser` |
