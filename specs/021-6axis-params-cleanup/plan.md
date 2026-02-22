# Implementation Plan: MQTT Parser and Normalization 6-Axis Cleanup

**Branch**: `021-6axis-params-cleanup` | **Date**: 2026-02-18 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/021-6axis-params-cleanup/spec.md`

---

## Summary

Feature 021 audits and documents the 6-axis-only contract at two boundaries: (1) the MQTT reading parser that receives live glove sensor data, and (2) the normalization configuration file used by the ML inference pipeline. Research confirms both are already implemented correctly — the MQTT validator and handler extract only aX/aY/aZ/gX/gY/gZ and discard all other fields; params.json contains exactly 6-axis entries with no magnetometer or flex data.

**Remaining work**: Comment updates in `mqtt_client.py` and `validators.py` to explicitly document that mX/mY/mZ are silently ignored (current comments only mention flex_1–5), plus verification runs for the params.json generation pipeline.

---

## Technical Context

**Backend Stack**: Django 5.x + Django REST Framework + Django Channels
**Frontend Stack**: React 18+ + Vite + Tailwind CSS + Recharts
**Database**: Supabase PostgreSQL (remote)
**Authentication**: JWT (SimpleJWT) with roles (doctor/patient)
**Testing**: pytest (backend), Jest/Vitest (frontend)
**Project Type**: web (monorepo: backend/ and frontend/)
**Real-time**: Django Channels WebSocket for live tremor data
**Integration**: MQTT subscription for glove sensor data (paho-mqtt)
**AI/ML**: scikit-learn (.pkl) and TensorFlow/Keras (.h5) — both use params.json for normalization
**Performance Goals**: Standard response times; MQTT message processing < 100ms per message
**Constraints**: Local development only; no Docker/CI/CD
**Scale/Scope**: ~10 doctors, ~100 patients, continuous MQTT stream from active gloves

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Monorepo Architecture**: Changes in `backend/realtime/` and `backend/apps/ml/` — all within monorepo
- [x] **Tech Stack Immutability**: No new frameworks or libraries; uses paho-mqtt, Django validators, numpy (all already in stack)
- [x] **Database Strategy**: No schema changes; no new database entities
- [x] **Authentication**: Feature does not affect auth; BiometricReading access control unchanged
- [x] **Security-First**: No secrets or credentials involved; no hardcoded values
- [x] **Real-time Requirements**: MQTT integration is the subject of E-3.3 — uses existing MQTT + Django Channels infrastructure
- [x] **MQTT Integration**: Feature verifies and documents MQTT sensor data extraction — directly within the MQTT subscription handler
- [x] **AI Model Serving**: Feature verifies normalization config for ML inference — served via Django backend
- [x] **API Standards**: No new API endpoints; feature is internal pipeline validation
- [x] **Development Scope**: Local development only; no deployment changes

**Result**: ✅ PASS — no constitution violations

---

## Project Structure

### Documentation (this feature)

```text
specs/021-6axis-params-cleanup/
├── plan.md                          # This file
├── research.md                      # Phase 0 output
├── data-model.md                    # Phase 1 output
├── quickstart.md                    # Phase 1 output
├── contracts/
│   └── mqtt-reading-schema.yaml     # Phase 1 output — MQTT + params.json schemas
└── tasks.md                         # Phase 2 output (/speckit.tasks)
```

### Source Code (files touched by this feature)

```text
backend/
├── realtime/
│   ├── mqtt_client.py               # [COMMENT] _handle_reading_message docstring: add mX/mY/mZ to silently-ignored list
│   └── validators.py                # [COMMENT] validate_biometric_reading_message docstring: add mX/mY/mZ to Ignores section
├── apps/
│   └── ml/
│       ├── generate_params.py       # [VERIFY] Produces 6-axis-only output — no changes needed
│       ├── normalize.py             # [VERIFY] Validates exactly 6 features — no changes needed
│       └── feature_utils.py        # [VERIFY] FEATURE_COLUMNS = 6 axes — no changes needed
└── ml_data/
    └── params.json                  # [VERIFY] 6-axis entries, no magnetometer — no changes needed
