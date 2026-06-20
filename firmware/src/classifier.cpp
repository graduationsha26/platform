// classifier.cpp — Flat-array LightGBM interpreter + sigmoid (Feature 053 — BINARY).
//
// Parity contract with the Python model (see contracts/binary-model-export-format.md):
//   * Numerical split: go LEFT iff  x <= threshold  (LightGBM default; non-finite -> default_left).
//   * Binary: ONE tree series — all trees sum into one raw score:
//       raw = init_score[0] + sum(leaf);  p_tremor = sigmoid(raw).
//   * proba = {1 - p_tremor, p_tremor};  class = (p_tremor >= 0.5) ? TREMOR : NON_TREMOR.

#include "classifier.h"
#include "tremor_model.h"

#include <cmath>

namespace edge {

namespace tm = tremor_model;

Decision classify_features(const float feat[N_FEATURES]) {
    float raw = tm::init_score[0];

    for (int t = 0; t < tm::NUM_TREES; ++t) {
        int node = tm::tree_root[t];
        while (tm::feature[node] >= 0) {                 // internal node
            const float x = feat[tm::feature[node]];
            bool go_left;
            if (std::isfinite(x)) go_left = (x <= tm::threshold[node]);
            else                  go_left = (tm::default_left[node] != 0);
            node = go_left ? tm::left[node] : tm::right[node];
        }
        raw += tm::leaf_value[node];                      // leaf (single series, t % 1 == 0)
    }

    const float p_tremor = 1.0f / (1.0f + std::exp(-raw));   // sigmoid

    Decision d{};
    d.proba[0] = 1.0f - p_tremor;     // P(Non-Tremor)
    d.proba[1] = p_tremor;            // P(Tremor)
    d.cls = (p_tremor >= 0.5f) ? TremorClass::TREMOR : TremorClass::NON_TREMOR;
    d.t_decision_us = 0;
    d.valid = true;
    return d;
}

Decision classify_current_window() {
    Decision d{};
    d.valid = false;
    if (!edge_window_ready()) return d;
    float feat[N_FEATURES];
    if (!edge_extract_features(feat)) return d;
    return classify_features(feat);
}

} // namespace edge
