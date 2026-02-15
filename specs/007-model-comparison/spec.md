# Feature Specification: Model Comparison & Deployment Selection

**Feature Branch**: `007-model-comparison`
**Created**: 2026-02-15
**Status**: Draft
**Input**: User description: "2.4 Comparison & Selection - 2.4.1 Model Comparison Report Compare all 4 models: accuracy, precision, recall, F1, confusion matrix, inference time. Generate comparison table + charts. 2.4.2 Supervisor Review & Selection Present results to Dr. Reem. Decide which model(s) to deploy based on accuracy vs latency trade-off."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generate Comprehensive Model Comparison Report (Priority: P1-MVP)

Dr. Reem (project supervisor) needs a comprehensive comparison of all 4 trained models (Random Forest, SVM, LSTM, 1D-CNN) to evaluate their performance and make an informed deployment decision. The report must include all key performance metrics, inference time measurements, and visual comparisons to facilitate objective model selection.

**Why this priority**: This is the MVP because it delivers the core value - a complete, objective comparison of all models that enables data-driven decision making. Without this report, there's no systematic way to evaluate and select models for deployment.

**Independent Test**: Can be fully tested by running the comparison script with all 4 trained models present, verifying that the generated report contains accurate metrics, comparison tables, and charts for all models. Delivers a presentable comparison document that can be reviewed independently.

**Acceptance Scenarios**:

1. **Given** all 4 models are trained (RF, SVM, LSTM, 1D-CNN with their metadata files), **When** the comparison script is executed, **Then** a comprehensive report is generated containing accuracy, precision, recall, F1-score, confusion matrices, and inference time for each model.

2. **Given** the comparison report has been generated, **When** a researcher opens the report file, **Then** they see a side-by-side comparison table showing all metrics and at least 3 visualization charts (accuracy comparison, confusion matrices, inference time comparison).

3. **Given** all 4 models exist with varying performance levels, **When** the comparison analysis runs, **Then** the system ranks models by accuracy, identifies the fastest model, and provides a recommendation based on the accuracy-latency trade-off.

4. **Given** the test dataset has 87 samples, **When** inference time is measured for each model, **Then** each model's prediction time is averaged over all test samples and reported in milliseconds with standard deviation.

5. **Given** the comparison report includes confusion matrices, **When** reviewing each model's confusion matrix, **Then** true positives, true negatives, false positives, and false negatives are clearly labeled and visualized as heatmaps.

---

### User Story 2 - Facilitate Deployment Decision Documentation (Priority: P2)

Dr. Reem needs to document the final deployment decision with clear rationale, including which model(s) were selected for deployment, why they were chosen, and what trade-offs were considered. This documentation will be part of the project deliverables and graduation requirements.

**Why this priority**: This is P2 because it depends on the comparison report (P1) but adds critical value for project documentation, reproducibility, and academic requirements. It formalizes the decision-making process.

**Independent Test**: Can be fully tested by reviewing the decision documentation file after a model selection is made, verifying that it contains the selected model(s), quantitative rationale (metric thresholds), qualitative rationale (use case considerations), and supervisor approval. Delivers a formal decision record.

**Acceptance Scenarios**:

1. **Given** the comparison report has been generated, **When** Dr. Reem reviews the results and selects a model for deployment, **Then** the system records the decision including: selected model name, key metrics that influenced the decision, and timestamp.

2. **Given** multiple models meet the ≥95% accuracy threshold, **When** the deployment decision is made, **Then** the documentation includes a trade-off analysis explaining why one model was chosen over others (e.g., "LSTM selected over 1D-CNN due to 0.5% higher accuracy despite 20ms slower inference time").

3. **Given** the deployment decision has been documented, **When** the decision file is exported, **Then** it is saved as both Markdown and PDF formats for inclusion in the graduation project report.

4. **Given** model performance metrics change (e.g., retraining with more data), **When** a new comparison is run, **Then** the decision documentation preserves the history of previous decisions with timestamps.

---

### Edge Cases

- **What happens when some models are missing or not trained yet?**
  System should detect missing models and generate a partial comparison report with a clear warning listing which models are unavailable. Report should still be generated for available models.

