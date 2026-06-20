# Feature Specification: Analytics and Reporting

**Feature Branch**: `003-analytics-reporting`
**Created**: 2026-02-15
**Status**: Draft
**Input**: User description: "3.4 Analytics - 3.4.1 Tremor Stats Endpoint (Avg amplitude, dominant freq, tremor reduction %. Group by session/day.) + 3.4.2 PDF Report Generation (Generate PDF report with tremor stats, charts, and model prediction results.)"

## User Scenarios & Testing

### User Story 1 - Tremor Statistics Aggregation (Priority: P1)

Doctors need to view aggregated tremor statistics for their patients to track treatment effectiveness and disease progression over time. The system provides statistical summaries (average amplitude, dominant frequency, tremor reduction percentage) grouped by session or day.

**Why this priority**: This is the foundation for clinical decision-making. Doctors cannot assess treatment effectiveness without historical data aggregation. This delivers immediate value by transforming raw sensor data into actionable clinical insights.

**Independent Test**: Can be fully tested by querying the statistics endpoint with date range parameters for a patient with historical biometric sessions. Delivers value by showing tremor trends without needing PDF generation.

**Acceptance Scenarios**:

1. **Given** a patient has 10 biometric sessions over 5 days, **When** doctor requests daily statistics, **Then** system returns 5 data points with average amplitude, dominant frequency, and tremor reduction percentage for each day
2. **Given** a patient has multiple sessions in one day, **When** doctor requests session-level statistics, **Then** system returns individual statistics for each session with timestamps
3. **Given** doctor selects a date range (last 30 days), **When** requesting statistics, **Then** system returns aggregated data only for sessions within that range
4. **Given** patient has no biometric sessions in the selected period, **When** requesting statistics, **Then** system returns empty result set with appropriate message

---

### User Story 2 - PDF Report Generation (Priority: P2)

Doctors need to generate comprehensive PDF reports containing tremor statistics, visual charts, and ML prediction results for patient consultations, medical records, and sharing with specialists.

**Why this priority**: While statistics viewing is essential (P1), PDF reports enable offline review, patient consultations, and medical record documentation. This is important but can be implemented after basic statistics are available.

**Independent Test**: Can be tested by requesting report generation for a patient with statistics data. Delivers value by producing shareable documentation even if advanced features are missing.

**Acceptance Scenarios**:

1. **Given** patient has tremor statistics available, **When** doctor requests PDF report, **Then** system generates PDF with summary statistics table, line charts showing trends, and ML prediction results
2. **Given** doctor specifies date range for report, **When** generating PDF, **Then** report includes only data from specified period with clear date labels
3. **Given** patient has ML predictions from multiple sessions, **When** generating report, **Then** PDF displays severity distribution (mild/moderate/severe) with percentages
4. **Given** large dataset (100+ sessions), **When** generating report, **Then** PDF is created within 10 seconds and file size remains under 5MB

---

### User Story 3 - Report Customization and Export (Priority: P3)

Doctors need to customize report content (select specific metrics, time periods, chart types) and export reports in different formats or share directly with patients or specialists.

**Why this priority**: Customization improves usability but is not essential for core value delivery. Can be added after basic report generation works.

**Independent Test**: Can be tested by specifying custom report parameters and validating output matches selections.

**Acceptance Scenarios**:

1. **Given** doctor wants specific metrics only, **When** selecting amplitude and frequency (excluding tremor reduction), **Then** generated report includes only selected metrics
2. **Given** doctor needs to share report with patient, **When** selecting "patient-friendly" format, **Then** report uses simplified language and removes technical jargon
3. **Given** report is generated, **When** doctor requests different chart types (bar chart vs line chart), **Then** report regenerates with selected visualization

---

### Edge Cases

- What happens when patient has only 1 or 2 biometric sessions (insufficient data for trend analysis)?
- How does system handle missing ML predictions for some sessions?
- What if tremor reduction percentage cannot be calculated (no baseline data)?
- How does system handle concurrent report generation requests for same patient?
- What happens when PDF generation fails (out of memory, chart rendering error)?
- How are sessions with incomplete sensor data (missing timestamps, invalid values) handled in statistics?
- What if date range spans multiple years (performance impact)?

## Requirements

### Functional Requirements

