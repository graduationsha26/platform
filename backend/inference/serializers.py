"""Django REST Framework serializers for inference API."""

from rest_framework import serializers


class InferenceRequestSerializer(serializers.Serializer):
    """
    Serializer for inference request payload.

    Validates incoming sensor data and ensures correct format.
    Supports both ML model format (6 features) and DL model format (128x6 sequences).
    """

    sensor_data = serializers.ListField(
        required=True,
        help_text="Sensor window: 2D array (window_size, 6) — rows of [aX, aY, aZ, gX, gY, gZ] "
                  "(lgbm: ~67 rows @ 66.67 Hz; DL: 128 rows)",
        allow_empty=False
    )

    def validate_sensor_data(self, value):
        """
        Validate sensor data format.

        Accepts:
        - 2D array with shape (128, 6) for DL models (LSTM, CNN)
        - 1D array with length 6 for ML models (RF, SVM) — [aX, aY, aZ, gX, gY, gZ]

        Detailed shape validation happens in validators.py after model type is known.
        """
        if not isinstance(value, list):
            raise serializers.ValidationError("sensor_data must be a list")

        if len(value) == 0:
            raise serializers.ValidationError("sensor_data cannot be empty")

        # Check if it's a 2D array (DL format) or 1D array (ML format)
        first_element = value[0]

        if isinstance(first_element, list):
            # DL format: 2D array
            if not all(isinstance(row, list) for row in value):
                raise serializers.ValidationError(
                    "For DL models, sensor_data must be a 2D array (all elements must be lists)"
                )
        elif isinstance(first_element, (int, float)):
            # ML format: 1D array with exactly 6 features [aX, aY, aZ, gX, gY, gZ]
            if not all(isinstance(x, (int, float)) for x in value):
                raise serializers.ValidationError(
                    "For ML models, sensor_data must be a 1D array of numbers"
                )
            if len(value) != 6:
                raise serializers.ValidationError(
                    f"ML models require exactly 6 features [aX, aY, aZ, gX, gY, gZ], "
                    f"got {len(value)}"
                )
        else:
            raise serializers.ValidationError(
                "sensor_data must contain either numbers (ML) or nested lists (DL)"
            )

        return value


class InferenceResponseSerializer(serializers.Serializer):
    """
    Serializer for inference response (Feature 053 — BINARY LightGBM).

    Core: prediction (class index), predicted_class, probabilities, model_used, timestamp
    Optional: confidence_score, inference_time_ms, model_version, input_validation
    """

    prediction = serializers.IntegerField(
        min_value=0,
        max_value=1,
        help_text="Predicted class index: 0 (Non-Tremor), 1 (Tremor)"
    )

    predicted_class = serializers.CharField(
        help_text="Predicted class label: Non-Tremor | Tremor"
    )

    probabilities = serializers.DictField(
        child=serializers.FloatField(),
        help_text="Per-class probabilities: {non_tremor, tremor}"
    )

    model_used = serializers.CharField(
        required=False,
        help_text="Model used for inference: lgbm, lstm, cnn_1d"
    )

    confidence_score = serializers.FloatField(
        required=False,
        min_value=0.0,
        max_value=1.0,
        help_text="Max class probability (0.0-1.0)"
    )

    inference_time_ms = serializers.IntegerField(
        required=False,
        min_value=0,
        help_text="Inference duration in milliseconds"
    )

    model_version = serializers.CharField(
        required=False,
        help_text="Model version identifier"
    )

    input_validation = serializers.DictField(
        required=False,
        help_text="Data quality assessment"
    )

    timestamp = serializers.DateTimeField(
        help_text="ISO 8601 timestamp when prediction was generated"
    )
