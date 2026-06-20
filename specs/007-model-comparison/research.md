# Technical Research: Model Comparison & Deployment Selection

**Feature**: 007-model-comparison
**Phase**: Phase 0 - Research & Technical Decisions
**Date**: 2026-02-15

## Overview

This document records technical decisions for implementing a comprehensive model comparison and deployment selection system. All decisions leverage existing libraries and patterns from Features 003, 005, and 006 to minimize complexity and maximize reuse.

## Technical Decisions

### Decision 1: Model Loading Strategy

**Context**: Need to load 4 different model types (scikit-learn .pkl files and TensorFlow .h5 files) with a unified interface for comparison.

**Decision**: Implement a unified `ModelLoader` class with type detection and format-specific loading methods.

**Implementation**:
```python
# Pseudo-code structure
class ModelLoader:
    def load_model(model_path: str, model_type: str):
        if model_type in ['rf', 'svm']:
            return joblib.load(model_path)  # scikit-learn
        elif model_type in ['lstm', 'cnn_1d']:
            return tf.keras.models.load_model(model_path)  # TensorFlow
```

**Rationale**:
- scikit-learn models (.pkl) use `joblib.load()` (standard persistence method)
- TensorFlow models (.h5) use `tf.keras.models.load_model()` (native Keras loader)
- Type detection based on file extension and model_type parameter
- Unified interface simplifies comparison logic

**Alternatives Considered**:
- Dynamic loading based on file extension only: Rejected because model type context is valuable for feature engineering validation
- Separate loaders per model: Rejected due to code duplication and harder maintenance

**References**: scikit-learn persistence documentation, TensorFlow/Keras model saving guide

---

### Decision 2: Inference Time Measurement Methodology

**Context**: Need reliable inference time measurements with low variance for fair model comparison across different model architectures.

**Decision**: Use 10 timed iterations with 3 warmup iterations, exclude outliers beyond 2 standard deviations, report mean ± std dev.

**Implementation**:
```python
# Pseudo-code structure
def benchmark_inference(model, X_test, n_warmup=3, n_iterations=10):
    # Warmup (exclude from timing)
    for _ in range(n_warmup):
        model.predict(X_test)

    # Timed iterations
    times = []
    for _ in range(n_iterations):
        start = time.perf_counter()
        model.predict(X_test)
        times.append((time.perf_counter() - start) * 1000)  # Convert to ms

    # Exclude outliers (>2 std dev)
    mean, std = np.mean(times), np.std(times)
    filtered = [t for t in times if abs(t - mean) <= 2 * std]

    return {
        'mean_ms': np.mean(filtered),
        'std_ms': np.std(filtered),
        'samples': len(filtered)
    }
```

**Rationale**:
- **3 warmup iterations**: Allow model/GPU to initialize and optimize (especially for TensorFlow models)
- **10 timed iterations**: Balance between reliability and execution time (total ~20-30 seconds for all 4 models)
- **Outlier exclusion**: Python GC, OS scheduling, or background processes can cause spikes
- **Report mean ± std**: Provides statistical reliability indication (target: std < 10% of mean per SC-004)

**Alternatives Considered**:
- Single prediction timing: Rejected due to high variance from OS scheduling
- 100+ iterations: Rejected due to excessive execution time for comparison script
- Median instead of mean: Rejected because mean ± std better represents reliability for SC-004 threshold

**Performance Implications**: Total benchmarking time = (3 warmup + 10 timed) × 4 models × ~0.1s/prediction = ~5 seconds (acceptable per SC-001: <2 minutes total)

**References**: Python `time.perf_counter()` for high-resolution timing, TensorFlow inference optimization best practices

---

### Decision 3: Report Generation Format and Structure

**Context**: Need to produce comparison reports in multiple formats (Markdown, PDF, JSON, CSV) for different stakeholders (supervisor, graduation committee, future analysis).

**Decision**: Generate Markdown as master format, convert to PDF using ReportLab, export data tables as JSON/CSV.

**Report Structure**:
1. **Executive Summary** (1 paragraph): Key findings, recommendation, highest performing model
2. **Comparison Table**: Side-by-side metrics for all 4 models
3. **Visualization Charts**: 3 required charts (accuracy, confusion matrices, inference time)
4. **Detailed Analysis**: Per-model breakdown with strengths/weaknesses
5. **Deployment Recommendation**: Data-driven recommendation with explicit trade-off reasoning
6. **Appendix**: Metadata (TensorFlow version, test dataset details, generation timestamp)

