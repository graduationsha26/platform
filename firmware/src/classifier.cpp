// classifier.cpp — Flat-array LightGBM interpreter + softmax (Feature 052).
//
// Parity contract with the Python model (see contracts/model-export-format.md):
//   * Numerical split: go LEFT iff  x <= threshold  (LightGBM default; non-finite -> default_left).
//   * Multiclass: tree t contributes to class (t % NUM_CLASS); raw[c] = init_score[c] + sum leaves.
//   * proba = softmax(raw - max(raw)); class = argmax(raw).

#include "classifier.h"
#include "tremor_model.h"

#include <cmath>

namespace edge {

namespace tm = tremor_model;

Decision classify_features(const float feat[N_FEATURES]) {
    float raw[tm::NUM_CLASS];
    for (int c = 0; c < tm::NUM_CLASS; ++c) raw[c] = tm::init_score[c];

    for (int t = 0; t < tm::NUM_TREES; ++t) {
        int node = tm::tree_root[t];
        while (tm::feature[node] >= 0) {                 // internal node
            const float x = feat[tm::feature[node]];
            bool go_left;
            if (std::isfinite(x)) go_left = (x <= tm::threshold[node]);
            else                  go_left = (tm::default_left[node] != 0);
            node = go_left ? tm::left[node] : tm::right[node];
        }
        raw[t % tm::NUM_CLASS] += tm::leaf_value[node];   // leaf
    }

    // numerically-stable softmax
    float m = raw[0];
    for (int c = 1; c < tm::NUM_CLASS; ++c) if (raw[c] > m) m = raw[c];
    float sum = 0.0f;
    float e[tm::NUM_CLASS];
    for (int c = 0; c < tm::NUM_CLASS; ++c) { e[c] = std::exp(raw[c] - m); sum += e[c]; }

    Decision d{};
    int best = 0;
    for (int c = 0; c < tm::NUM_CLASS; ++c) {
        d.proba[c] = e[c] / sum;
        if (raw[c] > raw[best]) best = c;
    }
    d.cls = static_cast<TremorClass>(best);
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
