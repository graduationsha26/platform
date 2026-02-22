# Tasks: Remove Flex Fields from MQTT Parser

**Input**: Design documents from `/specs/019-remove-flex-mqtt/`
**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ contracts/ ✅ quickstart.md ✅

**Tests**: Included — spec FR-006 and SC-004 explicitly require test updates.

**Organization**: Tasks grouped by user story. US1 implements the core raw-reading pipeline; US2 adds backward-compatibility test coverage for legacy flex payloads.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files or no shared dependencies)
- **[Story]**: Which user story this task belongs to ([US1], [US2])
- All paths are relative to repository root

---

## Phase 1: Setup (Baseline Audit)

**Purpose**: Confirm the existing MQTT code is clean before introducing new code, establishing a verified baseline.

- [x] T001 Audit `backend/realtime/validators.py` and `backend/realtime/mqtt_client.py` for any flex_1–flex_5 references and confirm zero exist — document findings as a comment block at the top of the new validator function

**Checkpoint**: Baseline confirmed — existing session-level pipeline is flex-free. Ready to add raw-reading pipeline.

---

## Phase 2: Foundational (Blocking Prerequisites)

No blocking prerequisites required for this feature. The `BiometricReading` model (`backend/biometrics/models.py`), its serializer, and its ViewSet are already implemented and flex-free (Features E-2.1 and E-2.2). No migrations needed.

*Proceed directly to User Story phases.*

---

## Phase 3: User Story 1 — Accept Sensor Payloads Without Flex Fields (Priority: P1) 🎯 MVP

**Goal**: A new MQTT message validator and handler that accepts 6-field sensor payloads (`serial_number`, `timestamp`, `aX`, `aY`, `aZ`, `gX`, `gY`, `gZ`) and creates `BiometricReading` records. Flex fields are neither required nor read at any step.

**Independent Test**: Send an MQTT message to `devices/{serial}/reading` containing only the six sensor fields. Verify a `BiometricReading` record is created with those values and no errors are raised.

### Implementation for User Story 1

- [x] T002 [US1] Add `validate_biometric_reading_message(payload: dict) -> None` to `backend/realtime/validators.py` — required fields: `serial_number` (str, 8-20 uppercase alphanum), `timestamp` (ISO 8601), `aX`/`aY`/`aZ`/`gX`/`gY`/`gZ` (numeric); out-of-range values log a WARNING and are accepted; all other fields including flex_1–flex_5 are silently ignored; raises `django.core.exceptions.ValidationError` on any required-field violation

- [x] T003 [US1] Subscribe to `devices/+/reading` in `MQTTClient.on_connect()` in `backend/realtime/mqtt_client.py` — add alongside existing `devices/+/data` subscription; log the new subscription at INFO level

- [x] T004 [US1] Add topic-type dispatch in `MQTTClient.on_message()` in `backend/realtime/mqtt_client.py` — extract the third segment of the topic path; route `"data"` to existing session handler (unchanged); route `"reading"` to new `_handle_reading_message()`; log and discard any other segment type

- [x] T005 [US1] Implement `MQTTClient._handle_reading_message(payload: dict, serial_number: str) -> BiometricReading` in `backend/realtime/mqtt_client.py` — steps: (1) call `validate_biometric_reading_message(payload)`, (2) call `validate_device_pairing(serial_number)`, (3) parse timestamp with `timezone.datetime.fromisoformat()`, (4) call `BiometricReading.objects.create(patient=patient, timestamp=..., aX=payload['aX'], aY=payload['aY'], aZ=payload['aZ'], gX=payload['gX'], gY=payload['gY'], gZ=payload['gZ'])` — no flex fields referenced at any step

### Tests for User Story 1

- [x] T006 [P] [US1] Add test class `BiometricReadingMQTTValidationTest` to `backend/realtime/tests/test_mqtt_client.py` with test `test_valid_6_field_reading_payload` — construct a payload with `serial_number`, `timestamp`, and all six sensor fields; call `validate_biometric_reading_message(payload)`; assert no exception is raised

- [x] T007 [P] [US1] Add test `test_missing_required_sensor_field_raises_error` to `backend/realtime/tests/test_mqtt_client.py` — payload is missing `gZ`; assert `ValidationError` is raised and the error message mentions `gZ`

- [x] T008 [P] [US1] Add test `test_non_numeric_sensor_value_raises_error` to `backend/realtime/tests/test_mqtt_client.py` — payload has `aX: "not_a_number"`; assert `ValidationError` is raised

- [x] T009 [P] [US1] Add test `test_invalid_timestamp_format_raises_error` to `backend/realtime/tests/test_mqtt_client.py` — payload has `timestamp: "not-a-date"`; assert `ValidationError` is raised

**Checkpoint**: User Story 1 complete. A valid 6-field reading payload is accepted, validated, and stored as a `BiometricReading` record. All four validation tests pass. Story is independently functional.

---

## Phase 4: User Story 2 — Gracefully Ignore Legacy Flex Fields (Priority: P2)

**Goal**: Verify that payloads from older glove firmware that still include `flex_1`–`flex_5` are accepted without errors and that none of the flex values are stored in the resulting `BiometricReading` record.

