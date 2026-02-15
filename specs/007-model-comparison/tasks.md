---

description: "Task list for Model Comparison & Deployment Selection feature"
---

# Tasks: Model Comparison & Deployment Selection

**Input**: Design documents from `/specs/007-model-comparison/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, quickstart.md ✓

**Tests**: NOT REQUESTED - No test tasks included (feature spec does not explicitly request TDD approach)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `backend/model_comparison/` (this is a backend-only feature)
- **No frontend**: This feature has no UI components for MVP
- **No API endpoints**: Scripts run locally via command line

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and directory structure creation

- [X] T001 Create backend/model_comparison/ directory structure per implementation plan
- [X] T002 [P] Create backend/model_comparison/__init__.py package initializer
- [X] T003 [P] Create backend/model_comparison/scripts/__init__.py package initializer
- [X] T004 [P] Create backend/model_comparison/utils/__init__.py package initializer
- [X] T005 [P] Create backend/model_comparison/reports/ output directory with .gitkeep
- [X] T006 [P] Create backend/model_comparison/reports/charts/ subdirectory with .gitkeep
- [X] T007 [P] Create backend/model_comparison/decisions/ output directory with .gitkeep
- [X] T008 Update backend/.gitignore to exclude generated reports and decisions (*.md, *.pdf, *.json, *.csv, *.png in reports/ and decisions/ directories)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core utility modules that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T009 [P] Create backend/model_comparison/utils/model_loader.py with ModelLoader class (unified interface for loading .pkl and .h5 models)
- [X] T010 [P] Implement ModelLoader.load_model() method supporting scikit-learn (.pkl via joblib) and TensorFlow (.h5 via tf.keras.models.load_model)
- [X] T011 [P] Implement ModelLoader.load_metadata() method to parse JSON metadata files
- [X] T012 [P] Create backend/model_comparison/utils/metrics_extractor.py with MetricsExtractor class
- [X] T013 [P] Implement MetricsExtractor.extract_from_metadata() to parse accuracy, precision, recall, F1, confusion matrix from JSON
- [X] T014 [P] Create backend/model_comparison/utils/chart_generator.py with ChartGenerator class
- [X] T015 [P] Implement ChartGenerator.generate_accuracy_chart() using Matplotlib bar chart with color-coded bars (green ≥95%, yellow 90-95%, red <90%)
- [X] T016 [P] Implement ChartGenerator.generate_confusion_matrices() using Matplotlib heatmaps (2×2 layout for 4 models)
- [X] T017 [P] Implement ChartGenerator.generate_inference_time_chart() using Matplotlib bar chart with error bars (mean ± std dev)
- [X] T018 [P] Create backend/model_comparison/utils/report_formatter.py with ReportFormatter class
- [X] T019 [P] Implement ReportFormatter.format_comparison_table() to generate Markdown table from comparison data
- [X] T020 [P] Implement ReportFormatter.generate_recommendation() with threshold-based decision tree (95% accuracy, 1% tie threshold, latency tiebreaker)
- [X] T021 [P] Implement ReportFormatter.export_to_pdf() using ReportLab to convert Markdown to PDF with embedded charts

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Generate Comprehensive Model Comparison Report (Priority: P1-MVP) 🎯

**Goal**: Compare all 4 trained models (RF, SVM, LSTM, 1D-CNN) and generate comprehensive comparison reports with metrics, charts, and deployment recommendation.

**Independent Test**: Run compare_all_models.py with all 4 trained models present, verify report contains accurate metrics for all models, at least 3 charts, comparison table, and deployment recommendation. Check that reports exported in Markdown, PDF, JSON, and CSV formats.

### Implementation for User Story 1

- [X] T022 [US1] Create backend/model_comparison/scripts/compare_all_models.py main comparison script
- [X] T023 [US1] Implement argument parser with --input-ml-dir, --input-dl-dir, --output-dir, --validate-consistency flags
- [X] T024 [US1] Implement load_all_models() function to load all 4 models (RF, SVM, LSTM, 1D-CNN) using ModelLoader, handle missing models gracefully with warnings
- [X] T025 [US1] Implement validate_test_dataset_consistency() to check all models evaluated on same test set (87 samples), error if mismatch detected
- [X] T026 [US1] Implement load_test_datasets() to load test_sequences.npy (DL: 87×128×6), test_seq_labels.npy, test_features.npy (ML: 87×18), test_labels.npy from backend/ml_data/processed/
- [X] T027 [US1] Create backend/model_comparison/scripts/benchmark_inference.py inference time measurement utility
- [X] T028 [US1] Implement benchmark_model() function with 3 warmup iterations + 10 timed iterations using time.perf_counter(), exclude outliers >2σ, return mean ± std dev
- [X] T029 [US1] Implement run_all_benchmarks() to measure inference time for all 4 models, validate std dev <10% of mean per SC-004, log warnings if exceeded
- [X] T030 [US1] Integrate benchmark_inference.py into compare_all_models.py to measure inference times after model loading
- [X] T031 [US1] Implement extract_all_metrics() using MetricsExtractor to parse performance metrics from all model metadata files
- [X] T032 [US1] Implement create_comparison_records() to build Model Comparison Record objects for each model (attributes per data-model.md)
- [X] T033 [US1] Implement rank_models() to rank by accuracy (primary) and inference time (secondary), assign ranking 1-4
- [X] T034 [US1] Generate all visualization charts by calling ChartGenerator methods, save to backend/model_comparison/reports/charts/ as PNG (300 DPI)
- [X] T035 [US1] Create backend/model_comparison/scripts/generate_report.py report generation script
- [X] T036 [US1] Implement generate_executive_summary() to create 1-2 paragraph summary with key findings and recommendation
- [X] T037 [US1] Implement format_comparison_table_markdown() using ReportFormatter to create side-by-side comparison table (Model, Type, Accuracy, Precision, Recall, F1, Inference, Ranking)
- [X] T038 [US1] Implement embed_charts_in_markdown() to include chart image paths in Markdown report
- [X] T039 [US1] Implement generate_markdown_report() to assemble full report: executive summary, comparison table, embedded charts, recommendation, metadata appendix
- [X] T040 [US1] Implement export_to_pdf() in generate_report.py to convert Markdown to PDF using ReportFormatter.export_to_pdf()
- [X] T041 [US1] Implement export_to_json() to save comparison data as structured JSON (schema per data-model.md Comparison Report entity)
- [X] T042 [US1] Implement export_to_csv() to export comparison table as CSV using pandas DataFrame
- [X] T043 [US1] Integrate generate_report.py into compare_all_models.py to export all 4 formats (Markdown, PDF, JSON, CSV) after comparison complete
- [X] T044 [US1] Implement missing_models_warning_banner() to display prominent warning in reports if partial comparison (< 4 models), list missing models with training commands
- [X] T045 [US1] Implement zero_models_error_check() to exit with clear error if no trained models found: "No trained models found. Please complete Features 005 and 006 first."
- [X] T046 [US1] Add logging throughout compare_all_models.py using Python logging module (INFO level: progress, WARNING: missing models/inconsistencies, ERROR: failures)
- [X] T047 [US1] Implement main() function in compare_all_models.py to orchestrate full workflow: load models → validate consistency → benchmark inference → extract metrics → rank → generate charts → generate reports → save all formats
- [X] T048 [US1] Add execution time tracking (start to finish) and validate < 120 seconds per SC-001, log warning if exceeded

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently. Run comparison script to generate reports for all 4 models.

---

## Phase 4: User Story 2 - Facilitate Deployment Decision Documentation (Priority: P2)

**Goal**: Document deployment decisions with clear rationale, selected model(s), trade-off analysis, and supervisor approval. Support decision history tracking.

**Independent Test**: Run document_decision.py to record a deployment decision, verify decision file created with YAML front matter and Markdown body, all required fields populated (decision_id, selected_models, rationale, supervisor, timestamp), PDF export generated, decision can be updated with change history preserved.

### Implementation for User Story 2

- [X] T049 [US2] Create backend/model_comparison/scripts/document_decision.py deployment decision documentation script
- [X] T050 [US2] Implement argument parser with --model (selected model name), --supervisor (name), --rationale (text), --alternatives (rejected models with reasons), --interactive (flag for interactive mode)
- [X] T051 [US2] Implement load_comparison_report() to read latest comparison_data.json for decision context (model metrics, rankings)
- [X] T052 [US2] Implement generate_decision_id() to create UUID for unique decision identification
- [X] T053 [US2] Implement create_decision_yaml_frontmatter() to generate YAML metadata: decision_id, timestamp (ISO 8601), supervisor_name, selected_models (list), approval_status (DRAFT/APPROVED), accuracy_threshold_met (boolean), latency_consideration (enum), metrics_snapshot (dict)
- [X] T054 [US2] Implement format_decision_markdown_body() to create structured Markdown: Decision Summary, Metrics Snapshot, Alternative Models Considered (table with rejection reasons), Trade-off Analysis, Approval section, Change History
- [X] T055 [US2] Implement generate_trade_off_analysis() to explain why selected model chosen over alternatives (accuracy vs latency reasoning, medical application priorities)
- [X] T056 [US2] Implement save_decision_file() to write decision as Markdown with YAML front matter, filename: decision_YYYY-MM-DD_HHmmss.md in backend/model_comparison/decisions/
- [X] T057 [US2] Implement export_decision_to_pdf() to convert decision Markdown to PDF using ReportLab, save as decision_YYYY-MM-DD_HHmmss.pdf
- [X] T058 [US2] Implement update_existing_decision() function with --update flag to modify existing decision (change approval status, add notes)
- [X] T059 [US2] Implement append_to_change_history() to track decision updates: timestamp, change_type (CREATED/UPDATED/APPROVED), changed_by, change_notes
- [X] T060 [US2] Implement interactive_decision_mode() with prompts for: model selection (from comparison report), supervisor name, rationale (multi-line input), alternatives (interactive list with reasons)
- [X] T061 [US2] Add validation: selected_models must reference valid model names from comparison report, rationale cannot be empty, supervisor name required
- [X] T062 [US2] Implement decision_history_listing() to scan decisions/ directory and list all decisions chronologically with summary (decision ID, date, selected model, status)
- [X] T063 [US2] Add logging for decision documentation workflow (INFO: decision created/updated, WARNING: validation issues, ERROR: file write failures)
- [X] T064 [US2] Implement main() function in document_decision.py to orchestrate: load comparison → generate decision ID → create YAML + Markdown → save file → export PDF → log completion

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently. Comparison report can be generated (US1), and deployment decisions can be documented (US2).

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, validation, and final improvements

- [X] T065 [P] Create backend/model_comparison/README.md with comprehensive usage instructions
- [X] T066 [P] Document comparison script usage in README: prerequisites (Features 004/005/006 complete), command-line examples, expected output, troubleshooting section
- [X] T067 [P] Document decision documentation usage in README: interactive and non-interactive modes, decision update workflow, decision history listing
- [X] T068 [P] Add quickstart examples to README: Example 1 (run complete comparison), Example 2 (benchmark single model), Example 3 (document decision), Example 4 (export data)
- [X] T069 [P] Document troubleshooting common issues in README: missing models error, ModuleNotFoundError for matplotlib/reportlab, chart generation TclError (headless environment), PDF generation slow, data consistency validation errors
- [X] T070 [P] Add performance benchmarks section to README: expected training times, report generation time (<2 minutes target), inference time measurements reliability (std dev <10%)
- [X] T071 Validate all tasks complete by running compare_all_models.py with all 4 models from Features 005 and 006, verify SC-001 through SC-010 success criteria met
- [X] T072 Run quickstart.md validation scenarios: Scenario 1 (complete comparison), Scenario 2 (partial comparison with missing models), Scenario 3 (inference time reliability), Scenario 4 (recommendation logic), Scenario 5 (decision documentation), Scenario 6 (decision history), Scenario 7 (data consistency validation)
- [X] T073 [P] Code cleanup: remove debug print statements, ensure consistent logging, verify all file paths use os.path.join for cross-platform compatibility
- [X] T074 [P] Add command-line help text (--help flag) to all scripts with usage examples and argument descriptions
- [X] T075 [P] Verify .gitignore excludes all generated outputs: reports/*.md, reports/*.pdf, reports/*.json, reports/*.csv, reports/charts/*.png, decisions/*.md, decisions/*.pdf
- [X] T076 Final validation: Generate comparison report with actual trained models, document deployment decision, verify all artifacts (Markdown, PDF, JSON, CSV, charts) generated successfully
- [X] T077 Create timestamped backup of comparison reports with naming: comparison_report_YYYY-MM-DD.md and comparison_report_YYYY-MM-DD.pdf for historical tracking

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion (Phase 1) - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational (Phase 2) completion - Can start immediately after Phase 2
- **User Story 2 (Phase 4)**: Depends on Foundational (Phase 2) completion - Can start after Phase 2, but typically runs after US1 since it references comparison reports
- **Polish (Phase 5)**: Depends on User Stories 1 and 2 completion

### User Story Dependencies

- **User Story 1 (P1-MVP)**: Can start after Foundational (Phase 2) - No dependencies on other stories
  - Delivers: Comparison report generation system
  - Independently testable: Run compare_all_models.py and verify reports generated

- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - References US1 comparison reports but is independently testable
  - Delivers: Deployment decision documentation system
  - Independently testable: Run document_decision.py with mock comparison data
  - Natural workflow: Runs after US1 comparison report exists, but code is independent

### Within Each User Story

**User Story 1 (Comparison Report)**:
- T022-T026: Load models and test data (can be parallel after T022)
- T027-T030: Benchmark inference time (depends on models loaded)
- T031-T033: Extract metrics and rank (depends on benchmarks)
- T034: Generate charts (depends on metrics)
- T035-T043: Generate reports (depends on charts)
- T044-T048: Error handling and validation (parallel with main workflow)

**User Story 2 (Decision Documentation)**:
- T049-T052: Setup and load context
- T053-T056: Create decision document
- T057: Export to PDF
- T058-T059: Update functionality (parallel development)
- T060-T064: Interactive mode and validation (parallel development)

### Parallel Opportunities

- **Phase 1 (Setup)**: All tasks T002-T007 can run in parallel (creating different files/directories)
- **Phase 2 (Foundational)**: All tasks T009-T021 can run in parallel (creating different utility modules)
- **User Story 1**: Tasks within same step can be parallel:
  - T024-T026: Model and data loading (different concerns)
  - T044-T045: Error handling (different scenarios)
- **User Story 2**: Tasks within same step can be parallel:
  - T058-T059, T060-T064: Different features of decision system
- **Phase 5 (Polish)**: All T065-T070 documentation tasks can run in parallel

---

## Parallel Example: User Story 1

```bash
# Parallel: Create all foundational utility modules together (Phase 2)
Task T009: "Create backend/model_comparison/utils/model_loader.py"
Task T012: "Create backend/model_comparison/utils/metrics_extractor.py"
Task T014: "Create backend/model_comparison/utils/chart_generator.py"
Task T018: "Create backend/model_comparison/utils/report_formatter.py"

