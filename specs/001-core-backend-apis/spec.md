# Feature Specification: Core Backend APIs

**Feature Branch**: `001-core-backend-apis`
**Created**: 2026-02-15
**Status**: Draft
**Input**: User description: "3.1 Auth & Users - User Model + JWT Auth - Extend User with role (patient/doctor). JWT login/register endpoints. 3.2 Core APIs - Patient CRUD API, Biometric Data API, Device Registration API"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - User Registration and Authentication (Priority: P1)

Doctors and patients need to register accounts and log in to access the TremoAI platform. Doctors use the platform to monitor patients, while patients can view their own data. Authentication must distinguish between these two user types.

**Why this priority**: Foundation for all other features. Without authentication, no other user story can function. This is the absolute minimum viable product.

**Independent Test**: Can be fully tested by registering new users (both doctor and patient roles), logging in with credentials, receiving JWT tokens, and verifying role-based access restrictions. Delivers value by securing the platform and enabling user identity management.

**Acceptance Scenarios**:

1. **Given** no existing account, **When** a doctor provides email, password, and role="doctor", **Then** system creates doctor account and returns success confirmation
2. **Given** valid doctor credentials, **When** doctor submits login request, **Then** system returns JWT token containing user ID and role="doctor"
3. **Given** valid patient credentials, **When** patient submits login request, **Then** system returns JWT token containing user ID and role="patient"
4. **Given** invalid credentials, **When** user attempts login, **Then** system returns authentication error without revealing whether email exists
5. **Given** an existing JWT token, **When** user includes token in API request, **Then** system validates token and allows/denies access based on role permissions

---

### User Story 2 - Patient Profile Management (Priority: P2)

Doctors need to create, view, update, and search patient profiles to manage their patient roster. Each patient profile contains basic information and can be assigned to specific doctors for monitoring.

**Why this priority**: Enables doctors to manage their patient base. Required before devices can be paired or data can be collected. This is the second critical piece after authentication.

**Independent Test**: Can be tested by authenticating as a doctor, creating patient records, viewing patient lists, updating patient information, searching for patients by name, and assigning patients to doctors. Delivers value by providing patient management capabilities.

**Acceptance Scenarios**:

1. **Given** authenticated doctor, **When** doctor creates patient with name, date of birth, contact info, **Then** system stores patient record and returns patient ID
2. **Given** authenticated doctor, **When** doctor requests patient list, **Then** system returns all patients assigned to or created by that doctor
3. **Given** authenticated doctor with patient ID, **When** doctor updates patient information, **Then** system saves changes and returns updated record
4. **Given** authenticated doctor, **When** doctor searches patients by name, **Then** system returns matching patient records
5. **Given** authenticated doctor, **When** doctor assigns patient to another doctor, **Then** system creates doctor-patient relationship
6. **Given** authenticated patient, **When** patient views own profile, **Then** system returns only that patient's information
7. **Given** authenticated patient, **When** patient attempts to view other patient data, **Then** system denies access

---

### User Story 3 - Device Registration and Patient Pairing (Priority: P3)

Glove devices must be registered in the system and paired with specific patients before sensor data can be collected. Doctors need to track which devices are online and properly paired.

**Why this priority**: Prerequisite for collecting biometric data. Enables device management and patient-device association. Must come before data collection but after patient management.

**Independent Test**: Can be tested by authenticating as a doctor, registering a glove device, pairing it to an existing patient, and tracking device online/offline status. Delivers value by establishing device inventory and patient-device relationships.

**Acceptance Scenarios**:

1. **Given** authenticated doctor with device serial number, **When** doctor registers new glove device, **Then** system creates device record with status="offline"
2. **Given** authenticated doctor with device ID and patient ID, **When** doctor pairs device to patient, **Then** system creates device-patient association
3. **Given** registered device, **When** device connects to platform, **Then** system updates device status to "online" with last-seen timestamp
4. **Given** online device, **When** device disconnects, **Then** system updates device status to "offline" with last-seen timestamp
5. **Given** authenticated doctor, **When** doctor views patient profile, **Then** system displays paired device information and online status
6. **Given** device already paired to patient, **When** doctor attempts to pair same device to different patient, **Then** system prevents pairing and returns error

---

