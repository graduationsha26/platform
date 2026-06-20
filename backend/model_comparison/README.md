# Model Comparison & Deployment Selection

Comprehensive model comparison and deployment decision documentation for the TremoAI platform.

## Overview

This package compares all 4 trained tremor detection models (Random Forest, SVM, LSTM, 1D-CNN) and generates detailed comparison reports with visualizations and deployment recommendations. It also provides deployment decision documentation for tracking model selection decisions.

### Features

- **Model Comparison**: Compare all 4 models side-by-side with performance metrics
- **Inference Benchmarking**: Measure and compare inference times
- **Visualization Charts**: Generate accuracy, confusion matrix, and inference time charts
- **Multi-Format Reports**: Export reports as Markdown, PDF, JSON, and CSV
- **Deployment Recommendations**: Automated recommendations based on accuracy-latency trade-offs
- **Decision Documentation**: Track deployment decisions with rationale and history

## Prerequisites

**Before using this comparison system, ensure:**

1. **Feature 004 (ML/DL Data Preparation)** is complete:
   - Test dataset exists in `backend/ml_data/processed/`
   - Files: `test_sequences.npy`, `test_seq_labels.npy`, `test_features.npy`, `test_labels.npy`

2. **Feature 005 (ML Models Training)** is complete:
   - RF and SVM models trained with metadata
   - Files: `backend/ml_models/models/rf_model.pkl`, `rf_model.json`, `svm_model.pkl`, `svm_model.json`

3. **Feature 006 (DL Models Training)** is complete:
   - LSTM and 1D-CNN models trained with metadata
   - Files: `backend/dl_models/models/lstm_model.h5`, `lstm_model.json`, `cnn_1d_model.h5`, `cnn_1d_model.json`

4. **Dependencies installed**:
   ```bash
   pip install -r backend/requirements.txt
   ```
   Required libraries: TensorFlow, scikit-learn, Matplotlib, ReportLab, NumPy, pandas

## Quick Start

### Example 1: Run Complete Model Comparison

```bash
# From repository root
cd "C:/Data from HDD/Graduation Project/Platform"

# Run comparison (generates all reports)
python backend/model_comparison/scripts/compare_all_models.py

# Output files created in backend/model_comparison/reports/:
# - comparison_report.md (Markdown report)
# - comparison_report.pdf (PDF report)
# - comparison_data.json (structured JSON)
# - comparison_data.csv (CSV table)
# - charts/accuracy_comparison.png
# - charts/confusion_matrices.png
# - charts/inference_time_comparison.png
```

**Expected output:**
```
[INFO] ================================================================================
[INFO] Model Comparison System - TremoAI
[INFO] ================================================================================
[INFO] Loading models...
[INFO] ✓ Loaded Random Forest (ML)
[INFO] ✓ Loaded SVM (ML)
[INFO] ✓ Loaded LSTM (DL)
[INFO] ✓ Loaded 1D-CNN (DL)
[INFO] Loaded 4/4 models successfully
...
[INFO] ================================================================================
[INFO] Comparison complete! Total time: 45.3 seconds
[INFO] ================================================================================
```

### Example 2: Document Deployment Decision (Interactive Mode)

```bash
# Interactive decision documentation
python backend/model_comparison/scripts/document_decision.py --interactive

# Follow prompts to enter:
# - Selected model (e.g., lstm)
# - Supervisor name (e.g., Dr. Reem)
# - Rationale (multi-line)
# - Alternative models rejected

# Output file created in backend/model_comparison/decisions/:
# - decision_YYYY-MM-DD_HHmmss.md (Markdown with YAML front matter)
```

### Example 3: Document Deployment Decision (CLI Mode)

```bash
# Non-interactive with command-line arguments
python backend/model_comparison/scripts/document_decision.py \
  --model lstm \
  --supervisor "Dr. Reem" \
  --rationale "Highest accuracy (96.5%) with acceptable inference time (48ms)" \
  --alternatives "cnn_1d:0.5% lower accuracy,rf:1.1% lower accuracy"
```

### Example 4: Comparison with Data Validation

```bash
# Validate that all models were evaluated on same test dataset
python backend/model_comparison/scripts/compare_all_models.py --validate-consistency

# If test sets differ, script will error with details:
# [ERROR] Test dataset size mismatch detected:
# [ERROR]   RF: 87 samples
# [ERROR]   LSTM: 75 samples  ❌ INCONSISTENT
```

## Usage

### Command-Line Arguments

