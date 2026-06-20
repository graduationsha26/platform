# Contract: `test_AI_live.py` Output Line Format

**Feature**: 051-migrate-lgbm-pipeline

The live evaluation script MUST emit one line per prediction (every ~100 ms) with **exactly
these seven fields, in this order** (spec FR-013, SC-005):

```
Sample, Prediction, Confidence, Precision, Non-Tremor %, Tremor %, Voluntary %
```

## Field definitions

| Field | Type | Definition |
|-------|------|------------|
| `Sample` | int | Incrementing prediction index, starting at 1 (or 0) after warm-up. |
| `Prediction` | string | Argmax class label: `Non-Tremor` \| `Tremor` \| `Voluntary`. |
| `Confidence` | percent | Max class probability × 100, 1 decimal (e.g. `92.4`). |
| `Precision` | percent | Model's overall validated precision from metadata (constant per run). |
| `Non-Tremor %` | percent | P(class 0) × 100. |
| `Tremor %` | percent | P(class 1) × 100. |
| `Voluntary %` | percent | P(class 2) × 100. |

## Rules

- A header row with these exact field names SHOULD be printed once at startup.
- Percentages use a consistent format (1 decimal place recommended).
- During warm-up (buffer not yet holding 1 second of samples) the script MUST print a clear
  "warming up" notice, NOT a partial result line.
- On malformed/недоступ data or a failed window, the script MUST print a clear "could not
  classify" notice instead of an incorrect/partial line (spec US3.3) and continue.
- The three class percentages SHOULD sum to ~100% (rounding aside).

## Example

```
Sample, Prediction, Confidence, Precision, Non-Tremor %, Tremor %, Voluntary %
1, Tremor, 92.4, 88.1, 4.2, 92.4, 3.4
2, Tremor, 90.1, 88.1, 6.0, 90.1, 3.9
3, Non-Tremor, 81.7, 88.1, 81.7, 12.0, 6.3
```
