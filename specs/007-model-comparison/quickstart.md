# Quickstart Guide: Model Comparison & Deployment Selection

**Feature**: 007-model-comparison
**Phase**: Phase 1 - Integration Scenarios
**Date**: 2026-02-15

## Overview

This quickstart guide provides validation scenarios and usage examples for the model comparison and deployment selection system. Use these scenarios to verify correct implementation and demonstrate feature functionality.

## Prerequisites

Before running comparison scripts, ensure:

1. **Features 004, 005, 006 Complete**:
   - ✅ Feature 004 (ML/DL Data Preparation): Test dataset exists in `backend/ml_data/processed/`
   - ✅ Feature 005 (ML Models Training): RF and SVM models trained with metadata files
   - ✅ Feature 006 (DL Models Training): LSTM and 1D-CNN models trained with metadata files

2. **Required Files Exist**:
   ```bash
   # ML Models (Feature 005)
   backend/ml_models/models/rf_model.pkl
   backend/ml_models/models/rf_model.json
   backend/ml_models/models/svm_model.pkl
   backend/ml_models/models/svm_model.json

   # DL Models (Feature 006)
   backend/dl_models/models/lstm_model.h5
   backend/dl_models/models/lstm_model.json
   backend/dl_models/models/cnn_1d_model.h5
   backend/dl_models/models/cnn_1d_model.json

   # Test Data (Feature 004)
   backend/ml_data/processed/test_sequences.npy  # 87 × 128 × 6 (for DL models)
   backend/ml_data/processed/test_seq_labels.npy  # 87 labels
   backend/ml_data/processed/test_features.npy    # 87 × 18 (for ML models)
   backend/ml_data/processed/test_labels.npy      # 87 labels
   ```

3. **Python Environment**:
   - Python 3.8+
   - All dependencies installed: `pip install -r backend/requirements.txt`

## Validation Scenarios

### Scenario 1: Complete Model Comparison (Happy Path)

**Goal**: Verify that all 4 models can be compared successfully and a complete report is generated.

**Preconditions**:
- All 4 models trained and metadata files present
- Test dataset available (87 samples)

**Execution**:
```bash
cd "C:/Data from HDD/Graduation Project/Platform"

# Run complete model comparison
python backend/model_comparison/scripts/compare_all_models.py
```

