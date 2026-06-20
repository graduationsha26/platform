"""
train.py — LightGBM tremor-classification training pipeline (Feature 053: BINARY pivot).

Reproduces the validated LGBM pipeline as a single, reproducible, deterministic run, now as a
TWO-class problem (Feature 053):

  0 = Non-Tremor   (clean Control-group resting recordings + the verified device still-glove capture)
  1 = Tremor       (Parkinson rest-tremor recordings)

The `Voluntary` class (former label 2) is dropped entirely.

Data integrity (Feature 053, T018): the Control group mixes physical-unit recordings (m/s², deg/s)
with a subject whose files were exported in RAW IMU ADC COUNTS (±thousands). Those raw-count files
inflated the Non-Tremor variance so badly that a still glove was classified Tremor. They are now
QUARANTINED automatically: any file whose median resultant accel is implausible for m/s² data
(> MEDIAN_RESULTANT_ACCEL_MAX) is skipped and logged.

Pipeline (unchanged per-window math):
  1. Load Control (label 0) + Parkinson (label 1), quarantining raw-count files; ADD the device
     still-glove capture as extra Non-Tremor data.
  2. Resample each recording to 100 Hz, apply the CAUSAL Butterworth band-pass 0.5-20 Hz to the
     WHOLE recording, slice 1.28-second (128-sample) non-overlapping windows, extract the 66
     features (shared features_lgbm module).
  3. Combine + label, drop inf/NaN, and SAVE backend/ml_data/combined_processed_data.csv BEFORE
     any model training begins.
  4. Train ONE SMOTE+LightGBM (objective="binary") model with PINNED hyperparameters,
     save backend/ml_models/lgbm_tremor_model.pkl + lgbm_tremor_model.json.

Run:
    python backend/ml_models/train.py
"""

import os
import sys
import glob
import json
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import GroupKFold, cross_val_predict
from sklearn.metrics import (
    precision_score, recall_score, f1_score, accuracy_score, classification_report,
)
from lightgbm import LGBMClassifier
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline

# Make features_lgbm importable whether run as a script or as part of the ml_models package.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from features_lgbm import (  # noqa: E402
    FS, WINDOW_SIZE, WINDOW_SECONDS, LOWCUT, HIGHCUT, BANDPASS_ORDER, SIGNAL_COLS,
    N_FEATURES, resample_df, bandpass, extract_features_66, get_feature_names_66,
)

# ── Configuration ────────────────────────────────────────────────────────────
RANDOM_STATE = 42

# PINNED hyperparameters — discovered once via RandomizedSearchCV, user-approved.
# Feature 053: objective="binary" makes LightGBM emit a SINGLE tree series (one output) whose
# probability is sigmoid(raw). The C exporter/interpreter rely on this (see export_to_c.py).
PINNED_PARAMS = {
    "objective": "binary",
    "n_estimators": 300,
    "learning_rate": 0.05,
    "num_leaves": 63,
    "max_depth": -1,
}

CLASS_NAMES = ["Non-Tremor", "Tremor"]               # index == label
GROUPS = [("Control", 0), ("Parkinson", 1)]          # (folder keyword, label) — Voluntary dropped

# Data-integrity guard (Feature 053): physical-unit accel is gravity-anchored (median |a| ≈ 9.8).
# Raw-ADC-count files swing into the thousands; quarantine anything implausible for m/s².
MEDIAN_RESULTANT_ACCEL_MAX = 40.0   # m/s² (≈4 g) — generous; raw counts are ~1000s

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))            # backend/ml_models
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)                          # backend
REPO_ROOT = os.path.dirname(BACKEND_DIR)                           # repo root
ML_DATA_DIR = os.path.join(BACKEND_DIR, "ml_data")
CSV_PATH = os.path.join(ML_DATA_DIR, "combined_processed_data.csv")
MODEL_PATH = os.path.join(SCRIPT_DIR, "lgbm_tremor_model.pkl")
META_PATH = os.path.join(SCRIPT_DIR, "lgbm_tremor_model.json")

# Device still-glove capture → extra Non-Tremor (label 0) training data (verified m/s² / deg/s).
STILL_CAPTURE_PATH = os.path.join(REPO_ROOT, "stable_glove_data_20260620_215329.csv")
STILL_CAPTURE_ID = "device_still_20260620"


# ── Data loading + preprocessing (US1) ───────────────────────────────────────

def find_group_dir(keyword):
    """Locate a dataset folder by keyword (folder names contain en-dashes/RTL marks)."""
    for name in os.listdir(REPO_ROOT):
        full = os.path.join(REPO_ROOT, name)
        if (os.path.isdir(full)
                and "clean dataset" in name.lower()
                and keyword.lower() in name.lower()):
            return full
    raise FileNotFoundError(
        f"No dataset folder matching '{keyword}' under {REPO_ROOT}. "
        f"Expected e.g. 'Clean Dataset – {keyword} Group'."
    )


