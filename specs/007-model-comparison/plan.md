# Implementation Plan: Model Comparison & Deployment Selection

**Branch**: `007-model-comparison` | **Date**: 2026-02-15 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/007-model-comparison/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

This feature implements a comprehensive model comparison and deployment selection system for the TremoAI platform. It compares all 4 trained tremor detection models (Random Forest, SVM, LSTM, 1D-CNN) side-by-side using standardized performance metrics (accuracy, precision, recall, F1-score, confusion matrices) and inference time benchmarks. The system generates visual comparison reports with charts, provides deployment recommendations based on accuracy-latency trade-offs, and facilitates formal decision documentation for graduation project deliverables. Primary deliverables include: (1) comparison script that loads all model metadata and runs inference benchmarks, (2) report generator producing Markdown and PDF outputs with executive summary, comparison tables, and visualization charts, and (3) deployment decision documentation system for recording and tracking model selection decisions.

**Technical Approach**: Backend-only Python implementation using existing models from Features 005 (ML Models: RF, SVM) and 006 (DL Models: LSTM, 1D-CNN). Comparison system loads model metadata (JSON), runs inference benchmarks on test dataset (87 samples), computes performance metrics, generates visualizations using Matplotlib, and exports reports using ReportLab for PDF generation. No database, API endpoints, or frontend UI required for MVP - standalone scripts producing file-based reports.

## Technical Context

**Backend Stack**: Python 3.x + scikit-learn + TensorFlow/Keras + Matplotlib + ReportLab + NumPy + pandas
**Frontend Stack**: Not applicable (backend-only feature)
**Database**: Not applicable (file-based report generation)
**Authentication**: Not applicable (local scripts)
**Testing**: pytest (unit tests for comparison logic, report generation)
**Project Type**: Backend scripts (standalone comparison and reporting system)
**Real-time**: Not applicable (batch report generation)
**Integration**: Loads model files from Features 005 and 006, reads test data from Feature 004
**AI/ML**: Loads scikit-learn models (.pkl) and TensorFlow/Keras models (.h5) for inference benchmarking
**Performance Goals**: Report generation <2 minutes, inference time measurements with <10% standard deviation
**Constraints**: Local development only, no Docker/CI/CD, depends on Features 004, 005, 006 completion
**Scale/Scope**: Compare 4 models, generate reports for 87-sample test dataset, support multiple report runs for decision tracking

**Key Libraries**:
- `scikit-learn`: Load and run inference for RF and SVM models
- `tensorflow`: Load and run inference for LSTM and 1D-CNN models
- `matplotlib`: Generate bar charts, heatmaps for confusion matrices
- `reportlab`: Export reports to PDF format
- `pandas`: Structure comparison tables, export to CSV
- `numpy`: Array operations for inference benchmarking
- `json`: Load/save model metadata and decision records

**File Dependencies**:
- **From Feature 005 (ML Models)**: `backend/ml_models/models/rf_model.pkl`, `rf_model.json`, `svm_model.pkl`, `svm_model.json`
- **From Feature 006 (DL Models)**: `backend/dl_models/models/lstm_model.h5`, `lstm_model.json`, `cnn_1d_model.h5`, `cnn_1d_model.json`
- **From Feature 004 (Data Prep)**: `backend/ml_data/processed/test_sequences.npy`, `test_seq_labels.npy`, `test_features.npy`, `test_labels.npy`

**Output Artifacts**:
- `backend/model_comparison/reports/comparison_report.md` (Markdown report)
- `backend/model_comparison/reports/comparison_report.pdf` (PDF report)
- `backend/model_comparison/reports/comparison_data.json` (structured JSON data)
- `backend/model_comparison/reports/comparison_data.csv` (CSV table)
- `backend/model_comparison/reports/charts/accuracy_comparison.png`
- `backend/model_comparison/reports/charts/confusion_matrices.png`
- `backend/model_comparison/reports/charts/inference_time_comparison.png`
- `backend/model_comparison/decisions/decision_[timestamp].md` (deployment decisions)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Validate this feature against `.specify/memory/constitution.md` principles:

- [X] **Monorepo Architecture**: Feature fits in `backend/` structure (backend/model_comparison/)
- [X] **Tech Stack Immutability**: Uses Python, Matplotlib, ReportLab (already in requirements.txt from Feature 003)
- [X] **Database Strategy**: No database access (file-based report generation)
- [X] **Authentication**: Not applicable (local scripts, no API)
- [X] **Security-First**: No secrets needed (reads local model files)
- [X] **Real-time Requirements**: Not applicable (batch processing)
- [X] **MQTT Integration**: Not applicable
- [X] **AI Model Serving**: Loads existing models (.pkl, .h5) for inference benchmarking
- [X] **API Standards**: Not applicable (scripts only, no API endpoints for MVP)
- [X] **Development Scope**: Local development only (no Docker/CI/CD/production)

**Result**: ✅ ALL PASS

**Justification**: This is a purely backend-focused reporting and analysis feature. It extends existing Features 005 and 006 by adding comparison and decision-making capabilities. No new frameworks, no database changes, no authentication requirements. Uses only libraries already approved and present in requirements.txt (Matplotlib from Feature 003, TensorFlow from Feature 006, scikit-learn from Feature 005).

**Re-check after Phase 1**: ✅ ALL PASS (no changes to constitutional compliance)

## Project Structure

### Documentation (this feature)

```text
specs/007-model-comparison/
├── spec.md              # Feature specification (completed via /speckit.specify)
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (technical decisions)
├── data-model.md        # Phase 1 output (entities: Model Comparison Record, etc.)
├── quickstart.md        # Phase 1 output (test scenarios for comparison reports)
├── checklists/
│   └── requirements.md  # Specification quality checklist (completed)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created yet)
```

