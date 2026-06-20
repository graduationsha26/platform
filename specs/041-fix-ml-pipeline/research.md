# Research: Fix ML Pipeline Unit Mismatch

**Feature**: 041-fix-ml-pipeline | **Date**: 2026-04-16

## R1: Excel Data Sampling Rate

**Question**: What is the actual sampling rate of the `Data v2/` Excel files?

**Finding**: The Excel files have `Hora` (HH:MM:SS) and `miliseg` (milliseconds) columns. Row 2-3 of `normal (1).xlsx` show miliseg values of 0, 4, ... indicating ~4ms between samples = **~250 Hz** sampling rate. This matches the MPU6050's typical output rate.

**Decision**: Use 250 Hz as the training data sampling rate for FFT frequency resolution. Store this in metadata.

**Alternatives**: Using 37 Hz (PSMAD dataset rate) was considered but would be incorrect for this dataset.

## R2: ADC → Physical Unit Conversion Factors

**Question**: What are the correct MPU6050 sensitivity factors?

**Finding**: The MPU6050 at default ±2g / ±250°/s full-scale configuration uses:
- Accelerometer: 16384 LSB/g → divide raw by 16384.0, then multiply by 9.81 for m/s²
- Gyroscope: 131 LSB/(°/s) → divide raw by 131.0 for °/s

**Validation**: Raw AcY value of -16652 → -16652/16384.0 × 9.81 ≈ -9.97 m/s² ≈ -1g (gravity pointing down when sensor is upright). This confirms the conversion is correct.

**Decision**: Apply these exact conversion factors in the aggregation script. Store them in metadata for traceability.

## R3: Gravity Handling Strategy

**Question**: Should we keep the Butterworth high-pass gravity filter or rely on FFT?

**Finding**: 
- The current v1 pipeline applies a 2nd-order Butterworth high-pass at 0.5 Hz to remove gravity from aX/aY/aZ before feature extraction.
- The new spec says "apply FFT to ignore gravity" and requests `dominant_freq` (via FFT) as one of 7 features.
- FFT inherently separates frequency components: the DC/gravity component sits at 0 Hz, while Parkinson's tremor is at 3-12 Hz. The `dominant_freq` feature finds the peak frequency in the tremor band, naturally ignoring gravity.
- The 6 statistical features (mean, std, max, min, RMS, median) will include the gravity component. However, since BOTH training data (after ADC→physical conversion) AND live data include gravity, the features are **consistent** between training and inference. This is the key requirement.

**Decision**: Remove the explicit gravity filter for v2 models. Consistency between training and inference is guaranteed by: (1) identical unit conversion, (2) shared feature extraction function, (3) gravity present in both data sources.

**Alternatives**: Keeping the gravity filter was considered but rejected because it adds complexity and another source of training/inference divergence.

## R4: Feature Set Composition

**Question**: How to map the 7 specified features × 6 axes to a deterministic 42-feature vector?

**Finding**: The spec requires: mean, std, max, min, RMS, median, dominant_freq for each of 6 axes (aX, aY, aZ, gX, gY, gZ).

**Decision**: Feature ordering will be axis-major: all 7 features for aX first, then aY, etc.
```
[mean_aX, std_aX, max_aX, min_aX, rms_aX, median_aX, dominant_freq_aX,
 mean_aY, std_aY, max_aY, min_aY, rms_aY, median_aY, dominant_freq_aY,
 ...
 mean_gZ, std_gZ, max_gZ, min_gZ, rms_gZ, median_gZ, dominant_freq_gZ]
```

This matches the existing convention in `feature_extractors.py` where features are grouped by axis.

## R5: StandardScaler Persistence Strategy

**Question**: Should the scaler be embedded in metadata (as mean/std arrays) or saved as a separate `.pkl`?

**Finding**: 
- Current v1 approach: scaler params embedded in metadata JSON as `preprocessing.scaler_params.mean` and `preprocessing.scaler_params.std`. Inference reconstructs manually with `(x - mean) / std`.
- Potential issue: floating-point precision differences between manual reconstruction and `scaler.transform()`.

**Decision**: Save the fitted `StandardScaler` as a separate `.pkl` file (`rf_model_v2_scaler.pkl`). The inference service loads it and calls `scaler.transform()` directly. This eliminates any numerical divergence.

**Alternatives**: Embedding in JSON was rejected because it introduces a precision risk and doesn't support edge cases like zero-variance features where sklearn clips std.

## R6: Model File Naming and Version Mapping

**Question**: How to handle the version mapping in `ModelLoader`?

**Finding**: Current `ModelLoader._get_model_path()` maps `'rf'` → `rf_model.pkl` (no version suffix), but actual files on disk are `rf_model_v1.pkl`. This is a disconnect — the current mapping doesn't actually work unless there's a symlink or copy.

**Decision**: Update the mapping to point directly to v2 filenames:
- `'rf'` → `rf_model_v2.pkl` / `rf_model_v2.json`
- Keep v1 files on disk for reference
- Add scaler path: `rf_model_v2_scaler.pkl`

The `ModelCache.get_model()` will be extended to also load the scaler when the metadata indicates a scaler file exists.

## R7: Window Size Impact on Live Inference

**Question**: What is the impact of changing window size from 100 to 200?

**Finding**:
- v1: 100 samples @ 30 Hz = 3.3s warm-up
- v2: 200 samples @ 30 Hz = 6.7s warm-up
- After warm-up, predictions still happen on every incoming message (stride=1 for live)
- Feature extraction on 200 samples × 6 axes is still well under 33ms (one MQTT message interval)

**Decision**: Accept the increased warm-up time. 6.7s is acceptable for a clinical monitoring scenario where sessions last minutes to hours. The larger window provides better frequency resolution for the FFT dominant_freq feature (0.15 Hz resolution at 30 Hz vs 0.3 Hz at 100 samples).
