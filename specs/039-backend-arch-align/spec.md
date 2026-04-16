# Feature Specification: Backend Architecture Alignment

**Feature Branch**: `039-backend-arch-align`  
**Created**: 2026-04-12  
**Status**: Draft  
**Input**: User description: "Update the root backend architecture to align with the new TremoAI constitution."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Secure the ML Inference API (Priority: P1)

A doctor or admin submits a tremor prediction request to the inference endpoint. The system must enforce that only users with the `doctor` or `admin` role may trigger predictions — any authenticated user with a different role (or an unauthenticated caller) must be rejected before inference runs.

**Why this priority**: The inference endpoint drives clinical decision-making. Allowing any authenticated user to trigger predictions is a security gap that exposes model outputs to unauthorized actors and violates the platform's role-based access model.

**Independent Test**: Can be tested by sending POST requests to `/api/inference/` with tokens belonging to a `doctor`, an `admin`, a non-clinical user, and an unauthenticated caller — verifying 200, 200, 403, and 401 responses respectively, without needing any other story implemented.

**Acceptance Scenarios**:

1. **Given** an authenticated user with role `doctor`, **When** they POST valid sensor data to `/api/inference/`, **Then** the system returns a 200 response with a prediction result.
2. **Given** an authenticated user with role `admin`, **When** they POST valid sensor data to `/api/inference/`, **Then** the system returns a 200 response with a prediction result.
3. **Given** an authenticated user whose role is neither `doctor` nor `admin`, **When** they POST to `/api/inference/`, **Then** the system returns 403 Forbidden with a clear error message before any model computation occurs.
4. **Given** an unauthenticated caller, **When** they POST to `/api/inference/`, **Then** the system returns 401 Unauthorized.

---

### User Story 2 - Centralize Hardware Config and Logging (Priority: P1)

A developer or operator managing the backend needs all MQTT broker connection parameters sourced from environment variables via the central settings file, and needs structured log channels for the `inference`, `cmg`, and `realtime` apps so that prediction events and hardware commands appear in identifiable log streams.

**Why this priority**: Hardcoded or scattered configuration is a deployment and security risk. Without dedicated loggers for hardware-critical apps, prediction and command activity is invisible during incidents, making debugging hardware misbehaviour impractical.

**Independent Test**: Can be tested by: (a) changing `.env` MQTT variables and confirming the broker address changes at startup without touching code, and (b) triggering any inference call or CMG command and confirming a log line appears under the `inference`, `cmg`, or `realtime` logger name in the log output.

**Acceptance Scenarios**:

1. **Given** an `.env` file with `MQTT_BROKER_URL`, `MQTT_USERNAME`, and `MQTT_PASSWORD` defined, **When** the backend starts, **Then** those values are loaded from settings and used for the MQTT connection — no credentials are hardcoded.
2. **Given** the backend is running with the updated logging configuration, **When** an inference prediction is executed, **Then** a log entry is produced under the `inference` logger name.
3. **Given** the backend is running, **When** a CMG command is published, **Then** a log entry is produced under the `cmg` logger name.
4. **Given** the backend is running, **When** a WebSocket or MQTT realtime event is processed, **Then** a log entry is produced under the `realtime` logger name.
5. **Given** the LOGGING dictionary in settings, **When** a developer inspects it, **Then** `inference`, `cmg`, and `realtime` each appear as named loggers routing to at least the console and file handlers.

---

### User Story 3 - Establish the Bidirectional MQTT Bridge (Priority: P2)

A doctor triggers a suppression action from the platform. The backend must be able to publish CMG counter-torque commands and servo PID tuning parameters back to the ESP32 glove hardware over MQTT, in addition to receiving telemetry. The foundational publish functions must be confirmed present, properly wired to settings-based config, and accessible from within the `realtime` app layer.

**Why this priority**: The platform's therapeutic value depends on closing the control loop: receive tremor data → classify → send suppression command. Without verified publish capability, the platform is read-only and cannot suppress tremors. This is P2 because the subscribe path already functions; this story solidifies and verifies the outbound half.

**Independent Test**: Can be tested by calling the publish functions directly in a Django shell with a test device serial number while a local MQTT broker is running — verifying the message appears on the expected topic without a real glove present.

