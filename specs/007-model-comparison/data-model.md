# Data Model: Model Comparison & Deployment Selection

**Feature**: 007-model-comparison
**Phase**: Phase 1 - Data Model Design
**Date**: 2026-02-15

## Overview

This document defines the logical data entities for the model comparison and deployment selection system. Note that this feature does NOT use database storage for MVP - all entities are represented as in-memory Python data structures and persisted as JSON files. Future Feature 008 (Model Comparison Dashboard) may add database persistence.

## Entity Definitions

### 1. Model Comparison Record

**Purpose**: Aggregates performance metrics from a single trained model for comparison purposes.

**Attributes**:
- `model_name` (string, required): Unique model identifier (e.g., "rf", "svm", "lstm", "cnn_1d")
- `model_display_name` (string, required): Human-readable name (e.g., "Random Forest", "LSTM")
- `model_type` (enum, required): Model category - "ML" (scikit-learn) or "DL" (TensorFlow/Keras)
- `model_file_path` (string, required): Absolute path to model file (.pkl or .h5)
- `metadata_file_path` (string, required): Absolute path to metadata JSON file
- `accuracy` (float, required): Test accuracy as decimal (0.0 to 1.0)
- `precision` (float, required): Test precision as decimal (0.0 to 1.0)
- `recall` (float, required): Test recall as decimal (0.0 to 1.0)
- `f1_score` (float, required): Test F1-score as decimal (0.0 to 1.0)
- `confusion_matrix` (2D array, required): 2×2 confusion matrix [[TN, FP], [FN, TP]]
- `inference_time_ms` (float, required): Mean inference time in milliseconds
- `inference_time_std` (float, required): Standard deviation of inference time in milliseconds
- `test_samples_count` (integer, required): Number of test samples used for evaluation (expected: 87)
- `meets_threshold_95` (boolean, required): True if accuracy ≥ 0.95, False otherwise
- `ranking` (integer, optional): Overall rank (1 = best, 4 = worst) based on accuracy (primary) and inference time (secondary)
- `training_timestamp` (datetime, required): When the model was trained (from metadata)
- `feature_dimensions` (object, required): Input feature shape (e.g., {"timesteps": 128, "features": 6} for DL, {"features": 18} for ML)

**Relationships**:
- One-to-many with **Inference Benchmark**: Each model has multiple inference time measurements
- Referenced by **Deployment Decision**: Decision records which models were considered

**Validation Rules**:
- `accuracy`, `precision`, `recall`, `f1_score` must be in range [0.0, 1.0]
- `confusion_matrix` must be 2×2 array with non-negative integers
- `inference_time_ms` must be > 0
- `inference_time_std` should be < 10% of `inference_time_ms` per SC-004 (warning if exceeded)
- `test_samples_count` should be 87 (warning if different)
- `ranking` must be 1-4 if present

**File Representation** (JSON):
```json
{
  "model_name": "lstm",
  "model_display_name": "LSTM",
  "model_type": "DL",
  "model_file_path": "C:/Data from HDD/.../backend/dl_models/models/lstm_model.h5",
  "metadata_file_path": "C:/Data from HDD/.../backend/dl_models/models/lstm_model.json",
  "accuracy": 0.965,
  "precision": 0.962,
  "recall": 0.968,
  "f1_score": 0.965,
  "confusion_matrix": [[42, 2], [1, 42]],
  "inference_time_ms": 48.3,
  "inference_time_std": 3.1,
  "test_samples_count": 87,
  "meets_threshold_95": true,
  "ranking": 1,
  "training_timestamp": "2026-02-15T12:34:56Z",
  "feature_dimensions": {
    "timesteps": 128,
    "features": 6
  }
}
```

---

### 2. Inference Benchmark

**Purpose**: Stores individual inference time measurements for a model during benchmarking. Used to compute mean, standard deviation, and identify outliers.

**Attributes**:
- `benchmark_id` (string, required): Unique benchmark run identifier (UUID)
- `model_name` (string, required): Model identifier (FK to Model Comparison Record)
- `run_id` (integer, required): Sequential run number (0 = warmup, 1+ = timed runs)
- `is_warmup` (boolean, required): True if warmup iteration, False if timed iteration
- `sample_id` (integer, optional): Test sample index (0-86) if measuring per-sample time, null if batch prediction
- `inference_time_ms` (float, required): Measured inference time in milliseconds for this run
- `timestamp` (datetime, required): When measurement was taken
- `hardware_info` (object, required): Hardware context (CPU vs GPU)
  - `device_type` (string): "CPU" or "GPU"
  - `device_name` (string): Device name (e.g., "Intel Core i7-9700K", "NVIDIA RTX 3060")
  - `memory_available_mb` (integer): Available system RAM in MB