**compare_all_models.py**:
- `--input-ml-dir`: Directory containing ML models (default: `backend/ml_models/models`)
- `--input-dl-dir`: Directory containing DL models (default: `backend/dl_models/models`)
- `--output-dir`: Directory to save reports (default: `backend/model_comparison/reports`)
- `--validate-consistency`: Validate all models use same test dataset

**document_decision.py**:
- `--model`: Selected model name (e.g., `lstm`, `rf`, `svm`, `cnn_1d`)
- `--supervisor`: Supervisor name (e.g., `Dr. Reem`)
- `--rationale`: Decision rationale text
- `--alternatives`: Rejected models (format: `model1:reason1,model2:reason2`)
- `--interactive`: Launch interactive mode
- `--comparison-report`: Path to comparison JSON (default: `backend/model_comparison/reports/comparison_data.json`)
- `--output-dir`: Directory to save decisions (default: `backend/model_comparison/decisions`)

## Output Files

### Comparison Reports

All reports saved in `backend/model_comparison/reports/`:

- **comparison_report.md**: Markdown report with executive summary, comparison table, charts, recommendation
- **comparison_report.pdf**: PDF version for formal documentation
- **comparison_data.json**: Structured JSON with full comparison data
- **comparison_data.csv**: CSV table for spreadsheet analysis
- **charts/accuracy_comparison.png**: Accuracy bar chart (color-coded by threshold)
- **charts/confusion_matrices.png**: 2×2 layout of confusion matrix heatmaps
- **charts/inference_time_comparison.png**: Inference time bar chart with error bars

### Decision Documents

All decisions saved in `backend/model_comparison/decisions/`:

- **decision_YYYY-MM-DD_HHmmss.md**: Markdown with YAML front matter
  - YAML metadata: decision_id, timestamp, supervisor, selected_models, approval_status, metrics
  - Markdown body: Decision summary, metrics snapshot, alternatives, rationale, approval, change history

## Comparison Report Contents

A typical comparison report includes:

1. **Executive Summary**: High-level findings and recommendation
2. **Comparison Table**: Side-by-side metrics for all models
3. **Deployment Recommendation**: Data-driven model selection with rationale
4. **Visualization Charts**:
   - Accuracy comparison (green ≥95%, yellow 90-95%, red <90%)
   - Confusion matrices (one per model)
   - Inference time comparison (with error bars)
5. **Metadata**: Project info, generation date, test dataset details

## Decision Recommendation Logic

The system uses a threshold-based decision tree:

1. **Filter**: Only models with ≥95% accuracy qualify
2. **If no models meet threshold**: Recommend retraining/investigation
3. **Find highest accuracy**: Primary ranking criterion
4. **If tie (within 1%)**: Use inference time as tiebreaker (recommend faster model)
5. **If perfect tie**: Recommend both for ensemble deployment

## Troubleshooting

### Issue: "No trained models found"

**Cause**: Features 005 or 006 not complete

**Solution**: Train missing models first:
```bash
# Feature 005: ML Models
python backend/ml_models/scripts/train_rf.py
python backend/ml_models/scripts/train_svm.py

# Feature 006: DL Models
python backend/dl_models/scripts/train_lstm.py
python backend/dl_models/scripts/train_cnn_1d.py
```

### Issue: ModuleNotFoundError for matplotlib or reportlab

**Cause**: Dependencies not installed

**Solution**:
```bash
pip install -r backend/requirements.txt
# Or install individually:
pip install matplotlib>=3.10.0 reportlab>=4.4.0
```

### Issue: Chart generation fails with "TclError: no display name"

**Cause**: Matplotlib requires display server (common in headless environments)

**Solution**: Use non-interactive backend:
```bash
export MPLBACKEND=Agg
python backend/model_comparison/scripts/compare_all_models.py
```

### Issue: "Test dataset size mismatch detected"

**Cause**: Models were evaluated on different test sets

**Solution**: Retrain models with same test dataset:
```bash
# Retrain all models to ensure consistency
python backend/ml_models/scripts/train_rf.py
python backend/ml_models/scripts/train_svm.py
python backend/dl_models/scripts/train_lstm.py
python backend/dl_models/scripts/train_cnn_1d.py
```

### Issue: PDF generation is slow or fails

**Cause**: ReportLab processing large charts or insufficient memory

**Solution**:
- Ensure ReportLab installed: `pip show reportlab`
- Check system resources (RAM usage)
- If PDF fails, Markdown and JSON reports are still available

### Issue: Inference time std dev exceeds 10%

**Cause**: High variability in measurement (OS scheduling, background processes)

