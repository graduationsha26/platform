# Tasks: MQTT Parser and Normalization 6-Axis Cleanup

**Input**: Design documents from `/specs/021-6axis-params-cleanup/`
**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅ | quickstart.md ✅

**Tests**: Not requested — no test tasks generated.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)

---

## Phase 1: Setup

**Purpose**: Confirm environment is ready and all relevant files are in their expected state before any edits.

- [X] T001 Verify the four key files exist and contain expected content: `backend/realtime/mqtt_client.py` (has `_handle_reading_message`), `backend/realtime/validators.py` (has `validate_biometric_reading_message`), `backend/apps/ml/generate_params.py`, and `backend/ml_data/params.json`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No foundational blocking tasks for this feature — it requires no migrations, no new packages, and no new files. The two user stories can begin immediately after Setup.

*(Phase intentionally empty — proceed directly to user story phases.)*

---

## Phase 3: User Story 1 — MQTT Messages Parsed for 6 Active Axes Only (Priority: P1) 🎯 MVP

**Goal**: Update inline documentation in the MQTT client and validator to explicitly state that magnetometer fields (mX, mY, mZ) are silently discarded alongside flex_1–5, then verify the validator accepts payloads containing these fields.

**Independent Test**: Run quickstart.md Scenario 1 — call `validate_biometric_reading_message` with a 9-field payload (6 active + mX, mY, mZ = −1) and confirm no `ValidationError` is raised. Inspect the docstrings in `mqtt_client.py` and `validators.py` to confirm mX/mY/mZ appear in the silently-ignored lists.

### Implementation for User Story 1

- [X] T002 [P] [US1] Update `_handle_reading_message` docstring in `backend/realtime/mqtt_client.py` (lines ~273–274): change "Flex fields (flex_1-flex_5) are silently ignored if present in the payload — they are never read or stored (Feature E-2.4)." to "Flex fields (flex_1–flex_5) and magnetometer fields (mX, mY, mZ) are silently ignored if present in the payload — they are never read or stored."
- [X] T003 [P] [US1] Update `validate_biometric_reading_message` docstring in `backend/realtime/validators.py`: (a) in the "Ignores (silently)" block (lines ~149–151), add "mX, mY, mZ (magnetometer disabled in hardware; constant −1 value; never extracted)" as the first ignored-field entry above flex_1–5; (b) in the module-level docstring audit comment (lines ~11–16), mention that mX/mY/mZ are also not referenced in this module
- [X] T004 [US1] Verify US1 acceptance: run quickstart.md Scenario 1 — call `validate_biometric_reading_message` with a payload containing aX, aY, aZ, gX, gY, gZ plus mX=−1, mY=−1, mZ=−1; confirm no exception is raised and the function returns without error

**Checkpoint**: US1 complete — MQTT parser docstrings accurately document mX/mY/mZ as silently ignored. Validator passes for 9-field legacy payloads.

---

## Phase 4: User Story 2 — Normalization Parameters Defined for 6 Axes Only (Priority: P2)

**Goal**: Verify that `params.json` contains exactly 6-axis entries with no magnetometer data, and that the generation pipeline produces correctly scoped output.

**Independent Test**: Run `python apps/ml/generate_params.py --verify --output ml_data/params.json` from `backend/` — exit code 0, output shows 6 features with names aX, aY, aZ, gX, gY, gZ. Also run quickstart.md Scenario 2 (inspect file) and Scenario 3 (normalize a 6-axis reading).

### Implementation for User Story 2

