"""
Admin authentication module for TAI Tutor AI.

This module handles admin password verification using PBKDF2-SHA256.
Provides secure password hashing and verification for admin access.
"""

import os
import json
import hashlib
import logging
from pathlib import Path
from typing import Optional

# Import with fallback for running as script
try:
    from config import ADMIN_CREDENTIALS_FILE, ADMIN_USERNAME, ADMIN_PASSWORD_HASH
except ImportError:
    from config import ADMIN_CREDENTIALS_FILE, ADMIN_USERNAME, ADMIN_PASSWORD_HASH

logger = logging.getLogger("backend.admin.admin_auth")


def _hash_password(password: str, salt: Optional[bytes] = None) -> tuple:
    """
    Hash password using PBKDF2-SHA256.
    
    Args:
        password: Plain text password
        salt: Optional salt bytes (generated if not provided)
    
    Returns:
        Tuple of (hash_hex, salt_hex)
    """
    if salt is None:
        salt = os.urandom(32)
    
    # PBKDF2 with SHA256, 100k iterations
    dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
    return dk.hex(), salt.hex()


def _verify_password(password: str, stored_hash: str, salt_hex: str) -> bool:
    """
    Verify a password against stored hash.
    
    Args:
        password: Plain text password to verify
        stored_hash: Stored password hash (hex)
        salt_hex: Salt used in hashing (hex)
    
    Returns:
        True if password matches, False otherwise
    """
    try:
        salt = bytes.fromhex(salt_hex)
        computed_hash, _ = _hash_password(password, salt)
        return computed_hash == stored_hash
    except Exception as e:
        logger.error(f"Password verification failed: {e}")
        return False


def _load_admin_credentials() -> Optional[dict]:
    """Load admin credentials from file."""
    try:
        creds_path = Path(ADMIN_CREDENTIALS_FILE)
        if not creds_path.exists():
            return None
        with open(creds_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load admin credentials: {e}")
        return None


def _save_admin_credentials(username: str, password_hash: str, salt: str) -> bool:
    """Save admin credentials to file."""
    try:
        creds_path = Path(ADMIN_CREDENTIALS_FILE)
        creds_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "username": username,
            "password_hash": password_hash,
            "salt": salt
        }
        
        tmp_path = creds_path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, creds_path)
        
        logger.info("Admin credentials saved successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to save admin credentials: {e}")
        return False


def verify_admin_password(username: str, password: str) -> bool:
    """
    Verify admin credentials.
    
    First checks environment variables, then falls back to credentials file.
    
    Args:
        username: Admin username
        password: Admin password
    
    Returns:
        True if credentials are valid, False otherwise
    """
    # Check environment variables first
    if ADMIN_USERNAME and ADMIN_PASSWORD_HASH:
        if username == ADMIN_USERNAME:
            # If password hash is in format "hash:salt", parse it
            if ":" in ADMIN_PASSWORD_HASH:
                stored_hash, salt = ADMIN_PASSWORD_HASH.split(":", 1)
                return _verify_password(password, stored_hash, salt)
            else:
                # Plain comparison (not recommended for production)
                return password == ADMIN_PASSWORD_HASH
    
    # Check credentials file
    creds = _load_admin_credentials()
    if creds:
        if creds.get("username") == username:
            stored_hash = creds.get("password_hash", "")
            salt = creds.get("salt", "")
            if stored_hash and salt:
                return _verify_password(password, stored_hash, salt)
    
    logger.warning(f"Admin authentication failed for username: {username}")
    return False


def set_admin_password(username: str, password: str) -> bool:
    """
    Set or update admin password.
    
    Args:
        username: Admin username
        password: New admin password
    
    Returns:
        True if password was set successfully
    """
    try:
        password_hash, salt = _hash_password(password)
        return _save_admin_credentials(username, password_hash, salt)
    except Exception as e:
        logger.error(f"Failed to set admin password: {e}")
        return False


def is_admin_configured() -> bool:
    """Check if admin credentials are configured."""
    # Check env vars
    if ADMIN_USERNAME and ADMIN_PASSWORD_HASH:
        return True
    
    # Check credentials file
    creds = _load_admin_credentials()
    return creds is not None and "password_hash" in creds


def get_admin_username() -> Optional[str]:
    """Get configured admin username."""
    if ADMIN_USERNAME:
        return ADMIN_USERNAME
    
    creds = _load_admin_credentials()
    if creds:
        return creds.get("username")
    
    return None
