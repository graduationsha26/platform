# Tasks: Real-Time Pipeline

**Input**: Design documents from `/specs/002-realtime-pipeline/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/websocket-messages.yaml, quickstart.md

**Tests**: Tests are NOT explicitly requested in the feature specification. Test tasks are omitted. Integration testing will be covered in quickstart.md scenarios.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app** (TremoAI): `backend/` for Django backend
- Paths reflect monorepo structure with backend/ directory

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and Django Channels configuration

- [X] T001 Install Python dependencies for Django Channels and MQTT in backend/requirements.txt (add channels==4.0.0, channels-redis==4.1.0, paho-mqtt==1.6.1, redis==5.0.1)
- [X] T002 Create realtime/ Django app in backend/realtime/ directory
- [X] T003 Register realtime app in backend/tremoai_backend/settings.py INSTALLED_APPS
- [X] T004 Configure Django Channels in backend/tremoai_backend/settings.py (add ASGI_APPLICATION and CHANNEL_LAYERS with Redis backend)
- [X] T005 Update backend/tremoai_backend/asgi.py to configure ASGI application with WebSocket routing
- [X] T006 Create backend/tremoai_backend/routing.py for root WebSocket URL routing
- [X] T007 [P] Create backend/realtime/routing.py for realtime app WebSocket URL patterns
- [X] T008 [P] Add MQTT and Redis environment variables to backend/.env.example (MQTT_BROKER_URL, MQTT_USERNAME, MQTT_PASSWORD, REDIS_URL)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data model extensions and infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T009 Extend BiometricSession model in backend/biometrics/models.py with ml_prediction (JSONField), ml_predicted_at (DateTimeField), received_via_mqtt (BooleanField)
- [X] T010 Create database migration for BiometricSession extensions in backend/biometrics/migrations/
- [X] T011 Run migrations to apply BiometricSession schema changes (python manage.py migrate)
- [X] T012 [P] Create backend/realtime/__init__.py with empty module initialization
- [X] T013 [P] Create backend/realtime/serializers.py with WebSocket message serializers (TremorDataSerializer, StatusSerializer, ErrorSerializer, PingPongSerializer)
- [ ] T014 [P] Verify Redis server is running locally on port 6379 (prerequisite for channel layer)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Automatic Data Collection from Glove Devices (Priority: P1) 🎯 MVP

**Goal**: Continuously receive sensor data from TremoAI glove devices via MQTT, validate data, store in database

**Independent Test**: Publish MQTT message to devices/{serial}/data topic → Verify BiometricSession record created in database with correct patient/device association and sensor_data populated

### Implementation for User Story 1

- [X] T015 [P] [US1] Create backend/realtime/mqtt_client.py with MQTTClient class skeleton (connect, disconnect, on_message callbacks)
- [X] T016 [P] [US1] Create backend/realtime/validators.py with MQTT message validation functions (validate_mqtt_message, validate_device_pairing)
- [X] T017 [US1] Implement MQTT connection logic in backend/realtime/mqtt_client.py (connect to broker, subscribe to devices/+/data, handle connection errors)
- [X] T018 [US1] Implement MQTT message validation in backend/realtime/validators.py (check required fields, validate serial_number, check device pairing, validate tremor_intensity range)
- [X] T019 [US1] Implement database storage logic in backend/realtime/mqtt_client.py on_message handler (create BiometricSession record, set received_via_mqtt=True)
- [X] T020 [US1] Implement MQTT reconnection logic in backend/realtime/mqtt_client.py (exponential backoff: 1s, 2s, 4s, 8s, up to 60s)
- [X] T021 [US1] Create backend/realtime/management/commands/__init__.py with empty module initialization
- [X] T022 [US1] Create backend/realtime/management/commands/run_mqtt_subscriber.py Django management command (instantiate MQTTClient, call client.loop_forever())
- [X] T023 [US1] Add logging for MQTT events in backend/realtime/mqtt_client.py (connection, disconnection, message received, validation errors, database writes)
- [X] T024 [US1] Add error handling for database write failures in backend/realtime/mqtt_client.py (log error, attempt retry once, discard message if still failing)
- [X] T025 [US1] Update backend/README.md with instructions for running MQTT subscriber (python manage.py run_mqtt_subscriber in separate terminal)

**Checkpoint**: At this point, User Story 1 should be fully functional - MQTT messages stored to database. Test with quickstart.md Scenario 1.

---

## Phase 4: User Story 2 - Live Monitoring of Patient Tremor Data (Priority: P2)

**Goal**: Stream real-time tremor data to authenticated users via WebSocket connections

**Independent Test**: Establish WebSocket connection to /ws/tremor-data/{patient_id}/ with JWT token → Publish MQTT message → Verify WebSocket client receives tremor_data message within 500ms

### Implementation for User Story 2

- [X] T026 [P] [US2] Create backend/realtime/consumers.py with TremorDataConsumer class skeleton (connect, disconnect, receive methods)
- [X] T027 [P] [US2] Create backend/realtime/auth.py with WebSocket JWT authentication helper functions (extract_jwt_from_query, validate_jwt_token)
- [X] T028 [US2] Implement WebSocket JWT authentication in backend/realtime/consumers.py connect method (extract token from query params, validate with SimpleJWT, reject with 4401 if invalid)
- [X] T029 [US2] Implement patient access control in backend/realtime/consumers.py connect method (verify user is assigned doctor or patient themselves, reject with 4403 if forbidden)
- [X] T030 [US2] Implement channel group join in backend/realtime/consumers.py connect method (add to patient_{patient_id}_tremor_data group)
- [X] T031 [US2] Implement status message on connect in backend/realtime/consumers.py (send StatusMessage with status="connected" after successful authentication)
- [X] T032 [US2] Implement channel group leave in backend/realtime/consumers.py disconnect method (remove from patient_{patient_id}_tremor_data group)
- [X] T033 [US2] Implement tremor_data handler in backend/realtime/consumers.py (receives messages from group_send, forwards to WebSocket client)
- [X] T034 [US2] Integrate channel layer broadcasting in backend/realtime/mqtt_client.py on_message handler (after database write, call channel_layer.group_send to patient group)
- [X] T035 [US2] Implement ping/pong handlers in backend/realtime/consumers.py receive method (respond to PingMessage with PongMessage)
- [X] T036 [US2] Update backend/realtime/routing.py with WebSocket URL pattern for /ws/tremor-data/<int:patient_id>/ (route to TremorDataConsumer)
- [X] T037 [US2] Add logging for WebSocket events in backend/realtime/consumers.py (connection established, authentication success/failure, disconnection, messages sent/received)
- [X] T038 [US2] Update backend/README.md with WebSocket connection instructions (URL format, JWT token parameter, example JavaScript code)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently - MQTT data flows through to WebSocket clients. Test with quickstart.md Scenarios 1, 2, 3, 4.

---

## Phase 5: User Story 3 - AI-Powered Tremor Severity Insights (Priority: P3)

**Goal**: Generate and display ML predictions alongside raw sensor data in real-time

**Independent Test**: Publish MQTT message → Verify WebSocket message includes prediction field with severity and confidence → Verify database record has ml_prediction populated

### Implementation for User Story 3

- [X] T039 [P] [US3] Create backend/realtime/ml_service.py with MLPredictionService class skeleton (singleton pattern)
- [X] T040 [P] [US3] Create backend/models/ directory for ML model files (add to .gitignore)
- [X] T041 [US3] Implement model loading in backend/realtime/ml_service.py __init__ method (load scikit-learn .pkl and TensorFlow .h5 models, cache in memory, use threading.Lock for thread-safety)
- [X] T042 [US3] Implement feature extraction in backend/realtime/ml_service.py _extract_features method (extract tremor_intensity_avg, frequency, duration from sensor_data)
- [X] T043 [US3] Implement prediction generation in backend/realtime/ml_service.py predict_severity method (preprocess features, call sklearn model.predict, return severity and confidence)
- [X] T044 [US3] Integrate ML prediction in backend/realtime/mqtt_client.py on_message handler (call MLPredictionService.predict_severity after validation, include in BiometricSession.ml_prediction)
- [X] T045 [US3] Add prediction to WebSocket broadcast in backend/realtime/mqtt_client.py (include prediction field in group_send message if ML service succeeded)
- [X] T046 [US3] Implement ML service error handling in backend/realtime/mqtt_client.py (catch exceptions, log errors, broadcast data without prediction if ML fails, set ml_prediction=None in database)
- [X] T047 [US3] Add ml_predicted_at timestamp in backend/realtime/mqtt_client.py (set to timezone.now() when prediction succeeds)
- [X] T048 [US3] Add logging for ML events in backend/realtime/ml_service.py (model loaded, prediction generated, prediction failed, feature extraction errors)
- [X] T049 [US3] Update backend/README.md with ML model setup instructions (where to place .pkl/.h5 files, expected model format, prediction output schema)

**Checkpoint**: All user stories should now be independently functional - complete real-time pipeline with ML predictions. Test with quickstart.md Scenarios 5, 6, 7.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories, documentation, and validation

- [X] T050 [P] Add comprehensive docstrings to all classes in backend/realtime/ modules (MQTTClient, TremorDataConsumer, MLPredictionService)
- [X] T051 [P] Add input validation and type hints to all functions in backend/realtime/ modules (use Python typing module)
- [X] T052 Create backend/realtime/tests/__init__.py with empty module initialization
- [X] T053 [P] Create backend/realtime/tests/test_mqtt_client.py with unit tests for MQTT message validation (mock MQTT client, test valid/invalid messages)
- [X] T054 [P] Create backend/realtime/tests/test_consumers.py with unit tests for WebSocket consumer authentication (mock JWT tokens, test valid/invalid/forbidden cases)
- [X] T055 [P] Create backend/realtime/tests/test_ml_service.py with unit tests for ML prediction service (mock model loading, test feature extraction and prediction)
- [ ] T056 Run all unit tests for realtime app (pytest backend/realtime/tests/)
- [ ] T057 Validate integration scenarios from quickstart.md (run all 8 scenarios, document results)
- [ ] T058 Measure end-to-end latency (MQTT → WebSocket) and verify meets SC-002 (<500ms requirement)
- [X] T059 [P] Update backend/README.md with troubleshooting section (common errors, solutions for MQTT/WebSocket/Redis/ML issues)
- [X] T060 [P] Document MQTT topic structure in backend/README.md (devices/{serial}/data pattern, payload schema)
- [X] T061 [P] Document WebSocket connection procedure in backend/README.md (authentication, message types, close codes)
- [ ] T062 Code review and refactoring for backend/realtime/ modules (check for code duplication, improve error messages, optimize performance)
- [ ] T063 Security audit for WebSocket authentication in backend/realtime/consumers.py (verify JWT validation, check access control, ensure no data leakage)
- [ ] T064 Performance testing with high-frequency data stream (publish 50 messages/sec, verify system handles load per SC-001)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User Story 1 (P1) can start after Foundational
  - User Story 2 (P2) can start after Foundational AND User Story 1 (requires MQTT pipeline)
  - User Story 3 (P3) can start after Foundational AND User Story 1 (requires MQTT pipeline)
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: DEPENDS on User Story 1 (requires MQTT client to broadcast to channel layer)
- **User Story 3 (P3)**: DEPENDS on User Story 1 (requires MQTT client to call ML service)

**Important**: User Stories 2 and 3 are NOT independent - both require User Story 1's MQTT pipeline to be functional.

### Within Each User Story

- **User Story 1**: Validators and MQTT client core → Management command → Error handling → Logging
- **User Story 2**: Consumer skeleton → Authentication → Channel groups → Broadcasting integration
- **User Story 3**: ML service skeleton → Model loading → Prediction → Integration with MQTT pipeline

### Parallel Opportunities

- **Phase 1 (Setup)**: T007 (routing.py) and T008 (.env.example) can run in parallel with T001-T006
- **Phase 2 (Foundational)**: T012 (__init__.py), T013 (serializers.py), T014 (Redis check) can run in parallel after T009-T011
- **Phase 3 (US1)**: T015 (mqtt_client.py skeleton) and T016 (validators.py skeleton) can run in parallel
- **Phase 4 (US2)**: T026 (consumers.py skeleton) and T027 (auth.py helpers) can run in parallel
- **Phase 5 (US3)**: T039 (ml_service.py skeleton) and T040 (models/ directory) can run in parallel
- **Phase 6 (Polish)**: T050, T051, T053, T054, T055, T059, T060, T061 can all run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch skeleton creation tasks together:
Task: "Create backend/realtime/mqtt_client.py with MQTTClient class skeleton"
Task: "Create backend/realtime/validators.py with MQTT message validation functions"

# After skeletons complete, these can proceed sequentially:
# - MQTT connection logic
# - Message validation
# - Database storage
# - Reconnection logic
# - Management command
# - Logging and error handling
```