**Markdown Template**:
```markdown
# Model Comparison Report - TremoAI
**Generated**: [timestamp]
**Test Dataset**: 87 samples, 6 sensors (aX, aY, aZ, gX, gY, gZ)

## Executive Summary
[1 paragraph: best model, key metrics, recommendation]

## Comparison Table
| Model | Type | Accuracy | Precision | Recall | F1 | Inference (ms) | Ranking |
|-------|------|----------|-----------|--------|----|--------------|---------|
| ...   | ...  | ...      | ...       | ...    |... | ...          | ...     |

## Performance Visualizations
[Embedded chart images]

## Deployment Recommendation
[Data-driven recommendation with reasoning]
```

**PDF Generation**:
- Use ReportLab (already in requirements.txt from Feature 003)
- Convert Markdown structure to ReportLab paragraphs, tables, and images
- Embed Matplotlib charts as PNG images
- Apply TremoAI branding (if available) or simple professional styling

**JSON Export**:
- Structured data for programmatic access
- Schema: `{ "models": [{"name": "...", "metrics": {...}}], "recommendation": "...", "metadata": {...} }`
- Supports future integration with dashboards or automated systems

**CSV Export**:
- Simple comparison table for spreadsheet analysis
- Columns: Model, Type, Accuracy, Precision, Recall, F1, Inference_ms, Ranking

**Rationale**:
- **Markdown master**: Human-readable, version-control friendly, easy to edit
- **PDF for stakeholders**: Professional format for graduation project documentation
- **JSON/CSV for analysis**: Machine-readable formats for future extensions
- **ReportLab reuse**: Leverage existing dependency from Feature 003 (analytics reports)

**Alternatives Considered**:
- HTML reports: Rejected because PDF is more formal for academic deliverables
- Word/DOCX format: Rejected due to library complexity (python-docx) and less common use
- LaTeX: Rejected due to steep learning curve and installation requirements

---

### Decision 4: Chart Generation Library and Visualization Types

**Context**: Need to generate 3+ visualization charts for model comparison: accuracy bar chart, confusion matrix heatmaps, inference time comparison.

**Decision**: Use Matplotlib (already in requirements.txt from Feature 003) for all charts.

**Chart Types**:

1. **Accuracy Comparison Bar Chart**:
   - X-axis: 4 models (RF, SVM, LSTM, 1D-CNN)
   - Y-axis: Accuracy percentage (0-100%)
   - Color-coded bars (green for ≥95% threshold, yellow for 90-95%, red for <90%)
   - Horizontal reference line at 95% threshold
   - Exact percentage labels on top of each bar

2. **Confusion Matrix Heatmaps** (4 heatmaps, 2×2 layout):
   - One heatmap per model
   - Axes: Predicted vs Actual (0=No Tremor, 1=Tremor)
   - Color scale: Sequential colormap (e.g., Blues) with annotations
   - Display counts in each cell (TP, TN, FP, FN)
   - Model name as subplot title

3. **Inference Time Comparison Bar Chart**:
   - X-axis: 4 models
   - Y-axis: Inference time (milliseconds)
   - Error bars showing ± standard deviation
   - Log scale if variance is high
   - Color-coded by model type (ML vs DL)

**Code Pattern**:
```python
# Pseudo-code
import matplotlib.pyplot as plt
import seaborn as sns

def generate_accuracy_chart(comparison_data, output_path):
    fig, ax = plt.subplots(figsize=(10, 6))
    models = [d['model_name'] for d in comparison_data]
    accuracies = [d['accuracy'] * 100 for d in comparison_data]
    colors = ['green' if a >= 95 else 'yellow' if a >= 90 else 'red' for a in accuracies]

    ax.bar(models, accuracies, color=colors)
    ax.axhline(y=95, color='black', linestyle='--', label='95% Threshold')
    ax.set_ylabel('Accuracy (%)')
    ax.set_title('Model Accuracy Comparison')
    ax.legend()

    for i, acc in enumerate(accuracies):
        ax.text(i, acc + 1, f'{acc:.1f}%', ha='center')

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
```

**Rationale**:
- **Matplotlib**: Already dependency for Feature 003 (analytics reports), proven reliable
- **Seaborn**: Optional enhancement for heatmaps (available as Matplotlib extension)
- **High DPI (300)**: Professional quality for PDF embedding
- **Color-coding**: Visual clarity for threshold-based evaluation
- **Error bars**: Communicate measurement reliability (SC-004)

**Alternatives Considered**:
- Plotly: Rejected because interactive charts not needed for static reports (future Feature 008 may use for web UI)
- Bokeh: Rejected for same reason as Plotly
- Seaborn exclusively: Rejected because Matplotlib more flexible and already a dependency

**Performance**: Chart generation expected <5 seconds total for all 3 charts (acceptable per SC-001)

**References**: Matplotlib gallery for bar charts and heatmaps, Seaborn heatmap documentation

---

### Decision 5: Deployment Recommendation Logic

**Context**: Need objective, rule-based recommendation logic for model selection based on accuracy-latency trade-offs.