- **What happens when models were trained on different test set sizes?**
  System should validate that all models use the same test set (same number of samples and features) and fail with a clear error message if test sets differ. Comparison is only valid for identical evaluation data.

- **How does system handle inference time measurement variability?**
  Inference time should be measured over multiple runs (minimum 10 iterations after 3 warmup iterations) and reported as mean ± standard deviation. Outliers beyond 2 standard deviations should be excluded.

- **What if models have identical performance metrics?**
  System should detect ties and report "TIE" status, recommending the model with faster inference time as a tiebreaker. If inference times are also tied (within 5ms), recommend BOTH models for ensemble deployment.

- **What if all models fail to meet the ≥95% accuracy threshold?**
  Comparison report should still be generated with a prominent warning. Recommendation section should suggest investigating data quality, hyperparameter tuning, or data augmentation strategies rather than recommending deployment.

- **How does system handle missing confusion matrix data in model metadata?**
  System should attempt to reconstruct confusion matrix from model predictions on test set. If model file is missing or cannot be loaded, mark confusion matrix as "Unavailable" in the report.

- **What if comparison script is run before any models are trained?**
  System should check for at least one trained model before proceeding. If zero models found, exit with a clear error message: "No trained models found. Please complete Feature 005 (ML Models) and Feature 006 (DL Models) first."

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST load model metadata from all 4 model types (Random Forest, SVM from Feature 005; LSTM, 1D-CNN from Feature 006).
- **FR-002**: System MUST extract performance metrics from each model's metadata file: accuracy, precision, recall, F1-score, confusion matrix.
- **FR-003**: System MUST measure inference time for each model by running predictions on the test dataset (87 samples × 128 timesteps × 6 features for DL models; 87 samples × 18 features for ML models).
- **FR-004**: System MUST generate a comparison table showing all metrics side-by-side for all 4 models in a structured format (CSV and Markdown).
- **FR-005**: System MUST generate at least 3 visualization charts: (1) accuracy comparison bar chart, (2) confusion matrix heatmaps (one per model), (3) inference time comparison bar chart with error bars.
- **FR-006**: System MUST produce a consolidated comparison report in both Markdown and PDF formats containing: executive summary, comparison table, all charts, and deployment recommendation.
- **FR-007**: System MUST provide a deployment recommendation based on accuracy-latency trade-off with explicit threshold: "If accuracy difference < 1%, recommend faster model; otherwise recommend more accurate model."
- **FR-008**: System MUST validate that all models were evaluated on identical test datasets before comparing (same number of samples, same feature dimensions).
- **FR-009**: System MUST rank models by accuracy (primary) and inference time (secondary) and display rankings in the comparison table.
- **FR-010**: System MUST handle missing models gracefully by generating a partial comparison report with warnings for unavailable models.
- **FR-011**: System MUST create a deployment decision documentation file (Markdown) that records: selected model(s), decision rationale, key metrics, supervisor name, decision date.
- **FR-012**: System MUST allow updating the deployment decision documentation if the decision changes (e.g., after model retraining or further evaluation).
- **FR-013**: System MUST export all comparison data (metrics table, inference times, decision records) as structured JSON for potential future analysis or integration with other tools.
- **FR-014**: System MUST include metadata in the comparison report: TremoAI project name, report generation date, TensorFlow/scikit-learn versions, test dataset details.

### Key Entities

- **Model Comparison Record**: Aggregates performance metrics from all 4 models. Attributes: model_name, model_type (ML/DL), accuracy, precision, recall, f1_score, confusion_matrix, inference_time_ms, inference_time_std, test_samples_count, meets_threshold_95, ranking.

- **Inference Benchmark**: Stores inference time measurements for each model. Attributes: model_name, run_id, sample_id, inference_time_ms, timestamp, hardware_info (CPU/GPU).

- **Deployment Decision**: Documents the final model selection decision. Attributes: decision_id, selected_models (list), decision_date, supervisor_name, rationale_text, accuracy_threshold_met, latency_consideration, alternative_models_considered, approval_status.

