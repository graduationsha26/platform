# Feature Specification: Real-Time Pipeline

**Feature Branch**: `002-realtime-pipeline`
**Created**: 2026-02-15
**Status**: Draft
**Input**: User description: "3.3 Real-Time Pipeline - 3.3.1 MQTT Broker Integration (Django subscribes to MQTT broker, stores incoming sensor data in PostgreSQL) + 3.3.2 WebSocket Consumer (Django Channels: push live tremor data + ML prediction to connected frontend clients)"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automatic Data Collection from Glove Devices (Priority: P1)

The platform continuously receives sensor data from TremoAI glove devices as patients wear them, validates the incoming measurements, and stores them in the central database for historical analysis and live monitoring. This enables the platform to act as a central data repository for all patient tremor measurements collected during daily activities or clinical sessions.

**Why this priority**: This is the foundational capability - without reliable data ingestion from the glove devices, the entire monitoring platform cannot function. All downstream features (analytics, alerts, AI predictions) depend on this data pipeline.

**Independent Test**: Can be fully tested by simulating a data transmission from a glove device and verifying that:
1. The message is received by the platform
2. The sensor data is validated and stored in the database
3. The stored data matches the original measurements
4. The system can handle continuous data streams from multiple devices simultaneously

**Acceptance Scenarios**:

1. **Given** a glove device is paired to a patient, **When** the device transmits tremor sensor data, **Then** the platform receives the data and stores a new biometric session record with all sensor readings
2. **Given** the data collection service is running, **When** an unpaired device transmits sensor data, **Then** the system logs a warning and does not store the data (invalid device)
3. **Given** the data collection service is running, **When** a device transmits malformed data (missing required fields), **Then** the system logs an error and does not store the data
4. **Given** multiple devices are transmitting data simultaneously, **When** measurements arrive from different devices, **Then** the system correctly associates each transmission with the corresponding device and patient
5. **Given** the database is temporarily unavailable, **When** sensor data arrives from a device, **Then** the system buffers the data temporarily and attempts to reconnect without losing measurements

---

### User Story 2 - Live Monitoring of Patient Tremor Data (Priority: P2)

Doctors and patients can view real-time tremor data updates on their screens as they arrive from the glove device. This provides immediate visibility into current patient status and enables live monitoring during consultations or patient self-monitoring sessions. The interface updates automatically within seconds of the glove capturing new measurements.

**Why this priority**: Real-time monitoring is a core value proposition of the TremoAI platform. Doctors need to see live data during patient sessions, and patients benefit from immediate feedback. This story delivers immediate clinical value once data collection (P1) is working.

**Independent Test**: Can be fully tested by:
1. Authenticating a doctor user and opening the live monitoring view for a patient
2. Simulating a data transmission from the patient's glove device
3. Verifying that the monitoring interface receives and displays the tremor data in real-time (within 500ms)
4. Confirming that only authorized users (assigned doctors or the patient) can view a patient's live data stream

**Acceptance Scenarios**:

1. **Given** a doctor is viewing a patient's profile, **When** the doctor opens the live monitoring page, **Then** the interface displays "Connected - waiting for data" and is ready to receive updates
2. **Given** the live monitoring view is open for patient P, **When** patient P's glove device transmits new sensor data, **Then** the interface displays the tremor data within 500ms
3. **Given** multiple doctors are monitoring the same patient, **When** new sensor data arrives, **Then** all connected viewers see the same data update simultaneously
4. **Given** a doctor is viewing patient P1's live data, **When** patient P2's device transmits data, **Then** the doctor does not see P2's data (proper isolation)
5. **Given** the live monitoring view is open, **When** the network connection is interrupted, **Then** the interface automatically attempts to reconnect and resumes displaying data
6. **Given** a user without access rights (unauthorized doctor or unrelated patient), **When** they attempt to view a patient's live data stream, **Then** the request is rejected with an "Access Denied" error

---

### User Story 3 - AI-Powered Tremor Severity Insights (Priority: P3)

