# Tasks: Backend Architecture Alignment

**Input**: Design documents from `specs/039-backend-arch-align/`  
**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅  
**Tests**: Not requested — no test tasks generated.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to
- Each task modifies an existing file — no new files are created.

## Path Conventions

- **Backend (Django)**: `backend/[app_name]/`, `backend/tremoai_backend/`
- **Environment**: `backend/.env.example`

---

> **Note**: No Setup or Foundational phases are needed. All infrastructure (apps,
> middleware, LOGGING dict, MQTT client, permission classes) already exists.
> Every task is a targeted modification to an existing file.

---

## Phase 1: User Story 1 — Secure the ML Inference API (Priority: P1) 🎯 MVP

**Goal**: Replace the overly-permissive `IsAuthenticated` guard on `InferenceAPIView` with `IsDoctorOrAdmin`, ensuring only doctors and admins can trigger ML predictions.

**Independent Test**: Send POST requests to `/api/inference/` with (a) a doctor JWT, (b) an admin JWT, (c) an unauthenticated request. Expect 200, 200, 401. If a non-doctor/admin role exists, expect 403.

### Implementation for User Story 1

- [x] T001 [US1] In `backend/inference/views.py` line 5, replace `from rest_framework.permissions import IsAuthenticated` with `from authentication.permissions import IsDoctorOrAdmin`; on line 41, replace `permission_classes = [IsAuthenticated]` with `permission_classes = [IsDoctorOrAdmin]`

**Checkpoint**: User Story 1 complete. `InferenceAPIView` now enforces role-based access. Verify with quickstart.md Scenario 1.

---

## Phase 2: User Story 2 — Centralize Hardware Config and Logging (Priority: P1)

**Goal**: Move MQTT broker credentials out of scattered `config()` calls into centralized `settings.py` entries, and add named loggers for `inference`, `cmg`, and `realtime` so hardware and prediction activity appears in identifiable log streams.

**Independent Test**: (a) Change `MQTT_BROKER_URL` in `backend/.env` and confirm the new value prints from `django.conf.settings` in a Django shell. (b) Call `logging.getLogger('inference').info('test')` in a Django shell and confirm the log line appears in console output and `backend/logs/django.log`.

### Implementation for User Story 2

- [x] T002 [P] [US2] In `backend/tremoai_backend/settings.py`, add three MQTT settings entries after the `SPECTACULAR_SETTINGS` block (before `LOGGING`): `MQTT_BROKER_URL = config('MQTT_BROKER_URL', default='mqtt://localhost:1883')`, `MQTT_USERNAME = config('MQTT_USERNAME', default='')`, `MQTT_PASSWORD = config('MQTT_PASSWORD', default='')`
- [x] T003 [P] [US2] In `backend/.env.example`, add the three MQTT variable placeholders with empty values and a comment: `# MQTT Broker (Bidirectional)\nMQTT_BROKER_URL=mqtt://localhost:1883\nMQTT_USERNAME=\nMQTT_PASSWORD=`
- [x] T004 [US2] In `backend/tremoai_backend/settings.py`, add three logger entries to `LOGGING['loggers']` after the existing `'biometrics'` entry: `'inference'` (handlers: console+file, level: DEBUG, propagate: False), `'cmg'` (handlers: console+file, level: DEBUG, propagate: False), `'realtime'` (handlers: console+file, level: DEBUG, propagate: False)

**Checkpoint**: User Story 2 complete. Run quickstart.md Scenarios 2 and 3 to verify.

---

## Phase 3: User Story 3 — Establish the Bidirectional MQTT Bridge (Priority: P2)

**Goal**: Migrate `MQTTClient.__init__` to read MQTT broker config from `django.conf.settings` (set by T002) instead of calling `config()` directly, completing the settings centralization and activating the `realtime` logger routing for all publish functions.

**Independent Test**: Open a Django shell, import `MQTTClient`, confirm it instantiates without error, and verify `client.broker_url` matches `settings.MQTT_BROKER_URL`. With a local broker running, call `publish_cmg_command('TEST-001', 'START')` and confirm it returns `True` and logs under `realtime.mqtt_client`.