- **FR-001**: System MUST aggregate tremor intensity values across biometric sessions to calculate average amplitude
- **FR-002**: System MUST calculate dominant frequency from frequency data across sessions
- **FR-003**: System MUST calculate tremor reduction percentage by comparing recent sessions against baseline (first session or earliest sessions)
- **FR-004**: System MUST support grouping statistics by individual session or by day (all sessions in a day aggregated)
- **FR-005**: System MUST support filtering statistics by date range (start date to end date)
- **FR-006**: System MUST generate PDF reports containing tremor statistics summary table
- **FR-007**: System MUST include visual charts in PDF reports (line charts for trends over time)
- **FR-008**: System MUST include ML prediction results in PDF reports (severity classifications with confidence scores)
- **FR-009**: System MUST allow doctors to access statistics and reports for all their assigned patients
- **FR-010**: System MUST allow patients to access statistics and reports for their own data only
- **FR-011**: System MUST validate date ranges (end date must be after start date, dates cannot be future dates)
- **FR-012**: System MUST handle sessions with missing ML predictions gracefully (show N/A or exclude from prediction summary)
- **FR-013**: System MUST return statistics sorted chronologically (oldest to newest)
- **FR-014**: System MUST generate unique filename for each PDF report (patient ID + timestamp)
- **FR-015**: System MUST clean up temporary PDF files after download or after 24 hours

### Key Entities

- **Tremor Statistics Aggregate**: Summary of tremor metrics over a time period
  - Average amplitude (0.0-1.0 normalized value)
  - Dominant frequency (Hz)
  - Tremor reduction percentage (relative to baseline)
  - Time period (session ID or date)
  - Session count (number of sessions included in aggregate)

- **PDF Report**: Generated document for patient tremor analysis
  - Patient information (name, ID)
  - Date range covered
  - Statistics summary table
  - Trend charts (visual representations)
  - ML prediction summary (severity distribution)
  - Generation timestamp
  - File size and format

## Success Criteria

### Measurable Outcomes

- **SC-001**: Doctors can retrieve tremor statistics for any date range within 3 seconds for datasets up to 365 days
- **SC-002**: Statistics calculations are accurate within 0.1% margin of error when compared to manual calculation
- **SC-003**: PDF reports are generated within 10 seconds for datasets containing up to 100 sessions
- **SC-004**: Generated PDF files are under 5MB in size to ensure easy email sharing and quick downloads
- **SC-005**: 90% of doctors successfully generate and download a PDF report on first attempt without errors
- **SC-006**: Tremor reduction percentage correctly reflects improvement or deterioration compared to baseline (validated against clinical expectations)
- **SC-007**: Charts in PDF reports are clearly readable when printed on standard paper (minimum font size, adequate contrast)

## Scope

### In Scope

- Aggregate statistics endpoint (average amplitude, dominant frequency, tremor reduction percentage)
- Grouping by session or day
- Date range filtering for statistics queries
- PDF report generation with statistics tables
- Line charts showing tremor metrics over time in PDF
- ML prediction summary in PDF reports
- Role-based access control (doctors access all assigned patients, patients access own data)
- PDF file generation and download

### Out of Scope

- Real-time statistics updates (use polling or manual refresh)
- Export to formats other than PDF (Excel, CSV) - future enhancement
- Email delivery of reports - future enhancement
- Custom report templates - future enhancement
- Multi-patient comparison reports - future enhancement
- Integration with external medical record systems (EMR/EHR) - future enhancement
- Advanced data visualizations (heatmaps, 3D charts) - future enhancement

## Assumptions

- Biometric sessions already exist in database with sensor data and ML predictions (from Feature 002)
- Patients have at least 2-3 sessions to calculate meaningful statistics (single session provides limited value)
- Baseline for tremor reduction calculation is defined as first session or average of first 3 sessions
- System has sufficient memory and CPU to generate PDFs concurrently (assume up to 5 concurrent report generations)
- PDF generation uses Python libraries available in Django ecosystem
- Charts are generated as images and embedded in PDF (not interactive)
- Date ranges are inclusive (start date and end date both included in results)
- Statistics are calculated on-demand (not pre-computed/cached) for accuracy
- ML predictions are optional - reports work without them but include them if available

## Dependencies

- **Feature 002: Real-Time Pipeline** - Requires BiometricSession model with sensor_data and ml_prediction fields
- **Biometric Sessions**: Must have historical data with valid sensor readings (tremor_intensity, frequency)
- **ML Predictions**: Optional but recommended for complete reports (severity, confidence scores)
- **Patient-Doctor Assignments**: Must be established for access control
- **Authentication System**: JWT authentication required for API access

## Non-Functional Requirements

### Performance
- Statistics queries return results within 3 seconds for 1 year of data
- PDF generation completes within 10 seconds for 100 sessions
- System supports 5 concurrent PDF generations without performance degradation

### Security
- Statistics and reports accessible only to authorized users (doctors for assigned patients, patients for self)
- PDF files stored temporarily with secure random filenames (prevent guessing)
- Temporary PDF files deleted after 24 hours or immediately after download

### Usability
- Error messages clearly explain issues (no data available, invalid date range, insufficient sessions)
- PDF reports formatted professionally for clinical use (readable fonts, clear layouts, proper headers)

### Scalability
- System handles statistics queries for patients with 500+ sessions without timeout
- PDF generation works for reports spanning 2 years of data

## Open Questions

None - specification is complete with reasonable defaults for all aspects.
