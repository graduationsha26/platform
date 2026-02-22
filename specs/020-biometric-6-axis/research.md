# Research: Biometric 6-Axis Field Cleanup (Feature 020)

**Branch**: `020-biometric-6-axis` | **Date**: 2026-02-18

---

## Finding 1: mX, mY, mZ Never Existed in BiometricReading

**Decision**: No migration to remove mX/mY/mZ from `BiometricReading` is required.

**Evidence**:
- Migration `0001_initial.py` (committed): Creates only `BiometricSession`. No `BiometricReading` model at all.
- Migration `0002_add_biometricreading.py` (pending): Creates `BiometricReading` with fields: `aX, aY, aZ, gX, gY, gZ, flex_1, flex_2, flex_3, flex_4, flex_5`. **No magnetometer columns.**
- Migration `0003_remove_flex_fields.py` (pending): Removes `flex_1` through `flex_5`.
- Final schema after all migrations: exactly `aX, aY, aZ, gX, gY, gZ`.

**Conclusion**: The magnetometer fields (mX, mY, mZ) were never part of the `biometric_readings` table. The feature description ("remove mX, mY, mZ") was written against the raw training CSV, not the Django model.

---

## Finding 2: mX, mY, mZ Live Only in the ML Training CSV Pipeline

**Decision**: The ML data pipeline (`backend/ml_data/`) correctly handles mX/mY/mZ and must NOT be changed.

**Evidence**:
- `Dataset.csv`: Raw training data from the hardware has 9 sensor columns (aX, aY, aZ, gX, gY, gZ, mX, mY, mZ, Result).
- Hardware fact: Magnetometer was present on the glove hardware but disabled — all mX, mY, mZ values are `-1`.
- `backend/ml_data/utils/data_loader.py`:
  - `validate_structure()` expects mX/mY/mZ as part of CSV validation (correct — the CSV has them).
  - `drop_magnetometer_columns()` removes them before feature extraction.
  - Final ML feature matrix is shape `(N, 6)` — only the 6 active axes.

**Conclusion**: This separation is correct and intentional. The ML pipeline validates the raw CSV as-is, then drops the disabled channels. No changes needed.

---

## Finding 3: BiometricReadingSerializer Already Exposes Only 6 Axes

**Decision**: No serializer field changes needed.

**Evidence** (`backend/biometrics/serializers.py:196-206`):
```python
class BiometricReadingSerializer(serializers.ModelSerializer):
    class Meta:
        model = BiometricReading
        fields = ['id', 'patient_id', 'timestamp', 'aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']
        read_only_fields = ['id', 'patient_id', 'timestamp', 'aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']
```

**Conclusion**: Serializer is correct. Comment cleanup needed — the current docstring references "flex_1 through flex_5 are intentionally excluded (removed in Feature E-2.1)." This is stale history; the correct description is that only 6-axis fields were ever part of the serializer.

---

## Finding 4: MQTT Pipeline Already Uses 6-Axis-Only Format

**Decision**: No changes needed to MQTT client or validators.

**Evidence**:
- `backend/realtime/validators.py`: `validate_biometric_reading_message()` requires exactly `aX, aY, aZ, gX, gY, gZ`. Flex fields and unknown fields are silently ignored.
- `backend/realtime/mqtt_client.py`: `_handle_reading_message()` creates `BiometricReading` with exactly the 6 sensor fields. No magnetometer or flex references.

---

## Finding 5: API Registration is Complete

**Decision**: No URL routing changes needed.

**Evidence** (`backend/tremoai_backend/urls.py:20`):
```python
path('api/biometric-readings/', include('biometrics.reading_urls')),
```
The `BiometricReadingViewSet` is registered at `/api/biometric-readings/`.

---

## What This Feature Actually Needs to Do

Given the above findings, the actual work for feature 020 is:

1. **Run the pending migrations** (0002 + 0003) to create the `biometric_readings` table with only 6 axes.
2. **Clean up stale comments** in `serializers.py` and `views.py` that still reference "E-2.1" and "flex_1 through flex_5". Replace with accurate descriptions of the 6-axis model.
3. **No schema changes** — the model, serializer, and API are already correct.
4. **No ML pipeline changes** — the data_loader.py handling of mX/mY/mZ is intentional and correct.

---

## Alternatives Considered

| Alternative | Reason Rejected |
|---|---|
| Add mX/mY/mZ to BiometricReading then remove them | Unnecessary churn; they never belonged there |
| Change data_loader.py to remove mX/mY/mZ validation | Would break CSV loading — the CSV legitimately has those columns |
| Create a squashed migration (single migration) | Overkill; existing 2-step migration sequence is clear and correct |
