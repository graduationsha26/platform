# Feature Specification: Dashboard Overview Page

**Feature Branch**: `032-dashboard-overview`
**Created**: 2026-02-20
**Status**: Draft
**Input**: User description: "N-4.2.1 Dashboard Overview Page - Summary cards: total patients, active devices, alerts count. 7-day tremor trend line chart fetching from /api/analytics/ stats endpoint."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View System Summary at a Glance (Priority: P1)

A doctor navigates to the dashboard and immediately sees three summary cards: the total number of registered patients, the count of currently active (connected) devices, and the number of outstanding alerts. This gives the doctor an instant situational overview without needing to drill into any sub-pages.

**Why this priority**: Summary cards are the most critical element — they surface key metrics that drive a doctor's immediate next action (e.g., responding to alerts, checking on patients). Without them, the dashboard has no value.

**Independent Test**: Can be tested by loading the dashboard page and verifying that three labeled cards appear with non-negative integer values that match the current system state. Delivers standalone value as a read-only operational status display.

**Acceptance Scenarios**:

1. **Given** a doctor is logged in and has patients registered in the system, **When** they navigate to the dashboard, **Then** three summary cards are displayed — "Total Patients", "Active Devices", and "Alerts" — each showing the correct current count.

2. **Given** a doctor is logged in and no alerts exist, **When** they view the dashboard, **Then** the Alerts card displays "0" (not blank or an error).

3. **Given** a doctor is logged in and no devices are currently connected, **When** they view the dashboard, **Then** the Active Devices card displays "0".

4. **Given** the backend is unavailable, **When** the doctor loads the dashboard, **Then** summary cards show a clear error or placeholder state rather than incorrect data.

---

### User Story 2 - View 7-Day Tremor Trend (Priority: P2)

A doctor views a line chart on the dashboard showing aggregated tremor activity over the past 7 days across all their patients. This allows the doctor to spot population-level trends — e.g., a spike in tremor severity over recent days — without needing to inspect each patient individually.

**Why this priority**: The trend chart provides insight into longitudinal patterns but requires summary cards to be in place first to contextualize the numbers. It delivers strategic value rather than immediate operational value.

**Independent Test**: Can be tested by loading the dashboard with at least one day of historical tremor data and verifying that a line chart renders with up to 7 data points, one per day, showing aggregated tremor values.

**Acceptance Scenarios**:

1. **Given** tremor data exists for the past 7 days, **When** the doctor views the dashboard, **Then** a line chart is displayed with exactly 7 data points, one per calendar day, showing aggregated tremor intensity for that day.

2. **Given** tremor data exists for only 3 of the past 7 days, **When** the doctor views the dashboard, **Then** the chart renders the 3 days with data; days without data are shown as gaps or zero values (not skipped entirely from the x-axis).

3. **Given** no tremor data exists for any of the past 7 days, **When** the doctor views the dashboard, **Then** the chart renders an empty state with an informative message (e.g., "No tremor data available").

4. **Given** the analytics endpoint is unavailable, **When** the doctor loads the dashboard, **Then** the chart area shows a clear error state rather than a blank or broken chart.

---

### Edge Cases

- What happens when the doctor has zero patients registered?
- What happens when the analytics endpoint returns partial data (some days missing)?
- What happens when alert count exceeds a large number (e.g., 9999+)?
- How does the dashboard behave when the session token expires during data load?
- What if the 7-day window spans a month boundary (e.g., last 3 days of January + first 4 days of February)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The dashboard MUST display a summary card labeled "Total Patients" showing the total count of all registered patients visible to the logged-in doctor.
- **FR-002**: The dashboard MUST display a summary card labeled "Active Devices" showing the count of currently connected/active wearable devices.
- **FR-003**: The dashboard MUST display a summary card labeled "Alerts" showing the count of outstanding (unacknowledged) alerts.
- **FR-004**: All three summary cards MUST populate their values by fetching data from the analytics stats endpoint when the page loads.
- **FR-005**: The dashboard MUST display a line chart showing aggregated tremor activity for each of the past 7 calendar days.
- **FR-006**: The trend chart data MUST be fetched from the `/api/analytics/` stats endpoint.
- **FR-007**: The trend chart x-axis MUST label each point with its calendar date.
- **FR-008**: The dashboard MUST display a loading state while data is being fetched for both the summary cards and the trend chart.
- **FR-009**: The dashboard MUST display an error state for any section where data fetch fails, without breaking the rest of the page.
- **FR-010**: Only authenticated doctors MUST be able to access the dashboard; unauthenticated users are redirected to login.

### Key Entities

- **Summary Stat**: A labeled numeric metric representing the current state of the system (e.g., patient count, active device count, alert count). Sourced from the analytics stats endpoint.
- **Tremor Trend Data Point**: A single day's aggregated tremor value, identified by calendar date and a numeric intensity measure. Comprises the 7-point dataset for the trend chart.
- **Alert**: An event requiring doctor attention, counted in the Alerts summary card. An alert is "outstanding" until acknowledged.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All three summary cards and the trend chart are visible on a standard desktop screen without horizontal scrolling.
- **SC-002**: The dashboard fully loads and renders all summary cards and the trend chart within 3 seconds on a standard broadband connection.
- **SC-003**: Summary card values match the actual current system counts with 100% accuracy (verified against known test data).
- **SC-004**: The trend chart displays the correct number of data points for available days (verified against known historical test data).
- **SC-005**: When any data source is unavailable, the affected section shows an error indicator within 5 seconds, while unaffected sections continue to render normally.
- **SC-006**: Doctors can identify the purpose of each dashboard section (patients, devices, alerts, 7-day tremor trend) without additional explanation or training.

## Assumptions

- The `/api/analytics/` stats endpoint returns all data needed for both summary cards (patient count, active device count, alert count) and the 7-day tremor trend in a single or related set of responses.
- "Active devices" means devices that have sent data within a recent time window — the exact threshold is defined by the backend.
- "Alerts" refers to system-generated clinical events (e.g., high tremor severity) that are unacknowledged by the doctor.
- The dashboard is a read-only view — no editing, acknowledging, or interaction beyond page navigation is in scope for this feature.
- A doctor sees only their own patients' data, not all patients system-wide.
- The 7-day window covers the 7 most recent calendar days, ending on today's date.
- Tremor trend values are pre-aggregated by the backend; the frontend only displays them, it does not compute them.
