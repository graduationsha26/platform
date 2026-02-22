---
description: "Task list for Frontend Authentication & Layout implementation"
---

# Tasks: Frontend Authentication & Layout

**Input**: Design documents from `/specs/009-frontend-auth-layout/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/auth.yaml, contracts/user.yaml, quickstart.md

**Tests**: No test tasks included (tests not explicitly requested in specification)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

All frontend code resides in `frontend/` directory (monorepo structure).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and dependency installation

- [X] T001 Install npm dependencies: react-router-dom@^6.22.0, axios@^1.6.7, react-hook-form@^7.50.0, lucide-react@^0.323.0 in frontend/package.json
- [X] T002 [P] Create frontend/.env.local with VITE_API_BASE_URL=http://localhost:8000/api
- [X] T003 [P] Create directory structure: frontend/src/components/auth/, frontend/src/components/layout/, frontend/src/components/common/
- [X] T004 [P] Create directory structure: frontend/src/pages/, frontend/src/contexts/, frontend/src/services/
- [X] T005 [P] Create directory structure: frontend/src/hooks/, frontend/src/utils/, frontend/src/routes/

**Checkpoint**: Project structure and dependencies ready for implementation

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core utilities and components that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T006 [P] Create Button component with Tailwind styling in frontend/src/components/common/Button.jsx
- [X] T007 [P] Create Input component with validation error display in frontend/src/components/common/Input.jsx
- [X] T008 [P] Create LoadingSpinner component in frontend/src/components/common/LoadingSpinner.jsx
- [X] T009 [P] Implement token storage utility (getToken, setToken, removeToken) in frontend/src/utils/tokenStorage.js
- [X] T010 [P] Implement form validators (email, password, required) in frontend/src/utils/validators.js
- [X] T011 Create axios API client with base URL configuration in frontend/src/services/api.js
- [X] T012 Add axios request interceptor to inject JWT token in Authorization header in frontend/src/services/api.js
- [X] T013 Add axios response interceptor to handle 401 errors (automatic logout) in frontend/src/services/api.js

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - User Login with JWT Authentication (Priority: P1) 🎯 MVP

**Goal**: Enable doctors and patients to log in with email/password, receive JWT tokens, and access role-specific dashboards

**Independent Test**: Create test doctor and patient accounts, log in with valid credentials, verify JWT token storage in localStorage, confirm redirect to role-specific dashboard (/doctor/dashboard or /patient/dashboard)

### Implementation for User Story 1

- [X] T014 [P] [US1] Create AuthContext with state (user, token, isAuthenticated, isLoading, isSubmitting, error) in frontend/src/contexts/AuthContext.jsx
- [X] T015 [US1] Implement login action in AuthContext (calls backend API, stores token, updates state) in frontend/src/contexts/AuthContext.jsx
- [X] T016 [US1] Implement logout action in AuthContext (clears localStorage, resets state) in frontend/src/contexts/AuthContext.jsx
- [X] T017 [US1] Implement token persistence on app initialization (check localStorage, validate token) in frontend/src/contexts/AuthContext.jsx
- [X] T018 [P] [US1] Create useAuth custom hook to access AuthContext in frontend/src/hooks/useAuth.js
- [X] T019 [P] [US1] Implement authService.login function (POST /api/auth/login/) in frontend/src/services/authService.js
- [X] T020 [P] [US1] Create LoginForm component with React Hook Form validation in frontend/src/components/auth/LoginForm.jsx
- [X] T021 [US1] Create LoginPage component wrapping LoginForm in frontend/src/pages/LoginPage.jsx
- [X] T022 [P] [US1] Create placeholder DoctorDashboard page in frontend/src/pages/DoctorDashboard.jsx
- [X] T023 [P] [US1] Create placeholder PatientDashboard page in frontend/src/pages/PatientDashboard.jsx
- [X] T024 [US1] Create AppRoutes component with React Router configuration (login, doctor/patient dashboards) in frontend/src/routes/AppRoutes.jsx
- [X] T025 [US1] Update App.jsx to wrap app with BrowserRouter and AuthProvider in frontend/src/App.jsx
- [X] T026 [US1] Implement role-based redirect logic after login (doctor → /doctor/dashboard, patient → /patient/dashboard) in frontend/src/contexts/AuthContext.jsx

**Checkpoint**: At this point, User Story 1 should be fully functional - users can log in and see their role-specific dashboard

---

## Phase 4: User Story 2 - User Registration (Priority: P2)

**Goal**: Enable new doctors and patients to create accounts with email, password, name, and role selection

**Independent Test**: Fill registration form with valid data (name, email, unique email, strong password, role), submit form, verify account creation in database, navigate to login page, log in with new credentials

### Implementation for User Story 2

- [X] T027 [P] [US2] Implement authService.register function (POST /api/auth/register/) in frontend/src/services/authService.js
- [X] T028 [US2] Implement register action in AuthContext (calls backend API, handles success/error) in frontend/src/contexts/AuthContext.jsx
- [X] T029 [P] [US2] Create RegisterForm component with React Hook Form validation (name, email, password, passwordConfirm, role) in frontend/src/components/auth/RegisterForm.jsx
- [X] T030 [US2] Create RegisterPage component wrapping RegisterForm in frontend/src/pages/RegisterPage.jsx
- [X] T031 [US2] Add /register route to AppRoutes in frontend/src/routes/AppRoutes.jsx
- [X] T032 [US2] Add "Don't have an account? Register" link to LoginPage in frontend/src/pages/LoginPage.jsx
- [X] T033 [US2] Add "Already have an account? Login" link to RegisterPage in frontend/src/pages/RegisterPage.jsx
- [X] T034 [US2] Implement success message display after registration before redirect to login in frontend/src/components/auth/RegisterForm.jsx

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently - new users can register and then log in

---

## Phase 5: User Story 3 - Protected Routes & Role-Based Access (Priority: P3)

**Goal**: Secure protected routes, redirect unauthenticated users to login, implement role-based redirects, handle token expiration

**Independent Test**: Log out (clear localStorage), attempt to access /doctor/dashboard (should redirect to /login), log in as doctor (should redirect to /doctor/dashboard), log in as patient (should redirect to /patient/dashboard), wait for token expiration (should auto-logout and redirect to /login)

### Implementation for User Story 3

- [X] T035 [P] [US3] Create ProtectedRoute wrapper component checking isAuthenticated from AuthContext in frontend/src/components/auth/ProtectedRoute.jsx
- [X] T036 [US3] Implement redirect to /login for unauthenticated users in ProtectedRoute in frontend/src/components/auth/ProtectedRoute.jsx
- [X] T037 [US3] Store attempted URL in location state for post-login redirect in ProtectedRoute in frontend/src/components/auth/ProtectedRoute.jsx
- [X] T038 [US3] Wrap dashboard routes with ProtectedRoute in AppRoutes in frontend/src/routes/AppRoutes.jsx
- [X] T039 [US3] Implement redirect authenticated users away from /login and /register to role-specific dashboard in frontend/src/routes/AppRoutes.jsx
- [X] T040 [US3] Implement post-login redirect to originally attempted URL (if stored) in frontend/src/contexts/AuthContext.jsx
- [X] T041 [US3] Add session expiration message display when 401 error triggers logout in frontend/src/contexts/AuthContext.jsx

**Checkpoint**: All protected routes now secure - unauthenticated users redirected to login, authenticated users redirected to appropriate dashboards

---

## Phase 6: User Story 4 - Responsive Layout with Role-Based Navigation (Priority: P4)

**Goal**: Implement responsive layout shell with sidebar, top bar, role-specific menu items, and mobile hamburger menu

**Independent Test**: Log in as doctor, verify doctor-specific menu items (Patients, Analytics, Reports) in sidebar, test mobile responsiveness (sidebar collapses to hamburger menu), log in as patient, verify patient-specific menu items (My Data, Sessions, Progress), click logout button, verify redirect to login and token cleared

### Implementation for User Story 4

- [X] T042 [P] [US4] Implement role helpers utility (getMenuItems, getDashboardPath) in frontend/src/utils/roleHelpers.js
- [X] T043 [P] [US4] Create TopBar component with user info display and logout button in frontend/src/components/layout/TopBar.jsx
- [X] T044 [P] [US4] Create Sidebar component with role-based menu items and active route highlighting in frontend/src/components/layout/Sidebar.jsx
- [X] T045 [P] [US4] Create MobileMenu component (overlay menu for mobile) in frontend/src/components/layout/MobileMenu.jsx
- [X] T046 [US4] Create AppLayout component integrating TopBar, Sidebar, MobileMenu with responsive state management in frontend/src/components/layout/AppLayout.jsx
- [X] T047 [US4] Implement hamburger menu toggle functionality in AppLayout in frontend/src/components/layout/AppLayout.jsx
- [X] T048 [US4] Add Tailwind responsive classes for desktop (persistent sidebar) and mobile (hidden sidebar, hamburger menu) in frontend/src/components/layout/AppLayout.jsx
- [X] T049 [US4] Update DoctorDashboard to use AppLayout wrapper in frontend/src/pages/DoctorDashboard.jsx
- [X] T050 [US4] Update PatientDashboard to use AppLayout wrapper in frontend/src/pages/PatientDashboard.jsx
- [X] T051 [US4] Implement logout button click handler in TopBar (calls AuthContext.logout) in frontend/src/components/layout/TopBar.jsx
- [X] T052 [US4] Implement menu item navigation in Sidebar (React Router Link) in frontend/src/components/layout/Sidebar.jsx
- [X] T053 [US4] Add active route highlighting logic using useLocation hook in frontend/src/components/layout/Sidebar.jsx

**Checkpoint**: All user stories complete - full authentication flow with responsive layout working end-to-end

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories and final validation

- [X] T054 [P] Add loading state handling for all async operations (login, register) with LoadingSpinner component
- [X] T055 [P] Add error message display styling and animations across all forms
- [X] T056 [P] Optimize bundle size by lazy loading dashboard pages with React.lazy() in frontend/src/routes/AppRoutes.jsx
- [X] T057 [P] Add PropTypes or TypeScript type checking for all components (optional enhancement)
- [X] T058 Perform manual testing checklist from quickstart.md (login, register, protected routes, layout, mobile responsive)
- [X] T059 Verify all success criteria from spec.md (login <10s, registration <2min, 100% protected routes secure, mobile responsive 320px-1920px+)
- [X] T060 [P] Update README with frontend setup instructions and environment configuration
- [X] T061 Code cleanup: Remove console.logs, fix linting warnings, format code

**Checkpoint**: Feature complete and production-ready for graduation project demo

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3 → P4)
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Independent of US1 (but integrates with AuthContext from US1)
- **User Story 3 (P3)**: Depends on US1 completion (requires AuthContext and login flow) - Extends US1 with route protection
- **User Story 4 (P4)**: Depends on US1 and US3 completion (requires authentication state and protected routes) - Adds layout shell

### Within Each User Story

**User Story 1:**
1. AuthContext first (T014-T017) - Foundation for all auth
2. useAuth hook (T018) - Can run parallel after AuthContext
3. authService.login (T019) - Can run parallel after AuthContext
4. LoginForm (T020) and LoginPage (T021) - After AuthContext
5. Dashboard placeholders (T022-T023) - Can run parallel
6. Routing (T024-T026) - After all above components

**User Story 2:**
1. authService.register (T027) - Can run parallel
2. register action in AuthContext (T028)
3. RegisterForm (T029) - Can run parallel after T028
4. RegisterPage (T030) and routing (T031) - After T029
5. Navigation links (T032-T033) - Can run parallel
6. Success message (T034) - After T029

**User Story 3:**
1. ProtectedRoute component (T035-T037) - Can run parallel
2. Update routing (T038-T039) - After T035
3. Post-login redirect (T040-T041) - After T038

**User Story 4:**
1. Role helpers (T042) - Can run parallel
2. Layout components (T043-T045) - Can run parallel after T042
3. AppLayout (T046-T048) - After T043-T045
4. Update dashboards (T049-T050) - After T046
5. Wire up interactions (T051-T053) - After T049-T050

### Parallel Opportunities

**Phase 1 (Setup)**: T002-T005 can all run in parallel after T001

**Phase 2 (Foundational)**: T006-T008 (components), T009-T010 (utils) can run parallel; T011 first, then T012-T013 sequentially

**User Story 1**: T014-T017 sequential; T018, T019, T022, T023 can run parallel after T017; T020-T021 after T018-T019; T024-T026 sequential at end

**User Story 2**: T027, T029 can run parallel; T032-T033 can run parallel

**User Story 3**: T035-T037 can be done together; T038-T039 together; T040-T041 together

**User Story 4**: T042-T045 can all run parallel; T049-T050 can run parallel; T051-T053 can run parallel

**Phase 7 (Polish)**: T054-T057, T060-T061 can all run in parallel

---

## Parallel Example: User Story 1

```bash
# After T017 (AuthContext complete), launch these in parallel:
Task T018: "Create useAuth hook in frontend/src/hooks/useAuth.js"
Task T019: "Implement authService.login in frontend/src/services/authService.js"
Task T022: "Create DoctorDashboard placeholder in frontend/src/pages/DoctorDashboard.jsx"
Task T023: "Create PatientDashboard placeholder in frontend/src/pages/PatientDashboard.jsx"
```

---

## Parallel Example: User Story 4

```bash
# After T042 (roleHelpers complete), launch layout components in parallel:
Task T043: "Create TopBar component in frontend/src/components/layout/TopBar.jsx"
Task T044: "Create Sidebar component in frontend/src/components/layout/Sidebar.jsx"
Task T045: "Create MobileMenu component in frontend/src/components/layout/MobileMenu.jsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T005)
2. Complete Phase 2: Foundational (T006-T013) - **CRITICAL - blocks all stories**
3. Complete Phase 3: User Story 1 (T014-T026)
4. **STOP and VALIDATE**: Test login flow with doctor and patient accounts
5. Demo MVP: Users can log in and see role-specific dashboard

