# Feature Specification: Live Tremor Monitor Page

**Feature Branch**: `034-live-tremor-monitor`
**Created**: 2026-02-20
**Status**: Draft
**Input**: User description: "N-4.2.3    Live Tremor Monitor Page    WebSocket connection to ws://localhost:8000/ws/tremor/{patient_id}/. Real-time amplitude line chart (rolling 60s). FFT spectrum bar chart. Severity indicator (green/yellow/red). Shows 6-axis raw values."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Live Connection & Amplitude Chart (Priority: P1)

A doctor navigates to the live monitor page for one of their patients. The page immediately begins establishing a live data connection and, once connected, displays a continuously updating line chart showing the patient's tremor amplitude over a rolling 60-second time window. As the session progresses, older data scrolls off the left edge and new readings appear on the right, giving the doctor an instant visual sense of tremor intensity over time. A connection status indicator clearly shows whether data is currently flowing.

**Why this priority**: This is the foundational value of the page. Without a live connection and the amplitude chart, none of the other visualizations are possible. A doctor monitoring a patient in real time needs this core view first and foremost.

**Independent Test**: Can be tested by simulating a live data stream and verifying the chart scrolls in real time, old data drops off at the 60-second boundary, and the connection status indicator accurately reflects the link state.

**Acceptance Scenarios**:

1. **Given** a doctor is on a patient's detail page, **When** they open the live monitor, **Then** the page establishes a connection and the amplitude chart begins displaying incoming data within 3 seconds.
2. **Given** the live monitor is running, **When** 60 seconds of data have accumulated, **Then** the chart begins scrolling so the oldest point drops off as each new reading arrives.
3. **Given** the live monitor is connected, **When** the connection is interrupted, **Then** the status indicator changes to "Disconnected" and the chart freezes on the last received data.
4. **Given** the live monitor shows "Disconnected", **When** the connection is automatically restored, **Then** the status changes to "Connected" and the chart resumes updating.
5. **Given** a doctor navigates away from the monitor page, **When** they return, **Then** the connection is cleanly re-established without stale data from the previous session.

---

### User Story 2 - FFT Frequency Spectrum Chart (Priority: P2)

A doctor viewing the live monitor can also see a bar chart showing the frequency spectrum (FFT) of the current tremor signal. This chart reveals which frequencies dominate the patient's tremor pattern — essential clinical information since Parkinson's tremor typically falls in the 4–6 Hz range while other tremor types occupy different ranges.

**Why this priority**: The FFT spectrum provides clinical depth beyond raw amplitude. Doctors need it to differentiate tremor types and assess treatment response, but the page still delivers value with just the amplitude chart (P1), making this a meaningful but non-blocking enhancement.

**Independent Test**: Can be tested by injecting a mock data stream with known frequency content and verifying the bar chart correctly highlights the dominant frequency bands.

**Acceptance Scenarios**:

1. **Given** the live monitor is connected and receiving data, **When** the FFT panel renders, **Then** a bar chart displays frequency bins along the horizontal axis and relative power on the vertical axis.
2. **Given** a patient's tremor is concentrated in a specific frequency range, **When** the chart updates, **Then** the bars at those frequencies are visibly taller than others.
3. **Given** the connection is lost, **When** the FFT panel renders, **Then** it shows the last known spectrum with a visual indication that it is not updating.

---

### User Story 3 - Severity Indicator (Priority: P3)

Alongside the charts, the doctor sees a prominent color-coded severity indicator that reflects the patient's current tremor classification: green for mild, yellow for moderate, and red for severe. This at-a-glance signal allows the doctor to assess the patient's condition without interpreting the raw charts, and it updates in real time as each new classification arrives.

**Why this priority**: The severity indicator is a high-level summary that saves the doctor cognitive effort. The underlying charts (P1, P2) still provide full diagnostic value without it, but the indicator significantly improves the speed of clinical assessment.

**Independent Test**: Can be tested by sending mock data with different severity levels and confirming the indicator color and label change correctly for each level.

**Acceptance Scenarios**:

1. **Given** the live monitor is connected, **When** incoming data carries a "mild" severity classification, **Then** the severity indicator displays green with the label "Mild".
2. **Given** the indicator is green, **When** a "moderate" classification arrives, **Then** the indicator changes to yellow with the label "Moderate" without a page refresh.
3. **Given** the indicator is yellow or green, **When** a "severe" classification arrives, **Then** the indicator changes to red with the label "Severe".
4. **Given** the connection is lost, **When** the indicator is displayed, **Then** it shows a neutral "No Data" state rather than a potentially misleading severity color.

---

### User Story 4 - 6-Axis Raw Sensor Values Panel (Priority: P4)

A doctor can view a panel showing the current raw readings from all six sensor axes: three for linear acceleration (X, Y, Z) and three for rotational velocity (X, Y, Z). Each value updates continuously with the live stream, giving the doctor or a researcher precise numerical insight into the glove's sensor output.

**Why this priority**: Raw sensor values are diagnostic detail useful for technical review and troubleshooting. They add transparency to the data pipeline, but the core clinical monitoring value is fully delivered by P1–P3 without them.