### Source Code (repository root)

```text
backend/
├── model_comparison/              # New Django app for model comparison
│   ├── __init__.py
│   ├── scripts/
│   │   ├── __init__.py
│   │   ├── compare_all_models.py      # Main comparison script (loads all 4 models)
│   │   ├── benchmark_inference.py     # Inference time measurement utility
│   │   ├── generate_report.py         # Report generation (Markdown + PDF)
│   │   └── document_decision.py       # Deployment decision documentation
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── model_loader.py            # Load ML/DL models (unified interface)
│   │   ├── metrics_extractor.py       # Extract metrics from metadata files
│   │   ├── chart_generator.py         # Generate Matplotlib charts
│   │   └── report_formatter.py        # Format comparison tables
│   ├── reports/                       # Output directory for reports (gitignored)
│   │   ├── .gitkeep                   # Keep directory in git
│   │   └── charts/                    # Generated chart images
│   │       └── .gitkeep
│   ├── decisions/                     # Deployment decision logs (gitignored)
│   │   └── .gitkeep
│   └── README.md                      # Usage instructions
│
├── tests/
│   └── test_model_comparison/
│       ├── test_model_loader.py
│       ├── test_metrics_extractor.py
│       ├── test_chart_generator.py
│       ├── test_report_formatter.py
│       └── test_compare_all_models.py
│
└── requirements.txt                   # No new dependencies needed
```

**Structure Decision**:

This feature creates a new `backend/model_comparison/` directory containing:
1. **scripts/**: Four main scripts for comparison, benchmarking, report generation, and decision documentation
2. **utils/**: Reusable modules for model loading, metrics extraction, chart generation, and report formatting
3. **reports/**: Output directory for generated comparison reports (Markdown, PDF, JSON, CSV) and chart images
4. **decisions/**: Output directory for deployment decision documentation files

**No Frontend**: This is a backend-only feature for MVP. Future Feature 008 may add a web UI for interactive comparison dashboards.

**No API Endpoints**: Scripts are run locally via command line. Future Feature 007 (Model Serving API) may expose comparison data via REST endpoints.

**No Database Tables**: All data is file-based (model files, metadata JSON, output reports). No Django models needed for MVP.

**Integration Points**:
- Reads model files from `backend/ml_models/models/` and `backend/dl_models/models/`
- Reads test data from `backend/ml_data/processed/`
- Uses existing libraries: Matplotlib (Feature 003), TensorFlow (Feature 006), scikit-learn (Feature 005)

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No constitutional violations. This section is not applicable.

## Phase 0: Research (Technical Decisions)

See [research.md](./research.md) for detailed technical research and decisions.

## Phase 1: Design (Data Model & Contracts)

### Data Model

See [data-model.md](./data-model.md) for entity definitions and relationships.

**Key Entities**:
- **Model Comparison Record**: Aggregates metrics from all 4 models
- **Inference Benchmark**: Stores inference time measurements
- **Deployment Decision**: Documents model selection decisions

### API Contracts

**Not Applicable**: This feature does not expose API endpoints in the MVP. All functionality is script-based for local execution.

Future Feature 008 (Model Comparison Dashboard) may add REST API endpoints like:
- `GET /api/model-comparison/` - Retrieve latest comparison report
- `GET /api/model-comparison/decisions/` - List deployment decisions
- `POST /api/model-comparison/decisions/` - Record new deployment decision

For now, contracts/ directory is omitted.

### Integration Scenarios

See [quickstart.md](./quickstart.md) for validation scenarios and usage examples.

## Implementation Notes

### Execution Order
1. **User Story 1 (P1-MVP)**: Comparison report generation
   - Implement model loader for all 4 model types
   - Implement inference benchmarking system
   - Generate comparison tables and charts
   - Export Markdown and PDF reports
   - Test with all 4 models present

2. **User Story 2 (P2)**: Deployment decision documentation
   - Implement decision recording system
   - Add decision history tracking
   - Export decision documentation (Markdown + PDF)
   - Test decision update workflow

### Critical Dependencies
- **BLOCKING**: Features 004, 005, 006 must be complete
- **BLOCKING**: All 4 models must be trained and metadata files present
- **BLOCKING**: Test dataset must be available in `backend/ml_data/processed/`

### Testing Strategy
- Unit tests for each utility module (model_loader, metrics_extractor, chart_generator, report_formatter)
- Integration test for full comparison workflow with mock models
- End-to-end test with actual trained models from Features 005 and 006
- Validate report generation (Markdown, PDF, JSON, CSV)
- Validate chart generation (accuracy, confusion matrices, inference time)
- Test missing model graceful handling
- Test inference time measurement reliability (standard deviation validation)

### Performance Considerations
- Inference benchmarking should run 10+ iterations after warmup for reliable measurements
- Exclude outliers beyond 2 standard deviations
- Parallel model loading where possible (though 4 models is small scale)
- Chart generation should be optimized for quick rendering
- PDF generation may take 10-30 seconds for multi-page report with charts

### Edge Case Handling
- Missing models: Generate partial report with warnings
- Different test set sizes: Validate and fail with clear error
- Inference time variability: Use statistical aggregation (mean ± std)
- Performance ties: Recommend both models or use latency tiebreaker
- Zero trained models: Exit with error message directing to Features 005/006
- Missing confusion matrix: Reconstruct from model predictions or mark unavailable

### Maintenance & Extensions
- Decision documentation supports versioning and history tracking
- Comparison data exported as JSON for future analysis/integration
- Modular design allows easy addition of new metrics or visualizations
- Report templates can be customized for different stakeholders
- Future: Web UI for interactive comparison (Feature 008)
- Future: Real-time model monitoring dashboard
- Future: Automated model selection based on configurable thresholds
