# Tasks: Personalized Doctor Dashboard Greeting

**Input**: Design documents from `/specs/001-doctor-greeting/`  
**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅

**Tests**: Not requested — no test tasks generated.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)

## Path Conventions

- **Backend (Django)**: `backend/authentication/`
- **Frontend (React)**: `frontend/src/components/layout/`

---

## Phase 1: Setup

> **No action required.** No new packages, project structure, or initialization is needed. The auth infrastructure (`CustomUser`, `UserSerializer`, `AuthContext`, `useAuth`) is already in place. Proceed directly to user story phases.

---

## Phase 2: Foundational

> **No action required.** No cross-story blocking prerequisites exist. Each user story targets a different file and different layer (frontend vs. backend). Both can start immediately in parallel.

---

## Phase 3: User Story 1 — Personalized Greeting in Dashboard Header (Priority: P1) 🎯 MVP

**Goal**: Fix the broken name reference in `TopBar.jsx` and render the doctor's full name as a personalized greeting using the `first_name` and `last_name` already available in the auth context.

**Independent Test**: Log in as any doctor → navigate to `/doctor/dashboard` → verify the TopBar shows "Dr. [First] [Last]" and the role sub-label. Refresh the page and verify the greeting persists without re-login.

### Implementation

- [x] T001 [US1] Replace `user?.name` with a computed `fullName` constant derived from `user?.first_name` and `user?.last_name`, add "Dr." prefix and "Doctor" fallback, and render it in the user-info block in `frontend/src/components/layout/TopBar.jsx`

**Checkpoint**: After T001 — navigate to the doctor dashboard, confirm the TopBar shows the correct doctor name. Confirm the role sub-label still shows. Confirm refreshing the page keeps the greeting.

---

## Phase 4: User Story 2 — Auth Endpoint Returns Doctor Name Fields (Priority: P1)

**Goal**: Add `GET /api/auth/me/` endpoint that returns the authenticated doctor's profile (including `first_name` and `last_name`) and rejects unauthenticated requests.

**Independent Test**: Call `GET /api/auth/me/` with a valid JWT access token → verify the response includes `first_name` and `last_name`. Call without a token → verify 401 response.

### Implementation

- [x] T002 [P] [US2] Add `MeView` class (extending `APIView` with `IsAuthenticated` permission) that returns `UserSerializer(request.user).data` in `backend/authentication/views.py`
- [x] T003 [US2] Import `MeView` and add `path('me/', MeView.as_view(), name='auth-me')` to `urlpatterns` in `backend/authentication/urls.py` (depends on T002)

**Checkpoint**: After T003 — restart Django dev server, call `GET /api/auth/me/` with and without a token (use curl or Postman), confirm 200 with `first_name`/`last_name` when authenticated and 401 when not.

---

## Phase 5: Polish & Integration Verification

**Purpose**: Confirm both user stories work together end-to-end per quickstart scenarios.

- [x] T004 Verify all four quickstart scenarios in `specs/001-doctor-greeting/quickstart.md` pass: (1) login shows greeting, (2) page refresh keeps greeting, (3) GET /api/auth/me/ returns correct data, (4) fallback state shows "Doctor" when name fields are empty

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No action — skip
- **Foundational (Phase 2)**: No action — skip
- **User Story 1 (Phase 3)**: No dependencies — can start immediately
- **User Story 2 (Phase 4)**: No dependencies — can start immediately (parallel with Phase 3)
- **Polish (Phase 5)**: Depends on Phase 3 AND Phase 4 completion

### User Story Dependencies

- **US1 (Frontend — TopBar.jsx)**: Independent — no dependency on US2
- **US2 (Backend — MeView + urls.py)**: Independent — no dependency on US1

### Within Phase 4 (US2)

- T002 must complete before T003 (MeView must exist before it can be imported in urls.py)

### Parallel Opportunities

- T001 (US1) and T002 (US2) can run in **parallel** — they touch entirely different files in different layers
- T003 must follow T002 sequentially

---

## Parallel Execution Example

```
# Both can start at the same time:
Task T001: Fix TopBar.jsx in frontend/src/components/layout/TopBar.jsx
Task T002: Add MeView in backend/authentication/views.py

# After T002 completes:
Task T003: Wire MeView in backend/authentication/urls.py

# After T001 + T003 both complete:
Task T004: Verify all quickstart scenarios
```

---

## Implementation Strategy

### MVP (User Story 1 Only — Frontend Fix)

1. Complete T001 only
2. Validate: login → see greeting in TopBar
3. **STOP and VALIDATE**: Doctor name displays correctly, fallback works, persists on refresh

### Full Feature (Both Stories)

1. T001 and T002 in parallel
2. T003 after T002
3. T004 — verify all integration scenarios

### Total Task Count: 4

| Story | Tasks | Parallelizable |
|-------|-------|----------------|
| US1 — Personalized Greeting in Header | 1 (T001) | Yes (with T002) |
| US2 — Auth Endpoint Returns Name Fields | 2 (T002, T003) | T002 parallel with T001; T003 sequential after T002 |
| Polish | 1 (T004) | No — requires prior stories complete |

---

## Notes

- T001 and T002 target completely different files — safe to implement simultaneously
- No database migrations needed — `first_name`/`last_name` already exist on `CustomUser`
- No new packages or dependencies required
- The `UserSerializer` already serializes `first_name` and `last_name` — MeView only needs to call it
- `user.first_name` and `user.last_name` are already stored in the frontend auth context from the login response — no extra API call is needed from the TopBar component
