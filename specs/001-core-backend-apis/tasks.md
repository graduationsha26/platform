# Tasks: Core Backend APIs

**Input**: Design documents from `/specs/001-core-backend-apis/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/ (all complete)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `backend/` at repository root (Django monorepo structure)
- **Apps**: `backend/authentication/`, `backend/patients/`, `backend/devices/`, `backend/biometrics/`
- **Project**: `backend/tremoai_backend/` (Django project settings)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Django project initialization and basic structure

- [ ] T001 Create backend directory structure at repository root
- [ ] T002 Initialize Django project: `django-admin startproject tremoai_backend backend/`
- [ ] T003 [P] Create requirements.txt in backend/ with Django 5.x, djangorestframework, djangorestframework-simplejwt, dj-database-url, django-filter, psycopg2-binary, python-decouple
- [ ] T004 [P] Create .env.example in repository root with DATABASE_URL, DJANGO_SECRET_KEY, SUPABASE_URL, SUPABASE_KEY, JWT_SECRET_KEY placeholders
- [ ] T005 Create Django app for authentication: `python manage.py startapp authentication` in backend/
- [ ] T006 [P] Create Django app for patients: `python manage.py startapp patients` in backend/
- [ ] T007 [P] Create Django app for devices: `python manage.py startapp devices` in backend/
- [ ] T008 [P] Create Django app for biometrics: `python manage.py startapp biometrics` in backend/
- [ ] T009 Create .gitignore entries for backend/ (*.pyc, __pycache__/, .env, db.sqlite3, *.log)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T010 Configure Django settings.py for Supabase PostgreSQL using dj-database-url in backend/tremoai_backend/settings.py
- [ ] T011 Configure CORS settings in backend/tremoai_backend/settings.py (django-cors-headers)
- [ ] T012 Configure REST Framework settings in backend/tremoai_backend/settings.py (pagination, authentication classes, permission classes)
- [ ] T013 Configure SimpleJWT settings in backend/tremoai_backend/settings.py (ACCESS_TOKEN_LIFETIME=24h, REFRESH_TOKEN_LIFETIME=7d)
- [ ] T014 Add installed apps to INSTALLED_APPS in backend/tremoai_backend/settings.py (rest_framework, rest_framework_simplejwt, django_filters, corsheaders, authentication, patients, devices, biometrics)
- [ ] T015 Configure AUTH_USER_MODEL = 'authentication.CustomUser' in backend/tremoai_backend/settings.py
- [ ] T016 Configure root URLs in backend/tremoai_backend/urls.py to include app URL patterns with /api/ prefix

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - User Registration and Authentication (Priority: P1) 🎯 MVP

**Goal**: Enable doctors and patients to register accounts and authenticate with JWT tokens

**Independent Test**: Register doctor and patient users, log in with credentials, receive JWT tokens, verify role-based access restrictions

### Models (US1)

- [ ] T017 [US1] Create CustomUser model in backend/authentication/models.py extending AbstractUser with role field (CHOICES: doctor/patient), email as USERNAME_FIELD, remove username field
- [ ] T018 [US1] Create and run migrations for authentication app: `python manage.py makemigrations authentication && python manage.py migrate`

### Serializers (US1)

- [ ] T019 [P] [US1] Create UserSerializer in backend/authentication/serializers.py (read-only: id, email, first_name, last_name, role, date_joined)
- [ ] T020 [P] [US1] Create RegisterSerializer in backend/authentication/serializers.py (write: email, password, first_name, last_name, role; validate email uniqueness, hash password)
- [ ] T021 [P] [US1] Create custom TokenObtainPairSerializer in backend/authentication/serializers.py to include user data (id, email, role) in token response

### Permissions (US1)

- [ ] T022 [P] [US1] Create IsDoctor permission class in backend/authentication/permissions.py (check user.role == 'doctor')
- [ ] T023 [P] [US1] Create IsPatient permission class in backend/authentication/permissions.py (check user.role == 'patient')
- [ ] T024 [P] [US1] Create IsOwnerOrDoctor permission class in backend/authentication/permissions.py (patient can access own data OR user is doctor)

### Views (US1)

- [ ] T025 [US1] Create RegisterView in backend/authentication/views.py (POST /api/auth/register/, use RegisterSerializer, return 201 with user data)
- [ ] T026 [US1] Create custom TokenObtainPairView in backend/authentication/views.py using custom serializer (POST /api/auth/login/)
- [ ] T027 [US1] Configure TokenRefreshView in backend/authentication/views.py (POST /api/auth/refresh/, use SimpleJWT built-in view)

### URLs (US1)

- [ ] T028 [US1] Create URL patterns in backend/authentication/urls.py for register/, login/, refresh/ endpoints
- [ ] T029 [US1] Include authentication URLs in root urls.py at /api/auth/ prefix

**Phase 3 Complete**: ✅ US1 - Users can register and authenticate with JWT

---

## Phase 4: User Story 2 - Patient Profile Management (Priority: P2)

**Goal**: Enable doctors to create, view, update, and search patient profiles

**Independent Test**: Authenticate as doctor, create patient records, view patient lists, update patient info, search by name, assign patients to doctors

**Dependencies**: Requires US1 (authentication) complete

### Models (US2)

- [ ] T030 [US2] Create Patient model in backend/patients/models.py (fields: full_name, date_of_birth, contact_phone, contact_email, medical_notes, created_by FK to CustomUser, user OneToOne to CustomUser nullable, timestamps)
- [ ] T031 [US2] Create DoctorPatientAssignment model in backend/patients/models.py (fields: doctor FK to CustomUser, patient FK to Patient, assigned_at, assigned_by FK to CustomUser; unique_together on doctor+patient)
- [ ] T032 [US2] Create and run migrations for patients app: `python manage.py makemigrations patients && python manage.py migrate`

### Serializers (US2)

- [ ] T033 [P] [US2] Create PatientListSerializer in backend/patients/serializers.py (fields: id, full_name, date_of_birth, contact_email, created_at; read-only)
- [ ] T034 [P] [US2] Create PatientDetailSerializer in backend/patients/serializers.py (all fields including medical_notes, assigned_doctors nested, paired_device nested, created_by nested)
- [ ] T035 [P] [US2] Create PatientCreateSerializer in backend/patients/serializers.py (write: full_name, date_of_birth, contact_phone, contact_email, medical_notes; validate date_of_birth not future)
- [ ] T036 [P] [US2] Create DoctorPatientAssignmentSerializer in backend/patients/serializers.py (doctor_id, patient_id, assigned_at)

### Filters (US2)

- [ ] T037 [US2] Create PatientFilter in backend/patients/filters.py using django-filter with custom name filter method (Q filter on first_name__icontains OR last_name__icontains)

### Views (US2)

- [ ] T038 [US2] Create PatientViewSet in backend/patients/views.py (ModelViewSet with list, create, retrieve, update actions; permission_classes=[IsAuthenticated, IsDoctor])
- [ ] T039 [US2] Add get_queryset override in PatientViewSet to filter patients by created_by or assigned doctors for current user
- [ ] T040 [US2] Add search action to PatientViewSet using PatientFilter (GET /api/patients/search/?name=...)
- [ ] T041 [US2] Add assign_doctor action to PatientViewSet (POST /api/patients/{id}/assign-doctor/ with doctor_id in body, create DoctorPatientAssignment)

### URLs (US2)

- [ ] T042 [US2] Create URL patterns in backend/patients/urls.py using DRF router for PatientViewSet
- [ ] T043 [US2] Include patients URLs in root urls.py at /api/patients/ prefix

**Phase 4 Complete**: ✅ US2 - Doctors can manage patient profiles

---

## Phase 5: User Story 3 - Device Registration and Patient Pairing (Priority: P3)

**Goal**: Enable device registration, patient pairing, and online/offline status tracking

**Independent Test**: Authenticate as doctor, register glove device, pair device to patient, update device online/offline status

**Dependencies**: Requires US2 (patients) complete

### Models (US3)

- [ ] T044 [US3] Create Device model in backend/devices/models.py (fields: serial_number unique, status CharField with CHOICES ['online','offline'] default='offline', last_seen DateTimeField nullable, patient FK to Patient nullable, registered_by FK to CustomUser, registered_at)
- [ ] T045 [US3] Create and run migrations for devices app: `python manage.py makemigrations devices && python manage.py migrate`

### Serializers (US3)

- [ ] T046 [P] [US3] Create DeviceListSerializer in backend/devices/serializers.py (fields: id, serial_number, status, last_seen, patient nested with id+full_name, registered_at)
- [ ] T047 [P] [US3] Create DeviceDetailSerializer in backend/devices/serializers.py (all fields including registered_by nested, patient full detail nested)
- [ ] T048 [P] [US3] Create DeviceCreateSerializer in backend/devices/serializers.py (write: serial_number; validate serial_number format alphanumeric 8-20 chars)
- [ ] T049 [P] [US3] Create DevicePairingSerializer in backend/devices/serializers.py (patient_id field, validate patient exists and user has access)
- [ ] T050 [P] [US3] Create DeviceStatusSerializer in backend/devices/serializers.py (status field with CHOICES validation, optional last_seen defaults to now)

### Views (US3)

- [ ] T051 [US3] Create DeviceViewSet in backend/devices/views.py (ModelViewSet with list, create, retrieve actions; permission_classes=[IsAuthenticated, IsDoctor])
- [ ] T052 [US3] Add pair action to DeviceViewSet (POST /api/devices/{id}/pair/, use DevicePairingSerializer, update device.patient field, return pairing confirmation with previous_patient_id if re-pairing)
- [ ] T053 [US3] Add unpair action to DeviceViewSet (POST /api/devices/{id}/unpair/, set device.patient=None)
- [ ] T054 [US3] Add status update action to DeviceViewSet (PUT /api/devices/{id}/status/, use DeviceStatusSerializer, update device.status and last_seen)
- [ ] T055 [US3] Add status filter to DeviceViewSet list action (FilterBackend with status query param)

### URLs (US3)

- [ ] T056 [US3] Create URL patterns in backend/devices/urls.py using DRF router for DeviceViewSet with custom actions for pair, unpair, status
- [ ] T057 [US3] Include devices URLs in root urls.py at /api/devices/ prefix

**Phase 5 Complete**: ✅ US3 - Devices can be registered and paired to patients

---

## Phase 6: User Story 4 - Biometric Data Storage and Retrieval (Priority: P4)

**Goal**: Enable storage and retrieval of sensor data sessions with date range filtering and aggregation

**Independent Test**: Store sensor session data for paired device-patient, retrieve sessions by date range, compute aggregation metrics

**Dependencies**: Requires US3 (devices) complete

### Models (US4)

- [ ] T058 [US4] Create BiometricSession model in backend/biometrics/models.py (fields: patient FK to Patient, device FK to Device, session_start DateTimeField, session_duration DurationField, sensor_data JSONField, created_at; indexes on patient+session_start and device+session_start)
- [ ] T059 [US4] Create and run migrations for biometrics app: `python manage.py makemigrations biometrics && python manage.py migrate`

### Serializers (US4)

- [ ] T060 [P] [US4] Create BiometricSessionListSerializer in backend/biometrics/serializers.py (fields: id, patient nested, device nested, session_start, session_duration, created_at; exclude sensor_data for list view)
- [ ] T061 [P] [US4] Create BiometricSessionDetailSerializer in backend/biometrics/serializers.py (all fields including full sensor_data JSON)
- [ ] T062 [P] [US4] Create BiometricSessionCreateSerializer in backend/biometrics/serializers.py (write: patient_id, device_id, session_start, session_duration, sensor_data; validate device paired to patient, sensor_data JSON structure with required keys: tremor_intensity, timestamps, frequency)
- [ ] T063 [P] [US4] Create BiometricAggregationSerializer in backend/biometrics/serializers.py (patient_id, date_range, metrics dict with session_count, total_duration, average_tremor_intensity, min/max tremor)

### Aggregation Logic (US4)

- [ ] T064 [US4] Create aggregation utility functions in backend/biometrics/aggregation.py (compute_average_tremor_intensity, compute_total_duration, compute_session_count using Django ORM aggregation)

### Views (US4)

- [ ] T065 [US4] Create BiometricSessionViewSet in backend/biometrics/views.py (ModelViewSet with list, create, retrieve actions; permission_classes=[IsAuthenticated, IsOwnerOrDoctor])
- [ ] T066 [US4] Add get_queryset override in BiometricSessionViewSet to filter by patient access (patients see own, doctors see assigned patients)
- [ ] T067 [US4] Add date range filtering to BiometricSessionViewSet list action (start_date and end_date query params using django-filter)
- [ ] T068 [US4] Add patient_id and device_id filtering to BiometricSessionViewSet list action
- [ ] T069 [US4] Add aggregate action to BiometricSessionViewSet (GET /api/biometric-sessions/aggregate/?patient_id=X&start_date=...&end_date=..., use aggregation.py functions, return BiometricAggregationSerializer)
- [ ] T070 [US4] Validate device-patient pairing in create action before accepting sensor data

### URLs (US4)

- [ ] T071 [US4] Create URL patterns in backend/biometrics/urls.py using DRF router for BiometricSessionViewSet with custom aggregate action
- [ ] T072 [US4] Include biometrics URLs in root urls.py at /api/biometric-sessions/ prefix

**Phase 6 Complete**: ✅ US4 - Biometric data can be stored and retrieved with aggregations

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Error handling, validation refinements, documentation, integration testing

- [ ] T073 [P] Create custom exception classes in backend/authentication/exceptions.py (InvalidCredentialsException, TokenExpiredException)
- [ ] T074 [P] Create custom exception classes in backend/devices/exceptions.py (DeviceAlreadyPairedException, DeviceNotPairedException, UnpairedDeviceException)
- [ ] T075 [P] Create custom DRF exception handler in backend/tremoai_backend/exceptions.py to format all errors as {"error": "message", "code": "code", "details": {}}
- [ ] T076 Configure custom exception handler in settings.py REST_FRAMEWORK['EXCEPTION_HANDLER']
- [ ] T077 [P] Add validation for duplicate email in RegisterSerializer with custom error message
- [ ] T078 [P] Add validation for future dates in Patient date_of_birth field
- [ ] T079 [P] Add validation for device serial number format in DeviceCreateSerializer (regex: ^[A-Z0-9]{8,20}$)
- [ ] T080 [P] Add validation for sensor_data JSON structure in BiometricSessionCreateSerializer
- [ ] T081 [P] Create API documentation endpoint using drf-spectacular at /api/docs/
- [ ] T082 [P] Add pagination configuration for biometric sessions (PAGE_SIZE=50) and patients (PAGE_SIZE=20)
- [ ] T083 [P] Add logging configuration in settings.py for authentication events, API errors, and device status changes
- [ ] T084 Create management command for creating test users: `python manage.py create_test_users` (1 doctor, 1 patient)
- [ ] T085 Create README.md in backend/ with setup instructions (env vars, migrations, runserver)

---

## Implementation Strategy

### MVP Scope (Minimum Viable Product)

**Phase 3 ONLY** (User Story 1 - Authentication)
- Doctors and patients can register and log in
- JWT tokens issued for authentication
- Foundation for all other features

**MVP Delivery**: Completes Phase 1, 2, 3 → Working authentication system

### Incremental Delivery

1. **Increment 1 (MVP)**: US1 - Authentication (Phase 1-3)
2. **Increment 2**: US2 - Patient Management (Phase 4)
3. **Increment 3**: US3 - Device Registration (Phase 5)
4. **Increment 4**: US4 - Biometric Data (Phase 6)
5. **Increment 5**: Polish & Refinements (Phase 7)

Each increment is independently testable and deployable.

### Parallel Execution Opportunities

**Setup Phase (Phase 1)**: Tasks T003-T008 can run in parallel (independent file creation)

**Foundational Phase (Phase 2)**: Tasks T010-T015 must run sequentially (settings.py modifications)

**US1 Phase (Phase 3)**:
- Parallel: T019-T021 (serializers), T022-T024 (permissions)
- Sequential: T017-T018 → T025-T027 → T028-T029

**US2 Phase (Phase 4)**:
- Parallel: T033-T036 (serializers after models)
- Sequential: T030-T032 → T038-T041 → T042-T043

**US3 Phase (Phase 5)**:
- Parallel: T046-T050 (serializers after models)
- Sequential: T044-T045 → T051-T054 → T056-T057

**US4 Phase (Phase 6)**:
- Parallel: T060-T063 (serializers after models)
- Sequential: T058-T059 → T065-T070 → T071-T072

**Polish Phase (Phase 7)**: Tasks T073-T083 can run in parallel (independent files)

## Dependencies

### User Story Dependencies

```
US1 (Authentication) → US2 (Patients) → US3 (Devices) → US4 (Biometrics)
         ↓                                                      ↑
    Foundation                                            Depends on
    (Blocks all)                                         Device Pairing