- `is_outlier` (boolean, required): True if measurement excluded from statistics (>2σ from mean)

**Relationships**:
- Many-to-one with **Model Comparison Record**: Multiple measurements per model

**Validation Rules**:
- `inference_time_ms` must be > 0
- `run_id` for warmup should be negative or 0, timed runs should be 1+
- `sample_id` should be 0-86 if present
- Outlier detection: `is_outlier = abs(time - mean) > 2 * std_dev`

**File Representation** (JSON array within comparison_data.json):
```json
{
  "benchmarks": [
    {
      "benchmark_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "model_name": "lstm",
      "run_id": 1,
      "is_warmup": false,
      "sample_id": null,
      "inference_time_ms": 47.8,
      "timestamp": "2026-02-15T14:25:10.123Z",
      "hardware_info": {
        "device_type": "CPU",
        "device_name": "Intel Core i7-9700K",
        "memory_available_mb": 16384
      },
      "is_outlier": false
    }
  ]
}
```

**Usage**:
- Generated during inference benchmarking phase
- Used to compute `inference_time_ms` and `inference_time_std` for Model Comparison Record
- Stored for transparency and reproducibility analysis
- Can be reviewed to identify hardware bottlenecks or measurement anomalies

---

### 3. Deployment Decision

**Purpose**: Documents a formal model selection decision made by the supervisor (Dr. Reem) for deployment. Supports decision history tracking and rationale documentation.

**Attributes**:
- `decision_id` (string, required): Unique decision identifier (UUID)
- `decision_date` (datetime, required): When decision was made
- `supervisor_name` (string, required): Name of decision maker (e.g., "Dr. Reem")
- `selected_models` (array<string>, required): List of model names selected for deployment (usually 1, may be 2+ for ensemble)
- `rationale_text` (string, required): Detailed explanation of why model(s) were selected
- `accuracy_threshold_met` (boolean, required): True if selected model(s) meet ≥95% accuracy
- `latency_consideration` (string, required): How inference time influenced decision ("not_considered", "tiebreaker", "primary_factor")
- `alternative_models_considered` (array<object>, required): Models evaluated but not selected
  - `model_name` (string): Name of alternative model
  - `reason_rejected` (string): Why not selected (e.g., "Lower accuracy", "Too slow")
- `approval_status` (enum, required): Decision status - "DRAFT", "UNDER_REVIEW", "APPROVED", "REJECTED"
- `comparison_report_path` (string, required): Path to comparison report that informed this decision
- `metrics_snapshot` (object, required): Key metrics of selected model(s) at decision time
  - `accuracy` (float)
  - `precision` (float)
  - `recall` (float)
  - `f1_score` (float)
  - `inference_time_ms` (float)
- `change_history` (array<object>, optional): Record of decision updates
  - `timestamp` (datetime)
  - `change_type` (string): "CREATED", "UPDATED", "APPROVED"
  - `changed_by` (string): Who made the change
  - `change_notes` (string): Description of change

**Relationships**:
- References **Model Comparison Record**: Decision based on comparison of multiple models
- Many-to-one with **Comparison Report**: Multiple decisions may reference same comparison report (if decision changes over time)

**Validation Rules**:
- `selected_models` must not be empty
- `selected_models` must reference valid model names
- `approval_status` must be one of allowed enum values
- `accuracy_threshold_met` should match actual metrics (validation check)
- `change_history` must be chronologically ordered

