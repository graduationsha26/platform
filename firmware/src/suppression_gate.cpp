// suppression_gate.cpp — Smoothed Tremor-gated suppression (Feature 052).
// See suppression_gate.h and specs/052-edge-ai-inference/research.md §7.

#include "suppression_gate.h"
#include "config.h"
#include "edge_config.h"   // 052: GATE_* / EDGE_GATE_ENABLED defaults (committed)

#include <algorithm>

namespace edge {

// ── Internal state (written only by gate_update / gate_reset) ─────────────────
static uint8_t  s_votes[GATE_N_VOTE];      // 1 = Tremor, 0 = non-Tremor
static int      s_vhead = 0;
static int      s_vcount = 0;
static bool     s_active = false;
static uint32_t s_last_change_us = 0;
static uint32_t s_last_update_us = 0;

// ── Published outputs (read cross-core by ControlTask) ────────────────────────
static volatile float s_authority = 0.0f;
static volatile bool  s_pub_active = false;
static volatile uint8_t s_pub_state = (uint8_t)Gate::DISENGAGED;

void gate_reset() {
    for (int i = 0; i < GATE_N_VOTE; ++i) s_votes[i] = 0;
    s_vhead = 0;
    s_vcount = 0;
    s_active = false;
    s_last_change_us = 0;
    s_last_update_us = 0;
    if (!EDGE_GATE_ENABLED) {
        // Rollback: behave like the legacy unconditional always-on suppression from boot.
        s_active = true;
        s_authority = 1.0f;
        s_pub_active = true;
        s_pub_state = (uint8_t)Gate::ENGAGED;
    } else {
        s_authority = 0.0f;
        s_pub_active = false;
        s_pub_state = (uint8_t)Gate::DISENGAGED;
    }
}

void gate_update(const Decision& d, uint32_t now_us) {
    // Rollback path: gate disabled -> behave like the legacy always-on suppression.
    if (!EDGE_GATE_ENABLED) {
        s_active = true;
        s_authority = 1.0f;
        s_pub_active = true;
        s_pub_state = (uint8_t)Gate::ENGAGED;
        return;
    }

    // Feature 053 — PROPORTIONAL engagement: authority target scales with the Tremor probability.
    //   invalid/warm-up -> 0 (default-safe; never engage from unknown).
    //   p <= GATE_P_LO  -> 0 (low-confidence floor; no dither from classifier noise).
    //   p >= GATE_P_HI  -> 1 (full authority).
    //   between         -> linear.
    float target = 0.0f;
    if (d.valid) {
        const float p = d.proba[(int)TremorClass::TREMOR];   // proba[1] = P(Tremor)
        target = (p - GATE_P_LO) / (GATE_P_HI - GATE_P_LO);
        target = std::min(1.0f, std::max(0.0f, target));
    }
    s_active = (target > 0.0f);

    // Ramp authority toward the target (smooth actuator engage/disengage; the ramp + floor are the
    // anti-chatter mechanism now — a probability hovering near the boundary cannot toggle per-cycle).
    const float dt = (s_last_update_us == 0) ? 0.0f : (now_us - s_last_update_us) / 1e6f;
    s_last_update_us = now_us;
    const float step = GATE_RAMP_PER_S * dt;
    float a = s_authority;
    if (a < target)      a = std::min(target, a + step);
    else if (a > target) a = std::max(target, a - step);

    // Derive reported state from authority vs. its target.
    Gate g;
    if (a >= 0.999f)        g = Gate::ENGAGED;
    else if (a <= 0.001f)   g = Gate::DISENGAGED;
    else                    g = (target > a) ? Gate::ENGAGING : Gate::DISENGAGING;

    s_authority = a;
    s_pub_active = (a > 0.0f);
    s_pub_state = (uint8_t)g;
}

bool  gate_suppression_active() { return s_pub_active; }
float gate_authority()          { return s_authority; }
Gate  gate_state()              { return (Gate)s_pub_state; }

} // namespace edge