```

**Files explicitly NOT touched**:
- `backend/realtime/tests/test_mqtt_client.py` — existing flex field tests cover the "unknown fields ignored" pattern; mX/mY/mZ follow the same path implicitly
- `backend/ml_data/utils/data_loader.py` — magnetometer CSV dropping is intentional and correct
- All `backend/apps/ml/predict.py`, `backend/apps/dl/inference.py` — use params.json correctly already

---

## Phase 0: Research Findings

See [research.md](research.md) for full details. Summary:

| Question | Answer |
|---|---|
| Does MQTT parser extract mX/mY/mZ? | No. Validator requires only 6 fields; extras are silently ignored. |
| Are mX/mY/mZ mentioned in MQTT comments? | No — comments only mention flex_1–5. Update needed. |
| Does params.json have magnetometer entries? | No. Exactly 6 entries (aX–gZ). Already correct. |
| Does generate_params.py exclude mX/mY/mZ? | Yes. Uses FEATURE_COLUMNS which is 6-axis-only. |
| Does normalize.py validate 6 entries? | Yes. Raises ValueError if count ≠ 6. |
| Is ml_service.py affected? | No. It uses different features (tremor_intensity, frequency — not raw axes). |

---

## Phase 1: Design & Contracts

### Data Model

See [data-model.md](data-model.md) for full entity definitions. No new entities created.

**MQTT Reading Message** — 6 required fields; mX/mY/mZ and other unknowns silently discarded.

**NormalizationConfig (params.json)** — exactly 6 entries: aX, aY, aZ, gX, gY, gZ; std > 0 required for each.

### Schemas / Contracts

See [contracts/mqtt-reading-schema.yaml](contracts/mqtt-reading-schema.yaml).

Documents:
- `MQTTReadingPayload` — required 6-axis fields; mX/mY/mZ listed as silently-ignored optionals
- `NormalizationConfig` — exactly 6 FeatureStats entries
- `FeatureStats` — name/mean/std per axis; name enum restricted to 6 active axes

### Integration Scenarios

See [quickstart.md](quickstart.md) for 5 verification scenarios covering:
1. MQTT validator accepts messages with mX/mY/mZ (silently ignored)
2. params.json has exactly 6-axis entries
3. Normalization pipeline accepts 6-axis input
4. Generator produces 6-axis-only output
5. Legacy 9-field firmware payloads accepted gracefully

---

## Implementation Tasks

Feature 021 has exactly 2 code changes (comment updates) and several verification steps.

### Task 1: Update `_handle_reading_message` Docstring

**File**: `backend/realtime/mqtt_client.py`

Current stale text (lines ~273–274):
```
Flex fields (flex_1-flex_5) are silently ignored if present in the payload
— they are never read or stored (Feature E-2.4).
```

Target:
```
Flex fields (flex_1–flex_5) and magnetometer fields (mX, mY, mZ) are
silently ignored if present in the payload — they are never read or stored.
```

### Task 2: Update `validate_biometric_reading_message` Docstring

**File**: `backend/realtime/validators.py`

Current "Ignores (silently)" section (lines ~149–151):
```
- flex_1 through flex_5 (removed from hardware; may appear in legacy payloads)
- Any other unknown fields
```

Target — add mX/mY/mZ explicitly:
```
- mX, mY, mZ (magnetometer disabled in hardware; constant -1 value; never extracted)
- flex_1 through flex_5 (flex sensors removed from hardware; may appear in legacy payloads)
- Any other unknown fields
```

Also update the module-level docstring in `validators.py` (lines ~11–16) to mention mX/mY/mZ alongside flex fields.

### Task 3: Verify params.json

Run verification to confirm current params.json meets the spec:
```bash
cd backend
python apps/ml/generate_params.py --verify --output ml_data/params.json
```

### Task 4: Verify Normalization Pipeline

Run the normalization smoke test from quickstart.md Scenario 3 to confirm the 6-axis pipeline works end-to-end.

---

## Complexity Tracking

No constitution violations. No new complexity added — this is a documentation and verification feature.
