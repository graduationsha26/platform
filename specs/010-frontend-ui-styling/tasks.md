---
description: "Task list for Outstanding UI & Styling implementation"
---

# Tasks: Outstanding UI & Styling for TremoAI Frontend

**Input**: Design documents from `/specs/010-frontend-ui-styling/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: No test tasks included (tests not explicitly requested in specification)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4, US5)
- Include exact file paths in descriptions

## Path Conventions

All frontend code resides in `frontend/` directory (monorepo structure).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and design token configuration

- [X] T001 Create frontend/src/styles/ directory structure (animations.css, utilities.css, tokens.css)
- [X] T002 Verify Tailwind CSS configuration exists in frontend/tailwind.config.js
- [X] T003 Verify PostCSS configuration includes Tailwind in frontend/postcss.config.js

**Checkpoint**: Project structure ready for design system implementation

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Design tokens and base styles that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 [P] Create CSS custom properties for design tokens in frontend/src/styles/tokens.css (colors, spacing, shadows, typography)
- [X] T005 [P] Define animation keyframes in frontend/src/styles/animations.css (fade-in, slide-in, scale-in, shimmer, shake)
- [X] T006 [P] Create utility CSS classes in frontend/src/styles/utilities.css (glassmorphism, accessibility helpers)
- [X] T007 Configure Tailwind theme extension in frontend/tailwind.config.js with medical color palette (primary blue #2563eb, secondary teal #0d9488, semantic colors)
- [X] T008 Add typography scale to Tailwind config in frontend/tailwind.config.js (display, h1-h4, body, caption sizes with line heights)
- [X] T009 Add spacing scale to Tailwind config in frontend/tailwind.config.js (4px base grid: 0-24 scale plus semantic tokens)
- [X] T010 Add shadow tokens to Tailwind config in frontend/tailwind.config.js (xs, sm, md, lg, xl, 2xl elevations)
- [X] T011 Add animation utilities to Tailwind config in frontend/tailwind.config.js (durations, timing functions, keyframes)
- [X] T012 Add border radius scale to Tailwind config in frontend/tailwind.config.js (sm, md, lg, xl, 2xl, full)
- [X] T013 Configure responsive breakpoints in frontend/tailwind.config.js (verify default sm:640, md:768, lg:1024, xl:1280, 2xl:1536)
- [X] T014 Import styles/tokens.css, styles/animations.css, styles/utilities.css in frontend/src/index.css
- [X] T015 Add @tailwind directives and global styles in frontend/src/index.css (base, components, utilities)
- [X] T016 Implement prefers-reduced-motion support in frontend/src/index.css (@media query to disable animations)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Professional Medical Design System (Priority: P1) 🎯 MVP

**Goal**: Establish professional medical-grade visual identity through cohesive color palette, typography hierarchy, and spacing system

**Independent Test**: Review all pages (Login, Register, Doctor Dashboard, Patient Dashboard) for visual consistency, verify color contrast meets WCAG AA (4.5:1 minimum) using axe DevTools, confirm typography hierarchy is clear, validate spacing follows 4px/8px grid

### Implementation for User Story 1

- [X] T017 [P] [US1] Update index.css with medical color palette as CSS custom properties in frontend/src/index.css
- [X] T018 [P] [US1] Apply typography hierarchy to all headings in frontend/src/index.css (h1, h2, h3, h4 font sizes, weights, line heights)
- [X] T019 [P] [US1] Apply body text styling in frontend/src/index.css (16px base, 1.5 line height, neutral-700 color)
- [X] T020 [P] [US1] Update LoginPage with medical color scheme in frontend/src/pages/LoginPage.jsx (bg-neutral-50 background, proper heading colors)
- [X] T021 [P] [US1] Update RegisterPage with medical color scheme in frontend/src/pages/RegisterPage.jsx (consistent with LoginPage)
- [X] T022 [P] [US1] Update DoctorDashboard with color palette and typography in frontend/src/pages/DoctorDashboard.jsx (page title h1, section titles h2)
- [X] T023 [P] [US1] Update PatientDashboard with color palette and typography in frontend/src/pages/PatientDashboard.jsx (consistent with DoctorDashboard)
- [X] T024 [P] [US1] Apply spacing system to page containers in frontend/src/pages/LoginPage.jsx (px-4 sm:px-6 lg:px-8, py-6 sm:py-8 lg:py-12)
- [X] T025 [P] [US1] Apply spacing system to page containers in frontend/src/pages/RegisterPage.jsx (consistent responsive padding)
- [X] T026 [P] [US1] Apply spacing system to dashboard layouts in frontend/src/pages/DoctorDashboard.jsx (section gaps, card grids)
- [X] T027 [P] [US1] Apply spacing system to dashboard layouts in frontend/src/pages/PatientDashboard.jsx (consistent with DoctorDashboard)
- [X] T028 [US1] Update Sidebar with medical color scheme in frontend/src/components/layout/Sidebar.jsx (bg-white, border-neutral-200, text-neutral-700)
- [X] T029 [US1] Update TopBar with medical color scheme in frontend/src/components/layout/TopBar.jsx (bg-white, border-neutral-200)
- [X] T030 [US1] Update MobileMenu with medical color scheme in frontend/src/components/layout/MobileMenu.jsx (consistent with Sidebar)
- [X] T031 [US1] Run accessibility audit with axe DevTools to verify WCAG AA contrast compliance (4.5:1 minimum)

**Checkpoint**: At this point, User Story 1 should be fully functional - all pages have professional medical color scheme, clear typography hierarchy, and consistent spacing

---

## Phase 4: User Story 2 - Enhanced Form & Authentication UI (Priority: P2)

**Goal**: Polish form components with smooth micro-interactions, clear validation states, and visual feedback

**Independent Test**: Fill out login and registration forms, intentionally trigger validation errors, observe smooth focus animations, hover button to verify micro-interactions, verify all transitions are smooth (60 FPS in Chrome DevTools Performance Monitor)

### Implementation for User Story 2

- [X] T032 [P] [US2] Enhance Button component with micro-interactions in frontend/src/components/common/Button.jsx (hover: bg darken + shadow increase, active: further darken + shadow decrease, transitions 200ms)
- [X] T033 [P] [US2] Add loading state to Button component in frontend/src/components/common/Button.jsx (spinner, opacity 70%, disabled, cursor-wait)
- [X] T034 [P] [US2] Add focus ring styles to Button component in frontend/src/components/common/Button.jsx (focus:ring-4 focus:ring-blue-300, focus:outline-none)
- [X] T035 [P] [US2] Enhance Input component with focus animations in frontend/src/components/common/Input.jsx (focus:border-blue-500 focus:ring-4 focus:ring-blue-100, transition 200ms)
- [X] T036 [P] [US2] Add error state styling to Input component in frontend/src/components/common/Input.jsx (border-red-500 focus:ring-red-100 when error)
- [X] T037 [P] [US2] Add success state styling to Input component in frontend/src/components/common/Input.jsx (border-green-500 focus:ring-green-100 when success)
- [X] T038 [US2] Update LoginForm with enhanced input styling in frontend/src/components/auth/LoginForm.jsx (apply new Input variants, verify error messages animate)
- [X] T039 [US2] Update RegisterForm with enhanced input styling in frontend/src/components/auth/RegisterForm.jsx (apply new Input variants, add password strength indicator)
- [X] T040 [US2] Add animated error messages to LoginForm in frontend/src/components/auth/LoginForm.jsx (slide-in-down animation, red background, error icon)
- [X] T041 [US2] Add animated success messages to RegisterForm in frontend/src/components/auth/RegisterForm.jsx (slide-in-down animation, green background, success icon)
- [X] T042 [US2] Add password strength indicator to RegisterForm in frontend/src/components/auth/RegisterForm.jsx (weak: red, medium: yellow, strong: green, smooth transitions)
- [X] T043 [US2] Implement button hover states in LoginForm in frontend/src/components/auth/LoginForm.jsx (verify smooth color and shadow transitions)
- [X] T044 [US2] Implement button hover states in RegisterForm in frontend/src/components/auth/RegisterForm.jsx (consistent with LoginForm)
- [X] T045 [US2] Add touch-action: manipulation to all buttons to prevent tap delay on mobile in frontend/src/components/common/Button.jsx

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently - forms have polished interactions and clear validation feedback

---

## Phase 5: User Story 3 - Polished Dashboard & Data Visualization (Priority: P3)

**Goal**: Enhance dashboard cards with depth, shadows, glassmorphism effects, and smooth hover interactions

**Independent Test**: Navigate to doctor/patient dashboards, observe card shadows and depth, hover over cards to verify elevation changes, check for glassmorphism effects (if applied), verify data visualizations animate smoothly, confirm visual hierarchy is clear

### Implementation for User Story 3

- [X] T046 [P] [US3] Create reusable card component styles in frontend/src/styles/utilities.css (.card-base, .card-hover, .glass-light, .glass-medium)
- [X] T047 [P] [US3] Apply card base styling to DoctorDashboard cards in frontend/src/pages/DoctorDashboard.jsx (bg-white, rounded-xl, shadow-md, p-6)
- [X] T048 [P] [US3] Apply card base styling to PatientDashboard cards in frontend/src/pages/PatientDashboard.jsx (consistent with DoctorDashboard)
- [X] T049 [US3] Add card hover effects to DoctorDashboard cards in frontend/src/pages/DoctorDashboard.jsx (hover:shadow-lg hover:-translate-y-1, transition 300ms)
- [X] T050 [US3] Add card hover effects to PatientDashboard cards in frontend/src/pages/PatientDashboard.jsx (consistent with DoctorDashboard)
- [X] T051 [P] [US3] Implement glassmorphism for prominent cards in frontend/src/pages/DoctorDashboard.jsx (backdrop-blur-md bg-white/20 border-white/30, fallback bg-white/85)
- [X] T052 [P] [US3] Implement glassmorphism for prominent cards in frontend/src/pages/PatientDashboard.jsx (consistent with DoctorDashboard)
- [X] T053 [US3] Add shadow elevation hierarchy to dashboard in frontend/src/pages/DoctorDashboard.jsx (primary cards: shadow-lg, secondary: shadow-md, tertiary: shadow-sm)
- [X] T054 [US3] Add shadow elevation hierarchy to dashboard in frontend/src/pages/PatientDashboard.jsx (consistent with DoctorDashboard)
- [X] T055 [P] [US3] Add rounded corners to all cards in frontend/src/pages/DoctorDashboard.jsx (rounded-xl for cards, rounded-lg for nested elements)
- [X] T056 [P] [US3] Add rounded corners to all cards in frontend/src/pages/PatientDashboard.jsx (consistent with DoctorDashboard)
- [X] T057 [US3] Enhance data visualization animations if charts exist in frontend/src/pages/DoctorDashboard.jsx (smooth loading animations, hover tooltips)
- [X] T058 [US3] Enhance data visualization animations if charts exist in frontend/src/pages/PatientDashboard.jsx (consistent with DoctorDashboard)
- [X] T059 [US3] Test glassmorphism fallback in Safari/older browsers (verify bg-white/85 fallback)

**Checkpoint**: All user stories complete - dashboards have professional depth, shadows, and modern glassmorphism effects

---

## Phase 6: User Story 4 - Premium Loading States & Transitions (Priority: P4)

**Goal**: Implement elegant loading indicators and smooth page transitions to enhance perceived performance

**Independent Test**: Navigate between pages and observe smooth transitions, trigger form submissions to see loading states, verify skeleton screens appear during data fetch, confirm all animations maintain 60 FPS

### Implementation for User Story 4

- [X] T060 [P] [US4] Enhance LoadingSpinner component in frontend/src/components/common/LoadingSpinner.jsx (professional circular spinner, 32px size, blue color, 1s spin animation)
- [X] T061 [P] [US4] Create skeleton screen component in frontend/src/components/common/SkeletonLoader.jsx (animate-pulse, bg-neutral-200 rounded, height variants)
- [X] T062 [US4] Apply loading spinner to button loading states in frontend/src/components/common/Button.jsx (inline spinner, opacity 70%, disabled)
- [X] T063 [P] [US4] Add skeleton screens to DoctorDashboard during initial load in frontend/src/pages/DoctorDashboard.jsx (skeleton cards matching eventual content)
- [X] T064 [P] [US4] Add skeleton screens to PatientDashboard during initial load in frontend/src/pages/PatientDashboard.jsx (consistent with DoctorDashboard)
- [X] T065 [US4] Implement page transition animations in frontend/src/routes/AppRoutes.jsx (fade-in 400ms ease-out on route changes)
- [X] T066 [US4] Add slide-in-up animation to page content in frontend/src/pages/DoctorDashboard.jsx (animate on mount, 400ms ease-out)
- [X] T067 [US4] Add slide-in-up animation to page content in frontend/src/pages/PatientDashboard.jsx (consistent with DoctorDashboard)
- [X] T068 [P] [US4] Implement staggered animations for dashboard cards in frontend/src/pages/DoctorDashboard.jsx (cascade effect, delay 50ms per card, max 12 cards)
- [X] T069 [P] [US4] Implement staggered animations for dashboard cards in frontend/src/pages/PatientDashboard.jsx (consistent with DoctorDashboard)
- [X] T070 [US4] Add fade-in animation to modal/dialog overlays in frontend/src/components/layout/AppLayout.jsx (if modals exist, backdrop-blur-in 300ms)
- [X] T071 [US4] Test loading states don't cause layout shifts (verify CLS score <0.1 in Lighthouse)

**Checkpoint**: Loading states and transitions are polished - users perceive improved performance and responsiveness

---

## Phase 7: User Story 5 - Responsive Mobile-First Refinements (Priority: P5)

**Goal**: Ensure mobile experience is polished with proper touch targets, spacing, and responsive design

**Independent Test**: Test on mobile devices (375px, 768px widths), verify all touch targets ≥44×44px, check mobile spacing is comfortable, test form inputs trigger correct keyboards, verify hamburger menu transitions smoothly

### Implementation for User Story 5

- [X] T072 [P] [US5] Verify all buttons meet 44×44px minimum on mobile in frontend/src/components/common/Button.jsx (min-h-[44px] min-w-[44px])
- [X] T073 [P] [US5] Verify all inputs meet 44px height minimum in frontend/src/components/common/Input.jsx (min-h-[44px], font-size: 16px on mobile to prevent iOS zoom)
- [X] T074 [P] [US5] Add mobile-specific spacing to LoginPage in frontend/src/pages/LoginPage.jsx (px-4 py-6 on mobile, increase on larger screens)
- [X] T075 [P] [US5] Add mobile-specific spacing to RegisterPage in frontend/src/pages/RegisterPage.jsx (consistent with LoginPage)
- [X] T076 [P] [US5] Add mobile-specific spacing to dashboards in frontend/src/pages/DoctorDashboard.jsx (tighter spacing on mobile, looser on desktop)
- [X] T077 [P] [US5] Add mobile-specific spacing to dashboards in frontend/src/pages/PatientDashboard.jsx (consistent with DoctorDashboard)
- [X] T078 [US5] Ensure proper input types on mobile forms in frontend/src/components/auth/LoginForm.jsx (type="email" for email, inputMode for specific keyboards)
- [X] T079 [US5] Ensure proper input types on mobile forms in frontend/src/components/auth/RegisterForm.jsx (type="tel" for phone, type="email", etc.)
- [X] T080 [US5] Test hamburger menu transitions on mobile in frontend/src/components/layout/MobileMenu.jsx (smooth slide-in 300ms, backdrop fade)
- [X] T081 [US5] Verify sidebar collapses properly on mobile in frontend/src/components/layout/Sidebar.jsx (hidden below md:768px)
- [X] T082 [US5] Test touch target spacing in navigation in frontend/src/components/layout/Sidebar.jsx (≥8px gaps between menu items)
- [X] T083 [US5] Add responsive breakpoints to dashboard grids in frontend/src/pages/DoctorDashboard.jsx (grid-cols-1 sm:grid-cols-2 lg:grid-cols-3)
- [X] T084 [US5] Add responsive breakpoints to dashboard grids in frontend/src/pages/PatientDashboard.jsx (consistent with DoctorDashboard)
- [X] T085 [US5] Test on physical mobile devices or DevTools mobile emulation (320px, 375px, 768px widths)

**Checkpoint**: All user stories complete - mobile experience is polished and touch-optimized

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final improvements that affect multiple user stories and validation

- [X] T086 [P] Add smooth scroll behavior to entire app in frontend/src/index.css (scroll-behavior: smooth)
- [X] T087 [P] Verify prefers-reduced-motion disables animations in frontend/src/index.css (test with OS setting or DevTools emulation)
- [X] T088 Run accessibility audit with axe DevTools on all major pages (target: 0 critical violations)
- [X] T089 Run Lighthouse Performance audit (target: ≥90 score, verify 60 FPS animations)
- [X] T090 Test color contrast on all pages with WebAIM Contrast Checker (verify WCAG AA 4.5:1 minimum)
- [X] T091 Verify glassmorphism fallbacks work in Safari/older browsers (test with @supports)
- [X] T092 [P] Test cross-browser compatibility (Chrome, Firefox, Safari, Edge)
- [X] T093 [P] Test on various device sizes (320px to 1920px)
- [X] T094 Verify all functional requirements met (FR-001 through FR-020 from spec.md)
- [X] T095 Run quickstart.md visual testing scenarios (Scenarios 1-6)
- [X] T096 Verify success criteria met (SC-001, 002, 006, 007, 008 from spec.md - technical metrics)
- [X] T097 [P] Code cleanup: Remove console.logs, fix linting warnings, format code
- [X] T098 [P] Update README with UI styling changes and design token documentation

**Checkpoint**: Feature complete and production-ready for graduation project demo

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3 → P4 → P5)
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Independent of US1 (but builds on design system)
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Independent of US1/US2 (applies design system to dashboards)
- **User Story 4 (P4)**: Can start after Foundational (Phase 2) - Independent of previous stories (adds loading states)
- **User Story 5 (P5)**: Can start after Foundational (Phase 2) - Independent of previous stories (mobile refinements)

### Within Each User Story

**User Story 1 (Design System)**:
1. Apply colors, typography, spacing to global styles (T017-T019) - Can run parallel
2. Update pages with design system (T020-T027) - Can run parallel after global styles
3. Update layout components (T028-T030) - Can run parallel
4. Accessibility audit (T031) - After all above

**User Story 2 (Forms)**:
1. Enhance Button component (T032-T034) - Can run parallel
2. Enhance Input component (T035-T037) - Can run parallel
3. Update forms (T038-T044) - After Button/Input enhancements
4. Mobile optimization (T045) - After forms updated

**User Story 3 (Dashboards)**:
1. Create card utilities (T046) - First
2. Apply card styling to dashboards (T047-T048) - Can run parallel after utilities
3. Add hover effects (T049-T050) - Can run parallel
4. Add glassmorphism (T051-T052) - Can run parallel
5. Add shadows and hierarchy (T053-T056) - Can run parallel
6. Enhance charts (T057-T058) - Can run parallel
7. Test fallbacks (T059) - After glassmorphism

**User Story 4 (Loading States)**:
1. Enhance LoadingSpinner and create SkeletonLoader (T060-T061) - Can run parallel
2. Apply loading states (T062-T064) - Can run parallel after components
3. Page transitions (T065-T070) - Sequential or parallel depending on file conflicts
4. Test performance (T071) - After all above

**User Story 5 (Mobile)**:
1. Verify touch targets (T072-T073) - Can run parallel
2. Add mobile spacing (T074-T077) - Can run parallel
3. Optimize forms (T078-T079) - Can run parallel
4. Test navigation (T080-T082) - After navigation components updated
5. Responsive grids (T083-T084) - Can run parallel
6. Device testing (T085) - After all above

### Parallel Opportunities

**Phase 1 (Setup)**: T001-T003 can all run in parallel

**Phase 2 (Foundational)**: T004-T006 (CSS files) can run parallel; T007-T015 (Tailwind config + imports) sequential; T016 parallel after imports

**User Story 1**: T017-T019 parallel; T020-T027 parallel; T028-T030 parallel

**User Story 2**: T032-T034 parallel; T035-T037 parallel; T038-T044 after components enhanced

**User Story 3**: T047-T048 parallel; T049-T059 many can run parallel (different pages or independent features)

**User Story 4**: T060-T061 parallel; T063-T064 parallel; T068-T069 parallel

**User Story 5**: T072-T077 parallel; T078-T079 parallel; T083-T084 parallel

**Phase 8 (Polish)**: T086-T087, T092-T093, T097-T098 can all run parallel

---

## Parallel Example: User Story 1

```bash
# After Foundational phase completes, launch these in parallel:
Task T017: "Update index.css with medical color palette as CSS custom properties"
Task T018: "Apply typography hierarchy to all headings in index.css"
Task T019: "Apply body text styling in index.css"