**Expected Output**:
```text
[INFO] ================================================================================
[INFO] Model Comparison System - TremoAI
[INFO] ================================================================================
[INFO] Loading models...
[INFO]   ✓ Random Forest (RF) loaded from backend/ml_models/models/rf_model.pkl
[INFO]   ✓ SVM loaded from backend/ml_models/models/svm_model.pkl
[INFO]   ✓ LSTM loaded from backend/dl_models/models/lstm_model.h5
[INFO]   ✓ 1D-CNN loaded from backend/dl_models/models/cnn_1d_model.h5
[INFO] All 4 models loaded successfully.
[INFO]
[INFO] Loading test dataset...
[INFO]   ✓ DL test data: 87 samples × 128 timesteps × 6 features
[INFO]   ✓ ML test data: 87 samples × 18 features
[INFO]
[INFO] Running inference benchmarks...
[INFO]   [RF] 3 warmup iterations... Done.
[INFO]   [RF] 10 timed iterations... Mean: 12.3ms, Std: 0.8ms
[INFO]   [SVM] 3 warmup iterations... Done.
[INFO]   [SVM] 10 timed iterations... Mean: 9.5ms, Std: 0.6ms
[INFO]   [LSTM] 3 warmup iterations... Done.
[INFO]   [LSTM] 10 timed iterations... Mean: 48.3ms, Std: 3.1ms
[INFO]   [CNN] 3 warmup iterations... Done.
[INFO]   [CNN] 10 timed iterations... Mean: 32.7ms, Std: 2.4ms
[INFO]
[INFO] Extracting performance metrics...
[INFO]   [RF]   Accuracy: 95.4%, Precision: 95.1%, Recall: 95.7%, F1: 95.4%
[INFO]   [SVM]  Accuracy: 94.3%, Precision: 94.0%, Recall: 94.6%, F1: 94.3%
[INFO]   [LSTM] Accuracy: 96.5%, Precision: 96.2%, Recall: 96.8%, F1: 96.5%
[INFO]   [CNN]  Accuracy: 96.0%, Precision: 95.8%, Recall: 96.2%, F1: 96.0%
[INFO]
[INFO] Generating comparison table...
[INFO] ┌──────────────┬──────┬──────────┬───────────┬────────┬────────┬─────────────┬─────────┐
[INFO] │ Model        │ Type │ Accuracy │ Precision │ Recall │ F1     │ Inference   │ Ranking │
[INFO] ├──────────────┼──────┼──────────┼───────────┼────────┼────────┼─────────────┼─────────┤
[INFO] │ LSTM         │ DL   │ 96.5%    │ 96.2%     │ 96.8%  │ 96.5%  │ 48.3ms ±3.1 │ 1       │
[INFO] │ 1D-CNN       │ DL   │ 96.0%    │ 95.8%     │ 96.2%  │ 96.0%  │ 32.7ms ±2.4 │ 2       │
[INFO] │ Random Forest│ ML   │ 95.4%    │ 95.1%     │ 95.7%  │ 95.4%  │ 12.3ms ±0.8 │ 3       │
[INFO] │ SVM          │ ML   │ 94.3%    │ 94.0%     │ 94.6%  │ 94.3%  │  9.5ms ±0.6 │ 4       │
[INFO] └──────────────┴──────┴──────────┴───────────┴────────┴────────┴─────────────┴─────────┘
[INFO]
[INFO] Generating visualization charts...
[INFO]   ✓ Accuracy comparison bar chart saved: backend/model_comparison/reports/charts/accuracy_comparison.png
[INFO]   ✓ Confusion matrix heatmaps saved: backend/model_comparison/reports/charts/confusion_matrices.png
[INFO]   ✓ Inference time comparison saved: backend/model_comparison/reports/charts/inference_time_comparison.png
[INFO]
[INFO] Generating deployment recommendation...
[INFO]   Recommendation: LSTM
[INFO]   Rationale: LSTM achieves highest accuracy (96.5%) with acceptable inference time (48.3ms).
[INFO]   Alternatives considered: 1D-CNN (96.0%, 32.7ms), Random Forest (95.4%, 12.3ms)
[INFO]
[INFO] Exporting reports...
[INFO]   ✓ Markdown report: backend/model_comparison/reports/comparison_report.md
[INFO]   ✓ PDF report: backend/model_comparison/reports/comparison_report.pdf
[INFO]   ✓ JSON data: backend/model_comparison/reports/comparison_data.json
[INFO]   ✓ CSV table: backend/model_comparison/reports/comparison_data.csv
[INFO]
[INFO] ================================================================================
[INFO] Comparison complete! Total time: 78.5 seconds
[INFO] ================================================================================
```

**Verification Steps**:
1. Check that all 4 models appear in comparison table
2. Verify accuracy values match metadata files
3. Confirm LSTM has highest accuracy and ranking = 1
4. Verify SVM (94.3%) is below 95% threshold and ranking = 4
5. Check that 3 chart PNG files exist in reports/charts/
6. Open comparison_report.md and verify it contains:
   - Executive summary
   - Comparison table
   - Embedded chart images
   - Deployment recommendation (LSTM)
7. Open comparison_report.pdf and verify professional formatting
8. Validate comparison_data.json structure matches data-model.md schema
9. Open comparison_data.csv in spreadsheet and verify table structure

**Pass Criteria**:
- ✅ All 4 models loaded without errors
- ✅ Inference time std dev < 10% of mean for all models (per SC-004)
- ✅ Report generation completes in < 120 seconds (per SC-001)
- ✅ All 4 export formats generated successfully
- ✅ Recommendation is "LSTM" (highest accuracy)