### Implementation for User Story 3

- [x] T005 [US3] In `backend/realtime/mqtt_client.py`, inside `MQTTClient.__init__`, replace the three `config()` calls with `settings` references: add `from django.conf import settings` to the import block (if not already imported), then set `self.broker_url = settings.MQTT_BROKER_URL`, `self.username = settings.MQTT_USERNAME`, `self.password = settings.MQTT_PASSWORD`; remove the now-unused direct `config()` imports for these three variables

**Checkpoint**: User Story 3 complete. Run quickstart.md Scenario 4 to verify publish functions work and return `False` gracefully when the broker is offline.

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Final verification and consistency cleanup

- [x] T006 [P] Confirm `from decouple import config` import in `backend/realtime/mqtt_client.py` is still needed for any remaining `config()` calls in the file; if not used elsewhere, remove the import line
- [x] T007 Run all four quickstart.md verification scenarios to confirm end-to-end behavior of all three user stories

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (US1)**: No dependencies — can start immediately in parallel with Phase 2
- **Phase 2 (US2)**: No dependencies — T002 and T003 can run in parallel (different files); T004 must follow T002 (same file, `settings.py`)
- **Phase 3 (US3)**: T005 depends on T002 (reads `settings.MQTT_BROKER_URL`)
- **Phase 4 (Polish)**: T006 depends on T005; T007 depends on all prior tasks

### User Story Dependencies

- **User Story 1 (P1)**: Independent — no dependency on US2 or US3
- **User Story 2 (P1)**: Independent — no dependency on US1 or US3
- **User Story 3 (P2)**: Depends on T002 (US2, settings entries must exist before migration)

### Within Each Phase

- Phase 1: T001 (single task)
- Phase 2: T002 [P] + T003 [P] → then T004 (T002 must complete first, same file)
- Phase 3: T005 (after T002)
- Phase 4: T006 → T007

### Parallel Opportunities

- T001 (US1, `views.py`) can run in parallel with T002+T003 (US2, `settings.py` + `.env.example`)
- T002 and T003 target different files — can run in parallel with each other
- T004 and T005 both edit different files but T005 depends on T002 being done first

---

## Parallel Example

```text
# Round 1 — all independent, different files:
T001 → backend/inference/views.py      (US1)
T002 → backend/tremoai_backend/settings.py  (US2 — MQTT entries)
T003 → backend/.env.example            (US2 — env docs)

# Round 2 — after T002 completes:
T004 → backend/tremoai_backend/settings.py  (US2 — loggers)
T005 → backend/realtime/mqtt_client.py      (US3 — settings migration)

# Round 3 — polish:
T006 → backend/realtime/mqtt_client.py  (cleanup unused import)
T007 → quickstart.md verification
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete T001 (1 task, ~2 minutes)
2. **STOP and VALIDATE**: Test inference endpoint with doctor/admin/unauthenticated tokens
3. Proceed to US2 and US3

### Incremental Delivery

1. T001 → US1 done: inference endpoint secured ✅
2. T002 + T003 + T004 → US2 done: hardware config centralized, loggers active ✅
3. T005 → US3 done: MQTT client reads from settings, bidirectional bridge wired ✅
4. T006 + T007 → Polish done: cleanup + full verification ✅

### Total: 7 tasks across 3 files + 1 env file

---

## Notes

- All tasks modify existing files — no new files, no migrations, no frontend changes
- T001 is the fastest and most impactful security fix — implement first
- T002 must complete before T004 and T005 can start (settings entries must exist)
- The `realtime.mqtt_client` logger is a child of `realtime` — once T004 adds the parent logger, all existing `logger.info(...)` calls in `mqtt_client.py` route correctly without any changes to those call sites
- Existing publish functions (`publish_cmg_command`, `publish_servo_command`, `publish_pid_config`, etc.) need no modifications — they already return `False` on failure and log warnings
