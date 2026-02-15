"""
Custom exception handler for DRF to format all errors consistently.
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response


def custom_exception_handler(exc, context):
    """
    Custom exception handler that formats all errors as:
    {
        "error": "Human-readable message",
        "code": "machine_readable_code",
        "details": {...}  # Optional
    }
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    if response is not None:
        # Format the error response
        error_data = {
            'error': str(exc),
            'code': getattr(exc, 'default_code', 'error')
        }

        # Add details if available
        if hasattr(exc, 'detail'):
            if isinstance(exc.detail, dict):
                error_data['details'] = exc.detail
            elif isinstance(exc.detail, list):
                error_data['details'] = {'messages': exc.detail}

        response.data = error_data

    return response
