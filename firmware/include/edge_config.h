// edge_config.h — On-device edge-AI constants (Feature 052), COMMITTED (not secret).
//
// These are required for the edge classifier + suppression gate to compile, so they live in a
// tracked header (not in the per-user, git-ignored config.h). Each is #ifndef-guarded, so a
// config.h that defines its own value still overrides these defaults. Tune the gate params here
// or in config.h. (config.h.example documents them for reference.)
#pragma once

// ── Pipeline (must match backend/ml_models/features_lgbm.py) ──────────────────
#ifndef EDGE_FS_HZ
#define EDGE_FS_HZ            100     // native IMU rate — no on-device resampling
#endif
#ifndef EDGE_WINDOW_SIZE
#define EDGE_WINDOW_SIZE      128     // samples per window (1.28 s) == FFT length
#endif
#ifndef EDGE_FFT_SIZE
#define EDGE_FFT_SIZE         128
#endif
#ifndef EDGE_HOP
#define EDGE_HOP              10      // samples between decisions → ~100 ms (>=10 Hz)
#endif
#ifndef EDGE_N_FEATURES
#define EDGE_N_FEATURES       66
#endif
#ifndef EDGE_N_CLASS
#define EDGE_N_CLASS          3
#endif

// ── ClassificationTask (Core 0; Core 1 is saturated by Sensor+Control) ────────
#ifndef CLASSIFY_TASK_CORE
#define CLASSIFY_TASK_CORE    0
#endif
#ifndef CLASSIFY_TASK_PRIO
#define CLASSIFY_TASK_PRIO    4       // below MqttTask(5); never on the control path
#endif
#ifndef CLASSIFY_TASK_STACK
#define CLASSIFY_TASK_STACK   8192    // bytes — feature/FFT buffers are static, not stack
#endif
#ifndef CLASSIFY_PERIOD_MS
#define CLASSIFY_PERIOD_MS    100     // decision cadence (~10 Hz)
#endif

// ── Suppression gate (smoothed; FR-003a/FR-003b, SC-009) ──────────────────────
#ifndef EDGE_GATE_ENABLED
#define EDGE_GATE_ENABLED      true   // false → legacy always-on suppression (rollback)
#endif
#ifndef GATE_N_VOTE
#define GATE_N_VOTE            5      // decisions in the sliding vote window (~500 ms)
#endif
#ifndef GATE_ENGAGE_VOTES
#define GATE_ENGAGE_VOTES      4      // TREMOR votes (of N_VOTE) required to ENGAGE
#endif
#ifndef GATE_DISENGAGE_VOTES
#define GATE_DISENGAGE_VOTES   4      // non-TREMOR votes required to DISENGAGE (asymmetric)
#endif
#ifndef GATE_MIN_DWELL_MS
#define GATE_MIN_DWELL_MS      400    // minimum time between gate state changes (anti-chatter)
#endif
#ifndef GATE_RAMP_PER_S
#define GATE_RAMP_PER_S        2.0f   // suppression authority change per second (0..1 ramp)
#endif
