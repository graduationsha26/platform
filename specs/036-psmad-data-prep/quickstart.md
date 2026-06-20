# Quickstart: PSMAD Data Preprocessing Pipeline

**Branch**: `036-psmad-data-prep`  
**Date**: 2026-04-07

---

## Prerequisites

```bash
# From repo root, ensure Python dependencies are available
cd backend
pip install pandas numpy scipy openpyxl
```

Required packages:
- `pandas` — CSV and Excel loading
- `numpy` — FFT and numerical operations
- `scipy` — skewness and kurtosis calculations (already used by existing pipeline)
- `openpyxl` — Excel (.xlsx) reading for metadata

---

## Run the Pipeline

```bash
# From repo root
cd backend/ml_data/scripts

python 4_psmad_pipeline.py
```

Default paths (relative to repo root):
- Parkinson data: `DataParkinson/Clean Dataset - Parkinson's Group/`
- Control data: `DataParkinson/Clean Dataset - Control Group/`
- Metadata: `DataParkinson/AdditionalData.xlsx`
- Output: `backend/ml_data/processed/ready_for_training_features.csv`

### Custom paths

```bash
python 4_psmad_pipeline.py \
  --parkinson-dir "C:/Data from HDD/Graduation Project/Platform/DataParkinson/Clean Dataset - Parkinson's Group" \
  --control-dir "C:/Data from HDD/Graduation Project/Platform/DataParkinson/Clean Dataset - Control Group" \
  --metadata "C:/Data from HDD/Graduation Project/Platform/DataParkinson/AdditionalData.xlsx" \
  --output "backend/ml_data/processed/ready_for_training_features.csv"
```

---

## Expected Output

Successful run produces:

```
======================================================================
PSMAD PREPROCESSING PIPELINE
======================================================================
[INFO] Loading metadata from DataParkinson/AdditionalData.xlsx
[INFO] Metadata loaded: 14 participants

[INFO] Loading Control Group recordings...
[INFO]   Found 89 CSV files, skipping 10 validation files (ending in 00)
[INFO]   Loaded 79 valid recordings

[INFO] Loading Parkinson Group recordings...
[INFO]   Found 29 CSV files, skipping 0 validation files (ending in 00)
[INFO]   Loaded 29 valid recordings

[INFO] Creating windows (size=100, non-overlapping)...
[INFO]   Control windows: ~237 (varies by recording length)
[INFO]   Parkinson windows: ~87 (varies by recording length)

[INFO] Extracting features (30 time-domain + 12 FFT)...

[INFO] Validating output (no NaN/Inf)... OK

[INFO] Saving ready_for_training_features.csv...
======================================================================
SUMMARY
  Total files processed: 108 (79 Control + 29 Parkinson)
  Total windows generated: ~324
  Label distribution: 0 (Control): ~237, 1 (Parkinson): ~87
  Features per window: 42 (30 time-domain + 12 FFT tremor-band)
  Output: backend/ml_data/processed/ready_for_training_features.csv
======================================================================
```

---

## Output File Structure

`backend/ml_data/processed/ready_for_training_features.csv`

```csv
RMS_aX,mean_aX,std_aX,skewness_aX,kurtosis_aX,...,dominant_freq_gZ,tremor_energy_gZ,label
12543.2,324.1,8921.3,0.231,-0.814,...,4.63,2891432.1,0
...
```

- **Rows**: One per window (~300–400 total, varies by recording lengths)
- **Columns**: 43 total (42 features + `label`)
- **label**: `0` = Control (Non-Parkinson), `1` = Parkinson

---

## Integration with Model Training

The output CSV is ready for direct use with scikit-learn:

```python
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

df = pd.read_csv('backend/ml_data/processed/ready_for_training_features.csv')

X = df.drop('label', axis=1).values
y = df['label'].values

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)
print(f"Accuracy: {model.score(X_test, y_test):.2%}")
```

---

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: openpyxl` | openpyxl not installed | `pip install openpyxl` |
| `FileNotFoundError: DataParkinson/...` | Wrong working directory | Run from `backend/ml_data/scripts/` or use absolute `--parkinson-dir` / `--control-dir` paths |
| `WARNING: Recording has < 100 samples` | File too short for one window | Expected for some validation-adjacent files; they are skipped automatically |
| Output file has class imbalance | 79 Control vs 29 Parkinson recordings | Expected — consider class-weighted training or oversampling at the model training stage |