# Sequential within US1: Load models → Benchmark → Generate charts → Generate reports
Task T024: "Load all 4 models" (must complete first)
  ↓
Task T029: "Run inference benchmarks" (depends on models loaded)
  ↓
Task T034: "Generate visualization charts" (depends on benchmark data)
  ↓
Task T043: "Export all report formats" (depends on charts)
```

---

## Parallel Example: User Story 2

```bash
# Parallel: Different decision system features can be developed together
Task T058: "Implement update_existing_decision()"
Task T060: "Implement interactive_decision_mode()"
Task T062: "Implement decision_history_listing()"

# All three features are independent and work on different aspects of decision system
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (8 tasks) - ~15 minutes
2. Complete Phase 2: Foundational (13 tasks) - ~2 hours
3. Complete Phase 3: User Story 1 (27 tasks) - ~4-5 hours
4. **STOP and VALIDATE**: Test User Story 1 independently
   - Run compare_all_models.py with all 4 trained models
   - Verify reports generated: Markdown, PDF, JSON, CSV
   - Verify 3 charts generated: accuracy, confusion matrices, inference time
   - Verify recommendation logic correct
   - Validate SC-001 through SC-010 success criteria
5. **MVP COMPLETE**: Comparison report system ready for supervisor review

**MVP Deliverable**: Functional comparison report generator that Dr. Reem can use to evaluate all 4 models and make deployment decision.