- **Comparison Report**: The final deliverable document. Attributes: report_id, generation_date, models_compared (list), executive_summary, comparison_table, chart_paths (list), recommendation_text, export_formats (markdown, pdf, json).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 4 trained models (RF, SVM, LSTM, 1D-CNN) can be compared in a single unified report within 2 minutes of execution.

- **SC-002**: Comparison report includes all required metrics for each model: accuracy (percentage), precision (percentage), recall (percentage), F1-score (percentage), confusion matrix (4 values), inference time (milliseconds with standard deviation).

- **SC-003**: Visual comparison charts clearly distinguish model performance with labeled axes, legends, and at least 3 distinct chart types (bar charts, heatmaps).

- **SC-004**: Inference time measurements are statistically reliable with standard deviation < 10% of mean for each model (averaged over minimum 10 runs).

- **SC-005**: Deployment recommendation is actionable, clearly stating which model to deploy with quantitative justification (e.g., "Deploy LSTM: 96.5% accuracy, 50ms inference time - best accuracy-latency balance").

- **SC-006**: Comparison report is presentable to non-technical stakeholders (supervisor, graduation committee) with clear executive summary and visual aids.

- **SC-007**: Report generation is reproducible - running the comparison script multiple times produces identical performance metrics (excluding inference time variance).

- **SC-008**: Deployment decision documentation can be exported in multiple formats (Markdown, PDF) and includes all required fields (model, rationale, date, approval).

- **SC-009**: System validates data consistency across models, ensuring all models were evaluated on the exact same test set before comparison.

- **SC-010**: Comparison process completes successfully even if 1-2 models are missing, generating a partial report with clear warnings.

## Assumptions

- All 4 models (RF, SVM, LSTM, 1D-CNN) have already been trained via Features 005 and 006 and their metadata files exist in the expected locations.
- Test dataset used for all model evaluations is the same (87 samples × various feature dimensions depending on model type).
- Model metadata files follow the standardized JSON format established in Features 005 and 006.
- Inference time measurements will be performed on the same hardware to ensure fair comparison (CPU-based by default, GPU if available for DL models).
- The ≥95% accuracy threshold is a hard requirement for model deployment consideration, as established in earlier features.
- Supervisor (Dr. Reem) will review the comparison report manually and make the final deployment decision - system provides recommendation but does not auto-deploy.
- PDF generation will use ReportLab (already in requirements.txt from Feature 003) or a Markdown-to-PDF converter.
- Comparison charts will be generated using Matplotlib (already in requirements.txt) and embedded in the report.
- Deployment decision documentation is for academic/project tracking purposes and does not trigger actual model deployment to production (that would be a future Feature 007: Model Serving API).

## Dependencies

- **Feature 005 (ML Models Training)**: Requires trained Random Forest and SVM models with metadata files (`rf_model.json`, `svm_model.json`).
- **Feature 006 (DL Models Training)**: Requires trained LSTM and 1D-CNN models with metadata files (`lstm_model.json`, `cnn_1d_model.json`).
- **Feature 004 (ML/DL Data Preparation)**: Requires test dataset (`test_sequences.npy`, `test_seq_labels.npy`, `test_features.npy`, `test_labels.npy`) for inference time measurements.
- **Python libraries**: Matplotlib (charts), ReportLab (PDF), scikit-learn (loading ML models), TensorFlow (loading DL models), NumPy, pandas (data manipulation).

## Out of Scope

- **Hyperparameter tuning**: This feature only compares existing trained models, it does not retrain or optimize models.
- **Model deployment/serving**: Actual deployment to a production API endpoint is out of scope (future Feature 007).
- **Ensemble model creation**: Combining multiple models (e.g., voting, stacking) is out of scope for this feature.
- **Real-time monitoring dashboard**: An interactive web dashboard for live model comparison is out of scope (static reports only).
- **Cross-validation comparison**: Models are compared only on the test set, not on k-fold cross-validation results.
- **Statistical significance testing**: P-values, confidence intervals, or hypothesis testing for performance differences are out of scope (simple ranking only).
- **Model explainability analysis**: Feature importance, SHAP values, or attention visualizations are out of scope for this comparison feature.
