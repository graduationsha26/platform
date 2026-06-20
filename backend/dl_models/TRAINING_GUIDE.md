# DL Model Training Guide - TensorFlow Compatibility

## Overview

This guide explains how to train the LSTM and 1D-CNN models in a Python 3.9-3.12 environment (required for TensorFlow compatibility).

**Current Environment Issue**: Python 3.14.2 is too new for TensorFlow (requires 3.9-3.12)

**Status**:
- ✅ Training scripts ready: `train_lstm.py`, `train_cnn_1d.py`
- ✅ Training data ready: `backend/ml_data/processed/*.npy` (4.3 MB total)
- ⚠ TensorFlow not installable in Python 3.14.2

---

## Quick Start (If You Have Python 3.11)

If you have Python 3.11 available via `py` launcher on Windows:

```bash
# Check available Python versions
py --list

# If Python 3.11 is available, use it directly:
py -3.11 -m pip install tensorflow>=2.13.0 numpy scikit-learn

# Train LSTM model
py -3.11 backend/dl_models/scripts/train_lstm.py

# Train 1D-CNN model
py -3.11 backend/dl_models/scripts/train_cnn_1d.py

# Re-run full comparison (can use current Python for this)
python backend/model_comparison/scripts/compare_all_models.py
```

---

## Option 1: Using Conda (Recommended)

### Step 1: Install Miniconda (if not already installed)

Download from: https://docs.conda.io/en/latest/miniconda.html

```bash
# Verify conda installation
conda --version
```

### Step 2: Create TensorFlow-Compatible Environment

```bash
# Create new environment with Python 3.11
conda create -n tremoai-dl python=3.11 -y

# Activate environment
conda activate tremoai-dl

# Install required packages
pip install tensorflow>=2.13.0
pip install numpy scikit-learn matplotlib

# Verify TensorFlow installation
python -c "import tensorflow as tf; print(f'TensorFlow {tf.__version__} installed successfully')"
```

### Step 3: Train Models

```bash
# Make sure you're in the project root directory
cd "C:\Data from HDD\Graduation Project\Platform"

# Train LSTM model (will take 5-15 minutes depending on hardware)
python backend/dl_models/scripts/train_lstm.py

# Train 1D-CNN model (will take 5-15 minutes)
python backend/dl_models/scripts/train_cnn_1d.py

# Deactivate when done
conda deactivate
```

### Step 4: Re-run Comparison (in your main Python 3.14 environment)

```bash
# Switch back to main environment
# TensorFlow is optional for comparison - model_loader handles gracefully

python backend/model_comparison/scripts/compare_all_models.py
```

---

## Option 2: Using pyenv (Alternative)

If you prefer pyenv:

```bash
# Install Python 3.11
pyenv install 3.11.7

# Create virtual environment
pyenv virtualenv 3.11.7 tremoai-dl

# Activate
pyenv activate tremoai-dl

# Install packages
pip install tensorflow>=2.13.0 numpy scikit-learn matplotlib

# Train models (same as above)
python backend/dl_models/scripts/train_lstm.py
python backend/dl_models/scripts/train_cnn_1d.py

# Deactivate
pyenv deactivate
```

---

## Option 3: Using venv with Separate Python Installation

If you install Python 3.11 separately:

```bash
# Download Python 3.11 from python.org
# Install to custom location (e.g., C:\Python311)

# Create virtual environment
C:\Python311\python.exe -m venv venv-dl

# Activate (Windows)
venv-dl\Scripts\activate

# Install packages
pip install tensorflow>=2.13.0 numpy scikit-learn matplotlib

# Train models
python backend/dl_models/scripts/train_lstm.py
python backend/dl_models/scripts/train_cnn_1d.py

# Deactivate
deactivate
```

---

## Expected Training Output

### LSTM Training