```

**Blocking Relationships**:
- US2 requires US1 (authentication needed to create patients)
- US3 requires US2 (devices pair to patients)
- US4 requires US3 (sessions require device pairing)

**Independent Relationships**: None - linear dependency chain

### Phase Completion Criteria

- **Phase 1 Complete**: All Django apps created, requirements.txt exists
- **Phase 2 Complete**: Settings configured, migrations can run, server starts
- **Phase 3 Complete**: Users can register and log in, JWT tokens work
- **Phase 4 Complete**: Doctors can CRUD patients, search works
- **Phase 5 Complete**: Devices can be registered and paired
- **Phase 6 Complete**: Biometric data can be stored and retrieved
- **Phase 7 Complete**: All error handling, validation, docs complete

## Task Statistics

**Total Tasks**: 85
- Phase 1 (Setup): 9 tasks
- Phase 2 (Foundational): 7 tasks
- Phase 3 (US1 - Authentication): 13 tasks
- Phase 4 (US2 - Patients): 14 tasks
- Phase 5 (US3 - Devices): 14 tasks
- Phase 6 (US4 - Biometrics): 15 tasks
- Phase 7 (Polish): 13 tasks

**Parallelizable Tasks**: 35 tasks marked with [P]
**Sequential Tasks**: 50 tasks (dependencies require order)

**Estimated Effort**:
- MVP (Phase 1-3): ~25 tasks → Foundation + Authentication
- Full Feature (All phases): 85 tasks → Complete backend APIs

## Validation Checklist

Before starting implementation:
- [X] All tasks follow checklist format (checkbox, ID, labels, file paths)
- [X] All tasks have clear file paths specified
- [X] User story labels (US1-US4) correctly assigned
- [X] Parallel tasks [P] marked appropriately
- [X] Dependencies documented and validated
- [X] Each user story independently testable
- [X] MVP scope clearly defined (US1 only)
- [X] Task IDs sequential (T001-T085)

**Ready for `/speckit.implement`** ✅
