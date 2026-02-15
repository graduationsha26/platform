"""
ML/DL Inference API Endpoint

Django app for deploying trained machine learning and deep learning models
for real-time tremor prediction and severity assessment.

Features:
- Model loading and caching for .pkl (scikit-learn) and .h5 (TensorFlow) models
- Automatic preprocessing based on model type (ML: 18 features, DL: 128x6 sequences)
- REST API endpoint: POST /api/inference/
- Model selection via query parameter
- Enhanced metadata (confidence, inference time, input validation)
"""

default_app_config = 'inference.apps.InferenceConfig'