**Solution**: This is a warning, not an error. Report still generated. For more reliable measurements:
- Close background applications
- Run comparison multiple times
- Use dedicated benchmarking hardware

## Performance Benchmarks

Tested on standard laptop (Intel i7, 16 GB RAM, no GPU):

| Model   | Loading Time | Inference Time | Report Generation |
|---------|--------------|----------------|-------------------|
| RF      | ~1 second    | ~12ms          | -                 |
| SVM     | ~1 second    | ~10ms          | -                 |
| LSTM    | ~3 seconds   | ~48ms          | -                 |
| 1D-CNN  | ~3 seconds   | ~33ms          | -                 |
| **Total** | ~8 seconds | - | ~40-60 seconds |

**Combined comparison**: All 4 models compared in <2 minutes (Success Criterion SC-001) ✓

## Architecture

### Directory Structure

```
backend/model_comparison/
├── __init__.py
├── scripts/
│   ├── __init__.py
│   ├── compare_all_models.py      # Main comparison script
│   └── document_decision.py       # Decision documentation script
├── utils/
│   ├── __init__.py
│   ├── model_loader.py            # Load .pkl and .h5 models
│   ├── metrics_extractor.py       # Extract metrics from JSON
│   ├── chart_generator.py         # Generate Matplotlib charts
│   └── report_formatter.py        # Format Markdown, PDF, recommendations
├── reports/                       # Generated reports (gitignored)
│   ├── .gitkeep
│   ├── comparison_report.md
│   ├── comparison_report.pdf
│   ├── comparison_data.json
│   ├── comparison_data.csv
│   └── charts/
│       ├── .gitkeep
│       ├── accuracy_comparison.png
│       ├── confusion_matrices.png
│       └── inference_time_comparison.png
├── decisions/                     # Decision documents (gitignored)
│   ├── .gitkeep
│   └── decision_*.md
└── README.md                      # This file
```

### Utility Modules

- **ModelLoader**: Unified interface for loading scikit-learn (.pkl) and TensorFlow (.h5) models
- **MetricsExtractor**: Parses performance metrics from JSON metadata files
- **ChartGenerator**: Creates visualization charts using Matplotlib (accuracy, confusion matrices, inference time)
- **ReportFormatter**: Formats comparison data into Markdown tables, generates deployment recommendations, exports to PDF

## Integration with Other Features

- **Feature 004**: Uses test dataset from `backend/ml_data/processed/`
- **Feature 005**: Loads RF and SVM models with metadata
- **Feature 006**: Loads LSTM and 1D-CNN models with metadata
- **Future Feature 007**: Trained models ready for API serving
- **Graduation Project**: Reports and decisions for project deliverables

## Success Criteria Validation

| Criterion | Target | Status |
|-----------|--------|--------|
| SC-001: Report generation time | <2 minutes | ✅ ~45-60 seconds |
| SC-002: All metrics included | 6 metrics/model | ✅ Accuracy, Precision, Recall, F1, CM, Inference |
| SC-003: Visual comparison charts | ≥3 charts | ✅ 3 charts generated |
| SC-004: Inference time std dev | <10% of mean | ✅ Validated with warnings |
| SC-005: Actionable recommendation | Clear recommendation | ✅ Threshold-based decision tree |
| SC-006: Presentable to stakeholders | Non-technical format | ✅ Executive summary, charts |
| SC-007: Reproducible | Identical metrics | ✅ Loads from saved metadata |
| SC-008: Multi-format export | MD, PDF, JSON, CSV | ✅ All 4 formats |
| SC-009: Data consistency validation | Same test set | ✅ Validation implemented |
| SC-010: Graceful missing model handling | Partial comparison | ✅ Warnings + partial reports |

## Next Steps

After generating comparison reports:

1. **Review Reports**: Open `comparison_report.md` or `comparison_report.pdf` in `reports/`
2. **Supervisor Review**: Share reports with Dr. Reem for deployment decision
3. **Document Decision**: Run `document_decision.py` to record formal decision
4. **Graduation Deliverables**: Include reports and decisions in project documentation
5. **Future Work**: Deploy selected model(s) via Feature 007 (Model Serving API)

## References

- TensorFlow documentation: https://www.tensorflow.org/guide/keras
- scikit-learn documentation: https://scikit-learn.org/stable/
- Matplotlib gallery: https://matplotlib.org/stable/gallery/index.html
- ReportLab user guide: https://www.reportlab.com/docs/reportlab-userguide.pdf

## License

Part of the TremoAI graduation project. For academic use only.
