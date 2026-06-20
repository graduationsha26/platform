"""scan_unit_integrity.py — classify each dataset file as physical-unit vs raw-ADC-count (T018).

Physical-unit accel recordings are gravity-anchored: the median resultant |a| ≈ 9.8 m/s².
Raw-ADC-count recordings swing into the thousands. We flag a file as CORRUPT (raw counts) when
its median resultant accel is implausibly large for m/s² data.
"""
import os, sys, glob
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from features_lgbm import SIGNAL_COLS

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))

# A sustained median resultant accel above this is not physical m/s² (gravity≈9.8, ≤ a few g moving).
MEDIAN_RESULTANT_MAX = 40.0   # m/s²  (≈4 g) — generous; raw counts are ~1000s


def find_group_dir(keyword):
    for name in os.listdir(REPO_ROOT):
        full = os.path.join(REPO_ROOT, name)
        if os.path.isdir(full) and "clean dataset" in name.lower() and keyword.lower() in name.lower():
            return full
    raise FileNotFoundError(keyword)


def classify(fp):
    df = pd.read_csv(fp)
    if df.shape[1] < 7:
        return ("skip", 0.0, 0.0)
    df = df.iloc[:, :7]
    df.columns = ["T"] + SIGNAL_COLS
    df = df.dropna()
    if len(df) < 5:
        return ("skip", 0.0, 0.0)
    a = df[["AX", "AY", "AZ"]].values.astype(float)
    med_res = float(np.median(np.linalg.norm(a, axis=1)))
    max_abs = float(np.abs(a).max())
    kind = "corrupt" if med_res > MEDIAN_RESULTANT_MAX else "clean"
    return (kind, med_res, max_abs)


for keyword in ("Control", "Parkinson"):
    folder = find_group_dir(keyword)
    files = sorted(glob.glob(os.path.join(folder, "*.csv")))
    clean, corrupt, skip = [], [], []
    for fp in files:
        kind, med, mx = classify(fp)
        b = os.path.basename(fp)
        if kind == "clean":   clean.append((b, med, mx))
        elif kind == "corrupt": corrupt.append((b, med, mx))
        else: skip.append(b)
    print(f"\n=== {keyword}: {len(files)} files -> clean={len(clean)} corrupt={len(corrupt)} skip={len(skip)} ===")
    print(f"  CORRUPT (raw-ADC-count, median|a| > {MEDIAN_RESULTANT_MAX}):")
    for b, med, mx in corrupt:
        print(f"    {b:18s} median|a|={med:10.1f}  max|a|={mx:10.1f}")
    print(f"  CLEAN (physical-unit, median|a|≈9.8):")
    for b, med, mx in clean:
        print(f"    {b:18s} median|a|={med:8.3f}  max|a|={mx:8.3f}")
    if skip:
        print(f"  SKIPPED (too small/malformed): {skip}")