**Acceptance Scenarios**:

1. **Given** a connected MQTT broker and a known device serial number, **When** a CMG counter-torque command is published, **Then** the message appears on topic `devices/{serial}/cmg_command` with the correct payload.
2. **Given** a connected MQTT broker, **When** servo PID tuning parameters are published, **Then** the message appears on topic `devices/{serial}/pid_config` with the correct payload structure.
3. **Given** the MQTT broker is disconnected, **When** a publish is attempted, **Then** the function returns a failure indicator and logs a warning — it does not raise an unhandled exception or crash the request thread.
4. **Given** the publish functions exist in the `realtime` app, **When** a developer imports them, **Then** they are importable without circular dependency errors and have clear docstrings describing the expected payload format.

---

### Edge Cases

- What happens when the MQTT broker is unreachable at backend startup — does the server fail to start or start in a degraded state?
- What happens when a publish is attempted while broker reconnection backoff is in progress?
- What if `MQTT_BROKER_URL` is absent from `.env` — does the backend fail loudly or silently use an empty default?
- What happens when an inference log database write fails after a successful prediction — does the prediction response still return to the client?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The inference endpoint MUST reject requests from any caller whose role is not `doctor` or `admin`, returning 403 Forbidden before any model computation occurs.
- **FR-002**: The inference endpoint MUST reject unauthenticated requests with 401 Unauthorized.
- **FR-003**: The backend MUST read MQTT broker URL, username, and password exclusively from environment variables; no credentials may be hardcoded in source files.
- **FR-004**: The central settings file MUST expose MQTT broker configuration as named settings entries so application code can reference them via the settings module rather than calling the env-loader directly in multiple places.
- **FR-005**: The LOGGING configuration MUST include dedicated named loggers for the `inference`, `cmg`, and `realtime` apps, each routing to at least the console handler.
- **FR-006**: The `realtime` app MQTT client MUST expose publish functions for CMG counter-torque commands and servo PID tuning parameters.
- **FR-007**: Publish functions MUST return a boolean success indicator and MUST NOT raise unhandled exceptions when the broker is disconnected.
- **FR-008**: Publish functions MUST log every outbound command at INFO level under the appropriate logger.

### Key Entities

- **Role**: Enumerated user attribute (`doctor`, `admin`) used to gate access to clinical and hardware-control operations.
- **MQTT Command**: An outbound message sent from backend to ESP32, carrying a CMG counter-torque instruction or servo PID configuration payload.
- **Logger**: A named logging channel scoped to an application domain (`inference`, `cmg`, `realtime`), enabling targeted log filtering and routing.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of inference requests from authenticated users without `doctor` or `admin` role are rejected with 403 before any model is loaded or run.
- **SC-002**: 100% of unauthenticated inference requests are rejected with 401.
- **SC-003**: All MQTT broker connection parameters are sourced from environment variables — a code search finds zero hardcoded broker URLs, usernames, or passwords.
- **SC-004**: Every inference prediction and every published hardware command produces at least one log line identifiable by its named logger (`inference`, `cmg`, or `realtime`) within the same request or event cycle.
- **SC-005**: CMG and servo PID publish functions complete without raising an exception when the broker is offline and return `False` to the caller within the existing reconnect timeout window.

## Assumptions

- The `IsDoctorOrAdmin` permission class already exists in `backend/authentication/permissions.py` and only needs to be applied to `InferenceAPIView` — no new permission class needs to be written.
- The `realtime/mqtt_client.py` already contains `publish_cmg_command`, `publish_servo_command`, `publish_servo_config`, and `publish_pid_config` functions; Story 3 is about verifying, documenting, and wiring them to settings-based configuration rather than writing them from scratch.
- `MQTT_BROKER_URL`, `MQTT_USERNAME`, and `MQTT_PASSWORD` are the canonical `.env` variable names already used by `mqtt_client.py` via direct env-loader calls; settings.py will centralize these.
- No new Django apps are created for this feature; changes are confined to existing files in `backend/inference/`, `backend/realtime/`, and `backend/tremoai_backend/`.
- A default fallback value for `MQTT_BROKER_URL` (e.g., `mqtt://localhost:1883`) is acceptable for local development so the backend does not crash when the variable is absent.
