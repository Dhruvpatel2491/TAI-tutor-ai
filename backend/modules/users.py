"""
Users module for TAI Tutor AI.

This module handles user authentication, registration, and profile management.
Uses file-backed storage for user credentials with PBKDF2-SHA256 password hashing.
"""

import os
import time
import base64
import hashlib
import json
import datetime
import logging
from typing import Optional, Dict
from pathlib import Path

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
        USER_DATA_DIR,
    )
except ImportError:
    from config import (
        JWT_SECRET,
        JWT_ALGORITHM,
        JWT_EXP_SECONDS,
        AUTH_DISABLED,
        DEFAULT_DEV_USER,
        USER_DATA_DIR,
    )

logger = logging.getLogger("backend.modules.users")

# User data storage directory
_ROOT_USER_DIR = USER_DATA_DIR / "login_register"


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
# User Storage Helpers
# =============================================================================

def _ensure_user_dir():
    """Ensure user data directory exists."""
    try:
        _ROOT_USER_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


def _safe_filename_for_email(email: str) -> str:
    """Convert email to safe filename."""
    return email.replace("@", "__at__").replace(".", "__dot__")


def _user_file_path(email: str) -> Path:
    """Get file path for user data."""
    _ensure_user_dir()
    fn = _safe_filename_for_email(email.strip().lower()) + ".json"
    return _ROOT_USER_DIR / fn


# =============================================================================
# User Registration and Authentication
# =============================================================================

def register_user(email: str, password: str, name: str = "") -> dict:
    """
    Register a user by saving a salted PBKDF2-SHA256 password hash to disk.
    
    Args:
        email: User email address
        password: Plain text password
        name: User's display name
    
    Returns:
        Dict with stored user metadata
    
    Raises:
        ValueError: If input is invalid or user already exists
    """
    if not email or not password:
        raise ValueError("email and password required")
    
    email = email.strip().lower()
    name = name.strip()
    p = _user_file_path(email)
    
    if p.exists():
        raise ValueError("user already exists")
    
    # Generate salt and hash password
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    
    payload = {
        "name": name,
        "email": email,
        "salt": base64.b64encode(salt).decode("utf-8"),
        "password_hash": base64.b64encode(dk).decode("utf-8"),
        "created_at": datetime.datetime.utcnow().isoformat() + "Z",
    }
    
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    
    logger.info(f"Registered new user: {email}")
    return payload


def verify_user(email: str, password: str) -> bool:
    """
    Verify a user's password.
    
    Args:
        email: User email
        password: Plain text password to verify
    
    Returns:
        True if password matches, False otherwise
    """
    if not email or not password:
        return False
    
    email = email.strip().lower()
    p = _user_file_path(email)
    
    if not p.exists():
        return False
    
    try:
        with open(p, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        
        salt_b64 = data.get("salt")
        expected_b64 = data.get("password_hash")
        
        if not salt_b64 or not expected_b64:
            return False
        
        salt = base64.b64decode(salt_b64)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
        got_b64 = base64.b64encode(dk).decode("utf-8")
        
        return got_b64 == expected_b64
    except Exception:
        return False


def user_exists(email: str) -> bool:
    """Check if a user exists."""
    email = (email or "").strip().lower()
    return _user_file_path(email).exists()


def get_user_profile(email: str) -> dict:
    """
    Get user profile data from disk.
    
    Args:
        email: User email
    
    Returns:
        Dict with name, email, created_at, or empty dict if not found
    """
    if not email:
        return {}
    
    email = email.strip().lower()
    p = _user_file_path(email)
    
    if not p.exists():
        return {"email": email, "name": "N/A"}
    
    try:
        with open(p, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return {
            "email": data.get("email", email),
            "name": data.get("name", "N/A"),
            "created_at": data.get("created_at", ""),
        }
    except Exception:
        return {"email": email, "name": "N/A"}


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
