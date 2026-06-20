# Contract: Inference Response & Telemetry (2-class) (US2, FR-019)

Defines the externally-visible shape changes from dropping the `Voluntary` class. Backend
`inference` REST response, MQTT telemetry payload, and the frontend consumer.

## Backend REST prediction object (`backend/inference/services.py` → views/serializers)

**Before (3-class):**
```json
{
  "prediction": 1,
  "predicted_class": "Tremor",
  "probabilities": { "non_tremor": 0.10, "tremor": 0.80, "voluntary": 0.10 },
  "is_tremor": true
}
```
**After (binary):**
```json
{
  "prediction": 1,
  "predicted_class": "Tremor",
  "probabilities": { "non_tremor": 0.20, "tremor": 0.80 },
  "is_tremor": true
}
```
Rules: `prediction ∈ {0,1}`; `predicted_class ∈ {"Non-Tremor","Tremor"}`; `probabilities` has exactly
two keys summing to ~1.0; `is_tremor == (prediction == 1)`. snake_case + `{ "error": "message" }`
on failure (unchanged). `CLASS_NAMES = {0:'Non-Tremor', 1:'Tremor'}`; `proba` shape `(n,2)`.

## MQTT telemetry payload (`firmware` → backend; `task_scheduler.cpp` / `mqtt_publisher`)
- `pred_class ∈ {-1, 0, 1}` (`-1` = invalid/warm-up).
- `pred_proba` → **2** entries `[p_non_tremor, p_tremor]` (was 3).
- `pred_valid` unchanged.

## Frontend (tremor monitor component)
- Render two classes; remove/guard any `voluntary` field and any `proba[2]`/index-2 access.
- Must not crash when a third probability is absent (FR-019).

## Acceptance
- No consumer references `voluntary`/`Voluntary`/index 2 (SC-006).
- Backend `inference` remains authoritative for stored predictions (constitution); device output
  agrees with backend on identical windows (SC-009).
- Existing REST/WebSocket consumers continue to function with the 2-key object (FR-019).