### Incremental Delivery

1. **Setup + Foundational** (Phase 1 + 2): Foundation ready - ~2.5 hours
2. **Add User Story 1** (Phase 3): Test independently → **Deploy/Demo (MVP!)** - ~5 hours total
   - Deliverable: Comparison reports with charts and recommendation
   - Value: Dr. Reem can objectively evaluate all models
3. **Add User Story 2** (Phase 4): Test independently → **Deploy/Demo** - ~7 hours total
   - Deliverable: Deployment decision documentation system
   - Value: Formal decision records for graduation project deliverables
4. **Polish** (Phase 5): Documentation and validation → **Final Release** - ~8 hours total
   - Deliverable: Complete, documented, validated comparison system
   - Value: Production-ready system with comprehensive usage instructions

### Parallel Team Strategy

With multiple developers:

1. **Team completes Setup + Foundational together** (Phase 1 + 2): All hands on deck to build foundation
2. **Once Foundational is done, split work**:
   - **Developer A**: User Story 1 (Phase 3) - Comparison report generation
   - **Developer B**: User Story 2 (Phase 4) - Decision documentation
   - Both can work in parallel since they depend only on Phase 2, not each other
3. **Converge for Polish** (Phase 5): Team collaborates on documentation and validation
4. **Total time**: ~4-5 hours with 2 developers (vs ~8 hours sequential)

