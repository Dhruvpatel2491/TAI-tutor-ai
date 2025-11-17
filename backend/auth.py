import os
import time
from typing import Optional, Dict

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