**Independent Test**: Send an MQTT reading payload containing all eleven fields (six standard + five flex). Verify the reading is accepted, a `BiometricReading` record is created with only the six sensor values, and no `ValidationError` is raised.

### Tests for User Story 2

*(No implementation changes needed — the validator and handler built in US1 already ignore unknown fields. These tasks add explicit test coverage to prevent future regression.)*

- [x] T010 [P] [US2] Add test `test_legacy_11_field_payload_is_accepted` to `backend/realtime/tests/test_mqtt_client.py` — payload includes `serial_number`, `timestamp`, six sensor fields, and `flex_1` through `flex_5` with numeric values; call `validate_biometric_reading_message(payload)`; assert no exception is raised

- [x] T011 [P] [US2] Add test `test_flex_fields_not_stored_in_biometric_reading` to `backend/realtime/tests/test_mqtt_client.py` — using `unittest.mock.patch` on `BiometricReading.objects.create`, call `_handle_reading_message()` with a 11-field legacy payload; assert `create()` was called with keyword args `aX`, `aY`, `aZ`, `gX`, `gY`, `gZ` only and `flex_1` through `flex_5` were NOT passed

- [x] T012 [P] [US2] Add test `test_out_of_range_sensor_value_warns_not_raises` to `backend/realtime/tests/test_mqtt_client.py` — payload has `aX: 999.0` (outside -20.0/+20.0 range); call `validate_biometric_reading_message(payload)`; assert no exception is raised and that a WARNING was logged (use `assertLogs` or mock `logger.warning`)

**Checkpoint**: User Story 2 complete. Legacy payloads with flex fields are silently accepted. All three legacy-coverage tests pass. Both user stories are independently functional.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Final verification and cleanup across both user stories.

- [x] T013 Confirm zero flex references in the active MQTT parsing code — run `grep -r "flex" backend/realtime/ --include="*.py"` and verify any matches are only in test assertions (not in validation logic or handler code); update `specs/019-remove-flex-mqtt/checklists/requirements.md` to mark all items complete

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Audit)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Skipped — prerequisites already satisfied
- **Phase 3 (US1)**: Depends on Phase 1 completion
  - T002 must complete before T003, T004, T005
  - T003, T004 must complete before T005 (T005 calls both)
  - T006–T009 can run in parallel after T002 is complete
- **Phase 4 (US2)**: Depends on Phase 3 completion (T002, T005 must exist)
  - T010, T011, T012 are parallel (different test methods)
- **Phase 5 (Polish)**: Depends on Phase 3 and Phase 4

### Task-Level Dependencies

| Task | Depends On | Reason |
|------|-----------|--------|
| T002 | T001 | Write validator after confirming baseline |
| T003 | T001 | Subscribe to new topic after audit |
| T004 | T003 | Dispatch logic needs subscription in place |
| T005 | T002, T004 | Handler calls both validator and dispatch routing |
| T006–T009 | T002 | Tests call the new validator function |
| T010–T012 | T005 | Tests exercise the full handler including storage |
| T013 | T010–T012 | Final audit after all tests written |

### Parallel Opportunities

- T003 and T002 can run in parallel (different files)
- T006, T007, T008, T009 can all run in parallel (different test methods)
- T010, T011, T012 can all run in parallel (different test methods)

---

## Parallel Example: User Story 1

```bash
# Step 1: Run in parallel (different files, no shared dependency)
Task T002: "Add validate_biometric_reading_message() to backend/realtime/validators.py"
Task T003: "Subscribe to devices/+/reading in backend/realtime/mqtt_client.py on_connect()"

# Step 2: Sequential (T004 depends on T003 being present)
Task T004: "Add dispatch logic in backend/realtime/mqtt_client.py on_message()"

# Step 3: Sequential (T005 depends on T002 and T004)
Task T005: "Implement _handle_reading_message() in backend/realtime/mqtt_client.py"

# Step 4: Run all tests in parallel (all test different conditions of T002)
Task T006: "Test: valid 6-field payload accepted"
Task T007: "Test: missing field raises ValidationError"
Task T008: "Test: non-numeric value raises ValidationError"
Task T009: "Test: invalid timestamp raises ValidationError"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Audit (T001)
2. Complete Phase 3: User Story 1 (T002–T009)
3. **STOP and VALIDATE**: Run pytest on `BiometricReadingMQTTValidationTest`
4. Send a test MQTT message to `devices/test/reading` and verify `BiometricReading` record is created

### Incremental Delivery

1. Complete Phase 1 + Phase 3 → Raw reading pipeline live, flex-free ✅ (MVP)
2. Complete Phase 4 → Legacy payload backward-compatibility verified ✅
3. Complete Phase 5 → Audit clean, checklist complete ✅

---

## Notes

- This feature modifies exactly **3 files**: `validators.py`, `mqtt_client.py`, `test_mqtt_client.py`
- No migrations, no new Django apps, no frontend changes
- The existing session-level MQTT pipeline (`devices/+/data`) is untouched
- Flex-ignoring is passive (no explicit code) — the validator only checks declared required fields and ignores all others
- Out-of-range sensor values produce a WARNING log but are not rejected (mirrors `feature_utils.validate_sensor_ranges(warn_only=True)`)
