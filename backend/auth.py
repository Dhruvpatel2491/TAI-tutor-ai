import os
import time
from typing import Optional, Dict
from flask import Request

# Read config from env; keep existing default ("dev") behavior if env not set.
DEFAULT_DEV_USER = os.getenv("DEFAULT_DEV_USER", "dev")

# Accept common env names; prefer DISABLE_AUTH (matches server.py). Treat common
# truthy strings as True. Default to False to avoid disabling auth accidentally.
AUTH_DISABLED = str(os.getenv("DISABLE_AUTH", os.getenv("AUTH_DISABLED", os.getenv("DISABLED_AUTH", "false")))).lower().strip() in ("1", "true", "yes", "on")


def _extract_email_from_headers(req: Request) -> Optional[str]:
    """
    Try common headers used by auth proxies to carry the authenticated user's email.
    """
    headers = req.headers
    for h in ("X-User-Email", "X-Forwarded-User", "X-Auth-User", "X-Forwarded-Email"):
        val = headers.get(h)
        if val:
            return val
    # Try Authorization: Bearer <token>; if token looks like an email, return it.
    auth = headers.get("Authorization") or headers.get("authorization")
    if auth and auth.startswith("Bearer "):
        token = auth.split(" ", 1)[1].strip()
        if "@" in token and " " not in token:
            return token
    return None


def get_user_from_request(req: Request) -> Dict:
    """
    Return a dict with keys: auth_disabled (bool), default_dev_user (str), user_id (str|None).
    When auth is enabled, prefer the login email extracted from headers; fall back to None.
    When auth is disabled, return the default dev user as before.
    """
    if AUTH_DISABLED:
        return {"auth_disabled": True, "default_dev_user": DEFAULT_DEV_USER, "user_id": DEFAULT_DEV_USER}

    # Auth enabled: extract login email from headers (requires auth proxy to set these headers)
    email = _extract_email_from_headers(req)
    return {"auth_disabled": False, "default_dev_user": DEFAULT_DEV_USER, "user_id": email}


try:
    import jwt
except Exception:  # pragma: no cover - if PyJWT missing, raise helpful error at import
    raise

JWT_SECRET = os.environ.get("BACKEND_JWT_SECRET", "tai")
JWT_ALGORITHM = os.environ.get("BACKEND_JWT_ALGORITHM", "HS256")
JWT_EXP_SECONDS = int(os.environ.get("BACKEND_JWT_EXP", "3600"))


def create_jwt_for_user(user_id: str, exp_seconds: Optional[int] = None) -> str:
    """Create a signed JWT for the given user_id."""
    if exp_seconds is None:
        exp_seconds = JWT_EXP_SECONDS
    payload = {"sub": str(user_id), "iat": int(time.time()), "exp": int(time.time()) + int(exp_seconds)}
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    # PyJWT >=2 returns str, older may return bytes
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


def verify_jwt(token: str) -> Optional[Dict]:
    """Verify token and return payload dict or None if invalid/expired."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except Exception:
        return None


def extract_bearer_token(authorization_header: Optional[str]) -> Optional[str]:
    if not authorization_header:
        return None
    parts = authorization_header.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


# --- simple file-backed user store for dev register/login ---
import base64
import hashlib
from pathlib import Path
import json
import datetime


_ROOT_USER_DIR = Path(__file__).resolve().parent.parent / "user_data" / "login_register"


def _ensure_user_dir():
    try:
        _ROOT_USER_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


def _safe_filename_for_email(email: str) -> str:
    # keep deterministic, reversible-ish mapping but avoid filesystem chars
    return email.replace("@", "__at__").replace(".", "__dot__")


def _user_file_path(email: str) -> Path:
    _ensure_user_dir()
    fn = _safe_filename_for_email(email.strip().lower()) + ".json"
    return _ROOT_USER_DIR / fn


def register_user(email: str, password: str, name: str = "") -> dict:
    """Register a user by saving a salted PBKDF2-SHA256 password hash to disk.

    Returns a dict with stored user metadata. Raises ValueError on invalid input
    or if user already exists.
    """
    if not email or not password:
        raise ValueError("email and password required")
    # if not name or not name.strip():
    #     raise ValueError("name is required")
    email = email.strip().lower()
    name = name.strip()
    p = _user_file_path(email)
    if p.exists():
        raise ValueError("user already exists")

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
    return payload


def verify_user(email: str, password: str) -> bool:
    """Verify a user's password. Returns True on success, False otherwise."""
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
    email = (email or "").strip().lower()
    return _user_file_path(email).exists()


def get_user_profile(email: str) -> dict:
    """Get user profile data from disk. Returns dict with name, email, created_at, or empty dict if not found."""
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


