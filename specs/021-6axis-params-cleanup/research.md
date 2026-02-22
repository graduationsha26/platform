# Research: MQTT Parser and Normalization 6-Axis Cleanup (Feature 021)

**Branch**: `021-6axis-params-cleanup` | **Date**: 2026-02-18

---

## Finding 1: MQTT Parser Already Extracts Only 6 Axes (E-3.3)

**Decision**: No logic change needed to the MQTT reading handler. Comment updates only.

**Evidence**:
- `backend/realtime/mqtt_client.py` — `_handle_reading_message()` (line 305–313): creates `BiometricReading` with exactly `aX, aY, aZ, gX, gY, gZ`. No magnetometer fields extracted.
- `backend/realtime/validators.py` — `validate_biometric_reading_message()` (line 164): `required_fields = ['serial_number', 'timestamp', 'aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']`. No mX/mY/mZ.
- `backend/apps/ml/feature_utils.py` (line 25): `FEATURE_COLUMNS = ['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']` — canonical definition used by training and inference.

**Gap found**: The existing comments in `mqtt_client.py` and `validators.py` reference "flex_1 through flex_5" as the silently-ignored legacy fields. They do NOT mention mX/mY/mZ. Since the spec for feature 021 now explicitly requires that magnetometer fields are silently discarded, these comments need updating to include mX/mY/mZ in the "silently ignored" list.

**Remaining work for E-3.3**:
- `backend/realtime/mqtt_client.py`: Update `_handle_reading_message()` docstring — mention mX/mY/mZ alongside flex_1-5 as silently ignored.
- `backend/realtime/validators.py`: Update `validate_biometric_reading_message()` docstring — add mX/mY/mZ to the "Ignores (silently)" list.

---

## Finding 2: params.json Already Has 6-Axis-Only Entries (E-3.4)

**Decision**: No rebuild of params.json is needed. Current file is correct.

**Evidence** (`backend/ml_data/params.json`):
```json
{
  "features": [
    {"name": "aX", "mean": 54.17..., "std": 5220.68...},
    {"name": "aY", "mean": 5756.36..., "std": 5201.57...},
    {"name": "aZ", "mean": -13338.65..., "std": 3058.97...},
    {"name": "gX", "mean": 5002.22..., "std": 485.18...},
    {"name": "gY", "mean": -239.64..., "std": 999.92...},
    {"name": "gZ", "mean": 275.45..., "std": 3340.55...}
  ],
  "metadata": {"generated_from": "Dataset.csv", "n_samples": 27995, ...}
}
```
6 entries. No mX, mY, mZ, or flex entries.

**Generation pipeline**:
- `generate_params.py` uses `FEATURE_COLUMNS` from `feature_utils.py` — hardcoded to `['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']`.
- `normalize.py` validates exactly 6 entries at load time — rejects any file with wrong count.
- The regeneration process correctly excludes magnetometer values (they are dropped from the CSV by `data_loader.py` before reaching the feature extraction step).

**Note on large mean/std values**: The sensor values in params.json appear to be raw ADC (analog-to-digital converter) counts, not physical units (m/s²). This is consistent with the glove hardware outputting uncalibrated integer ADC readings. The normalization is still mathematically correct — it z-scores the raw counts.

**Remaining work for E-3.4**: None for the data file. Only documentation/comment updates to confirm the generation process excludes magnetometer values by design.

---

## Finding 3: Two Separate ML Pipelines — MQTT vs Inference API

**Decision**: This feature concerns the raw sensor inference pipeline (apps/ml, apps/dl). The MQTT-triggered prediction path (`ml_service.py`) uses different features entirely.

**Evidence**:
- `backend/realtime/ml_service.py` — `_extract_features()`: uses `tremor_intensity_avg`, `tremor_intensity_max`, `tremor_intensity_std`, `frequency` (4 aggregated features). Does NOT use aX/aY/aZ/gX/gY/gZ directly. Does NOT use params.json.
- `backend/apps/ml/predict.py` + `backend/apps/dl/inference.py`: use the 6-axis raw feature pipeline with params.json normalization. Called from the inference API endpoint (Feature 008).

**Implication**: E-3.3 and E-3.4 affect the raw sensor inference API path (Feature 008), not the MQTT real-time prediction path. The MQTT parser (E-3.3) determines what gets stored in `BiometricReading` records; the inference API uses those stored readings for on-demand analysis.

---

## Finding 4: Test Coverage Already Addresses Flex Field Rejection

**Decision**: No new test logic needed; comment updates only.

**Evidence** (`backend/realtime/tests/test_mqtt_client.py`):
- `test_flex_fields_accepted_in_payload`: confirms flex_1–5 are accepted in the payload without error.
- `test_flex_fields_not_stored_in_biometric_reading`: confirms flex_1–5 are never passed to `BiometricReading.objects.create()`.
- No explicit test for mX/mY/mZ handling exists — but since the validator's `required_fields` list does not include them, they are treated the same as any unknown field (silently ignored). The existing "unknown fields silently ignored" behavior covers mX/mY/mZ without needing a separate test.

---

## What Feature 021 Actually Needs to Do

| Task | File | Type | Status |
|---|---|---|---|
| Update `_handle_reading_message` docstring to mention mX/mY/mZ silently ignored | `backend/realtime/mqtt_client.py` | Comment | Needed |
| Update `validate_biometric_reading_message` docstring to include mX/mY/mZ in silently-ignored list | `backend/realtime/validators.py` | Comment | Needed |
| Verify params.json has exactly 6 entries, no magnetometer entries | `backend/ml_data/params.json` | Verification | Already correct |
| Verify generate_params.py produces 6-axis-only output | `backend/apps/ml/generate_params.py` | Verification | Already correct |
| Verify normalize.py validates exactly 6 features | `backend/apps/ml/normalize.py` | Verification | Already correct |

---

## Alternatives Considered

| Alternative | Reason Rejected |
|---|---|
| Modify validator to explicitly reject mX/mY/mZ | Unnecessary — treating them as unknown fields (silently ignored) is the correct behavior |
| Rebuild params.json from scratch | Not needed — current file has correct 6-axis-only content derived from Dataset.csv |
| Add mX/mY/mZ specific tests | Overkill — existing "unknown fields ignored" coverage handles this case implicitly |
