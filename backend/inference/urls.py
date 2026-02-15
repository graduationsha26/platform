"""URL routing for inference app."""

from django.urls import path
from .views import InferenceAPIView

app_name = 'inference'

urlpatterns = [
    # POST /api/inference/ - Main inference endpoint
    # Query parameter: ?model=rf|svm|lstm|cnn_1d (optional, defaults to settings)
    path('', InferenceAPIView.as_view(), name='inference'),
]