### User Story 4 - Biometric Data Storage and Retrieval (Priority: P4)

The system must store sensor data from glove devices in sessions and allow doctors to retrieve this data for analysis. Data should be filterable by date ranges and provide basic aggregation metrics.

**Why this priority**: Core functionality for tremor monitoring. Enables doctors to analyze patient tremor patterns over time. Depends on device registration but provides the main clinical value.

**Independent Test**: Can be tested by storing sensor session data for a paired device-patient combination, retrieving sessions by date range, and computing basic aggregations (average tremor intensity, session duration). Delivers value by providing the clinical data doctors need for patient care.

**Acceptance Scenarios**:

1. **Given** paired device-patient combination, **When** device transmits sensor data, **Then** system creates new session record with timestamp, device ID, patient ID, and sensor measurements
2. **Given** authenticated doctor with patient ID, **When** doctor requests biometric sessions for date range, **Then** system returns all sessions for that patient within the specified period
3. **Given** biometric session data, **When** doctor requests aggregation metrics, **Then** system returns average tremor intensity, session count, and total recording duration
4. **Given** authenticated patient, **When** patient requests own biometric data, **Then** system returns patient's own sessions only
5. **Given** authenticated patient, **When** patient attempts to view other patient data, **Then** system denies access
6. **Given** device not paired to patient, **When** device attempts to transmit data, **Then** system rejects data and returns pairing error

---

### Edge Cases

- What happens when a user tries to register with an already-used email address?
- How does the system handle expired JWT tokens during active sessions?
- What happens when a doctor tries to create a patient with missing required fields?
- How does the system handle concurrent updates to the same patient record?
- What happens when a device goes offline mid-session during data transmission?
- How does the system handle biometric data from unpaired devices?
- What happens when date range filters include future dates or invalid date formats?
- How does the system handle extremely large biometric data payloads?
- What happens when a doctor account is deactivated but has assigned patients?
- How does the system handle device re-pairing scenarios (switching patients)?

## Requirements *(mandatory)*

### Functional Requirements

**Authentication & User Management (US1)**

- **FR-001**: System MUST extend base user model with role field supporting two values: "patient" and "doctor"
- **FR-002**: System MUST provide registration endpoint accepting email, password, full name, and role
- **FR-003**: System MUST validate email uniqueness and format during registration
- **FR-004**: System MUST hash passwords before storage (never store plaintext)
- **FR-005**: System MUST provide login endpoint accepting email and password credentials
- **FR-006**: System MUST generate JWT tokens containing user ID, email, and role upon successful login
- **FR-007**: System MUST validate JWT tokens on all protected endpoints
- **FR-008**: System MUST enforce role-based access control on all API endpoints
- **FR-009**: System MUST set JWT token expiration to 24 hours
- **FR-010**: System MUST reject requests with expired or invalid JWT tokens

**Patient Profile Management (US2)**

- **FR-011**: System MUST provide endpoint to create patient records with name, date of birth, contact information, and medical notes
- **FR-012**: System MUST assign unique patient ID upon creation
- **FR-013**: System MUST allow doctors to retrieve list of patients they created or are assigned to
- **FR-014**: System MUST allow doctors to update patient information (name, contact, medical notes)
- **FR-015**: System MUST provide patient search by name (partial match, case-insensitive)
- **FR-016**: System MUST allow doctors to assign patients to other doctors (doctor-patient relationship)
- **FR-017**: System MUST allow patients to view only their own profile information
- **FR-018**: System MUST prevent patients from viewing or modifying other patients' data
- **FR-019**: System MUST prevent patient deletion if device is paired or biometric data exists
- **FR-020**: System MUST track created_at and updated_at timestamps for patient records

**Device Registration & Pairing (US3)**

- **FR-021**: System MUST provide endpoint to register glove devices with unique serial number
- **FR-022**: System MUST validate device serial number uniqueness during registration
- **FR-023**: System MUST initialize device status as "offline" upon registration
- **FR-024**: System MUST provide endpoint to pair device to patient (one device to one patient)
- **FR-025**: System MUST prevent device from being paired to multiple patients simultaneously
- **FR-026**: System MUST allow device re-pairing after unpairing from previous patient
- **FR-027**: System MUST track device online/offline status with last-seen timestamp
- **FR-028**: System MUST update device status when device connects or disconnects
- **FR-029**: System MUST allow doctors to view device information and status for their patients
- **FR-030**: System MUST prevent device data transmission if device is not paired to patient

