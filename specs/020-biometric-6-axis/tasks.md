# Tasks: Biometric 6-Axis Field Cleanup

**Input**: Design documents from `/specs/020-biometric-6-axis/`
**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅ | quickstart.md ✅

**Tests**: Not requested — no test tasks generated.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)

---

## Phase 1: Setup

**Purpose**: Verify all prerequisites are in place before any changes are made.

- [X] T001 Verify pending migrations exist: confirm `backend/biometrics/migrations/0002_add_biometricreading.py` and `backend/biometrics/migrations/0003_remove_flex_fields.py` are present with correct operations

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Apply the two pending migrations to create the `biometric_readings` table in its final 6-axis-only shape. This is a hard prerequisite for US1 verification.

**⚠️ CRITICAL**: US1 schema verification cannot run until this phase is complete.

- [X] T002 Apply all pending biometrics migrations (`python manage.py migrate biometrics`) to execute 0002 (create table with aX–gZ + flex fields) and 0003 (drop flex_1–flex_5) in sequence

**Checkpoint**: `biometric_readings` table now exists with exactly: `id`, `patient_id`, `timestamp`, `aX`, `aY`, `aZ`, `gX`, `gY`, `gZ`. No flex or magnetometer columns.

---

## Phase 3: User Story 1 — Accurate Data Model for Supported Sensors (Priority: P1) 🎯 MVP

**Goal**: Confirm the `biometric_readings` table in the database has exactly the 6 active sensor axes and no legacy fields.

**Independent Test**: Run `python manage.py showmigrations biometrics` — all three migrations show `[X]`. Run `python manage.py dbshell` and `\d biometric_readings` — confirm columns are exactly `id`, `patient_id`, `timestamp`, `aX`, `aY`, `aZ`, `gX`, `gY`, `gZ`.

### Implementation for User Story 1

- [X] T003 [US1] Verify migration state by running `python manage.py showmigrations biometrics` and confirming all three migrations (0001, 0002, 0003) are marked `[X]` applied
- [X] T004 [US1] Verify database schema by inspecting `biometric_readings` table columns and confirming no `mX`, `mY`, `mZ`, or `flex_*` columns exist (via `python manage.py dbshell` or equivalent DB inspection)

**Checkpoint**: US1 is complete — the `biometric_readings` table holds exactly 6 sensor axes. No legacy fields present. US1 can be demonstrated and verified independently.

---

## Phase 4: User Story 2 — Clean API Responses with 6-Axis Fields Only (Priority: P2)

**Goal**: Remove stale inline comments from `BiometricReadingSerializer` and `BiometricReadingViewSet` that reference "Feature E-2.1" and "flex_1 through flex_5". These comments are misleading — the model was designed 6-axis-only from the start; flex fields were never part of the API.

**Independent Test**: Inspect `backend/biometrics/serializers.py` (lines ~196–206) and `backend/biometrics/views.py` (lines ~209–224) — neither should mention "E-2.1", "flex", or "flex_1 through flex_5". Call `GET /api/biometric-readings/` with a valid JWT token and confirm the response contains exactly `id`, `patient_id`, `timestamp`, `aX`, `aY`, `aZ`, `gX`, `gY`, `gZ`.

### Implementation for User Story 2

- [X] T005 [P] [US2] Update `BiometricReadingSerializer` docstring in `backend/biometrics/serializers.py` (lines ~196–200): replace the stale "flex_1 through flex_5 are intentionally excluded (removed in Feature E-2.1)" line with an accurate description — "The BiometricReading model was designed with only the 6 active IMU sensor axes (aX, aY, aZ, gX, gY, gZ) from inception. No magnetometer or flex fields are part of this model."
- [X] T006 [P] [US2] Update `BiometricReadingViewSet` class docstring in `backend/biometrics/views.py` (lines ~209–224): replace "flex_1 through flex_5 are intentionally absent from all responses (removed from the model in Feature E-2.1)" with "The BiometricReadingViewSet exposes only the 6 active IMU sensor axes (aX, aY, aZ, gX, gY, gZ). No magnetometer or flex fields were ever part of the BiometricReading model."

**Checkpoint**: US2 is complete — serializer and view docstrings accurately describe the 6-axis-only model history. No misleading "E-2.1" or "flex" references remain.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: End-to-end verification of the full feature against quickstart.md scenarios.

- [X] T007 Verify `GET /api/biometric-readings/` response against quickstart.md Scenario 1 — confirm JSON contains exactly `id`, `patient_id`, `timestamp`, `aX`, `aY`, `aZ`, `gX`, `gY`, `gZ` and no other sensor fields
- [X] T008 Verify `GET /api/biometric-readings/{id}/` response against quickstart.md Scenario 2 — single record contains exactly the 6 sensor fields
- [X] T009 [P] Verify ML data pipeline is unaffected: confirm `backend/ml_data/utils/data_loader.py` still validates and drops mX/mY/mZ from the training CSV correctly (no unintended changes from this feature)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup (T001) — BLOCKS US1 schema verification
- **US1 (Phase 3)**: Depends on Foundational (T002 applied) — can begin after migrations run
- **US2 (Phase 4)**: Independent of US1 — can begin immediately after Setup (T001)
  - T005 and T006 are pure comment edits; they have no dependency on migration state
- **Polish (Phase 5)**: Depends on US1 (T003–T004) and US2 (T005–T006) complete

### User Story Dependencies

- **US1 (P1)**: Requires Foundational phase (migrations applied). No dependency on US2.
- **US2 (P2)**: Requires only Setup (Phase 1). Can run in parallel with Foundational + US1 since it edits different files (serializers.py, views.py).

### Within Each User Story

- T003 → T004 (verify migrations, then verify schema)
- T005 and T006 are fully parallel (different files)

### Parallel Opportunities

- T005 and T006 can run simultaneously (different files: serializers.py vs views.py)
- US2 (T005, T006) can run in parallel with Foundational + US1 execution (no shared file conflicts)

---

## Parallel Example: US2

```bash
# T005 and T006 have no shared files — run them together:
Task: "Update BiometricReadingSerializer docstring in backend/biometrics/serializers.py"
Task: "Update BiometricReadingViewSet docstring in backend/biometrics/views.py"
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002)
3. Complete Phase 3: US1 (T003–T004)
4. **STOP and VALIDATE**: Migration state confirmed, schema verified
5. Demonstrate: `biometric_readings` table has exactly 6 sensor axes

### Incremental Delivery

1. Phase 1 + Phase 2 → Database table is correct
2. Phase 3 (US1) → Schema verified ✅
3. Phase 4 (US2, parallel) → Comments cleaned ✅
4. Phase 5 (Polish) → End-to-end verified ✅

### Notes

- **No model changes needed** — `BiometricReading` is already correct
- **No serializer field changes needed** — `BiometricReadingSerializer.Meta.fields` is already correct
- **No URL routing changes needed** — `/api/biometric-readings/` is already registered
- **ML pipeline is intentionally untouched** — `data_loader.py` mX/mY/mZ handling is correct
- The only code changes are docstring/comment updates in two files (T005, T006)
