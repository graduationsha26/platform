// parity_shim.cpp — host C-ABI shim exposing the firmware edge engine to the Python parity
// harness (Feature 052). Lets parity_harness.py (via ctypes) stream a recording through the
// SAME C code that runs on the ESP32 and compare features/predictions to features_lgbm.
//
// Build a shared library on a host with a C++ compiler (none on this dev box → Layer B skips):
//
//   g++ -O2 -std=c++17 -I firmware/include -shared -fPIC \
//       firmware/src/edge_features.cpp firmware/src/tremor_model.cpp \
//       firmware/src/classifier.cpp backend/ml_models/parity_shim.cpp -o edge_parity.so
//
//   (MSVC: cl /O2 /std:c++17 /I firmware\include /LD firmware\src\edge_features.cpp ^
//          firmware\src\tremor_model.cpp firmware\src\classifier.cpp ^
//          backend\ml_models\parity_shim.cpp /Fe:edge_parity.dll)
//
// Then extend parity_harness.run_c_parity() to load the library and:
//   1) edge_reset_c(); for each resampled sample of a held-out recording: edge_push_c(sample);
//      after warm-up, edge_features_c(out) and compare `out` to features_lgbm on the same window.
//   2) edge_predict_c(feat, proba) and compare to the Python model.

#include "edge_features.h"
#include "classifier.h"

extern "C" {

void edge_reset_c() { edge::edge_reset(); }

void edge_push_c(const float* sample) { edge::edge_push_sample(sample); }

int edge_ready_c() { return edge::edge_window_ready() ? 1 : 0; }

int edge_features_c(float* out) { return edge::edge_extract_features(out) ? 1 : 0; }

// Returns the class index (0/1/2) and fills proba[3].
int edge_predict_c(const float* feat, float* proba) {
    edge::Decision d = edge::classify_features(feat);
    for (int c = 0; c < 3; ++c) proba[c] = d.proba[c];
    return static_cast<int>(d.cls);
}

} // extern "C"
