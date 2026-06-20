"""
WebSocket authentication helpers for JWT token validation.

This module provides utilities for authenticating WebSocket connections
using JWT tokens passed as query parameters.
"""
import logging
from typing import Optional, Dict
from urllib.parse import parse_qs

from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

User = get_user_model()


def extract_jwt_from_query(scope: Dict) -> Optional[str]:
    """
    Extract JWT token from WebSocket query parameters.

    WebSocket URL format: /ws/tremor-data/123/?token=<JWT_ACCESS_TOKEN>

    Args:
        scope: ASGI scope dictionary containing connection metadata

    Returns:
        JWT token string if found, None otherwise
    """
    try:
        # Parse query string from scope
        query_string = scope.get('query_string', b'').decode('utf-8')
        query_params = parse_qs(query_string)

        # Extract token parameter
        token_list = query_params.get('token', [])
        if not token_list:
            logger.debug("No 'token' parameter found in WebSocket query string")
            return None

        # Return first token value
        token = token_list[0]
        logger.debug("JWT token extracted from query parameters")
        return token

    except Exception as e:
        logger.error(f"Error extracting JWT from query parameters: {e}", exc_info=True)
        return None


@sync_to_async
def validate_jwt_token(token: str) -> Optional[User]:
    """
    Validate JWT access token and retrieve associated user.

    This function:
    1. Validates the JWT token using SimpleJWT
    2. Extracts user_id from token payload
    3. Retrieves and returns the User object

    Args:
        token: JWT access token string

    Returns:
        User object if token is valid and user exists, None otherwise
    """
    try:
        # Validate token and decode payload
        access_token = AccessToken(token)
        user_id = access_token['user_id']

        # Retrieve user from database
        user = User.objects.get(id=user_id)
        logger.debug(f"JWT token validated successfully for user {user_id}")
        return user

    except TokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        return None
    except InvalidToken as e:
        logger.warning(f"Invalid JWT token format: {e}")
        return None
    except User.DoesNotExist:
        logger.warning(f"User not found for token user_id: {user_id}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error validating JWT token: {e}", exc_info=True)
        return None
