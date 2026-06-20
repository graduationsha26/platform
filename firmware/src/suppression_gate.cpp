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

    // Push this cycle's vote. Invalid/warm-up -> non-tremor (default-safe).
    const uint8_t v = (d.valid && d.cls == TremorClass::TREMOR) ? 1 : 0;
    s_votes[s_vhead] = v;
    s_vhead = (s_vhead + 1) % GATE_N_VOTE;
    if (s_vcount < GATE_N_VOTE) ++s_vcount;

    int tremor_votes = 0;
    for (int i = 0; i < GATE_N_VOTE; ++i) tremor_votes += s_votes[i];
    const int nontremor_votes = s_vcount - tremor_votes;

    // State change only after the minimum dwell time (anti-chatter) and with a full window.
    const bool dwell_ok = (s_last_change_us == 0) ||
                          ((now_us - s_last_change_us) >= (uint32_t)GATE_MIN_DWELL_MS * 1000u);
    if (dwell_ok) {
        if (!s_active && s_vcount >= GATE_N_VOTE && tremor_votes >= GATE_ENGAGE_VOTES) {
            s_active = true;
            s_last_change_us = now_us;
        } else if (s_active && nontremor_votes >= GATE_DISENGAGE_VOTES) {
            s_active = false;
            s_last_change_us = now_us;
        }
    }

    // Ramp authority toward the target (smooth actuator engage/disengage).
    const float dt = (s_last_update_us == 0) ? 0.0f : (now_us - s_last_update_us) / 1e6f;
    s_last_update_us = now_us;
    const float target = s_active ? 1.0f : 0.0f;
    const float step = GATE_RAMP_PER_S * dt;
    float a = s_authority;
    if (a < target)      a = std::min(target, a + step);
    else if (a > target) a = std::max(target, a - step);

    // Derive reported state.
    Gate g;
    if (s_active)        g = (a >= 1.0f) ? Gate::ENGAGED : Gate::ENGAGING;
    else                 g = (a <= 0.0f) ? Gate::DISENGAGED : Gate::DISENGAGING;

    s_authority = a;
    s_pub_active = (a > 0.0f);
    s_pub_state = (uint8_t)g;
}

bool  gate_suppression_active() { return s_pub_active; }
float gate_authority()          { return s_authority; }
Gate  gate_state()              { return (Gate)s_pub_state; }

} // namespace edge