---

## Critical Path

**Longest dependency chain** (tasks that MUST be sequential):

1. T001: Create directory structure
2. T009: Create model_loader.py (depends on directories)
3. T024: Load all 4 models (depends on ModelLoader)
4. T029: Run inference benchmarks (depends on loaded models)
5. T034: Generate charts (depends on benchmark data)
6. T043: Export reports (depends on charts)
7. T071: Validate complete system (depends on all reports)

**Critical path duration**: ~5-6 hours (cannot be reduced by parallelization)

---

## Blocking Dependencies

### Feature 004 (ML/DL Data Preparation) - REQUIRED
- **Blocks**: T026 (load test datasets)
- **Required files**:
  - backend/ml_data/processed/test_sequences.npy (87 × 128 × 6)
  - backend/ml_data/processed/test_seq_labels.npy (87)
  - backend/ml_data/processed/test_features.npy (87 × 18)
  - backend/ml_data/processed/test_labels.npy (87)
- **Status**: Must be complete before Phase 3 (User Story 1)

### Feature 005 (ML Models Training) - REQUIRED
- **Blocks**: T024 (load ML models - RF, SVM)
- **Required files**:
  - backend/ml_models/models/rf_model.pkl
  - backend/ml_models/models/rf_model.json
  - backend/ml_models/models/svm_model.pkl
  - backend/ml_models/models/svm_model.json
