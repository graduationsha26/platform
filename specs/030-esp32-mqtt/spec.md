# Feature Specification: ESP32 WiFi + MQTT Client

**Feature Branch**: `030-esp32-mqtt`
**Created**: 2026-02-19
**Status**: Draft
**Input**: User description: "1.4.1    1.4 Comm    WiFi + MQTT Client    ESP32 WiFi connection + MQTT publish. Send JSON payload: {device_id, timestamp, aX, aY, aZ, gX, gY, gZ, battery_level}. Publish at 30-50Hz to topic tremo/sensors/{device_id}. QoS 1."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Continuous Sensor Data Streaming (Priority: P1)

When the wearable glove is powered on in range of a known WiFi network, it automatically establishes a network and broker connection, then begins continuously publishing sensor readings — 9-axis motion data and battery level — to the monitoring platform at 30–50 messages per second. The platform backend receives and processes each message in real time, enabling live tremor monitoring on the doctor's dashboard.

**Why this priority**: Without a working publish loop, no other feature (tremor analysis, PID control, visualization) can function. This is the foundation of the entire system.

**Independent Test**: Can be verified by powering on the glove near a WiFi access point and observing that the MQTT broker receives well-formed JSON messages at the expected rate on the correct topic within seconds of boot.

**Acceptance Scenarios**:

1. **Given** the glove is powered on and a known WiFi network is in range, **When** boot completes, **Then** the glove connects to WiFi and the MQTT broker within 15 seconds and begins publishing sensor messages.
2. **Given** the glove is actively publishing, **When** the broker inspects incoming messages on `tremo/sensors/{device_id}`, **Then** each message contains all required fields: `device_id`, `timestamp`, `aX`, `aY`, `aZ`, `gX`, `gY`, `gZ`, `battery_level`.
3. **Given** the glove is actively publishing, **When** the message rate is measured over a 10-second window, **Then** the rate is between 30 and 50 messages per second.
4. **Given** a message is published, **When** the broker receives it, **Then** the `device_id` field matches the unique identifier of the transmitting glove.

---

### User Story 2 - Automatic Reconnection on Network Loss (Priority: P2)

When the WiFi or broker connection drops during an active session (due to interference, broker restart, or brief outage), the glove automatically attempts to reconnect and resumes publishing without requiring patient or caregiver intervention. This ensures clinical sessions are not interrupted by transient network events.

**Why this priority**: Tremor monitoring sessions may last 30–60 minutes. A manual restart requirement during a session is clinically unacceptable. Automatic recovery is essential for reliability.

**Independent Test**: Can be verified by disconnecting the MQTT broker mid-session and reconnecting it; the glove should resume publishing within 10 seconds of broker availability being restored, with no manual action required.

**Acceptance Scenarios**:

1. **Given** the glove is actively publishing, **When** WiFi connectivity is lost, **Then** the glove stops publishing and enters a reconnection loop without crashing or requiring a reboot.
2. **Given** the glove is in reconnection mode after WiFi loss, **When** the WiFi network becomes available again, **Then** the glove reconnects to WiFi and the broker and resumes publishing within 10 seconds.
3. **Given** the glove is connected to WiFi but the MQTT broker is temporarily unavailable, **When** the broker comes back online, **Then** the glove reconnects to the broker and resumes publishing within 10 seconds.
4. **Given** the glove has been reconnecting for more than 60 seconds without success, **When** connectivity is restored, **Then** the glove still recovers automatically without intervention.

---

### User Story 3 - Reliable Message Delivery with QoS 1 (Priority: P3)

Each sensor message is published with at-least-once delivery semantics, so that temporary network hiccups do not cause silent data loss. The broker acknowledges receipt, and the glove retransmits any unacknowledged messages until confirmed. This guarantees data integrity for clinical analysis and PID control downstream.

**Why this priority**: The PID controller and tremor analysis depend on a continuous stream of readings. Silent packet loss could cause incorrect suppression commands or gaps in session records. QoS 1 closes this gap.

**Independent Test**: Can be verified by introducing artificial packet loss on the network (e.g., via a network emulator) and confirming that the broker still receives every published message with no gaps in sequence numbers or timestamps.

**Acceptance Scenarios**:

1. **Given** the glove is publishing at 30–50 Hz, **When** temporary packet loss occurs on the network, **Then** messages lost in transit are retransmitted and eventually received by the broker.
2. **Given** the glove publishes a message, **When** the broker acknowledges receipt, **Then** the glove does not retransmit that message.
3. **Given** the glove publishes at 30–50 Hz over a 60-second window with no network faults, **When** the broker counts received messages, **Then** the count is within 1% of the expected total (no more than 1% message loss).

---

### Edge Cases