**Decision**: Implement threshold-based decision tree with explicit tie-breaking rules.

**Recommendation Algorithm**:
```python
def generate_recommendation(comparison_data):
    # Filter models meeting 95% accuracy threshold
    qualified = [m for m in comparison_data if m['accuracy'] >= 0.95]

    if len(qualified) == 0:
        return {
            'recommendation': 'NONE',
            'rationale': 'No models meet ≥95% accuracy threshold. Investigate data quality or retrain models.',
            'alternative_actions': ['Hyperparameter tuning', 'Data augmentation', 'Feature engineering']
        }

    # Find highest accuracy
    max_accuracy = max(m['accuracy'] for m in qualified)
    top_accurate = [m for m in qualified if m['accuracy'] >= max_accuracy - 0.01]  # Within 1% of best

    if len(top_accurate) == 1:
        # Clear winner
        model = top_accurate[0]
        return {
            'recommendation': model['model_name'],
            'rationale': f"{model['model_name']} achieves highest accuracy ({model['accuracy']:.1%}) among qualified models.",
            'deployment_ready': True
        }

    # Tie or near-tie (within 1% accuracy) - use latency tiebreaker
    fastest = min(top_accurate, key=lambda m: m['inference_time_ms'])

    return {
        'recommendation': fastest['model_name'],
        'rationale': f"Multiple models achieve similar accuracy (~{max_accuracy:.1%}). {fastest['model_name']} recommended for fastest inference time ({fastest['inference_time_ms']:.1f}ms).",
        'alternatives': [m['model_name'] for m in top_accurate if m != fastest],
        'deployment_ready': True
    }
```

**Decision Thresholds**:
- **Accuracy threshold**: 95% (from Features 005/006 success criteria)
- **"Near-tie" threshold**: Within 1% accuracy difference (e.g., 96.5% vs 96.0% = tie)
- **Latency tiebreaker**: If accuracies tied, recommend faster model
- **Multiple recommendations**: If both accuracy and latency tied (within 5ms), recommend ensemble deployment

**Rationale**:
- **Objective**: Rule-based logic removes subjective bias
- **Threshold-based**: Aligns with existing model training success criteria (≥95%)
- **Trade-off aware**: Explicitly considers accuracy vs latency per FR-007
- **Actionable**: Provides clear deployment recommendation or alternative actions

**Alternatives Considered**:
- Weighted scoring (e.g., 0.7×accuracy + 0.3×speed): Rejected because weights are subjective and project hasn't defined them
- Multi-criteria decision analysis (MCDA): Rejected as overly complex for 2-metric comparison
- Machine learning for recommendation: Rejected as overkill (need historical data, interpretability issues)

**Edge Cases Handled**:
- Zero qualified models: Recommend retraining/investigation
- Perfect tie: Recommend ensemble deployment (both models)
- Missing inference time data: Fallback to accuracy-only recommendation with warning

---

### Decision 6: Deployment Decision Documentation Format

**Context**: Need to record and track deployment decisions for graduation project deliverables and future reference.

**Decision**: Use timestamped Markdown files with structured YAML front matter, stored in `backend/model_comparison/decisions/` directory.

**File Naming**: `decision_[YYYY-MM-DD]_[HHmmss].md` (e.g., `decision_2026-02-15_143022.md`)

**Document Structure**:
```markdown
---
decision_id: UUID
timestamp: 2026-02-15T14:30:22Z
supervisor: Dr. Reem
status: APPROVED
selected_models:
  - LSTM
accuracy_threshold_met: true
latency_consideration: true
---

# Deployment Decision: [Model Name]

## Decision Summary
Selected **LSTM** for deployment based on highest accuracy (96.5%) among all qualified models.

## Metrics Snapshot
- **Accuracy**: 96.5%
- **Precision**: 96.2%
- **Recall**: 96.8%
- **F1-Score**: 96.5%
- **Inference Time**: 48ms ± 3ms

## Alternative Models Considered
1. **1D-CNN**: 96.0% accuracy, 32ms inference (rejected: 0.5% lower accuracy)
2. **Random Forest**: 95.2% accuracy, 15ms inference (rejected: 1.3% lower accuracy)
3. **SVM**: 94.8% accuracy, 12ms inference (rejected: below 95% threshold)

## Trade-off Analysis
LSTM selected despite ~20ms slower inference than 1D-CNN because:
- 0.5% higher accuracy is significant for medical application
- 48ms inference time still meets real-time requirements (<100ms target)
- Tremor detection accuracy prioritized over latency per project requirements

## Approval
**Supervisor**: Dr. Reem
**Date**: 2026-02-15
**Status**: APPROVED

## Change History
- 2026-02-15 14:30: Initial decision recorded
```

