# Tasks: Analytics and Reporting

**Input**: Design documents from `/specs/003-analytics-reporting/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/analytics-api.yaml, quickstart.md

**Tests**: Not explicitly requested in specification - test tasks omitted per template guidelines.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app structure**: `backend/analytics/` for new Django app
- All tasks reference Django project structure from plan.md

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and dependency installation

- [X] T001 Install Python dependencies: reportlab==4.0.7, matplotlib==3.8.2, pillow==10.2.0, numpy==1.26.3 in backend/requirements.txt
- [X] T002 Create analytics Django app: `py -m django startapp analytics` in backend/
- [X] T003 Add 'analytics' to INSTALLED_APPS in backend/tremoai_backend/settings.py
- [X] T004 Create analytics directory structure: backend/analytics/services/, backend/analytics/utils/, backend/analytics/management/commands/
- [X] T005 Configure analytics URL routing in backend/tremoai_backend/urls.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core utilities that all user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T006 [P] Create statistics calculation utility for average amplitude in backend/analytics/utils/calculations.py
- [X] T007 [P] Create dominant frequency calculation utility in backend/analytics/utils/calculations.py
- [X] T008 [P] Create baseline calculation utility (first 3 sessions) in backend/analytics/utils/calculations.py
- [X] T009 [P] Create tremor reduction percentage calculation utility in backend/analytics/utils/calculations.py
- [X] T010 [P] Create ML severity summary aggregation utility in backend/analytics/utils/calculations.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Tremor Statistics Aggregation (Priority: P1) 🎯 MVP

**Goal**: Provide doctors with aggregated tremor statistics over time (by session or by day) including baseline comparison and ML severity summaries.

**Independent Test**: Use Scenario 1 and Scenario 2 from quickstart.md to query daily and session-level statistics for a test patient.

### Implementation for User Story 1

- [X] T011 [P] [US1] Create TremorStatistics serializer in backend/analytics/serializers.py
- [X] T012 [P] [US1] Create Baseline serializer in backend/analytics/serializers.py
- [X] T013 [P] [US1] Create StatisticsResponse serializer with pagination fields in backend/analytics/serializers.py
- [X] T014 [US1] Implement statistics service for session-level grouping in backend/analytics/services/statistics.py
- [X] T015 [US1] Implement statistics service for daily grouping in backend/analytics/services/statistics.py
- [X] T016 [US1] Implement GET /api/analytics/stats/ view with JWT authentication in backend/analytics/views.py
- [X] T017 [US1] Add patient access control (doctors: all assigned patients, patients: self only) in backend/analytics/views.py
- [X] T018 [US1] Add query parameter validation (patient_id required, date range validation, group_by enum) in backend/analytics/views.py
- [X] T019 [US1] Add DRF pagination support (PageNumberPagination with page_size=50) in backend/analytics/views.py
- [X] T020 [US1] Register GET /api/analytics/stats/ URL route in backend/analytics/urls.py
- [X] T021 [US1] Add error handling for edge cases (no sessions, invalid dates, unauthorized access) in backend/analytics/views.py

**Checkpoint**: At this point, User Story 1 should be fully functional - doctors can query statistics via REST API

---

## Phase 4: User Story 2 - PDF Report Generation (Priority: P2)

**Goal**: Enable doctors to generate downloadable PDF reports containing tremor statistics, trend charts, and ML prediction summaries.

**Independent Test**: Use Scenario 6 from quickstart.md to generate and download a PDF report for a test patient with multiple sessions.

### Implementation for User Story 2

- [X] T022 [P] [US2] Create chart generation utility for matplotlib line charts in backend/analytics/utils/charts.py
- [X] T023 [P] [US2] Create chart styling configuration (clinical theme, blue/gray palette) in backend/analytics/utils/charts.py
- [X] T024 [P] [US2] Create ReportRequest serializer with validation in backend/analytics/serializers.py
- [X] T025 [US2] Implement PDF report generator service using ReportLab in backend/analytics/services/report_generator.py
- [X] T026 [US2] Add patient information header section to PDF generator in backend/analytics/services/report_generator.py
- [X] T027 [US2] Add statistics summary table section to PDF generator in backend/analytics/services/report_generator.py
- [X] T028 [US2] Add chart embedding logic (save matplotlib PNG, embed in PDF) in backend/analytics/services/report_generator.py
- [X] T029 [US2] Add ML severity distribution section to PDF generator in backend/analytics/services/report_generator.py
- [X] T030 [US2] Implement POST /api/analytics/reports/ view with JWT authentication in backend/analytics/views.py
- [X] T031 [US2] Add temporary file creation in media/reports/ directory in backend/analytics/views.py
- [X] T032 [US2] Add PDF response with Content-Disposition header (attachment) in backend/analytics/views.py
- [X] T033 [US2] Add immediate file deletion after PDF download in backend/analytics/views.py
- [X] T034 [US2] Add PDF file size validation (reject if > 5MB per SC-004) in backend/analytics/services/report_generator.py
- [X] T035 [US2] Create cleanup_temp_reports Django management command in backend/analytics/management/commands/cleanup_temp_reports.py
- [X] T036 [US2] Implement 24-hour file deletion logic in cleanup command in backend/analytics/management/commands/cleanup_temp_reports.py
- [X] T037 [US2] Register POST /api/analytics/reports/ URL route in backend/analytics/urls.py
- [X] T038 [US2] Add error handling (no data, PDF generation failure, file size exceeded) in backend/analytics/views.py

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently - doctors can query stats and generate PDF reports

---

## Phase 5: User Story 3 - Report Customization (Priority: P3)

**Goal**: Allow doctors to customize PDF reports by toggling charts and ML summaries on/off.

**Independent Test**: Use variations of Scenario 6 from quickstart.md with include_charts=false and include_ml_summary=false parameters.

### Implementation for User Story 3

- [X] T039 [P] [US3] Extend ReportRequest serializer with include_charts boolean field (default true) in backend/analytics/serializers.py
- [X] T040 [P] [US3] Extend ReportRequest serializer with include_ml_summary boolean field (default true) in backend/analytics/serializers.py
- [X] T041 [US3] Implement conditional chart generation logic in PDF generator in backend/analytics/services/report_generator.py
- [X] T042 [US3] Implement conditional ML summary section logic in PDF generator in backend/analytics/services/report_generator.py
- [X] T043 [US3] Update POST /api/analytics/reports/ view to pass customization flags to generator in backend/analytics/views.py

**Checkpoint**: All user stories should now be independently functional - doctors have full control over report content

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories and optimize performance

- [X] T044 [P] Add database index on (patient_id, session_start) for BiometricSession in backend/biometrics/migrations/
- [X] T045 [P] Add database index on (session_start) for BiometricSession in backend/biometrics/migrations/
- [X] T046 [P] Document analytics API endpoints in backend/README.md or docs/
- [X] T047 [P] Add docstrings to statistics service methods in backend/analytics/services/statistics.py
- [X] T048 [P] Add docstrings to PDF generator service methods in backend/analytics/services/report_generator.py
- [X] T049 Run quickstart.md validation scenarios (manual testing guidance for all 10 scenarios)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Uses statistics service from US1 but independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Extends US2 report generation but independently testable

### Within Each User Story

- Serializers before services (data structures defined first)
- Services before views (business logic before API layer)
- Views before URL routing (handlers before routes)
- Core implementation before error handling
- Story complete before moving to next priority

### Parallel Opportunities

- **Phase 1 Setup**: T001-T005 can all run in parallel (independent initialization)
- **Phase 2 Foundational**: T006-T010 can all run in parallel (different utility functions)
- **Phase 3 US1**: T011-T013 serializers can run in parallel (different classes)
- **Phase 4 US2**: T022-T024 can run in parallel (charts, styling, serializer are independent)
- **Phase 5 US3**: T039-T040 can run in parallel (different serializer fields)
- **Phase 6 Polish**: T044-T048 can run in parallel (documentation, indexes, docstrings are independent)
- **Once Foundational completes**: User Stories 1, 2, 3 can be worked on in parallel by different developers

---

## Parallel Example: User Story 1

```bash
# Launch all serializers for User Story 1 together:
Task: "Create TremorStatistics serializer in backend/analytics/serializers.py"
Task: "Create Baseline serializer in backend/analytics/serializers.py"
Task: "Create StatisticsResponse serializer in backend/analytics/serializers.py"
```

## Parallel Example: User Story 2

```bash
# Launch chart and serializer tasks together:
Task: "Create chart generation utility in backend/analytics/utils/charts.py"
Task: "Create chart styling configuration in backend/analytics/utils/charts.py"
Task: "Create ReportRequest serializer in backend/analytics/serializers.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T005)
2. Complete Phase 2: Foundational (T006-T010) - CRITICAL, blocks all stories
3. Complete Phase 3: User Story 1 (T011-T021)
4. **STOP and VALIDATE**: Test statistics endpoint with Scenarios 1-5 from quickstart.md
5. Deploy/demo MVP if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test with Scenarios 1-5 → Deploy/Demo (MVP!)
3. Add User Story 2 → Test with Scenarios 6-8 → Deploy/Demo
4. Add User Story 3 → Test customization → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (T001-T010)
2. Once Foundational is done:
   - Developer A: User Story 1 (T011-T021)
   - Developer B: User Story 2 (T022-T038)
   - Developer C: User Story 3 (T039-T043)
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Use `py -m` prefix for Python commands (per user preference)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Success criteria validation:
  - SC-001: Statistics queries < 3 seconds (validate after T015 with Scenario 10)
  - SC-003: PDF generation < 10 seconds (validate after T030 with Scenario 7)
  - SC-004: PDF files < 5MB (validate after T034)
  - SC-006: Tremor reduction reflects actual trends (validate after T015 with Scenario 1)