# Then launch page updates in parallel:
Task T020: "Update LoginPage with medical color scheme"
Task T021: "Update RegisterPage with medical color scheme"
Task T022: "Update DoctorDashboard with color palette and typography"
Task T023: "Update PatientDashboard with color palette and typography"
```

---

## Parallel Example: User Story 3

```bash
# After card utilities created (T046), launch these in parallel:
Task T047: "Apply card base styling to DoctorDashboard cards"
Task T048: "Apply card base styling to PatientDashboard cards"
Task T049: "Add card hover effects to DoctorDashboard cards"
Task T050: "Add card hover effects to PatientDashboard cards"
Task T051: "Implement glassmorphism for prominent cards in DoctorDashboard"
Task T052: "Implement glassmorphism for prominent cards in PatientDashboard"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T016) - **CRITICAL - blocks all stories**
3. Complete Phase 3: User Story 1 (T017-T031)
4. **STOP and VALIDATE**: Test design system across all pages, verify color contrast, confirm visual consistency
5. Demo MVP: Platform now has professional medical-grade appearance

### Incremental Delivery

1. **Foundation**: Complete Setup + Foundational → Design tokens ready
2. **MVP**: Add User Story 1 → Test independently → Deploy/Demo (professional design system!)
3. **Iteration 2**: Add User Story 2 → Test independently → Deploy/Demo (enhanced forms!)
4. **Iteration 3**: Add User Story 3 → Test independently → Deploy/Demo (polished dashboards!)
5. **Iteration 4**: Add User Story 4 → Test independently → Deploy/Demo (premium loading states!)
6. **Iteration 5**: Add User Story 5 → Test independently → Deploy/Demo (mobile-optimized!)
7. **Polish**: Complete Phase 8 → Final validation → Production demo

