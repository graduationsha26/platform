"""Measure band-passed per-axis std of the raw source files per training group (T017)."""
import os, sys, glob
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from features_lgbm import SIGNAL_COLS, resample_df, bandpass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))


def find_group_dir(keyword):
    for name in os.listdir(REPO_ROOT):
        full = os.path.join(REPO_ROOT, name)
        if os.path.isdir(full) and "clean dataset" in name.lower() and keyword.lower() in name.lower():
            return full
    raise FileNotFoundError(keyword)


for keyword, label in [("Control", 0), ("Parkinson", 1)]:
    folder = find_group_dir(keyword)
    files = sorted(glob.glob(os.path.join(folder, "*.csv")))[:5]
    print(f"\n=== {keyword} (label={label}) — {os.path.basename(folder)} ===")
    for fp in files:
        df = pd.read_csv(fp).iloc[:, :7]
        df.columns = ["T"] + SIGNAL_COLS
        df = df.dropna()
        raw_astd = df[["AX", "AY", "AZ"]].values.std(axis=0).mean()
        df = resample_df(df)
        bp = np.column_stack([bandpass(df[c].values) for c in SIGNAL_COLS])
        bstd = bp.std(axis=0)
        print(f"  {os.path.basename(fp):16s} n={len(df):5d}  raw_accel_std={raw_astd:7.3f}  "
              f"bandpassed_std[AX,AY,AZ,GX,GY,GZ]=" + ",".join(f"{v:8.3f}" for v in bstd))
