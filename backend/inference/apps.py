"""Django app configuration for inference."""

from django.apps import AppConfig


class InferenceConfig(AppConfig):
    """Configuration for the inference Django app."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'inference'
    verbose_name = 'ML/DL Inference'

    def ready(self):
        """
        Perform app initialization.

        Called when Django starts. Can be used for:
        - Registering signals
        - Preloading models (if needed for performance)
        - Setting up monitoring
        """
        pass
