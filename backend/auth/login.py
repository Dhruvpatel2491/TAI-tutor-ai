"""
Login module for TAI Tutor AI.

This module handles user login verification and profile retrieval.
Uses file-backed storage for user credentials with PBKDF2-SHA256 password hashing.
"""

import json
import logging
from pathlib import Path
from typing import Optional

# Import with fallback for running as script
try:
    from config import USER_DATA_DIR
    from auth.auth_utils import verify_password
except ImportError:
    from config import USER_DATA_DIR
    from auth.auth_utils import verify_password

logger = logging.getLogger("backend.auth.login")

# User data storage directory
_ROOT_USER_DIR = USER_DATA_DIR / "login_register"


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
# User Verification
# =============================================================================

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
        logger.debug(f"User not found: {email}")
        return False
    
    try:
        with open(p, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        
        salt_b64 = data.get("salt")
        expected_hash_b64 = data.get("password_hash")
        
        if not salt_b64 or not expected_hash_b64:
            logger.warning(f"User {email} has incomplete credentials data")
            return False
        
        return verify_password(password, expected_hash_b64, salt_b64)
    except Exception as e:
        logger.error(f"Error verifying user {email}: {e}")
        return False


def user_exists(email: str) -> bool:
    """
    Check if a user exists.
    
    Args:
        email: User email to check
    
    Returns:
        True if user exists, False otherwise
    """
    email = (email or "").strip().lower()
    return _user_file_path(email).exists()


def get_user_profile(email: str) -> dict:
    """
    Get user profile data from disk.
    
    Args:
        email: User email
    
    Returns:
        Dict with name, email, created_at, or minimal dict if not found
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
    except Exception as e:
        logger.error(f"Error reading profile for {email}: {e}")
        return {"email": email, "name": "N/A"}


def get_user_data(email: str) -> Optional[dict]:
    """
    Get full user data from disk (internal use, includes password hash).
    
    Args:
        email: User email
    
    Returns:
        Full user data dict or None if not found
    """
    if not email:
        return None
    
    email = email.strip().lower()
    p = _user_file_path(email)
    
    if not p.exists():
        return None
    
    try:
        with open(p, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as e:
        logger.error(f"Error reading user data for {email}: {e}")
        return None
