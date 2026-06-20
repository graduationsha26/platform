# Feature Specification: Smart Medical Alerts & Dashboard Layout Simplification

**Feature Branch**: `044-smart-alerts-dashboard`
**Created**: 2026-06-14
**Status**: Draft
**Input**: User description: "2.1 Layout Simplification - Remove 7-day global tremor trend chart and its data-fetch hook from DoctorDashboard. 3.1 Smart Medical Alerts - Update Critical Alerts metric card to consume 5-day consecutive severe tremor endpoint. 3.2 Smart Medical Alerts - Add query to count patients with severe tremor readings for 5 consecutive days up to today."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Smart Critical Alerts on Dashboard (Priority: P1)

A doctor opens the dashboard and immediately sees how many of their patients have had severe tremor readings for five or more consecutive days. This count appears in the "Critical Alerts" metric card, replacing a placeholder or stale value. The doctor can use this number to prioritize which patients need urgent attention today without having to manually review individual patient records.

**Why this priority**: Directly improves patient safety by surfacing the most medically urgent cases at a glance. A patient with a 5-day streak of severe tremors is at highest risk and requires immediate clinical attention. This is the core value of the smart alerts feature.

**Independent Test**: Call the analytics endpoint directly with a valid doctor JWT token and verify it returns a numeric count. Then load the dashboard and confirm the Critical Alerts card displays the same number. Can be tested without implementing US2 (the layout change).

**Acceptance Scenarios**:

1. **Given** a doctor is logged in and has patients with severe tremor readings for 5 or more consecutive days, **When** the doctor navigates to the dashboard, **Then** the Critical Alerts metric card shows the exact count of those patients.
2. **Given** a doctor has patients but none have 5 consecutive days of severe tremors, **When** the doctor navigates to the dashboard, **Then** the Critical Alerts card shows "0" (not blank, not an error).
3. **Given** a patient has 4 consecutive days of severe tremors, **When** the doctor views the dashboard, **Then** that patient is NOT counted in the Critical Alerts metric.
4. **Given** a patient has 5 consecutive days of severe tremors followed by a non-severe day, **When** the doctor views the dashboard, **Then** that patient IS counted only if the most recent 5-day window ending today is all severe.
5. **Given** the analytics data source is temporarily unavailable, **When** the doctor views the dashboard, **Then** the Critical Alerts card displays a clear error or loading indicator rather than a stale or zero value.

---

### User Story 2 - Simplified Dashboard Layout (Priority: P2)

A doctor opens the dashboard and sees a cleaner layout. The 7-day global tremor trend chart has been removed. The dashboard now loads faster and presents only the most actionable information — the metric cards — without a chart that aggregates data across all patients into a trend that may not be clinically actionable.

**Why this priority**: Improves dashboard usability and reduces visual clutter. The trend chart consumes screen space and triggers a data request that may not serve immediate clinical decision-making. Removing it simplifies the layout and improves load performance. It is P2 because it is non-additive (a removal) and delivers UX value rather than clinical safety value.

**Independent Test**: Load the doctor dashboard after removing the chart component and verify the chart is absent from the DOM, the dashboard layout renders correctly without empty gaps, and the browser network tab shows one fewer data request on initial load.

**Acceptance Scenarios**:

1. **Given** a doctor navigates to the dashboard, **When** the page loads, **Then** no 7-day tremor trend chart is rendered anywhere on the page.
2. **Given** the chart has been removed, **When** the dashboard loads, **Then** the remaining metric cards and layout elements fill the space cleanly without visual gaps or broken layout.
3. **Given** the chart component and its data-fetch logic have been removed, **When** the dashboard loads, **Then** no network request is made to fetch 7-day trend data.

---

### Edge Cases

- What if a patient has missing tremor readings on some days within a 5-day window (e.g., no data on day 3)? A gap in daily readings breaks the consecutive streak — the patient should not be counted.
- What if today's readings have not yet been recorded? The query should evaluate complete days only; partial-day data should be included if readings exist for today.
- What if a patient has multiple severe readings in a single day — does that count as one severe day? Yes, a calendar day with at least one severe reading counts as a severe day.
- What if the doctor has zero patients assigned? The Critical Alerts count should return 0 with no error.
- What if the layout change leaves the dashboard empty above the fold on smaller screens? The remaining layout must reflow gracefully at all supported viewport sizes.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide an endpoint that returns the count of patients who have had at least one severe-classified tremor reading on each of the 5 consecutive calendar days ending with today.
- **FR-002**: System MUST scope the 5-day consecutive severe tremor count to the patients associated with the authenticated doctor (not a platform-wide aggregate).
- **FR-003**: System MUST treat a calendar day as "severe" if at least one tremor reading on that day is classified as severe; a day with no readings must break the consecutive streak.
- **FR-004**: The "Critical Alerts" metric card on the doctor dashboard MUST display the count retrieved from the 5-day consecutive severe tremor endpoint.
- **FR-005**: The Critical Alerts card MUST show "0" when no patients qualify, and a visible error indicator when the endpoint is unreachable.
- **FR-006**: System MUST remove the 7-day global tremor trend chart component from the doctor dashboard layout.
- **FR-007**: System MUST remove the data-fetching logic (hook or function) that exclusively served the 7-day trend chart, leaving no unused dead code.

### Key Entities

- **Tremor Reading**: A single recorded tremor measurement for a patient on a specific date, carrying a severity classification (normal, mild, moderate, or severe).
- **Consecutive Severe Window**: A patient-level derived metric representing the number of consecutive calendar days ending today on which that patient had at least one severe tremor reading.
- **Critical Alert Count**: An aggregate count of patients whose Consecutive Severe Window equals or exceeds 5 days, scoped to the authenticated doctor's patient list.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Doctors can view the count of patients with 5+ consecutive severe tremor days directly on the dashboard without any additional navigation or manual calculation.
- **SC-002**: The Critical Alerts count reflects data current as of the time the dashboard is loaded — no stale cached values older than the current session.
- **SC-003**: A patient with exactly 4 consecutive severe days is never counted; a patient with exactly 5 consecutive severe days is always counted — zero false positives or false negatives in boundary cases.
- **SC-004**: After the layout simplification, the doctor dashboard renders fully without errors or layout gaps in the area previously occupied by the trend chart.
- **SC-005**: Removing the trend chart results in at least one fewer network request during dashboard initialization compared to the previous implementation.

## Assumptions

- Tremor readings already have a severity classification field in the data store (e.g., "severe", "moderate", "mild", "normal") — no new ML inference or reclassification is required.
- "Consecutive days" means calendar days (midnight-to-midnight), not rolling 24-hour windows.
- The doctor's patient list is already available via the existing authentication and patient-assignment model — no new patient scoping logic is needed beyond what already exists.
- The "Critical Alerts" metric card component already exists in the dashboard; this feature updates its data source, not its visual design.
- The 7-day trend chart being removed is a self-contained component with a dedicated data-fetch hook — removal does not affect any other dashboard component.
- The new endpoint is a read-only analytics query — no writes, no side effects.
