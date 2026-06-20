// edge_features.cpp — On-device 66-feature tremor pipeline (Feature 052).
//
// Parity contract with backend/ml_models/features_lgbm.py:
//   * Band-pass: causal Butterworth SOS (tremor_model::bandpass_sos), applied as a cascade of
//     Direct-Form-II-Transposed biquads — bit-for-bit the same recurrence scipy's sosfilt uses.
//     The filter runs continuously over the stream (persistent state); the rolling window holds
//     filtered samples, matching training (whole-recording causal filter, then sliced).
//   * Features per axis, in this exact order (== get_feature_names_66()):
//       mean, std(ddof=0), median, q1, q3, min, max, peak1_freq, peak1_amp, peak2_freq, peak2_amp
//   * FFT: real 128-pt, DC-removed; magnitudes over bins in [0.5, 20] Hz; top-2 by magnitude.
//   * Percentiles: NumPy linear interpolation. Median: mean of the two central order stats.
//
// DSP is portable (no esp-dsp) so the host parity harness validates the exact shipped code.
// esp-dsp's dsps_fft2r_* / dsps_biquad_f32 can replace fft128()/biquad later for speed — they
// implement the same math; keep this portable path as the parity reference.

#include "edge_features.h"

#include <cmath>
#include <cstring>
#include <algorithm>