def is_physical_units(df):
    """True if accel looks like m/s² (gravity-anchored), False if raw ADC counts (Feature 053)."""
    a = df[["AX", "AY", "AZ"]].values.astype(float)
    med_res = float(np.median(np.linalg.norm(a, axis=1)))
    return med_res <= MEDIAN_RESULTANT_ACCEL_MAX, med_res


def _windows_to_rows(arr, file_id, label):
    """Slice non-overlapping 128-sample windows -> 66-feature rows."""
    rows = []
    names = get_feature_names_66()
    for start in range(0, len(arr) - WINDOW_SIZE + 1, WINDOW_SIZE):
        feats = extract_features_66(arr[start:start + WINDOW_SIZE])
        row = dict(zip(names, feats))
        row["file_id"] = file_id
        row["label"] = label
        rows.append(row)
    return rows


def load_group(folder, label):
    """Load + preprocess every CSV in one group folder into feature rows.

    Returns (rows, quarantined) where `quarantined` lists raw-ADC-count files that were skipped.
    """
    rows = []
    quarantined = []
    files = sorted(glob.glob(os.path.join(folder, "*.csv")))
    skipped = 0
    for fp in files:
        try:
            df = pd.read_csv(fp)
            if df.shape[1] < 7:
                skipped += 1
                continue
            df = df.iloc[:, :7]
            df.columns = ["T"] + SIGNAL_COLS
            df = df.dropna()
            if len(df) < 5:
                skipped += 1
                continue

            # Feature 053: quarantine raw-ADC-count recordings (unit-integrity guard).
            ok, med_res = is_physical_units(df)
            if not ok:
                quarantined.append(os.path.basename(fp))
                print(f"  [QUARANTINE] {os.path.basename(fp)} median|a|={med_res:.1f} "
                      f"(> {MEDIAN_RESULTANT_ACCEL_MAX}) — raw ADC counts, skipped")
                continue

            df = resample_df(df)                       # -> 100 Hz
            for c in SIGNAL_COLS:                       # band-pass each axis
                df[c] = bandpass(df[c].values)

            arr = df[SIGNAL_COLS].values                # (n, 6)
            file_id = os.path.splitext(os.path.basename(fp))[0]
            file_rows = _windows_to_rows(arr, file_id, label)
            rows.extend(file_rows)
            if not file_rows:
                skipped += 1
        except Exception as e:
            skipped += 1
            print(f"  [skip] {os.path.basename(fp)}: {e}")

    print(f"  label={label} ({CLASS_NAMES[label]}): {len(files)} files, "
          f"{len(rows)} windows, {len(quarantined)} quarantined, {skipped} skipped")
    return rows, quarantined


def _timestamp_to_ms(t):
    """'HH:MM:SS.mmm' -> milliseconds."""
    h, m, s = str(t).split(":")
    return (int(h) * 3600 + int(m) * 60 + float(s)) * 1000.0


def load_still_capture(path, label=0):
    """Load the device still-glove capture as extra Non-Tremor windows (Feature 053)."""
    if not os.path.exists(path):
        print(f"  [still] capture not found: {path} — skipping")
        return []
    df = pd.read_csv(path).iloc[:, :7]
    df.columns = ["T"] + SIGNAL_COLS
    df = df.dropna()
    # Verify units before trusting it as Non-Tremor data.
    ok, med_res = is_physical_units(df)
    if not ok:
        print(f"  [still] capture median|a|={med_res:.1f} not physical units — skipping")
        return []
    df["T"] = df["T"].map(_timestamp_to_ms)
    df = df.drop_duplicates(subset="T").sort_values("T").reset_index(drop=True)
    df["T"] = df["T"] - df["T"].iloc[0]
    df = resample_df(df)                                # -> 100 Hz
    for c in SIGNAL_COLS:
        df[c] = bandpass(df[c].values)
    arr = df[SIGNAL_COLS].values
    rows = _windows_to_rows(arr, STILL_CAPTURE_ID, label)
    print(f"  [still] {len(rows)} Non-Tremor windows from device capture "
          f"({os.path.basename(path)})")
    return rows


def build_dataset():
    """Load both groups (+ still capture) -> combined, cleaned feature DataFrame + provenance."""
    print("Loading + preprocessing recording groups ...")
    all_rows = []
    quarantined_all = {}
    for keyword, label in GROUPS:
        folder = find_group_dir(keyword)
        print(f"[{keyword}] {folder}")
        rows, quarantined = load_group(folder, label)
        all_rows.extend(rows)
        if quarantined:
            quarantined_all[keyword] = quarantined

    # Feature 053: add the verified device still-glove capture as Non-Tremor.
    all_rows.extend(load_still_capture(STILL_CAPTURE_PATH, label=0))

    df = pd.DataFrame(all_rows)
    df = df.replace([np.inf, -np.inf], np.nan).dropna().reset_index(drop=True)

    feature_cols = get_feature_names_66()
    df = df[feature_cols + ["file_id", "label"]]
    return df, quarantined_all


