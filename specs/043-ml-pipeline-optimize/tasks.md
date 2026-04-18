# Tasks: ML Pipeline Optimization & Confidence Scoring

**Input**: Design documents from `/specs/043-ml-pipeline-optimize/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, quickstart.md ✅  
**Tests**: Not requested — no test tasks included.  
**Scope**: Backend-only. 4 files modified, 2 scripts executed, v3 model artifacts committed. No frontend/firmware/database changes.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no blocking dependencies)
- **[US1]**: Belongs to User Story 1 — Reduce Window Memory & Retrain
- **[US2]**: Belongs to User Story 2 — Implement Confidence Scoring in Live Test
- All paths are relative to the repository root

---

## Phase 1: Setup — Version Control Prerequisite

**Purpose**: Confirm `.gitignore` allows v3 model artifacts to be committed before any pipeline work begins (FR-009). Already updated in `/speckit.clarify` — this task audits the result.

- [x] T001 Audit `.gitignore` at repo root — confirm that all three of the following rules are commented out: `backend/ml_models/models/*.pkl`, `backend/ml_models/models/*.json`, and the `backend/models/*.pkl` / `backend/models/*.h5` blocks; if any are still active (not commented), comment them out now

**Checkpoint**: `.gitignore` no longer excludes `.pkl`, `.h5`, or JSON files under `backend/ml_models/models/`. Model artifacts can be staged with `git add`.

---

## Phase 2: Foundational — v3 Model Production

**Purpose**: Produce the v3 model artifact set that BOTH user stories depend on. US1 requires it for the inference service; US2 requires it for live test default arguments and correct scaler normalization.

**⚠️ CRITICAL**: Neither US1 nor US2 implementation can be fully validated until T005 completes and `rf_model_v3.pkl`, `rf_model_v3_scaler.pkl`, and `rf_model_v3.json` exist in `backend/ml_models/models/`.

- [x] T002 In `backend/ml_data/scripts/5_aggregate_and_extract.py`, change line 56 from `WINDOW_SIZE = 200` to `WINDOW_SIZE = 100` and line 57 from `STRIDE = 30` to `STRIDE = 15`; leave all other constants (`SAMPLING_RATE_HZ`, `AXIS_NAMES`, `ACCEL_SENSITIVITY`, `GYRO_SENSITIVITY`, `GRAVITY_MS2`) unchanged

- [x] T003 [P] In `backend/ml_models/scripts/train_random_forest.py`, change line 45 from `MODEL_VERSION = 2` to `MODEL_VERSION = 3`; leave all other training parameters (GridSearchCV grid, cross-validation folds, StandardScaler usage) unchanged

- [x] T004 Execute `python backend/ml_data/scripts/5_aggregate_and_extract.py` from the repository root — confirm it completes without error and that `backend/ml_data/processed/X_features.npy` and `backend/ml_data/processed/y_labels.npy` are updated (check file modification timestamp); depends on T002

- [x] T005 Execute `python backend/ml_models/scripts/train_random_forest.py` from the repository root — confirm it completes without error and that the following four files are created in `backend/ml_models/models/`: `rf_model_v3.pkl`, `rf_model_v3_scaler.pkl`, `rf_model_v3.json`, `rf_model_metrics_v3.json`; depends on T003 + T004

**Checkpoint**: Four v3 artifacts exist in `backend/ml_models/models/`. US1 and US2 implementation can now proceed in parallel.

---

## Phase 3: User Story 1 — Reduce Window Memory & Retrain (Priority: P1) 🎯

**Goal**: Update the inference service to load the v3 model and scaler as its active classification assets, so all API-served predictions use the optimized 100-sample window model.

**Independent Test**: Run the Django shell command: `from inference.services import ModelCache; cache = ModelCache(); m, meta, scaler = cache.get_model('rf'); print(meta['pipeline_params']['window_size'], scaler is not None)`. Expected output: `100 True`. No FileNotFoundError, no shape error.

### Implementation

- [x] T006 [P] [US1] In `backend/inference/services.py`, locate `model_map` (around line 185) and change the `'rf'` entry from `settings.ML_MODELS_DIR / 'rf_model_v2.pkl'` to `settings.ML_MODELS_DIR / 'rf_model_v3.pkl'`; then locate `metadata_map` (around line 201) and change the `'rf'` entry from `settings.ML_MODELS_DIR / 'rf_model_v2.json'` to `settings.ML_MODELS_DIR / 'rf_model_v3.json'`; no other changes to this file

- [x] T007 [US1] Verify inference service loads v3 correctly — run: `cd backend && python manage.py shell -c "from inference.services import ModelCache; cache = ModelCache(); m, meta, scaler = cache.get_model('rf'); print('window_size:', meta['pipeline_params']['window_size']); print('stride:', meta['pipeline_params']['stride']); print('scaler loaded:', scaler is not None)"` — confirm output shows `window_size: 100`, `stride: 15`, `scaler loaded: True`

**Checkpoint**: Inference service serves predictions from rf_model_v3. US1 is fully implemented and independently verifiable.

---

## Phase 4: User Story 2 — Implement Confidence Scoring in Live Test (Priority: P1)

**Goal**: Update `backend/live_glove_test.py` so every prediction line includes a millisecond timestamp, state emoji, state label + class index, and confidence percentage — matching the exact format `[HH:MM:SS.mmm] ✅ NORMAL (0) | Confidence: XX.X%`.

**Independent Test**: Run `python backend/live_glove_test.py` against the hardware glove or MQTT replay. Observe terminal output for 60 seconds. Confirm: every line matches the exact format, ✅ appears only for NORMAL, ⚠️ appears only for TREMOR, all lines include `Confidence: XX.X%`, no line is missing a confidence value.

### Implementation

- [x] T008 [P] [US2] In `backend/live_glove_test.py`: (1) change `WINDOW_SIZE = 200` → `WINDOW_SIZE = 100` (line 53); (2) change the `--model` argument default from `os.path.join(_models_dir, 'rf_model_v2.pkl')` to `os.path.join(_models_dir, 'rf_model_v3.pkl')` (~line 92); (3) change the `--scaler` argument default from `os.path.join(_models_dir, 'rf_model_v2_scaler.pkl')` to `os.path.join(_models_dir, 'rf_model_v3_scaler.pkl')` (~line 97)

- [x] T009 [US2] In `backend/live_glove_test.py`, locate the predict call (~line 192: `pred = model.predict(feature_scaled)[0]`) and replace it with the following three lines:
  ```python
  probs = model.predict_proba(feature_scaled)[0]  # shape (2,): [P(NORMAL), P(TREMOR)]
  pred = int(probs.argmax())
  confidence = probs[pred] * 100
  ```
  depends on T008

- [x] T010 [US2] In `backend/live_glove_test.py`, replace the print block (~lines 196-200) with:
  ```python
  ts = datetime.now().strftime('%H:%M:%S.%f')[:12]
  if pred == 0:
      print(f'[{ts}] ✅ NORMAL (0) | Confidence: {confidence:.1f}%')
  else:
      print(f'[{ts}] ⚠️ TREMOR (1) | Confidence: {confidence:.1f}%')
  ```
  Also verify that `from datetime import datetime` is present at the top of the file (add it if missing); depends on T009

**Checkpoint**: Live test prints confidence-scored, formatted output on every prediction. US2 is fully implemented and independently verifiable.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Commit v3 artifacts, audit for stale v2 references, and confirm metadata correctness.

- [x] T011 [P] Commit v3 model artifacts to git — run: `git add backend/ml_models/models/rf_model_v3.pkl backend/ml_models/models/rf_model_v3_scaler.pkl backend/ml_models/models/rf_model_v3.json backend/ml_models/models/rf_model_metrics_v3.json` — then run `git status` and confirm all four files show as "Changes to be committed" (not listed under "Ignored files" or absent)

- [x] T012 [P] Audit stale v2 references — run `grep -r "rf_model_v2" backend/inference/services.py backend/live_glove_test.py` and confirm zero matches; if any match is found, locate and update the remaining reference

- [x] T013 Verify v3 metadata correctness — run:
  ```bash
  python -c "
  import json
  with open('backend/ml_models/models/rf_model_v3.json') as f:
      m = json.load(f)
  pp = m['pipeline_params']
  assert pp['window_size'] == 100, f'window_size={pp[\"window_size\"]}'
  assert pp['stride'] == 15, f'stride={pp[\"stride\"]}'
  assert m['scaler_file'] == 'rf_model_v3_scaler.pkl', f'scaler={m[\"scaler_file\"]}'
  print('✅ v3 metadata OK — window_size=100, stride=15, scaler=rf_model_v3_scaler.pkl')
  "
  ```
  Confirm the `✅ v3 metadata OK` line prints without AssertionError

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 checkpoint — BLOCKS both US1 and US2 validation
  - T002 and T003 can run in parallel (different files)
  - T004 must follow T002; T005 must follow T003 + T004
- **US1 (Phase 3)**: Must wait for T005 (v3 artifacts must exist)
- **US2 (Phase 4)**: Must wait for T005 (v3 scaler needed for correct normalization); T006 and T008 can run in parallel (different files)
- **Polish (Phase 5)**: T011 and T012 require T005 complete; T013 requires T005; all three can run in parallel

### Within User Stories

```
T002 ──────────────────────────> T004 ──> T005
T003 [P] ─────────────────────────────> T005
                                    T005 ──> T006 [P] ──> T007   (US1)
                                    T005 ──> T008 [P] ──> T009 ──> T010  (US2)
                                    T005 ──> T011 [P]             (Polish)
                                    T005 ──> T012 [P]             (Polish)
                                            T007 + T010 ──> T013  (Polish)
```

---

## Parallel Opportunities

```bash
# Phase 2 — T002 and T003 are independent edits:
Task T002: Update backend/ml_data/scripts/5_aggregate_and_extract.py (Window, Stride)
Task T003: Update backend/ml_models/scripts/train_random_forest.py (MODEL_VERSION)

# After T005 completes — US1 and US2 implementation can run in parallel:
Task T006: Update backend/inference/services.py (model paths → v3)
Task T008: Update backend/live_glove_test.py (window size, model paths)

# Phase 5 — all three polish tasks can run in parallel:
Task T011: git add v3 model artifacts
Task T012: grep audit for stale v2 references
# Then T013 after T011+T012
```

---

## Implementation Strategy

### MVP: US1 First

1. Complete T001 (Setup)
2. Complete T002 → T004 → T005 (Foundational); T003 parallel with T002
3. Complete T006 → T007 (US1)
4. **STOP and VALIDATE**: `from inference.services import ModelCache` shell check confirms v3 loaded
5. Continue to US2 (T008 → T009 → T010)
6. Run T011 + T012 + T013 (Polish)
7. **Done**

### Notes

- `cmg.cpp` and all firmware files require **zero changes**
- Django REST API, WebSocket consumers, MQTT handlers, and frontend require **zero changes**
- The scaler path in `services.py` is self-referential: the training script writes `scaler_file` into `rf_model_v3.json`; the inference service reads it dynamically — no explicit scaler path entry needed in `services.py`
- `predict_proba()` is natively supported by `RandomForestClassifier` — no additional configuration required
- If `from datetime import datetime` is already in `live_glove_test.py`, T010 does not add a duplicate import
