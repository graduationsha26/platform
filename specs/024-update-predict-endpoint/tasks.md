# Tasks: Update ML Prediction Endpoint

**Input**: Design documents from `/specs/024-update-predict-endpoint/`
**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅ | quickstart.md ✅

**Tests**: Not requested — no test tasks generated.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)

---

## Phase 1: Setup

**Purpose**: Confirm environment is ready before any code changes.

- [X] T001 Verify prerequisites: (a) `backend/inference/serializers.py` exists and contains `InferenceRequestSerializer` with `validate_sensor_data()` method; (b) `backend/inference/validators.py` exists and contains `validate_ml_input_shape(data, expected_features: int = 18)` (with 18 as default); (c) `backend/inference/services.py` exists and `PreprocessingService._preprocess_ml()` contains the comment "18 engineered features"; (d) `POST /api/inference/` is registered in `backend/tremoai_backend/urls.py` via `include('inference.urls')`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No foundational blocking tasks for this feature — it requires no migrations, no new packages, and no new Django apps. Both user stories can begin immediately after Setup.

*(Phase intentionally empty — proceed directly to user story phases.)*

---

## Phase 3: User Story 1 — Prediction Succeeds with Valid 6-Feature Input (Priority: P1) 🎯 MVP

**Goal**: Add a `len(value) != 6` count check to `InferenceRequestSerializer.validate_sensor_data()` in `backend/inference/serializers.py` (ML branch), and update all inline documentation in that file to reflect the 6-feature schema.

**Independent Test**: POST `{"sensor_data": [0.5, -0.3, 10.2, 0.05, -0.02, 0.01]}` to `POST /api/inference/` and `POST /api/inference/?model=svm`; confirm HTTP 200 with `prediction` and `severity` fields. POST `{"sensor_data": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}` to confirm degenerate-but-valid input also succeeds.

### Implementation for User Story 1

- [X] T002 [US1] Update class docstring in `backend/inference/serializers.py` (line 11): change `"Supports both ML model format (18 features) and DL model format (128x6 sequences)."` to `"Supports both ML model format (6 features) and DL model format (128x6 sequences)."`; also update `sensor_data` field `help_text` (lines 16-17): change `"Sensor data: 2D array (128x6) for DL or 1D array (18) for ML"` to `"Sensor data: 2D array (128x6) for DL or 1D array (6) for ML — [aX, aY, aZ, gX, gY, gZ]"`; also update `validate_sensor_data` docstring (lines 24-26): change `"1D array with length 18 for ML models"` to `"1D array with length 6 for ML models [aX, aY, aZ, gX, gY, gZ]"`

- [X] T003 [US1] Add 6-element count check in `validate_sensor_data()` ML branch in `backend/inference/serializers.py` (after the existing `all(isinstance(x, (int, float)) for x in value)` check, approximately line 50): add `if len(value) != 6: raise serializers.ValidationError(f"ML models require exactly 6 features [aX, aY, aZ, gX, gY, gZ], got {len(value)}")` — this is the key functional change that converts a 500 server error into a clean 400 response for wrong-count ML input

- [X] T004 [US1] Verify US1 acceptance (quickstart Scenarios 1 and 6): start Django dev server from `backend/`; POST `{"sensor_data": [0.5, -0.3, 10.2, 0.05, -0.02, 0.01]}` with a valid JWT to `/api/inference/` (RF) and `/api/inference/?model=svm`; confirm HTTP 200 with `prediction` (true/false), `severity` (0–3), and `model_used`; POST `{"sensor_data": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}` and confirm HTTP 200 (all-zeros is valid)

**Checkpoint**: US1 complete — valid 6-feature ML requests return HTTP 200 with prediction; the serializer now enforces 6-element count and rejects wrong-count requests (tested in US2).

---

## Phase 4: User Story 2 — Invalid Input Is Rejected with Clear Errors (Priority: P2)

**Goal**: Update `validate_ml_input_shape()` default in `backend/inference/validators.py` (18 → 6) and update `_preprocess_ml()` comments in `backend/inference/services.py` (both are consistency/documentation changes). Verify that invalid-feature-count requests return HTTP 400 (not 500) with an actionable error message.

**Independent Test**: POST `{"sensor_data": [0.5, -0.3, 10.2, 0.05, -0.02]}` (5 features), POST with 18 features, and POST with 7 features; confirm each returns HTTP 400 with `error_code: "INVALID_INPUT_SHAPE"` and a message containing "6 features"; confirm none returns HTTP 500.

**Note**: T005 and T006 touch different files from T002–T003 (validators.py and services.py vs serializers.py) — they can run in parallel with each other and with T002–T003 during implementation. T007 verification requires T003 to be complete first (needs the count check in place).

### Implementation for User Story 2

- [X] T005 [P] [US2] Update `validate_ml_input_shape()` in `backend/inference/validators.py` (line 9): change function signature default `expected_features: int = 18` to `expected_features: int = 6`; update inline comment (line 22): change `"ML models expect 1D array with 18 features (or 2D with shape (1, 18))"` to `"ML models expect 1D array with 6 features [aX, aY, aZ, gX, gY, gZ] (or 2D with shape (1, 6))"`