---

### Scenario 2: Partial Comparison (Missing Models)

**Goal**: Verify graceful handling when some models are missing.

**Preconditions**:
- Only 2 of 4 models trained (e.g., LSTM and 1D-CNN from Feature 006)
- RF and SVM models missing

**Setup**:
```bash
# Temporarily rename RF and SVM models to simulate missing files
mv backend/ml_models/models/rf_model.pkl backend/ml_models/models/rf_model.pkl.backup
mv backend/ml_models/models/svm_model.pkl backend/ml_models/models/svm_model.pkl.backup
```

**Execution**:
```bash
python backend/model_comparison/scripts/compare_all_models.py
```

**Expected Output**:
```text
[INFO] Loading models...
[WARNING] Model 'rf' not found: FileNotFoundError backend/ml_models/models/rf_model.pkl
[WARNING] Model 'svm' not found: FileNotFoundError backend/ml_models/models/svm_model.pkl
[INFO]   ✓ LSTM loaded from backend/dl_models/models/lstm_model.h5
[INFO]   ✓ 1D-CNN loaded from backend/dl_models/models/cnn_1d_model.h5
[WARNING] Partial comparison: 2/4 models loaded. Missing: rf, svm
[INFO]
[INFO] ⚠️  PARTIAL COMPARISON WARNING
[INFO] This report compares only 2 of 4 models. The following models are missing:
[INFO]   - Random Forest (RF): Model file not found at backend/ml_models/models/rf_model.pkl
[INFO]   - SVM: Model file not found at backend/ml_models/models/svm_model.pkl
[INFO]
[INFO] To generate a complete comparison, please train missing models:
[INFO]   - Feature 005: python backend/ml_models/scripts/train_rf.py
[INFO]   - Feature 005: python backend/ml_models/scripts/train_svm.py
[INFO]
[INFO] Continuing with partial comparison...
[INFO] Running inference benchmarks...
[INFO]   [LSTM] Mean: 48.3ms, Std: 3.1ms
[INFO]   [CNN]  Mean: 32.7ms, Std: 2.4ms
[INFO]
[INFO] Comparison table (PARTIAL - 2/4 models):
[INFO] ┌──────────────┬──────┬──────────┬───────────┬────────┬────────┬─────────────┬─────────┐
[INFO] │ Model        │ Type │ Accuracy │ Precision │ Recall │ F1     │ Inference   │ Ranking │
[INFO] ├──────────────┼──────┼──────────┼───────────┼────────┼────────┼─────────────┼─────────┤
[INFO] │ LSTM         │ DL   │ 96.5%    │ 96.2%     │ 96.8%  │ 96.5%  │ 48.3ms ±3.1 │ 1       │
[INFO] │ 1D-CNN       │ DL   │ 96.0%    │ 95.8%     │ 96.2%  │ 96.0%  │ 32.7ms ±2.4 │ 2       │
[INFO] └──────────────┴──────┴──────────┴───────────┴────────┴────────┴─────────────┴─────────┘
[INFO]
[INFO] Exporting reports (partial comparison)...
[INFO]   ✓ Markdown report: backend/model_comparison/reports/comparison_report.md (with warning banner)
[INFO]   ✓ PDF report: backend/model_comparison/reports/comparison_report.pdf (with warning banner)
```

**Verification Steps**:
1. Verify script does NOT crash/exit with error
2. Confirm warning messages list missing models (RF, SVM)
3. Check that comparison table shows only 2 models (LSTM, 1D-CNN)
4. Verify warning banner appears in both Markdown and PDF reports
5. Confirm recommendation still provided (LSTM vs 1D-CNN only)

