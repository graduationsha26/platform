# Research Notes: CMG PID Controller Tuning (Feature 029)

**Branch**: `029-pid-tuning` | **Date**: 2026-02-19

---

## Decision 1: Where Does the PID Control Loop Run?

**Decision**: PID computation runs on the glove's embedded firmware. The web platform manages configuration, mode control, and effectiveness monitoring only.

**Rationale**: Parkinson's tremor occurs at 4–8 Hz, requiring PID loop closure at ≥ 50 Hz to achieve effective cancellation. Network round-trip via MQTT (glove → broker → Django backend → broker → glove) introduces 20–100 ms latency at minimum, which is incompatible with a 20 ms loop period. Embedded execution is the only viable approach.

**Alternatives considered**:
- Backend-side PID (Django service): Rejected — network latency is 5–50× the required loop period.
- Hybrid (coarse on backend, fine on device): Rejected — adds complexity for zero gain in this application.

**Platform scope implications**: The platform publishes PID gains and mode commands to the device. The device applies them and reports back status and amplitude metrics. The platform never computes servo commands from IMU data.

---

## Decision 2: PID Gain Safe Operating Bounds

**Decision**: Per-axis gain bounds stored as `.env` variables, validated server-side before persisting.

| Gain | Pitch min | Pitch max | Roll min | Roll max | Unit |
|------|-----------|-----------|----------|----------|------|
| Kp   | 0.0       | 0.20      | 0.0      | 0.15     | normalized output per degree error |
| Ki   | 0.0       | 0.020     | 0.0      | 0.015    | normalized output per degree·second |
| Kd   | 0.0       | 0.050     | 0.0      | 0.040    | normalized output per degree/second |

Roll bounds are tighter than pitch because ±20° travel represents a larger fraction of full servo output per degree of error.

**Default starting values (no existing config)**:

| Axis  | Kp    | Ki    | Kd    |
|-------|-------|-------|-------|
| Pitch | 0.08  | 0.002 | 0.012 |
| Roll  | 0.06  | 0.001 | 0.008 |

These defaults follow the "30% below instability" heuristic from servo tuning literature and the Kp/Ki/Kd ≈ 1:0.025:0.15 ratio validated in gimbal stabilization research.

**Rationale for bounds**:
- Kp upper bound: values above ~0.20 (pitch) / 0.15 (roll) produce low-frequency oscillation at 4–8 Hz on typical hobby-grade servos with ±30°/±20° travel.
- Ki upper bound: must be at least two orders of magnitude below Kp ceiling; above ~0.02 causes windup-driven overshoot at tremor frequencies.
- Kd upper bound: above ~0.05 (pitch) / 0.04 (roll) amplifies IMU measurement noise into servo chatter; derivative must stay below Kp/4.

**Anti-windup**: Handled in firmware via conditional integration (freeze integrator when output is saturated in same direction as error). Not managed by the platform; documented here for completeness.

**Env variable names** (following existing `GIMBAL_RATE_LIMIT_*` pattern):
```
PID_KP_PITCH_MAX=0.20
PID_KI_PITCH_MAX=0.020
PID_KD_PITCH_MAX=0.050
PID_KP_ROLL_MAX=0.15
PID_KI_ROLL_MAX=0.015
PID_KD_ROLL_MAX=0.040
```

**Alternatives considered**:
- Hard-coded bounds in serializer: Rejected — makes them non-configurable if hardware changes.
- Single set of bounds for both axes: Rejected — roll's tighter travel requires tighter gain ceilings.

---

## Decision 3: MQTT Topic Design for PID Mode and Config

**Decision**: Two new topics following the existing three-segment `devices/{serial}/{type}` pattern.

| Topic | Direction | QoS | Retain | Purpose |
|-------|-----------|-----|--------|---------|
| `devices/{serial}/pid_config` | Platform → Device | 1 | `True` | PID gain values (desired state) |
| `devices/{serial}/pid_mode` | Platform → Device | 1 | `True` | Suppression on/off (desired state) |
| `devices/{serial}/pid_status` | Device → Platform | 0 | `False` | Current mode + amplitude metrics stream |

**Retain=True for both platform→device topics**: Both PID gains and suppression mode are desired-state configurations. An offline device must receive the latest values upon reconnect — exactly the problem MQTT retention solves. This mirrors the existing `servo_config` pattern (retained, QoS 1) from Feature 028.

**Retain=False for pid_status**: Device-to-platform status stream is a telemetry feed. A dropped frame is inconsequential since the next follows within 1 second. This mirrors the existing `servo_state` pattern.

