"""
Registration module for TAI Tutor AI.

This module handles user registration.
Uses file-backed storage for user credentials with PBKDF2-SHA256 password hashing.
"""

import os
import json
import datetime
import logging
from pathlib import Path

# Import with fallback for running as script
try:
    from config import USER_DATA_DIR
    from auth.auth_utils import hash_password
except ImportError:
    from config import USER_DATA_DIR
    from auth.auth_utils import hash_password

logger = logging.getLogger("backend.auth.register")

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
# User Registration
# =============================================================================

def register_user(email: str, password: str, name: str = "") -> dict:
    """
    Register a user by saving a salted PBKDF2-SHA256 password hash to disk.
    
    Args:
        email: User email address
        password: Plain text password
        name: User's display name
    
    Returns:
        Dict with stored user metadata (excluding password hash)
    
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
    password_hash_b64, salt_b64 = hash_password(password)
    
    payload = {
        "name": name,
        "email": email,
        "salt": salt_b64,
        "password_hash": password_hash_b64,
        "created_at": datetime.datetime.utcnow().isoformat() + "Z",
    }
    
    # Atomic write: write to temp file, then rename
    tmp_path = p.with_suffix(".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        os.replace(tmp_path, p)
    except Exception as e:
        # Clean up temp file if it exists
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass
        raise e
    
    logger.info(f"Registered new user: {email}")
    
    # Return safe metadata (no password hash)
    return {
        "name": name,
        "email": email,
        "created_at": payload["created_at"],
    }


def update_user_profile(email: str, name: str = None) -> dict:
    """
    Update user profile data.
    
    Args:
        email: User email
        name: New display name (optional)
    
    Returns:
        Updated user profile dict
    
    Raises:
        ValueError: If user does not exist
    """
    if not email:
        raise ValueError("email required")
    
    email = email.strip().lower()
    p = _user_file_path(email)
    
    if not p.exists():
        raise ValueError("user not found")
    
    try:
        with open(p, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        
        # Update fields
        if name is not None:
            data["name"] = name.strip()
        
        data["updated_at"] = datetime.datetime.utcnow().isoformat() + "Z"
        
        # Atomic write
        tmp_path = p.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        os.replace(tmp_path, p)
        
        logger.info(f"Updated profile for user: {email}")
        
        return {
            "name": data.get("name", ""),
            "email": email,
            "created_at": data.get("created_at", ""),
            "updated_at": data.get("updated_at", ""),
        }
    except Exception as e:
        logger.error(f"Error updating profile for {email}: {e}")
        raise


def delete_user(email: str) -> bool:
    """
    Delete a user account.
    
    Args:
        email: User email
    
    Returns:
        True if user was deleted, False if user didn't exist
    """
    if not email:
        return False
    
    email = email.strip().lower()
    p = _user_file_path(email)
    
    if not p.exists():
        return False
    
    try:
        p.unlink()
        logger.info(f"Deleted user: {email}")
        return True
    except Exception as e:
        logger.error(f"Error deleting user {email}: {e}")
        return False