**Cleanup**:
```bash
# Restore models
mv backend/ml_models/models/rf_model.pkl.backup backend/ml_models/models/rf_model.pkl
mv backend/ml_models/models/svm_model.pkl.backup backend/ml_models/models/svm_model.pkl
```

**Pass Criteria**:
- ✅ Script completes successfully (does not crash)
- ✅ Clear warnings identify missing models
- ✅ Partial report generated with warning banner
- ✅ Recommendation provided for available models only

---

### Scenario 3: Inference Time Measurement Reliability

**Goal**: Verify inference time measurements are statistically reliable (std dev < 10% of mean).

**Preconditions**:
- All 4 models trained

**Execution**:
```bash
# Run inference benchmark separately with verbose output
python backend/model_comparison/scripts/benchmark_inference.py --model lstm --verbose
```

**Expected Output**:
```text
[INFO] Benchmarking model: LSTM
[INFO] Running 3 warmup iterations...
[INFO]   Warmup run 1: 52.1ms
[INFO]   Warmup run 2: 49.3ms
[INFO]   Warmup run 3: 48.7ms
[INFO] Running 10 timed iterations...
[INFO]   Timed run 1: 47.8ms
[INFO]   Timed run 2: 48.5ms
[INFO]   Timed run 3: 49.2ms
[INFO]   Timed run 4: 47.6ms
[INFO]   Timed run 5: 48.1ms
[INFO]   Timed run 6: 48.9ms
[INFO]   Timed run 7: 47.9ms
[INFO]   Timed run 8: 48.4ms
[INFO]   Timed run 9: 48.7ms
[INFO]   Timed run 10: 48.3ms
[INFO]
[INFO] Statistics (before outlier removal):
[INFO]   Mean: 48.34ms
[INFO]   Std Dev: 0.52ms (1.1% of mean)
[INFO]   Min: 47.6ms, Max: 49.2ms
[INFO]   Outliers (>2σ): None
[INFO]
[INFO] ✅ Reliability check: Std dev (1.1%) < 10% threshold
[INFO]
[INFO] Final result:
[INFO]   Inference time: 48.3ms ± 0.5ms
[INFO]   Samples: 10/10 (no outliers excluded)
```

**Verification Steps**:
1. Verify 3 warmup runs execute but are not included in statistics
2. Confirm 10 timed runs are recorded
3. Check that std dev is < 10% of mean (per SC-004)
4. Verify outlier detection logic (none expected in controlled environment)
5. Validate final result shows mean ± std dev

**Pass Criteria**:
- ✅ Warmup runs excluded from timing statistics
- ✅ Std dev < 10% of mean for all models
- ✅ Outlier detection identifies and excludes anomalous measurements (if any)

---

### Scenario 4: Deployment Recommendation Logic

**Goal**: Verify recommendation algorithm handles various scenarios correctly.

**Test Cases**:

#### 4a. Clear Winner (Single Highest Accuracy)
**Given**: LSTM = 96.5%, 1D-CNN = 96.0%, RF = 95.4%, SVM = 94.3%
**Expected Recommendation**: LSTM
**Rationale**: Highest accuracy, meets threshold

#### 4b. Accuracy Tie (Within 1%)
**Given**: LSTM = 96.5% (48ms), 1D-CNN = 96.4% (32ms), RF = 95.4%, SVM = 94.3%
**Expected Recommendation**: 1D-CNN
**Rationale**: Tied accuracy (<1% difference), faster inference time

#### 4c. No Models Meet Threshold
**Given**: All models < 95% accuracy (e.g., RF = 94.5%, SVM = 93.8%, LSTM = 94.2%, 1D-CNN = 94.0%)
**Expected Recommendation**: NONE
**Rationale**: "No models meet ≥95% accuracy threshold. Investigate data quality or retrain models."
**Alternative Actions**: ["Hyperparameter tuning", "Data augmentation", "Feature engineering"]

