// edge_features.h — On-device 66-feature tremor pipeline (Feature 052).
//
// Mirrors backend/ml_models/features_lgbm.py EXACTLY so the on-device features match the
// trained model. Pipeline: stream each 100 Hz calibrated 6-axis sample through a causal
// Butterworth band-pass (the same SOS the training pipeline used), keep a sliding 128-sample
// window of FILTERED samples, and on demand extract 66 features (11 per axis x 6 axes,
// axis-major) including band-limited FFT top-2 peaks.
//
// DSP is portable C++ (hand-written biquad + radix-2 FFT) so the host parity harness compiles
// and validates the exact code that ships. (esp-dsp is available as a future accelerator; see
// edge_features.cpp.)
#pragma once

#include <cstdint>
#include "tremor_model.h"   // WINDOW_SIZE, NUM_FEATURES, bandpass_sos, BANDPASS_N_SECTIONS

namespace edge {

constexpr int N_AXES     = 6;
constexpr int WINDOW      = tremor_model::WINDOW_SIZE;     // 128
constexpr int N_FEATURES  = tremor_model::NUM_FEATURES;    // 66

// Reset the rolling buffer and band-pass filter state. Call once after IMU calibration so the
// filter warm-up transient is not counted toward the first window.
void edge_reset();

// Stream one calibrated sample (axis order: aX,aY,aZ,gX,gY,gZ — matches SIGNAL_COLS). The
// sample is band-pass filtered (persistent state) and pushed into the rolling window.
void edge_push_sample(const float sample[N_AXES]);

// True once WINDOW filtered samples have been collected (warm-up gate, FR-011).
bool edge_window_ready();

// Extract the 66-feature vector from the current window (order == get_feature_names_66()).
// Returns false if the window is not ready or contains a non-finite value.
bool edge_extract_features(float out[N_FEATURES]);

} // namespace edge