namespace edge {

using tremor_model::bandpass_sos;
using tremor_model::BANDPASS_N_SECTIONS;

static constexpr float SAMPLE_RATE_HZ = tremor_model::SAMPLE_RATE_HZ;  // 100.0
static constexpr float LOWCUT_HZ  = 0.5f;
static constexpr float HIGHCUT_HZ = 20.0f;

// ── Rolling buffer of FILTERED samples + persistent biquad state ──────────────
static float    g_buf[N_AXES][WINDOW];                 // ring buffer, filtered samples
static int      g_head = 0;                            // next write index
static int      g_count = 0;                           // filled samples (caps at WINDOW)
static float    g_state[N_AXES][BANDPASS_N_SECTIONS][2]; // DF2T state per axis per section

void edge_reset() {
    std::memset(g_buf, 0, sizeof(g_buf));
    std::memset(g_state, 0, sizeof(g_state));
    g_head = 0;
    g_count = 0;
}

// One causal biquad cascade pass for a single axis (Direct Form II Transposed, a0 == 1).
// sos row layout: {b0, b1, b2, a0, a1, a2}. Matches scipy.signal.sosfilt.
static inline float biquad_cascade(int axis, float x) {
    for (int s = 0; s < BANDPASS_N_SECTIONS; ++s) {
        const float b0 = bandpass_sos[s][0];
        const float b1 = bandpass_sos[s][1];
        const float b2 = bandpass_sos[s][2];
        const float a1 = bandpass_sos[s][4];
        const float a2 = bandpass_sos[s][5];
        float *w = g_state[axis][s];
        const float y = b0 * x + w[0];
        w[0] = b1 * x - a1 * y + w[1];
        w[1] = b2 * x - a2 * y;
        x = y;
    }
    return x;
}

void edge_push_sample(const float sample[N_AXES]) {
    for (int a = 0; a < N_AXES; ++a) {
        g_buf[a][g_head] = biquad_cascade(a, sample[a]);
    }
    g_head = (g_head + 1) % WINDOW;
    if (g_count < WINDOW) ++g_count;
}

bool edge_window_ready() {
    return g_count >= WINDOW;
}

// ── Portable in-place iterative radix-2 FFT (Cooley-Tukey), N = WINDOW (128) ───
static void fft_radix2(float *re, float *im, int n) {
    // bit-reversal permutation
    for (int i = 1, j = 0; i < n; ++i) {
        int bit = n >> 1;
        for (; j & bit; bit >>= 1) j ^= bit;
        j ^= bit;
        if (i < j) { std::swap(re[i], re[j]); std::swap(im[i], im[j]); }
    }
    for (int len = 2; len <= n; len <<= 1) {
        const float ang = -2.0f * (float)M_PI / (float)len;
        const float wr = std::cos(ang), wi = std::sin(ang);
        for (int i = 0; i < n; i += len) {
            float cr = 1.0f, ci = 0.0f;
            for (int k = 0; k < len / 2; ++k) {
                const int a = i + k, b = i + k + len / 2;
                const float xr = re[b] * cr - im[b] * ci;
                const float xi = re[b] * ci + im[b] * cr;
                re[b] = re[a] - xr; im[b] = im[a] - xi;
                re[a] += xr;        im[a] += xi;
                const float ncr = cr * wr - ci * wi;
                ci = cr * wi + ci * wr;
                cr = ncr;
            }
        }
    }
}

// FFT top-2 in-band peaks for one axis window (DC removed). Mirrors features_lgbm._fft_top2.
static void fft_top2(const float *x, int n,
                     float *f1, float *a1, float *f2, float *a2) {
    static float re[WINDOW], im[WINDOW];
    float mean = 0.0f;
    for (int i = 0; i < n; ++i) mean += x[i];
    mean /= (float)n;
    for (int i = 0; i < n; ++i) { re[i] = x[i] - mean; im[i] = 0.0f; }
    fft_radix2(re, im, n);

    const float df = SAMPLE_RATE_HZ / (float)n;   // bin spacing (Hz)
    // Find the two strongest magnitude bins with freq in [LOWCUT, HIGHCUT].
    // Tie-handling mirrors numpy argsort()[::-1] (equal magnitudes -> higher bin index wins),
    // so use >= when comparing.
    int i1 = -1, i2 = -1;
    float m1 = -1.0f, m2 = -1.0f;
    const int half = n / 2;                        // rfft has bins 0..n/2
    for (int k = 0; k <= half; ++k) {
        const float fk = (float)k * df;
        if (fk < LOWCUT_HZ || fk > HIGHCUT_HZ) continue;
        const float mag = std::sqrt(re[k] * re[k] + im[k] * im[k]);
        if (mag >= m1) { m2 = m1; i2 = i1; m1 = mag; i1 = k; }
        else if (mag >= m2) { m2 = mag; i2 = k; }
    }
    if (i1 < 0) { *f1 = *a1 = *f2 = *a2 = 0.0f; return; }
    if (i2 < 0) { i2 = i1; m2 = m1; }              // only one in-band bin -> duplicate
    *f1 = (float)i1 * df; *a1 = m1;
    *f2 = (float)i2 * df; *a2 = m2;
}

// NumPy-linear-interpolation percentile over a sorted copy (q in [0,1]).
static inline float percentile_sorted(const float *sorted, int n, float q) {
    const float pos = q * (float)(n - 1);
    const int lo = (int)std::floor(pos);
    const float frac = pos - (float)lo;
    if (lo + 1 >= n) return sorted[n - 1];
    return sorted[lo] + frac * (sorted[lo + 1] - sorted[lo]);
}

bool edge_extract_features(float out[N_FEATURES]) {
    if (!edge_window_ready()) return false;

    static float col[WINDOW];
    static float sorted[WINDOW];
    int o = 0;
    for (int a = 0; a < N_AXES; ++a) {
        // Copy this axis' window in time order (oldest -> newest) out of the ring buffer.
        for (int i = 0; i < WINDOW; ++i) {
            const float v = g_buf[a][(g_head + i) % WINDOW];
            if (!std::isfinite(v)) return false;   // invalid window -> withhold decision
            col[i] = v;
        }
        // mean
        float mean = 0.0f;
        for (int i = 0; i < WINDOW; ++i) mean += col[i];
        mean /= (float)WINDOW;
        // std (population, ddof=0)
        float var = 0.0f;
        for (int i = 0; i < WINDOW; ++i) { const float d = col[i] - mean; var += d * d; }
        var /= (float)WINDOW;
        const float stdv = std::sqrt(var);
        // order statistics
        std::memcpy(sorted, col, sizeof(float) * WINDOW);
        std::sort(sorted, sorted + WINDOW);
        const float med = 0.5f * (sorted[WINDOW / 2 - 1] + sorted[WINDOW / 2]); // even N=128
        const float q1 = percentile_sorted(sorted, WINDOW, 0.25f);
        const float q3 = percentile_sorted(sorted, WINDOW, 0.75f);
        const float mn = sorted[0];
        const float mx = sorted[WINDOW - 1];
        // spectral peaks
        float f1, a1, f2, a2;
        fft_top2(col, WINDOW, &f1, &a1, &f2, &a2);

        out[o++] = mean;
        out[o++] = stdv;
        out[o++] = med;
        out[o++] = q1;
        out[o++] = q3;
        out[o++] = mn;
        out[o++] = mx;
        out[o++] = f1;
        out[o++] = a1;
        out[o++] = f2;
        out[o++] = a2;
    }
    return true;
}

} // namespace edge