- [X] T006 [P] [US2] Update `_preprocess_ml()` in `backend/inference/services.py` (documentation only): change docstring line (approximately line 265): `"data: Input features (should be 18 features)"` to `"data: Input features (6 raw sensor features [aX, aY, aZ, gX, gY, gZ])"` ; change inline comment (approximately line 274): `"# For ML models, data should already be 18 engineered features"` to `"# For ML models, data should be 6 raw sensor features [aX, aY, aZ, gX, gY, gZ]"`

- [X] T007 [US2] Verify US2 acceptance (quickstart Scenarios 2, 3, 4, 5): POST `{"sensor_data": [0.5, -0.3, 10.2, 0.05, -0.02]}` (5 items); confirm HTTP 400 with `error_code: "INVALID_INPUT_SHAPE"` and message mentioning "6 features, got 5"; POST 18-element array; confirm HTTP 400 (not HTTP 500) with message mentioning "got 18"; POST 7-element array; confirm HTTP 400; POST `{"sensor_data": [0.5, -0.3, "bad", 0.05, -0.02, 0.01]}`; confirm HTTP 400 about non-numeric values; POST `{"sensor_data": []}`; confirm HTTP 400 about empty input

**Checkpoint**: US2 complete — all invalid-count ML requests return HTTP 400 with clear error messages; HTTP 500 no longer occurs for wrong feature count.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Backward compatibility confirmation and end-to-end validation.

- [X] T008 [P] Verify DL backward compatibility (quickstart Scenario 7): POST a 2D 128×6 array to `/api/inference/?model=lstm` or `/api/inference/?model=cnn_1d`; confirm the response is either HTTP 200 (if DL model loaded) or HTTP 400 `MODEL_NOT_FOUND` (if model file absent) — NOT a feature-count validation error; confirm the ML count check does not interfere with DL-format requests

- [X] T009 [P] Verify pre-existing model-name validation (quickstart Scenario 8): POST `{"sensor_data": [0.5, -0.3, 10.2, 0.05, -0.02, 0.01]}` to `/api/inference/?model=xgboost`; confirm HTTP 400 with `error_code: "MODEL_NOT_FOUND"` and `available_models` list — confirm this pre-existing validation is unaffected by Feature 024 changes

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **US1 (Phase 3)**: Depends on T001 (Setup) — can start immediately after
- **US2 (Phase 4)**: T005 and T006 can start immediately after T001 (different files from T002–T003); T007 depends on T003 (needs count check in place)
- **Polish (Phase 5)**: T008, T009 depend on T003 (need count check in place); can run in parallel once T003 is complete

### User Story Dependencies

- **US1 (P1)**: Independent — all tasks in `serializers.py`
- **US2 (P2)**: T005 and T006 are fully independent (different files); T007 depends on T003 (artifact must be complete)

### Within Each User Story

- T002 → T003 are sequential (both edits to `serializers.py`, run in order to avoid conflicts)
- T004 depends on T003 (functional change must be in place before verifying valid input)
- T005 [P] is independent of T002–T003 (validators.py ≠ serializers.py)
- T006 [P] is independent of T002–T003 (services.py ≠ serializers.py)
- T007 depends on T003 (wrong-count rejection requires the count check)
- T008, T009 depend on T003; can run in parallel after

### Parallel Opportunities

- T005 [P] and T006 [P] run simultaneously with T002–T003 (different files)
- T008 and T009 run in parallel after T003 (polish verifications)

---

## Parallel Example: US1 + US2 Code Changes

```bash
# T002–T003 and T005–T006 have no shared files — run them together:
Task: "Update serializers.py docstrings + add count check"    # T002 → T003
Task: "Update validators.py default (18 → 6) + comment"      # T005
Task: "Update services.py _preprocess_ml comments"            # T006
```

## Parallel Example: Polish Phase

```bash
# T008 and T009 are independent — run them together after T003:
Task: "Verify DL backward compatibility"                      # T008
Task: "Verify model-name validation unchanged"                # T009
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 3: US1 (T002 → T003 → T004)
3. **STOP and VALIDATE**: valid 6-feature requests return HTTP 200; the count check is in place
4. Demonstrate: wrong-count requests already return HTTP 400 (error handling in views.py was already there)

### Incremental Delivery

1. Phase 1 (T001) → Environment confirmed
2. Phase 3 US1 (T002–T004) → Count check added, valid 6-feature requests confirmed ✅
3. Phase 4 US2 (T005–T007) → Validators/services updated, error behavior confirmed ✅
4. Phase 5 Polish (T008–T009) → Full backward-compatibility validation ✅

### Notes

- **Only 1 functional line added**: `if len(value) != 6: raise serializers.ValidationError(...)` — all other changes are documentation
- **No migrations, packages, or Django apps** required
- **T005 and T006 are the only parallel tasks** during implementation — run them alongside T002–T003
- **Companion to Features 022 + 023**: Together, 022 + 023 + 024 complete the 6-axis ML pipeline alignment
- **Error conversion**: Feature 024 converts HTTP 500 (sklearn ValueError) into HTTP 400 (clear API error) for wrong-count ML input
