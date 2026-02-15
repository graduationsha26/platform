"""Django REST Framework serializers for inference API."""

from rest_framework import serializers


class InferenceRequestSerializer(serializers.Serializer):
    """
    Serializer for inference request payload.

    Validates incoming sensor data and ensures correct format.
    Supports both ML model format (18 features) and DL model format (128x6 sequences).
    """

    sensor_data = serializers.ListField(
        required=True,
        help_text="Sensor data: 2D array (128x6) for DL or 1D array (18) for ML",
        allow_empty=False
    )

    def validate_sensor_data(self, value):
        """
        Validate sensor data format.

        Accepts:
        - 2D array with shape (128, 6) for DL models (LSTM, CNN)
        - 1D array with length 18 for ML models (RF, SVM)

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
            # ML format: 1D array
            if not all(isinstance(x, (int, float)) for x in value):
                raise serializers.ValidationError(
                    "For ML models, sensor_data must be a 1D array of numbers"
                )
        else:
            raise serializers.ValidationError(
                "sensor_data must contain either numbers (ML) or nested lists (DL)"
            )

        return value


class InferenceResponseSerializer(serializers.Serializer):
    """
    Serializer for inference response.

    P1 (MVP): prediction, severity, timestamp
    P2: + model_used
    P3: + confidence_score, inference_time_ms, model_version, input_validation
    """

    prediction = serializers.BooleanField(
        help_text="Tremor detected (true) or not detected (false)"
    )

    severity = serializers.IntegerField(
        min_value=0,
        max_value=3,
        help_text="Severity: 0 (none), 1 (mild), 2 (moderate), 3 (severe)"
    )

    model_used = serializers.CharField(
        required=False,
        help_text="Model used for inference: rf, svm, lstm, cnn_1d (P2)"
    )

    confidence_score = serializers.FloatField(
        required=False,
        min_value=0.0,
        max_value=1.0,
        help_text="Model confidence (0.0-1.0) (P3)"
    )

    inference_time_ms = serializers.IntegerField(
        required=False,
        min_value=0,
        help_text="Inference duration in milliseconds (P3)"
    )

    model_version = serializers.CharField(
        required=False,
        help_text="Model version identifier (P3)"
    )

    input_validation = serializers.DictField(
        required=False,
        help_text="Data quality assessment (P3)"
    )

    timestamp = serializers.DateTimeField(
        help_text="ISO 8601 timestamp when prediction was generated"
    )