def save_combined_csv(df):
    """Persist the combined dataset BEFORE any training (FR-003 / SC-001)."""
    os.makedirs(ML_DATA_DIR, exist_ok=True)
    df.to_csv(CSV_PATH, index=False)
    uniq, cnts = np.unique(df["label"].values, return_counts=True)
    print(f"\n[SAVED] {CSV_PATH}")
    print(f"  shape: {df.shape}  (features={len(get_feature_names_66())})")
    print(f"  class distribution: {dict(zip(uniq.tolist(), cnts.tolist()))}")
    print(f"  unique files: {df['file_id'].nunique()}")


# ── Training + evaluation (US2) ──────────────────────────────────────────────

def build_pipeline():
    """imblearn Pipeline: SMOTE (fit-time only) + binary LightGBM with PINNED params. No scaler."""
    return Pipeline([
        ("smote", SMOTE(random_state=RANDOM_STATE)),
        ("clf", LGBMClassifier(**PINNED_PARAMS, random_state=RANDOM_STATE, verbose=-1)),
    ])


def evaluate(df):
    """GroupKFold(4) out-of-fold metrics (window + file level) for parity reporting."""
    feature_cols = get_feature_names_66()
    X = df[feature_cols]
    y = df["label"].values
    groups = df["file_id"].values
    cv = GroupKFold(n_splits=4)

    print("\nEvaluating (GroupKFold=4, out-of-fold) ...")
    y_pred = cross_val_predict(build_pipeline(), X, y, groups=groups, cv=cv, n_jobs=-1)
    print(classification_report(y, y_pred, target_names=CLASS_NAMES))

    vote = pd.DataFrame({"file_id": groups, "y_true": y, "y_pred": y_pred})
    file_true = vote.groupby("file_id")["y_true"].agg(lambda s: s.mode().iloc[0])
    file_pred = vote.groupby("file_id")["y_pred"].agg(lambda s: s.mode().iloc[0])

    return {
        "cv": "GroupKFold(4) on file_id",
        "window_macro_precision": float(precision_score(y, y_pred, average="macro", zero_division=0)),
        "window_macro_recall": float(recall_score(y, y_pred, average="macro", zero_division=0)),
        "window_macro_f1": float(f1_score(y, y_pred, average="macro", zero_division=0)),
        "window_accuracy": float(accuracy_score(y, y_pred)),
        "window_tremor_precision": float(precision_score(y, y_pred, pos_label=1, zero_division=0)),
        "window_tremor_recall": float(recall_score(y, y_pred, pos_label=1, zero_division=0)),
        "file_macro_precision": float(precision_score(file_true, file_pred, average="macro", zero_division=0)),
        "file_accuracy": float(accuracy_score(file_true, file_pred)),
    }


def train_final(df):
    """Fit the pinned binary model on the full dataset and persist .pkl."""
    feature_cols = get_feature_names_66()
    X = df[feature_cols]
    y = df["label"].values

    print("\nTraining final model on full dataset (pinned binary params, no search) ...")
    model = build_pipeline()
    # Fit on a plain ndarray so the served model does not warn when inference passes NumPy vectors.
    model.fit(X.values, y)
    joblib.dump(model, MODEL_PATH)
    print(f"[SAVED] {MODEL_PATH}")
    return model


def save_metadata(metrics, quarantined_all):
    meta = {
        "model_type": "lightgbm",
        "task": "binary",
        "classes": {"0": "Non-Tremor", "1": "Tremor"},
        "n_features": N_FEATURES,
        "feature_names": get_feature_names_66(),
        "pipeline": {
            "fs_hz": FS,
            "window_seconds": WINDOW_SECONDS,
            "window_samples": WINDOW_SIZE,
            "bandpass_hz": [LOWCUT, HIGHCUT],
            "bandpass_order": BANDPASS_ORDER,
            "scaler": None,
        },
        "hyperparameters": PINNED_PARAMS,
        "smote": {"random_state": RANDOM_STATE},
        "data_integrity": {
            "median_resultant_accel_max": MEDIAN_RESULTANT_ACCEL_MAX,
            "quarantined_raw_adc_files": quarantined_all,
            "extra_non_tremor_sources": [os.path.basename(STILL_CAPTURE_PATH)],
        },
        "metrics": metrics,
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    print(f"[SAVED] {META_PATH}")
    print(f"  window macro precision (live 'Precision' field): "
          f"{metrics['window_macro_precision'] * 100:.1f}%")


def main():
    t0 = time.time()
    # US1 — dataset first, saved BEFORE any training
    df, quarantined_all = build_dataset()
    save_combined_csv(df)

    # US2 — evaluate, train, persist
    metrics = evaluate(df)
    train_final(df)
    save_metadata(metrics, quarantined_all)

    print(f"\nDone in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