### Incremental Delivery

1. **Foundation**: Complete Setup + Foundational → Infrastructure ready
2. **MVP**: Add User Story 1 → Test independently → Deploy/Demo (login works!)
3. **Iteration 2**: Add User Story 2 → Test independently → Deploy/Demo (registration works!)
4. **Iteration 3**: Add User Story 3 → Test independently → Deploy/Demo (route protection works!)
5. **Iteration 4**: Add User Story 4 → Test independently → Deploy/Demo (full layout works!)
6. **Polish**: Complete Phase 7 → Final validation → Production demo

### Parallel Team Strategy

With multiple developers:

1. **Week 1**: Team completes Setup + Foundational together (T001-T013)
2. **Week 2**: Once Foundational is done:
   - Developer A: User Story 1 (T014-T026)
   - Developer B: User Story 2 (T027-T034) - starts after US1 AuthContext ready
   - Developer C: Prep User Story 4 components (T042-T045)
3. **Week 3**:
   - Developer A: User Story 3 (T035-T041) - adds route protection to US1
   - Developer B: Complete User Story 4 (T046-T053) - integrates layout
   - Developer C: Polish tasks (T054-T061)
4. Stories integrate seamlessly due to independent design

---

## Task Summary

**Total Tasks**: 61 tasks

**By Phase**:
- Phase 1 (Setup): 5 tasks
- Phase 2 (Foundational): 8 tasks
- Phase 3 (US1 - Login): 13 tasks
- Phase 4 (US2 - Registration): 8 tasks
- Phase 5 (US3 - Protected Routes): 7 tasks
- Phase 6 (US4 - Layout): 12 tasks
- Phase 7 (Polish): 8 tasks

**By User Story**:
- User Story 1 (P1): 13 tasks - MVP scope
- User Story 2 (P2): 8 tasks
- User Story 3 (P3): 7 tasks
- User Story 4 (P4): 12 tasks
- Setup + Foundational: 13 tasks (required for all stories)
- Polish: 8 tasks (cross-cutting)

**Parallel Opportunities Identified**: 23 tasks marked [P] can run in parallel within their phase

**Independent Test Criteria**:
- US1: Log in with test accounts, verify token storage, confirm role-based redirect
- US2: Register new account, verify in database, log in successfully
- US3: Access protected route while logged out (redirect), test token expiration (auto-logout)
- US4: Verify role-specific menus, test mobile responsiveness, confirm logout functionality

**Suggested MVP Scope**: Phase 1 + Phase 2 + Phase 3 (User Story 1 only) = 26 tasks

**Format Validation**: ✅ All 61 tasks follow checklist format with checkbox, task ID, optional [P] marker, [Story] label for user story tasks, and file paths

---

## Notes

- [P] tasks = different files, no dependencies within the same phase
- [Story] label (US1, US2, US3, US4) maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group of tasks
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
- All file paths are absolute from repository root (frontend/ prefix)
- Tests are not included per specification (not explicitly requested)
