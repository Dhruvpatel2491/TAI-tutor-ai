"""
Authentication module for TAI Tutor AI.

This module provides user authentication, registration, and JWT token management.
"""

from auth.auth_utils import (
    create_jwt_for_user,
    verify_jwt,
    extract_bearer_token,
    hash_password,
    verify_password,
    get_user_from_request,
    extract_email_from_headers,
)

from auth.login import (
    verify_user,
    user_exists,
    get_user_profile,
)

from auth.register import (
    register_user,
)

__all__ = [
    # JWT utilities
    "create_jwt_for_user",
    "verify_jwt",
    "extract_bearer_token",
    # Password utilities
    "hash_password",
    "verify_password",
    # Request helpers
    "get_user_from_request",
    "extract_email_from_headers",
    # Login
    "verify_user",
    "user_exists",
    "get_user_profile",
    # Registration
    "register_user",
]
