"""Django REST Framework views for inference API."""

from rest_framework.views import APIView
from rest_framework.response import Response
from authentication.permissions import IsDoctorOrAdmin
from rest_framework import status
from django.utils import timezone

from .serializers import InferenceRequestSerializer, InferenceResponseSerializer
from .services import ModelLoader, PreprocessingService, InferenceService, InputValidationService
from .exceptions import (
    InferenceError, ModelNotFoundError, ModelLoadError,
    InvalidInputError, InferenceTimeoutError
)
from .models import InferenceLog

import logging

logger = logging.getLogger(__name__)


class InferenceAPIView(APIView):
    """
    API endpoint for ML/DL model inference.

    POST /api/inference/
    Query parameters:
        - model: Optional model selection (lgbm, lstm, cnn_1d); default lgbm

    Request body:
        - sensor_data: 2-D array (window_size, 6) — [aX, aY, aZ, gX, gY, gZ]

    Response (Feature 051 — 3-class LightGBM):
        - prediction: int class index (0=Non-Tremor, 1=Tremor, 2=Voluntary)
        - predicted_class: string label
        - probabilities: {non_tremor, tremor, voluntary}
        - model_used: string
        - timestamp: ISO 8601
        - (optional) confidence_score, inference_time_ms, model_version, input_validation
    """

    permission_classes = [IsDoctorOrAdmin]

    def post(self, request):
        """
        Handle inference request.

        Workflow:
        1. Validate request payload
        2. Parse model selection from query parameter (default model for US1)
        3. Load model (with caching)
        4. Preprocess input data
        5. Execute inference
        6. Map severity
        7. Log to database (async)
        8. Return response
        """
        try:
            # T034: Authentication check (handled by permission_classes)
            # T045: Request size limit (Django has built-in DATA_UPLOAD_MAX_MEMORY_SIZE)
            # Additional check for 100KB limit
            content_length = request.META.get('CONTENT_LENGTH')
            if content_length and int(content_length) > 100 * 1024:  # 100KB
                return Response(
                    {
                        "error": "Request payload too large. Maximum 100KB allowed.",
                        "error_code": "PAYLOAD_TOO_LARGE"
                    },
                    status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
                )

            # T035: Validate request payload
            serializer = InferenceRequestSerializer(data=request.data)
            if not serializer.is_valid():
                logger.warning(
                    f"Invalid inference request from user {request.user.id}: "
                    f"{serializer.errors}"
                )
                return Response(
                    {
                        "error": "Invalid input data",
                        "error_code": "INVALID_INPUT_SHAPE",
                        "details": serializer.errors
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            sensor_data = serializer.validated_data['sensor_data']

            # T048-T051: Model selection (US2) - parse query parameter or use default
            from django.conf import settings

            # T048: Extract model from query parameter, default to settings
            model_name = request.query_params.get('model', settings.DEFAULT_INFERENCE_MODEL)

            # T049: Validate model name
            valid_models = ['lgbm', 'lstm', 'cnn_1d']
            if model_name not in valid_models:
                logger.warning(
                    f"Invalid model name from user {request.user.id}: {model_name}"
                )
                return Response(
                    {
                        "error": f"Invalid model name: {model_name}",
                        "error_code": "MODEL_NOT_FOUND",
                        "available_models": valid_models,
                        "suggestion": "Please select from available models"
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # T050: Model availability check happens in ModelCache.get_model()
            # It will raise ModelNotFoundError if file doesn't exist

            logger.info(
                f"Inference request from user {request.user.id} "
                f"using model {model_name}"
            )

            # T037-T038: Execute inference using InferenceService
            # The service handles: model loading, preprocessing, prediction, severity mapping
            inference_service = InferenceService()

            import numpy as np
            sensor_array = np.array(sensor_data)

            # T068: Assess input data quality (US3 - P3 feature)
            input_validation_service = InputValidationService()
            input_validation = input_validation_service.assess_data_quality(sensor_array)

            # Validate sensor values (strict validation - raises error for invalid data)
            from .validators import validate_sensor_values
            try:
                validate_sensor_values(sensor_array)
            except InvalidInputError:
                # If strict validation fails, allow degraded data to proceed with warning
                # but only if it's not completely invalid (no NaN/Inf)
                if not input_validation['missing_values']:
                    logger.warning(
                        f"Degraded data quality for user {request.user.id}: "
                        f"{input_validation['data_quality']}"
                    )
                else:
                    raise  # Re-raise if missing values (too invalid)

            # Execute prediction with metadata (US3 - P3 feature)
            result = inference_service.predict(
                model_name=model_name,
                sensor_data=sensor_array,
                include_metadata=True  # US3: Include P3 metadata
            )

            # Construct 3-class response (Feature 051: LightGBM Non-Tremor/Tremor/Voluntary)
            response_data = {
                'prediction': result['prediction'],            # class index 0/1/2
                'predicted_class': result['predicted_class'],  # label string
                'probabilities': result['probabilities'],      # {non_tremor, tremor, voluntary}
                'model_used': model_name,
                'timestamp': timezone.now().isoformat()
            }

            # T069: Add P3 metadata if available
            if 'confidence_score' in result:
                response_data['confidence_score'] = result['confidence_score']
            if 'inference_time_ms' in result:
                response_data['inference_time_ms'] = result['inference_time_ms']
            if 'model_version' in result:
                response_data['model_version'] = result['model_version']

            # T069: Add input validation results (US3)
            response_data['input_validation'] = input_validation

            # T042: Log successful inference
            logger.info(
                f"Inference successful for user {request.user.id}: "
                f"class={result['prediction']} ({result['predicted_class']})"
            )

            # Audit log. The legacy InferenceLog schema keeps non-null prediction(bool) +
            # severity(int); we reuse them without a migration:
            #   prediction = is-Tremor (class 1), severity = class index (0/1/2).
            InferenceLog.objects.create(
                user=request.user,
                model_used=model_name,
                prediction=result['is_tremor'],
                severity=result['prediction'],
                confidence_score=result.get('confidence_score'),
                inference_time_ms=result.get('inference_time_ms'),
                input_shape=str(sensor_array.shape),
                # timestamp is auto-set by auto_now_add
            )

            # Return successful response
            response_serializer = InferenceResponseSerializer(data=response_data)
            if response_serializer.is_valid():
                return Response(
                    response_serializer.validated_data,
                    status=status.HTTP_200_OK
                )
            else:
                # This shouldn't happen, but handle it gracefully
                return Response(response_data, status=status.HTTP_200_OK)

        # T041: Error handling for all exception types
        except InvalidInputError as e:
            logger.warning(f"Invalid input from user {request.user.id}: {e.message}")
            return Response(
                {"error": e.message, "error_code": e.error_code},
                status=status.HTTP_400_BAD_REQUEST
            )

        except ModelNotFoundError as e:
            logger.error(f"Model not found for user {request.user.id}: {e.message}")
            return Response(
                {
                    "error": e.message,
                    "error_code": e.error_code,
                    "available_models": ["lgbm", "lstm", "cnn_1d"],
                    "suggestion": "Train the model first: python backend/ml_models/train.py"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        except ModelLoadError as e:
            logger.error(f"Model loading failed for user {request.user.id}: {e.message}")
            return Response(
                {"error": e.message, "error_code": e.error_code},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        except InferenceTimeoutError as e:
            logger.error(f"Inference timeout for user {request.user.id}: {e.message}")
            return Response(
                {"error": e.message, "error_code": e.error_code},
                status=status.HTTP_504_GATEWAY_TIMEOUT
            )

        except Exception as e:
            # Catch-all for unexpected errors
            logger.error(
                f"Unexpected error during inference for user {request.user.id}: {str(e)}",
                exc_info=True
            )
            return Response(
                {
                    "error": "Internal server error during inference",
                    "error_code": "INTERNAL_ERROR"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
