"""
train.py — LightGBM tremor-classification training pipeline (Feature 051).

Reproduces the validated LGBM.ipynb pipeline as a single, reproducible, deterministic run:

  1. Load the three labeled recording groups (Control=0, Parkinson's=1, Voluntary=2).
  2. Resample each recording to 66.67 Hz, band-pass 0.5-20 Hz, slice 1-second (67-sample)
     non-overlapping windows, extract the 66 features (shared features_lgbm module).
  3. Combine + label, drop inf/NaN, and SAVE backend/ml_data/combined_processed_data.csv
     *BEFORE* any model training begins.
  4. Train ONE SMOTE+LightGBM model with PINNED hyperparameters (no run-time search),
     save backend/ml_models/lgbm_tremor_model.pkl + lgbm_tremor_model.json.

Run:
    python backend/ml_models/train.py

Hyperparameters were discovered once via RandomizedSearchCV (GroupKFold(4) on file_id,
f1_macro, n_iter=15, random_state=42) and are hardcoded below for speed + reproducibility.
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

# PINNED hyperparameters — discovered once via RandomizedSearchCV (2026-06-20),
# user-approved. DO NOT run a search here. See specs/051-migrate-lgbm-pipeline/research.md §3.
PINNED_PARAMS = {
    "n_estimators": 300,
    "learning_rate": 0.05,
    "num_leaves": 63,
    "max_depth": -1,
}

CLASS_NAMES = ["Non-Tremor", "Tremor", "Voluntary"]
GROUPS = [("Control", 0), ("Parkinson", 1), ("Voluntary", 2)]  # (folder keyword, label)

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))            # backend/ml_models
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)                          # backend
REPO_ROOT = os.path.dirname(BACKEND_DIR)                           # repo root
ML_DATA_DIR = os.path.join(BACKEND_DIR, "ml_data")
CSV_PATH = os.path.join(ML_DATA_DIR, "combined_processed_data.csv")
MODEL_PATH = os.path.join(SCRIPT_DIR, "lgbm_tremor_model.pkl")
META_PATH = os.path.join(SCRIPT_DIR, "lgbm_tremor_model.json")


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


def load_group(folder, label):
    """Load + preprocess every CSV in one group folder into feature rows."""
    rows = []
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

            df = resample_df(df)                      # -> 66.67 Hz
            for c in SIGNAL_COLS:                      # band-pass each axis
                df[c] = bandpass(df[c].values)

            arr = df[SIGNAL_COLS].values               # (n, 6)
            file_id = os.path.splitext(os.path.basename(fp))[0]

            n_windows = 0
            for start in range(0, len(arr) - WINDOW_SIZE + 1, WINDOW_SIZE):
                window = arr[start:start + WINDOW_SIZE]
                feats = extract_features_66(window)
                row = dict(zip(get_feature_names_66(), feats))
                row["file_id"] = file_id
                row["label"] = label
                rows.append(row)
                n_windows += 1

            if n_windows == 0:
                skipped += 1
        except Exception as e:
            skipped += 1
            print(f"  [skip] {os.path.basename(fp)}: {e}")

    print(f"  label={label} ({CLASS_NAMES[label]}): {len(files)} files, "
          f"{len(rows)} windows, {skipped} skipped")
    return rows


def build_dataset():
    """Load all three groups -> combined, cleaned feature DataFrame."""
    print("Loading + preprocessing recording groups ...")
    all_rows = []
    for keyword, label in GROUPS:
        folder = find_group_dir(keyword)
        print(f"[{keyword}] {folder}")
        all_rows.extend(load_group(folder, label))

    df = pd.DataFrame(all_rows)
    df = df.replace([np.inf, -np.inf], np.nan).dropna().reset_index(drop=True)

    # Order columns: 66 features, then file_id, label
    feature_cols = get_feature_names_66()
    df = df[feature_cols + ["file_id", "label"]]
    return df


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
    """imblearn Pipeline: SMOTE (fit-time only) + LightGBM with PINNED params. No scaler."""
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

    # File-level via majority vote per file_id
    vote = pd.DataFrame({"file_id": groups, "y_true": y, "y_pred": y_pred})
    file_true = vote.groupby("file_id")["y_true"].agg(lambda s: s.mode().iloc[0])
    file_pred = vote.groupby("file_id")["y_pred"].agg(lambda s: s.mode().iloc[0])

    return {
        "cv": "GroupKFold(4) on file_id",
        "window_macro_precision": float(precision_score(y, y_pred, average="macro", zero_division=0)),
        "window_macro_recall": float(recall_score(y, y_pred, average="macro", zero_division=0)),
        "window_macro_f1": float(f1_score(y, y_pred, average="macro", zero_division=0)),
        "window_accuracy": float(accuracy_score(y, y_pred)),
        "file_macro_precision": float(precision_score(file_true, file_pred, average="macro", zero_division=0)),
        "file_accuracy": float(accuracy_score(file_true, file_pred)),
    }


def train_final(df):
    """Fit the pinned model on the full dataset and persist .pkl."""
    feature_cols = get_feature_names_66()
    X = df[feature_cols]
    y = df["label"].values

    print("\nTraining final model on full dataset (pinned params, no search) ...")
    model = build_pipeline()
    # Fit on a plain ndarray (not a named DataFrame) so the served model does not warn when
    # inference / live paths pass NumPy feature vectors. Column order == get_feature_names_66().
    model.fit(X.values, y)
    joblib.dump(model, MODEL_PATH)
    print(f"[SAVED] {MODEL_PATH}")
    return model


def save_metadata(metrics):
    meta = {
        "model_type": "lightgbm",
        "classes": {"0": "Non-Tremor", "1": "Tremor", "2": "Voluntary"},
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
    df = build_dataset()
    save_combined_csv(df)

    # US2 — evaluate, train, persist
    metrics = evaluate(df)
    train_final(df)
    save_metadata(metrics)

    print(f"\nDone in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