**Independent Test**: Can be tested by injecting mock sensor messages with known axis values and verifying each of the six displayed numbers matches the incoming data.

**Acceptance Scenarios**:

1. **Given** the live monitor is connected, **When** a sensor reading arrives, **Then** all six axis values (Acc X, Acc Y, Acc Z, Gyro X, Gyro Y, Gyro Z) are displayed and reflect the latest received values.
2. **Given** the values panel is visible, **When** new readings arrive in rapid succession, **Then** the displayed values update smoothly without flickering or layout shifting.
3. **Given** the connection is lost, **When** the panel is displayed, **Then** the values show the last received reading with a visual indication that they are not live.

---

### Edge Cases

- What happens when fewer than 60 seconds of data have been received? The chart displays the available data anchored at the left edge, expanding rightward until the 60-second window is full.
- What happens when the patient is not wearing or has not activated the glove? The page shows a "No active data stream" state with a prompt to check the device, rather than a blank chart.
- What happens when a doctor attempts to open the monitor for a patient they are not assigned to? Access is denied and the doctor is redirected with a permission error message.
- What happens if the data stream sends readings faster than the chart can render? The chart throttles rendering to a fixed refresh rate, buffering the most recent values between frames.
- What happens if a sensor axis value is missing from a message (partial data)? The missing axis shows its last known value marked with a stale indicator rather than going blank.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Doctors MUST be able to open a live monitor page for any patient assigned to them.
- **FR-002**: The page MUST establish a real-time data connection to the live feed for the specified patient immediately upon load.
- **FR-003**: The page MUST display a connection status indicator with at least three states: Connecting, Connected, and Disconnected.
- **FR-004**: The page MUST automatically attempt to reconnect when the connection is dropped, without requiring a manual page refresh.
- **FR-005**: The amplitude line chart MUST display a rolling 60-second window of tremor amplitude, scrolling continuously as new data arrives.
- **FR-006**: The FFT spectrum bar chart MUST display the frequency breakdown of the current tremor signal, updating with each new data message.
- **FR-007**: The severity indicator MUST display the current tremor severity classification using green (mild), yellow (moderate), and red (severe) color coding.
- **FR-008**: The severity indicator MUST update in real time with each new severity value received from the live feed.
- **FR-009**: The raw sensor panel MUST display all six axis readings (3 acceleration + 3 rotation) and update them with each incoming message.
- **FR-010**: When the connection is lost, all live-updating elements MUST visually indicate that they are showing stale data.
- **FR-011**: When the patient is not actively streaming data, the page MUST show a clear "No active data stream" state instead of empty charts.
- **FR-012**: Access to the live monitor MUST be restricted to doctors who are assigned to the patient; unauthorized access MUST be rejected.
- **FR-013**: When navigating away from the monitor page, the live connection MUST be cleanly closed to avoid resource leaks.

### Key Entities

- **Live Sensor Message**: A single real-time data packet received from the glove, containing a timestamp, tremor amplitude value, FFT frequency power array, severity classification, and six raw axis readings.
- **Tremor Amplitude**: A single numeric value representing the overall intensity of detected tremor at a point in time.
- **FFT Spectrum**: An array of power values indexed by frequency bin, representing the frequency distribution of the tremor signal.
- **Severity Classification**: A discrete level (mild / moderate / severe) assigned to the current tremor state, derived from the processed sensor data.
- **Sensor Axis Reading**: A numeric value for one of the six measurement axes (Acc-X, Acc-Y, Acc-Z, Gyro-X, Gyro-Y, Gyro-Z).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The live monitor begins displaying incoming data within 3 seconds of the page loading for a patient with an active glove session.
- **SC-002**: The amplitude chart updates at least 10 times per second when data is flowing, making the visualization feel continuous and live.
- **SC-003**: The severity indicator reflects each new classification within 500 milliseconds of the message being received.
- **SC-004**: The 6-axis values panel refreshes at least 10 times per second when data is streaming.
- **SC-005**: When the connection drops, the page automatically reconnects and resumes data display within 5 seconds, without any manual action from the doctor.
- **SC-006**: Doctors can identify the patient's current severity level at a glance (without reading a chart) in under 2 seconds of viewing the page.
- **SC-007**: The "No active data stream" state is clearly distinguishable from a connected-but-zero-tremor state, preventing false reassurance.

## Assumptions

- The live data feed sends messages at approximately 10–30 Hz (matching the hardware glove's sampling rate); the UI adapts to whatever rate it receives.
- Each incoming message includes all four data types (amplitude, FFT array, severity, 6-axis values) together; partial messages may occur and are handled gracefully.
- The rolling 60-second window is time-based (using message timestamps), not message-count-based.
- The severity classification has exactly three levels: mild, moderate, and severe; a null/missing severity maps to a "No Data" state.
- Access control follows the same doctor-patient assignment model already in place for the patient list and detail pages.
- The live monitor is a read-only page; no actions (e.g., triggering alerts, saving sessions) are in scope for this feature.
- The glove device connects to the backend independently; the frontend only consumes data from the live feed and does not manage device pairing or connection.