#### 4d. Perfect Tie (Accuracy AND Latency)
**Given**: LSTM = 96.5% (48ms), 1D-CNN = 96.5% (47ms)
**Expected Recommendation**: 1D-CNN (slightly faster)
**Or**: "TIE - recommend ensemble deployment" if latency difference < 5ms

**Execution**:
```bash
# Test recommendation logic with mock data
python backend/model_comparison/scripts/test_recommendation_logic.py
```

**Expected Output**:
```text
[INFO] Testing recommendation logic...
[INFO]
[INFO] Test Case 4a: Clear Winner
[INFO]   Input: LSTM=96.5%, CNN=96.0%, RF=95.4%, SVM=94.3%
[INFO]   Recommendation: LSTM
[INFO]   Rationale: "LSTM achieves highest accuracy (96.5%) among qualified models."
[INFO]   ✅ PASS
[INFO]
[INFO] Test Case 4b: Accuracy Tie
[INFO]   Input: LSTM=96.5% (48ms), CNN=96.4% (32ms)
[INFO]   Recommendation: 1D-CNN
[INFO]   Rationale: "Models achieve similar accuracy (~96.5%). 1D-CNN recommended for faster inference (32ms)."
[INFO]   ✅ PASS
[INFO]
[INFO] Test Case 4c: No Models Meet Threshold
[INFO]   Input: All models < 95%
[INFO]   Recommendation: NONE
[INFO]   Alternative Actions: ["Hyperparameter tuning", "Data augmentation", "Feature engineering"]
[INFO]   ✅ PASS
[INFO]
[INFO] Test Case 4d: Perfect Tie
[INFO]   Input: LSTM=96.5% (48ms), CNN=96.5% (47ms)
[INFO]   Recommendation: 1D-CNN (faster)
[INFO]   ✅ PASS
[INFO]
[INFO] ================================================================================
[INFO] All recommendation logic tests passed (4/4)
[INFO] ================================================================================
```

**Pass Criteria**:
- ✅ All 4 test cases return expected recommendations
- ✅ Rationale clearly explains decision logic
- ✅ Tie-breaking rules applied correctly
- ✅ Edge cases handled gracefully

---

### Scenario 5: Deployment Decision Documentation

**Goal**: Verify deployment decision can be recorded and exported.

**Preconditions**:
- Comparison report generated (Scenario 1 complete)
- Supervisor has reviewed report and selected model

**Execution**:
```bash
# Document deployment decision
python backend/model_comparison/scripts/document_decision.py \
  --model lstm \
  --supervisor "Dr. Reem" \
  --rationale "Highest accuracy (96.5%) among all models. 48ms inference time meets real-time requirements." \
  --alternatives "cnn_1d:0.5% lower accuracy,rf:1.1% lower accuracy"
```

**Expected Output**:
```text
[INFO] ================================================================================
[INFO] Deployment Decision Documentation
[INFO] ================================================================================
[INFO] Loading comparison report...
[INFO]   ✓ Comparison report found: backend/model_comparison/reports/comparison_report.md
[INFO]
[INFO] Recording deployment decision:
[INFO]   Selected model: LSTM
[INFO]   Supervisor: Dr. Reem
[INFO]   Decision date: 2026-02-15 14:30:22
[INFO]   Accuracy threshold met: ✅ Yes (96.5%)
[INFO]   Latency consideration: Tiebreaker
[INFO]
[INFO] Alternatives considered:
[INFO]   - 1D-CNN: Rejected (0.5% lower accuracy)
[INFO]   - Random Forest: Rejected (1.1% lower accuracy)
[INFO]
[INFO] Saving decision document...
[INFO]   ✓ Markdown: backend/model_comparison/decisions/decision_2026-02-15_143022.md
[INFO]   ✓ PDF: backend/model_comparison/decisions/decision_2026-02-15_143022.pdf
[INFO]
[INFO] ================================================================================
[INFO] Decision documented successfully!
[INFO] ================================================================================
```

