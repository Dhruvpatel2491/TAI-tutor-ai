"""
Admin authentication module for TAI-tutor-ai.
Manages password verification against hashed credentials stored in user_data/admin/credentials.json.
"""
import os
import json
import base64
import hashlib
from pathlib import Path
from typing import Optional, Dict

# Path to admin credentials
ADMIN_CREDS_PATH = Path(__file__).parent.parent / "user_data" / "admin" / "credentials.json"


def _load_admin_credentials() -> Optional[Dict]:
    """Load admin credentials from JSON file."""
    try:
        if not ADMIN_CREDS_PATH.exists():
            return None
        with open(ADMIN_CREDS_PATH, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading admin credentials: {e}")
        return None


def _hash_password(password: str, salt: str) -> str:
    """
    Hash a password using PBKDF2_HMAC with SHA256.
    
    Args:
        password: Plain text password
        salt: Base64-encoded salt
        
    Returns:
        Base64-encoded password hash
    """
    salt_bytes = base64.b64decode(salt)
    # Use PBKDF2 with 100,000 iterations for security
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt_bytes, 100000)
    return base64.b64encode(pwd_hash).decode('utf-8')


def verify_admin_password(password: str) -> bool:
    """
    Verify an admin password against the stored hash.
    
    Args:
        password: Plain text password to verify
        
    Returns:
        True if password matches, False otherwise
    """
    creds = _load_admin_credentials()
    if not creds:
        # If no credentials file, check against default "admin" password
        # with a default salt for initial setup
        default_salt = base64.b64encode(os.urandom(16)).decode('utf-8')
        default_hash = _hash_password("admin", default_salt)
        # For fallback, we'll just check if password is "admin"
        return password == "admin"
    
    try:
        salt = creds.get('salt')
        stored_hash = creds.get('password_hash')
        
        if not salt or not stored_hash:
            return False
        
        # Hash the provided password with the stored salt
        computed_hash = _hash_password(password, salt)
        
        # Compare hashes
        return computed_hash == stored_hash
    except Exception as e:
        print(f"Error verifying admin password: {e}")
        return False


def update_admin_password(new_password: str) -> bool:
    """
    Update the admin password with a new value.
    
    Args:
        new_password: New plain text password
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Generate new salt
        salt = base64.b64encode(os.urandom(16)).decode('utf-8')
        # Hash the new password
        pwd_hash = _hash_password(new_password, salt)
        
        # Create credentials object
        creds = {
            "salt": salt,
            "password_hash": pwd_hash,
            "created_at": None,
            "last_updated": None
        }
        
        # Ensure directory exists
        ADMIN_CREDS_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        # Write to file
        with open(ADMIN_CREDS_PATH, 'w') as f:
            json.dump(creds, f, indent=2)
        
        return True
    except Exception as e:
        print(f"Error updating admin password: {e}")
        return False


def initialize_default_admin():
    """
    Initialize default admin credentials if they don't exist.
    Sets password to "admin" by default.
    """
    if not ADMIN_CREDS_PATH.exists():
        print("Initializing default admin credentials...")
        update_admin_password("admin")
        print(f"Admin credentials created at {ADMIN_CREDS_PATH}")
