# Feature Specification: Patient Overview Grid

**Feature Branch**: `045-patient-overview-grid`  
**Created**: 2026-06-14  
**Status**: Draft  
**Input**: User description: "4.1 Patient Overview Grid Replace the removed chart section with a Patient Overview Grid component. 4.2 Render patient avatar (photo or initials fallback), full name, and online/offline device status badge per row. 4.3 Add View Profile and Live Monitor quick-action buttons on each patient card, routing to their respective pages. 4.4 Create GET /api/dashboard/patients-overview/ returning the doctor's patient list with full_name, avatar_url, device_online boolean. 4.5 Derive device_online from the latest device telemetry timestamp (last seen < 60 s = online)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Patient Overview Grid with Live Device Status (Priority: P1)

A doctor opens their dashboard and, in place of the previously removed trend chart, sees a grid of all their assigned patients. Each entry shows a patient photo (or initials if no photo is on file), the patient's full name, and a clear online/offline badge indicating whether the patient's wearable device is actively transmitting data right now. This gives the doctor an immediate at-a-glance status of their entire patient cohort without navigating away.

**Why this priority**: Core situational awareness. The chart removal left an empty space; restoring utility there is an MVP requirement. Real-time device connectivity status lets doctors know immediately whether their patients' gloves are active and data is flowing — a clinical safety concern.

**Independent Test**: A doctor with 3 assigned patients (one with a device that transmitted in the last 60 seconds, one with a device last seen 10 minutes ago, one with no device) loads the dashboard. The grid shows all 3 patient cards: the first shows an "Online" badge, the second shows "Offline", the third shows "Offline". If a patient has no avatar on file, the card shows their initials instead of a broken image.

**Acceptance Scenarios**:

1. **Given** a doctor is logged in and has patients assigned, **When** they view the dashboard, **Then** a grid of patient cards appears in the area where the tremor trend chart previously was, one card per patient.
2. **Given** a patient has an avatar photo on file, **When** their card is rendered, **Then** the photo is displayed as a circular avatar.
3. **Given** a patient has no avatar photo on file, **When** their card is rendered, **Then** their initials (derived from their full name) are displayed in the avatar area.
4. **Given** a patient's device transmitted telemetry within the last 60 seconds, **When** the card is rendered, **Then** an "Online" status badge is shown in a visually distinct color.
5. **Given** a patient's device last transmitted more than 60 seconds ago (or has no device), **When** the card is rendered, **Then** an "Offline" status badge is shown.
6. **Given** a doctor has no assigned patients, **When** they view the grid section, **Then** an empty-state message is displayed instead of a blank area.

---

### User Story 2 - Quick Navigation to Patient Detail Pages (Priority: P2)

From each patient card in the grid, the doctor can click either "View Profile" to go to the patient's full medical profile page, or "Live Monitor" to jump directly into the real-time monitoring view for that patient. These shortcuts reduce the number of clicks needed to reach the most common destinations from the dashboard.

**Why this priority**: High-frequency navigation path. Doctors using the dashboard frequently want to drill into a specific patient; surface-level shortcuts eliminate a navigation step and reduce cognitive load.

**Independent Test**: A doctor clicks "View Profile" on a patient card — the app navigates to that patient's profile page. The doctor clicks "Live Monitor" on another patient card — the app navigates to that patient's live monitoring page. Both buttons are visible on every patient card without scrolling.

**Acceptance Scenarios**:

1. **Given** a patient card is displayed in the grid, **When** the doctor clicks "View Profile", **Then** the app navigates to that patient's profile detail page.
2. **Given** a patient card is displayed in the grid, **When** the doctor clicks "Live Monitor", **Then** the app navigates to that patient's live monitoring page.
3. **Given** any patient card, **When** the page loads, **Then** both "View Profile" and "Live Monitor" buttons are visible and accessible without scrolling or hovering.

---

### Edge Cases

- What happens when the doctor has no assigned patients? → Show an empty-state message in the grid area; never show a blank space or error.
- What happens when a patient's avatar URL is empty or fails to load? → Fall back to displaying the patient's initials in the avatar placeholder — no broken image icons.
- What happens when a patient has no device assigned? → Show an "Offline" badge (no device means no active telemetry).
- What happens when the patient list endpoint fails to respond? → Show a non-blocking error message in the grid section; the summary cards above remain functional.
- What happens when a patient's name consists of only one word? → Use the first letter of that single name as the initials fallback.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST display a grid of patient cards on the doctor's dashboard, filling the space previously occupied by the removed trend chart.
- **FR-002**: System MUST show each patient's avatar photo when one is available; when no photo is on file, display initials derived from the patient's full name.
- **FR-003**: System MUST display the patient's full name on each card.
- **FR-004**: System MUST display a real-time online/offline status badge on each card, reflecting whether the patient's device transmitted data within the last 60 seconds.
- **FR-005**: System MUST provide a "View Profile" action on each card navigating to the patient's profile detail page.
- **FR-006**: System MUST provide a "Live Monitor" action on each card navigating to the patient's live monitoring page.
- **FR-007**: System MUST scope the patient list to only the patients assigned to the currently logged-in doctor.
- **FR-008**: System MUST display an empty-state message when the doctor has no assigned patients.
- **FR-009**: System MUST show a non-blocking error state in the grid area when patient data cannot be retrieved, without breaking the rest of the dashboard.

### Key Entities

- **Patient**: A person under medical care, identified by full name and optional avatar photo URL.
- **Device**: A wearable glove assigned to a patient; its online status is derived from whether its latest telemetry was received within the last 60 seconds.
- **Doctor–Patient Assignment**: The relationship scoping which patients a given doctor can see and manage.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All assigned patients for a doctor appear in the grid within 2 seconds of the dashboard loading under normal network conditions.
- **SC-002**: The online/offline badge accurately reflects each device's connectivity state at the time the page is loaded, with "Online" shown only for devices whose last telemetry was within 60 seconds.
- **SC-003**: A doctor can navigate from the dashboard grid to a specific patient's profile or live monitoring page in exactly 1 click.
- **SC-004**: Initials placeholders appear in 100% of cases where a patient has no avatar photo — no broken image icons ever appear.
- **SC-005**: The empty-state message appears when the doctor has zero assigned patients, so the grid area is never visually blank.

## Assumptions

- Avatar images are stored as URLs (absolute or relative) on the patient record; the system does not need to generate or upload photos as part of this feature.
- Patient initials are derived from the first letter of each space-delimited word in the full name (e.g., "Ahmed Karim Nour" → "AK" using first two initials).
- "View Profile" and "Live Monitor" destination pages already exist as named routes in the application; this feature only adds navigation links to them.
- The grid does not auto-refresh in real time; device status reflects the state at page load. Live polling or WebSocket updates are out of scope.
- The doctor role restriction is already enforced at the authentication layer; the endpoint inherits that restriction.
- Grid card order defaults to alphabetical by patient full name; no sorting or filtering controls are in scope for this feature.