As tremor data streams in real-time, the system analyzes measurements using trained AI models to predict tremor severity classifications and displays these insights alongside the raw sensor data. This provides actionable clinical interpretation to doctors and patients, helping them understand the significance of the measurements and make informed treatment decisions.

**Why this priority**: AI predictions enhance the value of raw sensor data by providing clinical interpretation. However, the core monitoring functionality (P1 + P2) is valuable even without AI insights. This is an enhancement that adds intelligence but is not blocking for MVP.

**Independent Test**: Can be fully tested by:
1. Opening the live monitoring view for a patient
2. Transmitting sensor data from a device that triggers AI analysis
3. Verifying that the monitoring interface displays both the raw sensor data AND the AI prediction (e.g., severity: "moderate", confidence: 92%)
4. Confirming that the prediction appears within acceptable time (under 200ms additional delay)

**Acceptance Scenarios**:

1. **Given** the live monitoring view is open, **When** new sensor data arrives and triggers AI analysis, **Then** the interface displays both the raw sensor readings and the AI prediction (severity classification, confidence score)
2. **Given** the AI analysis service is available, **When** sensor data is processed, **Then** the prediction is computed within 200ms and does not delay the data display
3. **Given** the AI analysis service is unavailable or fails, **When** sensor data arrives, **Then** the raw data is still displayed, and the prediction field shows "unavailable" or is omitted
4. **Given** sensor data does not meet AI model input requirements (e.g., insufficient data points), **When** the data arrives, **Then** the raw data is displayed without a prediction, and no error is shown to the user
5. **Given** AI predictions are enabled, **When** a doctor views historical session data, **Then** the stored biometric sessions also include the AI predictions that were generated at the time of data collection

---

### Edge Cases

- **What happens when the data collection service cannot reach the message broker?** The system should log connection errors, attempt to reconnect automatically with increasing delays, and alert administrators if the connection cannot be re-established within a defined threshold (e.g., 5 minutes).
- **What happens when a device sends data at very high frequency (>100 Hz)?** The system should handle high-frequency data streams by batching or reducing the transmission rate if necessary to prevent overwhelming the database and live monitoring viewers.
- **What happens when a viewer's device is slow to process live updates?** The system should implement message buffering with a maximum buffer size. If the buffer is exceeded, the oldest messages are dropped, and the viewer is notified of potential data loss.
- **What happens when the database is slow or unresponsive?** Data processing should have a timeout. If database writes take too long, the message should be logged and retried to avoid blocking incoming data streams.
- **What happens when a patient's device is unpaired mid-session?** Incoming data transmissions from the unpaired device should be rejected, and any active viewers should receive a notification that the device is no longer paired and the stream has ended.
- **What happens when a user's session expires during live monitoring?** The live monitoring view should gracefully close the connection with an "Unauthorized" message, and the interface should prompt the user to re-authenticate.
- **What happens when the AI model returns an invalid or unexpected result?** The system should validate AI predictions (e.g., check that severity is one of the expected values) and fallback to omitting the prediction if validation fails, logging the error for investigation.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST continuously listen for data transmissions from registered glove devices and identify the device by its unique serial number
- **FR-002**: System MUST validate that incoming data transmissions contain required fields: device identifier, timestamp, tremor intensity measurements, frequency, and time-series data points
- **FR-003**: System MUST verify that the device sending data is registered in the system and currently paired to a patient before storing the data
- **FR-004**: System MUST store validated sensor data as a new biometric session record with associated patient, device, session start time, duration, and complete sensor readings
- **FR-005**: System MUST log all data collection service events (connections, disconnections, errors) and data validation failures for monitoring and debugging
- **FR-006**: System MUST provide live monitoring interfaces where authenticated users can view real-time tremor data for specific patients
- **FR-007**: System MUST enforce access control on live monitoring views - only doctors assigned to the patient or the patient themselves can view the live data stream
- **FR-008**: System MUST deliver incoming sensor data to all users viewing the corresponding patient's live monitoring interface within 500ms of receiving the transmission
- **FR-009**: System MUST support multiple concurrent viewers per patient (e.g., multiple doctors monitoring the same patient simultaneously)
- **FR-010**: System MUST gracefully handle viewer disconnections and automatically clean up associated resources
- **FR-011**: System MUST analyze incoming sensor data using trained AI models to generate tremor severity predictions
- **FR-012**: System MUST display AI predictions alongside raw sensor data in live monitoring views, showing severity classification (mild/moderate/severe) and confidence score (0-100%)
- **FR-013**: System MUST handle AI analysis failures gracefully - if prediction fails, display the raw sensor data without predictions and log the error
- **FR-014**: System MUST persist AI predictions with the biometric session record for historical analysis and auditing
- **FR-015**: System MUST implement automatic connection recovery - if the data collection service loses connectivity to the message broker, it must reconnect automatically with increasing retry delays (1s, 2s, 4s, 8s, up to 60s)

