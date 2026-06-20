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
            'code': getattr(exc, 'default_code', 'error'),
            'details': {}
        }

        # Add details if available
        if hasattr(exc, 'detail'):
            if isinstance(exc.detail, dict):
                error_data['details'] = exc.detail
            elif isinstance(exc.detail, list):
                error_data['details'] = {'messages': exc.detail}
            else:
                # Single string detail
                error_data['details'] = {'message': str(exc.detail)}

        # Add request context for debugging (optional)
        if context and 'request' in context:
            request = context['request']
            error_data['details']['path'] = request.path
            error_data['details']['method'] = request.method

        response.data = error_data

    return response