```
======================================================================
LSTM Model Training
======================================================================
[INFO] TensorFlow version: 2.15.0
[INFO] No GPU detected, using CPU
[INFO] Loading training data from backend/ml_data/processed/...
[INFO] Train set: 440 samples, 100 timesteps, 6 features
[INFO] Test set: 110 samples, 100 timesteps, 6 features
[INFO] Validating input data...
[OK] Data validation passed
[INFO] Splitting training data (80/20 train/validation)...
[INFO] Train: 352 samples, Validation: 88 samples
[INFO] Building LSTM model...
[INFO] Model architecture:
  - LSTM(64, return_sequences=True) + Dropout(0.3)
  - LSTM(32) + Dropout(0.3)
  - Dense(1, sigmoid)
[INFO] Total parameters: 40,609
[INFO] Starting training (max_epochs=100, batch_size=32)...
...
[INFO] Training complete!
[INFO] Epochs trained: 45
[INFO] Evaluating on test set...
[INFO] Test Accuracy: 91.8%
[INFO] Precision: 85.3%
[INFO] Recall: 78.6%
[INFO] F1-Score: 81.8%
[WARNING] Model achieved 91.8%, below 95% threshold
[WARNING] Model will still be exported for analysis
[INFO] Model saved: backend/dl_models/models/lstm_model.h5
[INFO] Metadata saved: backend/dl_models/models/lstm_model.json
======================================================================
Training completed in 142.35 seconds
LSTM model ready for deployment
======================================================================
```

### 1D-CNN Training

Similar output with different architecture details and potentially different accuracy.

---

## Expected Model Files After Training

After successful training, you should see:

```
backend/dl_models/models/
├── lstm_model.h5          (~500 KB - trained LSTM model)
├── lstm_model.json        (~5 KB - LSTM metadata)
├── cnn_1d_model.h5        (~1 MB - trained CNN model)
└── cnn_1d_model.json      (~5 KB - CNN metadata)
```

---

## Re-running Full Comparison

Once both DL models are trained:

```bash
# From project root, using your main Python 3.14 environment
python backend/model_comparison/scripts/compare_all_models.py

# Expected output:
# ✓ Loaded Random Forest (ML)
# ✓ Loaded SVM (ML)
# ✓ Loaded LSTM (DL)
# ✓ Loaded 1D-CNN (DL)
# Loaded 4/4 models successfully
```

This will generate updated reports with all 4 models compared.

---

## Troubleshooting

### Issue: "No module named 'tensorflow'"

**Solution**: Make sure you're in the correct environment where TensorFlow is installed.

```bash
# Verify current Python
python --version

# Verify TensorFlow
python -c "import tensorflow"
```

### Issue: Training is very slow

**Cause**: Training on CPU without GPU acceleration.

**Solutions**:
1. **Reduce epochs**: Add `--epochs 50` flag (models use early stopping anyway)
2. **Accept slower training**: DL training on CPU takes 5-20 minutes per model
3. **Use GPU**: If you have NVIDIA GPU, install `tensorflow-gpu` version

### Issue: "Failed to load sequence data"

**Check data exists**:
```bash
ls -lh backend/ml_data/processed/
# Should see: train_sequences.npy, test_sequences.npy, etc.
```

If missing, Feature 004 (Data Preparation) needs to be completed first.

### Issue: Training crashes with OOM (Out of Memory)

**Reduce batch size**:
```bash
# Edit train_lstm.py or train_cnn_1d.py
# Change: batch_size=32 → batch_size=16
```

---

## Performance Expectations

### Training Time (CPU)
- LSTM: 5-15 minutes (depending on CPU)
- 1D-CNN: 5-15 minutes

### Training Time (GPU)
- LSTM: 1-3 minutes
- 1D-CNN: 1-3 minutes

### Model Accuracy Estimates
Based on current data:
- RF (ML): 88.2% ✓ (already trained)
- SVM (ML): 87.3% ✓ (already trained)
- LSTM (DL): ~90-93% (estimated)
- 1D-CNN (DL): ~90-93% (estimated)

**Note**: All models currently below 95% threshold. This indicates need for:
- Data augmentation
- Hyperparameter tuning
- More training samples
- Feature engineering

---

## Next Steps After Training

1. **Re-run comparison**: `python backend/model_comparison/scripts/compare_all_models.py`
2. **Review reports**: Check `backend/model_comparison/reports/comparison_report.md`
3. **Present to supervisor**: PDF available at `comparison_report.pdf`
4. **Document decision**: Use `document_decision.py` to record deployment choice

---

## Contact

If you encounter issues not covered here, check:
- TensorFlow documentation: https://www.tensorflow.org/install
- Training script comments: Detailed error messages in code
- Comparison system README: `backend/model_comparison/README.md`
