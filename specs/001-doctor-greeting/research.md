# Research: Personalized Doctor Dashboard Greeting

**Branch**: `001-doctor-greeting` | **Date**: 2026-06-14  
**Phase**: 0 — Research & Unknowns Resolution

## Findings

### 1. User Model & Fields

**Decision**: No model changes required.  
**Rationale**: `CustomUser` inherits from Django's `AbstractUser` which already has `first_name` and `last_name`. Both are required at registration (`RegisterSerializer` marks them `required=True`). Every doctor account in the system has these fields populated.  
**Alternatives considered**: Adding a separate `display_name` computed field — rejected as unnecessary given `first_name`/`last_name` already exist and are required.

---

### 2. Data Already Available in Frontend Auth Context

**Decision**: No new API call needed to populate the greeting on page load.  
**Rationale**: The login response (`POST /api/auth/login/`) returns:
```json
{
  "access": "...",
  "user": { "id", "email", "first_name", "last_name", "role", "date_joined", "last_login" }
}
```
`AuthContext.jsx` stores this full `user` object in both React state and `localStorage` (`storeUser(userData)`). On page refresh, `initializeAuth()` re-hydrates from storage. Therefore `user.first_name` and `user.last_name` are already available in every component that calls `useAuth()`.

**Implication**: The TopBar fix is purely a field-reference correction (`user?.name` → computed from `user?.first_name` and `user?.last_name`). No new network request is needed.

---

### 3. The Broken Field Reference in TopBar

**Decision**: Replace `user?.name` with `${user?.first_name} ${user?.last_name}`.  
**Rationale**: The `UserSerializer` never serializes a `name` field — only `first_name` and `last_name` as separate fields. The TopBar (`frontend/src/components/layout/TopBar.jsx`, line 40) references `user?.name`, which is always `undefined`. This is a bug.  
**Correct approach**: Concatenate `first_name` and `last_name` inline, or derive a `fullName` local variable within the component. No computed property needs to be added to the serializer or context.

---

### 4. GET /api/auth/me/ Endpoint — Missing

**Decision**: Add a `MeView` class to `backend/authentication/views.py` using DRF's `APIView`, protected by `IsAuthenticated`.  
**Rationale**: While the frontend can currently work from the login response, the spec requires this endpoint to exist so the frontend has a canonical way to fetch the current user's profile (e.g., after a hard refresh where the token is still valid but the stored `user` object needs re-validation). It also fulfills FR-001 and FR-005.  
**Implementation approach**: Re-use the existing `UserSerializer` — no new serializer needed. Returning `UserSerializer(request.user).data` with HTTP 200 is sufficient.  
**Alternatives considered**:
- Decoding `first_name`/`last_name` from the JWT payload on the frontend — rejected because it couples the frontend to the JWT structure and bypasses server-side truth.
- A separate `ProfileSerializer` — rejected as overkill; `UserSerializer` already serializes all needed fields.

---

### 5. Greeting Copy / Format

**Decision**: Display the doctor's full name inline in the TopBar user-info block, replacing the broken reference. Add a short greeting prefix ("Dr.") for a professional feel.  
**Rationale**: The spec does not mandate a specific greeting phrase — only that the name is present and correct. Using "Dr. [First] [Last]" is a standard medical-platform convention. The role sub-label below already says "doctor", so pairing it with "Dr." is coherent.  
**Alternatives considered**: Time-based salutation ("Good morning / afternoon / evening") — adds minor complexity with no functional benefit; deferred if desired as a future enhancement.

---

## Summary of Decisions

| # | Topic | Decision |
|---|-------|----------|
| 1 | User model changes | None required — fields already exist |
| 2 | Frontend data source | Use existing `user` from AuthContext (no extra API call on render) |
| 3 | TopBar field bug | Replace `user?.name` with computed full name from `first_name` + `last_name` |
| 4 | GET /api/auth/me/ | Add `MeView` to views.py + wire in urls.py, reuse `UserSerializer` |
| 5 | Greeting format | "Dr. [First] [Last]" in TopBar name display area |
