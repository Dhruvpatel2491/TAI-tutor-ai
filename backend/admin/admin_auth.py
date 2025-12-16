"""
Admin authentication module for TAI Tutor AI.

This module handles admin password verification using environment variables.
Provides simple password verification for admin access.
"""

import logging
from typing import Optional

# Import with fallback for running as script
try:
    from config import ADMIN_PASSWORD
    from auth.auth_utils import verify_jwt, extract_bearer_token
except ImportError:
    from config import ADMIN_PASSWORD
    from auth.auth_utils import verify_jwt, extract_bearer_token

logger = logging.getLogger("backend.admin.admin_auth")


def verify_admin_password(password: str) -> bool:
    """
    Verify admin password against environment variable.
    
    Args:
        password: Admin password to verify
    
    Returns:
        True if password matches configured admin password
    """
    if not ADMIN_PASSWORD:
        logger.warning("Admin password not configured")
        return False
    
    return password == ADMIN_PASSWORD


def verify_user_and_admin(authorization_header: Optional[str], admin_password: str) -> tuple[bool, Optional[dict]]:
    """
    Verify both user's bearer token and admin password.
    
    Args:
        authorization_header: Authorization header with bearer token
        admin_password: Admin password to verify
    
    Returns:
        Tuple of (is_valid: bool, user_claims: dict or None)
    """
    # Extract and verify bearer token
    token = extract_bearer_token(authorization_header)
    if not token:
        logger.warning("Missing bearer token in admin request")
        return False, None
    
    claims = verify_jwt(token)
    if not claims:
        logger.warning("Invalid or expired bearer token in admin request")
        return False, None
    
    # Verify admin password
    if not verify_admin_password(admin_password):
        logger.warning(f"Invalid admin password from user: {claims.get('sub')}")
        return False, None
    
    return True, claims