### Parallel Team Strategy

With multiple developers:

1. **Week 1**: Team completes Setup + Foundational together (T001-T016)
2. **Week 2**: Once Foundational is done:
   - Developer A: User Story 1 (T017-T031) - Design system
   - Developer B: User Story 2 (T032-T045) - Forms (waits for Button/Input components from US1 if needed)
   - Developer C: Prep User Story 3 components (T046)
3. **Week 3**:
   - Developer A: User Story 3 (T047-T059) - Dashboards
   - Developer B: User Story 4 (T060-T071) - Loading states
   - Developer C: User Story 5 (T072-T085) - Mobile refinements
4. **Week 4**:
   - Team: Polish tasks (T086-T098)
5. Stories integrate seamlessly due to independent design

---

## Task Summary

**Total Tasks**: 98 tasks

**By Phase**:
- Phase 1 (Setup): 3 tasks
- Phase 2 (Foundational): 13 tasks
- Phase 3 (US1 - Design System): 15 tasks
- Phase 4 (US2 - Forms): 14 tasks
- Phase 5 (US3 - Dashboards): 14 tasks
- Phase 6 (US4 - Loading States): 12 tasks
- Phase 7 (US5 - Mobile): 14 tasks
- Phase 8 (Polish): 13 tasks

**By User Story**:
- User Story 1 (P1): 15 tasks - MVP scope
- User Story 2 (P2): 14 tasks
- User Story 3 (P3): 14 tasks
- User Story 4 (P4): 12 tasks
- User Story 5 (P5): 14 tasks
- Setup + Foundational: 16 tasks (required for all stories)
- Polish: 13 tasks (cross-cutting)

**Parallel Opportunities Identified**: 45 tasks marked [P] can run in parallel within their phase

**Independent Test Criteria**:
- US1: Verify color palette, typography hierarchy, spacing consistency across all pages
- US2: Test form interactions, validation states, button micro-interactions, smooth transitions
- US3: Observe dashboard card depth, shadows, glassmorphism, hover effects, visual hierarchy
- US4: Trigger loading states, observe page transitions, verify skeleton screens, test 60 FPS performance
- US5: Test on mobile devices, verify touch targets ≥44×44px, check mobile spacing, test responsive breakpoints

**Suggested MVP Scope**: Phase 1 + Phase 2 + Phase 3 (User Story 1 only) = 31 tasks

**Format Validation**: ✅ All 98 tasks follow checklist format with checkbox, task ID, optional [P] marker, [Story] label for user story tasks, and file paths

---

## Notes

- [P] tasks = different files, no dependencies within the same phase
- [Story] label (US1, US2, US3, US4, US5) maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group of tasks
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
- All file paths are absolute from repository root (frontend/ prefix)
- Tests are not included per specification (not explicitly requested)
- Frontend-only feature - no backend modifications required