### Key Entities

- **Data Collection Service**: A background service that maintains a persistent connection to the device messaging infrastructure and processes incoming transmissions. Receives device data, triggers validation, storage, and live broadcast to viewers.
- **Live Monitoring Session**: Represents an active viewing session where a user (doctor or patient) is watching real-time tremor data. Manages the connection lifecycle, enforces authentication and authorization, and delivers updates to the viewer's interface.
- **Broadcast Channel**: The communication mechanism between the data collection service and live monitoring sessions. When data arrives from a device, it is published to the appropriate channel, and all active viewers subscribed to that channel receive the update.
- **AI Analysis Service**: A service that accepts sensor data as input and returns tremor severity predictions with confidence scores. Invoked when new data arrives to provide clinical interpretation alongside raw measurements.
- **Biometric Session** (extended): The existing database entity that stores sensor data from patient sessions. Will be extended to include AI prediction results (severity, confidence) alongside the raw sensor measurements.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The system can reliably receive and store sensor data from at least 10 concurrent glove devices transmitting data at 50Hz without message loss or delays exceeding 1 second
- **SC-002**: Doctors see real-time sensor data updates in their monitoring interface within 500ms of the glove device transmitting the data (measured end-to-end latency)
- **SC-003**: The platform can support at least 50 concurrent live monitoring sessions (multiple doctors monitoring multiple patients) without degradation in update delivery latency
- **SC-004**: AI predictions are computed and displayed alongside raw data with less than 200ms additional latency compared to data-only displays
- **SC-005**: The data collection service maintains 99% uptime (excluding planned maintenance) and automatically recovers from transient connectivity failures within 2 minutes
- **SC-006**: 95% of users successfully establish live monitoring sessions on the first attempt, and sessions can reconnect automatically after network interruptions within 5 seconds
- **SC-007**: The system correctly isolates patient data streams - unauthorized access attempts are rejected, and no data leakage occurs between different patients' streams
- **SC-008**: Doctors report that the live monitoring feature provides actionable real-time insights, with 90% of users successfully using the feature to monitor patient sessions without technical issues

## Assumptions *(mandatory)*

1. **Message Infrastructure Availability**: A message broker infrastructure is already deployed and accessible to both the platform backend and the glove devices. Connection credentials are securely configured.
2. **Device Communication Protocol**: Glove devices transmit sensor data using a standardized message format with defined schema including: device identifier, timestamp, tremor intensity measurements, frequency, and time-series data points.
3. **Real-time Communication Infrastructure**: The platform has the necessary infrastructure to support bidirectional real-time communication between the backend and frontend clients for live data streaming.
4. **AI Model Availability**: Trained AI models are accessible to the backend system and can perform inference on sensor data within 200ms response time.
5. **Authentication**: Live monitoring viewers must provide valid authentication credentials to establish connections. The authentication mechanism reuses the existing platform authentication system.
6. **Database Performance**: The database can handle the write load from real-time sensor data ingestion (estimated at 500-1000 records per minute during active monitoring sessions) without significant performance degradation.
7. **Network Reliability**: The connection between the message broker and backend platform is reasonably stable. Transient network issues are expected and handled via automatic reconnection logic, but persistent network partitions are out of scope.
8. **Frontend Client Capabilities**: Frontend clients have the capability to establish and maintain real-time connections and implement automatic reconnection logic on the client side.
9. **Data Persistence**: Real-time streamed data is also persisted in the database (not ephemeral). Historical data retention policies are defined separately and do not affect the real-time pipeline.
10. **Concurrency Limits**: The system is designed to support up to 50 concurrent glove devices and 100 concurrent live monitoring sessions in the initial deployment. Scaling beyond this requires infrastructure upgrades.

