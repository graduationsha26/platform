// suppression_gate.h — Smoothed Tremor-gated suppression (Feature 052, FR-003a/FR-003b, SC-009).
//
// Converts the stream of on-device class decisions into a SAFE, PROPORTIONAL authority signal for
// the PID suppression (Feature 053): the Tremor probability is mapped through a low-confidence
// floor + full-authority ceiling to a [0,1] target, then ramped (GATE_RAMP_PER_S) so the actuators
// never toggle per-cycle when the classifier oscillates near the boundary. Mild tremor -> gentle
// correction; strong tremor -> full authority. Replaces the earlier vote-based binary gate.
//
// Single-writer (ClassificationTask, Core 0 via gate_update) / single-reader (ControlTask,
// Core 1 via gate_authority/gate_suppression_active). Published outputs are 32-bit volatiles
// (atomic single load/store on Xtensa).
#pragma once

#include <cstdint>
#include "classifier.h"

namespace edge {

enum class Gate : uint8_t { DISENGAGED, ENGAGING, ENGAGED, DISENGAGING };

// Reset gate to a safe (disengaged) state. Call at boot / after calibration.
void gate_reset();

// Feed one decision (called by ClassificationTask each cycle). `now_us` = micros().
// Invalid/warm-up decisions count as non-tremor (default-safe: never engage from unknown).
void gate_update(const Decision& d, uint32_t now_us);

// Read by ControlTask (200 Hz). Authority in [0,1] ramps smoothly on engage/disengage.
bool  gate_suppression_active();   // true once engaged (authority > 0)
float gate_authority();            // 0.0 = neutral .. 1.0 = full PID authority
Gate  gate_state();

} // namespace edge