**Rationale**:
- **Timestamped files**: Each decision is a separate file for easy version control and history tracking
- **YAML front matter**: Structured metadata for programmatic parsing
- **Markdown body**: Human-readable rationale and analysis
- **UUID decision_id**: Unique identifier for cross-referencing
- **Change history**: Supports decision updates (FR-012)

**Alternatives Considered**:
- Database storage: Rejected because no database access for this feature (backend scripts only)
- Single decisions.json file: Rejected because harder to track history and merge conflicts
- Git commits as decision log: Rejected because not all stakeholders have Git access

**Export to PDF**: Decision files can be converted to PDF using same ReportLab pipeline as comparison reports for formal documentation.

---

### Decision 7: Missing Model Handling Strategy

**Context**: Comparison script may be run before all 4 models are trained or if some model files are missing/corrupted.

**Decision**: Implement graceful degradation with partial comparison and clear warnings.

**Implementation**:
```python
def load_all_models():
    models = {}
    missing = []

    model_configs = [
        {'name': 'rf', 'pkl': 'backend/ml_models/models/rf_model.pkl', 'json': 'backend/ml_models/models/rf_model.json'},
        {'name': 'svm', 'pkl': 'backend/ml_models/models/svm_model.pkl', 'json': 'backend/ml_models/models/svm_model.json'},
        {'name': 'lstm', 'h5': 'backend/dl_models/models/lstm_model.h5', 'json': 'backend/dl_models/models/lstm_model.json'},
        {'name': 'cnn_1d', 'h5': 'backend/dl_models/models/cnn_1d_model.h5', 'json': 'backend/dl_models/models/cnn_1d_model.json'},
    ]

    for config in model_configs:
        try:
            # Attempt to load model and metadata
            model = load_model(config)
            metadata = load_metadata(config['json'])
            models[config['name']] = {'model': model, 'metadata': metadata}
        except FileNotFoundError as e:
            missing.append(config['name'])
            logger.warning(f"Model '{config['name']}' not found: {e}")
        except Exception as e:
            missing.append(config['name'])
            logger.error(f"Failed to load model '{config['name']}': {e}")

    if len(models) == 0:
        raise ValueError("No trained models found. Please complete Features 005 and 006 first.")

    if missing:
        logger.warning(f"Partial comparison: {len(models)}/4 models loaded. Missing: {', '.join(missing)}")

    return models, missing
```

**Warning Display in Report**:
```markdown
⚠️ **PARTIAL COMPARISON WARNING**
This report compares only 2 of 4 models. The following models are missing:
- Random Forest (RF): Model file not found at backend/ml_models/models/rf_model.pkl
- SVM: Model file not found at backend/ml_models/models/svm_model.pkl

To generate a complete comparison, please train missing models:
- Feature 005: `python backend/ml_models/scripts/train_rf.py` and `python backend/ml_models/scripts/train_svm.py`
```

**Rationale**:
- **Graceful degradation**: Allows partial comparisons for incremental development
- **Clear warnings**: Users understand report limitations
- **Actionable feedback**: Directs users to specific training commands
- **Zero models = hard error**: Cannot generate meaningful report with no models

**Edge Case**: If only 1 model available, still generate report with single-model analysis (no comparison, but useful for validating that model meets threshold).

---

## Summary of Key Decisions

| Decision | Technology/Approach | Rationale |
|----------|-------------------|-----------|
| Model Loading | Unified `ModelLoader` class with `joblib` (ML) and `tf.keras` (DL) | Format-specific loaders with unified interface |
| Inference Benchmarking | 10 iterations + 3 warmup, exclude outliers >2σ | Statistical reliability with acceptable execution time |
| Report Formats | Markdown (master), PDF (ReportLab), JSON, CSV | Multi-stakeholder support, reuse existing dependencies |
| Visualization | Matplotlib bar charts and heatmaps | Reuse Feature 003 dependency, proven reliability |
| Recommendation Logic | Threshold-based decision tree (95% accuracy, 1% tie threshold) | Objective, rule-based, aligns with existing success criteria |
| Decision Documentation | Timestamped Markdown files with YAML front matter | Version control friendly, human-readable, programmatically parseable |
| Missing Model Handling | Graceful degradation with partial comparison + warnings | Supports incremental development, clear user feedback |

## Dependencies Confirmed

All required libraries already present in `backend/requirements.txt`:
- ✅ `scikit-learn` (Feature 005)
- ✅ `tensorflow` (Feature 006)
- ✅ `matplotlib` (Feature 003)
- ✅ `reportlab` (Feature 003)
- ✅ `numpy` (Feature 004)
- ✅ `pandas` (Feature 004)

**No new dependencies required** ✅

## Next Steps

Phase 1: Generate data-model.md (entities), quickstart.md (test scenarios)