## Out of Scope

- **Message Broker Setup and Management**: Provisioning, configuring, and maintaining the message broker infrastructure is out of scope. The broker is assumed to be pre-existing and managed separately.
- **Frontend Live Monitoring Interface**: Building the user interface components that display live data updates is out of scope for this backend-focused feature. The frontend will be implemented in a separate feature.
- **Historical Data Analytics Dashboard**: While this feature stores data for historical analysis, building analytics dashboards, charts, and reports is out of scope and covered by other features.
- **Advanced AI Features**: Features like model retraining, A/B testing of models, or real-time model updates are out of scope. The feature uses existing pre-trained models.
- **Alerting and Notifications**: Automatically sending alerts (e.g., SMS, email) based on tremor severity thresholds is out of scope. This feature focuses on data streaming, not alerting logic.
- **Glove Device Firmware**: Any changes to the glove device firmware or device-side data processing are out of scope.
- **Multi-Region Deployment**: The feature is designed for a single-region deployment. Geo-distributed infrastructure is out of scope.
- **Video/Audio Streaming**: Only sensor data is streamed. Streaming video or audio from patient sessions is out of scope.

## Dependencies

- **Feature 001 - Core Backend APIs**: This feature depends on the existing Device, Patient, and Biometric Session entities from Feature 001. The real-time pipeline extends these entities and uses them for validation and data storage.
- **Message Broker Infrastructure**: Requires an external message broker to be deployed and configured with appropriate authentication and topic/channel structure for device communication.
- **Real-time Communication Infrastructure**: Requires the platform to support bidirectional real-time communication capabilities between backend and frontend clients.
- **AI Models**: Requires trained AI models to be available in the platform for tremor severity prediction generation.
- **Inter-Process Communication Layer**: Requires a communication mechanism for coordinating between the data collection service and live monitoring sessions.

## Notes

- **Technology Alignment**: This feature fully aligns with the project constitution:
  - Backend: Django + Django Channels (WebSocket)
  - Database: Supabase PostgreSQL (all data stored remotely)
  - Real-time: Django Channels WebSocket (as specified in the constitution)
  - MQTT: Django subscribes to MQTT broker (as specified in the constitution)
  - AI Models: Uses existing scikit-learn (.pkl) and TensorFlow/Keras (.h5) models (as specified in the constitution)

- **Performance Considerations**: Real-time data streaming at 50Hz from multiple devices can generate significant load. The design should prioritize asynchronous processing, efficient database writes (consider batching), and optimized WebSocket message serialization.

- **Security Considerations**: WebSocket connections must be authenticated and authorized. JWT tokens should be validated on every connection attempt. The system must prevent unauthorized users from subscribing to other patients' data streams.

- **Testing Strategy**: This feature requires integration testing with an actual MQTT broker and WebSocket clients. Consider using Docker Compose for local development to spin up an MQTT broker (Mosquitto) and Redis for testing. Unit tests should mock the MQTT client and channel layer.

- **Deployment Notes**: The Django MQTT subscriber should run as a persistent background process (e.g., using Django management command in a supervisor/systemd service, or as a Celery worker). It must start automatically on server boot and restart on failure.