- What happens when the configured WiFi SSID is not in range at boot? The glove must not hang indefinitely; it should retry at intervals.
- What happens when WiFi credentials are incorrect? The glove should fail gracefully and signal an error (e.g., LED indicator), not enter an infinite loop.
- What happens when the MQTT broker address is unreachable (DNS failure or wrong host)? The glove should log the failure and retry.
- What happens when the glove's battery is critically low (≤5%)? The message should still carry the accurate `battery_level` value and publishing should continue until the device shuts down.
- What happens when the IMU sensor returns invalid or out-of-range readings? The glove should publish the raw values as received and let the platform apply filtering.
- What happens when the broker's topic ACL rejects the publish? The connection should be retained but publication errors should be logged.
- What happens if the device clock has not synced with a time source? The `timestamp` field should still be populated, using elapsed milliseconds since boot if wall-clock time is unavailable.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The device MUST connect to a configured WiFi network on power-on.
- **FR-002**: The device MUST connect to the MQTT broker after WiFi is established.
- **FR-003**: The device MUST publish sensor messages continuously at a rate between 30 Hz and 50 Hz during normal operation.
- **FR-004**: Each published message MUST be a valid JSON object containing exactly these fields: `device_id`, `timestamp`, `aX`, `aY`, `aZ`, `gX`, `gY`, `gZ`, `battery_level`.
- **FR-005**: The `device_id` field MUST uniquely identify the publishing device and MUST be consistent across all messages from the same glove.
- **FR-006**: The `timestamp` field MUST represent the time the reading was taken, as milliseconds since a reference point (NTP epoch preferred; elapsed-since-boot as fallback).
- **FR-007**: The `aX`, `aY`, `aZ` fields MUST represent 3-axis linear acceleration readings from the IMU sensor.
- **FR-008**: The `gX`, `gY`, `gZ` fields MUST represent 3-axis angular velocity readings from the IMU sensor.
- **FR-009**: The `battery_level` field MUST represent the current battery charge as a percentage (0–100).
- **FR-010**: All messages MUST be published to the topic `tremo/sensors/{device_id}` where `{device_id}` matches the message payload's `device_id`.
- **FR-011**: All messages MUST be published with QoS level 1 (at-least-once delivery).
- **FR-012**: The device MUST automatically reconnect to WiFi when the connection is lost, without requiring a reboot.
- **FR-013**: The device MUST automatically reconnect to the MQTT broker when the broker connection is lost, without requiring a reboot.
- **FR-014**: WiFi credentials (SSID, password) and broker address MUST be stored in device configuration, not hardcoded in the main firmware logic.

### Key Entities

- **Sensor Reading**: A single data point captured from the IMU and battery monitor, containing a device identifier, a timestamp, three-axis acceleration values (aX, aY, aZ), three-axis gyroscope values (gX, gY, gZ), and a battery percentage. Published as a JSON message.
- **Device Identity**: The unique identifier assigned to each wearable glove, used as both the MQTT topic segment and a field in every published message to allow the platform to route and attribute data correctly.
- **MQTT Message**: The network packet carrying a single Sensor Reading, addressed to the device-specific topic, delivered with at-least-once semantics.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The glove begins publishing sensor data within 15 seconds of power-on when WiFi and broker are accessible.
- **SC-002**: The sensor data publication rate is maintained between 30 and 50 messages per second during continuous operation.
- **SC-003**: Under normal network conditions (no packet loss), fewer than 1% of published messages fail to reach the broker over a 60-second window.
- **SC-004**: After a network disruption is resolved, the glove automatically resumes publishing within 10 seconds without any manual intervention.
- **SC-005**: 100% of published messages include all 9 required fields (`device_id`, `timestamp`, `aX`, `aY`, `aZ`, `gX`, `gY`, `gZ`, `battery_level`) with non-null values.
- **SC-006**: The battery level field in published messages is accurate within ±2% of the actual battery charge at the time of measurement.

## Assumptions

- WiFi network credentials (SSID and password) are pre-configured on the device before deployment; there is no over-the-air provisioning in scope for this feature.
- The MQTT broker address and port are also pre-configured on the device.
- The device has a working IMU sensor (3-axis accelerometer + 3-axis gyroscope) and a battery level monitor available.
- NTP synchronization is attempted on startup; if unavailable, the timestamp falls back to milliseconds elapsed since boot.
- The MQTT broker does not require TLS or client-certificate authentication for this feature (authentication may be added in a later feature).
- The `device_id` is a fixed value stored in device configuration (e.g., a hardware-derived serial or a pre-provisioned UUID).
- The 30–50 Hz publish rate is determined by the IMU sampling loop; no sub-sampling or buffering is required beyond what the sensor provides.