---

## Parallel Example: User Story 2

```bash
# Launch skeleton and helper creation tasks together:
Task: "Create backend/realtime/consumers.py with TremorDataConsumer class skeleton"
Task: "Create backend/realtime/auth.py with WebSocket JWT authentication helper functions"

# After skeletons complete, these proceed sequentially:
# - Authentication implementation
# - Access control
# - Channel group management
# - Broadcasting integration
# - Logging
```

---

## Parallel Example: Polish Phase

```bash
# Launch documentation and testing tasks together:
Task: "Add comprehensive docstrings to all classes"
Task: "Add input validation and type hints"
Task: "Create test_mqtt_client.py with unit tests"
Task: "Create test_consumers.py with unit tests"
Task: "Create test_ml_service.py with unit tests"
Task: "Update README.md with troubleshooting section"
Task: "Document MQTT topic structure"
Task: "Document WebSocket connection procedure"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (8 tasks, ~2 hours)
2. Complete Phase 2: Foundational (6 tasks, ~2 hours)
3. Complete Phase 3: User Story 1 (11 tasks, ~6 hours)
4. **STOP and VALIDATE**: Run quickstart.md Scenario 1 independently
5. Verify MQTT → Database flow works
6. **MVP DELIVERED**: Basic data collection operational

**Estimated MVP Time**: ~10 hours (1.5 days)

### Incremental Delivery

1. **Foundation** (Phase 1 + 2): ~4 hours → Django Channels + BiometricSession ready
2. **MVP** (Phase 3): ~6 hours → Data collection from MQTT works → Deploy/Demo
3. **Live Monitoring** (Phase 4): ~6 hours → WebSocket streaming works → Deploy/Demo
4. **ML Predictions** (Phase 5): ~4 hours → AI insights works → Deploy/Demo
5. **Production Ready** (Phase 6): ~4 hours → Tests, docs, validation complete

**Total Estimated Time**: ~24 hours (3 days of focused work)

### Parallel Team Strategy

With 2 developers:

1. **Both**: Complete Setup + Foundational together (~4 hours)
2. **Developer A**: User Story 1 (MQTT data collection) (~6 hours)
3. **Developer A completes US1** → Deploy MVP
4. **Developer A**: User Story 2 (WebSocket streaming) (~6 hours)
   **Developer B**: User Story 3 (ML predictions, WAITS for US1) (~4 hours)
5. **Both**: Polish phase together (~4 hours)

**Total Team Time**: ~14 hours (2 days with 2 developers)

**Note**: User Stories 2 and 3 cannot start until User Story 1 is complete (they depend on MQTT pipeline).

---

## Notes

- **[P] tasks** = different files, no dependencies within phase
- **[Story] label** maps task to specific user story for traceability
- **User Story 2 and 3 depend on User Story 1** - MQTT pipeline must be functional before WebSocket/ML features
- Each user story checkpoint can be validated with quickstart.md scenarios
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- **Tests omitted** - Feature spec does not explicitly request TDD approach. Integration testing covered by quickstart.md scenarios.
- **External prerequisites**: Redis server running (localhost:6379), MQTT broker running (configured in .env)
- **ML model files**: Must be manually placed in backend/models/ directory (not in git)

---

## Task Count Summary

- **Phase 1 (Setup)**: 8 tasks
- **Phase 2 (Foundational)**: 6 tasks
- **Phase 3 (User Story 1 - P1)**: 11 tasks
- **Phase 4 (User Story 2 - P2)**: 13 tasks
- **Phase 5 (User Story 3 - P3)**: 11 tasks
- **Phase 6 (Polish)**: 15 tasks

**Total Tasks**: 64 tasks

**Parallel Opportunities**: 15 tasks marked [P] can run in parallel within their phases

**MVP Scope**: Phases 1, 2, and 3 only (25 tasks) = Functional MQTT data collection

**Full Feature**: All 64 tasks = Complete real-time pipeline with WebSocket streaming and ML predictions