**Verification Steps**:
1. Check that decision Markdown file created with timestamped filename
2. Verify YAML front matter contains all required fields:
   - `decision_id` (UUID)
   - `timestamp` (ISO 8601)
   - `supervisor_name` ("Dr. Reem")
   - `selected_models` (["lstm"])
   - `approval_status` ("APPROVED")
3. Verify Markdown body includes:
   - Decision summary
   - Metrics snapshot
   - Alternatives considered with rejection reasons
   - Trade-off analysis
   - Approval section
4. Verify PDF export exists and is professionally formatted
5. Check that decision can be loaded and parsed back to JSON

**Pass Criteria**:
- ✅ Decision file created with correct structure
- ✅ All metadata fields populated accurately
- ✅ Rationale clearly explains selection logic
- ✅ PDF export generated successfully
- ✅ File is version-control friendly (Markdown with YAML)

---

### Scenario 6: Decision History Tracking

**Goal**: Verify decision updates are tracked in change history.

**Preconditions**:
- Initial decision documented (Scenario 5 complete)

**Execution**:
```bash
# Update decision (e.g., change status to APPROVED after supervisor review)
python backend/model_comparison/scripts/document_decision.py \
  --update decision_2026-02-15_143022 \
  --status APPROVED \
  --change-notes "Approved by Dr. Reem after review meeting"
```

**Expected Output**:
```text
[INFO] Updating decision: decision_2026-02-15_143022
[INFO]   Previous status: DRAFT
[INFO]   New status: APPROVED
[INFO]   Change notes: "Approved by Dr. Reem after review meeting"
[INFO]
[INFO] Appending to change history...
[INFO]   ✓ Change record added: 2026-02-15 15:45:10 - UPDATED - Status changed to APPROVED
[INFO]
[INFO] Saving updated decision...
[INFO]   ✓ Markdown: backend/model_comparison/decisions/decision_2026-02-15_143022.md (updated)
[INFO]   ✓ PDF: backend/model_comparison/decisions/decision_2026-02-15_143022.pdf (regenerated)
[INFO]
[INFO] Decision updated successfully!
```

**Verification Steps**:
1. Open decision Markdown file
2. Verify `approval_status` updated to "APPROVED"
3. Check that `change_history` array contains 2 entries:
   - Entry 1: "2026-02-15 14:30:22 - CREATED by comparison script"
   - Entry 2: "2026-02-15 15:45:10 - UPDATED - Status changed to APPROVED"
4. Confirm change history is chronologically ordered
5. Verify PDF regenerated with updated status

**Pass Criteria**:
- ✅ Decision status updated correctly
- ✅ Change history appended (not overwritten)
- ✅ Chronological ordering maintained
- ✅ PDF reflects latest changes

---

### Scenario 7: Data Consistency Validation

**Goal**: Verify that all models were evaluated on the same test dataset before comparison.

**Preconditions**:
- All 4 models trained

**Test Setup** (Simulate inconsistency):
```python
# Manually edit one model's metadata to have different test_samples_count
# Edit backend/dl_models/models/cnn_1d_model.json
# Change "test_samples" from 87 to 75
```

**Execution**:
```bash
python backend/model_comparison/scripts/compare_all_models.py --validate-consistency
```

**Expected Output**:
```text
[INFO] Loading models...
[INFO]   ✓ All 4 models loaded
[INFO]
[ERROR] Data consistency validation failed!
[ERROR]
[ERROR] Test dataset size mismatch detected:
[ERROR]   - RF:     87 samples
[ERROR]   - SVM:    87 samples
[ERROR]   - LSTM:   87 samples
[ERROR]   - 1D-CNN: 75 samples  ❌ INCONSISTENT
[ERROR]
[ERROR] All models must be evaluated on identical test sets for valid comparison.
[ERROR] Please retrain 1D-CNN model using the same test dataset:
[ERROR]   python backend/dl_models/scripts/train_cnn_1d.py
[ERROR]
[ERROR] Aborting comparison.
```