- **Status**: Must be complete before Phase 3 (User Story 1)

### Feature 006 (DL Models Training) - REQUIRED
- **Blocks**: T024 (load DL models - LSTM, 1D-CNN)
- **Required files**:
  - backend/dl_models/models/lstm_model.h5
  - backend/dl_models/models/lstm_model.json
  - backend/dl_models/models/cnn_1d_model.h5
  - backend/dl_models/models/cnn_1d_model.json
- **Status**: Must be complete before Phase 3 (User Story 1)

**NOTE**: If Features 005 or 006 are incomplete, comparison script will generate partial reports with warnings (per T044), but full validation requires all 4 models.

---

## Notes

- **[P] tasks**: Different files, no dependencies - can run in parallel
- **[Story] label**: Maps task to specific user story for traceability
- **No tests**: Feature specification does not explicitly request TDD approach, so test tasks are omitted
- **Each user story independently testable**:
  - User Story 1: Run compare_all_models.py and verify reports generated
  - User Story 2: Run document_decision.py and verify decision files created
- **Commit strategy**: Commit after completing each utility module (Phase 2) and each main script (Phase 3-4)
- **Stop at checkpoints**: Validate User Story 1 before starting User Story 2 to ensure MVP works
- **Backend-only feature**: No frontend UI, no API endpoints, no database tables for MVP
- **File-based outputs**: All reports and decisions stored as files (Markdown, PDF, JSON, CSV)
- **Dependencies**: All required libraries already in requirements.txt (Matplotlib, ReportLab, TensorFlow, scikit-learn, NumPy, pandas)
- **Execution time**: Total estimated ~8 hours for sequential implementation, ~4-5 hours with parallel team

---

## Task Count Summary

| Phase | Task Count | Estimated Duration |
|-------|------------|-------------------|
| Phase 1: Setup | 8 tasks | ~15 minutes |
| Phase 2: Foundational | 13 tasks | ~2 hours |
| Phase 3: User Story 1 (P1-MVP) | 27 tasks | ~4-5 hours |
| Phase 4: User Story 2 (P2) | 16 tasks | ~2 hours |
| Phase 5: Polish | 13 tasks | ~1.5 hours |
| **TOTAL** | **77 tasks** | **~8-10 hours** |

**Parallel Opportunities**:
- Phase 1: 6 parallel tasks (T002-T007)
- Phase 2: 13 parallel tasks (T009-T021) - all foundational utilities
- Phase 3: 2-3 parallel tasks within implementation steps
- Phase 4: 3-4 parallel tasks for different decision features
- Phase 5: 6 parallel tasks (T065-T070) for documentation

**MVP Scope** (Phases 1 + 2 + 3): 48 tasks, ~6.5 hours → **Deliverable**: Comparison report generator functional

**Full Feature** (All phases): 77 tasks, ~8-10 hours → **Deliverable**: Complete comparison and decision documentation system
