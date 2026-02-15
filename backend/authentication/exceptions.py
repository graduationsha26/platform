"""
Custom exceptions for authentication app.
"""
from rest_framework.exceptions import APIException
from rest_framework import status


class InvalidCredentialsException(APIException):
    """Exception raised when login credentials are invalid."""

    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = 'Invalid email or password.'
    default_code = 'invalid_credentials'


class TokenExpiredException(APIException):
    """Exception raised when JWT token has expired."""

    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = 'Token has expired. Please refresh your token or login again.'
    default_code = 'token_expired'


class InactiveAccountException(APIException):
    """Exception raised when user account is inactive."""

    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'Account is inactive. Please contact support.'
    default_code = 'inactive_account'
