// classifier.h — On-device tremor classifier (Feature 052).
//
// Runs the transpiled LightGBM flat-array interpreter (tremor_model) on the 66-feature vector
// and returns a 3-class decision. Canonical mapping is locked here and must never invert.
#pragma once

#include <cstdint>
#include "edge_features.h"

namespace edge {

// Canonical class mapping — identical to backend training (Control=0, Parkinson=1, Voluntary=2).
enum class TremorClass : uint8_t { NON_TREMOR = 0, TREMOR = 1, VOLUNTARY = 2 };
static_assert(static_cast<uint8_t>(TremorClass::NON_TREMOR) == 0, "mapping must not invert");
static_assert(static_cast<uint8_t>(TremorClass::TREMOR)     == 1, "mapping must not invert");
static_assert(static_cast<uint8_t>(TremorClass::VOLUNTARY)  == 2, "mapping must not invert");

struct Decision {
    TremorClass cls;
    float       proba[3];     // softmax, sums ~1.0  (index 0=Non-Tremor,1=Tremor,2=Voluntary)
    uint32_t    t_decision_us; // stamped by the caller (0 here)
    bool        valid;        // false during warm-up / invalid window
};

// Run the interpreter + softmax on a 66-feature vector.
Decision classify_features(const float feat[N_FEATURES]);

// Convenience: window-ready? -> extract -> classify. Sets valid=false if not ready / invalid.
Decision classify_current_window();

} // namespace edge