**Verification Steps**:
1. Verify script detects test sample count mismatch
2. Confirm clear error message identifies problematic model (1D-CNN)
3. Check that comparison is NOT generated when validation fails
4. Verify actionable remediation instructions provided

**Cleanup**:
```python
# Restore cnn_1d_model.json to correct test_samples value (87)
```

**Pass Criteria**:
- ✅ Data inconsistency detected automatically
- ✅ Script exits with clear error (does not generate invalid comparison)
- ✅ Error message identifies specific model with inconsistent data
- ✅ Remediation instructions provided (retrain model)

---

## Usage Examples

### Example 1: Run Complete Comparison

```bash
# From repository root
cd "C:/Data from HDD/Graduation Project/Platform"

# Run comparison (generates all reports)
python backend/model_comparison/scripts/compare_all_models.py

# View Markdown report
cat backend/model_comparison/reports/comparison_report.md

# Open PDF report (Windows)
start backend/model_comparison/reports/comparison_report.pdf

# Open PDF report (Linux/Mac)
xdg-open backend/model_comparison/reports/comparison_report.pdf
```

### Example 2: Benchmark Single Model

```bash
# Benchmark LSTM inference time only
python backend/model_comparison/scripts/benchmark_inference.py --model lstm --verbose

# Benchmark all models (without generating full report)
python backend/model_comparison/scripts/benchmark_inference.py --model all
```

### Example 3: Document Deployment Decision

```bash
# Interactive decision documentation
python backend/model_comparison/scripts/document_decision.py --interactive

# Non-interactive with CLI arguments
python backend/model_comparison/scripts/document_decision.py \
  --model lstm \
  --supervisor "Dr. Reem" \
  --rationale "Highest accuracy with acceptable latency" \
  --alternatives "cnn_1d:Lower accuracy,rf:Lower accuracy"
```

### Example 4: Export Comparison Data

```bash
# Comparison script already exports JSON and CSV automatically
# To manually export from existing comparison:
python backend/model_comparison/scripts/generate_report.py --input comparison_data.json --export csv

# View CSV in terminal
cat backend/model_comparison/reports/comparison_data.csv

# Load JSON for analysis
python -c "import json; print(json.dumps(json.load(open('backend/model_comparison/reports/comparison_data.json')), indent=2))"
```

## Troubleshooting

### Issue: ModuleNotFoundError for matplotlib or reportlab

**Solution**:
```bash
pip install -r backend/requirements.txt
# Or install individually:
pip install matplotlib>=3.10.0 reportlab>=4.4.0
```

### Issue: "No trained models found" error

**Solution**: Train models from Features 005 and 006 first:
```bash
# Feature 005: ML Models
python backend/ml_models/scripts/train_rf.py
python backend/ml_models/scripts/train_svm.py

# Feature 006: DL Models
python backend/dl_models/scripts/train_lstm.py
python backend/dl_models/scripts/train_cnn_1d.py
```

### Issue: Chart generation fails with "TclError: no display name"

**Cause**: Matplotlib requires display server (common in headless environments)

**Solution**: Use non-interactive backend:
```bash
# Set environment variable before running comparison
export MPLBACKEND=Agg
python backend/model_comparison/scripts/compare_all_models.py
```

### Issue: PDF generation is very slow or fails

**Solution**: Ensure ReportLab installed and check available memory:
```bash
pip show reportlab  # Verify installation
# If PDF generation takes >60 seconds, check system resources
# Consider running comparison on machine with more RAM
```

## Next Steps

After validating these scenarios:
1. Run `/speckit.tasks` to generate task breakdown for implementation
2. Execute implementation via `/speckit.implement`
3. Run pytest tests to verify unit test coverage
4. Generate final comparison report with actual trained models
5. Document deployment decision with supervisor (Dr. Reem)
6. Include comparison report and decision documentation in graduation project deliverables