**Biometric Data Storage & Retrieval (US4)**

- **FR-031**: System MUST provide endpoint to store biometric sensor sessions
- **FR-032**: System MUST validate device-patient pairing before accepting sensor data
- **FR-033**: System MUST store session data with timestamp, device ID, patient ID, and sensor measurements
- **FR-034**: System MUST provide endpoint to retrieve sessions by patient ID and date range
- **FR-035**: System MUST filter sessions by start date and end date (inclusive)
- **FR-036**: System MUST provide basic aggregation metrics: average tremor intensity, session count, total duration
- **FR-037**: System MUST allow doctors to retrieve biometric data for their assigned patients
- **FR-038**: System MUST allow patients to retrieve only their own biometric data
- **FR-039**: System MUST handle biometric data pagination for large result sets (50 sessions per page)
- **FR-040**: System MUST validate date range parameters (no future dates, valid format)

### Key Entities

- **User**: Represents platform users (doctors and patients). Attributes: email, hashed password, full name, role (patient/doctor), created timestamp. Relationships: Doctors can have many assigned patients.

- **Patient**: Represents patients being monitored. Attributes: unique ID, name, date of birth, contact information, medical notes, created timestamp, updated timestamp. Relationships: Belongs to user (if patient has account), assigned to multiple doctors, paired with one device, has many biometric sessions.

- **Device**: Represents physical glove hardware. Attributes: unique serial number, device ID, online/offline status, last-seen timestamp, registration timestamp. Relationships: Paired with one patient at a time, generates many biometric sessions.

- **BiometricSession**: Represents sensor data recording period. Attributes: session ID, timestamp, device ID, patient ID, sensor measurements (tremor data), session duration. Relationships: Belongs to one patient, belongs to one device.

- **DoctorPatientAssignment**: Represents doctor-patient relationship. Attributes: doctor user ID, patient ID, assignment date. Relationships: Links doctors to patients for access control.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Doctors can register an account and log in within 2 minutes without technical assistance
- **SC-002**: Authentication endpoints respond within 500ms for 95% of requests
- **SC-003**: Doctors can create a complete patient profile in under 1 minute
- **SC-004**: Patient search returns results within 1 second for databases with up to 1000 patient records
- **SC-005**: Device pairing process completes within 30 seconds including validation
- **SC-006**: System accurately tracks device online/offline status with status updates within 5 seconds of connection changes
- **SC-007**: Biometric data retrieval for 30-day date range completes within 2 seconds
- **SC-008**: System stores 100% of transmitted sensor data without loss when device is properly paired
- **SC-009**: Role-based access control prevents 100% of unauthorized access attempts across all endpoints
- **SC-010**: System handles 10 concurrent doctors each managing 20 patients without performance degradation

## Assumptions

- Doctors have valid email addresses for registration
- Device serial numbers are pre-assigned by hardware manufacturer and provided to doctors
- Sensor measurements format will be defined in technical implementation (not specified here)
- Biometric sessions are discrete time periods (not continuous streaming) - streaming will be separate feature
- Basic aggregation metrics are sufficient for initial release; advanced analytics will be future enhancement
- Patient date of birth is required for age-based analysis in future features
- Email-based authentication is sufficient; multi-factor authentication will be future enhancement
- One device per patient is sufficient initially; multiple devices per patient will be future enhancement
- Doctor-patient assignment allows many-to-many relationships (one patient can have multiple doctors)
- Device "online" status indicates device is powered on and connected to network, not actively transmitting

## Out of Scope

- Real-time WebSocket streaming of sensor data (separate feature)
- Advanced analytics and tremor pattern recognition (separate feature)
- Email verification for user registration (future enhancement)
- Password reset functionality (future enhancement)
- User profile management (photo, preferences) (future enhancement)
- Device firmware updates through platform (future enhancement)
- Patient-initiated doctor assignment requests (future enhancement)
- Biometric data visualization charts (frontend feature)
- Export biometric data to external formats (future enhancement)
- Audit logging of all API operations (future enhancement)