- [X] T005 [US2] Verify `backend/ml_data/params.json` content: run `python apps/ml/generate_params.py --verify --output ml_data/params.json` from the `backend/` directory and confirm exit code 0, feature count = 6, feature names = [aX, aY, aZ, gX, gY, gZ], and no mX/mY/mZ entries present
- [X] T006 [P] [US2] Verify normalization pipeline end-to-end: run quickstart.md Scenario 3 in the Django shell — load params, normalize a 6-axis numpy array `[0.12, -0.05, 9.81, 1.23, -0.44, 0.09]`, confirm result shape is `(6,)` with no errors
- [X] T007 [P] [US2] Verify params.json generator produces 6-axis-only output: run quickstart.md Scenario 4 — execute `python apps/ml/generate_params.py --dataset Dataset.csv --output ml_data/params_test.json` from `backend/` and inspect the generated file to confirm it has exactly 6 entries (aX–gZ) with no magnetometer fields

**Checkpoint**: US2 complete — params.json is verified 6-axis-only; generator confirmed correct; normalization pipeline operates cleanly on 6-axis input.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: End-to-end verification covering the legacy firmware scenario from quickstart.md and a final scan for any remaining stale references.

- [X] T008 Verify legacy firmware compatibility: run quickstart.md Scenario 5 — call `validate_biometric_reading_message` with a payload tagged as LEGACYDEVICE01 containing all 6 active axes plus mX=−1, mY=−1, mZ=−1; confirm the validator accepts it without raising `ValidationError`
- [X] T009 [P] Scan for any remaining stale mX/mY/mZ references in MQTT/normalization code: search `backend/realtime/` and `backend/apps/ml/` for any string `mX` or `mY` or `mZ` that appears in non-comment code (i.e., not in docstrings, not in `data_loader.py` which handles them intentionally) and confirm none exist

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **US1 (Phase 3)**: Depends on Setup (T001) — can start immediately after
- **US2 (Phase 4)**: Depends on Setup (T001) — fully independent of US1; can run in parallel
- **Polish (Phase 5)**: Depends on US1 complete (T004) for T008; T009 can run any time after Setup

### User Story Dependencies

- **US1 (P1)**: Independent — pure documentation edits in realtime/ files
- **US2 (P2)**: Independent — pure verification of ml_data/ and apps/ml/ files; no shared files with US1

### Within Each User Story

- T002 and T003 are fully parallel (different files: mqtt_client.py vs validators.py)
- T004 depends on T003 (needs validator docstring updated before verifying it)
- T005, T006, T007 are independent verification steps — T006 and T007 can run in parallel
- T008 depends on T003 (validator must be correct before testing legacy payload acceptance)

### Parallel Opportunities

- T002 and T003 run simultaneously (different files)
- T005, T006, T007 all verify independent components — T006 + T007 can run together
- US1 and US2 entire phases can be worked in parallel by different agents

---

## Parallel Example: US1

```bash
# T002 and T003 have no shared files — run them together:
Task: "Update _handle_reading_message docstring in backend/realtime/mqtt_client.py"
Task: "Update validate_biometric_reading_message docstring in backend/realtime/validators.py"
```

## Parallel Example: US2

```bash
# T006 and T007 verify independent components — run them together:
Task: "Verify normalization pipeline (Scenario 3) via Django shell"
Task: "Verify generator produces 6-axis output (Scenario 4) via generate_params.py"
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 3: US1 (T002, T003 in parallel → T004)
3. **STOP and VALIDATE**: Docstrings updated; validator accepts mX/mY/mZ payloads
4. Demonstrate: MQTT parser explicitly documents 6-axis-only extraction

### Incremental Delivery

1. Phase 1 (T001) → Environment confirmed
2. Phase 3 US1 (T002–T004) → MQTT parser documented ✅
3. Phase 4 US2 (T005–T007) → params.json verified ✅
4. Phase 5 Polish (T008–T009) → Legacy payloads verified; no stale references ✅

### Notes

- **Only 2 code edits** (T002, T003 — docstring-only changes in different files)
- **All other tasks are verification steps** — no logic changes needed
- **No new migrations, packages, or files** required
- **ML data pipeline (`data_loader.py`) is intentionally untouched** — its mX/mY/mZ handling is correct
- T007 generates `ml_data/params_test.json` as a temporary output — can be deleted after verification
