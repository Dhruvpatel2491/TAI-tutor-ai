"""
Authentication utilities for TAI Tutor AI.

This module provides:
- JWT token creation and verification
- Password hashing and verification using PBKDF2-SHA256
- Request authentication helpers
"""

import os
import time
import base64
import hashlib
import logging
from typing import Optional, Dict, Tuple

try:
    import jwt
except ImportError:
    raise ImportError("PyJWT is required. Install with: pip install PyJWT")

# Import with fallback for running as script
try:
    from config import (
        JWT_SECRET,
        JWT_ALGORITHM,
        JWT_EXP_SECONDS,
        AUTH_DISABLED,
        DEFAULT_DEV_USER,
    )
except ImportError:
    from config import (
        JWT_SECRET,
        JWT_ALGORITHM,
        JWT_EXP_SECONDS,
        AUTH_DISABLED,
        DEFAULT_DEV_USER,
    )

logger = logging.getLogger("backend.auth.auth_utils")


# =============================================================================
# Password Hashing
# =============================================================================

def hash_password(password: str, salt: Optional[bytes] = None) -> Tuple[str, str]:
    """
    Hash password using PBKDF2-SHA256.
    
    Args:
        password: Plain text password
        salt: Optional salt bytes (generated if not provided)
    
    Returns:
        Tuple of (password_hash_b64, salt_b64)
    """
    if salt is None:
        salt = os.urandom(16)
    
    # PBKDF2 with SHA256, 100k iterations
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    
    return (
        base64.b64encode(dk).decode("utf-8"),
        base64.b64encode(salt).decode("utf-8")
    )


def verify_password(password: str, stored_hash_b64: str, salt_b64: str) -> bool:
    """
    Verify a password against stored hash.
    
    Args:
        password: Plain text password to verify
        stored_hash_b64: Stored password hash (base64)
        salt_b64: Salt used in hashing (base64)
    
    Returns:
        True if password matches, False otherwise
    """
    try:
        salt = base64.b64decode(salt_b64)
        computed_hash, _ = hash_password(password, salt)
        return computed_hash == stored_hash_b64
    except Exception as e:
        logger.error(f"Password verification failed: {e}")
        return False


# =============================================================================
# JWT Token Management
# =============================================================================

def create_jwt_for_user(user_id: str, exp_seconds: Optional[int] = None) -> str:
    """
    Create a signed JWT for the given user_id.
    
    Args:
        user_id: User identifier (email)
        exp_seconds: Token expiration time in seconds
    
    Returns:
        Signed JWT token string
    """
    if exp_seconds is None:
        exp_seconds = JWT_EXP_SECONDS
    
    payload = {
        "sub": str(user_id),
        "iat": int(time.time()),
        "exp": int(time.time()) + int(exp_seconds)
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    # PyJWT >=2 returns str, older may return bytes
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    
    return token


def verify_jwt(token: str) -> Optional[Dict]:
    """
    Verify token and return payload dict or None if invalid/expired.
    
    Args:
        token: JWT token string
    
    Returns:
        Token payload dict or None if invalid
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.debug("JWT token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.debug(f"Invalid JWT token: {e}")
        return None
    except Exception:
        return None


def extract_bearer_token(authorization_header: Optional[str]) -> Optional[str]:
    """
    Extract bearer token from Authorization header.
    
    Args:
        authorization_header: Authorization header value
    
    Returns:
        Token string or None
    """
    if not authorization_header:
        return None
    
    parts = authorization_header.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    
    return None


# =============================================================================
# Request Authentication Helpers
# =============================================================================

def extract_email_from_headers(headers) -> Optional[str]:
    """
    Try common headers used by auth proxies to carry the authenticated user's email.
    
    Args:
        headers: Request headers object
    
    Returns:
        Email string or None
    """
    for h in ("X-User-Email", "X-Forwarded-User", "X-Auth-User", "X-Forwarded-Email"):
        val = headers.get(h)
        if val:
            return val
    
    # Try Authorization: Bearer <token>; if token looks like an email, return it
    auth = headers.get("Authorization") or headers.get("authorization")
    if auth and auth.startswith("Bearer "):
        token = auth.split(" ", 1)[1].strip()
        if "@" in token and " " not in token:
            return token
    
    return None


def get_user_from_request(req) -> Dict:
    """
    Return user info from request.
    
    Args:
        req: Flask request object
    
    Returns:
        Dict with auth_disabled, default_dev_user, and user_id keys
    """
    if AUTH_DISABLED:
        return {
            "auth_disabled": True,
            "default_dev_user": DEFAULT_DEV_USER,
            "user_id": DEFAULT_DEV_USER
        }
    
    # Auth enabled: extract login email from headers
    email = extract_email_from_headers(req.headers)
    return {
        "auth_disabled": False,
        "default_dev_user": DEFAULT_DEV_USER,
        "user_id": email
    }


def get_user_id_from_token(authorization_header: Optional[str]) -> Optional[str]:
    """
    Extract and validate user_id from Authorization Bearer token.
    
    Args:
        authorization_header: Authorization header value
    
    Returns:
        User ID (sub claim) or None if invalid
    """
    token = extract_bearer_token(authorization_header)
    if not token:
        return None
    
    claims = verify_jwt(token)
    if not claims:
        return None
    
    return claims.get("sub")