**Three-segment topic requirement**: The existing `on_message` dispatcher in `mqtt_client.py` parses `topic_parts[2]` as the message type. Four-segment topics (e.g., `devices/{serial}/pid/config`) would break the dispatcher. All new topics use single-token third segments.

**`pid_status` payload** (device → platform):
```json
{
  "mode": "enabled",
  "session_id": "uuid-string",
  "raw_amplitude_deg": 2.4,
  "residual_amplitude_deg": 0.8,
  "timestamp": "2026-02-19T10:30:01.000Z"
}
```
- `mode`: `"enabled"`, `"disabled"`, or `"fault"` — current actual state
- `raw_amplitude_deg`: RMS tremor amplitude before suppression (degrees, rolling window)
- `residual_amplitude_deg`: RMS tremor amplitude after suppression (degrees, rolling window)
- `session_id`: UUID matching the session started by the platform (allows metric association without a DB round-trip)

**Alternatives considered**:
- Separate `pid_config` and `pid_mode` combined into one `pid_command` topic: Rejected — separating concerns makes each retained message independently meaningful; a config update should not reset mode, and a mode toggle should not accidentally push stale gains.
- `suppression_mode` instead of `pid_mode`: Rejected — `pid_` prefix namespace consistency; `suppression_mode` would be an orphan prefix.

---

## Decision 4: SuppressionMetric Storage Strategy

**Decision**: Downsample device metrics to 1 Hz before storing; use live ORM aggregation for session summaries.

**Rationale**:
- Device publishes `pid_status` at ~10 Hz. Storing every message yields 36,000 rows/hour/device. At 1 Hz, this drops to 3,600 rows/hour/device — manageable at any scale relevant to this project.
- A 1-second WebSocket delay budget absorbs store-then-broadcast latency (~5 ms per write to Supabase). No async queue needed.
- Per-session aggregate (`AVG(raw_amplitude), AVG(residual_amplitude)`) over ≤3,600 rows completes in <10 ms with a composite index on `(session_id, device_timestamp)`.

**Downsampling implementation**: In-process counter in `MQTTClient` instance (`_pid_sample_counters: dict[str, int]`), keyed by `{serial_number}:{session_id}`. Store every 10th message. Counter needs no lock (paho `on_message` is single-threaded).

**Storage pattern**: `store then broadcast` — consistent with existing `_handle_cmg_telemetry` pattern. At 1 Hz, latency is negligible.

**Retention**: 30 days, via management command `cleanup_pid_metrics` (mirrors existing `cleanup_temp_reports` pattern). Delete rows where `created_at < NOW() - 30 days`.

**Alternatives considered**:
- Store at full 10 Hz: Rejected — excessive storage for no benefit; real-time display is driven by WebSocket, not DB reads.
- Precomputed aggregate row per session: Rejected — adds complexity and consistency risk; live `Avg()` over 3,600 rows is instant.
- Forward-first async store: Rejected — at 1 Hz, store latency is negligible; keep existing pattern for consistency.

---

## Decision 5: SuppressionSession State Machine

**Decision**: Session has three states: `active`, `completed`, `interrupted`.

| State | Entered by | Transition condition |
|-------|-----------|---------------------|
| `active` | Doctor POST to start endpoint | Created on demand |
| `completed` | Doctor DELETE / stop endpoint | Normal stop, `ended_at` set |
| `interrupted` | MQTT disconnect or device fault | Device sends `mode: fault` or `pid_status` stops for >30s |

**Open session detection**: At most one `active` session per device at a time. Starting a new session while one is active automatically closes the previous one as `interrupted`.

**Gain snapshot**: At session start, snapshot the current `PIDConfig` values into `SuppressionSession` fields (`kp_pitch_snap`, etc.). This makes the session audit self-contained even if gains are later updated.

---

## Decision 6: API Structure — Extend Existing CMG App

**Decision**: All new views, serializers, and models added to existing `backend/cmg/` Django app. No new app created.

**Rationale**: Feature 029 is a direct functional extension of the CMG module. Creating a separate app would fragment PID-related models from the closely related `GimbalCalibration` and `GimbalState` models from Feature 028. The existing `cmg/` app already has the access-control helpers (`_get_accessible_patient_ids`, `_get_calibration_dict`) that PID views need to reuse.

**New URL prefix**: `/api/cmg/pid/` — keeps PID routes namespaced under CMG while separating from the existing `/api/cmg/servo/` prefix.

**Alternatives considered**:
- New `pid/` Django app: Rejected — over-modularizes a small feature set that shares models with `cmg/`.
- Merge into existing `/api/cmg/servo/` URL prefix: Rejected — PID config is conceptually distinct from servo position commands.