**File Representation** (Markdown with YAML front matter):
```markdown
---
decision_id: a1b2c3d4-e5f6-7890-abcd-ef1234567890
decision_date: 2026-02-15T14:30:22Z
supervisor_name: Dr. Reem
selected_models:
  - lstm
approval_status: APPROVED
accuracy_threshold_met: true
latency_consideration: tiebreaker
metrics_snapshot:
  accuracy: 0.965
  precision: 0.962
  recall: 0.968
  f1_score: 0.965
  inference_time_ms: 48.3
comparison_report_path: backend/model_comparison/reports/comparison_report_2026-02-15.md
---

# Deployment Decision: LSTM

## Decision Summary
Selected **LSTM** for deployment based on highest accuracy (96.5%) among all qualified models.

## Alternative Models Considered
1. **1D-CNN**: 96.0% accuracy, 32ms inference
   - **Reason rejected**: 0.5% lower accuracy
2. **Random Forest**: 95.2% accuracy, 15ms inference
   - **Reason rejected**: 1.3% lower accuracy despite fast inference

## Rationale
LSTM selected because:
- Highest accuracy (96.5%) exceeds ≥95% threshold
- 0.5% accuracy improvement over 1D-CNN justifies 16ms slower inference
- Medical application prioritizes accuracy over latency
- 48ms inference time still meets real-time requirements (<100ms target)

## Approval
**Supervisor**: Dr. Reem
**Date**: 2026-02-15
**Status**: APPROVED

## Change History
- 2026-02-15 14:30:22 - CREATED by comparison script
- 2026-02-15 14:35:10 - APPROVED by Dr. Reem
```

**Usage**:
- Generated by `document_decision.py` script after supervisor reviews comparison report
- Supports interactive decision making (future Feature 008: Web UI)
- Exported to PDF for graduation project documentation
- Preserved as version-controlled Markdown for audit trail

---

### 4. Comparison Report

**Purpose**: Represents the final comparison report artifact (Markdown, PDF, JSON) containing aggregated comparison data.

**Attributes**:
- `report_id` (string, required): Unique report identifier (UUID)
- `generation_date` (datetime, required): When report was generated
- `models_compared` (array<string>, required): List of model names included in comparison
- `executive_summary` (string, required): High-level findings and recommendation (1-2 paragraphs)
- `comparison_table_data` (array<ModelComparisonRecord>, required): Full comparison data for all models
- `recommendation` (object, required): Deployment recommendation
  - `recommended_model` (string): Model name recommended for deployment (or "NONE" if no models qualify)
  - `rationale` (string): Why this model recommended
  - `alternatives` (array<string>): Other models considered
  - `deployment_ready` (boolean): True if recommendation actionable
- `chart_paths` (object, required): Paths to generated chart images
  - `accuracy_comparison` (string): Path to accuracy bar chart PNG
  - `confusion_matrices` (string): Path to confusion matrix heatmaps PNG
  - `inference_time_comparison` (string): Path to inference time bar chart PNG
- `export_formats` (object, required): Paths to exported report files
  - `markdown` (string): Path to .md report
  - `pdf` (string): Path to .pdf report
  - `json` (string): Path to .json data export
  - `csv` (string): Path to .csv comparison table
- `metadata` (object, required): Report generation context
  - `project_name` (string): "TremoAI"
  - `tensorflow_version` (string): TensorFlow version used
  - `sklearn_version` (string): scikit-learn version used
  - `test_dataset_samples` (integer): Number of test samples (87)
  - `test_dataset_features` (object): Feature dimensions per model type
  - `generation_time_seconds` (float): Report generation duration
- `warnings` (array<string>, optional): Warnings about missing models, data inconsistencies, etc.

**Relationships**:
- Aggregates multiple **Model Comparison Records**
- Referenced by **Deployment Decision**: Decisions cite specific comparison reports

**Validation Rules**:
- `models_compared` must have 1-4 models (error if 0)
- All chart_paths must point to existing PNG files
- All export_formats must point to successfully generated files
- `generation_time_seconds` should be < 120 (2 minutes per SC-001)

**File Representation** (JSON structure saved as comparison_data.json):
```json
{
  "report_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "generation_date": "2026-02-15T14:25:30Z",
  "models_compared": ["rf", "svm", "lstm", "cnn_1d"],
  "executive_summary": "Comparison of 4 tremor detection models...",
  "comparison_table_data": [
    { /* Model Comparison Record for RF */ },
    { /* Model Comparison Record for SVM */ },
    { /* Model Comparison Record for LSTM */ },
    { /* Model Comparison Record for CNN */ }
  ],
  "recommendation": {
    "recommended_model": "lstm",
    "rationale": "LSTM achieves highest accuracy (96.5%) with acceptable inference time (48ms).",
    "alternatives": ["cnn_1d", "rf"],
    "deployment_ready": true
  },
  "chart_paths": {
    "accuracy_comparison": "backend/model_comparison/reports/charts/accuracy_comparison.png",
    "confusion_matrices": "backend/model_comparison/reports/charts/confusion_matrices.png",
    "inference_time_comparison": "backend/model_comparison/reports/charts/inference_time_comparison.png"
  },
  "export_formats": {
    "markdown": "backend/model_comparison/reports/comparison_report.md",
    "pdf": "backend/model_comparison/reports/comparison_report.pdf",
    "json": "backend/model_comparison/reports/comparison_data.json",
    "csv": "backend/model_comparison/reports/comparison_data.csv"
  },
  "metadata": {
    "project_name": "TremoAI",
    "tensorflow_version": "2.13.0",
    "sklearn_version": "1.3.0",
    "test_dataset_samples": 87,
    "test_dataset_features": {
      "ML": {"features": 18},
      "DL": {"timesteps": 128, "features": 6}
    },
    "generation_time_seconds": 85.3
  },
  "warnings": []
}
```

