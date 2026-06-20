# Feature Specification: Reports Page & PDF Download

**Feature Branch**: `035-reports-pdf`
**Created**: 2026-02-21
**Status**: Draft
**Input**: User description: "N-4.3.1 Reports Page + PDF Download Date range picker. Stats preview: avg amplitude, max amplitude, dominant freq, tremor reduction %. Download PDF button calling backend report endpoint."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Date Range Selection & Statistics Preview (Priority: P1)

A doctor navigates to the Reports page for a specific patient. They select a date range using a date picker and immediately see a preview of key tremor metrics aggregated across that period: average amplitude, maximum amplitude, dominant frequency, and tremor reduction percentage compared to the patient's baseline. This gives the doctor a quick at-a-glance clinical summary without needing to download anything.

**Why this priority**: The statistics preview is the primary clinical value. A doctor needs to understand a patient's tremor trends before deciding whether to export a report. This story is independently useful even without the PDF download.

**Independent Test**: Navigate to `/doctor/patients/{id}/reports`, select a 30-day range, and verify that the four metric cards populate with numeric values. Change the date range and verify the values update. Select a range with no data and verify an informative "No data" message appears.

**Acceptance Scenarios**:

1. **Given** a doctor is viewing a patient's reports page, **When** they select a valid date range with existing sessions, **Then** four metric cards display: average amplitude, maximum amplitude, dominant frequency (in Hz), and tremor reduction % (labelled and with units).
2. **Given** a valid date range is selected, **When** the data loads, **Then** the tremor reduction % shows a positive value (improvement vs baseline) or a clearly labelled negative value (worsening).
3. **Given** a doctor selects a start date after the end date, **When** they attempt to apply the range, **Then** an inline validation message prevents the query and explains the error.
4. **Given** a doctor selects a date range with no recorded sessions, **When** the preview loads, **Then** a clear "No data available for this period" message is shown and the metric cards are hidden.
5. **Given** a doctor selects a future date as the end date, **When** they attempt to apply the range, **Then** the date picker prevents selecting future dates.

---

### User Story 2 — PDF Report Download (Priority: P2)

After viewing the statistics preview, a doctor clicks "Download PDF" to receive a formatted PDF document for the selected date range. The PDF includes patient information, the aggregated statistics, trend charts, and an ML severity distribution summary. The download starts automatically without navigating away from the page.

**Why this priority**: The PDF serves as a shareable clinical record for patient files, referrals, or follow-up appointments. It builds directly on the selected date range from User Story 1.

**Independent Test**: With a valid date range selected and stats visible, click "Download PDF" and verify a `.pdf` file is downloaded to the local machine. Open the file and verify it contains the patient's name, the report period, and the statistics summary.

**Acceptance Scenarios**:

1. **Given** a valid date range with data is selected, **When** the doctor clicks "Download PDF", **Then** a PDF file download starts within 10 seconds and the button shows a loading state during generation.
2. **Given** the PDF is successfully generated, **When** it downloads, **Then** it contains: the patient's name, the report date range, the four key metrics, trend charts, and ML severity distribution.
3. **Given** the selected date range has no session data, **When** the doctor attempts to download, **Then** the "Download PDF" button is disabled and a tooltip explains why.
4. **Given** a PDF generation error occurs, **When** the doctor clicks "Download PDF", **Then** a user-friendly error message is shown (e.g., "Report generation failed — please try a smaller date range") and no broken file is downloaded.
5. **Given** the PDF generation succeeds, **When** the doctor opens the downloaded file, **Then** the file is a valid, readable PDF.

---

### Edge Cases

- What happens when the selected date range spans years with thousands of sessions? The stats preview should still load promptly; the PDF may take longer with a visible loading indicator.
- How does the system handle a patient with no sessions at all? The page should still load, the date picker should be usable, and the empty state should display clearly.
- What if the doctor navigates away during PDF generation? The download continues in the background as a browser-managed file transfer.
- What if the date range is valid but the patient has only one session? Stats should still display (with tremor reduction % shown as "N/A — insufficient baseline data" if no baseline exists).
- What if the patient is not assigned to the currently logged-in doctor? The page should not be accessible and should redirect with an appropriate message.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Reports page MUST be accessible from a patient's profile page via a clearly labelled navigation entry point.
- **FR-002**: The page MUST display a date range picker with a start date and end date field; both default to a 30-day window ending today.
- **FR-003**: The date picker MUST prevent selection of future dates for both start and end fields.
- **FR-004**: The date picker MUST validate that the start date is not after the end date and display an inline error if violated.
- **FR-005**: Upon selecting a valid date range, the system MUST fetch and display four summary metrics: average tremor amplitude, maximum tremor amplitude, dominant tremor frequency (Hz), and tremor reduction percentage versus the patient's baseline.
- **FR-006**: When no session data exists for the selected range, the system MUST display a clear empty-state message and hide the metric cards.
- **FR-007**: The tremor reduction % MUST be visually distinguished as positive (improvement) or negative (worsening), using color or a sign indicator.
- **FR-008**: A "Download PDF" button MUST be present on the page and MUST be disabled when no data is available for the selected range.
- **FR-009**: Clicking "Download PDF" MUST trigger a PDF file download for the selected date range, scoped to the current patient.
- **FR-010**: During PDF generation, the button MUST show a loading state and MUST NOT allow duplicate requests.
- **FR-011**: If PDF generation fails, the system MUST display a user-friendly error message without downloading a corrupt or empty file.
- **FR-012**: The Reports page MUST enforce access control: only the assigned doctor may view the reports for a given patient.

### Key Entities

- **Report Configuration**: The date range (start date, end date) and patient scope for a report request; determines which session data is included.
- **Statistics Summary**: Aggregated metrics for the selected period — average amplitude, maximum amplitude, dominant frequency, tremor reduction percentage versus baseline, and session count.
- **Patient Baseline**: The patient's initial tremor amplitude (derived from their earliest sessions) used as the reference point for calculating tremor reduction %.
- **PDF Report**: A downloadable document containing patient information, the statistics summary, session trend charts, and ML severity distribution for the selected period.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A doctor can select a date range and see the four summary metrics displayed within 3 seconds on a normal connection.
- **SC-002**: The "Download PDF" button produces a downloaded file within 10 seconds for date ranges up to 90 days.
- **SC-003**: 100% of invalid date inputs (end before start, future dates) are caught with inline validation before any server request is made.
- **SC-004**: When no data exists for the selected range, the empty state is displayed without any unhandled errors or broken UI.
- **SC-005**: The downloaded PDF file is valid (opens without errors), contains the correct patient name and date range, and matches the metrics shown in the preview.
- **SC-006**: A doctor cannot access the reports page of a patient not assigned to them (redirected or shown an access-denied message).

---

## Assumptions

- The Reports page is scoped to a single patient, accessed via a link from the patient's detail page (e.g., `/doctor/patients/{id}/reports`).
- The default date range on page load is the last 30 calendar days (today minus 29 days to today).
- "Average amplitude" and "maximum amplitude" in the stats preview are computed by aggregating daily statistics across the selected period.
- "Tremor reduction %" compares the current period's average amplitude against the patient's historical baseline (their earliest recorded sessions), with a positive value indicating improvement.
- If a patient has fewer sessions than needed to establish a baseline, tremor reduction % is displayed as "Unavailable".
- PDF generation happens synchronously and the resulting file is delivered directly to the browser as a download attachment.
- Only doctors can access this feature; the feature description does not call for patient-facing reports access.
- The backend report endpoint already exists and accepts `patient_id`, `start_date`, and `end_date` parameters.
