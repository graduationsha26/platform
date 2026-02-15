"""Custom exceptions for inference app."""


class InferenceError(Exception):
    """
    Base exception for inference errors.

    All inference-related exceptions inherit from this class
    for consistent error handling and logging.
    """
    status_code = 500
    default_message = "Inference error occurred"
    error_code = "INTERNAL_ERROR"

    def __init__(self, message: str = None, **kwargs):
        self.message = message or self.default_message
        self.extra_data = kwargs
        super().__init__(self.message)


class ModelNotFoundError(InferenceError):
    """
    Raised when requested model doesn't exist.

    HTTP 400 Bad Request - client error (invalid model selection)
    """
    status_code = 400
    default_message = "Requested model not available"
    error_code = "MODEL_NOT_FOUND"


class ModelLoadError(InferenceError):
    """
    Raised when model loading fails (corrupted file, etc.).

    HTTP 503 Service Unavailable - server error (temporary issue)
    """
    status_code = 503
    default_message = "Model loading failed"
    error_code = "MODEL_UNAVAILABLE"


class InvalidInputError(InferenceError):
    """
    Raised when input data is invalid.

    HTTP 400 Bad Request - client error (invalid data format/shape)
    """
    status_code = 400
    default_message = "Invalid input data"
    error_code = "INVALID_INPUT_SHAPE"


class InferenceTimeoutError(InferenceError):
    """
    Raised when inference takes longer than timeout limit (>5 seconds).

    HTTP 504 Gateway Timeout - server error (processing too slow)
    """
    status_code = 504
    default_message = "Inference timeout exceeded"
    error_code = "INFERENCE_TIMEOUT"