---

## Entity Relationships Diagram

```text
┌─────────────────────────────┐
│  Comparison Report          │
│  - report_id                │
│  - generation_date          │
│  - models_compared          │
│  - executive_summary        │
│  - recommendation           │
│  - chart_paths              │
│  - export_formats           │
│  - metadata                 │
└──────────┬──────────────────┘
           │ aggregates
           │ (1 to many)
           ▼
┌─────────────────────────────┐
│  Model Comparison Record    │
│  - model_name               │
│  - model_type               │
│  - accuracy                 │
│  - precision, recall, f1    │
│  - confusion_matrix         │
│  - inference_time_ms        │
│  - inference_time_std       │
│  - meets_threshold_95       │
│  - ranking                  │
└──────────┬──────────────────┘
           │ has measurements
           │ (1 to many)
           ▼
┌─────────────────────────────┐
│  Inference Benchmark        │
│  - benchmark_id             │
│  - model_name               │
│  - run_id                   │
│  - is_warmup                │
│  - inference_time_ms        │
│  - hardware_info            │
│  - is_outlier               │
└─────────────────────────────┘

┌─────────────────────────────┐
│  Deployment Decision        │
│  - decision_id              │
│  - decision_date            │
│  - supervisor_name          │
│  - selected_models          │
│  - rationale_text           │
│  - approval_status          │
│  - metrics_snapshot         │
│  - change_history           │
└──────────┬──────────────────┘
           │ references
           │ (many to 1)
           ▼
┌─────────────────────────────┐
│  Comparison Report          │
│  (via comparison_report_path)│
└─────────────────────────────┘
```

## Data Flow

1. **Comparison Script Execution**:
   - Load model files → Create **Model Comparison Records**
   - Run inference benchmarks → Generate **Inference Benchmarks**
   - Compute statistics → Update Model Comparison Records with mean/std
   - Generate charts → Save PNG files
   - Format report → Create **Comparison Report**
   - Export to Markdown, PDF, JSON, CSV

2. **Deployment Decision**:
   - Supervisor reviews Comparison Report
   - Selects model(s) for deployment
   - Run `document_decision.py` script → Create **Deployment Decision**
   - Export decision to Markdown and PDF

3. **Decision Update** (if needed):
   - Load existing Deployment Decision
   - Update selected_models, rationale, or approval_status
   - Append to change_history
   - Re-export Markdown and PDF

## File Storage Structure

```text
backend/model_comparison/
├── reports/                          # Generated comparison reports
│   ├── comparison_report.md          # Latest Markdown report
│   ├── comparison_report.pdf         # Latest PDF report
│   ├── comparison_data.json          # Latest structured data
│   ├── comparison_data.csv           # Latest CSV table
│   ├── comparison_report_2026-02-15.md   # Timestamped backup
│   ├── comparison_report_2026-02-15.pdf  # Timestamped backup
│   └── charts/                       # Generated chart images
│       ├── accuracy_comparison.png
│       ├── confusion_matrices.png
│       └── inference_time_comparison.png
│
└── decisions/                        # Deployment decision documents
    ├── decision_2026-02-15_143022.md     # Timestamped decision (YAML + Markdown)
    ├── decision_2026-02-15_143022.pdf    # PDF export
    └── decision_2026-02-16_091530.md     # Updated decision (if changed)
```

## Notes

- **No Django Models**: This feature does not create Django ORM models. All entities are Python dictionaries/dataclasses serialized to JSON/Markdown.
- **File-based persistence**: Comparison reports and decisions stored as files for version control and easy sharing.
- **Future Database Migration**: If Feature 008 (Model Comparison Dashboard) adds a web UI, these entities can be migrated to PostgreSQL tables with Django ORM.
- **JSON Schema**: Consider adding JSON Schema validation for comparison_data.json to ensure data integrity.
